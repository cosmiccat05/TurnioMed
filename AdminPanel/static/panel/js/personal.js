// Modal de confirmación de eliminación — <dialog> nativo
const modalEliminar  = document.getElementById('modal-eliminar');
const btnCancelar    = document.getElementById('btn-cancelar-modal');

function abrirModalEliminar(nombre, tipo, rol, url) {
    // Iniciales desde el nombre (primeras letras de cada palabra)
    const iniciales = nombre
        .split(/[\s,]+/)
        .filter(Boolean)
        .slice(0, 2)
        .map(p => p[0].toUpperCase())
        .join('');

    document.getElementById('modal-iniciales').textContent = iniciales;
    document.getElementById('modal-nombre').textContent = nombre;
    document.getElementById('modal-tipo').textContent = tipo;
    document.getElementById('modal-rol').textContent = rol;
    document.getElementById('modal-form').action = url;

    modalEliminar.showModal();
}

btnCancelar?.addEventListener('click', () => modalEliminar.close());

// Cerrar al hacer click en el backdrop (fuera del card)
modalEliminar?.addEventListener('click', function (e) {
    const rect = this.getBoundingClientRect();
    const clickFuera = (
        e.clientX < rect.left || e.clientX > rect.right ||
        e.clientY < rect.top || e.clientY > rect.bottom
    );
    if (clickFuera) this.close();
});

// Selects dinámicos: área filtra por departamento, sala filtra por área
// URLs leídas desde data-* del <form> — sin rutas Django hardcodeadas en JS
const formPersonal = document.getElementById('form-personal');

if (formPersonal) {
    const urlAreas= formPersonal.dataset.urlAreas;
    const urlSalas= formPersonal.dataset.urlSalas;
    const selDepartamento = document.getElementById('id_departamento');
    const selArea= document.getElementById('id_area');
    const selSala= document.getElementById('id_sala');

    async function cargarOpciones(url, params, select, valorActual = '') {
        try {
            const res= await fetch(`${url}?${new URLSearchParams(params)}`);
            const data  = await res.json();
            const items = data.areas ?? data.salas ?? [];

            select.innerHTML = '<option value="">---------</option>';
            items.forEach(item => {
                const opt       = document.createElement('option');
                opt.value = item.id;
                opt.textContent = item.nombre;
                if (String(item.id) === String(valorActual)) opt.selected = true;
                select.appendChild(opt);
            });
        } catch {
            console.error('Error cargando opciones:', url);
        }
    }

    selDepartamento?.addEventListener('change', async function () {
        selArea.innerHTML = '<option value="">---------</option>';
        selSala.innerHTML = '<option value="">---------</option>';
        if (this.value) await cargarOpciones(urlAreas, { departamento_id: this.value }, selArea);
    });

    selArea?.addEventListener('change', async function () {
        selSala.innerHTML = '<option value="">---------</option>';
        if (this.value) await cargarOpciones(urlSalas, { area_id: this.value }, selSala);
    });
}