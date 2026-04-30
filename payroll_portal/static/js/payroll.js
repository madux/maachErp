// ═══════════════════════════════════════════════
//  PAYROLL PORTAL JS  –  v4
//  Features: list view, modal detail, bulk print
// ═══════════════════════════════════════════════

// ── Global state ──
let currentPage    = 1;
let currentFilter  = 'all';
let searchTerm     = '';
let totalPages     = 1;
const recordsPerPage = 20;

// Holds currently open payslip data (for single-print from modal)
let activePayslip = null;

// Holds ALL loaded rows (for bulk print from selection)
let loadedMemos = [];

// ── Company info (fetched once, cached) ──
let companyInfo = null;

// ─────────────────────────────────────────────
$(document).ready(function () {

    fetchCompanyInfo();   // preload logo + name
    loadMemos();

    // Filter tabs
    $('.filter-tab').on('click', function () {
        $('.filter-tab').removeClass('active');
        $(this).addClass('active');
        currentFilter = $(this).data('filter');
        currentPage   = 1;
        loadMemos();
    });

    // Search – debounced
    let searchTimeout;
    $('#searchInput').on('input', function () {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(function () {
            searchTerm  = $('#searchInput').val();
            currentPage = 1;
            loadMemos();
        }, 500);
    });

    // Pagination
    $('#btnPrevPage').on('click', function () {
        if (currentPage > 1) { currentPage--; loadMemos(); }
    });
    $('#btnNextPage').on('click', function () {
        if (currentPage < totalPages) { currentPage++; loadMemos(); }
    });

    // Select-all checkbox
    $('#selectAll').on('change', function () {
        $('#memoTableBody input[type="checkbox"]').prop('checked', this.checked);
    });

    // New button
    $('.btn-new').on('click', function () {
        alert('This feature is not available for portal users');
    });

    // Close modal when clicking outside it
    $('#payslipModal').on('click', function (e) {
        if ($(e.target).is('#payslipModal')) closeModal();
    });

    // ESC closes modal
    $(document).on('keydown', function (e) {
        if (e.key === 'Escape') closeModal();
    });
});

// ─────────────────────────────────────────────
//  Company info
// ─────────────────────────────────────────────
function fetchCompanyInfo() {
    $.ajax({
        url:  '/payroll/api/company',
        type: 'GET',
        success: function (res) {
            let data = typeof res === 'string' ? JSON.parse(res) : res;
            if (data.status === 'success') companyInfo = data.data;
        },
        error: function () {
            // Fall back to defaults – non-fatal
            companyInfo = { name: 'Organisation', logo_url: null };
        }
    });
}

// ─────────────────────────────────────────────
//  Load & render list
// ─────────────────────────────────────────────
function loadMemos() {
    showLoading();

    $.ajax({
        url:  '/payroll/api/list',
        type: 'GET',
        data: {
            page:   currentPage,
            limit:  recordsPerPage,
            filter: currentFilter,
            search: searchTerm
        },
        success: function (response) {
            let data = typeof response === 'string' ? JSON.parse(response) : response;
            if (data.status === 'success') {
                loadedMemos = data.data;          // cache for print
                renderMemos(data.data);
                updatePagination(data.pagination);
            } else {
                showError('Failed to load Payslip');
            }
        },
        error: function (xhr) {
            console.error('Load error:', xhr);
            showError('Error loading Payslip. Please try again.');
        },
        complete: function () { hideLoading(); }
    });
}

function renderMemos(memos) {
    const tbody = $('#memoTableBody');
    tbody.empty();

    if (memos.length === 0) {
        tbody.html(`
            <tr>
                <td colspan="13" class="no-records">
                    <i class="fas fa-inbox"></i>
                    <p>No records found</p>
                </td>
            </tr>
        `);
        return;
    }

    memos.forEach(function (memo) {
        const badgeClass = getBadgeClass(memo.state);
        const row = `
            <tr class="memo-row" data-memo-id="${memo.id}" style="cursor: pointer;">
                <td class="checkbox-cell" onclick="event.stopPropagation()">
                    <input type="checkbox" data-memo-id="${memo.id}">
                </td>
                <td>${escapeHtml(memo.number)}</td>
                <td class="text-truncate-custom" title="${escapeHtml(memo.employee)}">
                    ${truncate(memo.employee, 20)}
                </td>
                <td>${escapeHtml(memo.structure)}</td>
                <td>${escapeHtml(memo.date_from)}</td>
                <td>${escapeHtml(memo.date_to)}</td>
                <td>₦${formatNumber(memo.normal_wage)}</td>
                <td>₦${formatNumber(memo.deductions)}</td>
                <td>₦${formatNumber(memo.basic_wage)}</td>
                <td>₦${formatNumber(memo.net_wage)}</td>
                <td>₦${formatNumber(memo.gross_wage)}</td>
                <td><span class="badge ${badgeClass}">${escapeHtml(memo.stage || memo.state)}</span></td>
                <td>
                    <button class="btn-icon" onclick="event.stopPropagation(); showActions(${memo.id})">
                        <i class="fas fa-ellipsis-v"></i>
                    </button>
                </td>
            </tr>
        `;
        tbody.append(row);
    });

    // Row click → open modal
    $('.memo-row').on('click', function () {
        const memoId = $(this).data('memo-id');
        openPayslipModal(memoId);
    });
}

function updatePagination(pagination) {
    totalPages = pagination.pages;
    const start = ((currentPage - 1) * recordsPerPage) + 1;
    const end   = Math.min(currentPage * recordsPerPage, pagination.total);
    $('#paginationInfo').text(`${start}-${end} / ${pagination.total}`);
    $('#btnPrevPage').prop('disabled', !pagination.has_prev);
    $('#btnNextPage').prop('disabled', !pagination.has_next);
}

// ─────────────────────────────────────────────
//  Modal – open / close
// ─────────────────────────────────────────────
function openPayslipModal(memoId) {
    // Show overlay immediately with spinner
    $('#modalTitle').text('Payslip Details');
    $('#payslipModalBody').html(`
        <div class="modal-loading">
            <i class="fas fa-spinner fa-spin"></i> Loading payslip…
        </div>
    `);
    $('#payslipModal').addClass('open');
    $('body').css('overflow', 'hidden');

    $.ajax({
        url:  `/payroll/api/detail/${memoId}`,
        type: 'GET',
        success: function (res) {
            let data = typeof res === 'string' ? JSON.parse(res) : res;
            if (data.status === 'success') {
                activePayslip = data.data;
                renderModalContent(data.data);
            } else {
                $('#payslipModalBody').html('<p style="color:red;padding:2rem">Failed to load payslip details.</p>');
            }
        },
        error: function () {
            $('#payslipModalBody').html('<p style="color:red;padding:2rem">Error fetching payslip. Please try again.</p>');
        }
    });
}

function closeModal() {
    $('#payslipModal').removeClass('open');
    $('body').css('overflow', '');
    activePayslip = null;
}

// ─────────────────────────────────────────────
//  Render modal payslip content
// ─────────────────────────────────────────────
function renderModalContent(p) {
    const co   = companyInfo || {};
    const name = co.name || 'Organisation';

    const logoHtml = co.logo_url
        ? `<img src="${co.logo_url}" class="ps-company-logo" alt="Logo">`
        : `<div class="ps-company-logo-placeholder">${name.charAt(0).toUpperCase()}</div>`;

    const stateColor = getStateColor(p.state);

    $('#modalTitle').text(`Payslip – ${escapeHtml(p.number)}`);

    $('#payslipModalBody').html(`
        <!-- Company header -->
        <div class="ps-company-header">
            ${logoHtml}
            <div class="ps-company-info">
                <h3>${escapeHtml(name)}</h3>
                <p>Employee Payslip</p>
            </div>
            <div class="ps-title-badge">
                <div class="ps-doc-title">Payslip</div>
                <div class="ps-number">${escapeHtml(p.number)}</div>
                <span class="ps-state-chip" style="background:${stateColor.bg};color:${stateColor.text};margin-top:5px;display:inline-block;">
                    ${escapeHtml(p.stage || p.state)}
                </span>
            </div>
        </div>

        <!-- Employee & Period -->
        <div class="ps-section-label">Employee Information</div>
        <div class="ps-info-grid">
            <div>
                <div class="ps-info-row">
                    <span class="ps-info-label">Employee</span>
                    <span class="ps-info-value">${escapeHtml(p.employee)}</span>
                </div>
                <div class="ps-info-row">
                    <span class="ps-info-label">Employee Code</span>
                    <span class="ps-info-value">${escapeHtml(p.employee_code || 'N/A')}</span>
                </div>
                <div class="ps-info-row">
                    <span class="ps-info-label">Department</span>
                    <span class="ps-info-value">${escapeHtml(p.department || 'N/A')}</span>
                </div>
                <div class="ps-info-row">
                    <span class="ps-info-label">Job Position</span>
                    <span class="ps-info-value">${escapeHtml(p.job_position || 'N/A')}</span>
                </div>
            </div>
            <div>
                <div class="ps-info-row">
                    <span class="ps-info-label">Pay Structure</span>
                    <span class="ps-info-value">${escapeHtml(p.structure)}</span>
                </div>
                <div class="ps-info-row">
                    <span class="ps-info-label">Period From</span>
                    <span class="ps-info-value">${escapeHtml(p.date_from)}</span>
                </div>
                <div class="ps-info-row">
                    <span class="ps-info-label">Period To</span>
                    <span class="ps-info-value">${escapeHtml(p.date_to)}</span>
                </div>
                <div class="ps-info-row">
                    <span class="ps-info-label">Company</span>
                    <span class="ps-info-value">${escapeHtml(p.company || name)}</span>
                </div>
            </div>
        </div>

        <!-- Financials -->
        <div class="ps-section-label">Earnings &amp; Deductions</div>
        <div class="ps-financials">
            <div class="ps-fin-card">
                <div class="fin-label">Normal Wage</div>
                <div class="fin-amount">₦${formatNumber(p.normal_wage)}</div>
            </div>
            <div class="ps-fin-card">
                <div class="fin-label">Basic Wage</div>
                <div class="fin-amount">₦${formatNumber(p.basic_wage)}</div>
            </div>
            <div class="ps-fin-card">
                <div class="fin-label">Gross Wage</div>
                <div class="fin-amount">₦${formatNumber(p.gross_wage)}</div>
            </div>
            <div class="ps-fin-card danger">
                <div class="fin-label">Total Deductions</div>
                <div class="fin-amount">₦${formatNumber(p.deductions)}</div>
            </div>
            <div class="ps-fin-card highlight" style="grid-column:span 2">
                <div class="fin-label">Net Wage (Take Home)</div>
                <div class="fin-amount" style="font-size:22px">₦${formatNumber(p.net_wage)}</div>
            </div>
        </div>

        ${renderPayslipLines(p.lines)}

        <div style="margin-top:1.2rem;font-size:11px;color:#bbb;text-align:center;border-top:1px dashed #eee;padding-top:.8rem;">
            Generated from Employee Payroll Portal &nbsp;|&nbsp; ${escapeHtml(name)}
        </div>
    `);
}

function renderPayslipLines(lines) {
    if (!lines || lines.length === 0) return '';

    let rows = lines.map(l => `
        <div class="ps-info-row">
            <span class="ps-info-label">${escapeHtml(l.name)} <small style="color:#ccc">(${escapeHtml(l.code)})</small></span>
            <span class="ps-info-value">₦${formatNumber(l.total)}</span>
        </div>
    `).join('');

    return `
        <div class="ps-section-label">Payslip Lines</div>
        <div>${rows}</div>
    `;
}

// ─────────────────────────────────────────────
//  Print – single (from modal)
// ─────────────────────────────────────────────
function printCurrentPayslip() {
    if (!activePayslip) return;
    buildPrintArea([activePayslip]);
    setTimeout(() => { window.print(); cleanPrintArea(); }, 300);
}

// ─────────────────────────────────────────────
//  Print – selected rows (bulk)
// ─────────────────────────────────────────────
function printSelected() {
    const checkedIds = [];
    $('#memoTableBody input[type="checkbox"]:checked').each(function () {
        checkedIds.push(parseInt($(this).data('memo-id')));
    });

    if (checkedIds.length === 0) {
        alert('Please select at least one payslip to print.');
        return;
    }

    // Gather matching memos from cache
    const toFetch = checkedIds.length;
    let fetched   = [];
    let done      = 0;

    checkedIds.forEach(function (id) {
        $.ajax({
            url:  `/payroll/api/detail/${id}`,
            type: 'GET',
            success: function (res) {
                let data = typeof res === 'string' ? JSON.parse(res) : res;
                if (data.status === 'success') fetched.push(data.data);
            },
            complete: function () {
                done++;
                if (done === toFetch) {
                    if (fetched.length === 0) {
                        alert('Could not load payslip data.');
                        return;
                    }
                    buildPrintArea(fetched);
                    setTimeout(() => { window.print(); cleanPrintArea(); }, 400);
                }
            }
        });
    });
}

// ─────────────────────────────────────────────
//  Build hidden print area
// ─────────────────────────────────────────────
function buildPrintArea(payslips) {
    const co   = companyInfo || {};
    const name = co.name || 'Organisation';

    const logoHtml = co.logo_url
        ? `<img src="${co.logo_url}" class="print-logo" alt="Logo">`
        : `<div class="print-logo-placeholder">${name.charAt(0).toUpperCase()}</div>`;

    const html = payslips.map(function (p) {
        const linesHtml = (p.lines && p.lines.length)
            ? p.lines.map(l => `
                <div class="print-row">
                    <span class="lbl">${escapeHtml(l.name)} (${escapeHtml(l.code)})</span>
                    <span class="val">₦${formatNumber(l.total)}</span>
                </div>`).join('')
            : '';

        return `
        <div class="print-payslip">
            <div class="print-header">
                ${logoHtml}
                <div class="print-company">
                    <h2>${escapeHtml(name)}</h2>
                    <p>Employee Payslip</p>
                </div>
                <div class="print-doc-title">
                    <div class="title">Payslip</div>
                    <div class="num">${escapeHtml(p.number)}</div>
                    <div class="num" style="margin-top:4px">${escapeHtml(p.stage || p.state)}</div>
                </div>
            </div>

            <div class="print-section-label">Employee Information</div>
            <div class="print-grid">
                <div>
                    <div class="print-row"><span class="lbl">Employee</span><span class="val">${escapeHtml(p.employee)}</span></div>
                    <div class="print-row"><span class="lbl">Employee Code</span><span class="val">${escapeHtml(p.employee_code || 'N/A')}</span></div>
                    <div class="print-row"><span class="lbl">Department</span><span class="val">${escapeHtml(p.department || 'N/A')}</span></div>
                    <div class="print-row"><span class="lbl">Job Position</span><span class="val">${escapeHtml(p.job_position || 'N/A')}</span></div>
                </div>
                <div>
                    <div class="print-row"><span class="lbl">Pay Structure</span><span class="val">${escapeHtml(p.structure)}</span></div>
                    <div class="print-row"><span class="lbl">Period From</span><span class="val">${escapeHtml(p.date_from)}</span></div>
                    <div class="print-row"><span class="lbl">Period To</span><span class="val">${escapeHtml(p.date_to)}</span></div>
                    <div class="print-row"><span class="lbl">Company</span><span class="val">${escapeHtml(p.company || name)}</span></div>
                </div>
            </div>

            ${linesHtml ? `<div class="print-section-label">Payslip Lines</div><div>${linesHtml}</div>` : ''}

            <div class="print-section-label">Summary</div>
            <div class="print-fin-grid">
                <div class="print-fin-box">
                    <div class="lbl">Normal Wage</div>
                    <div class="amt">₦${formatNumber(p.normal_wage)}</div>
                </div>
                <div class="print-fin-box">
                    <div class="lbl">Basic Wage</div>
                    <div class="amt">₦${formatNumber(p.basic_wage)}</div>
                </div>
                <div class="print-fin-box">
                    <div class="lbl">Gross Wage</div>
                    <div class="amt">₦${formatNumber(p.gross_wage)}</div>
                </div>
                <div class="print-fin-box" style="background:#fef3f2;border-color:#f5c2be">
                    <div class="lbl" style="color:#c0392b">Deductions</div>
                    <div class="amt" style="color:#c0392b">₦${formatNumber(p.deductions)}</div>
                </div>
                <div class="print-fin-box hi" style="grid-column:span 2">
                    <div class="lbl">Net Wage (Take Home)</div>
                    <div class="amt" style="font-size:20px">₦${formatNumber(p.net_wage)}</div>
                </div>
            </div>

            <div class="print-footer">
                Generated from Employee Payroll Portal &nbsp;|&nbsp; ${escapeHtml(name)}
            </div>
        </div>`;
    }).join('');

    $('#printArea').html(html).addClass('print-active').show();
}

function cleanPrintArea() {
    $('#printArea').html('').hide().removeClass('print-active');
}

// ─────────────────────────────────────────────
//  Actions (row kebab menu)
// ─────────────────────────────────────────────
function showActions(memoId) {
    // Simple: open detail modal
    openPayslipModal(memoId);
}

function refreshList() { loadMemos(); }

// ─────────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────────
function getBadgeClass(state) {
    const stateMap = {
        'submit':   'badge-initiator',
        'Sent':     'badge-warning',
        'Approve':  'badge-warning',
        'Approve2': 'badge-success',
        'Done':     'badge-success',
        'done':     'badge-success',
        'paid':     'badge-success',
        'verify':   'badge-warning',
        'Refuse':   'badge-danger'
    };
    return stateMap[state] || 'badge-secondary';
}

function getStateColor(state) {
    const map = {
        'done':     { bg: '#d1fae5', text: '#065f46' },
        'paid':     { bg: '#d1fae5', text: '#065f46' },
        'verify':   { bg: '#fef3c7', text: '#92400e' },
        'draft':    { bg: '#e0e7ff', text: '#3730a3' },
        'Refuse':   { bg: '#fee2e2', text: '#991b1b' },
    };
    return map[state] || { bg: '#f3f4f6', text: '#374151' };
}

function formatNumber(num) {
    return parseFloat(num || 0).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

function truncate(str, length) {
    if (!str) return '';
    return str.length > length ? str.substring(0, length) + '…' : str;
}

function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return String(text).replace(/[&<>"']/g, m => map[m]);
}

function showLoading()  { $('#loadingOverlay').css('display', 'flex'); }
function hideLoading()  { $('#loadingOverlay').css('display', 'none'); }
function showError(msg) { alert(msg); }


// // Global variables
// // Load initial data
// let currentPage = 1;
// let currentFilter = 'all';
// let searchTerm = '';
// let totalPages = 1;
// const recordsPerPage = 20;
// $(document).ready(function() {
        
//         loadMemos();

//         // Filter tabs
//         $('.filter-tab').on('click', function() {
//             $('.filter-tab').removeClass('active');
//             $(this).addClass('active');
//             currentFilter = $(this).data('filter');
//             currentPage = 1;
//             loadMemos();
//         });

//         // Search with debounce
//         let searchTimeout;
//         $('#searchInput').on('input', function() {
//             clearTimeout(searchTimeout);
//             searchTimeout = setTimeout(function() {
//                 searchTerm = $('#searchInput').val();
//                 currentPage = 1;
//                 loadMemos();
//             }, 500); // Wait 500ms after user stops typing
//         });

//         // Pagination
//         $('#btnPrevPage').on('click', function() {
//             if (currentPage > 1) {
//                 currentPage--;
//                 loadMemos();
//             }
//         });

//         $('#btnNextPage').on('click', function() {
//             if (currentPage < totalPages) {
//                 currentPage++;
//                 loadMemos();
//             }
//         });

//         // Select all checkboxes
//         $('#selectAll').on('change', function() {
//             $('#memoTableBody input[type="checkbox"]').prop('checked', this.checked);
//         });

//         // New button
//         $('.btn-new').on('click', function() {
//             // window.location.href = '/memo-form';
//             alert("This feature is not available for portal users")
//         });
//     });

//     // Load memos function
//     function loadMemos() {
//         showLoading();

//         $.ajax({
//             url: '/payroll/api/list',
//             type: 'GET',
//             data: {
//                 page: currentPage,
//                 limit: recordsPerPage,
//                 filter: currentFilter,
//                 search: searchTerm
//             },
//             success: function(response) {
//                 let data = typeof response === 'string' ? JSON.parse(response) : response;
                
//                 if (data.status === 'success') {
//                     renderMemos(data.data);
//                     updatePagination(data.pagination);
//                 } else {
//                     showError('Failed to load Payslip');
//                 }
//             },
//             error: function(xhr) {
//                 console.error('Load error:', xhr);
//                 showError('Error loading Payslip. Please try again.');
//             },
//             complete: function() {
//                 hideLoading();
//             }
//         });
//     }

//     // Render memos in table
//     function renderMemos(memos) {
//         const tbody = $('#memoTableBody');
//         tbody.empty();

//         if (memos.length === 0) {
//             tbody.html(`
//                 <tr>
//                     <td colspan="10" class="no-records">
//                         <i class="fas fa-inbox"></i>
//                         <p>No records found</p>
//                     </td>
//                 </tr>
//             `);
//             return;
//         }

//         memos.forEach(function(memo) {
//             const badgeClass = getBadgeClass(memo.state);
//             const row = `
//                 <tr class="memo-row" data-memo-id="${memo.id}" style="cursor: pointer;">
//                     <td class="checkbox-cell" onclick="event.stopPropagation()">
//                         <input type="checkbox">
//                     </td>
//                     <td>${escapeHtml(memo.number)}</td>
//                     <td class="text-truncate-custom" title="${escapeHtml(memo.employee)}">
//                         ${truncate(memo.employee, 20)}
//                     </td>
//                     <td>${memo.structure}</td>
                    
//                     <td>${escapeHtml(memo.date_from)}</td>
//                     <td>${escapeHtml(memo.date_to)}</td>
//                     <td>₦${formatNumber(memo.normal_wage)}</td>
//                     <td>₦${formatNumber(memo.deductions)}</td>
//                     <td>₦${formatNumber(memo.basic_wage)}</td>
//                     <td>₦${formatNumber(memo.net_wage)}</td>
//                     <td>₦${formatNumber(memo.gross_wage)}</td>
//                     <td><span class="badge ${badgeClass}">${escapeHtml(memo.stage)}</span></td>

//                     <td>
//                         <button class="btn-icon" onclick="event.stopPropagation(); showActions(${memo.id})">
//                             <i class="fas fa-ellipsis-v"></i>
//                         </button>
//                     </td>
//                 </tr>
//             `;
//             tbody.append(row);
//         });

//         // Add click handler to rows
//         $('.memo-row').on('click', function() {
//             const memoId = $(this).data('memo-id');
//             // openMemo(memoId);
//             alert('You cannot view as a portal user')

//         });
//     }

//     // Update pagination info
//     function updatePagination(pagination) {
//         totalPages = pagination.pages;
        
//         const start = ((currentPage - 1) * recordsPerPage) + 1;
//         const end = Math.min(currentPage * recordsPerPage, pagination.total);
        
//         $('#paginationInfo').text(`${start}-${end} / ${pagination.total}`);
        
//         $('#btnPrevPage').prop('disabled', !pagination.has_prev);
//         $('#btnNextPage').prop('disabled', !pagination.has_next);
//     }

//     // Open memo in form view
//     function openMemo(memoId) {
//         window.location.href = `/memo-form/${memoId}`;
//         // window.location.href = `/memo/form/get/${memoId}`;
//     }

//     // Show actions menu
//     function showActions(memoId) {
//         // You can add a context menu or modal here
//         alert(`Actions for payslip ${memoId}:\n- Edit\n- Delete\n- View Details`);
//     }

//     // Refresh list
//     function refreshList() {
//         loadMemos();
//     }

//     // Helper functions
//     function getBadgeClass(state) {
//         const stateMap = {
//             'submit': 'badge-initiator',
//             'Sent': 'badge-warning',
//             'Approve': 'badge-warning',
//             'Approve2': 'badge-success',
//             'Done': 'badge-success',
//             'Refuse': 'badge-danger'
//         };
//         return stateMap[state] || 'badge-secondary';
//     }

//     function formatNumber(num) {
//         return parseFloat(num || 0).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
//     }

//     function truncate(str, length) {
//         if (!str) return '';
//         return str.length > length ? str.substring(0, length) + '...' : str;
//     }

//     function escapeHtml(text) {
//         if (!text) return '';
//         const map = {
//             '&': '&amp;',
//             '<': '&lt;',
//             '>': '&gt;',
//             '"': '&quot;',
//             "'": '&#039;'
//         };
//         return text.replace(/[&<>"']/g, m => map[m]);
//     }

//     function showLoading() {
//         $('#loadingOverlay').css('display', 'flex');
//     }

//     function hideLoading() {
//         $('#loadingOverlay').css('display', 'none');
//     }

//     function showError(message) {
//         alert(message); // Replace with a nicer notification system
//     }