/* ══════════════════════════════════════════════════════════
   PMS PORTAL — Complete Application
══════════════════════════════════════════════════════════ */

const App = {
  user: { name: '', employee_id: null },
  currentId: null,
  appraisal: null,    // current full appraisal data
  appraisals: [],
  lineCounter: 0,
  managerReturnId: null,
};

// ── Read injected user data ────────────────────────────────
(function(){
  // Try meta tag first (injected by Odoo controller)
  try {
    const m = document.querySelector('meta[name="pms-user-data"]');
    if (m && m.getAttribute('content')) {
      const d = JSON.parse(m.getAttribute('content'));
      App.user.name        = d.user_name    || '';
      App.user.employee_id = d.employee_id  || null;
    }
  } catch(e) { console.warn('PMS: Could not parse pms-user-data meta tag', e); }
})();

// ── Constants ──────────────────────────────────────────────
const UOM_OPTIONS = [
  {v:'',l:'-- Select --'},{v:'Desc',l:'Description'},{v:'Naira',l:'Naira'},
  {v:'Number',l:'Number(s)'},{v:'Percentage',l:'Percentage(s)'},
  {v:'Day',l:'Day(s)'},{v:'Week',l:'Week(s)'},{v:'Month',l:'Month(s)'},{v:'Others',l:'Others'},
];
const ACCEPTANCE_OPTIONS = [
  {v:'Accepted',l:'Accepted'},{v:'Revised',l:'Revised'},{v:'Dropped',l:'Dropped'},
];
const PROGRESS_OPTIONS = [
  {v:'',l:'-- Select --'},{v:'poor_progress',l:'Poor Progress'},
  {v:'good_progress',l:'Good Progress'},{v:'average_progress',l:'Average Progress'},
];
const CURRENT_ASSESS_OPTIONS = [
  {v:'none',l:'-- Select --'},{v:'Ordinary',l:'Ordinary'},{v:'Diligent',l:'Diligent'},
  {v:'Fantastic',l:'Fantastic'},{v:'Superb',l:'Superb'},
];
const POTENTIAL_ASSESS_OPTIONS = [
  {v:'none',l:'-- Select --'},{v:'Low Potential',l:'Low Potential'},
  {v:'Medium Potential',l:'Medium Potential'},{v:'High Potential',l:'High Potential'},
  {v:'Ready to go',l:'Ready to go'},
];

// ── Helpers ────────────────────────────────────────────────
const esc = s => String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');

function optHtml(opts, selected){
  return opts.map(o=>`<option value="${o.v}" ${o.v===selected?'selected':''}>${o.l}</option>`).join('');
}

function stateBadge(state){
  const map = {
    goal_setting_draft:['bg-yellow','Goal Setting'],
    gs_fa:['bg-blue','Pending FA Approval'],
    hyr_draft:['bg-blue','Mid Year Review'],
    hyr_admin_rating:['bg-purple','HYR Admin'],
    hyr_functional_rating:['bg-purple','HYR Functional'],
    draft:['bg-yellow','Full Appraisal Review'],
    admin_rating:['bg-blue','AA Rating'],
    functional_rating:['bg-blue','FA Rating'],
    reviewer_rating:['bg-purple','Reviewer'],
    wating_approval:['bg-yellow','HR Approval'],
    done:['bg-green','Completed'],
    signed:['bg-green','Signed Off'],
    withdraw:['bg-red','Withdrawn'],
  };
  const [cls,lbl] = map[state]||['bg-gray',state||'Unknown'];
  return `<span class="badge ${cls}"><span class="bdot"></span>${lbl}</span>`;
}

function typeLabel(t){ return {gs:'Goal Setting',hyr:'Mid Year Review',fyr:'Full Appraisal'}[t]||t||'–'; }

// ── Toast ──────────────────────────────────────────────────
function toast(msg, type='info'){
  const icon = {success:'fa-check-circle',error:'fa-exclamation-circle',info:'fa-info-circle'}[type]||'fa-info-circle';
  const el = $(`<div class="toast toast-${type}"><i class="fas ${icon}"></i><span>${msg}</span>
    <button class="toast-dismiss">&times;</button></div>`);
  $('#toast-wrap').append(el);
  el.find('.toast-dismiss').on('click',()=>el.remove());
  setTimeout(()=>el.fadeOut(350,()=>el.remove()),4500);
}

// ── RPC ───────────────────────────────────────────────────
function rpc(url, params){
  params = params || {};
  return $.ajax({
    url: url,
    type: 'POST',
    contentType: 'application/json',
    data: JSON.stringify({jsonrpc:'2.0', method:'call', id:Date.now(), params: params})
  }).then(function(r){
    if(r.error){
      var msg = (r.error.data && r.error.data.message) ? r.error.data.message : (r.error.message || 'Unknown error');
      return $.Deferred().reject(msg).promise();
    }
    return r.result;
  });
}

// ── Navigation ────────────────────────────────────────────
function showPage(key){
  const titles={dashboard:'Dashboard',appraisals:'My Appraisals',detail:'Appraisal Detail','pending-approvals':'Managers Rating',reporting:'Reporting',workforce:'Workforce Planning'};
  $('.page').removeClass('active');
  $('.nav-item').removeClass('active');
  $(`#page-${key}`).addClass('active');
  $(`.nav-item[data-page="${key}"]`).addClass('active');
  $('#topbar-title').text(titles[key]||'PMS Portal');
}

// ── Load appraisals ───────────────────────────────────────
function loadAppraisals(cb){
  rpc('/pms/api/appraisals').then(r=>{
    if(r && r.error){
      toast('Error: '+r.error,'error');
      // Still call cb with empty array so UI updates
      App.appraisals = [];
      if(cb) cb([]);
      return;
    }
    App.appraisals = (r && r.appraisals) ? r.appraisals : [];
    if(cb) cb(App.appraisals);
  }).fail(function(e){
    console.error('PMS API error:', e);
    const msg = (typeof e === 'string') ? e : (e.responseJSON?.error?.data?.message || 'Could not connect to server. Check you are logged in.');
    toast(msg,'error');
    $('#st-total,#st-gs,#st-hyr,#st-done').text('0');
    $('#dash-table').html('<div class="empty-state"><i class="fas fa-exclamation-triangle"></i><p>Failed to load appraisals. Please refresh the page.</p></div>');
    if(cb) cb([]);
  });
}

// ── Render appraisals table ────────────────────────────────
function renderAppraisalsTable(records, cid){
  const $c = $(cid);
  if(!records.length){ $c.html('<div class="empty-state"><i class="fas fa-inbox"></i><p>No appraisal records found.</p></div>'); return; }
  const rows = records.map(r=>`
    <tr>
      <td><button class="btn btn-secondary btn-sm open-appraisal" data-id="${r.id}" style="text-align:left;min-width:180px">${esc(r.name)}</button></td>
      <td>${typeLabel(r.type_of_pms)}</td>
      <td>${stateBadge(r.state)}</td>
      <td>${r.submitted_date||'–'}</td>
      <td><button class="btn btn-primary btn-sm open-appraisal" data-id="${r.id}"><i class="fas fa-eye"></i> Open</button></td>
    </tr>`).join('');
  $c.html(`<table><thead><tr><th>Appraisal</th><th>Type</th><th>Status</th><th>Submitted</th><th></th></tr></thead><tbody>${rows}</tbody></table>`);
}

// ── Dashboard ─────────────────────────────────────────────
function loadDashboard(){
  // Show 0 placeholders immediately while loading
  $('#st-total,#st-gs,#st-hyr,#st-done').text('…');
  loadAppraisals(recs=>{
    $('#st-total').text(recs.length);
    $('#st-gs').text(recs.filter(r=>r.type_of_pms==='gs').length);
    $('#st-hyr').text(recs.filter(r=>r.type_of_pms==='hyr').length);
    $('#st-done').text(recs.filter(r=>['done','signed'].includes(r.state)).length);
    renderAppraisalsTable(recs.slice(0,5),'#dash-table');
  });
}

// ════════════════════════════════════════════════════════════
//  OPEN APPRAISAL DETAIL
// ════════════════════════════════════════════════════════════
function openAppraisal(id){
  App.currentId = id;
  showPage('detail');
  // Reset all sections
  ['#sec-goal-settings','#sec-hyr','#sec-kra','#sec-fc','#sec-lc','#sec-training','#sec-current-assess','#sec-potential-assess'].forEach(s=>$(s).hide());
  $('#section-nav').hide().empty();
  $('#detail-header').html('<div class="loader-wrap"><div class="loader"></div></div>');

  rpc(`/pms/api/appraisal/${id}`).then(r=>{
    if(r.error){
      toast(r.error,'error'); return; 
    }
    App.appraisal = r;
    renderHeader(r);
    renderSections(r);
  }).fail(e=>toast('Failed to load: '+e,'error'));
}

// ── Stage bar ──────────────────────────────────────────────
function renderHeader(r){
  const stages=[
    {key:'goal_setting_draft',lbl:'Goal Setting'},{key:'gs_fa',lbl:'FA Approval'},
    {key:'hyr_draft',lbl:'Mid Year'},{key:'hyr_functional_rating',lbl:'HYR FA'},
    {key:'draft',lbl:'Full Appraisal'},{key:'admin_rating',lbl:'AA Rating'},
    {key:'functional_rating',lbl:'FA Rating'},{key:'reviewer_rating',lbl:'Reviewer'},
    {key:'done',lbl:'Completed'},
  ];
  const order = stages.map(s=>s.key);
  const ci = order.indexOf(r.state);
  const stageHtml = stages.map((s,i)=>{
    const cls = i<ci?'done':(i===ci?'active':'');
    return `<div class="stage ${cls}">${i<ci?'<i class="fas fa-check"></i> ':''} ${s.lbl}</div>`;
  }).join('');
  $('#stage-bar').html(stageHtml);

  $('#detail-header').html(`
    <div class="card-header">
      <div><h3>${esc(r.name)}</h3><div class="card-sub">${typeLabel(r.type_of_pms)} &nbsp;·&nbsp; ${stateBadge(r.state)}</div></div>
    </div>
    <div class="info-grid">
      <div class="info-item"><label>Employee</label><span>${esc(r.employee_name||'–')}</span></div>
      <div class="info-item"><label>Staff ID</label><span>${esc(r.staff_id||'–')}</span></div>
      <div class="info-item"><label>Job Title</label><span>${esc(r.job_title||'–')}</span></div>
      <div class="info-item"><label>Department</label><span>${esc(r.department||'–')}</span></div>
    </div>
    <div class="info-grid">
      <div class="info-item"><label>Submitted</label><span>${r.submitted_date||'Not yet submitted'}</span></div>
      <div class="info-item"><label>Manager</label><span>${esc(r.manager_id||'–')}</span></div>
      <div class="info-item"><label>Supervisor</label><span>${esc(r.administrative_supervisor_id||'–')}</span></div>
      <div class="info-item"><label>Reviewer</label><span>${esc(r.reviewer_id||'–')}</span></div>
    </div>
  `);
}

// ── Decide which sections to show based on state/role ─────
function renderSections(r){
  const st = r.state;
  const isEmp = r.is_employee;
  const isFA = r.is_fa;
  const isAA = r.is_aa;
  const isRev = r.is_reviewer;
  const isManager = isFA || isAA;
  let is_direct_appraisal = r.is_direct_appraisal // no or yes (checks if appraisal is the full appraisal)

  // Section nav shortcuts
  const navItems = [];

  // ── GOAL SETTINGS ──
  if(['goal_setting_draft','gs_fa'].includes(st)){
    $('#sec-goal-settings').show();
    renderGoalSettings(r);
    navItems.push({id:'sec-goal-settings',lbl:'Goal Settings'});
  }

  // ── MID YEAR (HYR) ──
  if(['hyr_draft','hyr_admin_rating','hyr_functional_rating'].includes(st)){
    $('#sec-hyr').show();
    renderHYR(r);
    navItems.push({id:'sec-hyr',lbl:'Mid Year Review'});
  }

  // ── FULL YEAR REVIEW ──
  if(['draft','admin_rating','functional_rating','reviewer_rating','wating_approval','done','signed'].includes(st)){
    $('#sec-kra').show(); 
    renderKRA(r);
    $('#goal-add-line').show();
    
    $('#sec-fc').show();  
    renderFC(r);
    $('#sec-lc').show();  
    renderLC(r);
    $('#sec-training').show(); renderTraining(r);
    $('#sec-current-assess').show(); renderCurrentAssess(r);
    $('#sec-potential-assess').show(); renderPotentialAssess(r);
    navItems.push(
      {id:'sec-kra',lbl:'KRA'},{id:'sec-fc',lbl:'Functional Comp.'},
      {id:'sec-lc',lbl:'Leadership Comp.'},{id:'sec-training',lbl:'Training'},
      {id:'sec-current-assess',lbl:'Current Assess.'},{id:'sec-potential-assess',lbl:'Potential Assess.'}
    );
  }

  // Section nav
  if(navItems.length>1){
    const navHtml = navItems.map(n=>`<button class="snav-btn" data-target="${n.id}">${n.lbl}</button>`).join('');
    $('#section-nav').html(navHtml).show();
  }
}

// ════════════════════════════════════════════════════════════
//  GOAL SETTINGS
// ════════════════════════════════════════════════════════════
function buildGoalRow(line, editable){
  const rid = line.id?`ex-${line.id}`:`nw-${++App.lineCounter}`;
  const dis = editable?'':'readonly';
  const selId = `uom-${rid}`;
  return `
    <tr data-row="${rid}" data-lid="${line.id||''}">
      <td><input type="text" class="kra-input" value="${esc(line.name||'')}" ${dis} placeholder="KRA description…"/></td>
      <td><input type="number" class="wt-input" value="${line.weightage||0}" min="0" max="20" ${dis}/></td>
      <td><select class="uom-sel" id="${selId}" ${editable?'':'disabled'}>${optHtml(UOM_OPTIONS,line.pms_uom||'')}</select></td>
      <td><input type="text" class="tgt-input" value="${esc(line.target||'')}" ${dis} placeholder="e.g. 90%"/></td>
      <td>${editable?`<button class="row-del" title="Remove"><i class="fas fa-trash-alt"></i></button>`:''}</td>
    </tr>`;
}

function renderGoalSettings(r){
  // const editable = r.state==='goal_setting_draft' && r.is_employee;
  console.log("what are state", r.state)
  const editable = ['goal_setting_draft', 'draft'].includes(r.state) && r.is_employee;
  const $body = $('#goal-body').empty();
  App.lineCounter=0;
  (r.goal_lines||[]).forEach(l=>$body.append(buildGoalRow(l,editable)));
  initSelect2('#goal-body .uom-sel');
  updateWBar();

  const $bg = $('#goal-btn-group').empty();
  if(editable){
    $('#goal-add-line').show();
    $bg.append(`
      <button class="btn btn-secondary" id="save-goals-btn"><i class="fas fa-save"></i> Save</button>
      <button class="btn btn-primary" id="submit-gs-btn"><i class="fas fa-paper-plane"></i> Submit Goal Setting to Manager</button>
    `);
  } else if(r.state==='gs_fa'){
    $('#goal-add-line').hide();
    disableGoalTable();
    if(r.is_fa||r.is_aa){
      $bg.append(`
        <button class="btn btn-success" id="approve-gs-btn"><i class="fas fa-check"></i> Approve for Mid Year Review</button>
        <button class="btn btn-warning" id="return-gs-btn"><i class="fas fa-undo"></i> Return to Employee</button>
      `);
    } else {
      $bg.html(`<div class="notice" style="flex:1"><i class="fas fa-clock"></i> Submitted. Awaiting Manager Approval.</div>`);
    }
  } else {
    $('#goal-add-line').hide();
    disableGoalTable();
    $bg.html(`<div class="notice" style="flex:1"><i class="fas fa-lock"></i> Goal settings are locked at this stage.</div>`);
  }
}

function disableGoalTable(){
  $('#goal-table input').prop('readonly',true);
  $('#goal-table select').prop('disabled',true);
}

function updateWBar(){
  let t=0;
  $('#goal-body .wt-input').each(function(){ t+=parseFloat($(this).val())||0; });
  const pct=Math.min(t,100);
  $('#wbar').css('width',pct+'%').toggleClass('over',t>100);
  $('#wbar-lbl').text(`${t} / 100`).css('color',t>100?'var(--danger)':'');
}



function collectGoalLines(){
  const lines=[];
  $('#goal-body tr').each(function(){
    const $r=$(this);
    lines.push({
      id:$r.data('lid')?parseInt($r.data('lid')):null,
      name:$r.find('.kra-input').val().trim(),
      weightage:parseFloat($r.find('.wt-input').val())||0,
      pms_uom:$r.find('.uom-sel').val(),
      target:$r.find('.tgt-input').val().trim(),
    });
  });
  return lines;
}

function validateGoalLines(lines){
  if(!lines.length){ toast('Add at least one Goal Setting line.','error'); return false; }
  // if($('#goal_saved').val() === 'false'){ 
  //   toast('Please click on save goal setting button ','error'); return false; 
  // }

  for(const l of lines){
    if(!l.name){ toast('KRA description is required for all rows.','error'); return false; }
    if(l.weightage<=5){ toast('Weightage must be greater than 0.','error'); return false; }
    if(l.weightage>25){ toast('Individual weightage cannot exceed 25.','error'); return false; }
  }
  const tot=lines.reduce((s,l)=>s+l.weightage,0);
  if(tot>100){ toast(`Total weightage (${tot}) cannot exceed 100.`,'error'); return false; }
  return true;
}

// ════════════════════════════════════════════════════════════
//  MID YEAR REVIEW (HYR)
// ════════════════════════════════════════════════════════════
function renderHYR(r){
  const st = r.state;
  const isManager = r.is_fa||r.is_aa;
  const editable = isManager && ['hyr_draft','hyr_admin_rating','hyr_functional_rating'].includes(st);

  const $body = $('#hyr-body').empty();
  let totWt=0, totRw=0;

  (r.hyr_lines||[]).forEach(l=>{
    totWt += l.weightage||0;
    totRw += l.revise_weightage||0;
    const selId = `hyr-prog-${l.id}`;
    const accId = `hyr-acc-${l.id}`;

    $body.append(`
      <tr data-lid="${l.id}">
        <td><span style="font-size:.83rem">${esc(l.name)}</span></td>
        <td>${l.weightage||0}</td>
        <td>${esc(l.target||'')}</td>
        <td><input type="number" class="hyr-rw" value="${l.revise_weightage||0}" min="0" max="20" style="width:65px" ${editable?'':'readonly'}/></td>
        <td>${esc(l.pms_uom||'')}</td>
        <td><input type="text" class="hyr-rt" value="${esc(l.revise_target||'')}" ${editable?'':'readonly'} style="width:80px"/></td>
        <td>
          ${editable?
            `<select class="hyr-acc-sel" id="${accId}">${optHtml(ACCEPTANCE_OPTIONS,l.acceptance_status||'Accepted')}</select>`
            :`<span>${esc(l.acceptance_status||'')}</span>`}
        </td>
        <td>
          ${editable?
            `<select class="hyr-prog-sel" id="${selId}">${optHtml(PROGRESS_OPTIONS, r.is_fa?l.hyr_fa_rating:l.hyr_aa_rating)}</select>`
            :`<span>${progressLabel(r.is_fa?l.hyr_fa_rating:l.hyr_aa_rating)}</span>`}
        </td>
        <td><textarea class="hyr-comment" style="width:100%;min-height:34px" ${editable?'':'readonly'}>${esc(l.fa_comment||'')}</textarea></td>
      </tr>`);
  });

  $('#hyr-tot-wt').text(totWt);
  $('#hyr-tot-rw').text(totRw);

  if(editable){
    initSelect2('#hyr-body .hyr-prog-sel');
    initSelect2('#hyr-body .hyr-acc-sel');
  }

  const $bg = $('#hyr-btn-group').empty();

  if(editable){
    $bg.append(`<button class="btn btn-secondary" id="save-hyr-btn"><i class="fas fa-save"></i> Save Mid Year Lines</button>`);
  }
  // Employee can submit HYR if in hyr_draft
  if(r.is_employee && st==='hyr_draft'){
    $bg.append(`<button class="btn btn-primary" id="submit-hyr-btn"><i class="fas fa-paper-plane"></i> Submit for Mid Year Review</button>`);
  }
  // Manager submits HYR functional rating
  if((r.is_fa||r.is_aa) && st==='hyr_functional_rating'){
    $bg.append(`<button class="btn btn-success" id="submit-hyr-mgr-btn"><i class="fas fa-check-double"></i> Submit Mid Year Review</button>`);
  }
  if(!$bg.children().length){
    const msg = st==='hyr_draft'?'Mid Year Review is open for manager review.':'Mid Year Review is locked at this stage.';
    $bg.html(`<div class="notice" style="flex:1"><i class="fas fa-info-circle"></i> ${msg}</div>`);
  }
}

function collectHyrLines(){
  const lines=[];
  $('#hyr-body tr').each(function(){
    const $r=$(this); const lid=$r.data('lid');
    lines.push({
      id:parseInt(lid),
      revise_weightage:parseFloat($r.find('.hyr-rw').val())||0,
      revise_target:$r.find('.hyr-rt').val().trim(),
      acceptance_status:$r.find('.hyr-acc-sel').length?$r.find('.hyr-acc-sel').val():null,
      hyr_fa_rating:$r.find('.hyr-prog-sel').length?$r.find('.hyr-prog-sel').val():null,
      hyr_aa_rating:$r.find('.hyr-prog-sel').length?$r.find('.hyr-prog-sel').val():null,
      fa_comment:$r.find('.hyr-comment').val().trim(),
    });
  });
  return lines;
}

function progressLabel(v){
  return {poor_progress:'Poor Progress',good_progress:'Good Progress',average_progress:'Average Progress'}[v]||v||'–';
}

// ════════════════════════════════════════════════════════════
//  KRA FULL YEAR SECTION
// ════════════════════════════════════════════════════════════
function renderKRA(r){
  const st=r.state;
  const isEmp=r.is_employee;
  const isAA=r.is_aa;
  const isFA=r.is_fa;
  const isRev=r.is_reviewer;
  let is_direct_appraisal = r.is_direct_appraisal // no or yes (checks if appraisal is the full appraisal)

  console.log('WHAR IS KRA STATE', r.state)
  // Determine which columns to show
  const showSelf = true;
  const showAA   = r.has_admin_supervisor;
  const showFA   = true;
  const showRev  = ['reviewer_rating','wating_approval','done','signed'].includes(st);

  let selfEdit = isEmp && st==='draft';
  const aaEdit   = isAA  && st==='admin_rating';
  const faEdit   = isFA  && st==='functional_rating';
  const revEdit  = isRev && st==='reviewer_rating';

  if (isEmp && is_direct_appraisal === 'yes'){
    // open if appraisal without goal settings
    selfEdit = true 
  }
    
  // Build header
  let thHtml = `<th style="width:30%">KRA</th>
  <th>FA(Mid Year) Review</th>
  <th>Weightage</th>`;
  if(showSelf) thHtml += `<th>Self Rating</th>`;
  if(showAA)   thHtml += `<th>AA Rating</th>`;
  if(showFA)   thHtml += `<th>FA Rating</th>`;
  if(showRev)  thHtml += `<th>Reviewer Ratings</th>`;
  $('#kra-thead-row').html(thHtml);

  let totWt=0,
  totSelf=0,
  totAA=0,
  totFA=0,
  totRev=0;
  const $body = $('#kra-body').empty();

  (r.kra_lines||[]).forEach(l=>{
    totWt += l.weightage||0;
    totSelf += l.self_rating||0;
    totAA += l.administrative_supervisor_rating||0;
    totFA += l.functional_supervisor_rating||0;
    totRev += l.reviewer_rating||0;

    let row = `<tr data-lid="${l.id}">
      <td><input type="text" id="kra-line-id" class="kra-name" value="${esc(l.name)}" disabled="${selfEdit ? 'false': 'true'}" placeholder="Enter KRA…"/></td>
      <td>${progressLabel(l.hyr_fa_rating)}</td>
      <td><input type="number" class="weightage-input kra-weightage" value="${l.weightage||0}" min="5" max="25"/></td>`;
    if(showSelf) row += `<td>${selfEdit
      ?`<input type="number" class="rating-input kra-self" value="${l.self_rating||0}" min="1" max="4"/>`
      :`${l.self_rating||0}`}</td>`;
    if(showAA) row += `<td>${aaEdit
      ?`<input type="number" class="rating-input kra-aa" value="${l.administrative_supervisor_rating||0}" min="1" max="4"/>`
      :`${l.administrative_supervisor_rating||0}`}</td>`;
    if(showFA) row += `<td>${faEdit
      ?`<input type="number" class="rating-input kra-fa" value="${l.functional_supervisor_rating||0}" min="1" max="4"/>`
      :`${l.functional_supervisor_rating||0}`}</td>`;
    if(showRev) row += `<td>${revEdit
      ?`<input type="number" class="rating-input kra-rev" value="${l.reviewer_rating||0}" min="1" max="4"/>`
      :`${l.reviewer_rating||0}`}</td>`;

    if(showSelf) row += `<td>${selfEdit && ['draft'].includes(st)
      ?`<button class="row-del-kra" title="Remove"><i class="fas fa-trash-alt"></i></button>`
      // :`${l.self_rating||0}`}</td>`;
      :`<button class="row-dummy-del" title="Remove"><i class="fas fa-trash-alt"></i></button>`}</td>`;

    
    row += '</tr>';
    $body.append(row);
  });


  // Footer totals
  let tfHtml = `<td></td><td></td><td>${totWt}</td>`;
  if(showSelf) tfHtml += `<td>${totSelf}</td>`;
  if(showAA)   tfHtml += `<td>${totAA}</td>`;
  if(showFA)   tfHtml += `<td>${totFA}</td>`;
  if(showRev)  tfHtml += `<td>${totRev}</td>`;
  $('#kra-tfoot-row').html(tfHtml);


  // Buttons

  const $bg = $('#kra-btn-group').empty();
    $("#kra-add-line").hide();

  if(selfEdit && ['draft'].includes(st)){
    $("#kra-add-line").show();
    $bg.append(`
      <button class="btn btn-secondary" id="save-kra-self"><i class="fas fa-save"></i> Save Self Rating</button>
      <button class="btn btn-primary" id="submit-fyr-btn"><i class="fas fa-paper-plane"></i> Submit Full Appraisal Review</button>
    `);
  } else if(aaEdit){
    $bg.append(`
      <button class="btn btn-secondary" id="save-ratings-kra-aa"><i class="fas fa-save"></i> Save AA Rating</button>
      <button class="btn btn-success"   id="submit-aa-btn"><i class="fas fa-check"></i> Submit AA Rating</button>
      <button class="btn btn-danger" id="return-btn"> ↩ Return Appraisal </button>
      
    `);
  } else if(faEdit){
    $bg.append(`
      <button class="btn btn-secondary" id="save-ratings-kra-fa"><i class="fas fa-save"></i> Save FA Rating</button>
      <button class="btn btn-success" id="submit-fa-btn"><i class="fas fa-check"></i> Submit FA Rating</button>
      <button class="btn btn-danger" id="return-btn"> ↩ Return Appraisal </button>
    `);
  } else if(revEdit){
    $bg.append(`
      <button class="btn btn-secondary" id="save-ratings-kra-rev"><i class="fas fa-save"></i> Save Reviewer Rating</button>
      <button class="btn btn-success"   id="submit-rev-btn"><i class="fas fa-check"></i> Submit Reviewer Rating</button>
      <button class="btn btn-danger" id="return-btn"> ↩ Return Appraisal </button>
    `);
  }
}

// ════════════════════════════════════════════════════════════
//  SHARED COMPETENCY SECTION RENDERER (FC / LC)
// ════════════════════════════════════════════════════════════
function renderCompetencySection(r, lines, tableId, theadId, tbodyId, tfootId, sectionKey){
  const st=r.state;
  const isAA=r.is_aa; const isFA=r.is_fa; const isRev=r.is_reviewer;
  const showAA  = r.has_admin_supervisor;
  const showRev = ['reviewer_rating','wating_approval','done','signed'].includes(st);
  const aaEdit  = isAA && st==='admin_rating';
  const faEdit  = isFA && st==='functional_rating';
  const revEdit = isRev && st==='reviewer_rating';

  let thHtml = `<th style="width:38%">Description</th><th>Weightage</th>`;
  if(showAA)  thHtml += `<th>AA Rating</th>`;
  thHtml += `<th>FA Rating</th>`;
  if(showRev) thHtml += `<th>Reviewer Ratings</th>`;
  thHtml += `<th>Section Scale</th><th>Weighted (%) Score</th>`;
  $(theadId).html(thHtml);

  const $body=$(tbodyId).empty();
  let totAA=0,totFA=0,totRev=0,totWScore=0;

  lines.forEach(l=>{
    totAA+=l.administrative_supervisor_rating||0;
    totFA+=l.functional_supervisor_rating||0;
    totRev+=l.reviewer_rating||0;
    totWScore+=l.weighted_score||0;

    let row=`<tr data-lid="${l.id}"><td>${esc(l.name)}</td><td>${l.weightage||0}</td>`;
    if(showAA) row+=`<td>${aaEdit?`<input type="number" class="rating-input comp-aa" value="${l.administrative_supervisor_rating||0}" min="1" max="5"/>`:`${l.administrative_supervisor_rating||0}`}</td>`;
    row+=`<td>${faEdit?`<input type="number" class="rating-input comp-fa" value="${l.functional_supervisor_rating||0}" min="1" max="5"/>`:`${l.functional_supervisor_rating||0}`}</td>`;
    if(showRev) row+=`<td>${revEdit?`<input type="number" class="rating-input comp-rev" value="${l.reviewer_rating||0}" min="1" max="5"/>`:`${l.reviewer_rating||0}`}</td>`;
    row+=`<td>${l.section_avg_scale||5}</td><td>${(l.weighted_score||0).toFixed(2)}</td></tr>`;
    $body.append(row);
  });

  let tfHtml=`<td></td><td></td>`;
  if(showAA)  tfHtml+=`<td>${totAA}</td>`;
  tfHtml+=`<td>${totFA}</td>`;
  if(showRev) tfHtml+=`<td>${totRev}</td>`;
  tfHtml+=`<td></td><td>${totWScore.toFixed(2)}</td>`;
  $(tfootId).html(tfHtml);
}

function renderFC(r){ renderCompetencySection(r,r.fc_lines,'#fc-table','#fc-thead-row','#fc-body','#fc-tfoot-row','fc'); setupCompButtons(r,'fc','#fc-btn-group'); }
function renderLC(r){ renderCompetencySection(r,r.lc_lines,'#lc-table','#lc-thead-row','#lc-body','#lc-tfoot-row','lc'); setupCompButtons(r,'lc','#lc-btn-group'); }

function setupCompButtons(r, sec, groupId){
  const st=r.state;
  const $bg=$(groupId).empty();
  if(r.is_aa && st==='admin_rating'){
    $bg.append(`<button class="btn btn-secondary save-comp-btn" data-sec="${sec}"><i class="fas fa-save"></i> Save AA Rating</button>`);
  } else if(r.is_fa && st==='functional_rating'){
    $bg.append(`<button class="btn btn-secondary save-comp-btn" data-sec="${sec}"><i class="fas fa-save"></i> Save FA Rating</button>`);
  } else if(r.is_reviewer && st==='reviewer_rating'){
    $bg.append(`<button class="btn btn-secondary save-comp-btn" data-sec="${sec}"><i class="fas fa-save"></i> Save Reviewer Rating</button>`);
  }
}


////////////////////////////////////////////////////////////////////

$(document).on('click', '.save-comp-btn', function () {
    const sec = $(this).data('sec');
    const r = App.appraisal;
    const lines = [];
 
    if (sec === 'kra') {
        $('#kra-body tr').each(function () {
            const $row = $(this); const lid = $row.data('lid'); if (!lid) return;
            let line = { id: parseInt(lid), model: sec };
            const aa = $row.find('.kra-aa');
            const fa = $row.find('.kra-fa');
            const rev = $row.find('.kra-rev');
            if (aa.length && !aa.prop('disabled') && !aa.prop('readonly')) { const val = parseInt(aa.val()); if (!isNaN(val)) line.administrative_supervisor_rating = val; }
            if (fa.length && !fa.prop('disabled') && !fa.prop('readonly')) { const val = parseInt(fa.val()); if (!isNaN(val)) line.functional_supervisor_rating = val; }
            if (rev.length && !rev.prop('disabled') && !rev.prop('readonly')) { const val = parseInt(rev.val()); if (!isNaN(val)) line.reviewer_rating = val; }
            lines.push(line);
        });
 
    } else if (['fc', 'lc'].includes(sec)) {
        const tbodyId = sec === 'fc' ? '#fc-body' : '#lc-body';
        $(tbodyId + ' tr').each(function () {
            const $row = $(this); const lid = $row.data('lid'); if (!lid) return;
            let line = { id: parseInt(lid), model: sec };
            const aa = $row.find('.comp-aa');
            const fa = $row.find('.comp-fa');
            const rev = $row.find('.comp-rev');
            if (aa.length && !aa.prop('disabled') && !aa.prop('readonly')) { const val = parseInt(aa.val()); if (!isNaN(val)) line.administrative_supervisor_rating = val; }
            if (fa.length && !fa.prop('disabled') && !fa.prop('readonly')) { const val = parseInt(fa.val()); if (!isNaN(val)) line.functional_supervisor_rating = val; }
            if (rev.length && !rev.prop('disabled') && !rev.prop('readonly')) { const val = parseInt(rev.val()); if (!isNaN(val)) line.reviewer_rating = val; }
            lines.push(line);
        });
 
    } else if (sec === 'training') {
        $('#training-body tr').each(function () {
            const $row = $(this);
            const lid = $row.data('lid');
            lines.push({
                id: lid ? parseInt(lid) : null,   // null = new record, backend creates it
                name: $row.find('.trn-name').val(),
                comments: $row.find('.trn-comment').val(),
                model: sec,
            });
        });
 
    } else if (sec === 'current_assessment') {
        (r.current_assessment || []).forEach(function (assessLine) {
            const $select = $(`#curr-assess-body .curr-assess-sel[data-id="${assessLine.id}"]`);
            const aType = $select.length ? $select.val() : assessLine.assessment_type;
            lines.push({ id: assessLine.id, model: 'current_assessment', assessment_type: aType,
                administrative_supervisor_rating: assessLine.administrative_supervisor_rating || 0,
                functional_supervisor_rating: assessLine.functional_supervisor_rating || 0,
                reviewer_rating: assessLine.reviewer_rating || 0 });
        });
 
    } else if (sec === 'potential_assessment') {
        (r.potential_assessment || []).forEach(function (potLine) {
            const $select = $(`#pot-assess-body .pot-assess-sel[data-id="${potLine.id}"]`);
            const pType = $select.length ? $select.val() : potLine.assessment_type;
            lines.push({ id: potLine.id, model: 'potential_assessment', assessment_type: pType,
                administrative_supervisor_rating: potLine.administrative_supervisor_rating || 0,
                functional_supervisor_rating: potLine.functional_supervisor_rating || 0,
                reviewer_rating: potLine.reviewer_rating || 0 });
        });
    }
 
    const $b = $(this).prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Saving…');
    const origHtml = '<i class="fas fa-save"></i> ' + $(this).text().trim().replace('Saving…', '');
 
    rpc('/pms/api/save-ratings', { appraisal_id: App.currentId, section: sec, lines })
        .then(function (res) {
            if (res.error) {
                toast(res.error, 'error');
                // Do NOT re-render — leave user inputs intact
                return;
            }
 
            toast(res.message, 'success');
 
            if (sec === 'training') {
                // ── FIX: Clear and re-render training from server response ──
                // This prevents duplication caused by newly-created rows
                // (data-lid="") being re-appended on top of server-returned rows.
                if (res.training_lines && res.training_lines.length) {
                    // Re-render in-place using server data (has real IDs now)
                    renderTrainingFromLines(res.training_lines, App.appraisal);
                } else {
                    // Fallback: reload the full appraisal if server didn't return lines
                    openAppraisal(App.currentId);
                }
            }
            // For other sections, no re-render needed on plain save
        })
        .fail(function (e) {
            toast(e, 'error');
        })
        .always(function () {
            $b.prop('disabled', false).html(origHtml);
        });
});
 
 
// ── 2. Add this helper — renders training rows from a lines array ─────────────
// This mirrors renderTraining() but accepts lines directly (no full `r` object needed).
function renderTrainingFromLines(lines, r) {
    const st = r.state;
    const canEdit = (r.is_fa || r.is_aa) && ['functional_rating', 'admin_rating'].includes(st);
 
    // FIX: always empty first — prevents any duplication
    const $body = $('#training-body').empty();
 
    lines.forEach(function (l) {
        $body.append(`
            <tr data-lid="${l.id}">
                <td><input type="text" class="trn-name" value="${esc(l.name || '')}" ${canEdit ? '' : 'readonly'} placeholder="Training description…"/></td>
                <td><textarea class="trn-comment" ${canEdit ? '' : 'readonly'}>${esc(l.comments || '')}</textarea></td>
                <td>${esc(l.requester_name || '–')}</td>
            </tr>`);
    });
}
 
 
// ── 3. Update renderTraining to also use the helper (keeps it DRY) ────────────
// Replace your existing renderTraining function with this:
function renderTraining(r) {
    const st = r.state;
    const canEdit = (r.is_fa || r.is_aa) && ['functional_rating', 'admin_rating'].includes(st);
 
    // Delegate row rendering to the shared helper
    renderTrainingFromLines(r.training_lines || [], r);
 
    if (canEdit) {
        $('#training-add-line').show();
        $('#training-btn-group').html(`<button class="btn btn-secondary save-comp-btn" data-sec="training"><i class="fas fa-save"></i> Save Training</button>`);
    } else {
        $('#training-add-line').hide();
        $('#training-btn-group').empty();
    }
}
 
 
// ── 4. Update training add-line to guard against accidental double-clicks ─────
// Replace the existing #training-add-line click handler with this:
$('#training-add-line').off('click').on('click', function () {
    $('#training-body').append(`
        <tr data-lid="">
            <td><input type="text" class="trn-name" placeholder="Training description…"/></td>
            <td><textarea class="trn-comment" placeholder="Comments…"></textarea></td>
            <td>${App.user.name}</td>
        </tr>`);
});



  //////////////////////////////////////////////////////////////


// ════════════════════════════════════════════════════════════
//  TRAINING
// ════════════════════════════════════════════════════════════
function renderTrainingXX(r){
  const st=r.state;
  const canEdit = (r.is_fa||r.is_aa) && ['functional_rating','admin_rating'].includes(st);
  const $body = $('#training-body').empty();

  (r.training_lines||[]).forEach(l=>{
    $body.append(`
      <tr data-lid="${l.id}">
        <td><input type="text" class="trn-name" value="${esc(l.name||'')}" ${canEdit?'':'readonly'} placeholder="Training description…"/></td>
        <td><textarea class="trn-comment" ${canEdit?'':'readonly'}>${esc(l.comments||'')}</textarea></td>
        <td>${esc(l.requester_name||'–')}</td>
      </tr>`);
  });

  if(canEdit){
    $('#training-add-line').show();
    $('#training-btn-group').html(`<button class="btn btn-secondary save-comp-btn" data-sec="training"><i class="fas fa-save"></i> Save Training</button>`);
  } else {
    $('#training-add-line').hide();
    $('#training-btn-group').empty();
  }
}

// ════════════════════════════════════════════════════════════
//  CURRENT ASSESSMENT
// ════════════════════════════════════════════════════════════
function renderCurrentAssess(r){
  const st=r.state;
  const canEdit=(r.is_fa||r.is_aa)&&['admin_rating','functional_rating','reviewer_rating'].includes(st);
  const $body=$('#curr-assess-body').empty();

  // The current_assessment lines represent rows (AA, FA, Reviewer)
  // But from screenshot, rows are "Assessment By" roles with a dropdown choice
  // We replicate the exact screenshot layout: each row is a rater
  const roleRows=[
    {label:'Administrative Appraiser', field:'administrative_supervisor_rating', isRole:r.is_aa, editState:'admin_rating'},
    {label:'Functional Appraiser',field:'functional_supervisor_rating', isRole:r.is_fa, editState:'functional_rating'},
    {label:'Functional Reviewer',      field:'reviewer_rating',isRole:r.is_reviewer, editState:'reviewer_rating'},
  ];

  // Get existing assessment values from first line (or defaults)
  // const assessLine = (r.current_assessment||[])//[0];
  // const aType = assessLine ? assessLine.assessment_type:'none';

  // roleRows.forEach(role=>{
  //   const rowEditable = role.isRole && st===role.editState;
  //   const selId=`ca-${role.field}`;
  //   $body.append(`
  //     <tr data-role="${role.field}">
  //       <td style="font-weight:500">${role.label}</td>
  //       <td>${rowEditable
  //         ?`<select class="curr-assess-sel" id="${selId}">${optHtml(CURRENT_ASSESS_OPTIONS,aType)}</select>`
  //         :`<span>${aType==='none'?'–':aType}</span>`
  //       }</td>
  //     </tr>`);
  // });
//   (r.current_assessment || []).forEach(function (ca) {

//     const roleEditable =
//         (r.is_aa && st === 'admin_rating') ||
//         (r.is_fa && st === 'functional_rating') ||
//         (r.is_reviewer && st === 'reviewer_rating');

//     const selId = `ca-${ca.id}`;
//     const aType = ca.assessment_type || 'none';

//     $body.append(`
//         <tr data-id="${ca.id}">
//             <td style="font-weight:500">${ca.name}</td>
//             <td>
//                 ${roleEditable
//                     ? `<select class="curr-assess-sel" id="${selId}" data-id="${ca.id}">
//                         ${optHtml(CURRENT_ASSESS_OPTIONS, aType)}
//                        </select>`
//                     : `<span>${aType === 'none' ? '–' : aType}</span>`
//                 }
//             </td>
//         </tr>
//     `);

// });

(r.current_assessment || []).forEach(function (ca) {

    let rowEditable = false;

    if (ca.name === 'Administrative Appraiser')
        rowEditable = r.is_aa && st === 'admin_rating';

    if (ca.name === 'Functional Appraiser')
        rowEditable = r.is_fa && st === 'functional_rating';

    if (ca.name === 'Functional Reviewer')
        rowEditable = r.is_reviewer && st === 'reviewer_rating';

    const selId = `ca-${ca.id}`;
    const aType = ca.assessment_type || 'none';

    $body.append(`
        <tr data-id="${ca.id}">
            <td style="font-weight:500">${ca.name}</td>
            <td>
                ${rowEditable
                    ? `<select class="curr-assess-sel" id="${selId}" data-id="${ca.id}">
                        ${optHtml(CURRENT_ASSESS_OPTIONS, aType)}
                       </select>`
                    : `<span>${aType === 'none' ? '–' : aType}</span>`
                }
            </td>
        </tr>
    `);

});

  if(canEdit) initSelect2('#curr-assess-body .curr-assess-sel');

  const $bg=$('#curr-assess-btn-group').empty();
  if(r.is_aa&&st==='admin_rating') $bg.append(`<button class="btn btn-secondary save-comp-btn" data-sec="current_assessment"><i class="fas fa-save"></i> Save Assessment</button>`);
  if(r.is_fa&&st==='functional_rating') $bg.append(`<button class="btn btn-secondary save-comp-btn" data-sec="current_assessment"><i class="fas fa-save"></i> Save Assessment</button>`);
  if(r.is_reviewer&&st==='reviewer_rating') $bg.append(`<button class="btn btn-secondary save-comp-btn" data-sec="current_assessment"><i class="fas fa-save"></i> Save Assessment</button>`);
}

// ════════════════════════════════════════════════════════════
//  POTENTIAL ASSESSMENT
// ════════════════════════════════════════════════════════════
function renderPotentialAssess(r){
  const st=r.state;
  const canEdit=(r.is_fa||r.is_aa)&&['admin_rating','functional_rating','reviewer_rating'].includes(st);
  const $body=$('#pot-assess-body').empty();

  const roleRows=[
    {label:'Administrative Appraiser', field:'administrative_supervisor_rating', isRole:r.is_aa, editState:'admin_rating'},
    {label:'Functional Appraiser',     field:'functional_supervisor_rating',     isRole:r.is_fa, editState:'functional_rating'},
    {label:'Functional Reviewer',      field:'reviewer_rating',                  isRole:r.is_reviewer, editState:'reviewer_rating'},
  ]; 

  (r.potential_assessment || []).forEach(function (pa) {

      let rowEditable = false;

      if (pa.name === 'Administrative Appraiser')
          rowEditable = r.is_aa && st === 'admin_rating';

      if (pa.name === 'Functional Appraiser')
          rowEditable = r.is_fa && st === 'functional_rating';

      if (pa.name === 'Functional Reviewer')
          rowEditable = r.is_reviewer && st === 'reviewer_rating';

      const selId = `pa-${pa.id}`;
      const pType = pa.assessment_type || 'none';
      $body.append(`
          <tr data-id="${pa.id}">
              <td style="font-weight:500">${pa.name}</td>
              <td>
                  ${rowEditable
                      ? `<select class="pot-assess-sel" id="${selId}" data-id="${pa.id}">
                          ${optHtml(POTENTIAL_ASSESS_OPTIONS, pType)}
                        </select>`
                      : `<span>${pType === 'none' ? '–' : pType}</span>`
                  }
              </td>
          </tr>
      `);

  });

  if(canEdit) initSelect2('#pot-assess-body .pot-assess-sel');

  const $bg=$('#pot-assess-btn-group').empty();
  if(r.is_aa&&st==='admin_rating') $bg.append(`<button class="btn btn-secondary save-comp-btn" data-sec="potential_assessment"><i class="fas fa-save"></i> Save Potential</button>`);
  if(r.is_fa&&st==='functional_rating') $bg.append(`<button class="btn btn-secondary save-comp-btn" data-sec="potential_assessment"><i class="fas fa-save"></i> Save Potential</button>`);
  if(r.is_reviewer&&st==='reviewer_rating') $bg.append(`<button class="btn btn-secondary save-comp-btn" data-sec="potential_assessment"><i class="fas fa-save"></i> Save Potential</button>`);
}

// ════════════════════════════════════════════════════════════
//  PENDING APPROVALS
// ════════════════════════════════════════════════════════════
function loadPendingApprovals(){
  const $c=$('#pending-table').html('<div class="loader-wrap"><div class="loader"></div></div>');
  rpc('/pms/api/pending-approvals').then(r=>{
    const items=r.pending||[];
    if(!items.length){ $c.html('<div class="empty-state"><i class="fas fa-check-double"></i><p>No pending actions.</p></div>'); return; }
    const actionLabel = {
      approve_gs:'Approve Goal Setting', hyr_rating:'HYR Review', hyr_submit:'Submit HYR',
      aa_rating:'AA Rating', fa_rating:'FA Rating', reviewer_rating:'Reviewer Rating',
    };
    const rows=items.map(it=>`
      <tr>
        <td><strong>${esc(it.employee_name)}</strong></td>
        <td>${esc(it.name)}</td>
        <td>${typeLabel(it.type_of_pms)}</td>
        <td>${stateBadge(it.state)}</td>
        <td><span class="badge bg-blue">${actionLabel[it.action_type]||it.action_type}</span></td>
        <td>${it.submitted_date||'–'}</td>
        <td>
          ${it.action_type==='approve_gs'?`
            <button class="btn btn-success btn-sm pending-approve-gs" data-id="${it.id}"><i class="fas fa-check"></i> Approve</button>
            <button class="btn btn-warning btn-sm pending-return-gs" data-id="${it.id}" style="margin-top:4px"><i class="fas fa-undo"></i> Return</button>
            <button class="btn btn-primary btn-sm open-appraisal mb-2" data-id="${it.id}"><i class="fas fa-eye"></i> Open</button>
          `:`<button class="btn btn-primary btn-sm open-appraisal" data-id="${it.id}"><i class="fas fa-eye"></i> Open</button>`}
        </td>
      </tr>`).join('');
    $c.html(`<table><thead><tr>
      <th>Employee</th><th>Appraisal</th><th>Type</th><th>Status</th><th>Action Required</th><th>Submitted</th><th></th>
    </tr></thead><tbody>${rows}</tbody></table>`);
  }).fail(e=>toast('Failed: '+e,'error'));
}

// ════════════════════════════════════════════════════════════
//  COLLECT RATINGS HELPERS
// ════════════════════════════════════════════════════════════
function collectRatingLines(tbodyId, ratingClass){
  const lines=[];
  $(`${tbodyId} tr`).each(function(){
    const $r=$(this); const lid=$r.data('lid');
    if(!lid) return;
    const obj={id:parseInt(lid)};
    obj.self_rating = parseInt($r.find('.kra-self').val())||0;
    obj.administrative_supervisor_rating = parseInt($r.find(`.${ratingClass}-aa, .comp-aa, .kra-aa`).val())||0;
    obj.functional_supervisor_rating = parseInt($r.find(`.${ratingClass}-fa, .comp-fa, .kra-fa`).val())||0;
    obj.reviewer_rating = parseInt($r.find(`.${ratingClass}-rev, .comp-rev, .kra-rev`).val())||0;
    lines.push(obj);
  });
  return lines;
}

// ── Select2 init ──────────────────────────────────────────
function initSelect2(selector){
  $(selector).each(function(){
    if(!$(this).hasClass('select2-hidden-accessible')){
      $(this).select2({width:'100%',minimumResultsForSearch:Infinity});
    }
  });
}

// ════════════════════════════════════════════════════════════
//  REPORTING
// ════════════════════════════════════════════════════════════

const Rpt = {
  data: [],          // full dataset loaded from API
  filtered: [],      // after applying filters
  filterMeta: {      // dropdown options loaded once
    years: [], managers: [], employees: [], departments: []
  },
  metaLoaded: false,
  view: 'cards'      // 'cards' | 'list'
};

// ── Colour helper for score bars ──────────────────────────
function scoreColor(val, max){
  const pct = max > 0 ? val/max : 0;
  if(pct >= 0.75) return '#27AE60';
  if(pct >= 0.5)  return '#F39C12';
  return '#E74C3C';
}

function fmt(v, dp){ return (v === null || v === undefined || isNaN(v)) ? '–' : parseFloat(v).toFixed(dp||1); }

// ── Load reporting meta (filter dropdowns) ────────────────
function loadReportingMeta(){
  return rpc('/pms/api/reporting-meta').then(function(r){
    if(!r) return;
    Rpt.filterMeta = r;

    // Populate year dropdown
    const $yr = $('#rpt-filter-year');
    (r.years||[]).forEach(function(y){
      $yr.append(`<option value="${y.id}">${esc(y.name)}</option>`);
    });
    // Manager dropdown
    const $mgr = $('#rpt-filter-manager');
    (r.managers||[]).forEach(function(m){
      $mgr.append(`<option value="${m.id}">${esc(m.name)}</option>`);
    });
    // Employee dropdown
    const $emp = $('#rpt-filter-employee');
    (r.employees||[]).forEach(function(e){
      $emp.append(`<option value="${e.id}">${esc(e.name)}</option>`);
    });
    // Department dropdown
    const $dept = $('#rpt-filter-dept');
    (r.departments||[]).forEach(function(d){
      $dept.append(`<option value="${d.id}">${esc(d.name)}</option>`);
    });
  }).fail(function(){ /* silently ignore if not accessible */ });
}

// ── Load report data ──────────────────────────────────────
function loadReportingData(filters){
  filters = filters || {};
  $('#rpt-cards-grid').html('<div class="loader-wrap" style="grid-column:1/-1"><div class="loader"></div></div>');
  $('#rpt-list-body').html('<tr><td colspan="14" style="text-align:center;padding:30px"><div class="loader" style="margin:0 auto"></div></td></tr>');
  updateReportSummary([]);

  return rpc('/pms/api/reporting-data', {filters: filters}).then(function(r){
    if(!r || r.error){ toast(r ? r.error : 'Failed to load reporting data','error'); return; }
    Rpt.data = r.records || [];
    Rpt.filtered = Rpt.data;
    renderReportingResults(Rpt.filtered);
  }).fail(function(e){ toast('Reporting error: '+e,'error'); });
}

// ── Apply client-side filters (instant, no re-fetch) ─────
function applyReportFilters(){
  const year  = $('#rpt-filter-year').val();
  const type  = $('#rpt-filter-type').val();
  const state = $('#rpt-filter-state').val();
  const mgr   = $('#rpt-filter-manager').val();
  const emp   = $('#rpt-filter-employee').val();
  const dept  = $('#rpt-filter-dept').val();

  Rpt.filtered = Rpt.data.filter(function(r){
    if(year  && String(r.pms_year_id) !== year)   return false;
    if(type  && r.type_of_pms !== type)            return false;
    if(state && r.state !== state)                 return false;
    if(mgr   && String(r.manager_id) !== mgr)     return false;
    if(emp   && String(r.employee_id) !== emp)     return false;
    if(dept  && String(r.department_id) !== dept)  return false;
    return true;
  });

  renderReportingResults(Rpt.filtered);
}

// ── Render both views + summary ───────────────────────────
function renderReportingResults(records){
  updateReportSummary(records);
  $('#rpt-result-count').text(records.length + ' record' + (records.length===1?'':'s') + ' found');

  if(Rpt.view === 'cards') renderReportCards(records);
  else                     renderReportList(records);
}

// ── Summary strip ─────────────────────────────────────────
function updateReportSummary(records){
  $('#rsum-total').text(records.length);
  if(!records.length){
    $('#rsum-avg-kra,#rsum-avg-lc,#rsum-avg-fc,#rsum-avg-overall').text('–');
    return;
  }
  function avg(field){
    const vals = records.map(r=>parseFloat(r[field])||0);
    return (vals.reduce((a,b)=>a+b,0)/vals.length).toFixed(1);
  }
  $('#rsum-avg-kra').text(avg('final_kra_score'));
  $('#rsum-avg-lc').text(avg('final_lc_score'));
  $('#rsum-avg-fc').text(avg('final_fc_score'));
  $('#rsum-avg-overall').text(avg('overall_score'));
}

// ── CARDS VIEW ────────────────────────────────────────────
function renderReportCards(records){
  const $grid = $('#rpt-cards-grid').empty();

  if(!records.length){
    $grid.html(`<div class="no-results" style="grid-column:1/-1">
      <i class="fas fa-search"></i><p>No appraisals match your filters.</p>
    </div>`);
    return;
  }

  records.forEach(function(r){
    const kra   = fmt(r.final_kra_score);
    const lc    = fmt(r.final_lc_score);
    const fc    = fmt(r.final_fc_score);
    const ca    = fmt(r.current_assessment_score);
    const pa    = fmt(r.potential_assessment_score);
    const total = fmt(r.overall_score);

    // Score bars (assume max 100 for overall, 40 for KRA, 25 each for LC/FC)
    function bar(label, val, max, colorClass){
      const pct = max > 0 ? Math.min((parseFloat(val)||0)/max*100,100) : 0;
      const color = scoreColor(parseFloat(val)||0, max);
      return `<div class="score-bar-row">
        <span>${label}</span>
        <div class="score-bar-track"><div class="score-bar-fill" style="width:${pct}%;background:${color}"></div></div>
        <span>${val}</span>
      </div>`;
    }

    const card = `
      <div class="appr-card open-appraisal" data-id="${r.id}" title="Click to open">
        <div class="appr-card-header">
          <div>
            <div class="appr-card-name">${esc(r.employee_name||'–')}</div>
            <div class="appr-card-meta">
              ${esc(r.department||'–')} &nbsp;·&nbsp; ${esc(r.period||r.name||'–')}
            </div>
          </div>
          <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px">
            ${stateBadge(r.state)}
            <span class="badge bg-gray">${typeLabel(r.type_of_pms)}</span>
          </div>
        </div>
        <div class="appr-card-body">
          <!-- KRA/LC chips -->
          <div class="appr-kra-counts" style="margin-bottom:10px">
            <span class="kra-chip"><i class="fas fa-bullseye"></i> ${r.kra_count||0} KRAs</span>
            <span class="kra-chip lc"><i class="fas fa-users-cog"></i> ${r.lc_count||0} LC</span>
            <span class="kra-chip fc"><i class="fas fa-cogs"></i> ${r.fc_count||0} FC</span>
          </div>
          <!-- Score bars -->
          ${bar('KRA Score', kra, 40, 'primary')}
          ${bar('LC Score',  lc,  25, 'info')}
          ${bar('FC Score',  fc,  25, 'accent')}
          <!-- Score mini-grid -->
          <div class="appr-score-grid" style="margin-top:10px">
            <div class="appr-score-item info"><div class="asv">${ca}</div><div class="asl">Curr.Assess</div></div>
            <div class="appr-score-item acc"><div class="asv">${pa}</div><div class="asl">Potential</div></div>
            <div class="appr-score-item"><div class="asv">${r.manager_name ? esc(r.manager_name.split(' ')[0]) : '–'}</div><div class="asl">Manager</div></div>
          </div>
          <!-- Overall score footer -->
          <div class="appr-overall">
            <span class="appr-overall-lbl"><i class="fas fa-trophy"></i> Overall Score</span>
            <span class="appr-overall-val">${total}</span>
          </div>
        </div>
      </div>`;
    $grid.append(card);
  });
}

// ── LIST VIEW ─────────────────────────────────────────────
function renderReportList(records){
  const $body = $('#rpt-list-body').empty();

  if(!records.length){
    $body.html(`<tr><td colspan="14"><div class="no-results">
      <i class="fas fa-search"></i><p>No appraisals match your filters.</p>
    </div></td></tr>`);
    return;
  }

  records.forEach(function(r){
    $body.append(`<tr>
      <td><strong>${esc(r.employee_name||'–')}</strong></td>
      <td>${esc(r.department||'–')}</td>
      <td>${esc(r.period||r.name||'–')}</td>
      <td>${typeLabel(r.type_of_pms)}</td>
      <td>${stateBadge(r.state)}</td>
      <td style="text-align:center"><strong>${r.kra_count||0}</strong></td>
      <td style="text-align:center"><strong>${r.lc_count||0}</strong></td>
      <td style="text-align:right;font-weight:600">${fmt(r.final_kra_score)}</td>
      <td style="text-align:right;font-weight:600">${fmt(r.final_lc_score)}</td>
      <td style="text-align:right;font-weight:600">${fmt(r.final_fc_score)}</td>
      <td style="text-align:center">${esc(r.current_assessment_score||'–')}</td>
      <td style="text-align:center">${esc(r.potential_assessment_score||'–')}</td>
      <td style="text-align:right;font-weight:800;color:var(--primary);font-size:.95rem">${fmt(r.overall_score)}</td>
      <td><button class="btn btn-primary btn-sm open-appraisal" data-id="${r.id}"><i class="fas fa-eye"></i></button></td>
    </tr>`);
  });
}

// ── Export CSV ────────────────────────────────────────────
function exportReportCSV(records){
  if(!records.length){ toast('No data to export.','info'); return; }
  const cols = ['Employee','Department','Period','Type','Status','KRAs','LC','KRA Score','LC Score','FC Score','Current Assess.','Potential','Overall Score'];
  const rows = [cols.join(',')];
  records.forEach(function(r){
    rows.push([
      '"'+(r.employee_name||'').replace(/"/g,'""')+'"',
      '"'+(r.department||'').replace(/"/g,'""')+'"',
      '"'+(r.period||r.name||'').replace(/"/g,'""')+'"',
      r.type_of_pms||'',
      r.state||'',
      r.kra_count||0,
      r.lc_count||0,
      fmt(r.final_kra_score),
      fmt(r.final_lc_score),
      fmt(r.final_fc_score),
      r.current_assessment_score||'',
      r.potential_assessment_score||'',
      fmt(r.overall_score)
    ].join(','));
  });
  const blob = new Blob([rows.join('\n')], {type:'text/csv'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'pms_report_'+new Date().toISOString().slice(0,10)+'.csv';
  a.click();
  URL.revokeObjectURL(a.href);
}

// ── Init reporting page (called once on first open, then on each open) ──
function initReportingPage(){
  // Load meta dropdowns only once
  const metaPromise = Rpt.metaLoaded
    ? $.Deferred().resolve().promise()
    : loadReportingMeta().then(function(){ Rpt.metaLoaded = true; });

  metaPromise.always(function(){
    // Only fetch data if not yet loaded
    if(Rpt.data.length === 0){
      loadReportingData({});
    } else {
      renderReportingResults(Rpt.filtered);
    }
  });
}


// ════════════════════════════════════════════════════════════
//  WORKFORCE PLANNING — Complete Engine
// ════════════════════════════════════════════════════════════

const WFP = {
  records: [],        // all records from server
  filtered: [],       // after type filter
  editId: null,       // record being edited
  loaded: false,
  overview: null,     // cached overview/KPI data
};

const WFP_TYPE_LABELS = {
  demand:'Demand Forecasting', supply:'Supply Analysis', gap:'Gap Analysis',
  recruitment:'Recruitment Plan', training:'Training & Dev', succession:'Succession Plan',
  budget:'Workforce Budget', performance:'Performance & Productivity', risk:'Risk Management'
};
const WFP_TYPE_ICONS = {
  demand:'fa-chart-line', supply:'fa-user-check', gap:'fa-search-minus',
  recruitment:'fa-user-plus', training:'fa-graduation-cap', succession:'fa-crown',
  budget:'fa-coins', performance:'fa-tachometer-alt', risk:'fa-exclamation-triangle'
};
const WFP_TYPE_COLORS = {
  demand:'var(--primary)', supply:'var(--info)', gap:'var(--warning)',
  recruitment:'var(--primary-lt)', training:'#8B5CF6', succession:'var(--accent)',
  budget:'var(--primary)', performance:'var(--info)', risk:'var(--danger)'
};

// ── Priority / Status badges ──────────────────────────────
function wfpPriorityBadge(p){
  const m={critical:'risk-high',high:'risk-high',medium:'risk-medium',low:'risk-low'};
  return `<span class="${m[p]||'risk-low'}">${(p||'').toUpperCase()}</span>`;
}
function wfpStatusBadge(s){
  const m={draft:['bg-yellow','Draft'],in_progress:['bg-blue','In Progress'],approved:['bg-green','Approved'],completed:['bg-green','Completed']};
  const[cls,lbl]=m[s]||['bg-gray',s];
  return `<span class="badge ${cls}"><span class="bdot"></span>${lbl}</span>`;
}
function currFmt(v){ return v?'₦'+parseFloat(v).toLocaleString('en-NG',{minimumFractionDigits:0}):'–'; }
function pct(v){ return (v!==null&&v!==undefined&&v!=='') ? parseFloat(v).toFixed(1)+'%' : '–'; }

// ── Collect form fields into a payload object ─────────────
function collectWfpForm(){
  const type = $('#wfp-f-type').val();
  if(!type){ toast('Please select a record type.','error'); return null; }
  if(!$('#wfp-f-title').val().trim()){ toast('Please enter a title.','error'); return null; }
  if(!$('#wfp-f-period').val().trim()){ toast('Please enter a period/year.','error'); return null; }

  const base = {
    record_type: type,
    title: $('#wfp-f-title').val().trim(),
    department: $('#wfp-f-dept').val().trim(),
    period: $('#wfp-f-period').val().trim(),
    priority: $('#wfp-f-priority').val(),
    status: $('#wfp-f-status').val(),
  };

  const type_data = {};
  if(type==='demand'){
    type_data.growth_driver=$('#wfp-d-growth').val(); type_data.headcount_needed=$('#wfp-d-headcount').val();
    type_data.current_headcount=$('#wfp-d-current').val(); type_data.budget_projection=$('#wfp-d-budget').val();
    type_data.projects=$('#wfp-d-projects').val(); type_data.tech_factor=$('#wfp-d-tech').val();
    type_data.notes=$('#wfp-d-notes').val();
  } else if(type==='supply'){
    type_data.headcount=$('#wfp-s-headcount').val(); type_data.skills=$('#wfp-s-skills').val();
    type_data.avg_experience=$('#wfp-s-exp').val(); type_data.avg_age=$('#wfp-s-age').val();
    type_data.pct_under30=$('#wfp-s-u30').val(); type_data.pct_3050=$('#wfp-s-3050').val();
    type_data.pct_over50=$('#wfp-s-o50').val(); type_data.pct_high_perf=$('#wfp-s-perf').val();
    type_data.notes=$('#wfp-s-notes').val();
  } else if(type==='gap'){
    type_data.role=$('#wfp-g-role').val(); type_data.demand=$('#wfp-g-demand').val();
    type_data.supply=$('#wfp-g-supply').val(); type_data.gap_type=$('#wfp-g-gaptype').val();
    type_data.skill_shortages=$('#wfp-g-skills').val(); type_data.criticality=$('#wfp-g-crit').val();
    type_data.notes=$('#wfp-g-notes').val();
  } else if(type==='recruitment'){
    type_data.role=$('#wfp-r-role').val(); type_data.position_count=$('#wfp-r-count').val();
    type_data.strategy=$('#wfp-r-strategy').val(); type_data.target_date=$('#wfp-r-date').val();
    type_data.cost_per_hire=$('#wfp-r-cost').val(); type_data.total_budget=$('#wfp-r-budget').val();
    type_data.notes=$('#wfp-r-notes').val();
  } else if(type==='training'){
    type_data.program=$('#wfp-t-program').val(); type_data.competency=$('#wfp-t-competency').val();
    type_data.employee_count=$('#wfp-t-count').val(); type_data.training_type=$('#wfp-t-type').val();
    type_data.budget=$('#wfp-t-budget').val(); type_data.target_date=$('#wfp-t-date').val();
    type_data.notes=$('#wfp-t-notes').val();
  } else if(type==='succession'){
    type_data.role=$('#wfp-su-role').val(); type_data.incumbent=$('#wfp-su-current').val();
    type_data.successor_primary=$('#wfp-su-p1').val(); type_data.successor_secondary=$('#wfp-su-p2').val();
    type_data.readiness=$('#wfp-su-ready').val(); type_data.role_criticality=$('#wfp-su-crit').val();
    type_data.notes=$('#wfp-su-notes').val();
  } else if(type==='budget'){
    type_data.payroll_budget=$('#wfp-b-payroll').val(); type_data.payroll_actual=$('#wfp-b-payroll-act').val();
    type_data.benefits_budget=$('#wfp-b-benefits').val(); type_data.benefits_actual=$('#wfp-b-benefits-act').val();
    type_data.training_budget=$('#wfp-b-training').val(); type_data.training_actual=$('#wfp-b-training-act').val();
    type_data.overtime_budget=$('#wfp-b-overtime').val(); type_data.overtime_actual=$('#wfp-b-overtime-act').val();
    type_data.notes=$('#wfp-b-notes').val();
  } else if(type==='performance'){
    type_data.utilization=$('#wfp-p-util').val(); type_data.absenteeism=$('#wfp-p-abs').val();
    type_data.attrition=$('#wfp-p-attrition').val(); type_data.output_score=$('#wfp-p-output').val();
    type_data.efficiency=$('#wfp-p-eff').val(); type_data.overtime_hours=$('#wfp-p-ot').val();
    type_data.notes=$('#wfp-p-notes').val();
  } else if(type==='risk'){
    type_data.risk_type=$('#wfp-ri-type').val(); type_data.affected_role=$('#wfp-ri-role').val();
    type_data.risk_level=$('#wfp-ri-level').val(); type_data.employees_at_risk=$('#wfp-ri-count').val();
    type_data.probability=$('#wfp-ri-prob').val(); type_data.estimated_impact=$('#wfp-ri-impact').val();
    type_data.notes=$('#wfp-ri-notes').val();
  }
  return Object.assign(base, {type_data: type_data});
}

// ── Reset & populate form for editing ─────────────────────
function populateWfpForm(rec){
  $('#wfp-f-type').val(rec.record_type).trigger('change');
  $('#wfp-f-title').val(rec.title);
  $('#wfp-f-dept').val(rec.department||'');
  $('#wfp-f-period').val(rec.period||'');
  $('#wfp-f-priority').val(rec.priority||'medium');
  $('#wfp-f-status').val(rec.status||'draft');

  const d = rec.type_data || {};
  const t = rec.record_type;
  if(t==='demand'){
    $('#wfp-d-growth').val(d.growth_driver||''); $('#wfp-d-headcount').val(d.headcount_needed||'');
    $('#wfp-d-current').val(d.current_headcount||''); $('#wfp-d-budget').val(d.budget_projection||'');
    $('#wfp-d-projects').val(d.projects||''); $('#wfp-d-tech').val(d.tech_factor||''); $('#wfp-d-notes').val(d.notes||'');
  } else if(t==='supply'){
    $('#wfp-s-headcount').val(d.headcount||''); $('#wfp-s-skills').val(d.skills||'');
    $('#wfp-s-exp').val(d.avg_experience||''); $('#wfp-s-age').val(d.avg_age||'');
    $('#wfp-s-u30').val(d.pct_under30||''); $('#wfp-s-3050').val(d.pct_3050||'');
    $('#wfp-s-o50').val(d.pct_over50||''); $('#wfp-s-perf').val(d.pct_high_perf||''); $('#wfp-s-notes').val(d.notes||'');
  } else if(t==='gap'){
    $('#wfp-g-role').val(d.role||''); $('#wfp-g-demand').val(d.demand||'');
    $('#wfp-g-supply').val(d.supply||''); $('#wfp-g-gaptype').val(d.gap_type||'shortage');
    $('#wfp-g-skills').val(d.skill_shortages||''); $('#wfp-g-crit').val(d.criticality||'medium'); $('#wfp-g-notes').val(d.notes||'');
  } else if(t==='recruitment'){
    $('#wfp-r-role').val(d.role||''); $('#wfp-r-count').val(d.position_count||'');
    $('#wfp-r-strategy').val(d.strategy||'external'); $('#wfp-r-date').val(d.target_date||'');
    $('#wfp-r-cost').val(d.cost_per_hire||''); $('#wfp-r-budget').val(d.total_budget||''); $('#wfp-r-notes').val(d.notes||'');
  } else if(t==='training'){
    $('#wfp-t-program').val(d.program||''); $('#wfp-t-competency').val(d.competency||'');
    $('#wfp-t-count').val(d.employee_count||''); $('#wfp-t-type').val(d.training_type||'upskill');
    $('#wfp-t-budget').val(d.budget||''); $('#wfp-t-date').val(d.target_date||''); $('#wfp-t-notes').val(d.notes||'');
  } else if(t==='succession'){
    $('#wfp-su-role').val(d.role||''); $('#wfp-su-current').val(d.incumbent||'');
    $('#wfp-su-p1').val(d.successor_primary||''); $('#wfp-su-p2').val(d.successor_secondary||'');
    $('#wfp-su-ready').val(d.readiness||'1_2_years'); $('#wfp-su-crit').val(d.role_criticality||'critical'); $('#wfp-su-notes').val(d.notes||'');
  } else if(t==='budget'){
    $('#wfp-b-payroll').val(d.payroll_budget||''); $('#wfp-b-payroll-act').val(d.payroll_actual||'');
    $('#wfp-b-benefits').val(d.benefits_budget||''); $('#wfp-b-benefits-act').val(d.benefits_actual||'');
    $('#wfp-b-training').val(d.training_budget||''); $('#wfp-b-training-act').val(d.training_actual||'');
    $('#wfp-b-overtime').val(d.overtime_budget||''); $('#wfp-b-overtime-act').val(d.overtime_actual||''); $('#wfp-b-notes').val(d.notes||'');
  } else if(t==='performance'){
    $('#wfp-p-util').val(d.utilization||''); $('#wfp-p-abs').val(d.absenteeism||'');
    $('#wfp-p-attrition').val(d.attrition||''); $('#wfp-p-output').val(d.output_score||'');
    $('#wfp-p-eff').val(d.efficiency||''); $('#wfp-p-ot').val(d.overtime_hours||''); $('#wfp-p-notes').val(d.notes||'');
  } else if(t==='risk'){
    $('#wfp-ri-type').val(d.risk_type||'retirement'); $('#wfp-ri-role').val(d.affected_role||'');
    $('#wfp-ri-level').val(d.risk_level||'medium'); $('#wfp-ri-count').val(d.employees_at_risk||'');
    $('#wfp-ri-prob').val(d.probability||''); $('#wfp-ri-impact').val(d.estimated_impact||''); $('#wfp-ri-notes').val(d.notes||'');
  }
}

// ── Open form modal ───────────────────────────────────────
function openWfpForm(preType, recId){
  WFP.editId = recId || null;
  // Reset form
  $('#wfp-f-type,#wfp-f-title,#wfp-f-dept,#wfp-f-period').val('');
  $('#wfp-f-priority').val('medium'); $('#wfp-f-status').val('draft');
  $('.wfp-type-fields').hide();
  // Clear all inputs inside type fields
  $('.wfp-type-fields input, .wfp-type-fields textarea').val('');

  if(recId){
    const rec = WFP.records.find(function(r){ return r.id===recId; });
    if(rec){ populateWfpForm(rec); }
    $('#wfp-modal-title').html('<i class="fas fa-edit" style="color:var(--primary);margin-right:8px"></i>Edit Workforce Planning Record');
    $('#wfp-modal-sub').text('Update the record details');
  } else {
    if(preType) $('#wfp-f-type').val(preType).trigger('change');
    $('#wfp-modal-title').html('<i class="fas fa-plus-circle" style="color:var(--primary);margin-right:8px"></i>Create Workforce Planning Record');
    $('#wfp-modal-sub').text('Fill in all required fields');
  }
  $('#modal-workforce').css('display','flex').addClass('open');
}

// ── View record modal ─────────────────────────────────────
function openWfpView(recId){
  const rec = WFP.records.find(function(r){ return r.id===recId; });
  if(!rec) return;
  const icon = WFP_TYPE_ICONS[rec.record_type]||'fa-file';
  const color = WFP_TYPE_COLORS[rec.record_type]||'var(--primary)';
  const lbl = WFP_TYPE_LABELS[rec.record_type]||rec.record_type;

  $('#wfp-view-title').html(`<i class="fas ${icon}" style="color:${color};margin-right:8px"></i>${esc(rec.title)}`);
  $('#wfp-view-sub').html(`${lbl} &nbsp;·&nbsp; ${esc(rec.period||'–')} &nbsp;·&nbsp; ${wfpPriorityBadge(rec.priority)} &nbsp;${wfpStatusBadge(rec.status)}`);
  $('#wfp-edit-from-view-btn').data('id', recId);

  const d = rec.type_data || {};
  let rows = `<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:16px">
    <div><div style="font-size:.7rem;color:var(--muted);text-transform:uppercase;font-weight:700">Department</div><div style="font-weight:600;margin-top:3px">${esc(rec.department||'–')}</div></div>
    <div><div style="font-size:.7rem;color:var(--muted);text-transform:uppercase;font-weight:700">Period</div><div style="font-weight:600;margin-top:3px">${esc(rec.period||'–')}</div></div>
    <div><div style="font-size:.7rem;color:var(--muted);text-transform:uppercase;font-weight:700">Created By</div><div style="font-weight:600;margin-top:3px">${esc(rec.created_by||'–')}</div></div>
    <div><div style="font-size:.7rem;color:var(--muted);text-transform:uppercase;font-weight:700">Date Created</div><div style="font-weight:600;margin-top:3px">${esc(rec.create_date||'–')}</div></div>
  </div><hr style="margin:0 0 16px;border:none;border-top:1px solid var(--border)"/>`;

  function row2(lbl2, val){ return `<div><div style="font-size:.7rem;color:var(--muted);text-transform:uppercase;font-weight:700;margin-bottom:3px">${lbl2}</div><div style="font-weight:500">${val||'–'}</div></div>`; }

  if(rec.record_type==='demand'){
    rows += `<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
      ${row2('Business Growth Driver',esc(d.growth_driver))}${row2('Headcount Needed',d.headcount_needed)}
      ${row2('Current Headcount',d.current_headcount)}${row2('Budget Projection',currFmt(d.budget_projection))}
      ${row2('Key Projects',esc(d.projects))}${row2('Technology Factor',esc(d.tech_factor))}
      <div style="grid-column:1/-1">${row2('Forecast Rationale',esc(d.notes))}</div></div>`;
  } else if(rec.record_type==='supply'){
    rows += `<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
      ${row2('Total Headcount',d.headcount)}${row2('Key Skills',esc(d.skills))}
      ${row2('Avg Experience',d.avg_experience?d.avg_experience+' yrs':'–')}${row2('Avg Age',d.avg_age?d.avg_age+' yrs':'–')}
      ${row2('Under 30',pct(d.pct_under30))}${row2('30–50',pct(d.pct_3050))}
      ${row2('Over 50',pct(d.pct_over50))}${row2('High Performers',pct(d.pct_high_perf))}
      <div style="grid-column:1/-1">${row2('Notes',esc(d.notes))}</div></div>`;
  } else if(rec.record_type==='gap'){
    rows += `<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
      ${row2('Role',esc(d.role))}${row2('Gap Type',(d.gap_type||'').replace('_',' ').toUpperCase())}
      ${row2('Demand',d.demand)}${row2('Supply',d.supply)}
      ${row2('Net Gap',(d.demand&&d.supply)?parseInt(d.demand)-parseInt(d.supply):'–')}
      ${row2('Criticality',(d.criticality||'').toUpperCase())}
      ${row2('Skill Shortages',esc(d.skill_shortages))}
      <div style="grid-column:1/-1">${row2('Summary',esc(d.notes))}</div></div>`;
  } else if(rec.record_type==='budget'){
    function budRow(lbl2, bgt, act){
      const pctUsed = bgt&&act ? (parseFloat(act)/parseFloat(bgt)*100).toFixed(0)+'%' : '–';
      return `<tr><td>${lbl2}</td><td style="text-align:right">${currFmt(bgt)}</td><td style="text-align:right">${currFmt(act)}</td><td style="text-align:center">${pctUsed}</td></tr>`;
    }
    rows += `<table style="width:100%;border-collapse:collapse;font-size:.85rem">
      <thead><tr style="background:var(--surface)"><th style="padding:8px;text-align:left">Item</th><th style="padding:8px;text-align:right">Budget</th><th style="padding:8px;text-align:right">Actual</th><th style="padding:8px;text-align:center">Used</th></tr></thead>
      <tbody style="border-top:2px solid var(--border)">
        ${budRow('Payroll',d.payroll_budget,d.payroll_actual)}
        ${budRow('Benefits',d.benefits_budget,d.benefits_actual)}
        ${budRow('Training',d.training_budget,d.training_actual)}
        ${budRow('Overtime',d.overtime_budget,d.overtime_actual)}
      </tbody></table>
      ${d.notes?`<div style="margin-top:14px;font-size:.84rem;color:var(--muted)">${esc(d.notes)}</div>`:''}`;
  } else if(rec.record_type==='risk'){
    rows += `<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
      ${row2('Risk Type',(d.risk_type||'').replace('_',' '))}${row2('Risk Level',`<span class="risk-${d.risk_level||'low'}">${(d.risk_level||'').toUpperCase()}</span>`)}
      ${row2('Affected Role',esc(d.affected_role))}${row2('Employees at Risk',d.employees_at_risk)}
      ${row2('Probability',pct(d.probability))}${row2('Estimated Impact',currFmt(d.estimated_impact))}
      <div style="grid-column:1/-1">${row2('Mitigation Plan',esc(d.notes))}</div></div>`;
  } else if(rec.record_type==='performance'){
    rows += `<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
      ${row2('Workforce Utilization',pct(d.utilization))}${row2('Absenteeism Rate',pct(d.absenteeism))}
      ${row2('Attrition Rate',pct(d.attrition))}${row2('Avg Output Score',d.output_score)}
      ${row2('Efficiency Index',pct(d.efficiency))}${row2('Overtime Hours/Mo',d.overtime_hours)}
      <div style="grid-column:1/-1">${row2('Productivity Notes',esc(d.notes))}</div></div>`;
  } else if(rec.record_type==='succession'){
    rows += `<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
      ${row2('Critical Role',esc(d.role))}${row2('Role Criticality',(d.role_criticality||'').replace('_',' '))}
      ${row2('Current Incumbent',esc(d.incumbent))}${row2('Readiness',(d.readiness||'').replace(/_/g,' '))}
      ${row2('Primary Successor',esc(d.successor_primary))}${row2('Secondary Successor',esc(d.successor_secondary))}
      <div style="grid-column:1/-1">${row2('Development Plan',esc(d.notes))}</div></div>`;
  } else {
    // Generic fallback — show all type_data keys
    const kvs = Object.entries(d).map(function([k,v]){ return row2(k.replace(/_/g,' '),esc(String(v))); }).join('');
    rows += `<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">${kvs}</div>`;
  }

  $('#wfp-view-body').html(rows);
  $('#modal-wfp-view').css('display','flex').addClass('open');
}

// ── Load WFP data from server ─────────────────────────────
function loadWfpData(){
  return rpc('/pms/api/workforce-data', {}).then(function(r){
    if(!r){ return; }
    WFP.records = r.records || [];
    WFP.overview = r.overview || {};
    WFP.filtered = WFP.records;
  }).fail(function(e){ toast('Could not load workforce data: '+e, 'error'); });
}

// ── Load KPI overview data (from performance records + server) ──
function renderWfpOverview(){
  const ov = WFP.overview || {};
  console.log(ov)
  console.log('the total wfp component ==>', WFP)
  // KPI Cards
  $('#kpi-headcount').text(ov.total_headcount||'–');
  $('#kpi-headcount-d').text(ov.headcount_note||'').removeClass('up down neu').addClass(ov.headcount_trend||'neu');
  $('#kpi-attrition').text(ov.attrition_rate ? ov.attrition_rate+'%' : '–');
  $('#kpi-attrition-d').text(ov.attrition_note||'').removeClass('up down neu').addClass(ov.attrition_trend||'neu');
  $('#kpi-cost-hire').text(ov.avg_cost_per_hire ? '₦'+parseFloat(ov.avg_cost_per_hire).toLocaleString() : '–');
  $('#kpi-absenteeism').text(ov.absenteeism_rate ? ov.absenteeism_rate+'%' : '–');
  $('#kpi-vacancies').text(ov.open_vacancies||'–');
  $('#kpi-utilization').text(ov.utilization ? ov.utilization+'%' : '–');
  $('#kpi-util-d').text(ov.utilization_note||'').removeClass('up down neu').addClass(ov.utilization_trend||'neu');

  // Demographics
  $('#demo-u30').text(ov.pct_under30 ? ov.pct_under30+'%' : '–');
  $('#demo-3040').text(ov.pct_3040 ? ov.pct_3040+'%' : '–');
  $('#demo-4050').text(ov.pct_4050 ? ov.pct_4050+'%' : '–');
  $('#demo-o50').text(ov.pct_over50 ? ov.pct_over50+'%' : '–');
  $('#demo-male').text(ov.pct_male ? ov.pct_male+'%' : '–');
  $('#demo-female').text(ov.pct_female ? ov.pct_female+'%' : '–');

  // Productivity bars
  const prodBars = [
    {lbl:'Workforce Utilization', val: parseFloat(ov.utilization||0), max:100, color:'var(--primary)'},
    {lbl:'Efficiency Index',       val: parseFloat(ov.efficiency||0),  max:100, color:'var(--info)'},
    {lbl:'Output Score',           val: parseFloat(ov.output_score||0),max:100, color:'var(--primary-lt)'},
    {lbl:'Absenteeism',            val: parseFloat(ov.absenteeism_rate||0), max:20, color:'var(--danger)'},
  ];
  $('#wfp-productivity-bars').html(prodBars.map(function(b){
    const pctW = Math.min(b.max>0?b.val/b.max*100:0,100);
    return `<div class="hbar-row"><span class="hbar-label">${b.lbl}</span>
      <div class="hbar-track"><div class="hbar-fill" style="width:${pctW}%;background:${b.color}"></div></div>
      <span class="hbar-val">${b.val||0}</span></div>`;
  }).join(''));

  // Budget bars
  const budBars = [
    {lbl:'Payroll', budget: parseFloat(ov.payroll_budget||0), actual: parseFloat(ov.payroll_actual||0)},
    {lbl:'Benefits',budget: parseFloat(ov.benefits_budget||0),actual: parseFloat(ov.benefits_actual||0)},
    {lbl:'Training', budget:parseFloat(ov.training_budget||0),actual: parseFloat(ov.training_actual||0)},
    {lbl:'Overtime', budget:parseFloat(ov.overtime_budget||0),actual: parseFloat(ov.overtime_actual||0)},
  ];
  $('#wfp-budget-bars').html(budBars.map(function(b){
    const pctW = b.budget>0 ? Math.min(b.actual/b.budget*100,120) : 0;
    const clr = pctW>100 ? 'var(--danger)' : pctW>80 ? 'var(--warning)' : 'var(--primary)';
    return `<div class="hbar-row"><span class="hbar-label">${b.lbl}</span>
      <div class="hbar-track"><div class="hbar-fill" style="width:${Math.min(pctW,100)}%;background:${clr}"></div></div>
      <span class="hbar-val" style="font-size:.72rem">${pctW.toFixed(0)}%</span></div>`;
  }).join(''));

  // Risk summary
  const risks = WFP.records.filter(function(r){ return r.record_type==='risk'; });
  if(!risks.length){
    $('#wfp-risk-summary-list').html('<div style="text-align:center;padding:20px;color:var(--muted)"><i class="fas fa-check-circle" style="font-size:2rem;margin-bottom:8px;display:block;color:var(--primary-lt)"></i>No risks recorded</div>');
  } else {
    $('#wfp-risk-summary-list').html(risks.slice(0,5).map(function(r){
      const d=r.type_data||{};
      return `<div style="display:flex;align-items:center;gap:10px;padding:9px 0;border-bottom:1px solid var(--border)">
        <span class="risk-${d.risk_level||'low'}">${(d.risk_level||'').toUpperCase()}</span>
        <div style="flex:1"><div style="font-weight:600;font-size:.84rem">${esc(r.title)}</div>
          <div style="font-size:.74rem;color:var(--muted)">${esc(d.affected_role||'')} &nbsp;·&nbsp; ${(d.risk_type||'').replace(/_/g,' ')}</div></div>
        <button class="btn btn-secondary btn-sm" onclick="openWfpView(${r.id})"><i class="fas fa-eye"></i></button>
      </div>`;
    }).join(''));
  }
}

// ── Render per-tab lists ──────────────────────────────────
function renderWfpTabContent(tabId){
  const typeMap = {
    'wfp-demand':'demand','wfp-supply':'supply','wfp-gap':'gap',
    'wfp-recruitment':'recruitment','wfp-succession':'succession',
    'wfp-budget':'budget','wfp-risk':'risk'
  };
  const type = typeMap[tabId];
  if(!type) return;
  const recs = WFP.records.filter(function(r){ return r.record_type===type; });
  const targetId = '#'+tabId+'-list, #'+tabId+'-content';

  // Find the content div inside the tab
  const $container = $(`#${tabId} [id$="-list"], #${tabId} [id$="-content"]`).first();
  if(!$container.length) return;

  if(!recs.length){
    $container.html('<div class="no-results"><i class="fas fa-inbox"></i><p>No records yet. Click "Add" to create one.</p></div>');
    return;
  }

  // Render a card list for each record
  const html = recs.map(function(r){
    const d=r.type_data||{};
    let detail = '';
    if(type==='demand') detail=`<span><i class="fas fa-users"></i> Need: ${d.headcount_needed||'–'}</span><span><i class="fas fa-layer-group"></i> Current: ${d.current_headcount||'–'}</span>`;
    else if(type==='supply') detail=`<span><i class="fas fa-users"></i> HC: ${d.headcount||'–'}</span><span><i class="fas fa-star"></i> High Perf: ${pct(d.pct_high_perf)}</span>`;
    else if(type==='gap') detail=`<span><i class="fas fa-arrow-up"></i> Demand: ${d.demand||'–'}</span><span><i class="fas fa-arrow-down"></i> Supply: ${d.supply||'–'}</span><span>Gap: ${d.demand&&d.supply?parseInt(d.demand)-parseInt(d.supply):'–'}</span>`;
    else if(type==='recruitment') detail=`<span><i class="fas fa-user-plus"></i> ${d.position_count||'–'} positions</span><span>${(d.strategy||'').replace(/_/g,' ')}</span><span>${currFmt(d.total_budget)}</span>`;
    else if(type==='succession') detail=`<span><i class="fas fa-crown"></i> ${esc(d.role||'–')}</span><span>Successor: ${esc(d.successor_primary||'–')}</span><span>${(d.readiness||'').replace(/_/g,' ')}</span>`;
    else if(type==='budget') detail=`<span>Payroll: ${currFmt(d.payroll_budget)}</span><span>Training: ${currFmt(d.training_budget)}</span>`;
    else if(type==='risk') detail=`<span class="risk-${d.risk_level||'low'}">${(d.risk_level||'').toUpperCase()}</span><span>${(d.risk_type||'').replace(/_/g,' ')}</span><span>Prob: ${pct(d.probability)}</span>`;

    return `<div style="background:var(--surface);border-radius:var(--r);padding:14px 16px;margin-bottom:10px;display:flex;align-items:center;gap:12px;flex-wrap:wrap">
      <div style="flex:1;min-width:200px">
        <div style="font-weight:700;font-size:.9rem;margin-bottom:4px">${esc(r.title)}</div>
        <div style="display:flex;gap:12px;flex-wrap:wrap;font-size:.78rem;color:var(--muted)">${detail}</div>
        <div style="margin-top:6px;font-size:.74rem;color:var(--muted)">${esc(r.department||'')} ${r.department&&r.period?'·':''} ${esc(r.period||'')}</div>
      </div>
      <div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap">
        ${wfpPriorityBadge(r.priority)} ${wfpStatusBadge(r.status)}
        <button class="btn btn-secondary btn-sm" onclick="openWfpView(${r.id})"><i class="fas fa-eye"></i></button>
        <button class="btn btn-warning btn-sm" onclick="openWfpForm('${type}',${r.id})"><i class="fas fa-edit"></i></button>
        <button class="btn btn-danger btn-sm wfp-delete-btn" data-id="${r.id}"><i class="fas fa-trash"></i></button>
      </div>
    </div>`;
  }).join('');
  $container.html(html);
}

// ── Render all records table ──────────────────────────────
function renderWfpRecordsTable(recs){
  recs = recs || WFP.filtered;
  const $body = $('#wfp-records-body').empty();
  $('#wfp-rec-count').text(recs.length+' record'+(recs.length===1?'':'s'));
  if(!recs.length){
    $body.html('<tr><td colspan="9"><div class="no-results"><i class="fas fa-inbox"></i><p>No records found.</p></div></td></tr>');
    return;
  }
  recs.forEach(function(r){
    const icon = WFP_TYPE_ICONS[r.record_type]||'fa-file';
    const color = WFP_TYPE_COLORS[r.record_type]||'var(--primary)';
    $body.append(`<tr>
      <td><span style="color:${color};font-weight:600"><i class="fas ${icon}"></i> ${WFP_TYPE_LABELS[r.record_type]||r.record_type}</span></td>
      <td><strong>${esc(r.title)}</strong></td>
      <td>${esc(r.department||'–')}</td>
      <td>${esc(r.period||'–')}</td>
      <td>${wfpStatusBadge(r.status)}</td>
      <td>${wfpPriorityBadge(r.priority)}</td>
      <td>${esc(r.created_by||'–')}</td>
      <td>${esc(r.create_date||'–')}</td>
      <td>
        <button class="btn btn-secondary btn-sm" onclick="openWfpView(${r.id})"><i class="fas fa-eye"></i></button>
        <button class="btn btn-warning btn-sm" style="margin-left:4px" onclick="openWfpForm('${r.record_type}',${r.id})"><i class="fas fa-edit"></i></button>
        <button class="btn btn-danger btn-sm wfp-delete-btn" data-id="${r.id}" style="margin-left:4px"><i class="fas fa-trash"></i></button>
      </td>
    </tr>`);
  });
}

// ── Export WFP CSV ────────────────────────────────────────
function exportWfpCsv(recs){
  if(!recs||!recs.length){ toast('No data to export.','info'); return; }
  const cols=['Type','Title','Department','Period','Status','Priority','Created By','Date'];
  const rows=[cols.join(',')];
  recs.forEach(function(r){
    rows.push([
      r.record_type||'', '"'+(r.title||'').replace(/"/g,'""')+'"',
      '"'+(r.department||'').replace(/"/g,'""')+'"', '"'+(r.period||'').replace(/"/g,'""')+'"',
      r.status||'', r.priority||'',
      '"'+(r.created_by||'').replace(/"/g,'""')+'"', r.create_date||''
    ].join(','));
  });
  const blob = new Blob([rows.join('\n')],{type:'text/csv'});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(blob); a.download='workforce_planning_'+new Date().toISOString().slice(0,10)+'.csv'; a.click();
  URL.revokeObjectURL(a.href);
}

// ── Init workforce page ───────────────────────────────────
function initWorkforcePage(){
  if(WFP.loaded){
    renderWfpOverview();
    renderWfpRecordsTable();
    return;
  }
  // Show loaders in overview panels
  $('#wfp-kpi-strip .wfp-kpi-val').text('…');
  $('#wfp-productivity-bars,#wfp-budget-bars').html('<div class="loader-wrap" style="padding:20px"><div class="loader"></div></div>');
  $('#wfp-risk-summary-list').html('<div class="loader-wrap" style="padding:20px"><div class="loader"></div></div>');

  loadWfpData().always(function(){
    WFP.loaded = true;
    renderWfpOverview();
    renderWfpRecordsTable();
    // Pre-render demand and risk tabs since overview shows those
    renderWfpTabContent('wfp-demand');
    renderWfpTabContent('wfp-risk');
  });
}

// ════════════════════════════════════════════════════════════
//  EVENT LISTENERS
// ════════════════════════════════════════════════════════════
$(function(){
  // ── Init: set username from meta tag (injected by controller) ──
  const uname = App.user.name || 'Employee';
  $('#sb-username,#dash-username, #refreshname').text(uname);

  // Load dashboard immediately — no blocking calls at startup
  loadDashboard();

  // ── Nav ──
  $(document).on('click','.nav-item',function(){
    const page=$(this).data('page');
    showPage(page);
    if(page==='appraisals'){
      $('#appraisals-table').html('<div class="loader-wrap"><div class="loader"></div></div>');
      loadAppraisals(recs=>renderAppraisalsTable(recs,'#appraisals-table'));
    }
    if(page==='pending-approvals') loadPendingApprovals();
    if(page==='reporting') initReportingPage();
    if(page==='workforce') initWorkforcePage();
  });
  // --- WORKFORCE PLANNING MENU --
  $('#workforce2').on('click', function () {
      window.location.href = '/wfp-portal'
  });

  // ── Refresh ──
  $('#refresh-btn').on('click',function(){
    $(this).find('i').addClass('fa-spin');
    loadDashboard();
    setTimeout(()=>$(this).find('i').removeClass('fa-spin'),900);
  });

  // ── Back ──
  $('#back-detail').on('click',()=>showPage('appraisals'));

  // ── Open appraisal ──
  $(document).on('click','.open-appraisal',function(){ openAppraisal($(this).data('id')); });

  // ── Section nav ──
  $(document).on('click','.snav-btn',function(){
    $('.snav-btn').removeClass('active'); $(this).addClass('active');
    const $target = $(`#${$(this).data('target')}`);
    if($target.length) $('html,body').animate({scrollTop:$target.offset().top-80},350);
  });

  // ── GOAL SETTING ──
  // Add line
  $('#goal-add-line').on('click',function(){
    const row=buildGoalRow({id:null,name:'',weightage:0,pms_uom:'',target:''},true);
    $('#goal-body').append(row);
    initSelect2('#goal-body .uom-sel');
    updateWBar();
  });
  $(document).on('input change','#goal-body .wt-input',updateWBar);
  $(document).on('click','.row-del',function(){ $(this).closest('tr').remove(); updateWBar(); });

  // Save goals
  $(document).on('click','#save-goals-btn',function(){
    const lines=collectGoalLines();
    $('#goal_saved').val('true');
    if(!validateGoalLines(lines)) return;
    const $b=$(this).prop('disabled',true).html('<i class="fas fa-spinner fa-spin"></i> Saving…');
    rpc('/pms/api/save-goals',{appraisal_id:App.currentId,lines}).then(r=>{
      r.error?toast(r.error,'error'):toast(r.message,'success');
    }).fail(e=>toast(e,'error')).always(()=>$b.prop('disabled',false).html('<i class="fas fa-save"></i> Save'));
  });

  // Submit goal setting
  $(document).on('click','#submit-gs-btn',function(){
    const lines=collectGoalLines();
    if(!validateGoalLines(lines)) return;
    const $b=$(this).prop('disabled',true).html('<i class="fas fa-spinner fa-spin"></i> Submitting…');
    rpc('/pms/api/save-goals',{appraisal_id:App.currentId,lines}).then(r=>{
      if(r.error){ 
        toast(r.error,'error'); return $.Deferred().reject(); }
      return rpc('/pms/api/submit-goal-setting',{appraisal_id:App.currentId});
    }).then(r=>{
      if(!r) return;
      r.error?toast(r.error,'error'):(toast(r.message,'success'),openAppraisal(App.currentId));
    }).fail(e=>{ if(e) toast(e,'error'); }).always(()=>$b.prop('disabled',false).html('<i class="fas fa-paper-plane"></i> Submit Goal Setting to Manager'));
  });

  // Manager approve GS
  $(document).on('click','#approve-gs-btn,.pending-approve-gs',function(){
    const id=$(this).data('id')||App.currentId;
    if(!confirm('Approve this Goal Setting and move to Mid Year Review?')) return;
    const $b=$(this).prop('disabled',true);
    rpc('/pms/api/manager-approve-goal-setting',{appraisal_id:id}).then(r=>{
      r.error?toast(r.error,'error'):(toast(r.message,'success'),id===App.currentId?openAppraisal(id):loadPendingApprovals());
    }).fail(e=>toast(e,'error')).always(()=>$b.prop('disabled',false));
  });

  // Open return modal
  $(document).on('click','#return-gs-btn,.pending-return-gs',function(){
    App.managerReturnId=$(this).data('id')||App.currentId;
    $('#return-reason').val('');
    $('#modal-return').css('display','flex').addClass('open');
  });

  // Confirm return
  $('#confirm-return-btn').on('click',function(){
    const reason=$('#return-reason').val().trim();
    if(!reason){ toast('Please enter a reason.','error'); return; }
    const $b=$(this).prop('disabled',true).html('<i class="fas fa-spinner fa-spin"></i> Returning…');
    rpc('/pms/api/manager-return-goal-setting',{appraisal_id:App.managerReturnId,reason}).then(r=>{
      r.error?toast(r.error,'error'):(toast(r.message,'success'),$('#modal-return').removeClass('open'),
        App.managerReturnId===App.currentId?openAppraisal(App.currentId):loadPendingApprovals());
    }).fail(e=>toast(e,'error')).always(()=>$b.prop('disabled',false).html('<i class="fas fa-undo"></i> Return to Employee'));
  });

  // ── HYR ──
  $(document).on('click','#save-hyr-btn',function(){
    const lines=collectHyrLines();
    const $b=$(this).prop('disabled',true).html('<i class="fas fa-spinner fa-spin"></i> Saving…');
    rpc('/pms/api/save-hyr-lines',{appraisal_id:App.currentId,lines}).then(r=>{
      r.error?toast(r.error,'error'):toast(r.message,'success');
    }).fail(e=>toast(e,'error')).always(()=>$b.prop('disabled',false).html('<i class="fas fa-save"></i> Save Mid Year Lines'));
  });

  $(document).on('click','#submit-hyr-btn',function(){
    const $b=$(this).prop('disabled',true).html('<i class="fas fa-spinner fa-spin"></i> Submitting…');
    rpc('/pms/api/submit-hyr',{appraisal_id:App.currentId}).then(r=>{
      r.error?toast(r.error,'error'):(toast(r.message,'success'),openAppraisal(App.currentId));
    }).fail(e=>toast(e,'error')).always(()=>$b.prop('disabled',false).html('<i class="fas fa-paper-plane"></i> Submit for Mid Year Review'));
  });

  $(document).on('click','#submit-hyr-mgr-btn',function(){
    if(!confirm('Submit Mid Year Review and move to Full Appraisal Review?')) return;
    const $b=$(this).prop('disabled',true).html('<i class="fas fa-spinner fa-spin"></i> Submitting…');
    let lines=collectHyrLines();
    rpc('/pms/api/save-hyr-lines',{appraisal_id:App.currentId,lines}).then(r=>{
      if(r.error){ 
        toast(r.error,'error'); return $.Deferred().reject(); 
      }
    })
    rpc('/pms/api/submit-hyr-manager',{appraisal_id:App.currentId}).then(r=>{
      r.error?toast(r.error,'error'):(toast(r.message,'success'),openAppraisal(App.currentId));
    }).fail(e=>toast(e,'error')).always(()=>$b.prop('disabled',false).html('<i class="fas fa-check-double"></i> Submit Mid Year Review'));
  });

  let refreshPage = function(){
    // openAppraisal(App.currentId)
    $('#kra-body').empty();
      rpc(`/pms/api/appraisal/${App.currentId}`).then(r=>{
      renderKRA(r);
      $('#save-kra-self').prop('disabled',false).html('<i class="fas fa-save"></i> Save')
    })
    
    // window.location.href = '/pms-portal';
  }
  


    // AIIIIIII

    function refreshKraTable(lines) {
      const $tbody = $('#kra-body');
  
      // FIX 2: Clear existing rows first to prevent duplication
      $tbody.empty();
  
      lines.forEach(function (line) {
          const row = `
              <tr data-lid="${line.id}">
                  <td>
                      <input
                          type="text"
                          id="kra-line-id"
                          class="form-control"
                          value="${escapeHtml(line.name || '')}"
                      />
                  </td>
                  <td><input type="number" class="midyear-review-input" value="" disabled="true"/></td>

                  <td>
                      <!-- FIX 3: NO readonly attribute – weightage is always editable -->
                      <input
                          type="number"
                          class="form-control kra-weightage"
                          min="5"
                          max="25"
                          value="${parseInt(line.weightage) || 0}"
                      />
                  </td>
                  <td>
                      <input type="number" class="rating-input kra-self" value="${parseInt(line.self_rating) || 0}" min="1" max="4"/>
                  </td>
                  <td><button class="row-del-kra" title="Remove"><i class="fas fa-trash-alt"></i></button></td>

              </tr>`;
          $tbody.append(row);
      });
  }
  
  // ── Utility: basic HTML escaping ─────────────────────────────────────────────
  function escapeHtml(str) {
      return String(str)
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;');
  }
  
  // ── Collect lines from DOM ────────────────────────────────────────────────────
  function collectKraLines() {
      const lines = [];
      $('#kra-body tr').each(function () {
          const $r = $(this);
          const lid = $r.data('lid');
          lines.push({
              // When lid is falsy (new row) send null so backend creates a record.
              id: lid ? parseInt(lid) : null,
              name: $r.find('#kra-line-id').val(),
              self_rating: parseInt($r.find('.kra-self').val()) || 0,
              self_weightage: parseInt($r.find('.kra-weightage').val()) || 0,
          });
      });
      return lines;
  }






  // function saveSelfRating($btn) {
  //     const lines = collectKraLines();
  
  //     rpc('/pms/api/save-kra-self-rating', {
  //         appraisal_id: App.currentId,
  //         lines,
  //     })
  //     .then(function (r) {
  //         if (r.error) {
  //             toast(r.error, 'error');
  //         } else {
  //             toast(r.message, 'success');
  
  //             // FIX 2: Re-render table in-place using returned lines
  //             //         instead of calling refreshPage() which caused duplication.
  //             if (r.lines && r.lines.length) {
  //                 refreshKraTable(r.lines);
  //             }
  //         }
  //     })
  //     .fail(function (e) {
  //         toast('An unexpected error occurred.', 'error');
  //         console.error(e);
  //     })
  //     .always(function () {
  //         // FIX 1: Re-enable the button AFTER the response is fully handled,
  //         //         not inside a setTimeout or before the response arrives.
  //         if ($btn) {
  //             $btn
  //                 .prop('disabled', false)
  //                 .html('<i class="fas fa-save"></i> Save Self Rating');
  //         }
  //     });
  // }

  function saveSelfRating($btn) {
      const lines = collectKraLines();

      rpc('/pms/api/save-kra-self-rating', {
          appraisal_id: App.currentId,
          lines,
      })
      .then(function (r) {
          if (r.error) {
              // Show the error but DO NOT touch the table –
              // user inputs remain exactly as they were.
              toast(r.error, 'error');
              return;
          }

          toast(r.message, 'success');
          // Only re-render on success, using lines returned from the backend.
          if (r.lines && r.lines.length) {
              refreshKraTable(r.lines);
          }
      })
      .fail(function (e) {
          // Network / server fault – again, leave the table untouched.
          toast('An unexpected error occurred. Please try again.', 'error');
          console.error(e);
      })
      .always(function () {
          // Re-enable the button regardless of outcome.
          if ($btn) {
              $btn
                  .prop('disabled', false)
                  .html('<i class="fas fa-save"></i> Save Self Rating');
          }
      });
  }

  $(document).on('click', '#save-kra-self', function () {
    const $btn = $(this);
 
    // FIX 1: Disable immediately and show spinner
    $btn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> Saving…');
 
    saveSelfRating($btn);
  });

  function DeleteKRALine(ID, model){
    // Id is the record id and model : target model
    rpc(`/pms/api/delete`,{record_id: ID, model: model}).then(r=>{
    r.error? toast(r.error,'error'): toast(r.message,'success');
    }).fail(e=>toast(e,'error')).always(()=> console.log("Deleted "));
  }

  $(document).on('click','#submit-fyr-btn',function(){
    if(!confirm('Submit your Full Appraisal self-rating?')) return;
    const $b=$(this).prop('disabled',true).html('<i class="fas fa-spinner fa-spin"></i> Submitting…');
    // saveSelfRating();
    rpc('/pms/api/submit-fyr',{appraisal_id:App.currentId}).then(r=>{
      r.error? (toast(r.error,'error')):(toast(r.message,'success'), openAppraisal(App.currentId));
    }).fail(
      e=>toast(e,'error')).always(
        ()=> $b.prop('disabled',false).html(
          '<i class="fas fa-paper-plane"></i> Submit Full Appraisal Review'), 
          console.log("HITTING THE NAIL")
        // $("#kra-add-line").hide()
        );
  });

  let saveCompLinesFunction = function(buttonProps){
      // this is just for FC, LC, POTENTIAL, CURRENT ASSET savings
      // const sec=$(this).data('sec');
      const r=App.appraisal;
      const recId = App.currentId
      const lines=[];

      // saving fc lines 
      let tbodyId = '#fc-body'
      $(tbodyId+' tr').each(function(){
        const $row=$(this); const lid=$row.data('lid'); if(!lid) return;
        let line = {
              id: parseInt(lid),
              model: 'fc'
          };

        const aa = $row.find('.comp-aa');
        const fa = $row.find('.comp-fa');
        const rev = $row.find('.comp-rev');
        if (aa.length && !aa.prop('disabled') && !aa.prop('readonly')) {
            const val = parseInt(aa.val());
            if (!isNaN(val)) line.administrative_supervisor_rating = val;
        }

        if (fa.length && !fa.prop('disabled') && !fa.prop('readonly')) {
            const val = parseInt(fa.val());
            if (!isNaN(val)) line.functional_supervisor_rating = val;
        }

        if (rev.length && !rev.prop('disabled') && !rev.prop('readonly')) {
            const val = parseInt(rev.val());
            if (!isNaN(val)) line.reviewer_rating = val;
        }
        lines.push(line);
      });

      // saving lc lines 
      
      let tbodyIdfc = '#lc-body';
      $(tbodyIdfc +' tr').each(function(){
        const $row=$(this); const lid=$row.data('lid'); if(!lid) return;
        let line = {
              id: parseInt(lid),
              model: 'lc'
          };
        const aa = $row.find('.comp-aa');
        const fa = $row.find('.comp-fa');
        const rev = $row.find('.comp-rev');
        if (aa.length && !aa.prop('disabled') && !aa.prop('readonly')) {
            const val = parseInt(aa.val());
            if (!isNaN(val)) line.administrative_supervisor_rating = val;
        }

        if (fa.length && !fa.prop('disabled') && !fa.prop('readonly')) {
            const val = parseInt(fa.val());
            if (!isNaN(val)) line.functional_supervisor_rating = val;
        }

        if (rev.length && !rev.prop('disabled') && !rev.prop('readonly')) {
            const val = parseInt(rev.val());
            if (!isNaN(val)) line.reviewer_rating = val;
        }
        lines.push(line);
      });
        
      // } else if(sec==='training'){

      // saving training lines 

      $('#training-body tr').each(function(){
        const $row=$(this);
        const lid= $row.data('lid');
        console.log(`TRAININGSSS == ?>${lid}`) 
        // if(!lid) return;
        lines.push(
          {
            id:parseInt(lid),
            model: 'training',
            name: $row.find('.trn-name').val(),
            comments:$row.find('.trn-comment').val(),

          });
      }); 

      // saving current assessment lines 

      (r.current_assessment || []).forEach(function (assessLine) {

        const $select = $(
            `#curr-assess-body .curr-assess-sel[data-id="${assessLine.id}"]`
        );

        const aType = $select.length
            ? $select.val()
            : assessLine.assessment_type;

        lines.push({
            id: assessLine.id,
            model: 'current_assessment',
            assessment_type: aType,
            administrative_supervisor_rating: assessLine.administrative_supervisor_rating || 0,
            functional_supervisor_rating: assessLine.functional_supervisor_rating || 0,
            reviewer_rating: assessLine.reviewer_rating || 0
        });

      });

      // saving potential assessment lines 
      (r.potential_assessment || []).forEach(function (potLine) {
        const $select = $(
            `#pot-assess-body .pot-assess-sel[data-id="${potLine.id}"]`
        );

        const pType = $select.length
            ? $select.val()
            : potLine.assessment_type;

        lines.push({
            id: potLine.id,
            model: 'potential_assessment',
            assessment_type: pType,
            administrative_supervisor_rating: potLine.administrative_supervisor_rating || 0,
            functional_supervisor_rating: potLine.functional_supervisor_rating || 0,
            reviewer_rating: potLine.reviewer_rating || 0
        });

      });
 
        const $b = buttonProps.prop('disabled',true).html('<i class="fas fa-spinner fa-spin"></i> Saving…');
        const origHtml='<i class="fas fa-save"></i> '+$(this).text().trim().replace('Saving…','');
      
        rpc('/pms/api/save-ratings',{appraisal_id: App.currentId, section:false, lines}).then(res=>{
          // res.error ? toast(res.error,'error') : toast(res.message,'success');
          if (res.error){
            toast(res.error,'error')
          }else{
            toast(res.message,'success');
            openAppraisal(recId);
          }
      }).fail(
        e=>toast(e,'error')).always(()=> $b.prop('disabled',false).html(origHtml));
    }

  // ── Save ratings (AA/FA/Reviewer) via generic button ──
  // $(document).on('click','.save-comp-btn',function(){
  //   const sec=$(this).data('sec');
  //   const r=App.appraisal;
  //   const lines=[];
  //   console.log('TRAINING LINES 1', lines)

  //   if(sec === 'kra'){
  //     $('#kra-body tr').each(function(){
  //       const $row = $(this); const lid=$row.data('lid'); if(!lid) return;
  //       let line = {
  //             id: parseInt(lid),
  //             model: sec
  //         };

  //       const aa = $r.find('.kra-aa');
  //       const fa = $r.find('.kra-fa');
  //       const rev = $r.find('.kra-rev');
  //       if (aa.length && !aa.prop('disabled') && !aa.prop('readonly')) {
  //             const val = parseInt(aa.val());
  //             if (!isNaN(val)) line.administrative_supervisor_rating = val;
  //         }

  //         if (fa.length && !fa.prop('disabled') && !fa.prop('readonly')) {
  //             const val = parseInt(fa.val());
  //             if (!isNaN(val)) line.functional_supervisor_rating = val;
  //         }

  //         if (rev.length && !rev.prop('disabled') && !rev.prop('readonly')) {
  //             const val = parseInt(rev.val());
  //             if (!isNaN(val)) line.reviewer_rating = val;
  //         }

  //         lines.push(line);
  //     });
  //   } else if(['fc','lc'].includes(sec)){
  //     const tbodyId = sec==='fc' ? '#fc-body' : '#lc-body';
  //     $(tbodyId+' tr').each(function(){
  //       const $row=$(this); const lid=$row.data('lid'); if(!lid) return;
  //       let line = {
  //             id: parseInt(lid),
  //             model: sec
  //         };

  //       const aa = $row.find('.comp-aa');
  //       const fa = $row.find('.comp-fa');
  //       const rev = $row.find('.comp-rev');
  //       if (aa.length && !aa.prop('disabled') && !aa.prop('readonly')) {
  //           const val = parseInt(aa.val());
  //           if (!isNaN(val)) line.administrative_supervisor_rating = val;
  //       }

  //       if (fa.length && !fa.prop('disabled') && !fa.prop('readonly')) {
  //           const val = parseInt(fa.val());
  //           if (!isNaN(val)) line.functional_supervisor_rating = val;
  //       }

  //       if (rev.length && !rev.prop('disabled') && !rev.prop('readonly')) {
  //           const val = parseInt(rev.val());
  //           if (!isNaN(val)) line.reviewer_rating = val;
  //       }
  //       lines.push(line);
        
  //       // lines.push({
  //       //   id:parseInt(lid),
  //       //   model: sec,
  //       //   administrative_supervisor_rating:parseInt($row.find('.comp-aa').val())||0,
  //       //   functional_supervisor_rating:parseInt($row.find('.comp-fa').val())||0,
  //       //   reviewer_rating:parseInt($row.find('.comp-rev').val())||0});
  //     });
  //   } else if(sec==='training'){
  //     console.log('TRAINING LINES 2', lines)

  //     $('#training-body tr').each(function(){
  //       const $row=$(this);
  //       const lid= $row.data('lid'); 
  //       console.log('TRAINING LINES 44', lines)
  //       // if(!lid){
  //       //   console.log('TRAINING LINES 44', lines)
  //       //   return;
  //       // } 
  //       lines.push(
  //         {
  //           id:parseInt(lid),
  //           name: $row.find('.trn-name').val(),
  //           comments:$row.find('.trn-comment').val(),
  //           model: sec,
  //         });
  //         console.log('TRAINING LINES 3', lines)
  //     });
  //   } else if(sec==='current_assessment'){
  //     (r.current_assessment || []).forEach(function (assessLine) {
  //       const $select = $(
  //           `#curr-assess-body .curr-assess-sel[data-id="${assessLine.id}"]`
  //       );

  //       const aType = $select.length
  //           ? $select.val()
  //           : assessLine.assessment_type;

  //       lines.push({
  //           id: assessLine.id,
  //           model: 'current_assessment',
  //           assessment_type: aType,
  //           administrative_supervisor_rating: assessLine.administrative_supervisor_rating || 0,
  //           functional_supervisor_rating: assessLine.functional_supervisor_rating || 0,
  //           reviewer_rating: assessLine.reviewer_rating || 0
  //       });

  //     });

  //   } else if(sec==='potential_assessment'){ 
  //     (r.potential_assessment || []).forEach(function (potLine) {
  //       const $select = $(
  //           `#pot-assess-body .pot-assess-sel[data-id="${potLine.id}"]`
  //       );

  //       const pType = $select.length
  //           ? $select.val()
  //           : potLine.assessment_type;

  //       lines.push({
  //           id: potLine.id,
  //           model: 'potential_assessment',
  //           assessment_type: pType,
  //           administrative_supervisor_rating: potLine.administrative_supervisor_rating || 0,
  //           functional_supervisor_rating: potLine.functional_supervisor_rating || 0,
  //           reviewer_rating: potLine.reviewer_rating || 0
  //       });

  //     });
  //   }

  //   const $b=$(this).prop('disabled',true).html('<i class="fas fa-spinner fa-spin"></i> Saving…');
  //   const origHtml='<i class="fas fa-save"></i> '+$(this).text().trim().replace('Saving…','');
  //   rpc('/pms/api/save-ratings',{appraisal_id:App.currentId,section:sec,lines}).then(res=>{
  //     res.error?toast(res.error,'error'):toast(res.message,'success');
  //   }).fail(e=>toast(e,'error')).always(()=>$b.prop('disabled',false).html(origHtml));
  // });











  // let saveKRAFunction = function(){
  //     const lines=[];
  //     $('#kra-body tr').each(function(){
  //       const $r = $(this); 
  //       const lid = $r.data('lid'); if(!lid) return;
  //       lines.push({
  //         id:parseInt(lid),
  //         model: 'kra',
  //         administrative_supervisor_rating:parseInt($r.find('.kra-aa').val())||0,
  //         functional_supervisor_rating:parseInt($r.find('.kra-fa').val())||0,
  //         reviewer_rating: parseInt($r.find('.kra-rev').val())||0});
  //     });
  //     const $b=$(this).prop('disabled',true).html('<i class="fas fa-spinner fa-spin"></i> Saving…');
  //     rpc('/pms/api/save-ratings',{appraisal_id:App.currentId,section:'kra',lines}).then(r=>{
  //       r.error ? toast(r.error,'error') : toast(r.message,'success');
  //     }).fail(e=>toast(e,'error')).always(()=>$b.prop('disabled',false).html('<i class="fas fa-save"></i> Save Rating'));
  // }

  //   let saveKRAFunction = function(){
  //     const lines = [];
  //     $('#kra-body tr').each(function(){
  //         const $r = $(this);
  //         const lid = $r.data('lid');
  //         if(!lid) return;
  //         const aa = $r.find('.kra-aa');
  //         const fa = $r.find('.kra-fa');
  //         const rev = $r.find('.kra-rev');

  //         let line = {
  //             id: parseInt(lid),
  //             model: 'kra'
  //         };

  //         if (aa.length){
  //             line.administrative_supervisor_rating = parseInt(aa.val()) || 0;
  //         }
  //         if (fa.length){
  //             line.functional_supervisor_rating = parseInt(fa.val()) || 0;
  //         }
  //         if (rev.length){
  //             line.reviewer_rating = parseInt(rev.val()) || 0;
  //         }
  //         lines.push(line);

  //     });

  //     const $b=$(this)
  //         .prop('disabled',true)
  //         .html('<i class="fas fa-spinner fa-spin"></i> Saving…');
  //     console.log('wetin be line ', lines)
  //     rpc('/pms/api/save-ratings',{
  //         appraisal_id:App.currentId,
  //         // section:'kra',
  //         section: false,
  //         lines
  //     }).then(r=>{
  //         r.error ? toast(r.error,'error') : toast(r.message,'success');
  //     }).fail(e=>toast(e,'error'))
  //     .always(()=>{
  //         $b.prop('disabled',false)
  //           .html('<i class="fas fa-save"></i> Save Rating')
  //     });


  // }

  let saveKRAFunction = function(){
      const lines = [];
      $('#kra-body tr').each(function(){
          const $r = $(this);
          const lid = $r.data('lid');
          // if(!lid) return;

          let line = {
              id: parseInt(lid),
              model: 'kra'
          };

          const aa = $r.find('.kra-aa');
          const fa = $r.find('.kra-fa');
          const rev = $r.find('.kra-rev');

          // Only include a field if the input exists AND is not disabled/readonly
          // This prevents overwriting other roles' ratings with 0
          if (aa.length && !aa.prop('disabled') && !aa.prop('readonly')) {
              const val = parseInt(aa.val());
              if (!isNaN(val)) line.administrative_supervisor_rating = val;
          }

          if (fa.length && !fa.prop('disabled') && !fa.prop('readonly')) {
              const val = parseInt(fa.val());
              if (!isNaN(val)) line.functional_supervisor_rating = val;
          }

          if (rev.length && !rev.prop('disabled') && !rev.prop('readonly')) {
              const val = parseInt(rev.val());
              if (!isNaN(val)) line.reviewer_rating = val;
          }

          lines.push(line);
      });
      const $b=$(this).prop('disabled',true).html('<i class="fas fa-spinner fa-spin"></i> Saving…');
      console.log('wetin be line ', lines)
      rpc('/pms/api/save-ratings',{
          appraisal_id:App.currentId,
          section:'kra',
          // section: false,
          lines
      }).then(r=>{
          r.error ? toast(r.error,'error') : toast(r.message,'success');
      }).fail(e=>toast(e,'error'))
      .always(()=>{
          $b.prop('disabled',false)
            .html('<i class="fas fa-save"></i> Save KRA Rating')
      });

      // ... rest of your save logic
  };
  // ── KRA rating submit buttons ──
  $(document).on('click','#save-ratings-kra-aa,#save-ratings-kra-fa,#save-ratings-kra-rev',function(){
    saveKRAFunction();
  });

  $(document).on('click','#submit-aa-btn',function(){
    if(!confirm('Submit AA rating to Functional Appraiser?')) return;
    const $b=$(this).prop('disabled',true).html('<i class="fas fa-spinner fa-spin"></i>…');
    saveKRAFunction();
    saveCompLinesFunction($(this));
    rpc('/pms/api/submit-aa-rating',{appraisal_id:App.currentId}).then(r=>{
      r.error?toast(r.error,'error'):(toast(r.message,'success'),openAppraisal(App.currentId));
    }).fail(e=>toast(e,'error')).always(()=>$b.prop('disabled',false).html('<i class="fas fa-check"></i> Submit AA Rating'));
  });

  $(document).on('click','#submit-fa-btn',function(){
    if(!confirm('Submit FA rating to Reviewer?')) return;
    const $b=$(this).prop('disabled',true).html('<i class="fas fa-spinner fa-spin"></i>…');
    saveKRAFunction();
    saveCompLinesFunction($(this));
    rpc('/pms/api/submit-fa-rating',{appraisal_id:App.currentId}).then(r=>{
      r.error?toast(r.error,'error'):(toast(r.message,'success'),openAppraisal(App.currentId));
    }).fail(e=>toast(e,'error')).always(()=>$b.prop('disabled',false).html('<i class="fas fa-check"></i> Submit FA Rating'));
  });

  $(document).on('click','#return-btn',function(){
    // if(!confirm('Submit FA rating to Reviewer?')) return;
    const $b=$(this).prop('disabled',true).html('<i class="fas fa-spinner fa-spin"></i>…');
    rpc('/pms/api/return-rating',{appraisal_id:App.currentId}).then(r=>{
      r.error?toast(r.error,'error'):(toast(r.message,'success'),openAppraisal(App.currentId));
    }).fail(e=>toast(e,'error')).always(()=>$b.prop('disabled',false).html('<i class="fas fa-check"></i> Return Appraisal'));
  });

  $(document).on('click','#submit-rev-btn',function(){
    
    if(!confirm('Submit Reviewer rating to HR?')) return;
    const $b = $(this).prop('disabled',true).html('<i class="fas fa-spinner fa-spin"></i>…');
    saveKRAFunction()
    saveCompLinesFunction($(this));
    rpc('/pms/api/submit-reviewer-rating',{
      appraisal_id:App.currentId
    }).then(r=>{
      r.error ? toast(r.error,'error') : (toast(r.message,'success'), openAppraisal(App.currentId));
    }).fail(e=>toast(e,'error')).always(()=>$b.prop('disabled',false).html('<i class="fas fa-check"></i> Submit Reviewer Rating'));
  });

  // ── Training add line ──
  $('#training-add-line').on('click',function(){
    $('#training-body').append(`
      <tr data-lid="">
        <td><input type="text" class="trn-name" placeholder="Training description…"/></td>
        <td><textarea class="trn-comment" placeholder="Comments…"></textarea></td>
        <td>${App.user.name}</td>
      </tr>`);
  });

  // ── KRA add line ──
  $('#kra-add-line').on('click',function(){
    $('#kra-body').append(`
      <tr data-lid="">
        <td><input type="text" id="kra-line-id" class="kra-name" placeholder="Enter KRA…"/></td>
        <td><input type="number" class="midyear-review-input" value="" disabled="true"/></td>
        <td><input type="number" class="weightage-input kra-weightage" value="${5}" min="5" max="25"/></td>
        <td><input type="number" class="rating-input kra-self" value="${0}" min="1" max="4"/></td>
        <td><button class="row-del-kra" title="Remove"><i class="fas fa-trash-alt"></i></button></td>

      </tr>`);
  });

  $(document).on('click','.row-del-kra',function(){ 
    let id = $(this).closest('tr').data('lid')
    console.log("What is deleted LID ", id)
    DeleteKRALine(id, 'kra.section.line')
    $(this).closest('tr').remove();
  });

  // ── WORKFORCE PLANNING EVENTS ──────────────────────────────

  // Tab switching
  $(document).on('click','.wfp-tab',function(){
    const tab=$(this).data('tab');
    $('.wfp-tab').removeClass('active'); $(this).addClass('active');
    $('.wfp-tab-panel').removeClass('active'); $('#'+tab).addClass('active');
    // Load content for the activated tab
    renderWfpTabContent(tab);
    if(tab==='wfp-records') renderWfpRecordsTable();
  });

  // Record type selector → show/hide type-specific fields
  $(document).on('change','#wfp-f-type',function(){
    const t=$(this).val();
    $('.wfp-type-fields').hide();
    if(t) $('#wfp-fields-'+t).show();
  });

  // Create Record button (header)
  $(document).on('click','#wfp-create-btn',function(){ openWfpForm(); });

  // Refresh button on workforce page
  $(document).on('click','#wfp-refresh-btn',function(){
    WFP.loaded=false; WFP.records=[]; WFP.filtered=[];
    initWorkforcePage();
    $(this).find('i').addClass('fa-spin');
    setTimeout(function(){ $('#wfp-refresh-btn i').removeClass('fa-spin'); },900);
  });

  // Save WFP record
  $(document).on('click','#wfp-save-btn',function(){
    const payload = collectWfpForm();
    if(!payload) return;
    if(WFP.editId) payload.record_id = WFP.editId;
    const $b=$(this).prop('disabled',true).html('<i class="fas fa-spinner fa-spin"></i> Saving…');
    rpc('/pms/api/workforce-save', payload).then(function(r){
      if(r&&r.error){ toast(r.error,'error'); return; }
      toast(r&&r.message ? r.message : 'Saved successfully.','success');
      $('#modal-workforce').removeClass('open');
      setTimeout(function(){ if(!$('#modal-workforce').hasClass('open')) $('#modal-workforce').css('display',''); },250);
      // Reload data
      WFP.loaded=false;
      loadWfpData().always(function(){
        WFP.loaded=true;
        renderWfpOverview();
        renderWfpRecordsTable();
        // Refresh active tab
        const activeTab = $('.wfp-tab.active').data('tab');
        if(activeTab) renderWfpTabContent(activeTab);
      });
    }).fail(function(e){ toast('Save failed: '+e,'error'); })
      .always(function(){ $b.prop('disabled',false).html('<i class="fas fa-save"></i> Save Record'); });
  });

  // Edit from view modal
  $(document).on('click','#wfp-edit-from-view-btn',function(){
    const id=$(this).data('id');
    $('#modal-wfp-view').removeClass('open');
    setTimeout(function(){ $('#modal-wfp-view').css('display',''); },220);
    openWfpForm(null,id);
  });

  // Delete record
  $(document).on('click','.wfp-delete-btn',function(){
    const id=$(this).data('id');
    const rec=WFP.records.find(function(r){ return r.id===id; });
    if(!rec) return;
    if(!confirm('Delete record "'+rec.title+'"? This cannot be undone.')) return;
    rpc('/pms/api/workforce-delete',{record_id:id}).then(function(r){
      if(r&&r.error){ toast(r.error,'error'); return; }
      toast('Record deleted.','success');
      WFP.loaded=false;
      loadWfpData().always(function(){
        WFP.loaded=true;
        renderWfpOverview();
        renderWfpRecordsTable();
        const activeTab=$('.wfp-tab.active').data('tab');
        if(activeTab) renderWfpTabContent(activeTab);
      });
    }).fail(function(e){ toast('Delete failed: '+e,'error'); });
  });

  // Records tab — type filter
  $(document).on('click','#wfp-rec-filter-btn',function(){
    const t=$('#wfp-rec-filter-type').val();
    WFP.filtered = t ? WFP.records.filter(function(r){ return r.record_type===t; }) : WFP.records;
    renderWfpRecordsTable(WFP.filtered);
  });

  // Records tab — export
  $(document).on('click','#wfp-export-csv-btn',function(){ exportWfpCsv(WFP.filtered); });

  // ── REPORTING EVENTS ──────────────────────────────────────


  // Apply filters button — re-filter the already-loaded data
  $(document).on('click','#rpt-apply-btn', function(){
    applyReportFilters();
  });

  // Clear filters
  $(document).on('click','#rpt-clear-btn', function(){
    $('#rpt-filter-year,#rpt-filter-type,#rpt-filter-state,#rpt-filter-manager,#rpt-filter-employee,#rpt-filter-dept').val('');
    Rpt.filtered = Rpt.data;
    renderReportingResults(Rpt.filtered);
  });

  // View toggle — Cards / List
  $(document).on('click','.vt-btn', function(){
    const view = $(this).data('view');
    Rpt.view = view;
    $('.vt-btn').removeClass('active');
    $(this).addClass('active');
    if(view === 'cards'){
      $('#rpt-cards-view').show();
      $('#rpt-list-view').hide();
      renderReportCards(Rpt.filtered);
    } else {
      $('#rpt-cards-view').hide();
      $('#rpt-list-view').show();
      renderReportList(Rpt.filtered);
    }
  });

  // Export CSV
  $(document).on('click','#rpt-export-btn', function(){
    exportReportCSV(Rpt.filtered);
  });

  // Refresh on reporting page
  $(document).on('click','#refresh-btn', function(){
    const page = $('.nav-item.active').data('page');
    if(page === 'reporting'){
      Rpt.data = []; Rpt.filtered = [];
      loadReportingData({});
    }
  });

  // ── Modal dismiss ──
  $(document).on('click','[data-dismiss]',function(){
    const $m = $(`#${$(this).data('dismiss')}`);
    $m.removeClass('open');
    // Delay display:none until after transition
    setTimeout(() => { if (!$m.hasClass('open')) $m.css('display',''); }, 250);
  });
  $(document).on('click','.modal-ov',function(e){
    if($(e.target).hasClass('modal-ov')){
      $(this).removeClass('open');
      const $m = $(this);
      setTimeout(() => { if (!$m.hasClass('open')) $m.css('display',''); }, 250);
    }
  });

  // ── Sidebar toggle (mobile) ──
  $('#sb-toggle').on('click',()=>$('#sidebar').toggleClass('open'));
  function checkMobile(){ if($(window).width()<768) $('#sb-toggle').show(); else { $('#sb-toggle').hide(); $('#sidebar').removeClass('open'); } }
  $(window).on('resize',checkMobile); checkMobile();
});