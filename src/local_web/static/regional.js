"use strict";

function regionalCalendarCycles(start,end) {
  const result=[];let cursor=start.slice(0,7)+"-01";
  while(cursor<=end){const y=Number(cursor.slice(0,4)),m=Number(cursor.slice(5,7));
    const last=new Date(Date.UTC(y,m,0)).toISOString().slice(0,10);
    const a=start>cursor?start:cursor,b=end<last?end:last;
    result.push({start_date:a,end_date:b,billing_month:cursor,bill_date:b,kind:"hypothetical_calendar",
      source:"Explicit hypothetical calendar meter cycle, not an actual utility reading schedule",account_overrides:{}});
    cursor=new Date(Date.UTC(y,m,1)).toISOString().slice(0,10);
  }return result;
}
function regionalRateEvidenceContext(plan,account,start,end) {
  plan=plan||{};account=account||{};
  const mode=account.rate_evidence_mode||"verified",accepted=account.provisional_assumptions_accepted===true;
  const fields=(plan.account_fields||[]).filter(d=>d&&typeof d==="object");
  const modes=fields.find(d=>d.name==="rate_evidence_mode")?.choices||[];
  const validDates=/^\d{4}-\d{2}-\d{2}$/.test(start||"")&&/^\d{4}-\d{2}-\d{2}$/.test(end||"")&&start<=end;
  const overlaps=w=>{let last=w.end;
    if(last&&w.basis==="billing_month")last=new Date(Date.UTC(Number(last.slice(0,4)),Number(last.slice(5,7)),0)).toISOString().slice(0,10);
    return validDates&&(!w.start||w.start<=end)&&(!last||start<=last);};
  const declared=plan.provisional_assumptions||[],assumptions=declared.filter(overlaps);
  const historical=modes.includes("provisional_2025");
  const relevant=historical?(declared.length?assumptions.length>0:(plan.provisional_coverage||[]).some(overlaps)):modes.some(m=>m!=="verified");
  return {mode,accepted,relevant,show_controls:relevant||mode!=="verified"||accepted,
    assumptions,coverage:[...(plan.coverage||[]),...(mode==="provisional_2025"&&accepted?plan.provisional_coverage||[]:[])]};
}
function regionalIntervalSupport(select,plan) {
  const allowed=plan?.interval_minutes||[15,30];
  for(const option of select.options)option.disabled=!allowed.includes(Number(option.value));
  // Keep the chosen value explicit; changing utilities must not resample inputs.
  return allowed;
}
function buildRegionalStudyRequest(base,v) {
  const r=JSON.parse(JSON.stringify(base));r.name="Untitled study";
  r.site={latitude:Number(v.latitude),longitude:Number(v.longitude),label:v.site_label,utility:v.utility};
  r.tariff_comparisons=v.rg_alternative?[v.rg_alternative]:[];
  r.site_profile=v.site_profile;r.regional_account=v.regional_account;r.account=v.account;
  for(const key of ["start_date","end_date"])r[key]=v[key];r.timestep_minutes=Number(v.timestep_minutes);
  r.billing_cycles=v.cycles||regionalCalendarCycles(r.start_date,r.end_date);
  r.load={mode:v.load_mode,power_kw:v.load_mode==="csv"?null:Number(v.load_power_kw),
    archetype:v.load_mode==="csv"?null:v.load_mode==="constant"?base.load.archetype:v.archetype,
    csv:v.load_mode==="csv"?v.native_csv:null,source:v.rg_load_source,native_basis_confirmed:v.rg_native_confirmed===true};
  const pv=v.pv_choice==="yes",battery=v.pv_choice==="storage"||pv&&v.rg_battery===true;
  if(pv)for(const key of Object.keys(r.solar))r.solar[key]=Number(v[key]);else r.solar.dc_capacity_kw=0;
  r.pv_capacity_kw=pv?Number(v.pv_capacity_kw):0;
  if(battery){for(const key of Object.keys(r.battery))r.battery[key]=Number(v[key]);r.ess=v.ess||null;}
  else {r.battery=null;r.ess=null;}
  r.weather_source=pv?v.weather_source:"clear_sky";r.weather_id=pv&&v.weather_source==="nsrdb"?v.weather_id:null;
  r.weather=pv&&v.weather_source==="era5"?v.era5:null;
  r.operating_contract={mode:v.rg_export,interconnection_confirmed:v.rg_interconnection===true,
    grid_charging_confirmed:battery&&v.rg_grid_charge===true,renewable_only_charging:battery&&v.rg_pv_charge===true,
    no_battery_export:true,reference:v.rg_operation_source};
  r.electrical_service=v.electrical_service;r.credit_objective_policy=v.rg_credit_policy;
  r.degradation_cost_per_kWh=Number(v.degradation_cost_per_kWh);
  r.include_degradation_in_optimization=v.include_degradation_in_optimization===true;
  return r;
}
if(typeof module!=="undefined")module.exports={buildRegionalStudyRequest,regionalCalendarCycles,regionalRateEvidenceContext,regionalIntervalSupport};

if(typeof document!=="undefined") {
  let currentKey=null,nativeCsv=null,era5=null,era5Key=null,wasActive=false,marketCsv=null;
  const f=name=>field("rg_"+name),pretty=s=>s.replaceAll("_"," ").replace(/^./,c=>c.toUpperCase());
  const panel=document.createElement("fieldset");panel.id="regional-account";panel.hidden=true;
  panel.innerHTML=`<legend>Retail account and jurisdiction</legend><p id="regional-identity" class="hint"></p>
    <p class="hint">Select service from your bill or utility confirmation. A state, city, postal code or wholesale pricing node does not establish territory. No third-party supply contract is assumed.</p>
    <label>Service evidence<select name="rg_verification"><option value="hypothetical_case">Explicit hypothetical study</option><option value="electricity_bill">Electricity bill</option><option value="utility_confirmation">Utility confirmation</option></select></label>
    <label>Service evidence / hypothetical assumption<input name="rg_reference" maxlength="500" placeholder="Omit account numbers and personal identifiers"/></label>
    <label>Account billing plan<select name="rg_plan"></select></label>
    <label>Optional tariff comparison<select name="rg_alternative"><option value="">No alternative</option></select></label><p class="hint">Each eligible plan is optimized independently using the same site, equipment and starting account facts. This is not repricing one fixed schedule. All eligibility conditions must hold for both plans.</p>
    <p id="regional-coverage" class="hint"></p><div id="regional-sources" class="hint"></div><details id="regional-assumptions" hidden><summary>Provisional historical rates and billing assumptions</summary><div id="regional-assumption-list" class="hint"></div></details>
    <button type="button" class="secondary" id="regional-hypothetical">Apply explicitly hypothetical account facts</button>
    <p class="hint">Review every account fact. Existing obligations, contracted demand and history remain the same across scenarios. A checked eligibility field is a user assertion, not verification by the simulator.</p>
    <div id="regional-fields" class="form-grid"></div>
    <details><summary>Advanced · wholesale pricing identity</summary><label>Wholesale location · JSON or null<textarea name="rg_location">null</textarea></label><p class="hint">Bundled studies do not require market prices. MISO metadata, if supplied, requires cpnode, node_type and source; A MISO resource-adequacy zone is not a price node. MISO price retrieval is not implemented. PSE&amp;G CIEP requires the exact PSEG_RESID_AGG aggregate and original PJM hourly file; no Western Hub fallback.</p></details>`;
  document.querySelector('[data-step="2"]').append(panel);
  const cycles=document.createElement("fieldset");cycles.hidden=true;
  cycles.innerHTML=`<legend>Utility meter cycles</legend><label>Cycle basis<select name="rg_cycle_mode"><option value="calendar">Explicit hypothetical calendar cycles</option><option value="documented">Documented utility cycles</option></select></label>
    <label id="regional-cycle-list">Consecutive cycle list · JSON<textarea name="rg_cycles" rows="8" placeholder="start_date, end_date, billing_month, bill_date, kind, source, account_overrides"></textarea></label>
    <p class="hint">The utility's billing month and bill date are separate from service dates. Actual meter cycles must cover every interval. Each jurisdiction applies its own proration and rate-change rules.</p>`;
  document.querySelector('[data-step="3"]').append(cycles);
  const load=document.createElement("fieldset");load.hidden=true;
  load.innerHTML=`<legend>Native consumption and provenance</legend><label>Load source / assumption<input name="rg_load_source" maxlength="500"/></label>
    <div id="regional-native"><label>Native-load CSV · timestamp,native_load_kw<input name="rg_native_file" type="file" accept=".csv,text/csv"/></label>
    <label><input name="rg_native_confirmed" type="checkbox"/> These interval averages are native consumption before solar and storage, not net utility-meter purchases.</label><p class="hint" id="regional-native-status">Complete explicit-offset timestamps; at most 2 MiB. No resampling or gap filling.</p></div>`;
  document.querySelector('[data-step="9"]').append(load);
  const operating=document.createElement("fieldset");operating.hidden=true;
  operating.innerHTML=`<legend>Solar and storage account treatment</legend><label id="regional-battery-choice"><input name="rg_battery" type="checkbox" checked/> Include battery / ESS comparison</label>
    <label>Export arrangement<select name="rg_export"><option value="non_export">Approved non-export · surplus curtailed</option><option value="net_metering">Confirmed standard net metering</option></select></label>
    <label><input name="rg_interconnection" type="checkbox"/> Approved parallel operation, or an explicitly hypothetical approved installation.</label>
    <label><input name="rg_grid_charge" type="checkbox"/> Account permits grid charging (non-export operation only).</label>
    <label><input name="rg_pv_charge" type="checkbox"/> Battery charges only from PV; battery exports are prohibited in this path.</label>
    <label>Operating approval / hypothetical assumptions<input name="rg_operation_source" maxlength="500"/></label>
    <button type="button" class="secondary" id="regional-nem-hypothetical">Apply explicit hypothetical net-metering eligibility</button>
    <p class="hint">Solar enrollment, vintage, credit banks and size eligibility must also be configured in the account fields. Unsupported arrangements reject explicitly. No renewable-production incentive is automatically credited.</p>`;
  document.querySelector('[data-step="5"]').append(operating);
  const economics=document.createElement("fieldset");economics.hidden=true;
  economics.innerHTML=`<legend>Billing objective and electrical assumptions</legend>
    <div id="regional-ciep"><h3>PSE&amp;G CIEP hourly supply</h3><p class="hint">Original PJM REAL_TIME_HOURLY data, PSEG_RESID_AGG · node 116472957 · RESIDUAL_METERED_EDC · native blank zone. Prices, revisions and source bytes remain private local inputs.</p>
    <button type="button" class="secondary" id="regional-ciep-location">Use the filed PSE&amp;G CIEP aggregate</button>
    <label>Original PJM hourly CSV<input name="rg_market_file" type="file" accept=".csv,text/csv"/></label>
    <label>PJM download retrieval timestamp · explicit UTC offset<input name="rg_market_retrieved" placeholder="2026-10-15T18:00:00Z"/></label>
    <label><input name="rg_market_confirmed" type="checkbox"/> The file is the identified PSE&amp;G residual hourly series, retained for permitted internal use only.</label><p id="regional-market-status" class="hint">8 MiB maximum; no market API credential or hub fallback.</p></div>
    <label>Carried-credit dispatch treatment<select name="rg_credit_policy"><option value="exclude_opening_credits">Opening credits affect the reported bill only</option><option value="explicit_cash_bill">Optimize current cash bill with opening credits</option></select></label>
    <p class="hint">New export credits follow the selected utility's rules. Linked cycles use rolling historical perfect foresight with continuous SOC and billing state; they are not an annual optimum. Bills, wear estimates and electrical losses remain separate.</p>
    <div class="form-grid"><label>Electrical service<select name="rg_voltage"><option value="secondary">Secondary</option><option value="primary">Primary · replay unsupported</option><option value="subtransmission">Subtransmission · replay unsupported</option><option value="high_voltage">High voltage · replay unsupported</option><option value="transmission">Transmission · replay unsupported</option></select></label>
    <label>Phase<select name="rg_phase"><option value="single">Single phase</option><option value="three">Three phase</option></select></label>
    <label>Nominal service voltage · V<input name="rg_volts" type="number" min="100" step="any"/></label></div>
    <label>Electrical service / representative assumptions<input name="rg_electrical_source" maxlength="500"/></label>
    <p class="hint">Reference circuits: residential 25 kVA 120/240 V split phase; commercial single phase 75 kVA; three phase 750 kVA 480 V. Other nominal voltages and primary/HV service remain unevaluated. These are representative QSTS checks, not surveyed feeder or protection validation.</p>`;
  document.querySelector('[data-step="8"]').append(economics);
  const weather=document.createElement("div");weather.hidden=true;
  weather.innerHTML=`<p class="hint">ERA5 is hourly historical reanalysis. Hourly means are held across study intervals, not converted into measured subhourly observations. Open-Meteo/Copernicus attribution applies; the free hosted API is noncommercial.</p><button class="secondary" type="button" id="regional-weather-fetch">Retrieve ERA5 for this site and period</button><p id="regional-weather-status" class="hint" role="status"></p>`;
  document.querySelector('[data-step="4"] fieldset').append(weather);
  field("weather_source").append(option("era5","Historical weather · ERA5 via Open-Meteo"));
  function active(){return capabilities?.hosting_mode==="local"&&!!capabilities?.regional_simulation?.utilities[field("utility").value];}
  function utility(){return capabilities.regional_simulation.utilities[field("utility").value];}
  function plans(){return utility().plans.filter(p=>p.customer_class===siteCustomerClass());}
  function selected(){return utility().plans.find(p=>p.id===f("plan").value);}
  function base(){return utility().study_defaults_by_plan?.[f("plan").value]||utility().defaults[siteCustomerClass()||"residential"];}
  function batteryEnabled(){return active()&&(field("pv_choice").value==="storage"||field("pv_choice").value==="yes"&&f("battery").checked);}
  function accountFields(value){
    $("regional-fields").replaceChildren();
    const advanced=document.createElement("details"),heading=document.createElement("summary"),advancedFields=document.createElement("div");
    heading.textContent="Advanced account facts · history, contracts and special eligibility";advancedFields.className="form-grid";advanced.style.gridColumn="1/-1";advanced.append(heading,advancedFields);
    const basic=new Set(["unmetered_source","history_confirmed","history_source","demand_method","estimated_demand_source","tax_jurisdiction","tax_source","type_i_confirmed","usc_band","usc_source","usc_assignment_2025_source","usc_assignment_2026_source","subtotal_scope_confirmed","relief_policy","rate_zone","legacy_rate_zone","ts_metering","ts_metering_source","rate_evidence_mode","provisional_assumptions_accepted","supply","supply_arrangement","supplier","eligibility_confirmed","ordinary_use_confirmed","ordinary_service_confirmed","local_charges_confirmed","full_monthly_charges_confirmed","dg_enrollment_confirmed","dg_source","ee_tier","ee_tier_source","no_local_tax_confirmed","der_ordinary_service_confirmed","der_eligibility_source","no_special_provisions_confirmed","locality","parallel_service","parallel_operation_approved","parallel_operation_confirmed","solar_mode","solar_program","export_mode","ami","tou_enrollment_confirmed","legacy_enrollment_confirmed","net_metering_confirmed","voltage","voltage_v","delivery_voltage_kv","phase","power_factor"]);
    const descriptors=selected()?.account_fields||[];
    const spec=Object.fromEntries(descriptors.map(d=>[typeof d==="string"?d:d.name,typeof d==="string"?{}:d]));
    for(const [key,v] of Object.entries(value)){
      if(key==="tariff")continue;
      const label=document.createElement("label"),desc=spec[key]||{};
      if(["supply","supplier","supply_arrangement"].includes(key)&&selected()?.supply_arrangements)desc.choices=selected().supply_arrangements;
      label.append(document.createTextNode(desc.label||pretty(key)));
      let input;
      const object=v!==null&&typeof v==="object"||desc.type==="number_array";
      if(object||v===null){input=document.createElement("textarea");input.rows=object?3:1;input.dataset.valueType="json";input.value=JSON.stringify(v);}
      else if(desc.choices){input=document.createElement("select");for(const c of desc.choices)input.append(option(c,({bgs_rscp:"Default supply · BGS-RSCP",bgs_ciep:"Hourly default supply · BGS-CIEP",bundled:"Bundled utility supply",default_ptc:"Default supply · fixed Price to Compare (GSC-1)",sso:"Default supply · Standard Service Offer",sos:"Default supply · Standard Offer Service",ohio_power:"Ohio Power legacy rate zone",columbus_southern:"Columbus Southern Power legacy rate zone",verified:"Verified dates only",provisional_2025:"Provisional 2025 · documented assumptions",provisional_cycles_v1:"Provisional PECO cycles · allocation assumptions"})[c]||c));input.value=String(v);input.dataset.valueType=typeof v;}
      else {input=document.createElement("input");input.type=typeof v==="boolean"?"checkbox":typeof v==="number"?"number":"text";
        if(typeof v==="boolean")input.checked=v;else input.value=String(v);if(input.type==="number")input.step="any";input.dataset.valueType=typeof v;}
      input.name="rg_a_"+key;label.append(input);(basic.has(key)?$("regional-fields"):advancedFields).append(label);
      if(["billing_month","bill_date","cycle_kind","cycle_source","customer_class","market_data"].includes(key))label.hidden=true;
    }
    $("regional-fields").append(advanced);
  }
  function accountValue(){const a={tariff:f("plan").value};
    for(const input of $("regional-fields").querySelectorAll("input,select,textarea")){
      const key=input.name.slice(5),type=input.dataset.valueType;
      a[key]=type==="boolean"?input.checked:type==="number"?(input.value===""?null:Number(input.value)):type==="json"?JSON.parse(input.value):input.value;
    }
    if(a.supply==="bgs_ciep"&&marketCsv){if(!f("market_confirmed").checked)throw new Error("Confirm the hourly supply identity and private-use permission.");
      a.market_data={csv_text:marketCsv,metadata:{market:"REAL_TIME_HOURLY",source_url:"https://dataminer2.pjm.com/feed/rt_hrl_lmps",retrieved_at:f("market_retrieved").value,unit:"$/MWh",usage_permission:"internal_use_only"}};
    }return a;
  }
  function sync(){const on=active();
    for(const section of [panel,cycles,load,operating,economics]){section.hidden=!on;for(const input of section.querySelectorAll("input,select,textarea,button"))input.disabled=!on;}
    const eraOption=field("weather_source").querySelector('option[value="era5"]');eraOption.hidden=eraOption.disabled=!on;
    weather.hidden=!on||field("weather_source").value!=="era5";
    if(!on){currentKey=null;return;}wasActive=true;
    field("timezone").value=utility().timezone||base().timezone;
    $("utility-suggestion").textContent="Manual utility selection. Confirm actual account eligibility; coordinates do not establish this service territory.";
    const key=field("utility").value+":"+siteCustomerClass();
    if(currentKey!==key){f("plan").replaceChildren(option("","Choose confirmed billing plan…"),...plans().map(p=>{
      const o=option(p.id,p.label+(p.status!=="supported"?" · unavailable":""));o.disabled=p.status!=="supported";o.title=p.reason||p.eligibility||"";return o;}));currentKey=key;$("regional-fields").replaceChildren();}
    const plan=selected();
    const evidence=regionalRateEvidenceContext(plan,{rate_evidence_mode:field("rg_a_rate_evidence_mode")?.value,
      provisional_assumptions_accepted:field("rg_a_provisional_assumptions_accepted")?.checked},field("start_date").value,field("end_date").value);
    for(const name of ["rate_evidence_mode","provisional_assumptions_accepted"]){const input=field("rg_a_"+name);if(input){input.closest("label").hidden=!evidence.show_controls;if(name==="provisional_assumptions_accepted")input.disabled=evidence.mode==="verified";}}
    const previousAlternative=f("alternative").value;
    f("alternative").replaceChildren(option("","No alternative"),...plans().filter(p=>p.status==="supported"&&p.id!==plan?.id&&((p.voltage||utility().accounts[p.id]?.voltage||base().electrical_service.voltage)===(plan?.voltage||utility().accounts[plan?.id]?.voltage||base().electrical_service.voltage))).map(p=>option(p.id,p.label)));
    if([...f("alternative").options].some(o=>o.value===previousAlternative))f("alternative").value=previousAlternative;
    $("regional-nem-hypothetical").hidden=f("export").value!=="net_metering";
    $("regional-nem-hypothetical").disabled=f("verification").value!=="hypothetical_case";
    const ciep=field("utility").value==="pseg"&&(utility().accounts[f("plan").value]?.supply==="bgs_ciep"||field("rg_a_supply")?.value==="bgs_ciep");
    $("regional-ciep").hidden=!ciep;
    const grid=utility().grid_operator||"PJM";
    const region=grid==="MISO"?`Resource adequacy zone: ${utility().resource_adequacy_zone} · Transmission zone: ${utility().transmission_zone||"Not assigned"} · Transmission owner: ${utility().transmission_owner||"Not assigned; verify site-specific ownership"} · LRZ is not a pricing node. ${utility().transmission_ownership_context||""}`:`Transmission zone: ${utility().transmission_zone}`;
    $("regional-identity").textContent=`Distribution: ${utility().label} · Jurisdiction: ${utility().state} · Default retail supplier: ${utility().label} · Grid operator: ${grid} · ${region} · Wholesale pricing identity is separate.`;
    $("regional-coverage").textContent=plan?`${plan.eligibility||"Confirm actual eligibility."} Verified: ${(plan.coverage||[]).map(w=>w.start+" → "+w.end).join(", ")}. ${(plan.limitations||[]).join(" ")}`:"Choose a plan to inspect its verified dates and requirements.";
    if(plan?.provisional_coverage)$("regional-coverage").textContent+=" Provisional coverage, only with explicit acceptance: "+plan.provisional_coverage.map(w=>w.start+" → "+w.end).join(", ")+". These are assumed historical estimates, not verified tariffs.";
    $("regional-assumptions").hidden=!evidence.assumptions.length;
    $("regional-assumption-list").replaceChildren();for(const item of evidence.assumptions){const p=document.createElement("p");p.textContent=`${item.id} · ${item.start} → ${item.end} · ${item.basis}: ${item.explanation} Values: ${JSON.stringify(item.assumed_values)}`;$("regional-assumption-list").append(p);}
    if(evidence.mode!=="verified"&&evidence.accepted&&evidence.assumptions.length)$("regional-assumptions").open=true;
    $("regional-sources").replaceChildren();for(const source of [...(plan?.sources||[]),...(utility().grid_sources||[])]){const url=typeof source==="string"?source:source.url;if(!url)continue;const a=document.createElement("a");a.href=url;a.target="_blank";a.rel="noreferrer";a.textContent="Official source";$("regional-sources").append(a,document.createTextNode(" · "));}
    $("regional-hypothetical").disabled=f("verification").value!=="hypothetical_case"||!plan;
    for(const opt of field("tariff_id").options)opt.disabled=opt.hidden=opt.value!=="__unset__";
    for(const p of plans().filter(p=>p.status==="supported")){let o=field("tariff_id").querySelector(`option[value="regional:${p.id}"]`);if(!o){o=option("regional:"+p.id,p.label);o.dataset.regional="true";field("tariff_id").append(o);}o.textContent=p.label;o.hidden=o.disabled=false;}
    field("tariff_id").value=plan?"regional:"+plan.id:"__unset__";
    $("fixed-price-label").hidden=true;$("price-note").textContent="Utility-specific itemized retail bill; all enabled decision-dependent components feed the same authoritative objective. Inspect completeness, sources and reconciliation in results.";
    const csvOption=field("load_mode").querySelector('option[value="csv"]');if(csvOption){csvOption.hidden=csvOption.disabled=false;csvOption.textContent="Uploaded native-load CSV";}
    $("regional-native").hidden=field("load_mode").value!=="csv";field("load_power_kw").disabled=field("load_mode").value==="csv";$("load-power-label").hidden=field("load_mode").value==="csv";
    $("regional-cycle-list").hidden=f("cycle_mode").value!=="documented";
    regionalIntervalSupport(field("timestep_minutes"),plan);
    $("strategies").closest("fieldset").hidden=true;$("orientation-controls").hidden=true;
    field("carbon_weight").closest("label").hidden=true;field("carbon_weight").disabled=true;
    const pv=field("pv_choice").value==="yes",storage=batteryEnabled();
    $("regional-battery-choice").hidden=!pv;
    for(const name of ["max_charge_kw","max_discharge_kw","charge_efficiency","discharge_efficiency","capacity_kWh","energy_kWh","SOC_min","SOC_max"]){field(name).disabled=!storage;field(name).closest("label").hidden=!storage;}
    for(const name of ["pv_capacity_kw","inverter_efficiency"]){field(name).disabled=!pv;field(name).closest("label").hidden=!pv;}
    $("pv-battery-connection").hidden=!(pv&&storage);field("pv_battery_connection").value="ac_coupled";
    const modes=plan?.equipment_modes||["grid_only","pv_only","pv_battery","storage_only"];
    for(const [value,allowed] of [["yes",modes.includes("pv_only")],["storage",modes.includes("storage_only")]]){const choice=field("pv_choice").querySelector(`option[value="${value}"]`);choice.disabled=!allowed;choice.dataset.regionalEquipment="true";}
    const solarModes=ciep?["non_export"]:plan?.solar_modes||(plan?.net_metering===false?["non_export"]:["non_export","net_metering"]);
    f("export").querySelector('option[value="net_metering"]').disabled=!solarModes.includes("net_metering");
    $("dataset-info").textContent=field("rg_a_rate_evidence_mode")?.value==="provisional_cycles_v1"?"PECO provisional allocation: 1–45 whole local service days; days/30 outside 26–35 days, dated delivery, end-of-service GSA/TSC and one cycle demand. Explicit acceptance is required. Bills and savings are estimates; prices remain within verified dates.":field("rg_a_rate_evidence_mode")?.value==="provisional_2025"&&field("rg_a_provisional_assumptions_accepted")?.checked?"Use complete utility cycles within the explicitly accepted provisional 2025 coverage. Rates and bills use documented assumptions; calendar cycles remain hypothetical. Wholesale prices do not replace bundled retail rates.":"Use complete utility cycles within the selected plan's verified dates. Calendar cycles are explicitly hypothetical; market data is unnecessary for bundled supply.";
    $("pv-choice-note").textContent="Compare grid-only, PV-only and PV plus storage, or choose storage without PV. Surplus is curtailed unless verified net metering is explicitly enabled.";
  }
  function leaving(){if(wasActive&&!active()){wasActive=false;for(const choice of field("pv_choice").querySelectorAll("option[data-regional-equipment]")){choice.disabled=false;delete choice.dataset.regionalEquipment;}for(const name of ["max_charge_kw","max_discharge_kw","charge_efficiency","discharge_efficiency","capacity_kWh","energy_kWh","SOC_min","SOC_max","pv_capacity_kw","inverter_efficiency"])field(name).closest("label").hidden=false;
    regionalIntervalSupport(field("timestep_minutes"),{interval_minutes:[5,15,30,60]});
    if(field("weather_source").value==="era5")field("weather_source").value="";}}
  function mainDefaults(){if(!active())return {};const d=base();return {...d.solar,...d.battery,pv_capacity_kw:d.pv_capacity_kw,load_mode:d.load.mode,load_power_kw:d.load.power_kw,archetype:d.load.archetype,weather_source:"clear_sky",timestep_minutes:15,degradation_cost_per_kWh:d.degradation_cost_per_kWh};}
  function defaults(page){if(!active())return;const d=base();
    if(page.contains(f("plan"))&&!f("plan").value){f("plan").value=d.account.tariff;accountFields(utility().accounts[d.account.tariff]);}
    const values={verification:"hypothetical_case",reference:d.regional_account.reference,load_source:d.load.source,cycle_mode:"calendar",credit_policy:d.credit_objective_policy,
      export:"non_export",
      voltage:d.electrical_service.voltage,phase:d.electrical_service.phase,volts:d.electrical_service.nominal_voltage_v,
      electrical_source:d.electrical_service.reference,operation_source:"Explicit hypothetical approved parallel non-export installation; review account facts"};
    for(const [key,v] of Object.entries(values)){const input=f(key);if(page.contains(input)&&input.value==="")input.value=v;}
    sync();
  }
  function values(){const v=Object.fromEntries(new FormData(form));for(const input of form.querySelectorAll('input[type="checkbox"]'))v[input.name]=input.checked;
    for(const key of [...Object.keys(base().solar),...Object.keys(base().battery||{}),"pv_capacity_kw","pv_choice","weather_source","degradation_cost_per_kWh","timestep_minutes"])v[key]=field(key).value;
    const a=accountValue();const region={...base().regional_account,verification_kind:f("verification").value,reference:f("reference").value,
      wholesale_pricing_location:JSON.parse(f("location").value||"null")};
    return {...v,site_profile:siteProfile(),site_label:siteLabel||`Coordinates ${field("latitude").value}, ${field("longitude").value}`,
      regional_account:region,account:a,cycles:f("cycle_mode").value==="documented"?JSON.parse(f("cycles").value):null,
      electrical_service:{voltage:f("voltage").value,phase:f("phase").value,nominal_voltage_v:Number(f("volts").value),reference:f("electrical_source").value},
      native_csv:nativeCsv,era5,weather_id:weatherId,ess:essResolution};}
  function request(){if(field("ess_mode").value==="equipment"&&batteryEnabled()&&!essResolution?.ready)throw new Error("Review and apply ESS equipment first.");return buildRegionalStudyRequest(base(),values());}
  function validate(page){if(!active())return true;try{
    if(page.dataset.step==="2"){if(!selected()||!f("reference").value.trim())throw new Error("Choose the actual billing plan and document service or hypothetical assumptions.");const a=accountValue();if(["provisional_2025","provisional_cycles_v1"].includes(a.rate_evidence_mode)&&!a.provisional_assumptions_accepted)throw new Error("Accept the documented provisional rates and billing assumptions before continuing.");}
    if(page.dataset.step==="3"){
      const allowed=regionalIntervalSupport(field("timestep_minutes"),selected());
      if(!allowed.includes(Number(field("timestep_minutes").value)))throw new Error("Choose a supported meter interval: "+allowed.join(" or ")+" minutes. Inputs are not automatically resampled.");
      const list=f("cycle_mode").value==="documented"?JSON.parse(f("cycles").value):regionalCalendarCycles(field("start_date").value,field("end_date").value);
      const a=accountValue(),coverage=regionalRateEvidenceContext(selected(),a,field("start_date").value,field("end_date").value).coverage;
      const covered=day=>coverage.some(w=>w.start<=day&&day<=w.end);
      for(const cycle of list){if(field("utility").value==="pseg"){
        if(!covered(cycle.bill_date))throw new Error("The utility bill date is outside verified tariff coverage. PSE&G selects rates by bill date; review the documented cycles.");
      }else {if((selected()?.bill_month_coverage_required||field("utility").value==="dte_electric")&&!covered(cycle.bill_date))throw new Error("Bill date is outside the selected supply/rider evidence coverage.");for(let day=cycle.start_date;day<=cycle.end_date;){if(!covered(day))throw new Error("Service date "+day+" is outside the selected component coverage. Review verified dates or explicitly accept the documented provisional assumptions in the account step; no automatic substitution is used.");const next=new Date(day+"T00:00:00Z");next.setUTCDate(next.getUTCDate()+1);day=next.toISOString().slice(0,10);}}}
    }
    if(page.dataset.step==="5"&&selected()?.equipment_modes){const mode=field("pv_choice").value==="yes"?(f("battery").checked?"pv_battery":"pv_only"):field("pv_choice").value==="storage"?"storage_only":"grid_only";if(!selected().equipment_modes.includes(mode))throw new Error("This billing plan does not permit the selected PV/storage arrangement. Choose an eligible plan or grid-only operation.");}
    if(page.dataset.step==="4"&&field("weather_source").value==="era5"&&(!era5||era5Key!==weatherKey()))throw new Error("Retrieve ERA5 for the selected site and exact service dates; no weather fallback is used.");
    if(page.dataset.step==="9"&&field("load_mode").value==="csv"&&(!nativeCsv||!f("native_confirmed").checked))throw new Error("Upload complete native consumption and confirm its measurement basis.");
    if(page.dataset.step==="8"&&!f("electrical_source").value.trim())throw new Error("Document electrical service facts or representative assumptions.");
    return true;
  }catch(e){showError("form-error",e);return false;}}
  function weatherKey(){return JSON.stringify([field("latitude").value,field("longitude").value,field("start_date").value,field("end_date").value,field("timezone").value]);}
  $("regional-weather-fetch").addEventListener("click",async()=>{const key=weatherKey();try{$("regional-weather-fetch").disabled=true;$("regional-weather-status").textContent="Retrieving ERA5 reanalysis…";
    const data=await api("/api/v1/regional/weather",{latitude:Number(field("latitude").value),longitude:Number(field("longitude").value),start_date:field("start_date").value,end_date:field("end_date").value,timezone:field("timezone").value});
    if(key!==weatherKey())throw new Error("Site or dates changed during retrieval; retrieve matching weather again.");era5=data.weather;era5Key=key;$("regional-weather-status").textContent=(data.cached?"Cached":"Retrieved")+" historical reanalysis ready. "+data.provenance.attribution;
  }catch(e){era5=null;era5Key=null;$("regional-weather-status").textContent=e.message;}finally{$("regional-weather-fetch").disabled=false;}});
  f("native_file").addEventListener("change",async()=>{const item=f("native_file").files[0];if(!item){nativeCsv=null;return;}if(item.size>2*1024*1024){nativeCsv=null;$("regional-native-status").textContent="File exceeds 2 MiB.";return;}nativeCsv=await item.text();$("regional-native-status").textContent="Loaded "+item.name+"; exact intervals checked on submission.";});
  f("market_file").addEventListener("change",async()=>{const item=f("market_file").files[0];if(!item){marketCsv=null;return;}if(item.size>8*1024*1024){marketCsv=null;$("regional-market-status").textContent="File exceeds 8 MiB.";return;}marketCsv=await item.text();$("regional-market-status").textContent="Loaded "+item.name+"; source identity, UTC coverage and revisions checked on submission.";});
  function ciepLocation(){f("location").value=JSON.stringify({pnode_id:116472957,pnode_name:"PSEG_RESID_AGG",zone:"",source:"Official PSE&G BGS-CIEP seminar: PJM Data Miner node selection"});}
  $("regional-ciep-location").addEventListener("click",ciepLocation);
  function syncExportAccount(){for(const key of ["solar_mode","solar_program","export_mode"]){const input=field("rg_a_"+key);if(input)input.value=f("export").value==="net_metering"?"net_metering":key==="export_mode"?"none":"non_export";}}
  f("export").addEventListener("change",()=>{syncExportAccount();if(f("export").value==="net_metering"){f("grid_charge").checked=false;f("pv_charge").checked=batteryEnabled();}sync();});
  $("regional-nem-hypothetical").addEventListener("click",()=>{if(f("verification").value!=="hypothetical_case")return;
    syncExportAccount();for(const key of ["net_metering_confirmed","net_metering_size_confirmed","parallel_service","parallel_operation_approved","parallel_operation_confirmed","recs_assignment_confirmed"]){const input=field("rg_a_"+key);if(input)input.checked=true;}
    const nem=utility().hypothetical_nem?.[f("plan").value];if(nem&&field("rg_a_nem")){const value=structuredClone(nem);value.period_start=value.bank_as_of=field("start_date").value||base().start_date;field("rg_a_nem").value=JSON.stringify(value);}
    f("operation_source").value="Explicit hypothetical utility-approved standard net-metering installation; review every eligibility and bank assumption";f("interconnection").checked=true;f("grid_charge").checked=false;f("pv_charge").checked=batteryEnabled();sync();});
  f("plan").addEventListener("change",()=>{accountFields(utility().accounts[f("plan").value]||{});syncExportAccount();sync();});
  $("regional-hypothetical").addEventListener("click",()=>{if(f("verification").value!=="hypothetical_case")return;
    const d=utility().hypothetical_accounts?.[f("plan").value]||utility().accounts[f("plan").value];accountFields(d);f("reference").value="Explicit hypothetical account; all enrollment, contract and history inputs are study assumptions";
    if(d.supply==="bgs_ciep")f("location").value=JSON.stringify({pnode_id:116472957,pnode_name:"PSEG_RESID_AGG",zone:"",source:"Official PSE&G BGS-CIEP seminar, slide with PJM Data Miner node selection"});sync();});
  form.addEventListener("change",event=>{if(!active())return;if(event.target.name==="tariff_id"&&event.target.value.startsWith("regional:")){f("plan").value=event.target.value.slice(9);accountFields(utility().accounts[f("plan").value]);}
    if(["rg_a_rate_evidence_mode","start_date","end_date","rg_cycles"].includes(event.target.name)){const accepted=field("rg_a_provisional_assumptions_accepted");if(accepted)accepted.checked=false;}
    sync();if(event.target.name==="rg_battery")renderWizard();});
  form.addEventListener("input",()=>{if(active())sync();});
  function restore(r){template=structuredClone(defaultSettings());restoreSiteProfile(r.site_profile);resetUtilityOptions(r.site.utility);field("utility").value=r.site.utility;siteLabel=r.site.label;
    for(const key of ["latitude","longitude"])field(key).value=r.site[key];field("location_query").value=siteLabel;
    for(const key of ["start_date","end_date","timestep_minutes","pv_capacity_kw","weather_source","degradation_cost_per_kWh"])field(key).value=r[key];
    for(const [key,value] of Object.entries({...r.solar,...(r.battery||{})}))field(key).value=value;
    field("include_degradation_in_optimization").checked=r.include_degradation_in_optimization;
    field("pv_choice").value=r.solar.dc_capacity_kw>0?"yes":r.battery?"storage":"no";f("battery").checked=!!r.battery;
    field("load_mode").value=r.load.mode;field("load_power_kw").value=r.load.power_kw??"";field("archetype").value=r.load.archetype??"";
    currentKey=null;sync();f("plan").value=r.account.tariff;accountFields(r.account);sync();f("alternative").value=r.tariff_comparisons?.[0]||"";
    f("verification").value=r.regional_account.verification_kind;f("reference").value=r.regional_account.reference;f("location").value=JSON.stringify(r.regional_account.wholesale_pricing_location);
    f("cycle_mode").value="documented";f("cycles").value=JSON.stringify(r.billing_cycles,null,2);
    f("load_source").value=r.load.source;f("native_confirmed").checked=r.load.native_basis_confirmed;nativeCsv=r.load.csv;
    for(const [key,target] of [["mode","export"],["reference","operation_source"]])f(target).value=r.operating_contract[key];
    for(const [key,target] of [["interconnection_confirmed","interconnection"],["grid_charging_confirmed","grid_charge"],["renewable_only_charging","pv_charge"]])f(target).checked=r.operating_contract[key];
    f("credit_policy").value=r.credit_objective_policy;f("voltage").value=r.electrical_service.voltage;f("phase").value=r.electrical_service.phase;f("volts").value=r.electrical_service.nominal_voltage_v;f("electrical_source").value=r.electrical_service.reference;
    marketCsv=r.account.market_data?.csv_text||null;f("market_retrieved").value=r.account.market_data?.metadata?.retrieved_at||"";f("market_confirmed").checked=!!marketCsv;
    restoreCandidate(r);weatherId=r.weather_id;weatherMeta=weatherId?{request:{...weatherRequest()}}:null;era5=r.weather;era5Key=era5?weatherKey():null;updateSiteControls();resetWizard();}
  function comparisonChart(table,enabled){
    let chart=$("regional-result-chart");if(!chart){chart=document.createElement("figure");chart.id="regional-result-chart";$("table-container").before(chart);}
    chart.replaceChildren();chart.hidden=!enabled;if(!enabled)return;
    const rows=table.data.map(row=>Object.fromEntries(table.columns.map((key,i)=>[key,row[i]])));
    const ns="http://www.w3.org/2000/svg",svg=document.createElementNS(ns,"svg");
    svg.setAttribute("viewBox",`0 0 760 ${50+rows.length*48}`);svg.setAttribute("role","img");svg.setAttribute("aria-label","Utility bills by scenario and tariff; exact amounts are in the comparison table");
    const maximum=Math.max(1,...rows.map(r=>Math.abs(Number(r.utility_bill_usd))));
    rows.forEach((row,i)=>{const y=28+i*48,label=document.createElementNS(ns,"text"),bar=document.createElementNS(ns,"rect"),amount=document.createElementNS(ns,"text");
      label.setAttribute("x",0);label.setAttribute("y",y);label.setAttribute("font-size",12);label.textContent=(row.tariff||"")+" · "+pretty(row.scenario);
      bar.setAttribute("x",255);bar.setAttribute("y",y-16);bar.setAttribute("width",Math.max(1,Math.abs(Number(row.utility_bill_usd))/maximum*350));bar.setAttribute("height",23);bar.setAttribute("fill",(row.rate_evidence_status==="provisional"||row.is_complete_bill===false||row.is_complete_bill==="False")?"#a56038":"#35786a");
      amount.setAttribute("x",620);amount.setAttribute("y",y);amount.setAttribute("font-size",13);amount.textContent=Number(row.utility_bill_usd).toLocaleString(undefined,{style:"currency",currency:"USD"});svg.append(label,bar,amount);});
    const caption=document.createElement("figcaption");caption.className="hint";caption.textContent="Utility charges only. Each tariff is optimized independently; wear and electrical losses are reported separately. Provisional historical estimates use the recorded rate and billing assumptions; completeness does not verify historical rates. Incomplete bills are flagged in the table.";chart.append(svg,caption);
  }
  window.regionalUI={comparisonChart,active,batteryEnabled,sync,leaving,mainDefaults,defaults,validate,restore,request,
    dateDefaults:()=>({start:field("start_date").value||base().start_date,end:field("end_date").value||base().end_date}),
    reset:()=>{currentKey=null;nativeCsv=era5=era5Key=marketCsv=null;},submit:()=>api("/api/v1/regional/studies?draft=1",request())};
}
