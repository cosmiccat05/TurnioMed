//base.js
// Seleccionamos los elementos por el ID que pusimos arriba
const userCard = document.getElementById('userCard');
const userDropdown = document.getElementById('userDropdown');

// Al hacer clic en la tarjeta, alterna la clase 'show'
userCard.addEventListener('click', function(e) {
    e.stopPropagation(); // Evita que el clic cierre el menú inmediatamente
    userDropdown.classList.toggle('show');
});

// Si haces clic en cualquier otro lado de la página, cierra el menú
document.addEventListener('click', function() {
    userDropdown.classList.remove('show');
});
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