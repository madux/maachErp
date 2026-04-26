/* ============================================================
   CRM PORTAL — MAIN JS
   ============================================================ */

const CRM = (() => {

    // ── State ──────────────────────────────────────────────────
    let state = {
        userData:    {},
        activeMenu:  'dashboard',
        records:     [],
        salesOrders: [],
        stages:      [],
        currentRecord: null,
        chartInstances: {},
    };

    // ── Init ───────────────────────────────────────────────────
    function init() {
        const meta = document.querySelector('meta[name="crm-user-data"]');
        if (meta) {
            try { state.userData = JSON.parse(meta.getAttribute('content')); } catch(e) {}
        }
        state.activeMenu = state.userData.active_menu || 'dashboard';

        // Topbar user
        document.getElementById('user-name').textContent = state.userData.user_name || 'User';
        document.getElementById('user-avatar').textContent =
            (state.userData.user_name || 'U').charAt(0).toUpperCase();

        // Sidebar toggle
        document.getElementById('sidebar-toggle').addEventListener('click', () => {
            document.getElementById('sidebar').classList.toggle('collapsed');
        });

        // Nav links
        document.querySelectorAll('[data-menu]').forEach(el => {
            el.addEventListener('click', e => {
                e.preventDefault();
                switchMenu(el.dataset.menu);
            });
        });

        switchMenu(state.activeMenu);
    }

    // ── Menu Switching ─────────────────────────────────────────
    function switchMenu(menu) {
        state.activeMenu = menu;
        document.querySelectorAll('[data-menu]').forEach(el =>
            el.classList.toggle('active', el.dataset.menu === menu));

        const titles = {
            dashboard: 'Dashboard', leads: 'Leads',
            opportunities: 'Opportunities', sales: 'Sales', pipeline: 'Pipeline'
        };
        document.getElementById('page-title').textContent = titles[menu] || 'CRM Portal';

        // Hide all views
        ['view-dashboard','view-list','view-pipeline'].forEach(id => {
            document.getElementById(id).style.display = 'none';
        });

        if (menu === 'dashboard') {
            document.getElementById('view-dashboard').style.display = '';
            loadDashboard();
        } else if (menu === 'pipeline') {
            document.getElementById('view-pipeline').style.display = '';
            loadPipeline();
        } else {
            document.getElementById('view-list').style.display = '';
            loadList(menu);
        }
    }

    // ── API Helper ─────────────────────────────────────────────
    async function rpc(url, params = {}) {
        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ jsonrpc: '2.0', method: 'call', params })
        });
        const data = await resp.json();
        if (data.error) throw new Error(data.error.data?.message || data.error.message);
        return data.result;
    }

    // ── Toast ──────────────────────────────────────────────────
    function toast(msg, type = 'success') {
        const container = document.getElementById('toast');
        const el = document.createElement('div');
        el.className = `toast-msg ${type}`;
        el.textContent = msg;
        container.appendChild(el);
        setTimeout(() => el.remove(), 3500);
    }

    // ── Dashboard ──────────────────────────────────────────────
    async function loadDashboard() {
        try {
            const d = await rpc('/crm-portal/api/dashboard');
            document.getElementById('kpi-leads').textContent = d.leads_count;
            document.getElementById('kpi-opps').textContent  = d.opps_count;
            document.getElementById('kpi-won').textContent   = d.won_count;
            document.getElementById('kpi-lost').textContent  = d.lost_count;
            document.getElementById('kpi-rev').textContent   = formatMoney(d.total_revenue);

            renderPipelineChart(d.pipeline);
            renderMonthlyChart(d.monthly_won);
        } catch(e) {
            toast('Failed to load dashboard: ' + e.message, 'error');
        }
    }

    function renderPipelineChart(pipeline) {
        const ctx = document.getElementById('chart-pipeline').getContext('2d');
        if (state.chartInstances.pipeline) state.chartInstances.pipeline.destroy();
        state.chartInstances.pipeline = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: pipeline.map(p => p.stage),
                datasets: [{
                    label: 'Opportunities',
                    data: pipeline.map(p => p.count),
                    backgroundColor: '#714B67CC',
                    borderRadius: 6,
                }, {
                    label: 'Expected Revenue',
                    data: pipeline.map(p => p.revenue),
                    backgroundColor: '#00A09D88',
                    borderRadius: 6,
                    yAxisID: 'y2',
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                scales: {
                    y:  { beginAtZero: true, title: { display: true, text: 'Count' } },
                    y2: { beginAtZero: true, position: 'right', title: { display: true, text: 'Revenue' }, grid: { drawOnChartArea: false } }
                },
                plugins: { legend: { position: 'bottom' } }
            }
        });
    }

    function renderMonthlyChart(monthly) {
        const ctx = document.getElementById('chart-monthly').getContext('2d');
        if (state.chartInstances.monthly) state.chartInstances.monthly.destroy();
        state.chartInstances.monthly = new Chart(ctx, {
            type: 'line',
            data: {
                labels: monthly.map(m => m.month),
                datasets: [{
                    label: 'Won Deals',
                    data: monthly.map(m => m.count),
                    borderColor: '#28a745',
                    backgroundColor: '#28a74522',
                    fill: true, tension: 0.4, pointRadius: 5,
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: true,
                scales: { y: { beginAtZero: true } },
                plugins: { legend: { position: 'bottom' } }
            }
        });
    }

    // ── List View ──────────────────────────────────────────────
    async function loadList(menu) {
        const tbody = document.getElementById('list-tbody');
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:40px"><div class="spinner"></div></td></tr>`;

        try {
            let records;
            let isSales = menu === 'sales';

            if (isSales) {
                records = await rpc('/crm-portal/api/sales');
                state.salesOrders = records;
            } else {
                const typeMap = { leads: 'lead', opportunities: 'opportunity' };
                records = await rpc('/crm-portal/api/records', { record_type: typeMap[menu] || 'all' });
                state.records = records;
            }

            renderList(records, isSales);
        } catch(e) {
            toast('Failed to load records: ' + e.message, 'error');
            tbody.innerHTML = `<tr><td colspan="8" class="empty-state"><i class="fa fa-exclamation-circle"></i><p>${e.message}</p></td></tr>`;
        }
    }

    function renderList(records, isSales) {
        const tbody = document.getElementById('list-tbody');
        const thead = document.getElementById('list-thead');

        if (isSales) {
            thead.innerHTML = `
                <tr>
                    <th>Reference</th><th>Customer</th><th>Date</th>
                    <th>Status</th><th>Invoice</th><th>Total</th><th>Actions</th>
                </tr>`;
        } else {
            thead.innerHTML = `
                <tr>
                    <th>Name</th><th>Type</th><th>Customer</th><th>Stage</th>
                    <th>Probability</th><th>Expected Revenue</th><th>Deadline</th><th>Actions</th>
                </tr>`;
        }

        if (!records.length) {
            tbody.innerHTML = `<tr><td colspan="8"><div class="empty-state"><i class="fa fa-inbox"></i><p>No records found</p></div></td></tr>`;
            return;
        }

        tbody.innerHTML = records.map(r => {
            if (isSales) {
                return `
                <tr data-so-id="${r.id}">
                    <td><strong>${r.name}</strong></td>
                    <td>${r.partner_name}</td>
                    <td>${r.date_order}</td>
                    <td>${soBadge(r.state)}</td>
                    <td><span class="badge badge-draft">${r.invoice_status || '-'}</span></td>
                    <td>${formatMoney(r.amount_total)}</td>
                    <td>
                        ${r.state === 'draft' ? `<button class="btn btn-success btn-sm confirm-so" data-id="${r.id}"><i class="fa fa-check"></i> Confirm</button>` : ''}
                        ${r.state === 'sale' ? `<button class="btn btn-info btn-sm gen-invoice" data-id="${r.id}"><i class="fa fa-file-text"></i> Invoice</button>` : ''}
                    </td>
                </tr>`;
            } else {
                return `
                <tr data-crm-id="${r.id}" class="crm-row">
                    <td><strong>${escHtml(r.name)}</strong></td>
                    <td>${typeBadge(r.type, r.is_won, r.active)}</td>
                    <td>${escHtml(r.partner_name)}</td>
                    <td>${escHtml(r.stage)}</td>
                    <td>${r.probability}%</td>
                    <td>${formatMoney(r.expected_revenue)}</td>
                    <td>${r.date_deadline || '-'}</td>
                    <td>
                        <button class="btn btn-primary btn-sm open-crm" data-id="${r.id}"><i class="fa fa-eye"></i></button>
                        ${!r.is_won ? `<button class="btn btn-danger btn-sm del-crm" data-id="${r.id}"><i class="fa fa-trash"></i></button>` : ''}
                    </td>
                </tr>`;
            }
        }).join('');

        // Bind row clicks
        tbody.querySelectorAll('.crm-row').forEach(row => {
            row.addEventListener('click', e => {
                if (e.target.closest('button')) return;
                openCrmForm(row.dataset.crmId);
            });
        });
        tbody.querySelectorAll('.open-crm').forEach(btn =>
            btn.addEventListener('click', e => { e.stopPropagation(); openCrmForm(btn.dataset.id); }));
        tbody.querySelectorAll('.del-crm').forEach(btn =>
            btn.addEventListener('click', e => { e.stopPropagation(); deleteRecord(btn.dataset.id); }));
        tbody.querySelectorAll('.confirm-so').forEach(btn =>
            btn.addEventListener('click', e => { e.stopPropagation(); confirmSO(btn.dataset.id); }));
        tbody.querySelectorAll('.gen-invoice').forEach(btn =>
            btn.addEventListener('click', e => { e.stopPropagation(); generateInvoice(btn.dataset.id); }));
    }

    // ── Pipeline View ──────────────────────────────────────────
    async function loadPipeline() {
        const board = document.getElementById('pipeline-board');
        board.innerHTML = '<div class="spinner"></div>';
        try {
            const [records, stages] = await Promise.all([
                rpc('/crm-portal/api/records', { record_type: 'opportunity' }),
                rpc('/crm-portal/api/stages')
            ]);
            state.stages = stages;

            board.innerHTML = stages.map(stage => {
                const stageCards = records.filter(r => r.stage_id === stage.id);
                return `
                <div class="pipeline-col">
                    <div class="pipeline-col-header">
                        <span>${escHtml(stage.name)}</span>
                        <span>${stageCards.length}</span>
                    </div>
                    ${stageCards.length ? stageCards.map(r => `
                        <div class="pipeline-card" data-id="${r.id}">
                            <div class="pc-name">${escHtml(r.name)}</div>
                            <div class="pc-partner">${escHtml(r.partner_name)}</div>
                            <div class="pc-rev">${formatMoney(r.expected_revenue)}</div>
                            <div class="pc-prob">${r.probability}% probability</div>
                        </div>
                    `).join('') : '<div style="color:#aaa;font-size:.8rem;text-align:center;padding:10px">No records</div>'}
                </div>`;
            }).join('');

            board.querySelectorAll('.pipeline-card').forEach(card =>
                card.addEventListener('click', () => openCrmForm(card.dataset.id)));
        } catch(e) {
            toast('Failed to load pipeline: ' + e.message, 'error');
            board.innerHTML = '';
        }
    }

    // ── CRM Form Modal ─────────────────────────────────────────
    async function openCrmForm(id) {
        try {
            const data = await rpc(`/crm-portal/api/record/${id}`);
            if (data.error) { toast(data.error, 'error'); return; }
            state.currentRecord = data;
            state.stages = data.stages;
            renderCrmForm(data);
            document.getElementById('crmModal').classList.add('open');
        } catch(e) {
            toast('Failed to load record: ' + e.message, 'error');
        }
    }

    function renderCrmForm(r) {
        const isEditable = !r.is_won;
        const dis = isEditable ? '' : 'disabled';

        // Stage options
        const stageOpts = r.stages.map(s =>
            `<option value="${s.id}" ${s.id === r.stage_id ? 'selected' : ''}>${escHtml(s.name)}</option>`
        ).join('');

        // Partner options
        const partnerOpts = `<option value="">-- Select Customer --</option>` +
            (r.partner_id ? `<option value="${r.partner_id}" selected>${escHtml(r.partner_name)}</option>` : '');

        // Sale orders table
            console.log('sooo', r.sale_orders);

        const soHtml = r.sale_orders.length ? `
            <table class="so-table">
                <thead>
                    <tr>
                        <th>Order</th>
                        <th>Status</th>
                        <th>Total</th>
                        <th>Date</th>
                        <th>Actions</th>
                        <th>Cancel</th>
                    </tr>
                </thead>
                <tbody>
                ${r.sale_orders.map(so => `
                    <tr>
                        <td>${so.name}</td>
                        <td>${soBadge(so.state)}</td>
                        <td>${formatMoney(so.amount_total)}</td>
                        <td>${so.date_order}</td>
                        <td>
                            ${so.state === 'draft' ? `<button class="btn btn-success btn-sm confirm-so" data-id="${so.id}"><i class="fa fa-check"></i> Confirm</button>` : ''}
                            ${so.state === 'sale' ? `<button class="btn btn-info btn-sm gen-invoice" data-id="${so.id}"><i class="fa fa-file-invoice"></i> Invoice</button>` : ''}
                        </td>
                        <td>
                            ${so.state === 'draft' ? `<button class="btn btn-warning btn-sm cancel-so" data-id="${so.id}"><i class="fa fa-check"></i> Cancel</button>` : ''}
                        </td>
                    </tr>`).join('')}
                </tbody>
            </table>` : '<p style="color:#aaa;font-size:.83rem">No sales orders linked.</p>';

        document.getElementById('modal-form-body').innerHTML = `
            <div class="form-grid">
                <div class="form-group full">
                    <label>Name / Title *</label>
                    <input id="f-name" value="${escHtml(r.name)}" ${dis} placeholder="Opportunity name"/>
                </div>
                <div class="form-group">
                    <label>Stage</label>
                    <select id="f-stage" ${dis}>${stageOpts}</select>
                </div>
                <div class="form-group">
                    <label>Probability (%)</label>
                    <input id="f-prob" type="number" min="0" max="100" value="${r.probability}" ${dis}/>
                </div>
                <div class="form-group">
                    <label>Expected Revenue</label>
                    <input id="f-rev" type="number" min="0" value="${r.expected_revenue}" ${dis}/>
                </div>
                <div class="form-group">
                    <label>Expected Close Date</label>
                    <input id="f-deadline" type="date" value="${r.date_deadline}" ${dis}/>
                </div>
                <div class="form-group full" style="border-top:1px solid #eee;padding-top:10px;margin-top:4px">
                    <label>Customer</label>
                    <select id="f-partner" ${dis}>${partnerOpts}</select>
                    <small style="color:#888">Can't find customer? Fill fields below</small>
                </div>
                <div class="form-group">
                    <label>Customer Name (manual)</label>
                    <input id="f-partner-name" value="${escHtml(r.partner_name_manual)}" ${dis} placeholder="If not in list"/>
                </div>
                <div class="form-group">
                    <label>Email</label>
                    <input id="f-email" type="email" value="${escHtml(r.email_from)}" ${dis}/>
                </div>
                <div class="form-group">
                    <label>Phone</label>
                    <input id="f-phone" value="${escHtml(r.phone)}" ${dis}/>
                </div>
                <div class="form-group">
                    <label>Address</label>
                    <input id="f-street" value="${escHtml(r.street)}" ${dis}/>
                </div>
                <div class="form-group full">
                    <label>Additional Notes</label>
                    <textarea id="f-desc" ${dis}>${escHtml(r.description)}</textarea>
                </div>
            </div>

            <div style="margin-top:18px;border-top:1px solid #eee;padding-top:14px">
                <h4 style="font-size:.9rem;margin-bottom:8px;color:var(--primary)">
                    <i class="fa fa-shopping-cart"></i> Sales Orders
                </h4>
                ${soHtml}
            </div>
        `;

        // Modal footer buttons
        const footer = document.getElementById('modal-footer');
        footer.innerHTML = '';

        // Always show Close
        addBtn(footer, '<i class="fa fa-arrow-down"></i> Cancel Opportunity', 'btn-danger', () => cancelOpportunity(r.id));
        addBtn(footer, 'Close', 'btn-secondary', () => closeModal());

        if (r.type === 'lead') {
            addBtn(footer, '<i class="fa fa-arrow-up"></i> Convert to Opportunity', 'btn-warning', () => convertOpportunity(r.id));
        } 

        if (!r.is_won && isEditable) {
            addBtn(footer, '<i class="fa fa-save"></i> Save', 'btn-primary', () => saveRecord(r.id));
            addBtn(footer, '<i class="fa fa-trophy"></i> Mark Won', 'btn-success', () => markWon(r.id));
            addBtn(footer, '<i class="fa fa-times-circle"></i> Mark Lost', 'btn-danger', () => markLost(r.id));
            if (r.type === 'opportunity') {
                addBtn(footer, '<i class="fa fa-file-text"></i> Create Quotation', 'btn-info', () => createQuotation(r.id));
            }
        }
         

        addBtn(footer, '<i class="fa fa-phone"></i> Call', 'btn-outline', () => logCall(r.id));
        addBtn(footer, '<i class="fa fa-comment"></i> SMS', 'btn-outline', () => openSmsModal(r.id));

        // Bind SO actions within the modal
        footer.closest('.modal').querySelectorAll('.confirm-so').forEach(btn =>
            btn.addEventListener('click', () => confirmSO(btn.dataset.id, r.id)));

        footer.closest('.modal').querySelectorAll('.cancel-so').forEach(btn =>
            btn.addEventListener('click', () => cancelSO(btn.dataset.id, r.id)));

        footer.closest('.modal').querySelectorAll('.gen-invoice').forEach(btn =>
            btn.addEventListener('click', () => generateInvoice(btn.dataset.id)));

        document.getElementById('modal-title').textContent =
            (r.is_won ? '🏆 ' : '') + escHtml(r.name);
    }

    function addBtn(container, html, cls, handler) {
        const btn = document.createElement('button');
        btn.className = `btn ${cls}`;
        btn.innerHTML = html;
        btn.addEventListener('click', handler);
        container.appendChild(btn);
    }

    function closeModal() {
        document.getElementById('crmModal').classList.remove('open');
        state.currentRecord = null;
    }

    // ── CRUD Actions ───────────────────────────────────────────
    async function saveRecord(id) {
        const vals = {
            name:             document.getElementById('f-name').value.trim(),
            stage_id:         parseInt(document.getElementById('f-stage').value) || false,
            probability:      parseFloat(document.getElementById('f-prob').value) || 0,
            expected_revenue: parseFloat(document.getElementById('f-rev').value) || 0,
            date_deadline:    document.getElementById('f-deadline').value || false,
            partner_id:       parseInt(document.getElementById('f-partner').value) || false,
            partner_name:     document.getElementById('f-partner-name').value.trim(),
            email_from:       document.getElementById('f-email').value.trim(),
            phone:            document.getElementById('f-phone').value.trim(),
            street:           document.getElementById('f-street').value.trim(),
            description:      document.getElementById('f-desc').value.trim(),
        };
        try {
            const res = await rpc(`/crm-portal/api/update/${id}`, { vals });
            if (res.error) { toast(res.error, 'error'); return; }
            toast('Record saved successfully');
            closeModal();
            reloadCurrentView();
        } catch(e) { toast(e.message, 'error'); }
    }

    async function deleteRecord(id) {
        if (!confirm('Delete this record? This cannot be undone.')) return;
        try {
            const res = await rpc(`/crm-portal/api/delete/${id}`);
            if (res.error) { toast(res.error, 'error'); return; }
            toast('Record deleted');
            reloadCurrentView();
        } catch(e) { toast(e.message, 'error'); }
    }

    async function convertOpportunity(id) {
        try {
            const res = await rpc(`/crm-portal/api/action/convert_opportunity/${id}`);
            if (res.error) { toast(res.error, 'error'); return; }
            toast('Converted to Opportunity!', 'info');
            closeModal();
            reloadCurrentView();
        } catch(e) { toast(e.message, 'error'); }
    }

    async function cancelOpportunity(id) {
        try {
            const res = await rpc(`/crm-portal/api/action/cancel_opportunity/${id}`);
            if (res.error) { toast(res.error, 'error'); return; }
            toast('Cancelled to Opportunity!', 'info');
            closeModal();
            reloadCurrentView();
        } catch(e) { toast(e.message, 'error'); }
    }

    async function markWon(id) {
        if (!confirm('Mark this opportunity as Won?')) return;
        try {
            const res = await rpc(`/crm-portal/api/action/mark_won/${id}`);
            if (res.error) { toast(res.error, 'error'); return; }
            toast('🏆 Marked as Won!', 'success');
            closeModal();
            reloadCurrentView();
        } catch(e) { toast(e.message, 'error'); }
    }

    async function markLost(id) {
        if (!confirm('Mark this opportunity as Lost?')) return;
        try {
            const res = await rpc(`/crm-portal/api/action/mark_lost/${id}`);
            if (res.error) { toast(res.error, 'error'); return; }
            toast('Marked as Lost', 'info');
            closeModal();
            reloadCurrentView();
        } catch(e) { toast(e.message, 'error'); }
    }

    async function createQuotation(crmId) {
        try {
            const res = await rpc(`/crm-portal/api/action/create_quotation/${crmId}`);
            if (res.error) { toast(res.error, 'error'); return; }
            toast(`Quotation ${res.sale_order_name} created!`, 'info');
            // Reload form to show the new SO
            openCrmForm(crmId);
        } catch(e) { toast(e.message, 'error'); }
    }

    async function confirmSO(soId, crmId) {
        if (!confirm('Confirm this sale order?')) return;
        try {
            const res = await rpc(`/crm-portal/api/action/confirm_quotation/${soId}`);
            if (res.error) { toast(res.error, 'error'); return; }
            toast('Sale order confirmed!', 'success');
            if (crmId) openCrmForm(crmId);
            else reloadCurrentView();
        } catch(e) { toast(e.message, 'error'); }
    }

    async function cancelSO(soId, crmId) {
        if (!confirm('Cancel this sale order?')) return;
        try {
            const res = await rpc(`/crm-portal/api/action/cancel_quotation/${soId}`);
            if (res.error) { toast(res.error, 'error'); return; }
            toast('Sale order cancelled!', 'success');
            if (crmId) openCrmForm(crmId);
            else reloadCurrentView();
        } catch(e) { toast(e.message, 'error'); }
    }

    async function generateInvoice(soId) {
        if (!confirm('Generate invoice for this sale order?')) return;
        try {
            const res = await rpc(`/crm-portal/api/action/generate_invoice/${soId}`);
            if (res.error) { toast(res.error, 'error'); return; }
            toast('Invoice generated!', 'success');
        } catch(e) { toast(e.message, 'error'); }
    }

    async function logCall(id) {
        try {
            const res = await rpc(`/crm-portal/api/action/log_call/${id}`);
            if (res.error) { toast(res.error, 'error'); return; }
            if (res.phone) window.location.href = `tel:${res.phone}`;
            toast(`Call logged to ${res.phone || 'unknown'}`, 'info');
        } catch(e) { toast(e.message, 'error'); }
    }

    function openSmsModal(id) {
        document.getElementById('sms-record-id').value = id;
        document.getElementById('sms-message').value = '';
        document.getElementById('smsModal').classList.add('open');
    }

    async function sendSms() {
        const id      = document.getElementById('sms-record-id').value;
        const message = document.getElementById('sms-message').value.trim();
        if (!message) { toast('Enter a message', 'error'); return; }
        try {
            const res = await rpc(`/crm-portal/api/action/send_sms/${id}`, { message });
            if (res.error) { toast(res.error, 'error'); return; }
            toast(`SMS sent to ${res.phone}`, 'success');
            document.getElementById('smsModal').classList.remove('open');
        } catch(e) { toast(e.message, 'error'); }
    }

    // ── Create New Record ──────────────────────────────────────
    async function openCreateForm() {
        const stages = await rpc('/crm-portal/api/stages');
        const stageOpts = stages.map(s => `<option value="${s.id}">${escHtml(s.name)}</option>`).join('');
        const typeVal = state.activeMenu === 'leads' ? 'lead' : 'opportunity';

        document.getElementById('modal-title').textContent = 'New Record';
        document.getElementById('modal-form-body').innerHTML = `
            <div class="form-grid">
                <div class="form-group full">
                    <label>Name / Title *</label>
                    <input id="f-name" placeholder="Enter title"/>
                </div>
                <div class="form-group">
                    <label>Type</label>
                    <select id="f-type">
                        <option value="lead" ${typeVal==='lead'?'selected':''}>Lead</option>
                        <option value="opportunity" ${typeVal==='opportunity'?'selected':''}>Opportunity</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Stage</label>
                    <select id="f-stage">${stageOpts}</select>
                </div>
                <div class="form-group">
                    <label>Probability (%)</label>
                    <input id="f-prob" type="number" min="0" max="100" value="10"/>
                </div>
                <div class="form-group">
                    <label>Expected Revenue</label>
                    <input id="f-rev" type="number" min="0" value="0"/>
                </div>
                <div class="form-group">
                    <label>Expected Close Date</label>
                    <input id="f-deadline" type="date"/>
                </div>
                <div class="form-group">
                    <label>Customer Name</label>
                    <input id="f-partner-name" placeholder="Customer name"/>
                </div>
                <div class="form-group">
                    <label>Email</label>
                    <input id="f-email" type="email" placeholder="customer@email.com"/>
                </div>
                <div class="form-group">
                    <label>Phone</label>
                    <input id="f-phone" placeholder="+234..."/>
                </div>
                <div class="form-group">
                    <label>Address</label>
                    <input id="f-street" placeholder="Street address"/>
                </div>
                <div class="form-group full">
                    <label>Additional Notes</label>
                    <textarea id="f-desc" placeholder="Notes..."></textarea>
                </div>
            </div>`;

        const footer = document.getElementById('modal-footer');
        footer.innerHTML = '';
        addBtn(footer, 'Cancel', 'btn-secondary', closeModal);
        addBtn(footer, '<i class="fa fa-save"></i> Create', 'btn-primary', createRecord);

        document.getElementById('crmModal').classList.add('open');
    }

    async function createRecord() {
        const name = document.getElementById('f-name').value.trim();
        if (!name) { toast('Name is required', 'error'); return; }
        const vals = {
            name,
            type:             document.getElementById('f-type').value,
            stage_id:         parseInt(document.getElementById('f-stage').value) || false,
            probability:      parseFloat(document.getElementById('f-prob').value) || 0,
            expected_revenue: parseFloat(document.getElementById('f-rev').value) || 0,
            date_deadline:    document.getElementById('f-deadline').value || false,
            partner_name:     document.getElementById('f-partner-name').value.trim(),
            email_from:       document.getElementById('f-email').value.trim(),
            phone:            document.getElementById('f-phone').value.trim(),
            street:           document.getElementById('f-street').value.trim(),
            description:      document.getElementById('f-desc').value.trim(),
        };
        try {
            const res = await rpc('/crm-portal/api/create', { vals });
            if (res.error) { toast(res.error, 'error'); return; }
            toast('Record created!', 'success');
            closeModal();
            reloadCurrentView();
        } catch(e) { toast(e.message, 'error'); }
    }

    // ── Helpers ────────────────────────────────────────────────
    function reloadCurrentView() {
        switchMenu(state.activeMenu);
    }

    function formatMoney(v) {
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(v || 0);
    }

    function escHtml(str) {
        return String(str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    function typeBadge(type, isWon, active) {
        if (isWon) return '<span class="badge badge-won">Won</span>';
        if (!active) return '<span class="badge badge-lost">Lost</span>';
        if (type === 'lead') return '<span class="badge badge-lead">Lead</span>';
        return '<span class="badge badge-opp">Opportunity</span>';
    }

    function soBadge(state) {
        const map = { draft:'badge-draft', sale:'badge-sale', done:'badge-done', cancel:'badge-lost' };
        const labels = { draft:'Draft', sale:'Confirmed', done:'Done', cancel:'Cancelled' };
        return `<span class="badge ${map[state]||'badge-draft'}">${labels[state]||state}</span>`;
    }

    // ── Filter ─────────────────────────────────────────────────
    function setupFilters() {
        document.getElementById('search-input').addEventListener('input', filterTable);
        document.getElementById('stage-filter').addEventListener('change', filterTable);
        document.getElementById('type-filter').addEventListener('change', filterTable);
    }

    async function populateStageFilter() {
        try {
            const stages = await rpc('/crm-portal/api/stages');
            const sel = document.getElementById('stage-filter');
            stages.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.name; opt.textContent = s.name;
                sel.appendChild(opt);
            });
        } catch(e) {}
    }

    function filterTable() {
        const q     = document.getElementById('search-input').value.toLowerCase();
        const stage = document.getElementById('stage-filter').value.toLowerCase();
        const type  = document.getElementById('type-filter').value.toLowerCase();
        document.querySelectorAll('#list-tbody tr').forEach(row => {
            const text = row.textContent.toLowerCase();
            const matchQ     = !q     || text.includes(q);
            const matchStage = !stage || text.includes(stage);
            const matchType  = !type  || text.includes(type);
            row.style.display = (matchQ && matchStage && matchType) ? '' : 'none';
        });
    }

    // ── Public API ─────────────────────────────────────────────
    return {
        init,
        openCreateForm,
        sendSms,
        closeModal: () => {
            document.getElementById('crmModal').classList.remove('open');
            document.getElementById('smsModal').classList.remove('open');
        },
        setupFilters,
        populateStageFilter,
    };
})();

document.addEventListener('DOMContentLoaded', () => {
    CRM.init();
    CRM.setupFilters();
    CRM.populateStageFilter();
});
