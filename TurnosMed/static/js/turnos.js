let typingBuffer = '';
let typingTimeout = null;

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

// Meta mensual referencial para el panel derecho.
const META_TARGET = 150;

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

// Marca visualmente una celda como seleccionada
// Si additive = false, limpia la selección anterior
// Si additive = true, permite seleccionar varias con Ctrl + click
function selectCell(td, additive = false) {
    if (!td) return;

    // Selección normal: limpia toodo y selecciona solo una celda.
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

    updatePanel(activeRow);
}


// Escribe o borra el código en la celda seleccionada.
function setCellCode(td, code) {
    if (!td) return;

    code = (code || '').trim().toUpperCase();

    if (code !== '' && !VALID_CODES.includes(code)) {
        td.classList.add('cell-error');

        setTimeout(() => {
            td.classList.remove('cell-error');
        }, 1000);
        return;
    }
    renderCell(td, code);
    updatePanel(td.closest('tr'));
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


// Actualiza el panel derecho con el resumen de la fila activa.
function updatePanel(row) {
    const { counts, hours } = calcStats(row);

    document.getElementById('count-d').textContent = counts.D + counts.D4;
    document.getElementById('count-t').textContent = counts.T;
    document.getElementById('count-m').textContent = counts.M;
    document.getElementById('count-n').textContent = counts.N + counts.N4;

    const pct = Math.min((hours / META_TARGET) * 100, 100).toFixed(1);

    document.getElementById('hours-total').textContent = hours + ' h';
    document.getElementById('hours-meta').textContent = `${hours} / ${META_TARGET} h requeridas`;
    document.getElementById('hours-bar-fill').style.width = pct + '%';

    const diff = META_TARGET - hours;
    const statusEl = document.getElementById('hours-status');

    if (diff > 0) {
        statusEl.innerHTML = `
            <i class="fa-solid fa-triangle-exclamation"></i>
            Faltan ${diff} h para completar el mes
        `;
        statusEl.className = 'hours-status warn';
    } else {
        statusEl.innerHTML = `
            <i class="fa-solid fa-circle-check"></i>
            Meta mensual cumplida
        `;
        statusEl.className = 'hours-status ok';
    }
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

    if (direction === 'left') {
        targetCellIndex--;
    }

    if (direction === 'right') {
        targetCellIndex++;
    }

    if (direction === 'up') {
        targetRowIndex--;
    }

    if (direction === 'down') {
        targetRowIndex++;
    }

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

    clearTimeout(typingTimeout);

    typingBuffer += upperKey;

    const possibleCodes = VALID_CODES.filter(code =>
        code.startsWith(typingBuffer)
    );

    // Si no coincide con ningún código válido, reinicia.
    if (possibleCodes.length === 0) {
        typingBuffer = '';
        return;
    }

    // Si coincide exactamente, escribe.
    if (VALID_CODES.includes(typingBuffer)) {
        const cellsToEdit = selectedCells.length > 0
            ? selectedCells
            : [selectedCell];

        cellsToEdit.forEach(cell => {
            setCellCode(cell, typingBuffer);
        });

        typingBuffer = '';
        return;
    }

    // Espera breve por si viene un segundo carácter (ej: D4)
    typingTimeout = setTimeout(() => {
        typingBuffer = '';
    }, 800);

    return;

    // Backspace o Delete limpia una o varias celdas seleccionadas.
    if (key === 'Backspace' || key === 'Delete') {
        event.preventDefault();

        const cellsToClear = selectedCells.length > 0 ? selectedCells : [selectedCell];

        cellsToClear.forEach(cell => {
            setCellCode(cell, '');
        });

        return;
    }

    // Movimiento con flechas.
    if (key === 'ArrowLeft') {
        event.preventDefault();
        moveSelection('left');
        return;
    }

    if (key === 'ArrowRight') {
        event.preventDefault();
        moveSelection('right');
        return;
    }

    if (key === 'ArrowUp') {
        event.preventDefault();
        moveSelection('up');
        return;
    }

    if (key === 'ArrowDown') {
        event.preventDefault();
        moveSelection('down');
        return;
    }

    // Tab avanza o retrocede como Excel.
    if (key === 'Tab') {
        event.preventDefault();

        if (event.shiftKey) {
            moveSelection('left');
        } else {
            moveSelection('right');
        }

        return;
    }

    // Enter baja a la siguiente fila.
    if (key === 'Enter') {
        event.preventDefault();
        moveSelection('down');
        return;
    }

    // Escape limpia toda la selección.
    if (key === 'Escape') {
        selectedCells.forEach(cell => {
            cell.classList.remove('selected');
        });
        selectedCells = [];
        selectedCell = null;

        return;
    }
});


// Inicializa el panel derecho al cargar.
if (activeRow) {
    updatePanel(activeRow);
}