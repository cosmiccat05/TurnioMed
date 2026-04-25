const VALID_CODES = ['D', 'T', 'M', 'N'];
const CODE_CLASS  = { D:'d', T:'t', M:'m', N:'n' };
const CODE_HOURS  = { D:12, T:12, M:6, N:12 };
const META_TARGET = 150;

function renderCell(td, code) {
    const cls = code ? CODE_CLASS[code] : '';
    td.setAttribute('data-code', code);
    td.innerHTML = `<span class="shift-cell ${cls}${!code?' empty':''}">${code}</span>`;
}

function calcStats(row) {
    const counts = { D:0, T:0, M:0, N:0 };
    let hours = 0;
    row.querySelectorAll('.editable-cell').forEach(td => {
        const c = td.getAttribute('data-code');
        if (c && counts[c] !== undefined) { counts[c]++; hours += CODE_HOURS[c]; }
    });
    return { counts, hours };
}

function updatePanel(row) {
    const { counts, hours } = calcStats(row);
    document.getElementById('count-d').textContent  = counts.D;
    document.getElementById('count-t').textContent  = counts.T;
    document.getElementById('count-m').textContent  = counts.M;
    document.getElementById('count-n').textContent  = counts.N;

    const pct = Math.min((hours / META_TARGET) * 100, 100).toFixed(1);
    document.getElementById('hours-total').textContent = hours + ' h';
    document.getElementById('hours-meta').textContent  = `${hours} / ${META_TARGET} h requeridas`;
    document.getElementById('hours-bar-fill').style.width = pct + '%';

    const diff = META_TARGET - hours;
    const statusEl = document.getElementById('hours-status');
    if (diff > 0) {
        statusEl.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> Faltan ${diff} h para completar el mes`;
        statusEl.className = 'hours-status warn';
    } else {
        statusEl.innerHTML = `<i class="fa-solid fa-circle-check"></i> Meta mensual cumplida`;
        statusEl.className = 'hours-status ok';
    }
}

let activeRow = document.querySelector('tr[data-row="0"]');
if (activeRow) updatePanel(activeRow);

document.querySelectorAll('.editable-cell').forEach(td => {
    td.addEventListener('click', () => {
        document.querySelectorAll('.editable-cell.selected').forEach(el => el.classList.remove('selected'));
        td.classList.add('selected');
        activeRow = td.closest('tr');
        updatePanel(activeRow);
        td.setAttribute('contenteditable', 'true');
        td.focus();
        const range = document.createRange();
        range.selectNodeContents(td);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
    });

    td.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === 'Tab') { e.preventDefault(); td.blur(); }
    });

    td.addEventListener('blur', () => {
        td.setAttribute('contenteditable', 'false');
        const typed = (td.textContent || '').trim().toUpperCase();
        if (VALID_CODES.includes(typed)) {
            renderCell(td, typed);
        } else if (typed === '') {
            renderCell(td, '');
        } else {
            renderCell(td, td.getAttribute('data-code'));
            td.classList.add('cell-error');
            setTimeout(() => td.classList.remove('cell-error'), 1200);
        }
        if (activeRow) updatePanel(activeRow);
    });
});