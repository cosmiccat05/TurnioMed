const MONTHS = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
];
const DAYS_HEADER = ['Do', 'Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sa'];

const page = document.querySelector('.vac-page');
const currentYear = Number(page?.dataset.anio || new Date().getFullYear());
const personalData = JSON.parse(document.getElementById('personal-data')?.textContent || '[]');
const vacacionesData = JSON.parse(document.getElementById('vacaciones-data')?.textContent || '[]');
let selectedWorker = null;

function parseISODate(value) {
    const [year, month, day] = value.split('-').map(Number);
    return new Date(year, month - 1, day);
}

function formatShortDate(date) {
    return `${date.getDate()} ${MONTHS[date.getMonth()]}`;
}

function getPeriodosTrabajador(trabajadorId) {
    return vacacionesData.filter(item => Number(item.trabajador_id) === Number(trabajadorId));
}

function getPeriodoPrincipal(trabajadorId) {
    const periodos = getPeriodosTrabajador(trabajadorId);
    return periodos.find(item => item.tipo === 'programacion') || periodos[0];
}

function getOccupiedDays() {
    const occupied = {};
    vacacionesData.forEach(item => {
        const start = parseISODate(item.fecha_inicio);
        const end = parseISODate(item.fecha_fin);
        for (let date = new Date(start); date <= end; date.setDate(date.getDate() + 1)) {
            if (date.getFullYear() !== currentYear) continue;
            const month = date.getMonth();
            if (!occupied[month]) occupied[month] = [];
            occupied[month].push(date.getDate());
        }
    });
    return occupied;
}

function isSelectedWorkerDay(month, day) {
    if (!selectedWorker) return false;
    const current = new Date(currentYear, month, day);
    return getPeriodosTrabajador(selectedWorker.id).some(item => (
        current >= parseISODate(item.fecha_inicio) && current <= parseISODate(item.fecha_fin)
    ));
}

function buildMonth(month, occupied) {
    const card = document.createElement('div');
    card.className = 'cal-card';

    const title = document.createElement('div');
    title.className = 'cal-title';
    title.textContent = MONTHS[month];
    card.appendChild(title);

    const grid = document.createElement('div');
    grid.className = 'cal-grid';
    DAYS_HEADER.forEach(day => {
        const cell = document.createElement('div');
        cell.className = 'cal-day-hdr';
        cell.textContent = day;
        grid.appendChild(cell);
    });

    const firstDay = new Date(currentYear, month, 1).getDay();
    const daysInMonth = new Date(currentYear, month + 1, 0).getDate();
    for (let index = 0; index < firstDay; index++) {
        const blank = document.createElement('div');
        blank.className = 'cal-cell other-month';
        grid.appendChild(blank);
    }

    for (let day = 1; day <= daysInMonth; day++) {
        const cell = document.createElement('div');
        cell.className = 'cal-cell';
        cell.textContent = day;
        if ((occupied[month] || []).includes(day)) cell.classList.add('ocupado');
        if (isSelectedWorkerDay(month, day)) cell.classList.add('seleccionado');
        grid.appendChild(cell);
    }

    card.appendChild(grid);
    return card;
}

function buildCalendars() {
    const grid = document.getElementById('calendars-grid');
    if (!grid) return;
    const occupied = getOccupiedDays();
    grid.innerHTML = '';
    for (let month = 0; month < 12; month++) {
        grid.appendChild(buildMonth(month, occupied));
    }
}

function updateObsCounter() {
    const obsInput = document.getElementById('obs-input');
    const obsCount = document.getElementById('obs-count');
    if (obsInput && obsCount) obsCount.textContent = obsInput.value.length;
}

function selectWorker(workerId) {
    selectedWorker = personalData.find(item => Number(item.id) === Number(workerId));
    if (!selectedWorker) return;

    const periodo = getPeriodoPrincipal(workerId);
    const badge = document.getElementById('estado-badge');
    const observations = document.getElementById('obs-input');

    document.getElementById('staff-avatar').textContent = selectedWorker.iniciales;
    document.getElementById('staff-name').textContent = selectedWorker.nombre;
    document.getElementById('staff-role').textContent = selectedWorker.cargo;

    if (periodo) {
        document.getElementById('date-from').value = formatShortDate(parseISODate(periodo.fecha_inicio));
        document.getElementById('date-to').value = formatShortDate(parseISODate(periodo.fecha_fin));
        document.getElementById('days-total').value = periodo.dias_totales;
        badge.textContent = periodo.tipo === 'adelanto' ? 'Adelanto procesado' : 'Programado';
        badge.className = 'estado-badge programado';
        observations.value = periodo.observaciones || '';
    } else {
        document.getElementById('date-from').value = '';
        document.getElementById('date-to').value = '';
        document.getElementById('days-total').value = 0;
        badge.textContent = 'Sin programar';
        badge.className = 'estado-badge sin-programar';
        observations.value = '';
    }
    updateObsCounter();
    buildCalendars();
}

function renderStaffList() {
    const list = document.getElementById('staff-list');
    if (!list) return;
    list.innerHTML = '';
    personalData.forEach(persona => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'staff-option';
        button.dataset.id = persona.id;
        button.innerHTML = `
            <span class="staff-option-avatar">${persona.iniciales}</span>
            <span class="staff-option-info">
                <strong>${persona.nombre}</strong>
                <small>${persona.cargo}</small>
            </span>
        `;
        button.addEventListener('click', () => {
            document.querySelectorAll('.staff-option').forEach(item => item.classList.remove('active'));
            button.classList.add('active');
            selectWorker(persona.id);
        });
        list.appendChild(button);
    });
}

function navigateYear(year) {
    const params = new URLSearchParams(window.location.search);
    params.set('anio', year);
    window.location.search = params.toString();
}

function initVacaciones() {
    document.getElementById('prev-year')?.addEventListener('click', () => navigateYear(currentYear - 1));
    document.getElementById('next-year')?.addEventListener('click', () => navigateYear(currentYear + 1));
    document.getElementById('year-display').textContent = currentYear;
    document.getElementById('year-label').textContent = currentYear;
    document.getElementById('staff-search')?.addEventListener('input', function () {
        const query = this.value.toLowerCase();
        document.querySelectorAll('.staff-option').forEach(item => {
            item.style.display = item.textContent.toLowerCase().includes(query) ? '' : 'none';
        });
    });
    renderStaffList();
    buildCalendars();
}

document.addEventListener('DOMContentLoaded', initVacaciones);
