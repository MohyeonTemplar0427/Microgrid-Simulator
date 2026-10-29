"""Offline browser contracts for optional regional carbon and visible results."""
import json
from pathlib import Path
import subprocess

import pytest

from src.local_web.regional_study import defaults


ROOT = Path(__file__).resolve().parents[1]


def node(script, value):
    result = subprocess.run(["node", "-e", script], input=json.dumps(value), text=True,
                            cwd=ROOT, capture_output=True, check=True)
    return json.loads(result.stdout)


@pytest.mark.parametrize("enabled", [False, True])
def test_pjm_checkbox_serializes_explicit_source_without_mutating_saved_settings(enabled):
    request = defaults("firstenergy_pa_penn_power", "residential")
    script = """
    const fs=require('fs'), x=JSON.parse(fs.readFileSync(0,'utf8'));
    const {buildRegionalStudyRequest}=require('./src/local_web/static/regional.js');
    const r=x.request, v={...r,...r.site, site_label:r.site.label,
      cycles:r.billing_cycles, load_mode:r.load.mode, load_power_kw:r.load.power_kw,
      archetype:r.load.archetype, rg_load_source:r.load.source,
      rg_native_confirmed:r.load.native_basis_confirmed, rg_carbon:x.enabled,
      pv_choice:'no', rg_export:'non_export', rg_operation_source:r.operating_contract.reference,
      rg_credit_policy:r.credit_objective_policy};
    const output=buildRegionalStudyRequest(r,v);
    process.stdout.write(JSON.stringify({carbon:output.carbon,original:r}));
    """
    result = node(script, {"request": request, "enabled": enabled})
    assert result["carbon"] == ({"source": "electricity_maps", "region": "US-MIDA-PJM"}
                                if enabled else None)
    assert result["original"] == request


def test_non_pjm_switch_clears_carbon_without_assigning_factor_from_state_or_coordinates():
    script = """
    const {regionalCarbonControl}=require('./src/local_web/static/regional.js');
    const input={checked:true};
    regionalCarbonControl(input,'PJM');const pjm={...input};
    regionalCarbonControl(input,'MISO');const miso={...input};
    regionalCarbonControl(input,'PJM');
    process.stdout.write(JSON.stringify({pjm,miso,back:input}));
    """
    result = node(script, None)
    assert result == {"pjm": {"checked": True, "disabled": False},
                      "miso": {"checked": False, "disabled": True},
                      "back": {"checked": False, "disabled": False}}


def test_regional_result_summary_uses_saved_carbon_provenance_and_labels_missing_calculation():
    metadata = {"status": "verified", "source": "electricity_maps", "zone": "US-MIDA-PJM",
                "provider_interval_minutes": 15, "study_interval_minutes": 30,
                "coverage": {"start_utc": "2025-01-01T05:00:00+00:00",
                             "end_exclusive_utc": "2026-01-01T05:00:00+00:00",
                             "estimated_interval_count": 44, "interval_count": 35040}}
    script = """
    const fs=require('fs'), meta=JSON.parse(fs.readFileSync(0,'utf8'));
    const {regionalCarbonResultText}=require('./src/local_web/static/regional.js');
    process.stdout.write(JSON.stringify({verified:regionalCarbonResultText(meta),
      omitted:regionalCarbonResultText(),disabled:regionalCarbonResultText({status:'not_requested'})}));
    """
    result = node(script, metadata)
    assert metadata["zone"] in result["verified"]
    assert metadata["coverage"]["start_utc"] in result["verified"]
    assert "kg CO₂e" in result["verified"]
    assert "not marginal avoided emissions" in result["verified"]
    assert "Exports receive no emissions credit" in result["verified"]
    assert "Bill optimization is unchanged" in result["verified"]
    assert "44 / 35040" in result["verified"]
    assert "Provider resolution: 15 minutes; study resolution: 30 minutes" in result["verified"]
    assert result["omitted"] == result["disabled"]
    assert "not calculated" in result["disabled"] and "not zero" in result["disabled"]


def test_actual_default_comparison_renderer_shows_emissions_units_and_retains_missing_values():
    """Run the production table renderer with its real default column selection."""
    script = """
    const fs=require('fs'),vm=require('vm');
    const source=fs.readFileSync('./src/local_web/static/app.js','utf8');
    const renderer=source.slice(source.indexOf('async function loadTable()'),source.indexOf('function tableAction'));
    function element(tag){return {tag,children:[],parentElement:{},append(...x){this.children.push(...x);},
      replaceChildren(...x){this.children=x;},textContent:'',checked:false};}
    const nodes={};const $=id=>nodes[id]||(nodes[id]=element('div'));
    const table={columns:['scenario','grid_import_emissions_kg_co2e','emissions_difference_vs_grid_kg_co2e'],
      labels:['Scenario','raw emissions name','raw difference name'],
      data:[['grid_only',12.5,0],['pv_only',null,null]],total:2};
    const context={$,document:{createElement:element},api:async()=>table,activeId:'test',
      activeStudy:{request:{schema_version:11}},offset:0,PAGE_SIZE:100,tableRequest:0,
      window:{regionalUI:{comparisonChart(){}}},names:{grid_only:'Grid only',pv_only:'Solar'}};
    $('table-select').value='comparison';
    (async()=>{await vm.runInNewContext(renderer+';loadTable()',context);
      const rendered=$('table-container').children[0];
      process.stdout.write(JSON.stringify({headers:rendered.children[0].children[0].children.map(x=>x.textContent),
        rows:rendered.children[1].children.map(row=>row.children.map(x=>x.textContent))}));})();
    """
    result = node(script, None)
    assert result["headers"] == ["Scenario", "Grid-import emissions (kg CO₂e)",
                                 "Grid reference − scenario (kg CO₂e)"]
    assert result["rows"][0] == ["Grid only", "12.5", "0"]
    assert result["rows"][1] == ["Solar", "—", "—"]
