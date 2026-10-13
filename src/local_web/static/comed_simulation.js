"use strict";

// The same production builder is exercised by form-to-worker tests.
function buildComedSimulationRequest(base, v) {
  const r=JSON.parse(JSON.stringify(base));
  r.name="Untitled study";r.site_profile=v.site_profile;
  r.site={latitude:Number(v.latitude),longitude:Number(v.longitude),label:v.site_label,utility:"comed"};
  r.start_date=v.start_date;r.end_date=v.end_date;r.timestep_minutes=Number(v.timestep_minutes);
  r.regional_account.verification_kind=v.ce_verification;r.regional_account.reference=v.ce_reference;
  r.account.supply=v.tariff_id==="comed_BESH"?"BESH":"BES";
  if(!["comed_BES","comed_BESH"].includes(v.tariff_id))throw new Error("Choose ComEd BES or BESH in Economics.");
  r.account.delivery_class=v.ce_class;r.account.billing_month=r.start_date.slice(0,7)+"-01";
  r.account.ordinary_import_only_confirmed=v.ce_account_confirmed===true;
  if(r.site_profile.site_type==="commercial"||r.site_profile.subtype==="common_areas") {
    for(const key of ["previous_12_month_peak_kw","previous_calendar_year_peak_kw","previous_year_months_ge_100kw"])
      r.account[key]=Number(v["ce_"+key]);
    r.account.service_voltage=v.ce_voltage;r.account.utility_transformer=v.ce_transformer==="yes";
    r.account.competitively_declared=v.ce_competitive==="yes";r.account.electric_space_heat=v.ce_heat==="yes";
    r.account.watt_hour_eligibility=v.ce_class==="watt_hour"?v.ce_watt:"not_applicable";
    r.account.previous_12_month_mkd_kw=v.ce_class==="high_voltage"?Number(v.ce_hv_mkd):null;
    r.account.eligibility_source=v.ce_reference;
  }
  if(r.account.supply==="BESH") {
    r.account.capacity_obligation_kw=Number(v.ce_capacity);r.account.capacity_source=v.ce_capacity_source;
    r.prices={mode:v.ce_price_mode,source:v.ce_price_source,basis_confirmed:v.ce_price_confirmed===true,
      usd_per_mwh:v.ce_price_mode==="constant_example"?Number(v.ce_price):null,
      csv:v.ce_price_mode==="csv"?v.price_csv:null};
  } else {r.account.capacity_obligation_kw=null;r.account.capacity_source=null;r.prices=null;}
  r.load={mode:v.load_mode,power_kw:v.load_mode==="csv"?null:Number(v.load_power_kw),
    archetype:v.load_mode==="csv"?null:v.load_mode==="constant"?base.load.archetype:v.archetype,csv:v.load_mode==="csv"?v.native_csv:null,
    source:v.ce_load_source,native_basis_confirmed:v.ce_native_confirmed===true};
  const pv=v.pv_choice==="yes";
  if(pv)for(const key of Object.keys(r.solar))r.solar[key]=Number(v[key]);
  else r.solar.dc_capacity_kw=0;
  r.pv_capacity_kw=pv?Number(v.pv_capacity_kw):0;
  const storage=v.pv_choice==="storage"||pv&&v.ce_include_battery===true;
  if(storage&&Number(v.capacity_kWh)>0) {
    for(const key of Object.keys(r.battery))r.battery[key]=Number(v[key]);
    r.ess=v.ess||null;
  } else {r.battery=null;r.ess=null;}
  r.weather_source=pv?v.weather_source:"clear_sky";r.weather_id=pv&&v.weather_source==="nsrdb"?v.weather_id:null;
  r.degradation_cost_per_kWh=Number(v.degradation_cost_per_kWh);
  r.include_degradation_in_optimization=v.include_degradation_in_optimization===true;
  r.operating_contract={mode:pv||storage?"approved_non_export":"grid_only",
    interconnection_confirmed:v.ce_nonexport===true,standard_tariff_confirmed:v.ce_standard===true,
    grid_charging_confirmed:v.ce_grid_charge===true,reference:v.ce_operation_reference||""};
  return r;
}
if(typeof module!=="undefined")module.exports={buildComedSimulationRequest};

if(typeof document!=="undefined") {
  const f=name=>field("ce_"+name);
  let nativeCsv=null,priceCsv=null,lastKind=null,wasActive=false;
  const account=document.createElement("fieldset");account.id="comed-account";account.hidden=true;
  account.innerHTML=`<legend>ComEd account confirmation</legend>
    <p class="hint">Distribution utility: ComEd · State jurisdiction: Illinois · Retail supplier: ComEd · PJM transmission zone: COMED. The hourly pricing location/basis is configured separately for BESH in Economics.</p>
    <p class="hint">ComEd is a manual service selection. Illinois, Chicago, a ZIP code and PJM membership do not establish service territory or enrollment. Standard subtotals exclude state excise tax, municipal taxes and franchise fees.</p>
    <label>Service confirmation basis<select name="ce_verification"><option value="hypothetical_case">Explicit hypothetical study</option><option value="electricity_bill">Electricity bill</option><option value="utility_confirmation">Utility confirmation</option></select></label>
    <label>Service and eligibility reference<input name="ce_reference" maxlength="500" required placeholder="Describe evidence or hypothetical assumptions; omit account numbers"/></label>
    <label>ComEd delivery class<select name="ce_class" required></select></label>
    <label><input name="ce_account_confirmed" type="checkbox" required/> Confirm one standard account with ComEd supply, no discounts, exemptions, special contracts or generation/export settlement; class and supply eligibility are confirmed or explicitly hypothetical.</label>
    <div id="comed-commercial"><div class="form-grid">
      <label>Service voltage<select name="ce_voltage"><option value="">Choose…</option><option value="secondary">Secondary</option><option value="primary">Primary</option><option value="high_voltage">High voltage · single point ≥69 kV</option></select></label>
      <label>Utility owns service transformer<select name="ce_transformer"><option value="">Choose…</option><option value="yes">Yes</option><option value="no">No</option></select></label>
      <label>Competitively declared account<select name="ce_competitive"><option value="">Choose…</option><option value="no">No</option><option value="yes">Yes · BES unavailable</option></select></label>
      <label>Utility electric-space-heating supply subgroup<select name="ce_heat"><option value="">Choose…</option><option value="no">No</option><option value="yes">Yes · confirmed subgroup</option></select></label>
      <label>Prior 12 billing periods · overall peak kW<input name="ce_previous_12_month_peak_kw" type="number" min="0" step="any"/></label>
      <label>Previous calendar year · overall peak kW<input name="ce_previous_calendar_year_peak_kw" type="number" min="0" step="any"/></label>
      <label>Previous calendar year · months ≥100 kW<input name="ce_previous_year_months_ge_100kw" type="number" min="0" max="12" step="1"/></label>
    </div><label id="comed-watt">Watt-Hour eligibility<select name="ce_watt"><option value="">Choose…</option><option value="legacy_pre_2022">Confirmed legacy pre-2022 account</option><option value="dedicated_ev">Separate dedicated EV meter</option></select></label>
    <label id="comed-hv">Prior 12 billing periods · maximum MKD kW<input name="ce_hv_mkd" type="number" min="0" step="any"/></label>
    <p class="hint">Class history, previous-year rider thresholds, current all-hours demand, current billed MKD and BESH capacity are distinct quantities. Histories remain fixed across every scenario. Select BES/BESH in Economics.</p></div>`;
  document.querySelector('[data-step="2"]').append(account);
  const load=document.createElement("fieldset");load.id="comed-load";load.hidden=true;
  load.innerHTML=`<legend>ComEd native building load</legend><p class="hint">Use the shared constant or generic synthetic load, or upload native consumption before PV/storage. Generic shapes are study assumptions, not Illinois reference data or appliance/HVAC estimates.</p>
    <label>Native-load source or assumption<input name="ce_load_source" maxlength="500" required/></label>
    <div id="comed-native-file"><label>Native-load CSV · timestamp,native_load_kw<input name="ce_native_file" type="file" accept=".csv,text/csv"/></label>
    <label><input name="ce_native_confirmed" type="checkbox"/> Confirm these are native building loads before PV/battery, not utility-meter purchases or net imports.</label><p class="hint" id="comed-native-status">Exact timezone-aware study intervals, 2 MiB maximum; no scaling, resampling or gap filling.</p></div>`;
  document.querySelector('[data-step="9"]').append(load);
  const operation=document.createElement("fieldset");operation.id="comed-operation";operation.hidden=true;
  operation.innerHTML=`<legend>ComEd equipment and non-export operation</legend>
    <label id="comed-storage-choice"><input name="ce_include_battery" type="checkbox" checked/> Include battery / ESS in the comparison</label>
    <div id="comed-operating-confirmations"><label><input name="ce_nonexport" type="checkbox"/> Approved non-export PV/storage interconnection, or an explicitly hypothetical non-export installation.</label>
    <label><input name="ce_standard" type="checkbox"/> Standard import tariff remains applicable without DER rebates, standby charges, reassignment or other special billing.</label>
    <label id="comed-grid-charge"><input name="ce_grid_charge" type="checkbox"/> Storage may charge from the grid under this account arrangement.</label>
    <label>Non-export approval / study assumption reference<input name="ce_operation_reference" maxlength="500"/></label></div>
    <p class="hint">Zero exports are enforced. Unused PV is recorded as curtailment; no surplus sale, net-metering credit or future capacity reduction is assumed.</p>`;
  document.querySelector('[data-step="5"]').append(operation);
  const pricing=document.createElement("fieldset");pricing.id="comed-pricing";pricing.hidden=true;
  pricing.innerHTML=`<legend>ComEd supply and optimization</legend><p class="hint">Compare grid-only, PV without storage and PV plus optimized storage using identical native loads, dates and account history. Minimize the modeled subtotal before line-cent rounding; optional wear is separate. Perfect foresight is a benchmark, not a deployable controller.</p>
    <p class="hint"><a id="comed-rate-source" target="_blank" rel="noreferrer">Official ComEd ratebook and billing rules</a> · Rate version, source pages and excluded costs are preserved in results.</p>
    <div id="comed-hourly"><label>BESH billed capacity obligation · kW<input name="ce_capacity" type="number" min="0" step="any"/></label><label>Capacity obligation source<input name="ce_capacity_source" maxlength="500"/></label>
    <label>ComEd-zone residual hourly LMP source<select name="ce_price_mode"><option value="constant_example">Explicit synthetic constant assumption</option><option value="csv">Identified hourly CSV · observed or synthetic</option></select></label>
    <label id="comed-price-constant">Synthetic residual LMP · USD/MWh<input name="ce_price" type="number" step="any"/></label>
    <label id="comed-price-file">Hourly price CSV · timestamp,residual_lmp_usd_per_mwh<input name="ce_price_file" type="file" accept=".csv,text/csv"/></label>
    <label>Hourly price source or synthetic assumption<input name="ce_price_source" maxlength="500"/></label>
    <label><input name="ce_price_confirmed" type="checkbox"/> Verified COMED PJM real-time residual hourly LMP in USD/MWh at interval starts, or an explicitly synthetic assumption. No hub, day-ahead or adjusted-retail substitution.</label>
    <p id="comed-price-status" class="hint">Prices and raw market inputs stay local; actual data retrieval is not enabled. Capacity is fixed across scenarios.</p></div>
    <p class="hint">Verified September and October 2026 complete calendar months only. America/Chicago boundaries. Commercial demand uses aligned 30-minute averages from 15/30-minute records, weekday 09:00–18:00 excluding NERC holidays. Excluded taxes and fees remain visible in results.</p>`;
  document.querySelector('[data-step="8"]').append(pricing);
  field("load_mode").append(option("csv","Uploaded native-load CSV · ComEd"));
  for(const k of ["residential","multifamily"])if(![...field("archetype").options].some(o=>o.value===k))field("archetype").append(option(k,"Generic synthetic "+k));
  function active(){return !!capabilities?.comed_simulation&&capabilities.hosting_mode==="local"&&field("utility").value==="comed";}
  function batteryEnabled(){return active()&&(field("pv_choice").value==="storage"||field("pv_choice").value==="yes"&&f("include_battery").checked);}
  function leaving(){if(wasActive&&!active()){
    for(const name of ["max_charge_kw","max_discharge_kw","charge_efficiency","discharge_efficiency","pv_capacity_kw","inverter_efficiency","load_power_kw"])field(name).closest("label").hidden=false;
    field("capacity_kWh").min="0.001";
    for(const minutes of ["5","60"])field("timestep_minutes").querySelector(`option[value="${minutes}"]`).disabled=false;
    field("weather_source").querySelector('option[value="nsrdb"]').disabled=false;
    wasActive=false;
  }}
  function mainDefaults(){if(!active())return {};const d=capabilities.comed_simulation.defaults[siteCustomerClass()||"residential"];return {...d.solar,...(d.battery||{}),pv_capacity_kw:d.pv_capacity_kw,load_mode:d.load.mode,load_power_kw:d.load.power_kw,archetype:d.load.archetype,weather_source:"clear_sky",degradation_cost_per_kWh:d.degradation_cost_per_kWh};}
  function sync(){
    const on=active(), commercial=siteCustomerClass()==="commercial";
    for(const panel of [account,load,operation,pricing]){panel.hidden=!on;for(const c of panel.querySelectorAll("input,select"))c.disabled=!on;}
    const csvOption=field("load_mode").querySelector('option[value="csv"]');csvOption.disabled=csvOption.hidden=!on;
    if(!on){if(field("load_mode").value==="csv")field("load_mode").value="";lastKind=null;return;}
    wasActive=true;
    field("timezone").value="America/Chicago";
    $("comed-rate-source").href=capabilities.comed.source_url;
    const kind=commercial?"commercial":"residential";
    if(lastKind!==kind){const classes=capabilities.comed[kind+"_classes"];f("class").replaceChildren(option("","Choose confirmed delivery class…"),...classes.map(c=>option(c,c.replaceAll("_"," "))));lastKind=kind;}
    $("comed-commercial").hidden=!commercial;$("comed-watt").hidden=!commercial||f("class").value!=="watt_hour";$("comed-hv").hidden=!commercial||f("class").value!=="high_voltage";
    for(const opt of field("tariff_id").options){opt.hidden=opt.disabled=!opt.value.startsWith("comed_")&&opt.value!=="__unset__";}
    for(const supply of ["BES","BESH"]){if(!field("tariff_id").querySelector(`option[value="comed_${supply}"]`))field("tariff_id").append(option("comed_"+supply,"ComEd "+supply+(supply==="BES"?" · eligible fixed supply":" · Hourly Pricing")));const o=field("tariff_id").querySelector(`option[value="comed_${supply}"]`);o.hidden=o.disabled=false;}
    $("fixed-price-label").hidden=true;$("price-note").textContent="ComEd modeled subtotal, with fixed account charges, signed riders and applicable distribution/transformer demand. Excludes state excise tax, municipal taxes and franchise fees.";
    $("comed-hourly").hidden=field("tariff_id").value!=="comed_BESH";
    $("comed-price-constant").hidden=f("price_mode").value!=="constant_example";$("comed-price-file").hidden=f("price_mode").value!=="csv";
    $("comed-native-file").hidden=field("load_mode").value!=="csv";
    field("load_power_kw").closest("label").hidden=field("load_mode").value==="csv";field("load_power_kw").disabled=field("load_mode").value==="csv";
    $("archetype-label").hidden=field("load_mode").value!=="synthetic";
    $("dataset-info").textContent="One complete September/October 2026 calendar month. Supply native loads; meter purchases may differ at sites with PV/storage.";
    field("timestep_minutes").querySelector('option[value="5"]').disabled=true;field("timestep_minutes").querySelector('option[value="60"]').disabled=commercial;
    const storage=batteryEnabled(),pv=field("pv_choice").value==="yes",equipment=storage||pv;
    field("pv_choice").querySelector('option[value="storage"]').disabled=false;
    $("comed-storage-choice").hidden=!pv;$("comed-operating-confirmations").hidden=!equipment;$("comed-grid-charge").hidden=!storage;
    for(const name of ["max_charge_kw","max_discharge_kw","charge_efficiency","discharge_efficiency"]){field(name).disabled=!storage;field(name).closest("label").hidden=!storage;}
    for(const name of ["pv_capacity_kw","inverter_efficiency"]){field(name).disabled=!pv;field(name).closest("label").hidden=!pv;}
    for(const name of ["capacity_kWh","energy_kWh","SOC_min","SOC_max"]){field(name).disabled=!storage;}
    field("capacity_kWh").min="0";
    $("strategies").closest("fieldset").hidden=true;$("orientation-controls").hidden=true;
    field("carbon_weight").closest("label").hidden=true;
    $("pv-battery-connection").hidden=!(pv&&storage);field("pv_battery_connection").value="ac_coupled";
    field("weather_source").querySelector('option[value="nsrdb"]').disabled=true;
    $("pv-choice-note").textContent="Choose grid-only, approved non-export PV, or storage without PV. Uncheck battery comparison for a zero-storage case.";
  }
  function defaults(page){if(!active())return;if(page.contains(f("verification"))&&!f("verification").value)f("verification").value="hypothetical_case";const hypothetical=f("verification").value==="hypothetical_case";
    const d=capabilities.comed_simulation.defaults[siteCustomerClass()||"residential"],a=d.account;
    const map={class:a.delivery_class,voltage:a.service_voltage,transformer:a.utility_transformer?"yes":"no",heat:"no",competitive:"no",
      reference:d.regional_account.reference,load_source:d.load.source,operation_reference:"Hypothetical approved non-export operation; standard import tariff and grid charging assumed",
      previous_12_month_peak_kw:a.previous_12_month_peak_kw,previous_calendar_year_peak_kw:a.previous_calendar_year_peak_kw,
      previous_year_months_ge_100kw:a.previous_year_months_ge_100kw,capacity:2,capacity_source:"Synthetic fixed capacity obligation",
      price_mode:"constant_example",price:50,price_source:"Synthetic constant ComEd residual hourly LMP assumption"};
    for(const [name,value] of Object.entries(map)){const input=f(name);if(input&&page.contains(input)&&input.value===""&&value!==undefined&&(hypothetical||["load_source","price","price_source"].includes(name)))input.value=value;}
  }
  function values(){const v=Object.fromEntries(new FormData(form));for(const input of form.querySelectorAll('input[type="checkbox"]'))v[input.name]=input.checked;
    for(const name of [...Object.keys(mainDefaults()),"pv_choice","timestep_minutes","start_date","end_date","tariff_id"])v[name]=field(name)?.value;
    return {...v,site_profile:siteProfile(),site_label:siteLabel||`Coordinates ${field("latitude").value}, ${field("longitude").value}`,native_csv:nativeCsv,price_csv:priceCsv,ess:essResolution,weather_id:weatherId};}
  function request(){if(field("ess_mode").value==="equipment"&&batteryEnabled()&&!essResolution?.ready)throw new Error("Review and apply ESS equipment first.");return buildComedSimulationRequest(capabilities.comed_simulation.defaults[siteCustomerClass()],values());}
  function validate(page){if(!active())return true;
    try{
      if(page.dataset.step==="3") {const start=field("start_date").value,end=field("end_date").value;if(!["2026-09-01","2026-10-01"].includes(start)||end!==({"2026-09-01":"2026-09-30","2026-10-01":"2026-10-31"}[start]))throw new Error("Use one complete September or October 2026 calendar month.");}
      if(page.dataset.step==="9"&&field("load_mode").value==="csv"&&(!nativeCsv||!f("native_confirmed").checked))throw new Error("Upload the exact native-load CSV and confirm its basis.");
      const required=page.querySelectorAll('#comed-account input,#comed-account select,#comed-load input,#comed-operating-confirmations input,#comed-hourly input');
      for(const input of required){if(input.disabled||input.closest('[hidden]')||input.type==="file")continue;
        if(input.type==="checkbox"&&!input.checked||input.type!=="checkbox"&&input.value==="")throw new Error("Enter and confirm the relevant ComEd account/source fields, or apply explicitly hypothetical defaults.");}
      if(page.dataset.step==="8") {if(!["comed_BES","comed_BESH"].includes(field("tariff_id").value))throw new Error("Choose ComEd BES or BESH.");if(field("tariff_id").value==="comed_BESH"&&f("price_mode").value==="csv"&&!priceCsv)throw new Error("Upload the complete identified residual hourly price CSV.");}
      return true;
    }catch(e){showError("form-error",e);return false;}
  }
  async function file(name,set,status){const item=f(name).files[0];if(!item){set(null);return;}if(item.size>2*1024*1024){set(null);$(status).textContent="File exceeds 2 MiB.";return;}set(await item.text());$(status).textContent="Loaded "+item.name+" · validated against study timestamps on submission.";}
  f("native_file").addEventListener("change",()=>file("native_file",v=>nativeCsv=v,"comed-native-status"));
  f("price_file").addEventListener("change",()=>file("price_file",v=>priceCsv=v,"comed-price-status"));
  form.addEventListener("change",event=>{
    if(["latitude","longitude","utility","site_type","site_subtype","ce_class","ce_voltage","ce_transformer","ce_competitive","ce_heat","ce_verification"].includes(event.target.name))f("account_confirmed").checked=false;
    if(event.target.name.startsWith("ce_")||event.target.name==="tariff_id"){sync();if(event.target.name==="ce_include_battery")renderWizard();}
  });
  function restore(r){template=structuredClone(defaultSettings());restoreSiteProfile(r.site_profile);lastKind=null;
    resetUtilityOptions("comed");field("utility").value="comed";siteLabel=r.site.label;
    for(const k of ["latitude","longitude"])field(k).value=r.site[k];field("location_query").value=siteLabel;
    for(const k of ["start_date","end_date","timestep_minutes","pv_capacity_kw","weather_source","degradation_cost_per_kWh"])field(k).value=r[k];
    field("include_degradation_in_optimization").checked=r.include_degradation_in_optimization;
    for(const [k,v] of Object.entries(r.solar))field(k).value=v;
    for(const [k,v] of Object.entries(r.battery||{}))field(k).value=v;
    field("load_mode").value=r.load.mode;field("load_power_kw").value=r.load.power_kw??"";field("archetype").value=r.load.archetype??"";
    field("pv_choice").value=r.solar.dc_capacity_kw>0?"yes":r.battery?"storage":"no";f("include_battery").checked=!!r.battery;
    nativeCsv=r.load.csv;priceCsv=r.prices?.csv||null;restoreCandidate(r);weatherId=r.weather_id;sync();
    f("verification").value=r.regional_account.verification_kind;f("reference").value=r.regional_account.reference;
    const a=r.account;f("class").value=a.delivery_class;f("account_confirmed").checked=a.ordinary_import_only_confirmed;
    for(const k of ["previous_12_month_peak_kw","previous_calendar_year_peak_kw","previous_year_months_ge_100kw"])f(k).value=a[k]??"";
    f("voltage").value=a.service_voltage||"";f("transformer").value=a.utility_transformer?"yes":"no";f("heat").value=a.electric_space_heat?"yes":"no";f("competitive").value=a.competitively_declared?"yes":"no";f("watt").value=a.watt_hour_eligibility;f("hv_mkd").value=a.previous_12_month_mkd_kw??"";
    f("load_source").value=r.load.source;f("native_confirmed").checked=r.load.native_basis_confirmed;
    field("tariff_id").value="comed_"+a.supply;f("capacity").value=a.capacity_obligation_kw??"";f("capacity_source").value=a.capacity_source??"";
    if(r.prices){f("price_mode").value=r.prices.mode;f("price").value=r.prices.usd_per_mwh??"";f("price_source").value=r.prices.source;f("price_confirmed").checked=r.prices.basis_confirmed;}
    for(const [key,target] of [["interconnection_confirmed","nonexport"],["standard_tariff_confirmed","standard"],["grid_charging_confirmed","grid_charge"]])f(target).checked=r.operating_contract[key];f("operation_reference").value=r.operating_contract.reference;
    updateSiteControls();resetWizard();
  }
  window.comedUI={active,batteryEnabled,sync,leaving,defaults,mainDefaults,validate,restore,request,
    reset:()=>{nativeCsv=priceCsv=null;lastKind=null;},
    submit:()=>api("/api/v1/comed/simulations?draft=1",request())};
}
