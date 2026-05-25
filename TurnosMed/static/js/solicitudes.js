document.querySelectorAll('.sol-item').forEach(item => {
    item.addEventListener('click', () => {
        document.querySelectorAll('.sol-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');

        const id = item.dataset.id;
        const tipo = item.dataset.tipo;

        const empty = document.getElementById('sol-empty');
        const content = document.getElementById('sol-detail-content');

        empty.style.display = 'none';
        content.style.display = 'flex';

        const urlMap = {
            'cambio-turno': id => `/solicitudes/${id}/detalle/cambio-turno/`,
            'descanso-medico': id => `/solicitudes/${id}/detalle/descanso-medico/`,
            'vacaciones': id => `/solicitudes/${id}/detalle/vacaciones/`,
        };

        const url = urlMap[tipo]?.(id);

        if (!url) return;

        content.dataset.currentUrl = url;

        content.innerHTML = `
            <div class="detail-placeholder">
                <i class="fa-solid fa-spinner fa-spin"></i>
                <span>Cargando detalle…</span>
            </div>
        `;

        fetch(url)
            .then(r => {
                if (!r.ok) throw new Error('No se pudo cargar el detalle');
                return r.text();
            })
            .then(html => {
                content.innerHTML = html;
            })
            .catch(() => {
                content.innerHTML = `
                    <div class="detail-placeholder">
                        <i class="fa-solid fa-circle-exclamation"></i>
                        <span>No se pudo cargar el detalle.</span>
                    </div>
                `;
            });
    });
});

document.querySelectorAll('.sol-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.sol-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
    });
});

document.getElementById('searchInput')?.addEventListener('input', function () {
    const q = this.value.toLowerCase();

    document.querySelectorAll('.sol-item').forEach(item => {
        const text = item.textContent.toLowerCase();
        item.style.display = text.includes(q) ? '' : 'none';
    });
});

function getCSRFToken() {
    const cookie = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrftoken='));

    return cookie ? cookie.split('=')[1] : '';
}

function accionSolicitud(accion, tipo, id) {
    const url = `/solicitudes/${tipo}/${id}/revisar/`;

    const body = new URLSearchParams();
    body.append('accion', accion);

    fetch(url, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCSRFToken(),
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: body.toString(),
    })
    .then(r => r.json())
    .then(data => {
        if (!data.ok) {
            alert(data.error || 'No se pudo procesar la solicitud.');
            return;
        }

        const itemActivo = document.querySelector('.sol-item.active');

        if (itemActivo) {
            const estadoEl = itemActivo.querySelector('.sol-status');

            if (estadoEl) {
                const esRechazado = data.estado === 'rechazado_jefe';
                estadoEl.textContent = `\u25cf ${data.estado_display}`;
                estadoEl.className = `sol-status ${esRechazado ? 'rechazado_jefe' : data.estado}`;
            }
        }

        const content = document.getElementById('sol-detail-content');

        if (content?.dataset.currentUrl) {
            fetch(content.dataset.currentUrl)
                .then(r => r.text())
                .then(html => {
                    content.innerHTML = html;
                });
        }
    })
    .catch(() => {
        alert('Error al procesar la solicitud.');
    });
}
