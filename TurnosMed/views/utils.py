# views/utils.py
from TurnosMed.models import Usuario, SolicitudCambioTurno, SolicitudVacaciones, SolicitudDescansoMedico

# Funciones compartidas entre views para no repetir logica lol

MESES_ES = [
    '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
]

DIAS_ES = {
    0: 'Lun',
    1: 'Mar',
    2: 'Mié',
    3: 'Jue',
    4: 'Vie',
    5: 'Sáb',
    6: 'Dom',
}

# Helpers de personal
def get_personal(usuario):

    # Devuelve el queryset de personal visible para el usuario según su rol:
    # Jefe de departamento: ve a los jefes de área de su departamento.
    # Jefe de área: ve al personal asistencial de su área.
    # Cualquier otro rol: queryset vacío.

    if usuario.es_jefe_departamento():
        return Usuario.objects.filter(
            departamento=usuario.departamento,
            rol='jefe_area',
            is_active=True
        ).exclude(id=usuario.id)

    if usuario.es_jefe_area():
        return Usuario.objects.filter(
            departamento=usuario.departamento,
            area=usuario.area,
            rol='asistencial',
            is_active=True
        )

    return Usuario.objects.none()

# Helpers de solicitudes
def get_filtro_solicitudes(usuario):
    # Devuelve el dict de filtros para consultar solicitudes según el rol
    # del usuario revisor (solo aplica para jefes - el admin usa AdminPanel).
    # - Jefe de departamento: ve solicitudes de los jefes de área de su departamento.
    # - Jefe de área: ve solicitudes del personal asistencial de su área.

    if usuario.es_jefe_departamento():
        return {
            'solicitante__rol': 'jefe_area',
            'solicitante__departamento': usuario.departamento,
        }

    if usuario.es_jefe_area():
        return {
            'solicitante__rol': 'asistencial',
            'solicitante__departamento': usuario.departamento,
            'solicitante__area': usuario.area,
        }

    # Para cualquier otro rol devolvemos un filtro que no retorna nada
    return {'id__isnull': True}


def get_total_pendientes(usuario):
    # Devuelve el total de solicitudes en estado 'pendiente' visibles
    # para el usuario (osea de fase 1: pendientes de revisión del jefe).
    # Solo aplica para jefes; el admin tiene su propio contador en AdminPanel.

    filtro = {**get_filtro_solicitudes(usuario), 'estado': 'pendiente'}
    return (
        SolicitudCambioTurno.objects.filter(**filtro).count()
        + SolicitudVacaciones.objects.filter(**filtro).count()
        + SolicitudDescansoMedico.objects.filter(**filtro).count()
    )


# Helpers de presentación
def get_iniciales(usuario):
    # Devuelve las iniciales (primera letra de nombre + apellido) de un usuario.
    nombre   = usuario.nombre[0].upper()   if usuario.nombre    else ''
    apellido = usuario.apellidos[0].upper() if usuario.apellidos else ''
    return f'{nombre}{apellido}'


def get_pill_codigo(codigo):
    # Devuelve la clase CSS correspondiente al código de turno.
    mapa = {
        'D4': 'dia',
        'D': 'dia',
        'M': 'medio',
        'T': 'tarde',
        'N4': 'noche',
        'N': 'noche',
    }
    return mapa.get(codigo, 'dia')