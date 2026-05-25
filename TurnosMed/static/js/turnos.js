let typingBuffer = '';
let typingTimeout = null;
let pendingCells = [];
const CODE_WAIT_MS = 5000;

const VALID_CODES = ['D', 'D4', 'T', 'M', 'N', 'N4'];

// Esto se usa para pintar la celda con color diferente.
const CODE_CLASS = {
    D: 'd',
    D4: 'd',
    T: 't',
    M: 'm',
    N: 'n',
    N4: 'n'
};

// Cantidad de horas que suma cada tipo de turno.
const CODE_HOURS = {
    D: 12,
    D4: 12.5,
    T: 6,
    M: 6,
    N: 12,
    N4: 12.5
};

const CODE_LABELS = {
    D: 'Día',
    D4: 'Día completo',
    T: 'Tarde',
    M: 'Medio día',
    N: 'Noche',
    N4: 'Noche completa'
};

// Celda principal seleccionada.
// Esta se usa para moverse con flechas, Enter y Tab.
let selectedCell = null;

// Lista de celdas seleccionadas con Ctrl + click.
// Si solo hay una celda seleccionada, también estará aquí.
let selectedCells = [];

// Fila activa para actualizar el panel derecho.
let activeRow = document.querySelector('tr[data-row="0"]');


// Renderiza visualmente una celda.
// No usa contenteditable.
// Solo actualiza data-code y el span interno.
function renderCell(td, code) {
    code = (code || '').trim().toUpperCase();

    const cls = code ? CODE_CLASS[code] : '';

    td.setAttribute('data-code', code);
    td.innerHTML = `<span class="shift-cell ${cls}${!code ? ' empty' : ''}">${code}</span>`;
}

function renderPreview(td, code) {
    const cls = CODE_CLASS[code] || '';
    td.innerHTML = `<span class="shift-cell ${cls}">${code}</span>`;
}

function clearTypingPreview() {
    clearTimeout(typingTimeout);
    pendingCells.forEach(cell => {
        renderCell(cell, cell.getAttribute('data-code') || '');
    });
    typingBuffer = '';
    pendingCells = [];
    typingTimeout = null;
}

// Marca visualmente una celda como seleccionada.
// Si additive = false, limpia la selección anterior.
// Si additive = true, permite seleccionar varias con Ctrl + click.
function selectCell(td, additive = false) {
    if (!td) return;
    if (td.dataset.bloqueo) {
        showToast('info', 'Dia libre', `No se puede programar: ${td.dataset.bloqueo}.`);
        return;
    }
    if (typingBuffer) {
        clearTypingPreview();
    }

    // Selección normal: limpia y selecciona solo una celda.
    if (!additive) {
        document.querySelectorAll('.editable-cell.selected').forEach(cell => {
            cell.classList.remove('selected');
        });

        selectedCells = [td];
    }

    // Selección múltiple: agrega o quita la celda del grupo.
    else {
        if (selectedCells.includes(td)) {
            td.classList.remove('selected');
            selectedCells = selectedCells.filter(cell => cell !== td);
        } else {
            selectedCells.push(td);
        }
    }

    // Aplica clase visual a todas las seleccionadas.
    selectedCells.forEach(cell => {
        cell.classList.add('selected');
    });

    // La última celda clickeada queda como celda principal.
    selectedCell = td;
    activeRow = td.closest('tr');

    updateDetalle(activeRow, td);
    updatePanel(activeRow, td);
}


// Escribe o borra el código en la celda seleccionada.
function setCellCode(td, code) {
    if (!td) return;
    if (td.dataset.bloqueo && code) return;

    code = (code || '').trim().toUpperCase();

    if (code !== '' && !VALID_CODES.includes(code)) {
        td.classList.add('cell-error');

        setTimeout(() => {
            td.classList.remove('cell-error');
        }, 1000);
        return;
    }

    renderCell(td, code);
}

function cellsForEditing() {
    return selectedCells.length > 0 ? [...selectedCells] : [selectedCell];
}

function applyCodeToSelection(code, cells = cellsForEditing()) {
    cells.forEach(cell => setCellCode(cell, code));
    typingBuffer = '';
    pendingCells = [];
    typingTimeout = null;
    updatePanel(activeRow, selectedCell);
}

function beginAmbiguousCode(code) {
    clearTypingPreview();
    typingBuffer = code;
    pendingCells = cellsForEditing();
    pendingCells.forEach(cell => renderPreview(cell, code));
    updateDetalle(activeRow, selectedCell, code);
    typingTimeout = setTimeout(() => {
        const codeToApply = typingBuffer;
        const cellsToApply = [...pendingCells];
        applyCodeToSelection(codeToApply, cellsToApply);
    }, CODE_WAIT_MS);
}

// Calcula cantidad de turnos y horas de una fila.
function calcStats(row) {
    const counts = {
        D: 0,
        D4: 0,
        T: 0,
        M: 0,
        N: 0,
        N4: 0
    };

    let hours = 0;

    if (!row) {
        return { counts, hours };
    }

    row.querySelectorAll('.editable-cell').forEach(td => {
        const code = td.getAttribute('data-code');

        if (code && counts[code] !== undefined) {
            counts[code]++;
            hours += CODE_HOURS[code];
        }
    });

    return { counts, hours };
}

function recopilarTurnos() {
    const turnos = [];

    document.querySelectorAll('.editable-cell').forEach(td => {
        turnos.push({
            trabajador_id: td.dataset.trabajadorId,
            fecha: td.dataset.fecha,
            codigo: td.getAttribute('data-code') || ''
        });
    });

    return turnos;
}

function formatDate(dateText) {
    if (!dateText) return 'Fecha no seleccionada';

    const [year, month, day] = dateText.split('-');
    return `${day}/${month}/${year}`;
}

function updateDetalle(row, cell = selectedCell, previewCode = null) {
    const avatar = document.querySelector('.detail-doctor .person-avatar');
    const name = document.querySelector('.detail-doctor .person-name');
    const role = document.querySelector('.detail-doctor .person-role');
    const shiftCell = document.querySelector('.detail-shift .shift-cell');
    const shiftTitle = document.querySelector('.detail-shift-info strong');
    const shiftSubtitle = document.querySelector('.detail-shift-info span');
    const dateEl = document.querySelector('.detail-date');

    if (!row || !cell) {
        avatar.textContent = '--';
        name.textContent = 'Seleccione una celda';
        role.textContent = 'Personal asistencial';
        shiftCell.className = 'shift-cell empty';
        shiftCell.textContent = '';
        shiftTitle.textContent = 'Sin turno';
        shiftSubtitle.textContent = 'Seleccione una celda';
        dateEl.innerHTML = '<i class="fa-regular fa-calendar"></i> Fecha no seleccionada';
        return;
    }

    const code = previewCode || cell.getAttribute('data-code') || '';
    const fecha = cell.getAttribute('data-fecha');
    const cls = code ? CODE_CLASS[code] : '';

    avatar.textContent = row.dataset.iniciales || '--';
    name.textContent = row.dataset.nombre || 'Sin nombre';

    const tipo = row.dataset.tipo || 'Personal asistencial';
    const condicion = row.dataset.condicion || '';
    role.textContent = condicion ? `${tipo} - ${condicion}` : tipo;

    shiftCell.className = `shift-cell ${cls}${!code ? ' empty' : ''}`;
    shiftCell.textContent = code;

    shiftTitle.textContent = code ? CODE_LABELS[code] : 'Sin turno';
    shiftSubtitle.textContent = code ? `${CODE_HOURS[code]} horas programadas` : 'Celda libre';

    dateEl.innerHTML = `<i class="fa-regular fa-calendar"></i> ${formatDate(fecha)}`;
}

// Actualiza el panel derecho con el resumen de la fila activa.
function updatePanel(row, cell = selectedCell) {
    const { counts, hours } = calcStats(row);

    const countD = document.getElementById('count-d');
    const countT = document.getElementById('count-t');
    const countM = document.getElementById('count-m');
    const countN = document.getElementById('count-n');
    const hoursTotal = document.getElementById('hours-total');
    const hoursMeta = document.getElementById('hours-meta');

    if (countD) countD.textContent = counts.D + counts.D4;
    if (countT) countT.textContent = counts.T;
    if (countM) countM.textContent = counts.M;
    if (countN) countN.textContent = counts.N + counts.N4;

    if (hoursTotal) hoursTotal.textContent = hours + ' h';
    if (hoursMeta) hoursMeta.textContent = 'Segun programacion vigente';

    updateDetalle(row, cell);
}


// Devuelve todas las celdas editables como una lista ordenada.
function getEditableCells() {
    return Array.from(document.querySelectorAll('.editable-cell'));
}

// Mueve la selección hacia otra celda.
// direction puede ser: left, right, up, down.
function moveSelection(direction) {
    if (!selectedCell) return;

    const row = selectedCell.closest('tr');
    const tbody = row.closest('tbody');

    const rows = Array.from(tbody.querySelectorAll('tr'));
    const currentRowIndex = rows.indexOf(row);

    const cellsInRow = Array.from(row.querySelectorAll('.editable-cell'));
    const currentCellIndex = cellsInRow.indexOf(selectedCell);

    let targetRowIndex = currentRowIndex;
    let targetCellIndex = currentCellIndex;

    if (direction === 'left')  targetCellIndex--;
    if (direction === 'right') targetCellIndex++;
    if (direction === 'up')    targetRowIndex--;
    if (direction === 'down')  targetRowIndex++;

    const targetRow = rows[targetRowIndex];
    if (!targetRow) return;

    const targetCells = Array.from(targetRow.querySelectorAll('.editable-cell'));
    const targetCell = targetCells[targetCellIndex];
    if (!targetCell) return;

    selectCell(targetCell, false);

    targetCell.scrollIntoView({
        block: 'nearest',
        inline: 'nearest'
    });
}

// Al hacer clic en cualquier celda editable, se selecciona.
// Click normal: selecciona una sola celda.
// Ctrl + click: agrega o quita celdas de la selección múltiple.
document.querySelectorAll('.editable-cell').forEach(td => {
    td.addEventListener('click', event => {
        selectCell(td, event.ctrlKey);
    });
});


// Control global del teclado.
// Permite escribir códigos y moverse como en Excel.
document.addEventListener('keydown', event => {
    if (!selectedCell) return;

    const key = event.key;
    const upperKey = key.toUpperCase();

    if (/^[A-Z0-9]$/.test(upperKey)) {
        event.preventDefault();

        if (typingBuffer && upperKey === '4' && ['D', 'N'].includes(typingBuffer)) {
            const cellsToApply = [...pendingCells];
            clearTimeout(typingTimeout);
            applyCodeToSelection(`${typingBuffer}4`, cellsToApply);
            return;
        }

        if (typingBuffer) {
            clearTypingPreview();
        }

        if (upperKey === 'D' || upperKey === 'N') {
            beginAmbiguousCode(upperKey);
            return;
        }

        if (VALID_CODES.includes(upperKey)) {
            applyCodeToSelection(upperKey);
            return;
        }

        return;
    }

    if (key === 'Backspace' || key === 'Delete') {
        event.preventDefault();

        clearTypingPreview();
        applyCodeToSelection('');

        return;
    }

    if (key === 'ArrowLeft') {
        event.preventDefault();
        clearTypingPreview();
        moveSelection('left');
        return;
    }

    if (key === 'ArrowRight') {
        event.preventDefault();
        clearTypingPreview();
        moveSelection('right');
        return;
    }

    if (key === 'ArrowUp') {
        event.preventDefault();
        clearTypingPreview();
        moveSelection('up');
        return;
    }

    if (key === 'ArrowDown') {
        event.preventDefault();
        clearTypingPreview();
        moveSelection('down');
        return;
    }

    if (key === 'Tab') {
        event.preventDefault();
        clearTypingPreview();

        if (event.shiftKey) {
            moveSelection('left');
        } else {
            moveSelection('right');
        }

        return;
    }

    if (key === 'Enter') {
        event.preventDefault();
        clearTypingPreview();
        moveSelection('down');
        return;
    }

    if (key === 'Escape') {
        clearTypingPreview();

        selectedCells.forEach(cell => {
            cell.classList.remove('selected');
        });

        selectedCells = [];
        selectedCell = null;

        updateDetalle(null, null);

        return;
    }
});


// ── TOAST NOTIFICATIONS ──
function showToast(type, title, msg, duration = 5000) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: '<i class="fa-solid fa-circle-check"></i>',
        error:   '<i class="fa-solid fa-circle-xmark"></i>',
        warn:    '<i class="fa-solid fa-triangle-exclamation"></i>',
        info:    '<i class="fa-solid fa-circle-info"></i>'
    };

    const lines = msg.split('\n').map(l => `<div>${l}</div>`).join('');

    toast.innerHTML = `
        <span class="toast-icon">${icons[type]}</span>
        <div class="toast-body">
            <div class="toast-title">${title}</div>
            <div class="toast-msg">${lines}</div>
            <div class="toast-progress" style="animation-duration:${duration}ms"></div>
        </div>
        <button class="toast-close" type="button">
            <i class="fa-solid fa-xmark"></i>
        </button>
    `;

    // Botón de cierre usando addEventListener en lugar de onclick inline.
    toast.querySelector('.toast-close').addEventListener('click', () => {
        dismissToast(toast);
    });

    container.appendChild(toast);

    setTimeout(() => dismissToast(toast), duration);
}

function dismissToast(toast) {
    if (!toast) return;
    toast.classList.add('hide');
    setTimeout(() => toast.remove(), 320);
}


// ── CSRF ──
function getCSRFToken() {
    const cookie = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='));

    return cookie ? cookie.split('=')[1] : '';
}


// ── GUARDAR PROGRAMACIÓN ──
const saveBtn = document.querySelector('.btn-save');

if (saveBtn) {
    saveBtn.addEventListener('click', async () => {
        if (typingBuffer) {
            const codeToApply = typingBuffer;
            const cellsToApply = [...pendingCells];
            clearTimeout(typingTimeout);
            applyCodeToSelection(codeToApply, cellsToApply);
        }
        const turnos = recopilarTurnos();

        try {
            saveBtn.disabled = true;
            saveBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Guardando...';

            const response = await fetch(window.location.href, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({ turnos })
            });

            const data = await response.json();

            if (!response.ok || !data.ok) {
                showToast('error', 'Error al guardar', data.error || 'Ocurrió un error al guardar la programación.');
                return;
            }

            if (data.errores && data.errores.length > 0) {
                showToast('error', data.message, data.errores.join('\n'));
                return;
            }

            if (data.advertencias && data.advertencias.length > 0) {
                showToast('warn', data.message, 'Advertencias:\n' + data.advertencias.join('\n'));
            } else {
                showToast('success', '¡Guardado!', data.message || 'Programación guardada correctamente.');
            }

        } catch (error) {
            showToast('error', 'Sin conexión', 'No se pudo conectar con el servidor.');
        } finally {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Guardar programación';
        }
    });
}


// Inicializa el panel derecho al cargar.
if (activeRow) {
    updatePanel(activeRow);
}
