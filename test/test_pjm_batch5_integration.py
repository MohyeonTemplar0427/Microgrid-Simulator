"""Normal regional forms, queued workers and saved results for five additions."""
from copy import deepcopy
from io import BytesIO
import json
from zipfile import ZipFile

import numpy as np
import pytest

from src.billing.regional import adapter
from src.billing.regional_counterfactual import grid_only_counterfactual
from src.local_web.regional_study import capabilities, prepare
from test_local_web import service, wait_for_study
from test_regional_study import browser_request
from tools.run_regional_validation import PJM_BATCH5_CASES, case_request, selected_cases

IDENTITY={
    "appalachian_power_west_virginia":("WV","AEP"),
    "pepco_district_of_columbia":("DC","PEPCO"),
    "delmarva_delaware":("DE","DPL"),
    "mon_power_west_virginia":("WV","APS"),
    "indiana_michigan_power_michigan":("MI","AEP"),
}


def request(utility,kind,plan):
    return case_request(utility,kind,"monthly",plan=plan)


@pytest.mark.parametrize("utility,kind,plan",PJM_BATCH5_CASES)
def test_form_keeps_dates_source_identity_and_evidence(utility,kind,plan):
    raw=request(utility,kind,plan)
    r=browser_request(raw)
    assert r=={**raw,"name":"Untitled study"}
    cap=capabilities()["utilities"][utility]
    assert (cap["state"],cap["transmission_zone"])==IDENTITY[utility]
    assert cap["grid_operator"]=="PJM" and (utility,kind,plan) in selected_cases([utility])
    assert r["regional_account"]["wholesale_pricing_location"] is None
    assert r["regional_account"]["retail_supplier"]==utility
    assert r["operating_contract"]["renewable_only_charging"]
    assert prepare(r)[0].index[0].strftime("%Y-%m-%d")==r["start_date"]
    for field,bad in (("distribution_utility","indiana_michigan_power_indiana"),
                      ("state_jurisdiction","XX"),("transmission_zone","OTHER"),("retail_supplier","other")):
        altered=deepcopy(r);altered["regional_account"][field]=bad
        with pytest.raises(ValueError):prepare(altered)
    altered=deepcopy(r);altered["operating_contract"]["grid_charging_confirmed"]=True
    with pytest.raises(ValueError):prepare(altered)
    altered=deepcopy(r);altered["account"]["der_ordinary_service_confirmed"]=False
    with pytest.raises(ValueError):prepare(altered)
    # Request compatibility only. No external carbon data are fetched here.
    r["carbon"]={"source":"electricity_maps","region":"US-MIDA-PJM"}
    prepare(r)


@pytest.mark.parametrize("utility,kind,plan",PJM_BATCH5_CASES)
def test_native_scope_and_absent_der_reference(utility,kind,plan):
    r=request(utility,kind,plan)
    with pytest.raises(ValueError):
        adapter(utility).validate_native_load(r["account"],np.full(3000,100.))
    reference=grid_only_counterfactual(utility,r["account"])
    assert reference["account"]["der_ordinary_service_confirmed"] is False
    for field in ("der_eligibility_source","der_activation_date"):
        assert reference["account"][field]==""
    assert all(reference["account"][key]==value for key,value in r["account"].items()
               if key not in reference["changed_account_fields"])


@pytest.mark.parametrize("utility,kind,plan",PJM_BATCH5_CASES)
def test_queued_worker_bills_save_reopen_csv_and_zip(service,utility,kind,plan):
    app,call,headers=service
    endpoints={
        "appalachian_power_west_virginia":("2026-10-01","2026-10-31"),
        "pepco_district_of_columbia":("2026-10-01","2026-10-31"),
        "delmarva_delaware":("2026-11-01","2026-11-30"),
        "mon_power_west_virginia":("2026-11-01","2026-11-30"),
        "indiana_michigan_power_michigan":("2026-09-01","2026-09-30"),
    }
    start,end=endpoints[utility]
    r=browser_request(case_request(utility,kind,"custom",plan=plan,start_date=start,end_date=end))
    run=call("/api/v1/regional/studies",r,headers)
    result=wait_for_study(call,run["id"])
    assert result["status"]=="completed",result.get("error")
    output=result["result"]
    assert output["engine_id"]==app.engine["id"] and output["is_complete_bill"]
    assert output["ac_validation"]["all_intervals_feasible"]
    base="/api/studies/"+run["id"]
    t=call(base+"/tables/comparison")
    rows=[dict(zip(t["columns"],row)) for row in t["data"]]
    assert {x["scenario"] for x in rows}=={"grid_only","pv_only","pv_battery"}
    assert max(x["maximum_reconciliation_difference_usd"] for x in rows)<.0001
    assert all(cycle["cost_optimum_proven"] is True
               for scenario in ("pv_only","pv_battery")
               for cycle in output["optimization"][scenario]["cycles"])
    run_dir=app.store.directory/"runs"/run["id"]
    with ZipFile(BytesIO(call(base+"/tables.zip"))) as archive:
        assert archive.testzip() is None
        assert json.loads(archive.read("result-manifest.json"))==output
        for table in output["tables"]:
            filename=table["id"]+".csv"
            assert archive.read(filename)==call(base+"/tables/"+filename)==(run_dir/filename).read_bytes()
    call(base+"/save",{"name":utility+" "+plan+" acceptance"},headers)
    assert call(base)["saved"]
    reopened=call(base+"/request.json")
    assert browser_request(reopened)["account"]==r["account"]
    assert reopened["billing_cycles"]==r["billing_cycles"]
