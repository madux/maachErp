/**
 * report_portal.js
 * ================
 * Reads injected meta from <meta name="report-portal-meta">
 * All data calls go to /report-portal/* JSON endpoints.
 * Libraries expected: jQuery 3, Chart.js 4, jsPDF + autotable, SheetJS (xlsx)
 */

$(function () {
  'use strict';

  /* ── Read server-injected metadata ─────────────────────── */
  const META_EL = document.querySelector('meta[name="report-portal-meta"]');
  const META    = META_EL ? JSON.parse(META_EL.getAttribute('content')) : {};

  /* ── Palette for charts / branch dots ──────────────────── */
  const PALETTE = [
    '#f0a500','#3fb950','#f85149','#58a6ff','#bc8cff',
    '#39d353','#e3b341','#79c0ff','#ff7b72','#d2a8ff',
    '#ffa657','#a5d6ff',
  ];

  /* ═══════════════════════════════════════════════════════════
     UTILITIES
  ═══════════════════════════════════════════════════════════ */
  const fmt  = n => (n===null||n===undefined) ? '—'
    : parseFloat(n).toLocaleString('en-NG',{minimumFractionDigits:2,maximumFractionDigits:2});
  const fmtK = n => {
    const v = Math.abs(n);
    if (v>=1e9) return (n/1e9).toFixed(1)+'B';
    if (v>=1e6) return (n/1e6).toFixed(1)+'M';
    if (v>=1e3) return (n/1e3).toFixed(0)+'K';
    return fmt(n);
  };
  const esc = s => $('<span>').text(String(s||'')).html();
  const dateRange = () => ({ from: $('#g_date_from').val(), to: $('#g_date_to').val() });
  const fmtRange  = () => {
    const {from,to} = dateRange();
    const f = d => d ? new Date(d).toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric'}) : '';
    return from&&to ? `${f(from)} – ${f(to)}` : '';
  };

  function toast(msg, type='info') {
    const icons = {success:'fa-circle-check',error:'fa-circle-xmark',info:'fa-circle-info'};
    const cols  = {success:'var(--green)',error:'var(--red)',info:'var(--blue)'};
    const $t = $(`<div class="toast ${type}">
      <i class="fa-solid ${icons[type]}" style="color:${cols[type]}"></i>
      <span>${esc(msg)}</span></div>`);
    $('#toast-container').append($t);
    setTimeout(()=>$t.fadeOut(300,()=>$t.remove()), 3200);
  }

  /* ── JSON-RPC helper ────────────────────────────────────── */
  function rpc(url, params={}) {
    return $.ajax({
      url, type:'POST',
      contentType:'application/json',
      data: JSON.stringify({jsonrpc:'2.0',method:'call',id:Date.now(),params}),
    }).then(res=>{
      if (res.error) throw new Error(res.error.data?.message || res.error.message);
      return res.result;
    });
  }

  /* ── Collected company & branch selection ───────────────── */
  function selectedCompanyIds() {
    return $('.fr-check-company:checked').map((_,el)=>parseInt(el.value)).get();
  }
  function selectedBranchIds() {
    return $('.fr-check-branch:checked').map((_,el)=>parseInt(el.value)).get();
  }

  /* ═══════════════════════════════════════════════════════════
     INIT – populate filters from META
  ═══════════════════════════════════════════════════════════ */
  (function initFilters() {
    // Set dates
    const today = META.today || new Date().toISOString().slice(0,10);
    $('#g_date_to').val(today);
    $('#g_date_from').val(META.year_start || today.slice(0,4)+'-01-01');

    // Company chips in topbar dropdown
    const $coBox = $('#fr_company_filter_box');
    (META.companies||[]).forEach((co,i)=>{
      $coBox.append(`<label class="fr-check-label" style="display:flex;align-items:center;gap:6px;
        padding:4px 14px;cursor:pointer;font-size:12px;color:var(--text-2);
        border-bottom:1px solid var(--border-2)">
        <input type="checkbox" class="fr-check-company" value="${co.id}" ${i===0?'checked':''}/>
        <span>${esc(co.name)}</span></label>`);
    });

    // Company badge text
    const firstName = META.companies?.[0]?.name || META.company_name || '';
    $('#active_company_name').text(firstName);

    // Branches
    const $brBox = $('#fr_branch_filter_box');
    if ((META.branches||[]).length) {
      META.branches.forEach(br=>{
        $brBox.append(`<label class="fr-check-label" style="display:flex;align-items:center;gap:6px;
          padding:4px 14px;cursor:pointer;font-size:12px;color:var(--text-2);
          border-bottom:1px solid var(--border-2)">
          <input type="checkbox" class="fr-check-branch" value="${br.id}"/>
          <span>${esc(br.name)}</span></label>`);
      });
    } else {
      $brBox.html('<span style="padding:8px 14px;color:var(--muted);font-size:11px">No branches configured</span>');
    }
  })();

  /* ═══════════════════════════════════════════════════════════
     NAVIGATION
  ═══════════════════════════════════════════════════════════ */
  let currentPage = 'dashboard';

  function switchPage(page) {
    currentPage = page;
    $('.page-section').removeClass('active');
    $(`#page-${page}`).addClass('active');
    $('.tb-nav-link').removeClass('active');
    $(`.tb-nav-link[data-page="${page}"]`).addClass('active');
    $('.tb-dropdown-item').removeClass('active');
    $(`.tb-dropdown-item[data-page="${page}"]`).addClass('active');
    loadPage(page);
  }

  $(document).on('click','.tb-nav-link[data-page]',function(){switchPage($(this).data('page'))});
  $(document).on('click','.tb-nav-link[data-toggle]',function(e){
    e.stopPropagation();
    $(this).closest('.tb-nav-item').toggleClass('open');
  });
  $(document).on('click','.tb-dropdown-item[data-page]',function(){
    switchPage($(this).data('page'));
    $(this).closest('.tb-nav-item').removeClass('open');
  });
  $(document).on('click',function(){$('.tb-nav-item').removeClass('open')});
  $(document).on('click','.fr-tile[data-report]',function(){
    $('#fr_report_type').val($(this).data('report'));
    switchPage($(this).data('report'));
  });

  /* ── Run / export buttons ───────────────────────────────── */
  $('#btn_run').on('click',()=>{ loadPage(currentPage); toast('Report generated','success'); });
  $('#btn_export_excel').on('click', exportExcel);
  $('#btn_export_pdf').on('click',   exportPDF);
  $(document).on('click','#gl_expand_all',  ()=>toggleAll('#gl_tbody',true));
  $(document).on('click','#gl_collapse_all',()=>toggleAll('#gl_tbody',false));
  $(document).on('click','#con_expand_all', ()=>toggleAll('#con_tbody',true));

  /* ── Filter dropdowns (company / branch dropdowns in topbar) */
  $(document).on('click','#btn_company_toggle',function(e){
    e.stopPropagation();
    $('#company_dropdown').toggle();
    $('#branch_dropdown').hide();
  });
  $(document).on('click','#btn_branch_toggle',function(e){
    e.stopPropagation();
    $('#branch_dropdown').toggle();
    $('#company_dropdown').hide();
  });
  $(document).on('click',function(){ $('#company_dropdown,#branch_dropdown').hide(); });
  $(document).on('click','#company_dropdown,#branch_dropdown',e=>e.stopPropagation());

  /* ═══════════════════════════════════════════════════════════
     PAGE LOADER DISPATCH
  ═══════════════════════════════════════════════════════════ */
  function loadPage(page) {
    const map = {
      dashboard:       loadDashboard,
      general_ledger:  ()=>loadReport('general_ledger'),
      trial_balance:   ()=>loadReport('trial_balance'),
      profit_loss:     ()=>loadReport('profit_loss'),
      balance_sheet:   ()=>loadReport('balance_sheet'),
      tax_report:      ()=>loadReport('tax_report'),
      consolidated:    ()=>loadReport('consolidated'),
      monthly_expense: ()=>loadReport('monthly_expense'),
    };
    if (map[page]) map[page]();
  }

  /* ═══════════════════════════════════════════════════════════
     DASHBOARD
  ═══════════════════════════════════════════════════════════ */
  let _chartTrend=null, _chartBranch=null;

  function loadDashboard() {
    const {from,to} = dateRange();
    rpc('/report-portal/dashboard',{
      date_from:   from,
      date_to:     to,
      company_ids: selectedCompanyIds(),
      branch_ids:  selectedBranchIds(),
    }).then(renderDashboard)
      .catch(err=>toast('Dashboard error: '+err.message,'error'));
  }

  function renderDashboard(d) {
    const k = d.kpis;
    $('#kpi_income').text(fmtK(k.total_income));
    $('#kpi_expense').text(fmtK(k.total_expense));
    const net = k.net_pl;
    $('#kpi_net').text(fmtK(net)).css('color', net>=0?'var(--green)':'var(--red)');
    $('#kpi_net_delta').removeClass('up down').addClass(net>=0?'up':'down')
      .html(`<i class="fa-solid fa-caret-${net>=0?'up':'down'}"></i> ${net>=0?'Profitable':'Loss'}`);
    $('#kpi_payable').text(fmtK(k.total_payable));
    $('#kpi_tx').text((k.tx_count||0).toLocaleString());

    // Trend chart
    if (_chartTrend) _chartTrend.destroy();
    const tCtx = $('#chart_trend')[0].getContext('2d');
    _chartTrend = new Chart(tCtx,{
      type:'line',
      data:{
        labels: d.monthly.map(m=>m.month),
        datasets:[
          {label:'Income', data:d.monthly.map(m=>m.income),
           borderColor:'#3fb950',backgroundColor:'rgba(63,185,80,.07)',fill:true,tension:.35,pointRadius:3},
          {label:'Expense',data:d.monthly.map(m=>m.expense),
           borderColor:'#f85149',backgroundColor:'rgba(248,81,73,.07)',fill:true,tension:.35,pointRadius:3},
        ]
      },
      options:{
        responsive:true,maintainAspectRatio:false,
        plugins:{legend:{labels:{color:'#8b949e',font:{family:"'DM Sans'"}}},
                 tooltip:{backgroundColor:'#161b22',borderColor:'#30363d',borderWidth:1}},
        scales:{
          x:{ticks:{color:'#6e7681',font:{size:10}},grid:{color:'rgba(255,255,255,.03)'}},
          y:{ticks:{color:'#6e7681',font:{size:10},callback:v=>fmtK(v)},grid:{color:'rgba(255,255,255,.04)'}},
        }
      }
    });

    // Branch bar chart
    if (_chartBranch) _chartBranch.destroy();
    const bCtx = $('#chart_branch')[0].getContext('2d');
    if (d.branch_chart && d.branch_chart.length) {
      _chartBranch = new Chart(bCtx,{
        type:'bar',
        data:{
          labels:d.branch_chart.map(b=>b.branch.split(' ')[0]),
          datasets:[
            {label:'Income', data:d.branch_chart.map(b=>b.income),
             backgroundColor:'rgba(63,185,80,.7)',borderRadius:4},
            {label:'Expense',data:d.branch_chart.map(b=>b.expense),
             backgroundColor:'rgba(248,81,73,.7)',borderRadius:4},
          ]
        },
        options:{
          responsive:true,maintainAspectRatio:false,
          plugins:{legend:{labels:{color:'#8b949e',font:{family:"'DM Sans'"}}},
                   tooltip:{backgroundColor:'#161b22',borderColor:'#30363d',borderWidth:1}},
          scales:{
            x:{ticks:{color:'#6e7681',font:{size:10}},grid:{display:false}},
            y:{ticks:{color:'#6e7681',font:{size:10},callback:v=>fmtK(v)},grid:{color:'rgba(255,255,255,.04)'}},
          }
        }
      });
    } else {
      bCtx.clearRect(0,0,bCtx.canvas.width,bCtx.canvas.height);
      $('#chart_branch_empty').removeClass('d-none');
    }

    // Branch table
    const maxExp = Math.max(...(d.branch_chart||[]).map(b=>b.expense),1);
    let brHtml='';
    (d.branch_chart||[]).forEach((b,i)=>{
      const bal=b.income-b.expense;
      const pct=Math.round((b.expense/maxExp)*100);
      brHtml+=`<tr>
        <td><span class="branch-dot" style="background:${PALETTE[i%PALETTE.length]}"></span>${esc(b.branch)}
          <div class="bar-mini"><div class="bar-mini-fill" style="width:${pct}%;background:${PALETTE[i%PALETTE.length]}"></div></div></td>
        <td class="num" style="color:var(--green)">${fmt(b.income)}</td>
        <td class="num" style="color:var(--red)">${fmt(b.expense)}</td>
        <td class="num" style="color:${bal>=0?'var(--green)':'var(--red)'}">${fmt(Math.abs(bal))}</td>
        <td><span class="badge-state ${bal>0?'good':bal<0?'bad':'warn'}">${bal>0?'Surplus':bal<0?'Deficit':'Even'}</span></td>
      </tr>`;
    });
    $('#branch_tbody').html(brHtml||'<tr><td colspan="5" style="text-align:center;padding:24px;color:var(--muted)">No branch data</td></tr>');
    $('#branch_count_badge').text(`${(d.branch_chart||[]).length} branches`);

    // Company table
    const totalCoExp=(d.company_chart||[]).reduce((s,c)=>s+c.expense,0)||1;
    let coHtml='';
    (d.company_chart||[]).forEach((c,i)=>{
      coHtml+=`<tr>
        <td><span class="branch-dot" style="background:${PALETTE[i%PALETTE.length]}"></span>${esc(c.name)}</td>
        <td class="num">${fmt(c.expense)}</td>
        <td class="num" style="color:var(--amber)">${c.pct??((c.expense/totalCoExp*100).toFixed(1))}%</td>
      </tr>`;
    });
    $('#company_tbody').html(coHtml||'<tr><td colspan="3" style="text-align:center;padding:20px;color:var(--muted)">No data</td></tr>');

    // Top accounts
    let accHtml='';
    (d.top_accounts||[]).forEach(a=>{
      accHtml+=`<tr>
        <td><span class="acc-code">${esc(a.code)}</span>${esc(a.name)}</td>
        <td class="num">${fmt(a.amount)}</td>
      </tr>`;
    });
    $('#topaccount_tbody').html(accHtml||'<tr><td colspan="2" style="text-align:center;padding:20px;color:var(--muted)">No data</td></tr>');

    $('#dash_period').text(fmtRange());
  }

  /* ═══════════════════════════════════════════════════════════
     GENERIC REPORT LOADER
  ═══════════════════════════════════════════════════════════ */
  const RPT_CFG = {
    general_ledger:  { title_el:'#gl_title',  period_el:'#gl_period',  tbody:'#gl_tbody',  thead:null,         count:'#gl_count',  summary:'#gl_summary',  expand:true  },
    trial_balance:   { title_el:'#tb_title',  period_el:'#tb_period',  tbody:'#tb_tbody',  thead:null,         count:'#tb_count',  summary:'#tb_summary',  expand:false },
    profit_loss:     { title_el:'#pl_title',  period_el:'#pl_period',  tbody:'#pl_tbody',  thead:null,         count:'#pl_count',  summary:'#pl_summary',  expand:false },
    balance_sheet:   { title_el:'#bs_title',  period_el:'#bs_period',  tbody:'#bs_tbody',  thead:null,         count:'#bs_count',  summary:'#bs_summary',  expand:false },
    tax_report:      { title_el:'#tax_title', period_el:'#tax_period', tbody:'#tax_tbody', thead:null,         count:'#tax_count', summary:'#tax_summary', expand:false },
    consolidated:    { title_el:'#con_title', period_el:'#con_period', tbody:'#con_tbody', thead:'#con_thead', count:'#con_count', summary:'#con_summary', expand:true  },
    monthly_expense: { title_el:'#me_title',  period_el:'#me_period',  tbody:'#me_tbody',  thead:'#me_thead',  count:'#me_count',  summary:'#me_summary',  expand:false },
  };

  function loadReport(reportType) {
    const cfg = RPT_CFG[reportType];
    if (!cfg) return;
    const {from,to} = dateRange();
    const accType = $(`#${reportType}_acc_type`).val() || $('#gl_acc_type').val() || '';

    // Show skeleton
    const colCount = cfg.thead ? 6 : 5;
    $(cfg.tbody).html(
      Array(3).fill(`<tr class="skeleton-row">${'<td></td>'.repeat(colCount)}</tr>`).join('')
    );

    rpc('/report-portal/data',{
      report_type:  reportType,
      date_from:    from,
      date_to:      to,
      company_ids:  selectedCompanyIds(),
      branch_ids:   selectedBranchIds(),
      account_type: accType,
      account_ids:  [],
    }).then(res=>{
      if (!res.status){ toast(res.message||'Error','error'); return; }
      renderReport(res, cfg, reportType);
    }).catch(err=>toast('Error: '+err.message,'error'));
  }

  function renderReport(data, cfg, reportType) {
    $(cfg.title_el).text(data.title);
    $(cfg.period_el).text(fmtRange());

    // Dynamic thead (consolidated, monthly)
    if (cfg.thead && data.columns) {
      $(cfg.thead).html('<tr>' +
        data.columns.map((c,i)=>`<th class="${i>1?'num':''}">${esc(c)}</th>`).join('') +
        '</tr>');
    }

    // Summary banner
    if (data.summary && Object.keys(data.summary).length) {
      const $sb = $(cfg.summary);
      $sb.show().html(
        Object.entries(data.summary).map(([k,v])=>{
          const isNum = !isNaN(parseFloat(String(v).replace(/,/g,'')));
          const cls = isNum ? (parseFloat(String(v).replace(/,/g,''))>=0?'':'neg') : '';
          return `<div class="summary-item">
            <span class="summary-key">${esc(k)}</span>
            <span class="summary-val ${cls}">${esc(v)}</span></div>`;
        }).join('')
      );
    }

    // Table body
    const tbody = $(cfg.tbody);
    tbody.empty();
    let dataRowCount = 0;

    (data.rows||[]).forEach((row,ri)=>{
      const isGrand = row.is_group && !(row.detail_lines&&row.detail_lines.length);
      const hasDet  = row.is_group && row.detail_lines && row.detail_lines.length > 0;
      const cls     = row.is_group ? (isGrand?'tr-grand':'tr-group'+(hasDet?' expandable':'')) : '';

      const $tr = $('<tr>').addClass(cls);
      if (hasDet) $tr.attr('data-group','rg'+ri);

      (row.cells||[]).forEach((cell,ci)=>{
        const isNum = ci > 1 || (data.columns && ci > 1);
        const cellStr = String(cell||'');
        let tdCls = isNum ? 'num' : '';
        if (isNum && cellStr.startsWith('-')) tdCls+=' neg';
        $tr.append($('<td>').addClass(tdCls).html(
          ci===0 && !row.is_group
            ? `<span class="acc-code">${esc(cellStr)}</span>`
            : esc(cellStr)
        ));
      });
      tbody.append($tr);

      // Detail sub-rows
      if (hasDet) {
        $tr.prepend(
          $('<span class="expand-icon">').html('&#9654;').prependTo($tr.find('td:first'))
        );
        row.detail_lines.forEach(dl=>{
          const $det = $('<tr>').addClass('tr-detail').attr('data-parent','rg'+ri);
          $det.append(
            $('<td>').text(dl.date),
            $('<td>').html(`${esc(dl.desc)}<br><small style="color:#555">${esc(dl.ref)} ${dl.partner?'| '+esc(dl.partner):''}</small>`),
            $('<td>').text(dl.partner||''),
            $('<td>').text(dl.branch||''),
            $('<td class="num">').css('color',dl.raw<0?'var(--green)':'var(--red)').text(fmt(Math.abs(dl.raw))),
          );
          tbody.append($det);
        });
      }

      if (!row.is_group) dataRowCount++;
    });

    $(cfg.count).text(`${dataRowCount} rows`);
    if (cfg.expand) wireExpandCollapse(cfg.tbody);
  }

  /* ── Expand / collapse ─────────────────────────────────── */
  function wireExpandCollapse(sel) {
    $(sel).off('click.expand').on('click.expand','tr.tr-group.expandable[data-group]',function(){
      const grp = $(this).data('group');
      const open = !$(this).hasClass('open');
      $(this).toggleClass('open', open);
      $(`[data-parent="${grp}"]`).toggleClass('show', open);
    });
  }
  function toggleAll(sel, open) {
    $(`${sel} tr.tr-group.expandable[data-group]`).each(function(){
      $(this).toggleClass('open', open);
      $(`[data-parent="${$(this).data('group')}"]`).toggleClass('show', open);
    });
  }

  /* ── Filter changes ─────────────────────────────────────── */
  $(document).on('change','#con_acc_type',()=>loadReport('consolidated'));
  $(document).on('change','#gl_acc_type', ()=>loadReport('general_ledger'));

  /* ═══════════════════════════════════════════════════════════
     EXPORT HELPERS
  ═══════════════════════════════════════════════════════════ */
  function getExportData() {
    const lbls = {
      general_ledger:'General Ledger', trial_balance:'Trial Balance',
      profit_loss:'Profit & Loss',     balance_sheet:'Balance Sheet',
      tax_report:'Tax Report',         consolidated:'Consolidated District Report',
      monthly_expense:'Monthly Expenditure',
    };
    const tbMap = {
      general_ledger:'#gl_tbody',  trial_balance:'#tb_tbody',
      profit_loss:'#pl_tbody',     balance_sheet:'#bs_tbody',
      tax_report:'#tax_tbody',     consolidated:'#con_tbody',
      monthly_expense:'#me_tbody',
    };
    const thMap = { consolidated:'#con_thead', monthly_expense:'#me_thead' };

    const cfg = { tbody: tbMap[currentPage], thead: thMap[currentPage]||null };
    if (!cfg.tbody) return null;

    let headers = [];
    if (cfg.thead) {
      $(`${cfg.thead} th`).each(function(){ headers.push($(this).text().trim()); });
    } else {
      $(`${cfg.tbody}`).closest('table').find('thead th').each(function(){ headers.push($(this).text().trim()); });
    }

    const rows = [];
    $(`${cfg.tbody} tr`).each(function(){
      if ($(this).hasClass('tr-detail')) return;
      const cells=[];
      $(this).find('td').each(function(){ cells.push($(this).text().replace(/\s+/g,' ').trim()); });
      if (cells.some(c=>c)) rows.push(cells);
    });

    return { title: lbls[currentPage]||currentPage, period: fmtRange(), headers, rows };
  }

  /* ── Excel ─────────────────────────────────────────────── */
  function exportExcel() {
    const data = getExportData();
    if (!data){ toast('No table to export','info'); return; }
    const {title,period,headers,rows} = data;
    const WB = XLSX.utils.book_new();
    const ws_data = [[title],[`Period: ${period}`],[`Generated: ${new Date().toLocaleString()}`],[],headers,...rows];
    const WS = XLSX.utils.aoa_to_sheet(ws_data);
    WS['!cols'] = headers.map((_,ci)=>({
      wch: Math.min(Math.max(headers[ci].length, ...rows.map(r=>String(r[ci]||'').length))+2, 52)
    }));
    if (headers.length>1) WS['!merges']=[
      {s:{r:0,c:0},e:{r:0,c:headers.length-1}},
      {s:{r:1,c:0},e:{r:1,c:headers.length-1}},
      {s:{r:2,c:0},e:{r:2,c:headers.length-1}},
    ];
    XLSX.utils.book_append_sheet(WB, WS, title.slice(0,31));
    const WS2 = XLSX.utils.aoa_to_sheet([
      ['Report',title],['Period',period],['Generated',new Date().toLocaleString()],
      ['Rows',rows.length],['Columns',headers.length],
    ]);
    WS2['!cols']=[{wch:12},{wch:44}];
    XLSX.utils.book_append_sheet(WB, WS2, 'Info');
    const fn=`${currentPage}_${new Date().toISOString().slice(0,10)}.xlsx`;
    XLSX.writeFile(WB, fn);
    toast(`Excel saved: ${fn}`,'success');
  }

  /* ── PDF ───────────────────────────────────────────────── */
  function exportPDF() {
    const data = getExportData();
    if (!data){ toast('No table to export','info'); return; }
    const {title,period,headers,rows} = data;
    const orient = headers.length>6?'landscape':'portrait';
    const {jsPDF} = window.jspdf;
    const doc  = new jsPDF({orientation:orient,unit:'pt',format:'a4'});
    const pageW= doc.internal.pageSize.getWidth();
    const pageH= doc.internal.pageSize.getHeight();
    const ML   = 36;

    const INK=[21,27,34], AMB=[240,165,0], ALT=[246,248,250],
          WHT=[255,255,255], BOR=[210,218,226], MUT=[140,150,165];

    function drawHeader(){
      doc.setFillColor(...INK); doc.rect(0,0,pageW,50,'F');
      doc.setFillColor(...AMB); doc.roundedRect(ML,11,28,28,3,3,'F');
      doc.setFont('helvetica','bold'); doc.setFontSize(13); doc.setTextColor(21,27,34);
      doc.text('F',ML+8,30);
      doc.setFont('helvetica','bold'); doc.setFontSize(12); doc.setTextColor(...AMB);
      doc.text(title,ML+38,23);
      doc.setFont('helvetica','normal'); doc.setFontSize(8); doc.setTextColor(180,190,205);
      doc.text(period,ML+38,36);
      doc.setFontSize(7); doc.setTextColor(...MUT);
      doc.text(`Generated: ${new Date().toLocaleString()}`,pageW-ML,36,{align:'right'});
    }

    const colStyles={};
    headers.forEach((_,i)=>{ if(i>1) colStyles[i]={halign:'right'}; });
    colStyles[0]={cellWidth:orient==='landscape'?65:50};
    const grandIdx=rows.length-1;

    doc.autoTable({
      head:[headers], body:rows, startY:58,
      margin:{left:ML,right:ML,top:58,bottom:36},
      styles:{font:'helvetica',fontSize:8,
              cellPadding:{top:4,bottom:4,left:5,right:5},
              lineColor:BOR,lineWidth:.25,textColor:[40,50,60],
              overflow:'linebreak',minCellHeight:15},
      headStyles:{fillColor:INK,textColor:AMB,fontStyle:'bold',fontSize:8,halign:'left',lineWidth:0},
      columnStyles:colStyles,
      didParseCell(h){
        if(h.row.index===grandIdx){
          h.cell.styles.fillColor=AMB; h.cell.styles.textColor=INK;
          h.cell.styles.fontStyle='bold'; h.cell.styles.fontSize=9;
        } else {
          h.cell.styles.fillColor=h.row.index%2===0?ALT:WHT;
        }
      },
      didDrawPage(h){
        drawHeader();
        doc.setDrawColor(...BOR); doc.setLineWidth(.4);
        doc.line(ML,pageH-26,pageW-ML,pageH-26);
        doc.setFontSize(7); doc.setTextColor(...MUT);
        doc.text('FinanceIQ · Financial Reports',ML,pageH-14);
        doc.text(`Page ${h.pageNumber} of ${doc.internal.getNumberOfPages()}`,pageW/2,pageH-14,{align:'center'});
        doc.text(title,pageW-ML,pageH-14,{align:'right'});
      },
    });

    const fn=`${currentPage}_${new Date().toISOString().slice(0,10)}.pdf`;
    doc.save(fn);
    toast(`PDF saved: ${fn}`,'success');
  }

  /* ═══════════════════════════════════════════════════════════
     BOOT
  ═══════════════════════════════════════════════════════════ */
  loadDashboard();
});
