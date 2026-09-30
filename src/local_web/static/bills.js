"use strict";
// Observed bills are deliberately separate from simulation load inputs.
const BILL_PDF_LIMIT = 12 * 1024 * 1024;
const BILL_NUMERIC = new Set(['billing_days','meter_import_kwh','current_electric_charges',
  'statement_amount_due','maximum_demand_kw','export_kwh','export_credit','total_charges',
  'interval_minutes','reported_interval_count','amount','quantity_kwh']);
const BILL_DATES = new Set(['period_start','period_end']);

function billPdfBase64(bytes) {
  if (!(bytes instanceof Uint8Array) || bytes.length < 5 ||
      String.fromCharCode(...bytes.subarray(0,5)) !== '%PDF-') throw new Error('Choose a PDF document.');
  if (bytes.length > BILL_PDF_LIMIT) throw new Error('PDF exceeds the 12 MiB analysis limit.');
  let binary = '';
  for (let offset=0; offset<bytes.length; offset+=32768)
    binary += String.fromCharCode(...bytes.subarray(offset,offset+32768));
  return btoa(binary);
}
function billCorrectionValue(path, raw) {
  const name=path.split('.').at(-1), value=raw.trim();
  if (!value) return null;
  if (BILL_NUMERIC.has(name)) {
    const number=Number(value);
    if (!Number.isFinite(number)) throw new Error(`${name.replaceAll('_',' ')} must be a number.`);
    return number;
  }
  return value;
}
async function billExtract(bytes, post) {
  return post('/api/v1/bills/extract',{pdf_base64:billPdfBase64(bytes)});
}
async function billReview(draft, corrections, approve, post) {
  return post('/api/v1/bills/review',{draft,corrections,approve});
}
async function billAnalyze(bills, post) {
  return post('/api/v1/bills/analyze',{bills});
}
if (typeof module !== 'undefined' && module.exports)
  module.exports={billPdfBase64,billCorrectionValue,billExtract,billReview,billAnalyze};

if (typeof document !== 'undefined') (()=>{
  const el=id=>document.getElementById(id), editable=new Map();
  let draft=null, reviewed=[], report=null, revision=0, busy=false, accountType=null;
  const label=name=>({meter_import_kwh:'Meter purchases (kWh)',current_electric_charges:'Current electric charges ($)',
    statement_amount_due:'Statement amount due ($)',billing_plan:'Printed billing plan (unverified)',
    maximum_demand_kw:'Printed maximum demand (kW)',export_kwh:'Printed export (kWh)',
    export_credit:'Printed export credit ($)',interval_minutes:'Printed interval minutes',
    reported_interval_count:'Printed interval count',total_charges:'Section total charges ($)',
    quantity_kwh:'TOU energy (kWh)'}[name]||name.replaceAll('_',' '));
  const text=(tag,value,className)=>{const node=document.createElement(tag);node.textContent=value??'';
    if(className)node.className=className;return node;};
  function error(message){el('bill-error').textContent=message;el('bill-error').hidden=false;}
  function status(message){el('bill-status').textContent=message;el('bill-error').hidden=true;}
  function setBusy(value){busy=value;for(const id of ['bill-extract','bill-review','bill-approve','bill-analyze'])el(id).disabled=value;
    el('bill-file').disabled=value;}
  function showBills(){
    if(accountType==='guest'){window.location.assign('/auth/login');return;}
    document.querySelector('.workspace').hidden=true;el('bill-workspace').hidden=false;
    el('bill-workspace').scrollIntoView({behavior:'smooth',block:'start'});
  }
  function showStudy(){el('bill-workspace').hidden=true;document.querySelector('.workspace').hidden=false;
    el('configure-title').scrollIntoView({behavior:'smooth',block:'start'});}
  function setAccount(type){accountType=type;el('open-bills').hidden=false;
    el('open-bills').textContent=type==='guest'?'Sign in to analyze my bills':'Analyze my bills without a simulation';
    el('bill-signin').hidden=type!=='guest';el('bill-controls').hidden=type==='guest';}
  function clearData(message=true){revision++;draft=null;reviewed=[];report=null;editable.clear();
    el('bill-file').value='';el('bill-correction-reason').value='';render();
    if(message)status('Cleared from this tab. The server did not save these PDF reviews.');}
  function evidenceNode(sources){
    const details=document.createElement('details');details.className='bill-evidence';
    details.open=!!sources?.length;
    details.append(text('summary',sources?.length?`Source evidence · ${sources.length}`:'No source text found'));
    for(const source of sources||[]){const line=text('p',`Page ${source.page} · ${source.method.replaceAll('_',' ')} · ${source.text}`);
      details.append(line);}return details;
  }
  function fieldNode(path,record,title){
    const wrapper=document.createElement('div');wrapper.className='bill-field';
    const heading=document.createElement('label');heading.append(text('span',title));
    const name=path.split('.').at(-1), input=document.createElement('input');
    input.dataset.billPath=path;input.type=BILL_DATES.has(name)?'date':BILL_NUMERIC.has(name)?'number':'text';
    if(input.type==='number')input.step='any';input.value=record.value==null?'':String(record.value);
    input.setAttribute('aria-label',title);heading.append(input);wrapper.append(heading);
    wrapper.append(text('span',record.status||'observed',`bill-field-status ${record.status||'observed'}`));
    if(record.unit)wrapper.append(text('span',` · ${record.unit}`,'hint'));
    if(record.alternatives?.length)wrapper.append(text('p',`Ambiguous alternatives: ${record.alternatives.join(' / ')}`,'hint'));
    wrapper.append(evidenceNode(record.evidence));editable.set(path,{input,original:record.value});return wrapper;
  }
  function renderIssues(){const list=el('bill-issues');list.replaceChildren();
    if(!draft?.issues?.length){list.append(text('li','No validation issues found. Verify the PDF before approval.'));return;}
    for(const issue of draft.issues)list.append(text('li',`${issue.severity.toUpperCase()} · ${issue.message}${issue.path?' ('+issue.path+')':''}`,`bill-issue ${issue.severity}`));
  }
  function renderDraft(){
    el('bill-draft').hidden=!draft;editable.clear();if(!draft)return;
    const methods=draft.pages.map(page=>`Page ${page.page}: ${page.method.replaceAll('_',' ')}`);
    el('bill-pages').textContent=`PDF review · ${methods.join('; ')}. ${draft.interval_summary?'A full attached interval CSV was validated against printed totals.':'No complete attached interval CSV has been validated.'}`;
    const fields=el('bill-fields');fields.replaceChildren(text('h4','Bill-wide observations'));
    for(const [name,record] of Object.entries(draft.fields))fields.append(fieldNode(`fields.${name}`,record,label(name)));
    const services=el('bill-services');services.replaceChildren();
    if(!draft.services.length)services.append(text('p','No supported itemized service section was found. Required bill-wide fields can still be corrected; charge composition may remain unavailable.','hint'));
    draft.services.forEach((service,index)=>{
      const section=document.createElement('section');section.className='bill-service';
      section.append(text('h4',`${service.role} section ${index+1}`));
      section.append(fieldNode(`services.${index}.provider`,{value:service.provider,status:'extracted',evidence:[]},'Provider name'));
      for(const [name,record] of Object.entries(service.fields))
        section.append(fieldNode(`services.${index}.fields.${name}`,record,label(name)));
      if(service.line_items?.length)section.append(text('h5','Itemized charges'));
      (service.line_items||[]).forEach((row,item)=>{
        const block=document.createElement('div');block.className='bill-line-item';
        block.append(text('strong',`Charge ${item+1}`));
        for(const name of ['description','kind','quantity_kwh','amount'])if(Object.hasOwn(row,name))
          block.append(fieldNode(`services.${index}.line_items.${item}.${name}`,
            {value:row[name],status:'extracted',evidence:row.evidence||[]},label(name)));
        section.append(block);
      });services.append(section);
    });renderIssues();
  }
  function renderReviewed(){
    const box=el('bill-reviewed'),list=el('bill-list');box.hidden=!reviewed.length;list.replaceChildren();
    reviewed.forEach((item,index)=>{
      const row=document.createElement('div');row.className='bill-reviewed-row';
      row.append(text('span',`${item.fields.period_start.value} to ${item.fields.period_end.value} · ${item.fields.meter_import_kwh.value} kWh`));
      const remove=text('button','Remove');remove.type='button';remove.className='secondary';
      remove.addEventListener('click',()=>{reviewed.splice(index,1);if(draft?.source_sha256===item.source_sha256)draft={...draft,approved:false};
        report=null;render();status('Removed this reviewed bill from the tab.');});row.append(remove);list.append(row);
    });el('bill-step-status').textContent=reviewed.length?`${reviewed.length} approved bill${reviewed.length===1?'':'s'} in this tab. No bill values are copied into simulation inputs.`:'No reviewed bills in this tab. You can continue without uploading a bill.';
  }
  function renderReport(){const section=el('bill-report');section.hidden=!report;if(!report)return;
    const table=document.createElement('table'),head=document.createElement('thead'),body=document.createElement('tbody');
    const headers=['Billing period','Meter purchases · kWh','kWh/day','Current electric charges','Charges/day','Printed plan'];
    const hr=document.createElement('tr');for(const name of headers)hr.append(text('th',name));head.append(hr);
    for(const cycle of report.cycles){const row=document.createElement('tr');
      for(const value of [`${cycle.period_start} to ${cycle.period_end}`,cycle.meter_import_kwh,
        cycle.meter_import_kwh_per_day,cycle.current_electric_charges_usd==null?'—':`$${cycle.current_electric_charges_usd.toFixed(2)}`,
        cycle.electric_charges_usd_per_day==null?'—':`$${cycle.electric_charges_usd_per_day.toFixed(2)}`,
        cycle.billing_plan||'Missing'])row.append(text('td',String(value)));body.append(row);}
    table.append(head,body);el('bill-report-table').replaceChildren(table);
    const notes=el('bill-report-notes');notes.replaceChildren(text('h4','What the bills show'));
    for(const finding of report.observed_facts||[])notes.append(text('p',`${finding.basis}: highest ${finding.highest_kwh_per_day} kWh/day, lowest ${finding.lowest_kwh_per_day} kWh/day.`));
    for(const recommendation of report.recommendations||[])notes.append(text('p',`${recommendation.claim_level.replaceAll('_',' ')}: ${recommendation.message}`));
    for(const limitation of report.limitations||[])notes.append(text('p',limitation,'hint'));
  }
  function render(){renderDraft();renderReviewed();renderReport();}
  function corrections(){const changed={},reason=el('bill-correction-reason').value.trim();
    for(const [path,{input,original}] of editable){const value=billCorrectionValue(path,input.value);
      if(value!==original)changed[path]={value,reason};}return changed;}
  async function extract(){if(busy)return;const file=el('bill-file').files?.[0];
    if(!file){error('Choose one PDF first.');return;}const call=++revision;setBusy(true);status(`Extracting ${file.name}…`);
    try{const bytes=new Uint8Array(await file.arrayBuffer());const next=await billExtract(bytes,api);
      if(call!==revision)return;draft=next;report=null;el('bill-correction-reason').value='';render();
      status('Extraction complete. Compare each value and source page with your PDF before approving.');
    }catch(failure){if(call===revision)error(failure.message||String(failure));}
    finally{el('bill-file').value='';setBusy(false);}
  }
  async function review(approve){if(!draft||busy)return;const call=++revision;let edits;
    try{edits=corrections();}catch(failure){error(failure.message);return;}
    setBusy(true);status(approve?'Checking required fields before approval…':'Validating corrections…');
    try{const next=await billReview(draft,edits,false,api);if(call!==revision)return;
      draft=next;render();el('bill-correction-reason').value='';
      const blockers=next.issues.filter(item=>item.severity==='error');
      if(!approve){status(blockers.length?`${blockers.length} required issue${blockers.length===1?'':'s'} remain. Correct them before approval.`:'Corrections validated. Check warnings, then approve when ready.');return;}
      if(blockers.length){status(`${blockers.length} required issue${blockers.length===1?'':'s'} remain. Correct them before approval.`);return;}
      if(reviewed.length>=60&&!reviewed.some(item=>item.source_sha256===draft.source_sha256))throw new Error('Analyze at most 60 reviewed billing cycles. Remove one first.');
      const approved=await billReview(draft,{},true,api);if(call!==revision)return;
      draft=approved;reviewed=reviewed.filter(item=>item.source_sha256!==approved.source_sha256);
      reviewed.push(approved);report=null;render();status('Bill approved for this tab. Upload another PDF or analyze the approved bills.');
    }catch(failure){if(call===revision)error(failure.message||String(failure));}
    finally{setBusy(false);}
  }
  async function analyze(){if(!reviewed.length||busy)return;const call=++revision;setBusy(true);status('Analyzing approved billing cycles…');
    try{const next=await billAnalyze(reviewed,api);if(call!==revision)return;report=next;renderReport();
      status(`Analyzed ${next.cycles.length} approved billing cycle${next.cycles.length===1?'':'s'}.`);
      el('bill-report').scrollIntoView({behavior:'smooth',block:'start'});
    }catch(failure){if(call===revision)error(failure.message||String(failure));}
    finally{setBusy(false);}
  }
  el('open-bills').addEventListener('click',showBills);
  el('step-open-bills').addEventListener('click',showBills);
  el('bill-back').addEventListener('click',showStudy);
  el('bill-clear').addEventListener('click',()=>clearData());
  el('bill-extract').addEventListener('click',extract);
  el('bill-review').addEventListener('click',()=>review(false));
  el('bill-approve').addEventListener('click',()=>review(true));
  el('bill-analyze').addEventListener('click',analyze);
  el('bill-draft').addEventListener('input',event=>{
    if(!event.target.dataset.billPath||!draft?.approved)return;
    reviewed=reviewed.filter(item=>item.source_sha256!==draft.source_sha256);
    draft={...draft,approved:false};report=null;renderReviewed();renderReport();
    status('Edits are pending. Validate and approve this bill again.');
  });
  window.addEventListener('pagehide',()=>clearData(false));
  window.billUI={setAccount,clear:clearData};
})();
