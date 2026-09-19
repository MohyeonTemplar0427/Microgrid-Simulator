"use strict";
// Southern California account controls in the existing shared wizard.
(() => {
 const active=()=>!!capabilities?.socal && ['ladwp','sce'].includes(field('utility').value);
 const f=n=>field('sc_'+n), page=n=>form.querySelector(`.wizard-page[data-step="${n}"]`);
 let savedResolution=null, lastChoice='', loadCsv=null, confirmationRevision=0, wasActive=false;
 const previousHidden=new Map();
 function panel(step,markup){const n=document.createElement('div');n.dataset.socal='';n.hidden=true;n.innerHTML=markup;for(const e of n.querySelectorAll('[name]'))e.name='sc_'+e.name;page(step).append(n);return n;}
 const input=(name,label,type='number')=>`<label>${label}<input name="${name}" type="${type}" ${type==='number'?'step="any"':''}></label>`;
 panel(2,`<label>Billing comparison<select name="mode"><option value="actual_service">Actual confirmed account</option><option value="hypothetical_bundled">Hypothetical bundled comparison</option></select></label>
 <label>Generation provider<select name="generation"><option value="">Choose from your bill…</option><option value="bundled">Delivery utility's bundled generation</option><option value="cca">CCA generation · billing not yet supported</option></select></label>
 <p id="socal-generation" class="hint"></p>${input('reference','Bill or utility confirmation reference · omit account numbers','text')}
 <label class="checkbox"><input name="delivery_confirmed" type="checkbox">I verified the delivery utility on my bill or with the utility.</label>
 <button type="button" class="secondary" id="socal-confirm">Save service confirmation</button><p id="socal-resolution" role="status" class="hint"></p>`);
 panel(3,`<p class="hint">Enter the actual billing-cycle dates. LADWP covers January 2025–September 17, 2026. SCE residential also covers 2025; current SCE coverage is June 25–September 17, 2026. Check the selected Billing Plan for verified date windows. Gaps are rejected.</p>
 ${input('month_factor','Billed month factor · 1 monthly, 2 bimonthly; confirm on bill')}
 <label class="checkbox"><input name="cycle_confirmed" type="checkbox">These dates and the month factor describe a complete bill or explicit study approximation.</label>`);
 panel(4,`<p class="hint">This Southern California candidate uses a local clear-sky estimate with the existing PVWatts, cell-temperature and inverter model (20 °C air, 1 m/s wind, 14% system losses, 96% inverter efficiency and 1.2 DC/AC ratio). It does not substitute historical weather. PV operating savings exclude installation costs and incentives.</p>`);
 panel(5,`${input('pv_kw','PV DC capacity · kW')}${input('tilt','Array tilt · degrees')}${input('azimuth','Array azimuth · degrees')}
 <label>Solar compensation program<select name="solar_program"><option value="none">No solar</option><option value="approved_non_export">Approved non-export PV · curtail surplus</option><option value="nem" disabled>NEM · settlement unsupported</option><option value="nbt" disabled>SCE Solar Billing Plan · settlement unsupported</option></select></label>
 <label class="checkbox"><input name="interconnection_confirmed" type="checkbox">Non-export interconnection and standby exemption are confirmed.</label>`);
 panel(8,`<label>Billing Plan<select name="tariff_id"></select></label><p id="socal-coverage" class="hint"></p>
 <label class="checkbox"><input name="eligibility_confirmed" type="checkbox">Utility confirms this assigned schedule and required qualification history; or these are explicit hypothetical assumptions.</label>
 <label class="checkbox"><input name="ordinary_account_confirmed" type="checkbox">Ordinary account: no CARE/FERA, medical baseline, deed-restricted discount, CPP, EV meter credit, special riders or dedicated residential transformer.</label>
 <label>Voltage<select name="voltage"><option value="secondary">Secondary / SCE below 2 kV</option><option value="ladwp_4.8kv">LADWP 4.8 kV system</option><option value="ladwp_34.5kv">LADWP 34.5 kV system</option></select></label>
 <label>Phase<select name="phase"><option value="single">Single</option><option value="three">Three</option></select></label>
 <div id="socal-ladwp-region"><label>LADWP temperature zone<select name="temperature_zone"><option value="">Confirm…</option><option>1</option><option>2</option></select></label><label>Annual Power Access Charge tier<select name="pac_tier"><option value="">Confirm…</option><option>1</option><option>2</option><option>3</option></select></label>${input('annual_average_kwh','Prior 12-month average energy · kWh/month')}</div>
 <div id="socal-sce-region"><label>SCE baseline region<select name="baseline_region"></select></label><label>Baseline allocation<select name="baseline_type"><option value="basic">Basic</option><option value="all_electric">Utility-approved all electric</option></select></label><label class="checkbox"><input name="heat_pump_water" type="checkbox">Confirmed heat-pump water heater allowance</label></div>
 <label class="checkbox" id="socal-region-confirm"><input name="region_confirmed" type="checkbox">Region is confirmed from bill/utility; utility territory does not establish climate region.</label>
 <label id="socal-prime">PRIME qualifying technology<select name="prime_qualification"><option value="">Confirm…</option><option value="ev">EV</option><option value="battery">Battery</option><option value="heat_pump_water">Heat pump water heating</option><option value="heat_pump_space">Heat pump space heating</option></select></label>
 <div id="socal-commercial"><label class="checkbox"><input name="non_cpp_confirmed" type="checkbox">Confirmed non-CPP enrollment</label><label class="checkbox"><input name="reactive_charge_exempt_confirmed" type="checkbox">Confirmed no reactive-power charge applies</label><label id="socal-history">Previous 11 monthly demand peaks · kW, comma separated<input name="history" type="text"></label></div>
 ${input('local_tax_percent','Local utility tax · percent from your bill')}
 <div id="socal-climate-credit">${input('climate_credit_amount','Climate credit on this bill · $ (optional)')}<label class="checkbox"><input name="climate_credit_confirmed" type="checkbox">This credit appears on this billing statement; apply it once after utility tax.</label></div>
 <label class="checkbox"><input name="tax_confirmed" type="checkbox">I confirmed the local tax jurisdiction/rate or explicitly specified a study assumption.</label>`);
 panel(9,`<fieldset><legend>Building load</legend><label>Load source<select name="load_mode"><option value="daily_peak">Daily load assumption</option><option value="csv">15-minute measured load CSV</option></select></label>${input('base_kw','Base load · kW')}${input('peak_kw','Daily peak load · kW')}${input('peak_start_hour','Peak begins · local hour')}${input('peak_end_hour','Peak ends · local hour')}<label>Load CSV · timestamp,native_load_kw<input name="load_file" type="file" accept=".csv"></label></fieldset><p class="hint">Compare grid-only, PV-only and PV plus storage operating costs. Exports are disabled. Inspect itemized bills and dispatch in the existing result tables.</p>`);
 const override=document.createElement('details');override.className='help';override.innerHTML='<summary>Delivery utility differs from the map</summary><p>Use only a customer bill or utility confirmation. Original map evidence is retained; this does not establish generation enrollment or climate region.</p><label>Bill-confirmed delivery override<select id="socal-override" name="sc_override"><option value="">Choose from your bill…</option><option value="ladwp">LADWP</option><option value="sce">Southern California Edison</option></select></label><button type="button" id="socal-override-select" class="secondary">Configure bill-confirmed override</button>';page(2).append(override);
 $('socal-override-select').addEventListener('click',()=>{const value=$('socal-override').value;if(!value)return;if(![...field('utility').options].some(o=>o.value===value))field('utility').append(option(value,value.toUpperCase()+' · bill confirmation required'));field('utility').value=value;f('mode').value='actual_service';invalidate();updateSiteControls();});
 const hidden=[];
 for(const step of [4,5])for(const n of page(step).querySelector('fieldset').children)if(n.tagName!=='LEGEND')hidden.push(n);
 for(const name of ['pv_capacity_kw','inverter_efficiency','tariff_id','carbon_weight'])hidden.push(field(name).closest('label'));
 hidden.push($('price-note'),$('ess-controls'),field('fixed_price_per_kWh').closest('[data-site]'));
 for(const n of page(9).querySelectorAll(':scope > fieldset'))hidden.push(n);
 function sync(){
  override.hidden=!capabilities?.socal;const on=active();for(const n of form.querySelectorAll('[data-socal]'))n.hidden=!on;
  if(!on){if(wasActive){for(const [node,value] of previousHidden)node.hidden=value;previousHidden.clear();wasActive=false;updateSiteControls();}return;}
  if(!wasActive){for(const n of hidden)previousHidden.set(n,n.hidden);wasActive=true;}
  field('pv_choice').querySelector('option[value="storage"]').disabled=false;
  for(const n of hidden)n.hidden=true;
  for(const step of [4,5])page(step).querySelector('.default-actions').hidden=false;
  field('ess_mode').value='manual';field('timezone').value='America/Los_Angeles';field('timestep_minutes').value='15';
  const choice=field('utility').value+'|'+siteCustomerClass();
  if(choice!==lastChoice){lastChoice=choice;f('tariff_id').replaceChildren(option('','Choose a Billing Plan…'),...capabilities.socal.plans.filter(p=>p.utility===field('utility').value&&p.customer_class===siteCustomerClass()).map(p=>option(p.id,p.label)));savedResolution=null;f('eligibility_confirmed').checked=false;}
  const baseline=f('baseline_region').value;f('baseline_region').replaceChildren(option('','Confirm region…'),...capabilities.socal.baseline_regions.map(x=>option(x,x))); 
  f('baseline_region').value=baseline;
  const p=capabilities.socal.plans.find(x=>x.id===f('tariff_id').value),s=p?.schedule;
  for(const g of ['ladwp-region','sce-region','prime','commercial'])$('socal-'+g).hidden=!(p?.input_groups||[]).includes(g);
  $('socal-region-confirm').hidden=$('socal-ladwp-region').hidden&&$('socal-sce-region').hidden;
  $('socal-history').hidden=field('utility').value!=='ladwp';
  const windows=p?.coverage_windows|| (p?[{start:p.effective_start,end:p.effective_end}]:[]);
  let covered=field('start_date').value;
  for(const w of windows){if(w.start<=covered&&w.end>=covered){const d=new Date(w.end+'T12:00:00Z');d.setUTCDate(d.getUTCDate()+1);covered=d.toISOString().slice(0,10);}}
  const outside=p&&covered<=field('end_date').value;
  $('socal-climate-credit').hidden=field('utility').value!=='sce'||siteCustomerClass()!=='residential';
  $('socal-coverage').textContent=p?`${windows.map(w=>w.start+' through '+w.end).join('; ')} · ${p.tariff_data_version} · ${p.qualification_note||''}${outside?' · Selected dates are outside coverage':''}`:'';
  $('socal-generation').textContent=f('generation').value==='cca'?'CCA billing is unsupported. An explicitly hypothetical bundled comparison uses SCE generation and does not represent your actual bill.':'Confirm generation enrollment separately from delivery.';
 }
 async function confirm(){
  const utility=field('utility').value,reference=f('reference').value.trim();
  if(!reference)throw new Error('Supply service confirmation or hypothetical reference.');
  const body={latitude:Number(field('latitude').value),longitude:Number(field('longitude').value)};
  if(f('mode').value==='hypothetical_bundled'&&locationResolution?.resolution_id){savedResolution=locationResolution;$('socal-resolution').textContent='Saved geographic evidence for an explicitly hypothetical comparison.';return;}
  if(f('mode').value==='actual_service'){
   if(!f('delivery_confirmed').checked)throw new Error('Confirm delivery from your bill or utility.');
   body.manual_confirmation={delivery_utility:utility,evidence_type:'electricity_bill',reference,confirmed_on:new Date().toLocaleDateString('en-CA')};
  }
  const revision=confirmationRevision;const result=await api('/api/v1/utility-resolution',body);
  if(revision!==confirmationRevision||utility!==field('utility').value||body.latitude!==Number(field('latitude').value)||body.longitude!==Number(field('longitude').value))throw new Error('Location changed; confirm again.');
  savedResolution=result;$('socal-resolution').textContent=`${result.status}: ${result.explanation}`;
 }
 function numeric(n){if(f(n).value==='')throw new Error(`Enter ${n.replaceAll('_',' ')}.`);const v=Number(f(n).value);if(!Number.isFinite(v))throw new Error('Invalid '+n);return v;}
 function request(){
  if(!savedResolution)throw new Error('Save service confirmation first.');
  if(!f('generation').value)throw new Error('Select your generation provider.');
  if(f('generation').value==='cca'&&f('mode').value!=='hypothetical_bundled')throw new Error('Actual CCA bills are unsupported; choose an explicitly hypothetical bundled comparison.');
  const a={customer_class:siteCustomerClass(),reference:f('reference').value,generation_provider:field('utility').value,actual_generation_provider:f('generation').value,solar_program:gridOnly()||field('pv_choice').value==='storage'?'none':f('solar_program').value,voltage:f('voltage').value,phase:f('phase').value,local_tax_percent:numeric('local_tax_percent'),billing_month_factor:numeric('month_factor')};
  for(const n of ['eligibility_confirmed','ordinary_account_confirmed','cycle_confirmed','tax_confirmed','region_confirmed','interconnection_confirmed','heat_pump_water','non_cpp_confirmed','reactive_charge_exempt_confirmed'])a[n]=f(n).checked;
  for(const n of ['temperature_zone','baseline_region','baseline_type','prime_qualification'])a[n]=f(n).value;
  a.climate_credit_amount=$('socal-climate-credit').hidden?0:f('climate_credit_amount').value===''?0:numeric('climate_credit_amount');a.climate_credit_confirmed=f('climate_credit_confirmed').checked;
  if(siteCustomerClass()==='residential')a.accommodation=siteProfile().subtype==='apartment_unit'?'multifamily':'single_family';
  a.pac_tier=Number(f('pac_tier').value);a.annual_average_kwh=f('annual_average_kwh').value===''?null:Number(f('annual_average_kwh').value);
  a.previous_11_month_peaks_kw=f('history').value.trim()?f('history').value.split(',').map(Number):[];
  const battery=gridOnly()?null:Object.fromEntries(['capacity_kWh','energy_kWh','SOC_min','SOC_max','max_charge_kw','max_discharge_kw','charge_efficiency','discharge_efficiency'].map(k=>[k,Number(field(k).value)]));
  const load=f('load_mode').value==='csv'?{mode:'csv',csv:loadCsv}:{mode:'daily_peak',...Object.fromEntries(['base_kw','peak_kw','peak_start_hour','peak_end_hour'].map(k=>[k,numeric(k)]))};
  return {schema_version:6,name:field('name').value,resolution_id:savedResolution.resolution_id,mode:f('mode').value,tariff_id:f('tariff_id').value,account:a,site_profile:siteProfile(),start_date:field('start_date').value,end_date:field('end_date').value,timezone:'America/Los_Angeles',timestep_minutes:15,load,solar:{capacity_kw:a.solar_program==='none'?0:numeric('pv_kw'),tilt:a.solar_program==='none'?20:numeric('tilt'),azimuth:a.solar_program==='none'?180:numeric('azimuth')},battery,degradation_cost_per_kWh:gridOnly()?0:Number(field('degradation_cost_per_kWh').value)};
 }
 function defaults(p){if(!active())return;const vals={month_factor:1,pv_kw:5,tilt:20,azimuth:180,base_kw:siteCustomerClass()==='residential'?.4:5,peak_kw:siteCustomerClass()==='residential'?2:10,peak_start_hour:16,peak_end_hour:21};for(const [k,v]of Object.entries(vals))if(p.contains(f(k)))f(k).value=v;sync();}
 function invalidate(){confirmationRevision++;savedResolution=null;for(const n of ['eligibility_confirmed','region_confirmed','tax_confirmed','interconnection_confirmed','ordinary_account_confirmed','non_cpp_confirmed','reactive_charge_exempt_confirmed'])f(n).checked=false;$('socal-resolution').textContent='Location or account changed. Confirm again.';}
 function reset(){invalidate();lastChoice='';loadCsv=null;for(const x of form.querySelectorAll('[name^=sc_]')){if(x.type==='checkbox')x.checked=false;else if(x.tagName==='SELECT')x.selectedIndex=0;else x.value='';}}
 function restore(r){
  reset();
  fillForm(defaultSettings(),false);restoreSiteProfile(r.site_profile);field('utility').append(option(r.account.generation_provider,r.account.generation_provider.toUpperCase()));field('utility').value=r.account.generation_provider;
  for(const n of ['name','start_date','end_date'])field(n).value=r[n];field('latitude').value=r.resolution.coordinates.latitude;field('longitude').value=r.resolution.coordinates.longitude;field('location_query').value='';siteLabel='Saved site coordinates';$('location-status').textContent=siteLabel;
  field('pv_choice').value=r.battery?(r.solar.capacity_kw?'yes':'storage'):'no';locationResolution={...r.resolution,resolution_id:r.resolution_id};lastChoice='';sync();
  for(const [k,v]of Object.entries(r.account)){const x=f(k);if(x){if(x.type==='checkbox')x.checked=v;else x.value=v;}}
  f('baseline_region').value=r.account.baseline_region||'';f('month_factor').value=r.account.billing_month_factor;f('history').value=(r.account.previous_11_month_peaks_kw||[]).join(',');f('tariff_id').value=r.tariff_id;f('mode').value=r.mode;f('generation').value=r.account.actual_generation_provider||'bundled';
  for(const [k,v]of Object.entries(r.battery||{}))field(k).value=v;
  for(const k of ['base_kw','peak_kw','peak_start_hour','peak_end_hour'])if(r.load[k]!==undefined)f(k).value=r.load[k];f('load_mode').value=r.load.mode;loadCsv=r.load.csv||null;
  f('pv_kw').value=r.solar.capacity_kw;f('tilt').value=r.solar.tilt;f('azimuth').value=r.solar.azimuth;field('degradation_cost_per_kWh').value=r.degradation_cost_per_kWh;
  savedResolution={...r.resolution,resolution_id:r.resolution_id};$('socal-resolution').textContent='Saved evidence restored · '+r.resolution.status;$('utility-suggestion').textContent=r.resolution.explanation||'Saved location evidence restored.';f('delivery_confirmed').checked=r.resolution.status==='verified';sync();resetWizard();
 }
 form.addEventListener('change',e=>{if(['latitude','longitude','utility','site_type','site_subtype','sc_mode','sc_generation','sc_reference','sc_delivery_confirmed'].includes(e.target.name))invalidate();if(['start_date','end_date','sc_tariff_id'].includes(e.target.name))f('eligibility_confirmed').checked=false;sync();});
 f('load_file').addEventListener('change',async()=>{loadCsv=f('load_file').files[0]?await f('load_file').files[0].text():null;});
 $('socal-confirm').addEventListener('click',async()=>{const button=$('socal-confirm');button.disabled=true;$('form-error').hidden=true;$('socal-resolution').textContent='Saving service evidence…';try{await confirm();}catch(e){showError('form-error',e);}finally{button.disabled=false;}});
 function validatePage(p){if(!active())return true;if(p.dataset.step==='2'&&f('generation').value==='cca'&&f('mode').value==='actual_service'){showError('form-error',new Error('Actual CCA billing is unsupported. Choose a separately labeled hypothetical bundled comparison.'));return false;}if(p.dataset.step==='2'&&!savedResolution){showError('form-error',new Error('Save service confirmation and wait for the evidence status before continuing.'));return false;}return true;}
 window.socalUI={validate:validatePage,active,sync,restore,reset,defaults,invalidate,submit:()=>api('/api/v1/socal/studies',request())};
})();
