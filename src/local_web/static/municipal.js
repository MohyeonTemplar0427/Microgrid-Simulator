"use strict";
// Account-specific controls embedded in the common nine-step wizard.
(() => {
  let caps, resolution=null, revision=0, csvText=null;
  const shared=new Set(['name','latitude','longitude','utility','start_date','end_date','capacity_kWh','energy_kWh','max_charge_kw','max_discharge_kw','SOC_min','SOC_max','charge_efficiency','discharge_efficiency','degradation_cost_per_kWh']);
  const f=name=>field(shared.has(name)?name:'m_'+name);
  const el=id=>document.getElementById(id);
  const active=()=>['amp','svp'].includes(field('utility').value);
  const page=i=>form.querySelector(`.wizard-page[data-step="${i}"]`);
  function panel(i,html){
    const box=document.createElement('div');box.dataset.municipal='';box.hidden=true;
    box.innerHTML=html;
    for(const input of box.querySelectorAll('[name]'))input.name='m_'+input.name;
    page(i).append(box);return box;
  }
  panel(2,`      <label>Service mode<select name="mode"><option value="actual_service">Actual confirmed account</option><option value="alternative_location">Hypothetical alternative location</option></select></label>
      <p class="hint" id="municipal-mode-note"></p>
      <p class="hint" id="municipal-generation"></p>
      <div id="municipal-evidence"><label>Service evidence<select name="evidence_type"><option value="electricity_bill">Electricity bill</option><option value="utility_confirmation">Utility confirmation</option></select></label>
      <label>Evidence reference · no account numbers<input name="evidence_reference" maxlength="500"></label><label>Confirmation date<input name="confirmed_on" type="date"></label>
      <label class="checkbox"><input name="delivery_confirmed" type="checkbox"> I verified electricity delivery from the stated evidence.</label></div>
<button type="button" class="secondary" id="municipal-resolve">Save account confirmation</button><p id="municipal-resolution" class="hint" role="status"></p>`);
  panel(8,`
      <label hidden>Customer class from Step 2<select name="customer_class"><option value="commercial">Commercial</option><option value="residential">Residential dwelling</option><option value="industrial">Industrial</option></select></label>
      <label>Billing Plan<select name="tariff_id"></select></label><p class="hint" id="municipal-coverage"></p>
      <div class="form-grid"><label>Service phase<select name="phase"><option value="single">Single phase</option><option value="three">Three phase</option></select></label><label>Service voltage<select name="voltage"><option value="secondary">Secondary</option><option value="primary_12kv">12 kV primary</option></select></label></div>
      <label class="checkbox"><input name="rate_confirmed" type="checkbox"> Existing schedule is verified, or explicitly assumed for an alternative-location scenario.</label>
      <label>Schedule confirmation reference<input name="schedule_reference" maxlength="500"></label>
      <label class="checkbox"><input name="scope_confirmed" type="checkbox"> Metered service with no onsite generation, exports, standby requirement or special discount riders.</label>
      <label class="checkbox" id="municipal-tou"><input name="time_of_use" type="checkbox"> Confirmed TOU enrollment and meter (or scenario assumption)</label>
      <label id="municipal-heat">Primary heating<select name="heating_source"><option value="gas_or_other">Gas or other</option><option value="permanent_electric">Permanently installed electric heat</option></select></label>
      <label id="municipal-uut">Alameda utility users tax<select name="uut_status"><option value="standard">Standard · 7.5%</option><option value="reduced_confirmed">Confirmed reduced · 5.5%</option><option value="exempt_confirmed">Confirmed exempt</option></select></label>
      <label class="checkbox"><input name="state_exempt" type="checkbox"> Confirmed state energy surcharge exemption</label>
      <label id="municipal-tax-reference">Tax exemption / reduction reference<input name="tax_reference" maxlength="500"></label>
      <label class="checkbox" id="municipal-primary"><input name="primary_qualified" type="checkbox"> Utility confirms primary-voltage discount qualification, including required transformer ownership.</label>
      <label class="checkbox" id="municipal-secondary"><input name="secondary_approved" type="checkbox"> SVP approves secondary CB-3 service.</label>
      <div id="municipal-pf-state"><label>CB-1 power-factor adjustment state<select name="pf_active"><option value="">Confirm historical state…</option><option value="no">Inactive</option><option value="yes">Active</option></select></label><label>Power-factor state reference<input name="pf_reference" maxlength="500"></label></div>
      <label id="municipal-pf">Monthly power factor · %<input name="power_factor" type="number" min="0" max="100" step="any"></label>
      <label id="municipal-minimum">C-1 minimum-charge connected load · applicable kVA/HP units<input name="minimum_units" type="number" min="0" step="any"><span class="hint">Enter 0 only when no listed connected equipment applies; not the simulated peak.</span></label>
      <div id="municipal-history"><p class="hint">Prior 11 monthly eligible-window demand peaks (kW). Required for SVP's annual ratchet; never inferred from this month's load.</p><div class="form-grid" id="municipal-peak-fields"></div></div>
    <button type="button" class="secondary" id="municipal-check">Check tariff eligibility</button><div id="municipal-eligibility" class="hint" role="status"></div>`);
  panel(9,`<fieldset><legend>Building load</legend>      <label>Native load source<select name="load_mode"><option value="daily_peak">Daily peak assumption</option><option value="constant">Constant assumption</option><option value="csv">Upload 15-minute load CSV</option></select></label>
      <div id="municipal-load-manual"><label>Base load · kW<input name="base_kw" type="number" min="0" step="any"></label><div id="municipal-daily"><label>Daily peak load · kW<input name="peak_kw" type="number" min="0" step="any"></label><div class="form-grid"><label>Peak begins · local hour<input name="peak_start_hour" type="number" min="0" max="23" step="1"></label><label>Peak ends · local hour<input name="peak_end_hour" type="number" min="1" max="24" step="1"></label></div></div></div>
      <label id="municipal-csv" hidden>Load CSV<input name="load_file" type="file" accept=".csv,text/csv"><span class="hint">Exactly timestamp,grid_import_kw columns. Timestamp includes timezone offset. Complete cycle, no PV or export.</span></label><p id="municipal-csv-status" class="hint"></p>
    </fieldset><p class="hint" id="municipal-strategy-note">Compare no battery with cost-optimal storage, including throughput degradation. The battery finishes at its starting energy. No AC network validation is performed.</p>`);
  panel(3,`<p class="hint">Municipal billing requires 15-minute intervals in America/Los_Angeles. AMP: complete 27–33 day cycle. SVP: complete calendar month, within verified coverage.</p><label class="checkbox"><input name="cycle_confirmed" type="checkbox">These are complete billing-cycle boundaries, or explicit scenario assumptions.</label>`);
  panel(4,`<p class="hint">Weather is not used for the supported municipal storage study. Solar and standby billing are not yet implemented for AMP/SVP.</p>`);
  panel(5,`<p class="hint">Onsite generation and exports are unavailable for municipal billing until the applicable standby and settlement rules are implemented. This study uses grid-charged storage only.</p>`);
  panel(7,`<p class="hint">Enter effective battery capacity and power limits manually. Municipal studies currently use these parameters without equipment-catalog or AC network validation.</p>`);
  const legacy=[];
  function legacyNode(node){if(node&&!legacy.includes(node))legacy.push(node);}
  for(const i of [4,5])for(const node of page(i).querySelector('fieldset').children)if(node.tagName!=='LEGEND')legacyNode(node);
  for(const name of ['pv_capacity_kw','inverter_efficiency','tariff_id','carbon_weight'])legacyNode(field(name).closest('label'));
  legacyNode(el('price-note'));legacyNode(field('fixed_price_per_kWh').closest('[data-site]'));
  legacyNode(el('ess-controls'));
  for(const node of page(9).querySelectorAll(':scope > fieldset'))legacyNode(node);
  function sync(){
    if(window.socalUI?.active()){for(const node of form.querySelectorAll("[data-municipal]"))node.hidden=true;window.socalUI.sync();return;}
    const enabled=active();
    for(const node of legacy)node.hidden=enabled;
    for(const node of form.querySelectorAll('[data-municipal]'))node.hidden=!enabled;
    // Restore conditional weather/equipment visibility in the legacy flow.
    if(!enabled){el('clear-sky-settings').hidden=field('weather_source').value!=='clear_sky';el('historical-settings').hidden=field('weather_source').value!=='nsrdb';updateCandidateControls();}
    for(const i of [4,5])page(i).querySelector('.default-actions').hidden=enabled;
    if(enabled){field('ess_mode').value='manual';for(const input of [field('capacity_kWh'),field('energy_kWh'),field('SOC_min'),field('SOC_max'),field('max_charge_kw'),field('max_discharge_kw'),field('charge_efficiency'),field('discharge_efficiency')])input.readOnly=false;}
    update();
    updateEquipmentChoice();
  }
  const batteryLabels={capacity_kWh:1,energy_kWh:1,max_charge_kw:1,max_discharge_kw:1,SOC_min:1,SOC_max:1,charge_efficiency:1,discharge_efficiency:1};
  function rate(){return caps?.tariffs.find(t=>t.id===f('tariff_id').value);}
  function tariffs(saved){
    f("customer_class").value=siteCustomerClass()||"commercial";
    const residential=f('customer_class').value==='residential';
    const choices=(caps?.tariffs||[]).filter(t=>t.utility===f('utility').value && (t.schedule==='D-1')===residential);
    f('tariff_id').replaceChildren(...choices.map(t=>option(t.id,`${t.utility.toUpperCase()} ${t.schedule}`)));
    if(choices.some(t=>t.id===saved)) f('tariff_id').value=saved;
  }
  function peakFields(saved={}) {
    for(const input of el('municipal-peak-fields').querySelectorAll('input')) if(!(input.dataset.month in saved)) saved[input.dataset.month]=input.value;
    el('municipal-peak-fields').replaceChildren();
    if(!f('start_date').value) return;
    const [year,month]=f('start_date').value.split('-').map(Number);
    for(let i=1;i<=11;i++) {
      const d=new Date(Date.UTC(year,month-1-i,1)), key=d.toISOString().slice(0,7);
      const label=document.createElement('label'),input=document.createElement('input');label.textContent=`${key} peak · kW`;
      input.type='number';input.min='0';input.step='any';input.dataset.month=key;input.value=saved[key]??'';label.append(input);el('municipal-peak-fields').append(label);
    }
  }
  function update(){
    const r=rate(),amp=f('utility').value==='amp',s=r?.schedule;
    for(const opt of f('phase').options)opt.disabled=opt.hidden=s==='D-1' && opt.value!=='single';
    for(const opt of f('voltage').options)opt.disabled=opt.hidden=!amp && ['D-1','C-1'].includes(s) && opt.value==='primary_12kv';
    for(const name of ['phase','voltage'])if(f(name).selectedOptions[0]?.disabled)f(name).value='';
    el('municipal-mode-note').textContent=f('mode').value==='actual_service'?'Actual billing requires saved bill/utility-confirmed delivery and account facts.':'Hypothetical alternative-location comparison. This does not establish utility service at the original site.';
    el('municipal-evidence').hidden=f('mode').value!=='actual_service';
    el('municipal-resolve').hidden=f('mode').value!=='actual_service';
    el('municipal-generation').textContent=`Generation provider: ${amp?'Alameda Municipal Power':'Silicon Valley Power'}. No PG&E delivery add-on. Export program: none.`;
    el('municipal-coverage').textContent=r?`Verified coverage: ${r.effective_start} through ${r.verified_through}. Dates outside this range are unsupported.`:'';
    el('municipal-heat').hidden=!(amp&&s==='D-1');el('municipal-uut').hidden=!amp;
    el('municipal-tou').hidden=amp;if(amp) f('time_of_use').checked=false;
    el('municipal-primary').hidden=f('voltage').value!=='primary_12kv';
    el('municipal-secondary').hidden=!(s==='CB-3'&&f('voltage').value==='secondary');
    el('municipal-pf-state').hidden=s!=='CB-1';
    el('municipal-pf').hidden=!(s==='A-3'||s==='CB-3'||s==='CB-1'&&f('pf_active').value==='yes');
    el('municipal-minimum').hidden=s!=='C-1';el('municipal-history').hidden=!(!amp&&r?.demand);
    el('municipal-tax-reference').hidden=!(f('state_exempt').checked||amp&&f('uut_status').value!=='standard');
    el('municipal-load-manual').hidden=f('load_mode').value==='csv';el('municipal-csv').hidden=f('load_mode').value!=='csv';el('municipal-daily').hidden=f('load_mode').value!=='daily_peak';
  }
  function invalidateResolution(){resolution=null;revision++;for(const name of ['scope_confirmed','cycle_confirmed','time_of_use','state_exempt','primary_qualified','secondary_approved'])f(name).checked=false;for(const name of ['schedule_reference','pf_reference','pf_active','power_factor','minimum_units','tax_reference','evidence_reference','confirmed_on'])f(name).value='';for(const input of el('municipal-peak-fields').querySelectorAll('input'))input.value='';f('delivery_confirmed').checked=false;f('rate_confirmed').checked=false;el('municipal-resolution').textContent='Location or account changed. Resolve the location and confirm this account again.';el('municipal-eligibility').textContent='';}
  function acceptResolution(result){resolution=result;el('municipal-resolution').textContent=`${result.status.toUpperCase()} — ${result.explanation}`;}
  function serviceChanged(){invalidateResolution();tariffs();if(locationResolution)acceptResolution(locationResolution);sync();}
  form.addEventListener('input',event=>{
    revision++;el('municipal-eligibility').textContent='';
    const name=event.target.name.replace(/^m_/,'');
    if(['mode','evidence_type','evidence_reference','confirmed_on','delivery_confirmed'].includes(name)){
      resolution=locationResolution;el('municipal-resolution').textContent='Save the updated account confirmation before actual billing.';
    }
    if(name==='customer_class'){tariffs();f('rate_confirmed').checked=false;}
    if(['tariff_id','phase','voltage'].includes(name))f('rate_confirmed').checked=false;
    if(['start_date','end_date'].includes(name))f('cycle_confirmed').checked=false;
    if(name==='start_date')peakFields();sync();
  });
  const numeric=name=>{if(f(name).value==='')throw new Error(`Enter ${name.replaceAll('_',' ')}.`);const v=Number(f(name).value);if(!Number.isFinite(v))throw new Error(`Invalid ${name}.`);return v;};
  function account(){
    const r=rate();if(!r)throw new Error('Choose a rate schedule.');
    if(!f('scope_confirmed').checked||!f('rate_confirmed').checked||!f('cycle_confirmed').checked)throw new Error('Confirm the account scope, assigned rate and complete billing cycle.');
    const ref=f('schedule_reference').value.trim()||(f('mode').value==='alternative_location'?'Explicit alternative-location schedule assumption':'');
    if(!ref)throw new Error('Enter the schedule confirmation reference.');
    const a={customer_class:f('customer_class').value,phase:f('phase').value,voltage:f('voltage').value,metered:true,onsite_generation:false,special_riders:[],billing_cycle_confirmed:true,state_surcharge_exempt:f('state_exempt').checked,confirmed_schedule:r.schedule,schedule_confirmation_reference:ref,time_of_use:f('time_of_use').checked};
    if(a.time_of_use)a.tou_enrollment_confirmed=true;
    if(r.demand)a.demand_interval_minutes=15;
    if(r.utility==='amp')a.uut_status=f('uut_status').value;
    if(r.utility==='amp'&&r.schedule==='D-1')a.heating_source=f('heating_source').value;
    if(a.voltage==='primary_12kv')a.primary_discount_qualified=f('primary_qualified').checked;
    if(r.schedule==='CB-3')a.secondary_service_approved=f('secondary_approved').checked;
    if(r.schedule==='CB-1'){
      if(!f('pf_active').value)throw new Error('Confirm CB-1 power-factor adjustment state.');
      a.power_factor_adjustment_active=f('pf_active').value==='yes';
      a.power_factor_state_reference=f('pf_reference').value.trim()||(f('mode').value==='alternative_location'?'Explicit scenario PF state assumption':'');
      if(!a.power_factor_state_reference)throw new Error('Enter the PF state reference.');
    }
    if(r.schedule==='A-3'||r.schedule==='CB-3'||a.power_factor_adjustment_active)a.monthly_power_factor_percent=numeric('power_factor');
    if(r.schedule==='C-1')a.minimum_charge_load_units=numeric('minimum_units');
    if(r.utility==='svp'&&r.demand){a.previous_11_month_peaks_kw={};for(const input of el('municipal-peak-fields').querySelectorAll('input')){if(input.value==='')throw new Error(`Enter the actual or assumed ${input.dataset.month} peak.`);a.previous_11_month_peaks_kw[input.dataset.month]=Number(input.value);}}
    if(a.state_surcharge_exempt||a.uut_status&&a.uut_status!=='standard'){a.tax_confirmation_reference=f('tax_reference').value.trim();if(!a.tax_confirmation_reference)throw new Error('Enter the tax confirmation reference.');}
    return a;
  }
  function arrangement(){const r=rate();return {delivery_utility:r.utility,generation_provider:r.utility,tariff_id:r.id,export_program:'none'};}
  function savedResolution(){if(!resolution)throw new Error('Resolve electricity service first.');return resolution.resolution_id;}
  function exclusiveEnd(){const d=new Date(`${f('end_date').value}T12:00:00Z`);d.setUTCDate(d.getUTCDate()+1);return d.toISOString().slice(0,10);}
  async function check(){
    const body={interface_version:1,mode:f('mode').value,resolution_id:savedResolution(),arrangement:arrangement(),account:account(),start:f('start_date').value,end:exclusiveEnd()};
    const old=revision, result=await api('/api/v1/municipal/eligibility',body);
    if(old!==revision)throw new Error('Settings changed during eligibility check. Check again.');
    const rows=result.eligibility.map(item=>`${item.tariff.schedule}: ${item.status.replaceAll('_',' ')}${item.reasons.length?' — '+item.reasons.join('; '):''}${item.missing_inputs.length?' — needs '+item.missing_inputs.join(', '):''}`);
    el('municipal-eligibility').textContent=rows.join('\n');
    const chosen=result.eligibility.find(item=>item.tariff.id===body.arrangement.tariff_id);
    if(chosen?.status!=='eligible')throw new Error('Selected tariff is not yet eligible. Review the reasons above.');
  }
  el('municipal-resolve').addEventListener('click',async()=>{
    el('form-error').hidden=true;el('municipal-resolve').disabled=true;
    try{
      const request={latitude:numeric('latitude'),longitude:numeric('longitude')};
      if(f('mode').value==='actual_service'&&f('delivery_confirmed').checked){
        if(!f('evidence_reference').value.trim()||!f('confirmed_on').value)throw new Error('Enter service evidence and confirmation date.');
        request.manual_confirmation={delivery_utility:f('utility').value,evidence_type:f('evidence_type').value,reference:f('evidence_reference').value.trim(),confirmed_on:f('confirmed_on').value};
      }
      const old=revision;el('municipal-resolution').textContent='Resolving official utility territories…';
      const result=await api('/api/v1/utility-resolution',request);
      if(old!==revision)throw new Error('Location settings changed during lookup. Resolve again.');
      resolution=result;el('municipal-resolution').textContent=`${result.status.toUpperCase()} — ${result.explanation} Candidates: ${result.delivery_candidates.map(c=>c.name).join(', ')||'none'}`;
    }catch(error){showError('form-error',error);}finally{el('municipal-resolve').disabled=false;}
  });
  el('municipal-check').addEventListener('click',async()=>{el('form-error').hidden=true;try{await check();}catch(error){showError('form-error',error);}});
  f('load_file').addEventListener('change',async()=>{csvText=null;const file=f('load_file').files[0];if(file){const text=await file.text();if(f('load_file').files[0]!==file)return;csvText=text;el('municipal-csv-status').textContent=`Loaded ${file.name}; interval validation runs before submission.`;}});
  async function submit(){
    await check();
    const battery=gridOnly()?null:Object.fromEntries(Object.keys(batteryLabels).map(k=>[k,numeric(k)]));
    let load;
    if(f('load_mode').value==='csv'){if(!csvText)throw new Error('Choose a load CSV.');load={mode:'csv',csv:csvText};}
    else{load={mode:f('load_mode').value,base_kw:numeric('base_kw')};if(load.mode==='daily_peak')for(const k of ['peak_kw','peak_start_hour','peak_end_hour'])load[k]=numeric(k);}
    return api('/api/v1/municipal/studies',{schema_version:4,carbon:carbonSettings(),grid_only:gridOnly(),site_profile:siteProfile(),name:f('name').value,resolution_id:savedResolution(),mode:f('mode').value,arrangement:arrangement(),account:account(),start_date:f('start_date').value,end_date:f('end_date').value,timezone:field('timezone').value,timestep_minutes:Number(field('timestep_minutes').value),battery:gridOnly()?null:battery,load,degradation_cost_per_kWh:gridOnly()?0:numeric('degradation_cost_per_kWh'),include_degradation_in_optimization:!gridOnly()&&field('include_degradation_in_optimization').checked});
  }
  function validate(page){
    if(!active())return true;
    try{
      const i=Number(page.dataset.step);
      if(i===2){
        if(!resolution)throw new Error('Resolve the Step 2 location first.');
        if(f('mode').value==='actual_service'&&(resolution.status!=='verified'||resolution.delivery_utility!==f('utility').value))throw new Error('Save matching bill or utility confirmation, or explicitly choose a hypothetical scenario.');
      }
      if(i===3){if(field('timestep_minutes').value!=='15'||field('timezone').value!=='America/Los_Angeles')throw new Error('Municipal billing requires 15-minute intervals and America/Los_Angeles.');if(!f('cycle_confirmed').checked)throw new Error('Confirm the complete billing cycle.');}
      if(i===8)account();
      return true;
    }catch(error){showError('form-error',error);return false;}
  }
  function defaults(page){
    if(!active())return;
    // Fill simulation assumptions only. Never fabricate account history or confirmations.
    const residential=siteCustomerClass()==='residential';
    const values={base_kw:residential?1:20,peak_kw:residential?3:90,peak_start_hour:17,peak_end_hour:19};
    for(const [k,v]of Object.entries(values))if(page.contains(f(k))&&!f(k).value)f(k).value=v;
    if(page.dataset.step==='3'){if(!field('timestep_minutes').value)field('timestep_minutes').value='15';if(!field('timezone').value)field('timezone').value='America/Los_Angeles';peakFields();}
  }
  function restore(request){
    fillForm(defaultSettings(),false);
    field('include_degradation_in_optimization').checked=request.include_degradation_in_optimization===true;
    field('pv_choice').value=request.grid_only?'no':'storage';
    restoreSiteProfile(request.site_profile || (request.account.customer_class==='residential'
      ? {site_type:'residential',subtype:null} : {site_type:'commercial',subtype:null}));
    locationGeneration++;clearTimeout(utilityTimer);
    setLocationChoices({...request.resolution,resolution_id:request.resolution_id},request.arrangement.delivery_utility);
    siteLabel=`Coordinates ${request.resolution.coordinates.latitude}, ${request.resolution.coordinates.longitude}`;field('location_query').value=siteLabel;el('location-status').textContent=siteLabel;
    field('timezone').value=request.timezone;field('timestep_minutes').value=request.timestep_minutes;
    csvText=null;f('load_file').value='';el('municipal-peak-fields').replaceChildren();el('municipal-eligibility').textContent='';el('form-error').hidden=true;
    const a=request.account;
    for(const [k,v]of Object.entries({name:request.name,mode:request.mode,latitude:request.resolution.coordinates.latitude,longitude:request.resolution.coordinates.longitude,utility:request.arrangement.delivery_utility,customer_class:a.customer_class,start_date:request.start_date,end_date:request.end_date,phase:a.phase,voltage:a.voltage,heating_source:a.heating_source||'gas_or_other',uut_status:a.uut_status||'standard',schedule_reference:a.schedule_confirmation_reference,pf_reference:a.power_factor_state_reference||'',pf_active:a.power_factor_adjustment_active===true?'yes':'no',power_factor:a.monthly_power_factor_percent??'',minimum_units:a.minimum_charge_load_units??'',tax_reference:a.tax_confirmation_reference||'',degradation_cost_per_kWh:request.degradation_cost_per_kWh,...request.battery}))f(k).value=v;
    for(const [k,v]of Object.entries({rate_confirmed:true,scope_confirmed:true,cycle_confirmed:true,time_of_use:a.time_of_use,state_exempt:a.state_surcharge_exempt,primary_qualified:a.primary_discount_qualified,secondary_approved:a.secondary_service_approved}))f(k).checked=!!v;
    tariffs(request.arrangement.tariff_id);peakFields(a.previous_11_month_peaks_kw||{});
    const manual=request.resolution.manual_confirmation;
    f('delivery_confirmed').checked=!!manual;f('evidence_reference').value=manual?.reference||'';f('confirmed_on').value=manual?.confirmed_on||'';f('evidence_type').value=manual?.evidence_type||'electricity_bill';
    resolution={...request.resolution,resolution_id:request.resolution_id};el('municipal-resolution').textContent=`Saved ${resolution.status} service evidence restored.`;
    const load=request.load;f('load_mode').value=load.mode==='intervals'?'csv':load.mode;
    if(load.mode==='csv')csvText=load.csv;else if(load.mode==='intervals')csvText='timestamp,grid_import_kw\n'+load.intervals.map(r=>`${r.timestamp},${r.grid_import_kw}`).join('\n');
    else for(const k of ['base_kw','peak_kw','peak_start_hour','peak_end_hour'])f(k).value=load[k]??'';
    el('municipal-csv-status').textContent=csvText?'Saved interval inputs restored.':'';revision++;sync();resetWizard();
  }
  function clearLoad(){
    csvText=null;f('load_file').value='';el('municipal-csv-status').textContent='';
    for(const name of ['base_kw','peak_kw','peak_start_hour','peak_end_hour'])f(name).value='';
  }
  function reset(){for(const input of form.querySelectorAll('[name^=m_]')){if(input.type==='checkbox')input.checked=false;else if(input.tagName==='SELECT')input.selectedIndex=0;else input.value='';}csvText=null;el('municipal-csv-status').textContent='';el('municipal-peak-fields').replaceChildren();invalidateResolution();sync();}
  window.municipalUI={clearLoad,reset,active,sync,serviceChanged,invalidateResolution,acceptResolution,validate,defaults,submit,restore,init(all){caps=all.municipal;tariffs();sync();}};
  if(typeof capabilities!=='undefined'&&capabilities)window.municipalUI.init(capabilities);
})();
