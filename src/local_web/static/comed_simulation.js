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
  delete r.billing_cycles;
  if(v.ce_cycle_mode==="meter_cycles") {
    if(v.ce_cycles_json?.trim())r.billing_cycles=JSON.parse(v.ce_cycles_json);
    else r.billing_cycles=[{start_date:r.start_date,end_date:r.end_date,billing_month:v.ce_billing_month,
      kind:v.ce_cycle_kind||"regular",source:v.ce_cycle_source,
      charge_factors:v.ce_cycle_kind==="short_service"?JSON.parse(v.ce_charge_factors||"{}"):null}];
    r.account.billing_month=r.billing_cycles[0]?.billing_month;
  } else if(v.ce_cycle_mode==="calendar_year") {
    const year=Number(r.start_date.slice(0,4));
    if(r.start_date!==`${year}-01-01`||r.end_date!==`${year}-12-31`)throw new Error("A calendar-year study requires January 1 through December 31 of the same year.");
    r.billing_cycles=Array.from({length:12},(_,m)=>({
      start_date:`${year}-${String(m+1).padStart(2,"0")}-01`,
      end_date:new Date(Date.UTC(year,m+1,0)).toISOString().slice(0,10),
      billing_month:`${year}-${String(m+1).padStart(2,"0")}-01`,kind:"regular",charge_factors:null,
      source:"Hypothetical calendar-designated billing cycle; not an actual utility meter-reading schedule"}));
  }
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
      csv:["csv","pjm_csv"].includes(v.ce_price_mode)?v.price_csv:null};
    if(v.ce_price_mode==="pjm_csv")r.prices.pjm_metadata={market:"REAL_TIME_HOURLY",
      source_url:"https://dataminer2.pjm.com/feed/rt_hrl_lmps",retrieved_at:v.ce_price_retrieved_at,
      unit:"$/MWh",usage_permission:"internal_use_only"};
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
function comedBillingMonths(capabilities, supply) {
  return capabilities.comed_simulation.billing_months_by_supply?.[supply]
    || capabilities.comed.billing_months_by_supply?.[supply]
    || capabilities.comed_simulation.billing_months || capabilities.comed.billing_months;
}
if(typeof module!=="undefined")module.exports={buildComedSimulationRequest,comedBillingMonths};

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
  const cycles=document.createElement("fieldset");cycles.id="comed-cycles";cycles.hidden=true;
  cycles.innerHTML=`<legend>ComEd billing cycle</legend>
    <label>Billing period basis<select name="ce_cycle_mode"><option value="calendar_month">Calendar-month study</option><option value="calendar_year">Full calendar-year study · hypothetical billing cycles</option><option value="meter_cycles">Documented utility meter cycle(s)</option></select></label>
    <div id="comed-cycle-details"><label>Utility-designated billing month<select name="ce_billing_month"></select></label>
    <label>Cycle type<select name="ce_cycle_kind"><option value="regular">Regular cycle · monthly charges once</option><option value="short_service">Shortened first/final service bill · documented allocations</option></select></label>
    <label>Cycle designation and allocation source<input name="ce_cycle_source" maxlength="500" placeholder="Bill/cycle schedule, or explicitly hypothetical study; omit identifiers"/></label>
    <label id="comed-allocation">Short-service charge factors · JSON<textarea name="ce_charge_factors" placeholder='{"customer":0.5,"standard_metering":0.5,"low_income_discount_recovery":0.5}'></textarea></label>
    <details><summary>Advanced: consecutive billing-cycle list</summary><label>Cycle list · JSON<textarea name="ce_cycles_json" placeholder="Optional documented cycles; include start_date, end_date, billing_month, kind, source, charge_factors for each"></textarea></label></details></div>
    <p class="hint">Start date is the first service day after the previous meter read; end date includes the current read day. The utility billing month is a separate designation. Calendar boundaries do not automatically split monthly rates or demand peaks. Include every study interval; missing records are not a partial bill. Short-service factors must come from documented billing rules or bill allocations; no days/30 assumption is made.</p>`;
  document.querySelector('[data-step="3"]').append(cycles);
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
    <label>ComEd-zone residual hourly LMP source<select name="ce_price_mode"><option value="constant_example">Explicit synthetic constant assumption</option><option value="csv">Identified hourly CSV · observed or synthetic</option><option value="pjm_csv">Official PJM hourly CSV · COMED_RESID_AGG</option></select></label>
    <label id="comed-price-constant">Synthetic residual LMP · USD/MWh<input name="ce_price" type="number" step="any"/></label>
    <label id="comed-price-file"><span id="comed-price-format">Hourly price CSV · timestamp,residual_lmp_usd_per_mwh</span><input name="ce_price_file" type="file" accept=".csv,text/csv"/></label>
    <label id="comed-price-retrieved">PJM file retrieval time · ISO timestamp with UTC offset<input name="ce_price_retrieved_at" maxlength="60" placeholder="2026-10-13T18:00:00Z"/></label>
    <label>Hourly price source or synthetic assumption<input name="ce_price_source" maxlength="500"/></label>
    <label><input name="ce_price_confirmed" type="checkbox"/> Verified COMED PJM real-time residual hourly LMP in USD/MWh at interval starts, or an explicitly synthetic assumption. No hub, day-ahead or adjusted-retail substitution.</label>
    <p id="comed-price-status" class="hint">Official PJM files must include UTC interval starts, node 116472935 / COMED_RESID_AGG, RESIDUAL_METERED_EDC, native blank zone, prices and revision fields. At most 8 MiB; normalized two-column CSVs at most 2 MiB. Prices stay local; no automatic market API download. Capacity is fixed across scenarios.</p></div>
    <p class="hint" id="comed-verified-months">Only the engine's listed verified billing months are supported; historical gaps reject explicitly. Calendar studies and documented meter cycles are supported. America/Chicago boundaries. Commercial demand uses aligned 30-minute averages from 15/30-minute records, weekday 09:00–18:00 excluding NERC holidays. Excluded taxes and fees remain visible in results.</p>`;
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
    for(const panel of [account,cycles,load,operation,pricing]){panel.hidden=!on;for(const c of panel.querySelectorAll("input,select,textarea"))c.disabled=!on;}
    // Regional adapters share this native-load selector and own its value.
    if(!on&&window.regionalUI?.active()){lastKind=null;return;}
    const csvOption=field("load_mode").querySelector('option[value="csv"]');csvOption.disabled=csvOption.hidden=!on;
    if(!on){if(field("load_mode").value==="csv")field("load_mode").value="";lastKind=null;return;}
    wasActive=true;
    const supply=field("tariff_id").value==="comed_BESH"?"BESH":"BES";
    const months=comedBillingMonths(capabilities,supply);
    f("cycle_mode").querySelector('option[value="meter_cycles"]').disabled=!capabilities.comed_simulation.billing_cycle_support;
    f("cycle_mode").querySelector('option[value="calendar_year"]').disabled=!capabilities.comed_simulation.annual_calendar_support;
    if(!capabilities.comed_simulation.billing_cycle_support)f("cycle_mode").value="calendar_month";
    if([...f("billing_month").options].slice(1).map(o=>o.value).join()!==months.join()){
      const previous=f("billing_month").value;
      f("billing_month").replaceChildren(option("","Choose confirmed billing month…"),...months.map(m=>option(m,m.slice(0,7))));
      f("billing_month").value=months.includes(previous)?previous:"";
    }
    $("comed-cycle-details").hidden=f("cycle_mode").value!=="meter_cycles";
    $("comed-allocation").hidden=f("cycle_kind").value!=="short_service";
    field("timezone").value="America/Chicago";
    $("comed-rate-source").href=capabilities.comed.source_url;
    const kind=commercial?"commercial":"residential";
    if(lastKind!==kind){const classes=capabilities.comed[kind+"_classes"];f("class").replaceChildren(option("","Choose confirmed delivery class…"),...classes.map(c=>option(c,c.replaceAll("_"," "))));lastKind=kind;}
    $("comed-commercial").hidden=!commercial;$("comed-watt").hidden=!commercial||f("class").value!=="watt_hour";$("comed-hv").hidden=!commercial||f("class").value!=="high_voltage";
    for(const opt of field("tariff_id").options){opt.hidden=opt.disabled=!opt.value.startsWith("comed_")&&opt.value!=="__unset__";}
    for(const supply of ["BES","BESH"]){if(!field("tariff_id").querySelector(`option[value="comed_${supply}"]`))field("tariff_id").append(option("comed_"+supply,"ComEd "+supply+(supply==="BES"?" · eligible fixed supply":" · Hourly Pricing")));const o=field("tariff_id").querySelector(`option[value="comed_${supply}"]`);o.hidden=o.disabled=false;}
    $("fixed-price-label").hidden=true;$("price-note").textContent="ComEd modeled subtotal, with fixed account charges, signed riders and applicable distribution/transformer demand. Excludes state excise tax, municipal taxes and franchise fees.";
    $("comed-hourly").hidden=field("tariff_id").value!=="comed_BESH";
    f("price_mode").querySelector('option[value="pjm_csv"]').disabled=!capabilities.comed_simulation.pjm_file_support;
    $("comed-price-constant").hidden=f("price_mode").value!=="constant_example";$("comed-price-file").hidden=f("price_mode").value==="constant_example";
    $("comed-price-retrieved").hidden=f("price_mode").value!=="pjm_csv";
    $("comed-price-format").textContent=f("price_mode").value==="pjm_csv"?"Original PJM Data Miner real-time hourly CSV · retain all columns":"Hourly price CSV · timestamp,residual_lmp_usd_per_mwh";
    $("comed-native-file").hidden=field("load_mode").value!=="csv";
    field("load_power_kw").closest("label").hidden=field("load_mode").value==="csv";field("load_power_kw").disabled=field("load_mode").value==="csv";
    $("archetype-label").hidden=field("load_mode").value!=="synthetic";
    const coverage=months.map(m=>m.slice(0,7)).join(", ");
    $("comed-verified-months").textContent=`Verified ${supply} billing months: ${coverage}. Gaps remain unsupported. America/Chicago boundaries; documented cycles may cross calendar months. Commercial demand uses aligned 30-minute averages, weekday 09:00–18:00 excluding NERC holidays. Excluded taxes and fees remain visible in results.`;
    $("dataset-info").textContent=`Verified billing months: ${coverage}. Supply complete native loads; meter purchases may differ at PV/storage sites.`;
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
    field("weather_source").querySelector('option[value="nsrdb"]').disabled=!capabilities.comed_simulation.historical_weather_support;
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
      if(page.dataset.step==="3") {const start=field("start_date").value,end=field("end_date").value;
        if(f("cycle_mode").value==="calendar_month") {
          if(!comedBillingMonths(capabilities,field("tariff_id").value==="comed_BESH"?"BESH":"BES").includes(start)||end!==new Date(Date.UTC(Number(start.slice(0,4)),Number(start.slice(5,7)),0)).toISOString().slice(0,10))throw new Error("Use one complete verified billing month for this supply plan, or select documented meter cycles.");
        } else if(f("cycle_mode").value==="calendar_year") {
          const year=start.slice(0,4),months=comedBillingMonths(capabilities,field("tariff_id").value==="comed_BESH"?"BESH":"BES");
          if(start!==`${year}-01-01`||end!==`${year}-12-31`||!Array.from({length:12},(_,i)=>`${year}-${String(i+1).padStart(2,"0")}-01`).every(m=>months.includes(m)))throw new Error("Use one complete calendar year with all twelve verified billing months; cycles are hypothetical calendar designations.");
        } else if(!f("cycles_json").value.trim()&&(!f("billing_month").value||!f("cycle_source").value.trim()))throw new Error("Confirm the utility billing month and cycle source; do not infer it from calendar dates.");
      }
      if(page.dataset.step==="9"&&field("load_mode").value==="csv"&&(!nativeCsv||!f("native_confirmed").checked))throw new Error("Upload the exact native-load CSV and confirm its basis.");
      const required=page.querySelectorAll('#comed-account input,#comed-account select,#comed-load input,#comed-operating-confirmations input,#comed-hourly input');
      for(const input of required){if(input.disabled||input.closest('[hidden]')||input.type==="file")continue;
        if(input.type==="checkbox"&&!input.checked||input.type!=="checkbox"&&input.value==="")throw new Error("Enter and confirm the relevant ComEd account/source fields, or apply explicitly hypothetical defaults.");}
      if(page.dataset.step==="8") {if(!["comed_BES","comed_BESH"].includes(field("tariff_id").value))throw new Error("Choose ComEd BES or BESH.");if(field("tariff_id").value==="comed_BESH"&&["csv","pjm_csv"].includes(f("price_mode").value)&&!priceCsv)throw new Error("Upload the complete identified residual hourly price CSV.");}
      return true;
    }catch(e){showError("form-error",e);return false;}
  }
  async function file(name,set,status){const item=f(name).files[0];if(!item){set(null);return;}const limit=name==="price_file"&&f("price_mode").value==="pjm_csv"?8:2;if(item.size>limit*1024*1024){set(null);$(status).textContent=`File exceeds ${limit} MiB.`;return;}set(await item.text());$(status).textContent="Loaded "+item.name+" · validated against study timestamps on submission.";}
  f("native_file").addEventListener("change",()=>file("native_file",v=>nativeCsv=v,"comed-native-status"));
  f("price_file").addEventListener("change",()=>file("price_file",v=>priceCsv=v,"comed-price-status"));
  form.addEventListener("change",event=>{
    if(["latitude","longitude","utility","site_type","site_subtype","ce_class","ce_voltage","ce_transformer","ce_competitive","ce_heat","ce_verification"].includes(event.target.name))f("account_confirmed").checked=false;
    if(event.target.name.startsWith("ce_")||event.target.name==="tariff_id"){sync();if(event.target.name==="ce_include_battery")renderWizard();}
    if(event.target.name==="ce_price_mode"){priceCsv=null;f("price_file").value="";f("price_confirmed").checked=false;}
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
    f("cycle_mode").value=r.billing_cycles?"meter_cycles":"calendar_month";
    const cycle=r.billing_cycles?.[0];f("billing_month").value=cycle?.billing_month||"";
    f("cycle_kind").value=cycle?.kind||"regular";f("cycle_source").value=cycle?.source||"";
    f("charge_factors").value=cycle?.charge_factors?JSON.stringify(cycle.charge_factors):"";
    f("cycles_json").value=r.billing_cycles?.length>1?JSON.stringify(r.billing_cycles,null,2):"";
    const a=r.account;f("class").value=a.delivery_class;f("account_confirmed").checked=a.ordinary_import_only_confirmed;
    for(const k of ["previous_12_month_peak_kw","previous_calendar_year_peak_kw","previous_year_months_ge_100kw"])f(k).value=a[k]??"";
    f("voltage").value=a.service_voltage||"";f("transformer").value=a.utility_transformer?"yes":"no";f("heat").value=a.electric_space_heat?"yes":"no";f("competitive").value=a.competitively_declared?"yes":"no";f("watt").value=a.watt_hour_eligibility;f("hv_mkd").value=a.previous_12_month_mkd_kw??"";
    f("load_source").value=r.load.source;f("native_confirmed").checked=r.load.native_basis_confirmed;
    field("tariff_id").value="comed_"+a.supply;f("capacity").value=a.capacity_obligation_kw??"";f("capacity_source").value=a.capacity_source??"";
    if(r.prices){f("price_mode").value=r.prices.mode;f("price").value=r.prices.usd_per_mwh??"";f("price_source").value=r.prices.source;f("price_confirmed").checked=r.prices.basis_confirmed;f("price_retrieved_at").value=r.prices.pjm_metadata?.retrieved_at||"";}
    for(const [key,target] of [["interconnection_confirmed","nonexport"],["standard_tariff_confirmed","standard"],["grid_charging_confirmed","grid_charge"]])f(target).checked=r.operating_contract[key];f("operation_reference").value=r.operating_contract.reference;
    updateSiteControls();resetWizard();
  }
  window.comedUI={active,batteryEnabled,sync,leaving,defaults,mainDefaults,validate,restore,request,
    reset:()=>{nativeCsv=priceCsv=null;lastKind=null;f("cycle_mode").value="calendar_month";f("cycles_json").value="";},
    submit:()=>api("/api/v1/comed/simulations?draft=1",request())};
}
