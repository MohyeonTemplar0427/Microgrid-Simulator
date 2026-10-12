"use strict";
function buildPjmRequest(defaults, values, weather, marketCsv) {
  const r=JSON.parse(JSON.stringify(defaults));
  r.start_date=values.start_date;r.end_date=values.end_date;
  r.site={latitude:Number(values.latitude),longitude:Number(values.longitude),label:"Henrico commercial study"};
  for(const key of ["distribution_utility","state_jurisdiction","retail_supplier","customer_class","tariff","transmission_zone"])r.regional_account[key]=values[key];
  r.regional_account.utility_verification={kind:values.verification_kind,reference:values.verification_reference};
  r.account.eligibility_confirmed=values.account_confirmed===true;
  r.account.history_peaks_kw=values.history_peaks.split(",").map(x=>Number(x.trim()));
  for(const key of ["contract_demand_kw","power_factor","billing_month"])r.account[key]=Number(values[key]);
  r.load.scale=Number(values.load_scale);
  for(const key of Object.keys(r.solar))r.solar[key]=Number(values[key]);
  for(const key of Object.keys(r.battery))r.battery[key]=Number(values[key]);
  r.weather=weather;r.include_degradation_in_optimization=values.include_wear===true;
  r.degradation_cost_per_kWh=Number(values.degradation_cost_per_kWh);
  if(marketCsv!==null && marketCsv!==undefined){
    r.regional_account.wholesale_pricing_location={pnode_id:values.pnode_id,pnode_name:values.pnode_name,zone:values.transmission_zone,source:values.pnode_source};
    r.market_data={csv:marketCsv,metadata:{market:values.market,source_url:values.source_url,retrieved_at:values.retrieved_at,unit:"$/MWh",usage_permission:"internal_use_only"}};
  }
  return r;
}
if(typeof module!=="undefined")module.exports={buildPjmRequest};
if(typeof document!=="undefined"){
  const $=id=>document.getElementById(id), form=$("pjm-form"), field=name=>form.elements.namedItem(name);
  let caps,weather=null,studyId=null,timer=null;
  function values(){const out=Object.fromEntries(new FormData(form));for(const k of ["account_confirmed","include_wear"])out[k]=field(k).checked;return out;}
  async function api(path,body){const response=await fetch(path,{method:body===undefined?"GET":"POST",headers:{"Content-Type":"application/json","X-Study-Token":caps?.token||""},...(body===undefined?{}:{body:JSON.stringify(body)})});const out=await response.json();if(!response.ok)throw new Error(out.error||"Request failed");return out;}
  function status(text){$("status").textContent=text;}
  for(const name of ["latitude","longitude","start_date","end_date"])field(name).addEventListener("change",()=>{weather=null;$("weather-status").textContent="Location or dates changed. Retrieve matching weather again.";});
  $("weather").onclick=async()=>{ $("weather").disabled=true;try{const v=values();weather=await api("/api/v1/pjm/weather",{latitude:Number(v.latitude),longitude:Number(v.longitude),start_date:v.start_date,end_date:v.end_date});$("weather-status").textContent="Historical ERA5 weather retrieved. Open-Meteo / Copernicus attribution is retained in results.";}catch(e){weather=null;$("weather-status").textContent=e.message;}finally{$("weather").disabled=false;}};
  async function poll(){try{const study=await api("/api/studies/"+studyId);status(study.status+" · "+(study.progress||""));if(["completed","failed","cancelled"].includes(study.status)){clearInterval(timer);$("run").disabled=false;if(study.status!=="completed"){status(study.error||study.status);return;}$("results").replaceChildren();const table=await api("/api/studies/"+studyId+"/tables/comparison");const el=document.createElement("table"),head=document.createElement("tr");for(const label of table.labels){const th=document.createElement("th");th.textContent=label;head.append(th);}el.append(head);for(const row of table.data){const tr=document.createElement("tr");for(const v of row){const td=document.createElement("td");td.textContent=typeof v==="number"?v.toFixed(2):String(v);tr.append(td);}el.append(tr);}const scroll=document.createElement("div");scroll.className="table-scroll";scroll.append(el);$("results").append(scroll);for(const warning of study.result.warnings){const p=document.createElement("p");p.className="hint";p.textContent=warning;$("results").append(p);}const market=document.createElement("p");market.textContent="Wholesale signal: "+study.result.market_data.status+". Not used for retail billing.";$("results").append(market);$("save").hidden=false;$("all-results").hidden=false;$("all-results").href="/#"+studyId;}}catch(e){clearInterval(timer);$("run").disabled=false;status(e.message);}}
  form.onsubmit=async event=>{event.preventDefault();try{if(!weather)throw new Error("Retrieve historical weather before running.");let csv=null;const file=$("market-file").files[0];if(file){if(file.size>8*1024*1024)throw new Error("PJM CSV exceeds 8 MiB.");csv=await file.text();}const r=buildPjmRequest(caps.pjm_candidate.defaults,values(),weather,csv);$("run").disabled=true;$("save").hidden=true;const study=await api("/api/v1/pjm/studies",r);studyId=study.id;status("Queued · candidate study "+studyId);clearInterval(timer);timer=setInterval(poll,2000);await poll();}catch(e){$("run").disabled=false;status(e.message);}};
  $("save").onclick=async()=>{const name=prompt("Name this study before saving:");if(name===null)return;try{await api("/api/studies/"+studyId+"/save",{name});status("Saved: "+name);}catch(e){status(e.message);}};
  (async()=>{try{caps=await api("/api/capabilities");if(!caps.pjm_candidate||caps.hosting_mode!=="local")throw new Error("PJM is a local candidate. Open its separate validated preview; the stable engine is unchanged.");const d=caps.pjm_candidate.defaults;for(const [k,v] of Object.entries({...d.site,...d.solar,...d.battery,...d.regional_account,...d.account,start_date:d.start_date,end_date:d.end_date,load_scale:d.load.scale,degradation_cost_per_kWh:d.degradation_cost_per_kWh}))if(field(k))field(k).value=v;field("history_peaks").value=d.account.history_peaks_kw.join(", ");field("verification_reference").value=d.regional_account.utility_verification.reference;$("engine").textContent=caps.engine.id.slice(0,12);for(const url of caps.pjm_candidate.source_urls){const li=document.createElement("li"),a=document.createElement("a");a.href=url;a.textContent=url.split("/").pop();a.target="_blank";a.rel="noreferrer";li.append(a);$("sources").append(li);}status("Candidate ready · verified rates "+caps.pjm_candidate.effective_start+" to "+caps.pjm_candidate.effective_end);}catch(e){status(e.message);for(const control of form.elements)control.disabled=true;}})();
}
