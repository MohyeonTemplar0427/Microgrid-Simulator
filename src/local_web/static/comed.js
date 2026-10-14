"use strict";
function buildComedRequest(defaults, values, loadCsv, priceCsv) {
  const r=JSON.parse(JSON.stringify(defaults[values.customer_type]));
  const a=r.account;
  for(const key of ["supply","delivery_class","billing_month"])a[key]=values[key];
  a.ordinary_import_only_confirmed=values.account_confirmed===true;
  r.utility_reference=values.utility_reference;
  if(values.customer_type==="commercial"){
    for(const key of ["service_voltage","watt_hour_eligibility","eligibility_source"])a[key]=values[key];
    for(const key of ["utility_transformer","competitively_declared","electric_space_heat"])a[key]=values[key]==="true";
    for(const key of ["previous_12_month_mkd_kw","previous_12_month_peak_kw","previous_calendar_year_peak_kw","previous_year_months_ge_100kw"])a[key]=values[key]===""?null:Number(values[key]);
  }
  r.load={mode:values.load_mode,kw:values.load_mode==="constant_example"?(values.load_kw===""?null:Number(values.load_kw)):null,csv:loadCsv,source:values.load_source};
  if(values.supply==="BESH"){
    a.capacity_obligation_kw=values.capacity_obligation_kw===""?null:Number(values.capacity_obligation_kw);
    a.capacity_source=values.capacity_source;
    r.prices={mode:values.price_mode,usd_per_mwh:values.price_mode==="constant_example"?(values.price_value===""?null:Number(values.price_value)):null,
      csv:priceCsv,source:values.price_source,basis_confirmed:values.price_confirmed===true};
  }
  return r;
}
if(typeof module!=="undefined")module.exports={buildComedRequest};
if(typeof document!=="undefined"){
  const $=id=>document.getElementById(id),form=$("comed-form"),field=n=>form.elements.namedItem(n);
  let caps,studyId=null,timer=null,running=false;
  const label=value=>value.replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase());
  const labels={watt_hour:"Watt-Hour · verified legacy or EV eligibility",small:"Small Load · ≤100 kW",medium:"Medium Load · >100–400 kW",large:"Large Load · >400–1,000 kW",very_large:"Very Large Load · >1,000–10,000 kW",extra_large:"Extra Large Load · >10,000 kW",high_voltage:"High Voltage · ≥69 kV"};
  function status(text){$("status").textContent=text;}
  async function api(path,body){const res=await fetch(path,{method:body===undefined?"GET":"POST",headers:{"Content-Type":"application/json","X-Study-Token":caps?.token||""},...(body===undefined?{}:{body:JSON.stringify(body)})});const out=await res.json();if(!res.ok)throw new Error(out.error||"Request failed");return out;}
  function visibility(){
    if(caps){
      const months=caps.comed.billing_months_by_supply?.[field("supply").value]||caps.comed.billing_months;
      const previous=field("billing_month").value;
      field("billing_month").replaceChildren(new Option("Choose verified billing month…",""),...months.map(m=>new Option(m.slice(0,7),m)));
      field("billing_month").value=months.includes(previous)?previous:"";
      $("coverage").textContent="Verified "+field("supply").value+" billing months: "+months.map(m=>m.slice(0,7)).join(", ");
    }
    $("commercial-fields").hidden=field("customer_type").value!=="commercial";
    $("hourly-fields").hidden=field("supply").value!=="BESH";
    $("load-file-label").hidden=field("load_mode").value!=="csv";
    $("load-kw-label").hidden=field("load_mode").value!=="constant_example";
    $("price-file-label").hidden=field("price_mode").value!=="csv";
    $("price-value-label").hidden=field("price_mode").value!=="constant_example";
    for(const id of ["commercial-fields","hourly-fields"])for(const el of $(id).querySelectorAll("input,select"))el.disabled=running||$(id).hidden;
  }
  function configureCustomer(){
    const type=field("customer_type").value,d=caps.comed.defaults[type];
    field("delivery_class").replaceChildren(...caps.comed[type+"_classes"].map(value=>new Option(labels[value]||label(value),value)));
    for(const [k,v] of Object.entries(d.account))if(field(k))field(k).value=v===null?"":String(v);
    field("utility_reference").value=d.utility_reference;field("load_kw").value=d.load.kw;
    field("load_source").value=d.load.source;field("account_confirmed").checked=false;
    field("load_mode").value="constant_example";$("load-file").value="";
    field("capacity_obligation_kw").value="2";
    field("capacity_source").value="Synthetic account capacity obligation: 2 kW";
    field("price_confirmed").checked=false;
    visibility();
  }
  function busy(value){running=value;for(const el of form.elements)el.disabled=value;visibility();}
  for(const n of ["supply","load_mode","price_mode"])field(n).addEventListener("change",visibility);
  field("customer_type").addEventListener("change",configureCustomer);
  field("delivery_class").addEventListener("change",()=>{if(field("customer_type").value==="commercial"){
    const d=field("delivery_class").value;
    if(d==="high_voltage")field("service_voltage").value="high_voltage";
    else if(field("service_voltage").value==="high_voltage")field("service_voltage").value="secondary";
    if(d!=="high_voltage")field("previous_12_month_mkd_kw").value="";
    if(d!=="watt_hour")field("watt_hour_eligibility").value="not_applicable";
    field("account_confirmed").checked=false;
  }});
  form.addEventListener("change",()=>{if(studyId&&!running)status("Inputs changed. Calculate again to update the result; the displayed bill belongs to the previous run.");});
  function render(bill,warnings){
    const root=$("results");root.replaceChildren();
    const total=document.createElement("h3");total.textContent=new Intl.NumberFormat("en-US",{style:"currency",currency:"USD"}).format(bill.subtotal_usd)+" · subtotal before excluded taxes and fees";root.append(total);
    const summary=document.createElement("p");summary.textContent=bill.import_kwh.toLocaleString()+" kWh · "+bill.billing_month.slice(0,7)+(bill.billed_mkd_kw===undefined?"":" · billed demand "+bill.billed_mkd_kw.toFixed(2)+" kW; overall peak "+bill.overall_30min_peak_kw.toFixed(2)+" kW");root.append(summary);
    const scroll=document.createElement("div");scroll.className="table-scroll";const table=document.createElement("table"),head=document.createElement("thead"),tr=document.createElement("tr");
    for(const text of ["Charge or credit","Amount ($)"]){const th=document.createElement("th");th.textContent=text;tr.append(th);}head.append(tr);table.append(head);
    const body=document.createElement("tbody");for(const row of bill.lines){const tr=document.createElement("tr");for(const text of [label(row.name),row.amount_usd.toFixed(2)]){const td=document.createElement("td");td.textContent=text;tr.append(td);}body.append(tr);}table.append(body);scroll.append(table);root.append(scroll);
    for(const warning of warnings){const p=document.createElement("p");p.className="hint";p.textContent=warning;root.append(p);}
  }
  async function poll(){try{const study=await api("/api/studies/"+studyId);status(study.status+" · "+(study.progress||""));if(["completed","failed","cancelled"].includes(study.status)){
    clearInterval(timer);busy(false);
    if(study.status!=="completed"){status(study.error||study.status);return;}
    render(study.result.bill,study.result.warnings);$("save").hidden=false;$("all-results").hidden=false;$("all-results").href="/#"+studyId;
  }}catch(error){clearInterval(timer);busy(false);status(error.message);}}
  async function readFile(id){const file=$(id).files[0];if(!file)throw new Error("Select the required CSV file.");if(file.size>2*1024*1024)throw new Error("CSV exceeds 2 MiB.");return file.text();}
  form.onsubmit=async event=>{event.preventDefault();try{
    const values=Object.fromEntries(new FormData(form));values.account_confirmed=field("account_confirmed").checked;values.price_confirmed=field("price_confirmed").checked;
    const loadCsv=values.load_mode==="csv"?await readFile("load-file"):null;
    const priceCsv=values.supply==="BESH"&&values.price_mode==="csv"?await readFile("price-file"):null;
    const request=buildComedRequest(caps.comed.defaults,values,loadCsv,priceCsv);
    busy(true);$("save").hidden=true;$("all-results").hidden=true;$("results").replaceChildren();
    const study=await api("/api/v1/comed/studies",request);studyId=study.id;status("Queued · ComEd billing study");clearInterval(timer);timer=setInterval(poll,1000);await poll();
  }catch(error){busy(false);status(error.message);}};
  $("save").onclick=async()=>{const name=prompt("Name this bill study:");if(name===null)return;try{await api("/api/studies/"+studyId+"/save",{name});status("Saved: "+name);}catch(error){status(error.message);}};
  (async()=>{try{caps=await api("/api/capabilities");if(!caps.comed||caps.hosting_mode!=="local")throw new Error("This engine does not offer local ComEd billing. Open the updated development browser.");configureCustomer();$("engine").textContent=caps.engine.id.slice(0,12);$("source").href=caps.comed.source_url;$("run").disabled=false;status("Ready · select a verified month for this supply plan. Example inputs are explicitly synthetic.");}catch(error){status(error.message);busy(true);}})();
}
