/* ---------- Dropdown usuario ---------- */
const userCard     = document.getElementById('userCard');
const userDropdown = document.getElementById('userDropdown');

if (userCard && userDropdown) {
    userCard.addEventListener('click', function (e) {
        e.stopPropagation();
        const isOpen = userDropdown.classList.toggle('show');
        userCard.classList.toggle('open', isOpen);
    });

    document.addEventListener('click', function () {
        userDropdown.classList.remove('show');
        userCard.classList.remove('open');
    });
}

/* ---------- Reloj ---------- */
function actualizarReloj() {
    const ahora   = new Date();
    const horas   = String(ahora.getHours()).padStart(2, '0');
    const minutos = String(ahora.getMinutes()).padStart(2, '0');
    const el = document.getElementById('reloj');
    if (el) el.textContent = `${horas}:${minutos}`;
}
actualizarReloj();
setInterval(actualizarReloj, 60_000);

/* ---------- Sidebar responsive (mobile) ---------- */
const sidebar        = document.querySelector('.sidebar');
const sidebarToggle  = document.getElementById('sidebarToggle');
const sidebarOverlay = document.getElementById('sidebarOverlay');

function openSidebar() {
    sidebar.classList.add('open');
    sidebarOverlay.classList.add('show');
    document.body.style.overflow = 'hidden';
}

function closeSidebar() {
    sidebar.classList.remove('open');
    sidebarOverlay.classList.remove('show');
    document.body.style.overflow = '';
}

if (sidebarToggle) {
    sidebarToggle.addEventListener('click', function () {
        sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
    });
}

if (sidebarOverlay) {
    sidebarOverlay.addEventListener('click', closeSidebar);
}

/* ---------- Cerrar sidebar al cambiar a desktop ---------- */
const mq = window.matchMedia('(min-width: 769px)');
mq.addEventListener('change', function (e) {
    if (e.matches) closeSidebar();
});

/* ---------- Auto-cierre de alertas (5 s) ---------- */
document.querySelectorAll('.alert').forEach(function (alert) {
    setTimeout(function () {
        alert.style.transition = 'opacity .4s ease';
        alert.style.opacity = '0';
        setTimeout(function () { alert.remove(); }, 400);
    }, 5000);
});