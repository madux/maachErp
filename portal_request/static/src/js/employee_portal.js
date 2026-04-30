// ─────────────────────────────────────────────
//  Dashboard Bootstrap
// ─────────────────────────────────────────────
$(document).ready(function () {
    Promise.all([
        fetchEmployee(),
        fetchStats()
    ]).finally(function () {
        $('#pageLoader').fadeOut(300);
    });
});

// ── Fetch employee profile ──
function fetchEmployee() {
    return $.ajax({
        url: '/employee/api/dashboard/profile',
        type: 'GET'
    }).then(function (res) {
        let data = typeof res === 'string' ? JSON.parse(res) : res;
        if (data.status === 'success') renderProfile(data.data);
    }).catch(function () {
        $('#empName').text('Could not load profile');
    });
}

// ── Fetch statistics ──
function fetchStats() {
    return $.ajax({
        url: '/employee/api/dashboard/stats',
        type: 'GET'
    }).then(function (res) {
        let data = typeof res === 'string' ? JSON.parse(res) : res;
        if (data.status === 'success') renderStats(data.data);
    }).catch(function (xhr) {
        console.error('Stats error', xhr);
    });
}

// ── Render profile ──
function renderProfile(e) {
    // Avatar
    if (e.image_url) {
        document.getElementById('avatarImg').src = e.image_url;
    } else {
        const initials = (e.name || '?').split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase();
        document.getElementById('avatarPlaceholder').textContent = initials;
    }

    const setText = (id, val) => { document.getElementById(id).textContent = val || '—'; };

    setText('empName', e.name);
    setText('empDept', e.department);
    setText('empManager', e.manager);
    setText('empJob', e.job_position);
    setText('empStaffId', e.employee_number);

    // Detail table
    setText('infoName', e.name);
    setText('infoStaffId', e.employee_number);
    setText('infoDept', e.department);
    setText('infoJob', e.job_position);
    setText('infoManager', e.manager);
    setText('infoEmail', e.work_email);
    setText('infoPhone', e.work_phone);
    setText('infoCompany', e.company);
}

// ── Render stats ──
function renderStats(s) {
    animateNumber('numRequests', s.requests || 0);
    animateNumber('numLeaves', s.leaves || 0);
    animateNumber('numAppraisals', s.appraisals || 0);
    animateNumber('numPayslips', s.payslips || 0);
    animateNumber('numProjects', s.projects || 0);
    animateNumber('numTasks', s.tasks || 0);

    // Remove skeleton classes
    ['numRequests', 'numLeaves', 'numAppraisals', 'numPayslips', 'numProjects', 'numTasks'].forEach(function (id) {
        document.getElementById(id).classList.remove('skeleton', 'sk-num');
    });

    // Appraisal donut
    if (s.appraisal_scores && s.appraisal_scores.length > 0) {
        renderDonut(s.appraisal_scores, s.appraisal_avg);
    } else {
        renderEmptyDonut();
    }
}

// ── Count-up animation ──
function animateNumber(id, target) {
    const el = document.getElementById(id);
    if (target === 0) { el.textContent = '0'; return; }
    let current = 0;
    const step = Math.max(1, Math.floor(target / 30));
    const timer = setInterval(function () {
        current = Math.min(current + step, target);
        el.textContent = current;
        if (current >= target) clearInterval(timer);
    }, 30);
}

// ── Donut chart ──
const SCORE_BANDS = [
    { label: 'Excellent (≥80)', min: 80, max: Infinity, color: '#0d9e75' },
    { label: 'Good (60–79)', min: 60, max: 79.99, color: '#1a73e8' },
    { label: 'Fair (40–59)', min: 40, max: 59.99, color: '#d97706' },
    { label: 'Needs Work (<40)', min: -Infinity, max: 39.99, color: '#e11d48' },
];

function renderDonut(scores, avg) {
    const bands = SCORE_BANDS.map(b => ({
        ...b,
        count: scores.filter(v => v >= b.min && v <= b.max).length
    })).filter(b => b.count > 0);

    const ctx = document.getElementById('appraisalChart').getContext('2d');
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: bands.map(b => b.label),
            datasets: [{
                data: bands.map(b => b.count),
                backgroundColor: bands.map(b => b.color),
                borderWidth: 3,
                borderColor: '#ffffff',
                hoverOffset: 6
            }]
        },
        options: {
            cutout: '70%',
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => ` ${ctx.parsed} appraisal${ctx.parsed !== 1 ? 's' : ''}`
                    }
                }
            },
            animation: { animateScale: true, duration: 700 }
        }
    });

    // Centre label
    document.getElementById('chartAvg').textContent = avg != null ? parseFloat(avg).toFixed(1) : '—';

    // Legend
    const legend = document.getElementById('chartLegend');
    legend.innerHTML = bands.map(b => `
<div class="legend-item">
    <div class="legend-dot" style="background:${b.color}"></div>
    <span class="lbl">${b.label}</span>
    <span class="val">${b.count}</span>
</div>
`).join('');
}

function renderEmptyDonut() {
    const ctx = document.getElementById('appraisalChart').getContext('2d');
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['No appraisals'],
            datasets: [{ data: [1], backgroundColor: ['#e2e8f0'], borderWidth: 0 }]
        },
        options: {
            cutout: '70%',
            plugins: { legend: { display: false }, tooltip: { enabled: false } }
        }
    });
    document.getElementById('chartAvg').textContent = 'N/A';
    document.getElementById('chartLegend').innerHTML =
        '<div style="font-size:12px;color:#94a3b8;text-align:center">No appraisal records found</div>';
}