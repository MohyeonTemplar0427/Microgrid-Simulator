"use strict";
const $ = (id) => document.getElementById(id);
const form = $("study-form");
const names = {no_battery:"No battery", rule_based:"Rule based", cost_optimal:"Cost optimal", carbon_optimal:"Carbon optimal", combined_optimal:"Combined optimal"};
let capabilities, selectedDatasetId, datasets = [], activeStudy = null, activeId = null, pollTimer, offset = 0, tableRequest = 0;
const PAGE_SIZE = 100;
let essResolution=null, essKey=null, annualResult=null, annualKey=null;
let utilityTimer, strategiesEdited=false;
let template, siteLabel, weatherId = null, weatherMeta = null, locationGeneration = 0;
const field = name => form.elements.namedItem(name);
function weatherRequest() { return {latitude:Number(field("latitude").value),longitude:Number(field("longitude").value),year:Number(field("start_date").value.slice(0,4)),timezone:field("timezone").value,timestep_minutes:Number(field("timestep_minutes").value)}; }
function weatherMatches(meta) { const wanted=weatherRequest(); return meta && Object.keys(wanted).every(k=>meta.request[k]===wanted[k]) && Number(field("end_date").value.slice(0,4))===wanted.year; }
function updateSiteControls() {
  const utility=field("utility").value;
  const service=["cleanpowersf","cec:other:12"].includes(utility)?"cleanpowersf":["hetch_hetchy","cec:distribution:52"].includes(utility)?"hetch_hetchy":utility;
  for(const opt of field("tariff_id").options) {
    if(!opt.value || opt.value==="__unset__") continue;
    opt.hidden=template?.schema_version>=2 && (opt.value.startsWith("hetch_hetchy_")?"hetch_hetchy":opt.value.startsWith("cleanpowersf_")?"cleanpowersf":"pge")!==service;
    opt.disabled=opt.hidden;
  }

  updateCandidateControls();
  const site=template?.schema_version>=2;
  for (const node of document.querySelectorAll("[data-site]")) { node.hidden=!site; for(const input of node.querySelectorAll("input,select,button")) input.disabled=!site; }
  $("legacy-note").hidden=site;
  $("clear-sky-settings").hidden=field("weather_source").value!=="clear_sky";
  $("historical-settings").hidden=field("weather_source").value!=="nsrdb";
  $("archetype-label").hidden=field("load_mode").value!=="synthetic";
  $("fixed-price-label").hidden=!!field("tariff_id").value;
  field("tariff_id").querySelector('option[value=""]').textContent=site?"Flat energy-price assumption · no utility bill":"Profile energy prices · no utility bill";
  $("pv-note").textContent=site?"AC rating limits the weather-derived output. Temperature and inverter losses are calculated separately from system losses.":"PV AC capacity sets the inverter rating; generation uses the saved profile.";
  $("price-note").textContent=field("tariff_id").value.startsWith("hetch_hetchy_")?"Hetch Hetchy retail C-1: confirm an eligible small-commercial account below 75 kW and Premium enrollment if selected. Generation and delivery are included. FY2026–27 rates; calendar-month billing with partial-month cost allocation, not an actual meter-cycle bill. Taxes, discounts and export settlements are excluded.":field("tariff_id").value.startsWith("cleanpowersf_")?"CleanPowerSF B-1 + PG&E delivery. Choose the phase, Green/SuperGreen product, and PCIA vintage shown on your bill (not the simulation year). Non-exempt commercial accounts only. Verified March 1–September 16, 2026; taxes, discounts, standby and NEM/NBT settlements excluded.":site?"A selected tariff supplies both dispatch energy prices and billing. Its effective dates must cover the study. Confirm your account first.":"Dispatch uses saved profile prices; the selected tariff applies to billing.";
  if (site) $("dataset-info").textContent="Location studies generate solar and load inputs from the settings below.";
  if(weatherMeta && !weatherMatches(weatherMeta)) { weatherId=null; weatherMeta=null; }
  $("weather-status").textContent=field("weather_source").value==="nsrdb" ? (weatherId?"Historical weather ready. A copy will be saved with the study.":"Retrieve matching historical weather before running."):"Clear-sky estimates are calculated locally when the simulation runs.";
}
$("new-site").addEventListener("click",()=>startBlankStudy());
$("search-location").addEventListener("click",async()=>{
  const generation=++locationGeneration, query=field("location_query").value;
  $("search-location").disabled=true; $("location-status").textContent="Finding location…";
  try {
    const match=await api("/api/location",{query});
    if(generation!==locationGeneration) { $("location-status").textContent="Location settings changed during lookup. Search again to apply a match."; return; }
    siteLabel=match.display_name; field("latitude").value=match.latitude; field("longitude").value=match.longitude;
    resetUtilityOptions(); field("tariff_id").value="";
    if(match.suggestion.timezone) field("timezone").value=match.suggestion.timezone;
    $("location-status").textContent=match.display_name;
    refreshUtilities(generation);
    updateSiteControls();
  }catch(error){$("location-status").textContent=error.message;}
  finally{$("search-location").disabled=false;}
});
$("retrieve-weather").addEventListener("click",async()=>{
  $("retrieve-weather").disabled=true; $("weather-status").textContent="Retrieving weather… This can take a few minutes.";
  try {
    const request=weatherRequest();
    if(Number(field("end_date").value.slice(0,4))!==request.year) throw new Error("Use dates within one historical year.");
    const metadata=await api("/api/weather",request);
    if(!weatherMatches(metadata)) throw new Error("Settings changed during retrieval. Retrieve weather for the current settings.");
    weatherId=metadata.id; weatherMeta=metadata; updateSiteControls();
    $("weather-status").textContent=`${metadata.cached?"Cached":"Retrieved"} historical weather ready · ${metadata.row_count.toLocaleString()} intervals for ${metadata.request.year}.`;
  }catch(error){$("weather-status").textContent=error.message;}
  finally{$("retrieve-weather").disabled=false;}
});
form.addEventListener("input",event=>{
  if(["latitude","longitude","location_query"].includes(event.target.name)) {
    locationGeneration++;
    if(event.target.name!=="location_query") {
      siteLabel=`Coordinates ${field("latitude").value}, ${field("longitude").value}`;
      $("location-status").textContent=siteLabel; $("utility-suggestion").textContent="Coordinates changed. Confirm the timezone and electricity service.";
      resetUtilityOptions(); field("tariff_id").value="";
      clearTimeout(utilityTimer); utilityTimer=setTimeout(()=>refreshUtilities(locationGeneration),600);
    }
  }
  updateSiteControls();
});

async function api(path, body) {
  const options = body === undefined ? {} : {method:"POST", headers:{"Content-Type":"application/json", "X-Study-Token":capabilities.token}, body:JSON.stringify(body)};
  const response = await fetch(path, options);
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || `Request failed (${response.status})`);
  return result;
}
function showError(id, error) { $(id).textContent = error.message || String(error); $(id).hidden = false; }
function badge(status) { const span=document.createElement("span"); span.className=`status ${status}`; span.textContent=status; return span; }
function option(value, label) { const node=document.createElement("option"); node.value=value; node.textContent=label; return node; }

function fillForm(request, lookup=true) {
  strategiesEdited=true;
  locationGeneration++;
  clearTimeout(utilityTimer);
  resetUtilityOptions(request.site?.utility);
  template=structuredClone(request);
  selectedDatasetId=request.dataset_id;
  weatherId=request.weather_id || null;
  weatherMeta=request.schema_version>=2 && weatherId?{request:{latitude:request.site.latitude,longitude:request.site.longitude,year:Number(request.start_date.slice(0,4)),timezone:request.timezone,timestep_minutes:request.timestep_minutes}}:null;
  if(request.schema_version>=2) {
    siteLabel=request.site.label;
    field("location_query").value=siteLabel; field("latitude").value=request.site.latitude; field("longitude").value=request.site.longitude; field("utility").value=request.site.utility;
    for(const [key,value] of Object.entries(request.solar)) field(key).value=value;
    field("load_mode").value=request.load.mode; field("load_power_kw").value=request.load.power_kw; field("archetype").value=request.load.archetype;
    $("location-status").textContent=siteLabel;
    $("utility-suggestion").textContent="Utility service depends on your account. Search the location for an available locality hint; confirm bundled service before choosing a tariff.";
  }
  for (const [key,value] of Object.entries(request)) {
    if (form.elements.namedItem(key) && key !== "strategies") form.elements.namedItem(key).value = value ?? "";
  }
  for (const [key,value] of Object.entries(request.battery)) form.elements.namedItem(key).value=value;
  for (const box of $("strategies").querySelectorAll("input")) box.checked=request.strategies.includes(box.value);
  restoreCandidate(request);
  updateDatasetInfo(); updateSiteControls();
  resetWizard();
  if(lookup && request.schema_version>=2) refreshUtilities(locationGeneration,request.site.utility);
}
function updateDatasetInfo() {
  const dataset=datasets.find(d=>d.id===selectedDatasetId);
  const source=selectedDatasetId===capabilities.defaults.dataset_id ? "Built-in sample profiles" : `Saved study profiles (${dataset?.name || "original dataset"})`;
  $("dataset-info").textContent=dataset ? `${source} · ${dataset.start.slice(0,10)} to ${dataset.end.slice(0,10)} · ${dataset.timestep_minutes}-minute intervals.` : source;
}
async function loadDatasets() {
  datasets=await api("/api/datasets");
}

function readRequest() {
  const request=structuredClone(template);
  if(request.schema_version===1) request.dataset_id=selectedDatasetId;
  for (const key of ["name","start_date","end_date","timezone"]) request[key]=form.elements.namedItem(key).value;
  for (const key of ["timestep_minutes","carbon_weight","degradation_cost_per_kWh","pv_capacity_kw"]) request[key]=Number(form.elements.namedItem(key).value);
  request.tariff_id=form.elements.tariff_id.value || null;
  request.strategies=[...$("strategies").querySelectorAll("input:checked")].map(box=>box.value);
  for (const key of Object.keys(request.battery)) request.battery[key]=Number(form.elements.namedItem(key).value);
  if(request.schema_version>=2) {
    request.site={label:siteLabel,latitude:Number(field("latitude").value),longitude:Number(field("longitude").value),utility:field("utility").value};
    request.weather_source=field("weather_source").value; request.weather_id=request.weather_source==="nsrdb"?weatherId:null;
    for(const key of Object.keys(request.solar)) request.solar[key]=request.weather_source==="nsrdb" && ["temperature_c","wind_speed_m_per_s"].includes(key)?template.solar[key]:Number(field(key).value);
    request.load={mode:field("load_mode").value,power_kw:Number(field("load_power_kw").value),archetype:field("load_mode").value==="constant"?template.load.archetype:field("archetype").value};
    for(const key of ["fixed_price_per_kWh","carbon_intensity_g_per_kWh"]) request[key]=Number(field(key).value);
  }
  if(request.schema_version===3) {
    if(field("ess_mode").value==="equipment" && !essResolution?.ready) throw new Error("Review and apply the equipment settings first.");
    request.ess=field("ess_mode").value==="equipment"?essResolution:null;
    request.solar_optimization=annualResult;
  }
  return request;
}
form.addEventListener("submit",async event=>{
  event.preventDefault();
  if(wizardIndex < wizardPages().length-1) { advanceWizard(); return; }
  if(!validateWizard()) return;
  $("form-error").hidden=true; $("run-button").disabled=true;
  try { const study=await api("/api/studies",readRequest()); await selectStudy(study.id); await history(); }
  catch(error) { showError("form-error",error); }
  finally { $("run-button").disabled=false; }
});

async function history() {
  const studies=await api("/api/studies");
  if (!studies.length) return;
  $("history").replaceChildren(...studies.map(study=>{
    const row=document.createElement("button"); row.type="button"; row.className=`history-row ${study.id===activeId?"selected":""}`;
    const info=document.createElement("span"), name=document.createElement("strong"), date=document.createElement("small");
    name.textContent=study.name; date.textContent=new Date(study.created_at).toLocaleString();
    info.append(name,date); row.append(info,badge(study.status));
    row.addEventListener("click",()=>selectStudy(study.id).catch(error=>showError("connection",error))); return row;
  }));
}
async function selectStudy(id) {
  clearTimeout(pollTimer); activeId=id; activeStudy=null; offset=0; tableRequest++;
  window.location.hash=id;
  $("empty-state").hidden=true; $("study-output").hidden=false;
  $("results-content").hidden=true; $("run-error").hidden=true; $("manifest-download").hidden=true;
  $("progress").textContent="Loading study…";
  $("results-title").scrollIntoView({behavior:"smooth",block:"start"});
  await refreshStudy(id);
}
async function refreshStudy(id) {
  try {
    const study=await api(`/api/studies/${id}`); if (id!==activeId) return;
    activeStudy=study; $("connection").hidden=true;
    $("run-name").textContent=study.name;
    $("run-meta").textContent=`${study.request.start_date} → ${study.request.end_date} · ${study.request.timezone} · ${study.request.timestep_minutes} min · Engine ${study.engine_id.slice(0,12)}`;
    $("status-badge").textContent=study.status; $("status-badge").className=`status ${study.status}`;
    $("progress").textContent=study.status==="completed" ? "Calculation complete. Inspect AC validation for electrical feasibility." : study.progress;
    $("request-download").href=`/api/studies/${id}/request.json`;
    if (study.status==="failed") { showError("run-error",study.error); await history(); }
    else if (study.status==="completed") {
      $("manifest-download").hidden=false; $("manifest-download").href=`/api/studies/${id}/result.json`;
      $("results-content").hidden=false;
      $("table-select").replaceChildren(...study.result.tables.map(t=>option(t.id,t.label)));
      $("warning-list").replaceChildren(...study.result.warnings.map(w=>{const li=document.createElement("li");li.textContent=w;return li;}));
      await loadTable(); await history();
    } else pollTimer=setTimeout(()=>refreshStudy(id),1200);
  } catch(error) {
    if (id!==activeId) return;
    showError("connection",new Error(`Cannot reach the study service: ${error.message} Keep the local server running. Retrying…`));
    pollTimer=setTimeout(()=>refreshStudy(id),3000);
  }
}
const summaryColumns=["scenario","total_explicit_cost","energy_cost","demand_charge","emissions_kgCO2","peak_grid_import_kw","minimum_voltage_pu","feasible_intervals","interval_count"];
async function loadTable() {
  const generation=++tableRequest, id=activeId, selected=$("table-select").value;
  $("table-container").textContent="Loading table…";
  $("csv-download").hidden=true;
  $("previous").disabled=true; $("next").disabled=true;
  const table=await api(`/api/studies/${id}/tables/${selected}?offset=${offset}&limit=${PAGE_SIZE}`);
  if (generation!==tableRequest || id!==activeId) return;
  $("run-error").hidden=true;
  $("all-columns").parentElement.hidden=selected!=="comparison";
  const priority=selected==="comparison" ? summaryColumns : selected.startsWith("ac-") ? ["timestamp","feasible","converged","minimum_voltage_pu","maximum_voltage_pu","setpoint_mismatch","inverter_capability_violation"] : ["timestamp"];
  const order=[...priority.filter(c=>table.columns.includes(c)),...table.columns.filter(c=>!priority.includes(c))];
  const indices=order.filter(c=>selected!=="comparison" || $("all-columns").checked || summaryColumns.includes(c)).map(c=>table.columns.indexOf(c));
  const element=document.createElement("table"), head=document.createElement("thead"), body=document.createElement("tbody"), header=document.createElement("tr");
  for (const i of indices) {const cell=document.createElement("th");cell.scope="col";cell.textContent=table.columns[i]==="timestamp"?"Time (UTC)":table.labels[i];cell.title=table.columns[i];header.append(cell);}
  head.append(header);
  for (const row of table.data) {
    const tr=document.createElement("tr");
    for (const i of indices) {
      const td=document.createElement("td"), value=row[i];
      const text=typeof value==="string" && value.startsWith("combined_optimal_") ? `Combined · $${value.slice("combined_optimal_".length)}/kgCO₂` : (names[value] || String(value));
      td.textContent=value===null ? "—" : typeof value==="number" ? value.toLocaleString(undefined,{maximumFractionDigits:4}) : typeof value==="boolean" ? (value?"Yes":"No") : text;
      tr.append(td);
    }
    body.append(tr);
  }
  element.append(head,body); $("table-container").replaceChildren(element); $("table-container").scrollTop=0;
  $("csv-download").href=`/api/studies/${id}/tables/${selected}.csv`;
  $("csv-download").hidden=false;
  $("row-count").textContent=`${table.total?offset+1:0}–${offset+table.data.length} of ${table.total.toLocaleString()} rows · Full precision in CSV`;
  $("previous").disabled=offset===0; $("next").disabled=offset+PAGE_SIZE>=table.total;
}
function tableAction(action) { return ()=>{action();loadTable().catch(error=>showError("run-error",error));}; }
$("table-select").addEventListener("change",tableAction(()=>{offset=0;}));
$("all-columns").addEventListener("change",tableAction(()=>{}));
$("previous").addEventListener("click",tableAction(()=>{offset=Math.max(0,offset-PAGE_SIZE);}));
$("next").addEventListener("click",tableAction(()=>{offset+=PAGE_SIZE;}));
$("reuse").addEventListener("click",()=>{if(activeStudy){fillForm(activeStudy.request);$("configure-title").scrollIntoView({behavior:"smooth"});}});
$("refresh-history").addEventListener("click",()=>history().catch(error=>showError("connection",error)));

function essSelection() {
  const overrides={};
  for(const [input,key] of [["ess_charge_override","max_charge_kw"],["ess_discharge_override","max_discharge_kw"]]) if(field(input).value!=="") overrides[key]=Number(field(input).value);
  return {equipment_id:field("equipment_id").value,quantity:Number(field("ess_quantity").value),initial_soc:Number(field("ess_initial").value),backup_reserve:Number(field("ess_reserve").value),capacity_basis:field("ess_basis").value || null,efficiency_approximation:field("ess_efficiency").checked,overrides};
}
function orientationKey() {
  return JSON.stringify(["latitude","longitude","timezone","orientation_year","pv_capacity_kw","dc_capacity_kw","tilt_degrees","azimuth_degrees","system_losses_fraction","inverter_efficiency"].map(k=>field(k).value));
}
function updateCandidateControls() {
  const enabled=!!capabilities?.candidate_defaults && template?.schema_version===3;
  $("ess-controls").hidden=!enabled; $("orientation-controls").hidden=!enabled;
  const equipment=enabled && field("ess_mode").value==="equipment";
  $("ess-selection").hidden=!equipment;
  if(essResolution && essKey!==JSON.stringify(essSelection())) {essResolution=null; $("ess-review").textContent="Settings changed. Review & apply again.";}
  if(annualResult && annualKey!==orientationKey()) {annualResult=null; $("orientation-status").textContent="PV or location settings changed. Optimize again, or keep these manual angles.";}
  for(const key of Object.keys(capabilities?.defaults?.battery || {})) field(key).readOnly=equipment;
  field("SOC_min").min=enabled?"0":"0.001";
}
function showEssFacts(entry) {
  $("ess-facts").replaceChildren();
  if(!entry) return;
  for(const [key,fact] of Object.entries(entry.fields)) {
    const p=document.createElement("p"); p.textContent=`${key.replaceAll("_"," ")}: ${fact.value===null?"Unresolved":Array.isArray(fact.value)?fact.value.join(" / "):fact.value} · ${fact.status}. `;
    const a=document.createElement("a");a.textContent=`${fact.document_revision}, ${fact.section}`;a.href=fact.source_url;a.target="_blank";a.rel="noreferrer";p.append(a);$("ess-facts").append(p);
  }
  const note=document.createElement("p");note.textContent=entry.unresolved.join(" ");$("ess-facts").append(note);
}
function restoreCandidate(request) {
  essResolution=request.ess || null; annualResult=request.solar_optimization || null;
  field("ess_mode").value=essResolution?"equipment":"manual";
  if(essResolution) {
    const v=essResolution.selection;
    field("equipment_id").value=v.equipment_id;field("ess_quantity").value=v.quantity;field("ess_initial").value=v.initial_soc;field("ess_reserve").value=v.backup_reserve;field("ess_basis").value=v.capacity_basis || "";field("ess_efficiency").checked=v.efficiency_approximation;
    field("ess_charge_override").value=v.overrides.max_charge_kw ?? "";field("ess_discharge_override").value=v.overrides.max_discharge_kw ?? "";
    $("ess-review").textContent=`Saved catalog ${essResolution.catalog_revision}. ${essResolution.assumptions.join(" ")}`;
    showEssFacts(essResolution.equipment);
  } else $("ess-review").textContent="Choose equipment and review its assumptions before running.";
  if(annualResult) field("orientation_year").value=annualResult.year;
  essKey=JSON.stringify(essSelection());annualKey=orientationKey();
  $("orientation-status").textContent=annualResult?`Saved ${annualResult.year} optimum: ${annualResult.tilt_degrees}° tilt, ${annualResult.azimuth_degrees}° azimuth, ${annualResult.energy_kwh.toFixed(1)} kWh/year.`:"";
}
field("equipment_id").addEventListener("change",()=>showEssFacts(capabilities.ess_catalog.find(e=>e.id===field("equipment_id").value)));
$("resolve-ess").addEventListener("click",async()=>{
  $("resolve-ess").disabled=true; const selection=essSelection(), key=JSON.stringify(selection);
  try {
    const resolved=await api("/api/ess/resolve",selection);
    if(key!==JSON.stringify(essSelection())) throw new Error("Selection changed while resolving. Review again.");
    essResolution=resolved;essKey=key;showEssFacts(resolved.equipment);
    if(!resolved.ready) {$("ess-review").textContent=resolved.requirements.join(" ");return;}
    for(const [name,value] of Object.entries(resolved.battery)) field(name).value=value;
    $("ess-review").textContent=`Applied catalog ${resolved.catalog_revision} · ${resolved.usable_ac_energy_kwh.toFixed(2)} kWh usable AC · ${resolved.dispatchable_ac_energy_kwh.toFixed(2)} kWh above reserve. ${resolved.assumptions.join(" ")}`;
  }catch(error){essResolution=null;$("ess-review").textContent=error.message;}
  finally{$("resolve-ess").disabled=false;}
});
$("optimize-orientation").addEventListener("click",async()=>{
  $("optimize-orientation").disabled=true; const key=orientationKey();
  try {
    const required=["latitude","longitude","timezone","orientation_year","pv_capacity_kw","dc_capacity_kw","tilt_degrees","azimuth_degrees","system_losses_fraction","inverter_efficiency"];
    if(required.some(name=>field(name).value==="")) throw new Error("Set the location, time range, PV and inverter values first, then return here to optimize orientation.");
    const study=readRequest();study.weather_source="clear_sky";study.weather_id=null;
    $("orientation-status").textContent="Retrieving the full historical year…";
    const weather=await api("/api/weather",{latitude:study.site.latitude,longitude:study.site.longitude,year:Number(field("orientation_year").value),timezone:study.timezone,timestep_minutes:60});
    $("orientation-status").textContent="Comparing 32,760 integer orientations locally…";
    const result=await api("/api/solar/optimize",{study,weather_id:weather.id});
    if(key!==orientationKey()) throw new Error("Settings changed during optimization. Result was not applied; try again.");
    field("tilt_degrees").value=result.tilt_degrees;field("azimuth_degrees").value=result.azimuth_degrees;
    annualResult=result;annualKey=orientationKey();
    $("orientation-status").textContent=`${result.year}: ${result.tilt_degrees}° tilt, ${result.azimuth_degrees}° azimuth · ${result.energy_kwh.toFixed(1)} kWh/year (${(result.energy_kwh-result.original_energy_kwh).toFixed(1)} kWh above previous angles). Best for this historical year under the model assumptions.`;
  }catch(error){$("orientation-status").textContent=error.message;}
  finally{$("optimize-orientation").disabled=false;}
});

let wizardIndex=0, wizardReached=0;

async function initialize() {
  try {
    capabilities=await api("/api/capabilities");
    for(const entry of capabilities.ess_catalog || []) field("equipment_id").append(option(entry.id,`${entry.manufacturer} · ${entry.model}`));
    for(const year of [...(capabilities.nsrdb_years || [])].reverse()) field("orientation_year").append(option(year,String(year)));
    showEssFacts(capabilities.ess_catalog?.[0]);
    for (const tariff of capabilities.tariffs) form.elements.tariff_id.append(option(tariff.id,`${tariff.label} · from ${tariff.effective_start || "catalog date"}${tariff.effective_end ? " to "+tariff.effective_end : ""}`));
    for (const name of capabilities.strategies) {
      const label=document.createElement("label"), box=document.createElement("input");
      label.className="checkbox"; box.type="checkbox"; box.value=name; box.disabled=name==="no_battery";
      label.append(box,document.createTextNode(names[name] || name)); $("strategies").append(label);
    }
    await loadDatasets(); startBlankStudy(); await history();
    $("engine-info").textContent=`Engine ${capabilities.engine.id.slice(0,12)} · Local development snapshot · Studies saved on this computer`;
    $("credentials-note").textContent=capabilities.nsrdb_configured?"NSRDB credentials are configured on the local server. Retrieval contacts NSRDB.":"Historical retrieval needs NSRDB credentials. Start the server with --env-file pointing to your existing src/.env.";
    $("run-button").disabled=false;
    const id=window.location.hash.slice(1); if (/^[0-9a-f]{32}$/.test(id)) await selectStudy(id);
  } catch(error) {showError("connection",error);}
}
initialize();


async function refreshPipeline() {
  try {
    const health = await api("/api/health");
    $("pipeline-status").textContent = health.worker === "connected"
      ? `Simulation service connected · ${health.running} running · ${health.queued} queued`
      : `Simulation worker offline · ${health.queued} queued. Submitted studies are saved and will run when the worker starts.`;
  } catch (_) {
    $("pipeline-status").textContent = "Simulation service disconnected. Reconnecting…";
  } finally {
    setTimeout(refreshPipeline, 5000);
  }
}
refreshPipeline();


function resetUtilityOptions(saved="unconfirmed") {
  field("utility").replaceChildren(option("unconfirmed","Choose your electricity service"),
    option("pge","PG&E bundled service · manual confirmation"), option("cleanpowersf","CleanPowerSF + PG&E delivery · confirm account"), option("hetch_hetchy","Hetch Hetchy Power · confirm eligible account"), option("other","Other / CCA service · manual"));
  if(saved.startsWith("cec:")) field("utility").append(option(saved,`Saved provider (${saved})`));
  field("utility").value=saved;
}
async function refreshUtilities(generation, saved="unconfirmed") {
  const latitude=field("latitude"), longitude=field("longitude");
  if(!latitude.value || !longitude.value || !latitude.checkValidity() || !longitude.checkValidity()) return;
  $("utility-suggestion").textContent="Matching utility service territories…";
  try {
    const result=await api("/api/utilities",{latitude:Number(latitude.value),longitude:Number(longitude.value)});
    if(generation!==locationGeneration) return;
    // Preserve an explicit account choice made while the lookup was in flight.
    const chosen=field("utility").value || saved;
    const options=[option("unconfirmed","Choose your electricity service")];
    for(const item of result.candidates) options.push(option(item.id,
      item.id==="pge"?`${item.name} · confirm bundled service`:item.id==="cec:other:12"?"CleanPowerSF + PG&E delivery · B-1 supported":item.id==="cec:distribution:52"?"Hetch Hetchy Power · C-1 supported; confirm eligibility":`${item.name} · ${item.type} · tariff not yet modeled`));
    if(!result.candidates.some(x=>x.id==="pge")) options.push(option("pge","PG&E bundled service · manual override"));
    if(chosen==="cleanpowersf" || !result.candidates.some(x=>x.id==="cec:other:12")) options.push(option("cleanpowersf","CleanPowerSF + PG&E delivery · confirm account"));
    if(chosen==="hetch_hetchy" || !result.candidates.some(x=>x.id==="cec:distribution:52")) options.push(option("hetch_hetchy","Hetch Hetchy Power · confirm eligible account"));
    options.push(option("other","Other / CCA service · manual"));
    if(chosen.startsWith("cec:") && !result.candidates.some(x=>x.id===chosen)) options.push(option(chosen,`Saved provider (${chosen}) · not in current matches`));
    field("utility").replaceChildren(...options); field("utility").value=chosen;
    $("utility-suggestion").textContent=result.message;
  } catch(error) {
    if(generation===locationGeneration) $("utility-suggestion").textContent="Utility lookup unavailable. Select your service manually.";
  }
}
field("utility").addEventListener("change",()=>{
  field("tariff_id").value="__unset__";
  updateSiteControls();
});


function wizardPages() {
  return [...document.querySelectorAll(".wizard-page")].filter(page=>
    template?.schema_version>=2 || !page.querySelector(":scope > fieldset[data-site]"));
}
function resetWizard() { wizardIndex=0; wizardReached=0; renderWizard(); }
function renderWizard(focus=false) {
  const pages=wizardPages();
  for(const page of document.querySelectorAll(".wizard-page")) page.hidden=page!==pages[wizardIndex];
  const review=wizardIndex===pages.length-1;
  $("step-progress").textContent=review ? "Review your study before running" : `Step ${wizardIndex+1} of ${pages.length-1}`;
  $("step-navigation").replaceChildren(...pages.map((page,index)=>{
    const button=document.createElement("button");button.type="button";
    button.textContent=page.querySelector("legend,h3").textContent;
    button.disabled=index>wizardReached;
    if(index===wizardIndex) button.setAttribute("aria-current","step");
    button.addEventListener("click",()=>{
      if(index>wizardIndex && !validateWizardPage(pages[wizardIndex])) return;
      wizardIndex=index;renderWizard(true);
    });return button;
  }));
  $("step-back").disabled=wizardIndex===0;
  $("step-next").hidden=review; $("run-button").hidden=!review;
  $("step-next").textContent=wizardIndex===pages.length-2?"Review study":"Next";
  if(review) renderStudySummary();
  if(focus) {
    const heading=pages[wizardIndex].querySelector("legend,h3");heading.tabIndex=-1;heading.focus();
    $("step-progress").scrollIntoView({behavior:"smooth",block:"start"});
  }
}
function validateWizardPage(page) {
  $("form-error").hidden=true;
  for(const input of page.querySelectorAll("input,select")) {
    let hidden=false;
    for(let parent=input.parentElement;parent && parent!==page;parent=parent.parentElement) if(parent.hidden) hidden=true;
    if(input.disabled || hidden) continue;
    const optional=["location_query","orientation_year","ess_basis","ess_charge_override","ess_discharge_override"];
    if(input.type!=="checkbox" && !optional.includes(input.name) && ((input.value==="" && input.name!=="tariff_id") || input.value==="__unset__")) {
      for(let parent=input.parentElement;parent && parent!==page;parent=parent.parentElement) if(parent.tagName==="DETAILS") parent.open=true;
      showError("form-error",new Error("Enter the required values or choose Use Default Values for this step."));input.focus();return false;
    }
    if(!input.checkValidity()) {
      for(let parent=input.parentElement;parent && parent!==page;parent=parent.parentElement) if(parent.tagName==="DETAILS") parent.open=true;
      input.reportValidity();return false;
    }
  }
  let error=null;
  if(page.contains(field("end_date")) && field("end_date").value<field("start_date").value) error="End date must be on or after the start date.";
  if(page.contains(field("weather_source")) && template?.schema_version>=2 && field("weather_source").value==="nsrdb" && !weatherId) error="Retrieve matching historical weather before continuing.";
  if(page.contains(field("capacity_kWh"))) {
    if(field("ess_mode").value==="equipment" && !essResolution?.ready) error="Review and apply the equipment settings before continuing.";
    else {
      const capacity=Number(field("capacity_kWh").value), energy=Number(field("energy_kWh").value), min=Number(field("SOC_min").value), max=Number(field("SOC_max").value);
      if(min>=max || energy<capacity*min || energy>capacity*max) error="Initial battery energy must lie between its minimum and maximum SOC limits.";
    }
  }
  if(error) {showError("form-error",new Error(error));return false;}
  return true;
}
function advanceWizard() {
  if(!capabilities || !validateWizardPage(wizardPages()[wizardIndex])) return;
  wizardIndex++;wizardReached=Math.max(wizardReached,wizardIndex);renderWizard(true);
}
function validateWizard() {
  const pages=wizardPages();
  for(let index=0;index<pages.length;index++) {
    wizardIndex=index;renderWizard();
    if(!validateWizardPage(pages[index])) {renderWizard(true);return false;}
  }
  return true;
}
function renderStudySummary() {
  const summary=$("study-summary");summary.replaceChildren();
  for(const page of wizardPages().slice(0,-1)) {
    const details=document.createElement("details"), title=document.createElement("summary"), list=document.createElement("dl");
    title.textContent=page.querySelector("legend").textContent;details.append(title,list);
    for(const input of page.querySelectorAll("input,select")) {
      if(input.disabled || input.closest("[hidden]") && input.closest("[hidden]")!==page) continue;
      const label=input.closest("label");if(!label) continue;
      const name=document.createElement("dt"), value=document.createElement("dd");
      name.textContent=[...label.childNodes].filter(node=>node.nodeType===Node.TEXT_NODE).map(node=>node.textContent).join("").trim();
      value.textContent=input.tagName==="SELECT"?input.selectedOptions[0]?.textContent || "—":input.type==="checkbox"?(input.checked?"Yes":"No"):input.value || "—";
      list.append(name,value);
    }
    summary.append(details);
  }
}
$("step-back").addEventListener("click",()=>{if(wizardIndex>0){wizardIndex--;$("form-error").hidden=true;renderWizard(true);}});
$("step-next").addEventListener("click",advanceWizard);


function defaultSettings() { return capabilities.candidate_defaults || capabilities.site_defaults || capabilities.defaults; }
function startBlankStudy() {
  fillForm(defaultSettings(),false);
  strategiesEdited=false;
  locationGeneration++; clearTimeout(utilityTimer); siteLabel="";
  weatherId=null;weatherMeta=null;annualResult=null;essResolution=null;
  for(const input of form.querySelectorAll("input[name],select[name]")) {
    if(input.type==="checkbox") input.checked=false;
    else if(input.name==="utility") input.value="unconfirmed";
    else input.value=input.name==="tariff_id"?"__unset__":"";
  }
  for(const box of $("strategies").querySelectorAll("input")) box.checked=box.value==="no_battery";
  $("location-status").textContent="Enter coordinates or search for your microgrid location.";
  $("utility-suggestion").textContent="Utility choices will appear after you set a location.";
  $("orientation-status").textContent="";
  updateSiteControls();resetWizard();
}
function applyStepDefaults(page) {
  const defaults=defaultSettings();
  const hadCoordinates=field("latitude").value!=="" || field("longitude").value!=="";
  const values={...defaults,...defaults.battery,...defaults.solar,
    latitude:defaults.site?.latitude,longitude:defaults.site?.longitude,location_query:defaults.site?.label,
    utility:"unconfirmed",load_mode:defaults.load?.mode,load_power_kw:defaults.load?.power_kw,
    archetype:defaults.load?.archetype,orientation_year:Math.max(...(capabilities.nsrdb_years || [2025])),
    ess_mode:"manual",ess_quantity:1,ess_initial:.5,ess_reserve:.2};
  for(const input of page.querySelectorAll("input[name],select[name]")) {
    if(input.disabled || input.readOnly || input.type==="checkbox" || !["","__unset__"].includes(input.value)) continue;
    if(input.name==="location_query" && hadCoordinates) continue;
    if(Object.hasOwn(values,input.name)) input.value=values[input.name] ?? "";
  }
  if(page.contains($("strategies")) && !strategiesEdited) for(const box of $("strategies").querySelectorAll("input")) box.checked=defaults.strategies.includes(box.value);
  if(page.contains(field("latitude"))) {
    locationGeneration++;siteLabel=field("location_query").value || `Coordinates ${field("latitude").value}, ${field("longitude").value}`;
    $("location-status").textContent=siteLabel;refreshUtilities(locationGeneration);
  }
  $("form-error").hidden=true;updateSiteControls();
}
for(const button of document.querySelectorAll(".use-defaults")) button.addEventListener("click",()=>applyStepDefaults(button.closest(".wizard-page")));

$("strategies").addEventListener("change",()=>{strategiesEdited=true;});
