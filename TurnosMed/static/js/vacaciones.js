let currentYear = 2027;

const OCCUPIED = {
    2026: {
    0: [1, 2, 3, 15, 16, 17, 18], // Enero 2026
    6: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15], // Julio 2026 (15 días)
    11: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30] // Diciembre (Mes completo)
    },

    2027: {
        0: [],
    }
};

// Objeto para guardar el rango seleccionado
let rangeSelection = {
    start: null, // { month, day }
    end: null    // { month, day }
};

const MONTHS = [
    'Enero','Febrero','Marzo','Abril','Mayo','Junio',
    'Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'
];
const DAYS_HEADER = ['Su','Mo','Tu','We','Th','Fr','Sa'];

/* ─── Render calendarios ───────────────────── */
function buildCalendars(year) {
    const grid = document.getElementById('calendars-grid');
    grid.innerHTML = '';
    for (let m = 0; m < 12; m++) {
        grid.appendChild(buildMonth(year, m));
    }
}

function buildMonth(year, month) {
    const occ = (OCCUPIED[year] || {})[month] || [];
    const card = document.createElement('div');
    card.className = 'cal-card';

    const title = document.createElement('div');
    title.className = 'cal-title';
    title.textContent = MONTHS[month];
    card.appendChild(title);

    const hdr = document.createElement('div');
    hdr.className = 'cal-grid';
    DAYS_HEADER.forEach(d => {
        const cell = document.createElement('div');
        cell.className = 'cal-day-hdr';
        cell.textContent = d;
        hdr.appendChild(cell);
    });

    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    for (let i = 0; i < firstDay; i++) {
        const blank = document.createElement('div');
        blank.className = 'cal-cell other-month';
        hdr.appendChild(blank);
    }

    for (let d = 1; d <= daysInMonth; d++) {
        const cell = document.createElement('div');
        cell.className = 'cal-cell';
        cell.textContent = d;
        cell.dataset.month = month;
        cell.dataset.day = d;

        if (occ.includes(d)) cell.classList.add('ocupado');

        // Verificar si este día cae dentro del rango seleccionado para pintarlo
        if (isDayInRange(month, d)) {
            cell.classList.add('seleccionado');
        }

        cell.addEventListener('click', () => handleDateClick(month, d));
        hdr.appendChild(cell);
    }

    card.appendChild(hdr);
    return card;
}

/* ─── Lógica de Selección de Rango ─────────── */
function handleDateClick(month, day) {
    // Si el año es 2026, bloqueamos la edición
    if (currentYear === 2026) {
        alert("La programación para el año 2026 ya está cerrada. El cambio debe ser realizado mediante Solicitudes.");
        return;
    }

    const occ = (OCCUPIED[currentYear] || {})[month] || [];
    if (occ.includes(day)) return; // No permitir seleccionar días ocupados

    const clickedDate = new Date(currentYear, month, day);

    if (!rangeSelection.start || (rangeSelection.start && rangeSelection.end)) {
        // Primer clic o reinicio de selección
        rangeSelection.start = { month, day, date: clickedDate };
        rangeSelection.end = null;
    } else {
        // Segundo clic: definir el fin del rango
        if (clickedDate < rangeSelection.start.date) {
            // Si el segundo clic es antes que el primero, invertimos
            rangeSelection.end = rangeSelection.start;
            rangeSelection.start = { month, day, date: clickedDate };
        } else {
            rangeSelection.end = { month, day, date: clickedDate };
        }
    }

    updateUI();
}

function isDayInRange(m, d) {
    if (!rangeSelection.start) return false;
    const current = new Date(currentYear, m, d);
    if (rangeSelection.end) {
        return current >= rangeSelection.start.date && current <= rangeSelection.end.date;
    }
    return current.getTime() === rangeSelection.start.date.getTime();
}

function updateUI() {
    buildCalendars(currentYear);

    if (rangeSelection.start) {
        document.getElementById('date-from').value = `${rangeSelection.start.day} ${MONTHS[rangeSelection.start.month]}`;

        if (rangeSelection.end) {
            document.getElementById('date-to').value = `${rangeSelection.end.day} ${MONTHS[rangeSelection.end.month]}`;

            // Calcular diferencia de días
            const diffTime = Math.abs(rangeSelection.end.date - rangeSelection.start.date);
            const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)) + 1;
            document.getElementById('days-total').value = diffDays;
        } else {
            document.getElementById('date-to').value = "---";
            document.getElementById('days-total').value = 1;
        }
    }
}

/* ─── Navegación año ──────────────────────── */
document.getElementById('prev-year').addEventListener('click', () => {
    currentYear--;
    resetAndRefresh();
});
document.getElementById('next-year').addEventListener('click', () => {
    currentYear++;
    resetAndRefresh();
});

function resetAndRefresh() {
    rangeSelection = { start: null, end: null };
    document.getElementById('year-display').textContent = currentYear;
    document.getElementById('year-label').textContent = currentYear;
    document.getElementById('date-from').value = "";
    document.getElementById('date-to').value = "";
    document.getElementById('days-total').value = 0;
    buildCalendars(currentYear);
}

/* ─── Init ────────────────────────────────── */
// Iniciamos con los valores limpios para 2027
updateUI();
document.getElementById('year-display').textContent = currentYear;
document.getElementById('year-label').textContent = currentYear;