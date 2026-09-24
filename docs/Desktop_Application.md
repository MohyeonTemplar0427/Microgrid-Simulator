# Desktop application

The default macOS desktop launcher displays the local browser study interface
inside a native WebKit window. The desktop and local browser share the same
HTML/CSS/JavaScript, API routes, validation, billing adapters, dispatch worker,
and result tables. A validated backend feature should be connected to that
shared interface and tested there; it then appears in both modes without a
second set of GUI controls. Keep the two launch modes in scope when reviewing
future backend work.

Run from the project root with:

```sh
/usr/local/bin/python3 -m src.simulation.graphical_interface
```

The desktop launcher starts its own loopback server on an available port and
stops it when the window closes. Studies are stored in
`.cache/local_web_desktop`, separate from the browser server's
`.cache/local_web`; this lets both modes run at once without competing for a
single worker or database lock. The desktop refreshes its pinned local engine
snapshot from the current checkout when launched. Nothing is sent to an
external server except explicit weather, carbon, and location provider
requests made by the study workflow.

The macOS window uses system WebKit and the installed Swift command-line
tools; it adds no Python package. Browser downloads use a native save dialog.
The old Tkinter engineering interface remains available with `--legacy` for
its specialized signal/profile controls. Those controls have not all been
ported to the shared study workflow. On non-macOS systems, continue using the
local browser server or the legacy Tkinter interface.
