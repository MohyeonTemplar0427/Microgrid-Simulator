"""Shared exact numerical / bounded MILP tariff operations.

This module contains no utility rates. Utility charge expressions own pricing;
the optimizer supplies finite physical bounds and collects constraints here.
"""
import numpy as np
import pandas as pd


class BillingMath:
    def __init__(self, index, *, convex=False, power_bound=None, constraints=None):
        self.index = pd.DatetimeIndex(index)
        if len(self.index) < 2 or self.index.tz is None:
            raise ValueError("Billing requires a complete timezone-aware interval grid.")
        seconds = np.diff(self.index.asi8) / 1e9
        if not np.all(seconds == seconds[0]) or seconds[0] <= 0:
            raise ValueError("Billing intervals must be unique, ordered and uniformly spaced in UTC.")
        self.hours = float(seconds[0] / 3600)
        self.convex = convex
        self.constraints = [] if constraints is None else constraints
        self.power_bound = power_bound
        self._bounds = {}
        self._maximum_graphs = {}
        self._entry_bounds = {}
        self._sum_bounds = {}
        self._condition_selectors = {}
        if convex and (power_bound is None or not np.isfinite(power_bound) or power_bound <= 0):
            raise ValueError("Exact tariff optimization requires a finite positive import/export bound.")

    def register(self, x, lower, upper):
        if self.convex and hasattr(x, "id"):
            self._bounds[x.id] = (float(lower), float(upper))
        return x

    def register_power(self,x,lower,upper,*,energy_upper=None):
        lower,upper=(np.asarray(v,dtype=float) for v in (lower,upper))
        self.register(x,float(lower.min()),float(upper.max()))
        self._entry_bounds[x.id]=(lower,upper)
        self._sum_bounds[x.id]=(float(lower.sum()),float(upper.sum()) if energy_upper is None else energy_upper/self.hours)
        return x

    def bounds(self, x):
        if not hasattr(x, "args"):
            a = np.asarray(x, dtype=float)
            return float(a.min()), float(a.max())
        if x.is_constant():
            return self.bounds(x.value)
        if x.id in self._bounds:
            return self._bounds[x.id]
        name = type(x).__name__
        args = x.args
        if name == "AddExpression":
            pairs = [self.bounds(a) for a in args]
            return sum(a for a, _ in pairs), sum(b for _, b in pairs)
        if name == "NegExpression":
            a, b = self.bounds(args[0]); return -b, -a
        if name in ("index", "special_index", "reshape", "Promote", "broadcast_to"):
            return self.bounds(args[0])
        if name == "Sum":
            a, b = self.bounds(args[0]); return a*args[0].size, b*args[0].size
        if name in ("multiply", "MulExpression", "DivExpression"):
            a, b = self.bounds(args[0]); c, d = self.bounds(args[1])
            if name == "DivExpression":
                if c <= 0 <= d:
                    raise ValueError("Cannot bound a tariff division crossing zero.")
                c, d = min(1/c, 1/d), max(1/c, 1/d)
            values = (a*c, a*d, b*c, b*d)
            return min(values), max(values)
        raise ValueError("No finite proven tariff bound for "+name+"; refusing an arbitrary big-M.")

    def sum(self, x):
        if not self.convex or not hasattr(x, "is_constant"):
            return np.sum(x)
        import cvxpy as cp
        result = cp.sum(x)
        if getattr(x,"id",None) in self._sum_bounds:
            return self.register(result,*self._sum_bounds[x.id])
        lo, hi = self.bounds(x)
        return self.register(result, lo*x.size, hi*x.size)

    def dot(self, x, coefficients):
        if not self.convex or not hasattr(x, "is_constant"):
            return float(np.dot(np.asarray(x), np.asarray(coefficients)))
        import cvxpy as cp
        coeff = np.asarray(coefficients, dtype=float)
        identity = getattr(x, "id", None)
        if identity in self._sum_bounds and coeff.size and np.all(coeff == coeff.flat[0]):
            # A constant dated rate must retain the physical total-energy cap;
            # multiplying a global interval maximum by the horizon loses it.
            lo, hi = self._sum_bounds[identity]
            scale = float(coeff.flat[0])
            a, b = sorted((lo*scale, hi*scale))
        else:
            lo, hi = self._entry_bounds.get(identity, self.bounds(x))
            a = np.where(coeff >= 0, coeff*lo, coeff*hi).sum()
            b = np.where(coeff >= 0, coeff*hi, coeff*lo).sum()
        return self.register(cp.sum(cp.multiply(x, coeff)), a, b)

    @staticmethod
    def _condition_key(value):
        """Recognize scalar multiples without aliasing different sliced inputs."""
        if not hasattr(value, "args"):
            scalar = np.asarray(value)
            return ("constant", float(scalar)) if scalar.size == 1 else ("object", id(value))
        # Parameter values can change; equal current values are not identities.
        if value.parameters():
            return ("expression", value.id)
        if value.is_constant():
            scalar = np.asarray(value.value)
            return ("constant", float(scalar)) if scalar.size == 1 else ("object", id(value))
        if value.shape == () and type(value).__name__ in ("multiply", "MulExpression"):
            left, right = value.args
            for constant, expression in ((left, right), (right, left)):
                if constant.is_constant() and constant.size == 1:
                    child = BillingMath._condition_key(expression)
                    scale = float(np.asarray(constant.value))
                    if child[0] == "scaled":
                        return ("scaled", scale*child[1], child[2])
                    return ("scaled", scale, child)
        return ("expression", value.id)

    def affine(self, value):
        """Materialize nested tariff maxima before an exact equality/selector.

        A convex epigraph is sufficient in a monotone positive objective but
        cannot be substituted into a minimum, negative coefficient or branch.
        Rebuild only our known bounded graphs; reject unknown nonlinear atoms.
        """
        if not hasattr(value,"is_affine") or value.is_affine():
            return value
        if value.id in self._maximum_graphs:
            a,b=self._maximum_graphs[value.id]
            return self.maximum(a,b,exact=True)
        result=value.copy(args=[self.affine(arg) for arg in value.args])
        if not result.is_affine():
            raise ValueError("Unsupported nonlinear tariff operation in exact graph: "+type(value).__name__)
        return result

    def maximum(self, a, b=None, *, exact=False, upper_bound=None):
        if not self.convex:
            return np.max(a) if b is None else np.maximum(a, b)
        import cvxpy as cp
        if exact:
            a=[self.affine(v) for v in a] if isinstance(a,(list,tuple)) else self.affine(a)
            b=self.affine(b) if b is not None else None
        values = cp.hstack(a) if isinstance(a, (list, tuple)) else a
        if b is not None:
            values = cp.hstack([values, b])
        if not hasattr(values, "is_constant") or values.is_constant():
            return float(np.max(values.value if hasattr(values, "value") else values))
        if b is not None and np.prod(getattr(a, "shape", ())) > 1:
            raise ValueError("Use scalar tariff maxima; vector selectors must be explicit.")
        bounds = [self.bounds(v) for v in (a if isinstance(a, (list, tuple)) else [a])]
        if b is not None:
            bounds.append(self.bounds(b))
        lower, upper = max(lo for lo, _ in bounds), max(hi for _, hi in bounds)
        entries=self._entry_bounds.get(getattr(values,"id",None))
        if entries is not None:
            lower,upper=float(np.max(entries[0])),float(np.max(entries[1]))
        if lower == upper:
            return lower
        # For a vector, the maximum has the same safe interval as its entries.
        if not exact:
            result=self.register(cp.max(values), lower, upper)
            self._maximum_graphs[result.id]=(a,b)
            return result
        flat = cp.reshape(values, (values.size,), order="C")
        result = cp.Variable()
        possible=np.arange(values.size) if entries is None else np.flatnonzero(np.asarray(entries[1]).reshape(-1)>=lower)
        selected = cp.Variable(len(possible), boolean=True)
        min_entry = min(lo for lo, _ in bounds)
        big_m=(upper-min_entry) if entries is None else upper-np.asarray(entries[0]).reshape(-1)[possible]
        self.constraints.extend([result >= flat, result <= flat[possible]+cp.multiply(big_m,1-selected),
                                 cp.sum(selected) == 1, result >= lower, result <= upper])
        return self.register(result, lower, upper)

    def minimum(self, a, b):
        if not self.convex:
            return np.minimum(a, b)
        return -self.maximum(-a, -b, exact=True)

    def positive(self, x, *, exact=False):
        return self.maximum(x, 0., exact=exact)

    def choose_leq(self, x, threshold, true_value, false_value):
        if not self.convex:
            return true_value if x <= threshold else false_value
        import cvxpy as cp
        test = self.affine(x)-self.affine(threshold)
        true_value,false_value=self.affine(true_value),self.affine(false_value)
        lo, hi = self.bounds(test)
        if hi <= 0:
            return true_value
        if lo > 0:
            return false_value
        key = (self._condition_key(x), self._condition_key(threshold))
        if key not in self._condition_selectors:
            selector = self._condition_selectors[key] = cp.Variable(boolean=True)
            self.constraints.extend([test <= hi*(1-selector), test >= lo*selector])
        else:
            selector = self._condition_selectors[key]
        a, b = self.bounds(true_value); c, d = self.bounds(false_value)
        result = cp.Variable()
        lower, upper = min(a, c), max(b, d)
        true_above_false = max(0., b-c)
        false_above_true = max(0., d-a)
        # At equality either branch may be selected. Utility expressions using
        # this helper must agree there, or explicitly validate a tolerance band.
        self.constraints.extend([
            result >= true_value-true_above_false*(1-selector), result <= true_value+false_above_true*(1-selector),
            result >= false_value-false_above_true*selector, result <= false_value+true_above_false*selector,
            result >= lower, result <= upper])
        return self.register(result, lower, upper)

    def tiered(self, volume, bounds, rates):
        """Cumulative finite upper bounds and one extra marginal rate.

        Exact filled tiers also support decreasing prices; no convex envelope.
        Bounds can be tariff expressions (e.g. hours-use demand blocks).
        """
        if len(rates) != len(bounds)+1:
            raise ValueError("Supply cumulative finite tier bounds and a final rate.")
        remaining, total, previous = volume, 0., 0.
        for limit, rate in zip(bounds, rates):
            used = self.minimum(self.positive(remaining, exact=True), limit-previous)
            total += used*rate
            remaining -= used
            previous = limit
        return total+remaining*rates[-1]

    def demand(self, power, index, minutes, mask=None, *, exact=False, upper_bound=None):
        index = pd.DatetimeIndex(index)
        native = self.hours*60
        ratio = round(minutes/native)
        if ratio < 1 or not np.isclose(ratio*native, minutes) or len(index) % ratio:
            raise ValueError("Demand intervals require complete aligned averaging blocks.")
        starts = index[::ratio]
        if np.any(starts.minute % minutes) or np.any(starts.second):
            raise ValueError("Demand averaging must align with utility clock boundaries.")
        eligible = np.ones(len(starts), dtype=bool)
        if mask is not None:
            mask = np.asarray(mask, dtype=bool)
            if mask.shape == (len(index),):
                blocks = mask.reshape(-1, ratio)
                if np.any(blocks.any(axis=1) != blocks.all(axis=1)):
                    raise ValueError("Demand window splits a utility averaging block.")
                eligible = blocks[:, 0]
            elif mask.shape == (len(starts),):
                eligible = mask
            else:
                raise ValueError("Demand mask does not match the supplied timestamps.")
        if not eligible.any():
            return 0.
        if not self.convex or not hasattr(power, "is_constant"):
            return float(np.asarray(power).reshape(-1, ratio).mean(axis=1)[eligible].max())
        import cvxpy as cp
        averaged = cp.sum(cp.reshape(power, (len(index)//ratio, ratio), order="C"), axis=1)/ratio
        self.register(averaged, *self.bounds(power))
        values=averaged[eligible]
        if getattr(power,"id",None) in self._entry_bounds:
            lo,hi=self._entry_bounds[power.id]
            lo=lo.reshape(-1,ratio).mean(axis=1)[eligible]
            hi=hi.reshape(-1,ratio).mean(axis=1)[eligible]
            self.register(values,float(lo.min()),float(hi.max()))
            self._entry_bounds[values.id]=(lo,hi)
        return self.maximum(values, exact=exact, upper_bound=upper_bound)
