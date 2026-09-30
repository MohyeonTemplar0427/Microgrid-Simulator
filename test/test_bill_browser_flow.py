"""Exercise the shipped browser bill client against the real private HTTP API."""
import base64
import json
import subprocess
import threading
from pathlib import Path

from src.local_web.runtime import Application
from src.local_web.server import make_server
from test_bill_analysis import _pdf


CLIENT = Path(__file__).resolve().parents[1] / "src/local_web/static/bills.js"


def _statement(start, end, days, usage):
    return _pdf([
        "Electric Usage", "Utility: Example Electric", "Rate Schedule: R-1",
        f"{start} to {end} ({days} billing days)",
        f"Total Usage {usage} kWh", "Total Electric Charges $100.00",
    ])


def test_browser_bill_client_reviews_text_and_scanned_pdfs_without_persisting(tmp_path, monkeypatch):
    from src.bill_analysis import pdf

    monkeypatch.setattr(pdf, "_local_ocr", lambda _content, pages: {
        page: "Electric Usage\nUtility: Example Electric\n"
              "03/01/2026 to 03/31/2026 (31 billing days)\n"
              "Total Usage 310 kWh\nTotal Electric Charges $120.00"
        for page in pages
    })
    app = Application(tmp_path, embedded_worker=False)
    original_json = set(tmp_path.rglob("*.json"))
    server = make_server(app, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    script = r"""
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {billExtract,billReview,billAnalyze,billCorrectionValue,billPdfBase64}=require(process.argv[1]);
const base=process.argv[2], inputs=JSON.parse(fs.readFileSync(0,'utf8'));
async function run(){
  const page=await fetch(base+'/');assert.equal(page.status,200);
  const html=await page.text();assert.match(html,/Bills &amp; usage data/);
  assert.match(html,/Analyze my bills without a simulation/);
  assert.match(html,/Download CSV/);
  const js=await fetch(base+'/bills.js');assert.equal(js.status,200);
  const caps=await (await fetch(base+'/api/capabilities')).json();
  async function post(path,body,token=caps.token){
    const response=await fetch(base+path,{method:'POST',headers:{'Content-Type':'application/json','X-Study-Token':token},body:JSON.stringify(body)});
    assert.equal(response.headers.get('cache-control'),'no-store');
    const value=await response.json();
    if(!response.ok)throw Object.assign(new Error(value.error||String(response.status)),{status:response.status});
    return value;
  }
  assert.equal(billCorrectionValue('fields.meter_import_kwh',' 300 '),300);
  assert.throws(()=>billCorrectionValue('fields.billing_days','bad'),/number/);
  const oversize=new Uint8Array(12*1024*1024+1);oversize.set(Buffer.from('%PDF-'));
  assert.throws(()=>billPdfBase64(oversize),/12 MiB/);
  const reviewed=[];
  for(const [index,encoded] of inputs.entries()){
    const draft=await billExtract(new Uint8Array(Buffer.from(encoded,'base64')),post);
    assert.equal(draft.pages[0].page,1);
    assert.equal(draft.pages[0].method,index===2?'local_ocr':'embedded_text');
    assert.equal(draft.fields.meter_import_kwh.evidence[0].page,1);
    assert.ok(draft.fields.maximum_demand_kw.status==='missing');
    if(index===0){
      const invalid=await billReview(draft,{'fields.billing_days':{value:31,reason:'test'}},false,post);
      assert.ok(invalid.issues.some(issue=>issue.code==='billing_days_mismatch'));
      await assert.rejects(()=>billReview(invalid,{},true,post),/billing_days_mismatch/);
    }
    const corrected=await billReview(draft,{'fields.billing_plan':{value:'Checked printed label',reason:'Page 1'}},false,post);
    assert.equal(corrected.fields.billing_plan.status,'corrected');
    assert.equal(corrected.corrections[0].reason,'Page 1');
    const approved=await billReview(corrected,{},true,post);
    assert.equal(approved.approved,true);reviewed.push(approved);
  }
  const report=await billAnalyze(reviewed,post);
  assert.equal(report.cycles.length,3);
  assert.equal(report.basis,'observed_utility_meter_purchases_not_native_building_load');
  assert.ok(report.recommendations.every(item=>item.estimated_savings_usd===null));
  await assert.rejects(()=>billAnalyze([reviewed[0],reviewed[0]],post),/overlap/);
  await assert.rejects(()=>post('/api/v1/bills/review',{draft:reviewed[0],corrections:{},approve:true},'wrong'),error=>error.status===403);
  await assert.rejects(()=>billExtract(new Uint8Array(Buffer.from('not a pdf')),post),/PDF document/);
  console.log(JSON.stringify({cycles:report.cycles.length,methods:['embedded_text','local_ocr']}));
}
run().catch(error=>{console.error(error);process.exitCode=1});
"""
    try:
        source = [
            _statement("01/01/2026", "01/30/2026", 30, 300),
            _statement("02/01/2026", "02/28/2026", 28, 280),
            _pdf(),
        ]
        result = subprocess.run(
            ["node", "-e", script, str(CLIENT), f"http://127.0.0.1:{server.server_port}"],
            input=json.dumps([base64.b64encode(item).decode() for item in source]),
            text=True, capture_output=True, timeout=90, check=False,
        )
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["cycles"] == 3
        assert not list(tmp_path.rglob("*.pdf"))
        assert set(tmp_path.rglob("*.json")) == original_json
    finally:
        server.shutdown()
        thread.join()
        server.server_close()
        app.close()
