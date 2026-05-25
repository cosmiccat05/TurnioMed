//base.js
// Seleccionamos los elementos por el ID que pusimos arriba
const userCard = document.getElementById('userCard');
const userDropdown = document.getElementById('userDropdown');

if (userCard && userDropdown) {
    userCard.addEventListener('click', function(e) {
        e.stopPropagation();
        const isOpen = userDropdown.classList.toggle('show');
        userCard.classList.toggle('open', isOpen);
    });

    document.addEventListener('click', function() {
        userDropdown.classList.remove('show');
        userCard.classList.remove('open');
    });
}
// para q el reloj recupere la hora irl
function actualizarReloj() {
    const ahora = new Date();
    const horas   = String(ahora.getHours()).padStart(2, '0');
    const minutos = String(ahora.getMinutes()).padStart(2, '0');
    const el = document.getElementById('reloj');
    if (el) el.textContent = `${horas}:${minutos}`;
}
actualizarReloj();
setInterval(actualizarReloj, 60000);
