from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from TurnosMed.models import (
    SolicitudCambioTurno,
    SolicitudVacaciones,
    SolicitudDescansoMedico,
    Notificacion,
)
from TurnosMed.views.utils import (
    get_filtro_solicitudes,
    get_iniciales,
    get_pill_codigo,
    get_total_pendientes,
)

# Estados que el jefe puede usar como filtro en la vista de solicitudes
ESTADOS_JEFE = ['entrada', 'aprobado', 'rechazado']

TIPO_LABEL_VACACIONES = {
    'adelanto': 'Adelanto de vacaciones',
}

# Helpers privados
def _solo_jefe(usuario):
    #Solo jefes de área y de departamento acceden a esta app.
    return usuario.es_jefe()


def _querysets_solicitudes(usuario, estado='entrada'):
    # Devuelve los tres querysets de solicitudes filtrados por usuario y estado.
    # Los jefes solo ven la fase 1 (estados propios de su revisión).

    filtro = get_filtro_solicitudes(usuario)

    cambios = SolicitudCambioTurno.objects.filter(**filtro).select_related(
        'solicitante', 'companero',
        'turno_original', 'turno_destino', 'revisado_por',
    )
    vacaciones = SolicitudVacaciones.objects.filter(**filtro).select_related(
        'solicitante', 'revisado_por',
    )
    descansos = SolicitudDescansoMedico.objects.filter(**filtro).select_related(
        'solicitante', 'revisado_por',
    )

    if estado == 'entrada':
        cambios = cambios.filter(estado='pendiente')
        vacaciones = vacaciones.filter(estado='pendiente')
        descansos = descansos.filter(estado='pendiente')
    elif estado == 'aprobado':
        cambios = cambios.filter(estado='procesado')
        vacaciones = vacaciones.filter(estado__in=['aprobado_jefe', 'procesado'])
        descansos = descansos.filter(estado__in=['aprobado_jefe', 'procesado'])
    elif estado == 'rechazado':
        cambios = cambios.filter(estado='rechazado_jefe')
        vacaciones = vacaciones.filter(estado__in=['rechazado_jefe', 'rechazado_admin'])
        descansos = descansos.filter(estado__in=['rechazado_jefe', 'rechazado_admin'])

    return cambios, vacaciones, descansos


def _build_solicitudes_lista(usuario, estado='entrada'):
    # Construye la lista unificada de solicitudes para el template.
    cambios, vacaciones, descansos = _querysets_solicitudes(usuario, estado)
    lista = []

    for sol in cambios:
        lista.append({
            'id': sol.id,
            'tipo': 'cambio_turno',
            'tipo_url': 'cambio-turno',
            'tipo_label': 'Cambio de turno',
            'solicitante_nombre': f'{sol.solicitante.apellidos}, {sol.solicitante.nombre}',
            'solicitante_iniciales': get_iniciales(sol.solicitante),
            'cargo_display': sol.solicitante.cargo_display(),
            'fecha_solicitud': sol.fecha_solicitud,
            'estado': sol.estado,
            'estado_display': sol.get_estado_display(),
        })

    for sol in vacaciones:
        lista.append({
            'id': sol.id,
            'tipo': 'vacaciones',
            'tipo_url': 'vacaciones',
            'tipo_label': TIPO_LABEL_VACACIONES.get(sol.tipo, 'Vacaciones'),
            'solicitante_nombre': f'{sol.solicitante.apellidos}, {sol.solicitante.nombre}',
            'solicitante_iniciales': get_iniciales(sol.solicitante),
            'cargo_display': sol.solicitante.cargo_display(),
            'fecha_solicitud': sol.fecha_solicitud,
            'estado': sol.estado,
            'estado_display': sol.get_estado_display(),
        })

    for sol in descansos:
        lista.append({
            'id': sol.id,
            'tipo': 'descanso_medico',
            'tipo_url': 'descanso-medico',
            'tipo_label': 'Descanso médico',
            'solicitante_nombre': f'{sol.solicitante.apellidos}, {sol.solicitante.nombre}',
            'solicitante_iniciales': get_iniciales(sol.solicitante),
            'cargo_display': sol.solicitante.cargo_display(),
            'fecha_solicitud': sol.fecha_solicitud,
            'estado': sol.estado,
            'estado_display': sol.get_estado_display(),
        })

    lista.sort(key=lambda x: x['fecha_solicitud'], reverse=True)
    return lista


def _get_solicitud(tipo, pk):
    # Devuelve la instancia de solicitud correcta según su tipo.
    mapa = {
        'cambio-turno': SolicitudCambioTurno,
        'descanso-medico': SolicitudDescansoMedico,
        'vacaciones': SolicitudVacaciones,
    }
    modelo = mapa.get(tipo)
    if modelo is None:
        return None
    try:
        return modelo.objects.get(id=pk)
    except modelo.DoesNotExist:
        return None


def _usuario_puede_revisar(usuario, solicitud):
    # Verifica que el jefe tenga jurisdicción sobre el solicitante
    # El admin no pasa por aqui (tiene sus propias vistas en AdminPanel)

    solicitante = solicitud.solicitante

    if usuario.es_jefe_departamento():
        return (
            solicitante.rol == 'jefe_area'
            and solicitante.departamento_id == usuario.departamento_id
        )

    if usuario.es_jefe_area():
        return (
            solicitante.rol == 'asistencial'
            and solicitante.departamento_id == usuario.departamento_id
            and solicitante.area_id == usuario.area_id
        )

    return False

@login_required
def solicitudes(request):
    usuario = request.user

    if not _solo_jefe(usuario):
        return HttpResponseForbidden('No tienes permisos para ver esta sección.')

    # Default: bandeja de entrada (pendientes de revisión)
    estado = request.GET.get('estado', 'entrada')
    if estado not in ESTADOS_JEFE:
        estado = 'entrada'

    context = {
        'usuario': usuario,
        'hoy': timezone.localdate(),
        'estado_actual': estado,
        'estados_jefe': ESTADOS_JEFE,
        'solicitudes_lista': _build_solicitudes_lista(usuario, estado),
        'total_pendientes': get_total_pendientes(usuario),
    }
    return render(request, 'solicitudes.html', context)


@login_required
def detalle_cambio_turno(request, id):
    usuario = request.user

    if not _solo_jefe(usuario):
        return HttpResponseForbidden()

    sol = get_object_or_404(
        SolicitudCambioTurno.objects.select_related(
            'solicitante', 'companero',
            'turno_original', 'turno_destino',
            'turno_original__trabajador', 'turno_destino__trabajador',
            'revisado_por',
        ),
        id=id,
    )

    if not _usuario_puede_revisar(usuario, sol):
        return HttpResponseForbidden()

    context = {
        'sol': sol,
        'solicitante_iniciales': get_iniciales(sol.solicitante),
        'companero_iniciales':   get_iniciales(sol.companero),
        'turno_original':        sol.turno_original,
        'turno_original_pill':   get_pill_codigo(sol.turno_original.codigo),
        'turno_destino':         sol.turno_destino,
        'turno_destino_pill':    get_pill_codigo(sol.turno_destino.codigo),
    }
    return render(request, 'detalle_cambio_turno.html', context)


@login_required
def detalle_descanso_medico(request, id):
    usuario = request.user

    if not _solo_jefe(usuario):
        return HttpResponseForbidden()

    sol = get_object_or_404(
        SolicitudDescansoMedico.objects.select_related('solicitante', 'revisado_por'),
        id=id,
    )

    if not _usuario_puede_revisar(usuario, sol):
        return HttpResponseForbidden()

    context = {
        'sol': sol,
        'solicitante_iniciales': get_iniciales(sol.solicitante),
        'dias_totales': sol.dias_totales,
        'en_curso':     sol.en_curso,
    }
    return render(request, 'detalle_descanso_medico.html', context)


@login_required
def detalle_vacaciones(request, id):
    usuario = request.user

    if not _solo_jefe(usuario):
        return HttpResponseForbidden()

    sol = get_object_or_404(
        SolicitudVacaciones.objects.select_related('solicitante', 'revisado_por'),
        id=id,
    )

    if not _usuario_puede_revisar(usuario, sol):
        return HttpResponseForbidden()

    # Historial: adelantos ya procesados del mismo trabajador
    historial = SolicitudVacaciones.objects.filter(
        solicitante=sol.solicitante,
        estado='procesado',
    ).exclude(id=sol.id).order_by('-fecha_inicio')[:5]

    context = {
        'sol': sol,
        'solicitante_iniciales': get_iniciales(sol.solicitante),
        'dias_totales': sol.dias_totales,
        'historial':    historial,
    }
    return render(request, 'detalle_vacaciones.html', context)


@login_required
def revisar_solicitud(request, tipo, id):
    # Vista unificada para que el jefe apruebe o rechaze una solicitud (fase 1).
    # Regla especial: SolicitudCambioTurno no requiere segunda fase (admin),
    # por lo que si el jefe la aprueba el estado pasa directo a 'procesado'.
    # Para el resto, aprobar la deja en 'aprobado_jefe' a la espera del admin.

    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    usuario = request.user

    if not _solo_jefe(usuario):
        return JsonResponse({'error': 'Sin permisos'}, status=403)

    sol = _get_solicitud(tipo, id)
    if sol is None:
        return JsonResponse({'error': 'Solicitud no encontrada'}, status=404)

    if not _usuario_puede_revisar(usuario, sol):
        return JsonResponse({'error': 'Sin permisos para revisar esta solicitud'}, status=403)

    # Solo se puede revisar si está pendiente (fase 1)
    if not sol.pendiente_jefe:
        return JsonResponse({'error': 'Esta solicitud ya fue revisada.'}, status=400)

    accion = request.POST.get('accion', '').strip()
    if accion not in ['aprobar', 'rechazar']:
        return JsonResponse({'error': 'Acción inválida'}, status=400)

    comentario = request.POST.get('comentario', '').strip()

    try:
        with transaction.atomic():
            if accion == 'rechazar':
                sol.rechazar_por_jefe(usuario, comentario)
                titulo = 'Solicitud rechazada'
                mensaje = 'Su solicitud fue rechazada por el jefe responsable.'
            else:
                sol.aprobar_por_jefe(usuario, comentario)
                if isinstance(sol, SolicitudCambioTurno):
                    sol.ejecutar_cambio()
                    titulo = 'Cambio de turno aprobado'
                    mensaje = 'Su cambio de turno fue aprobado y aplicado a la programacion.'
                    Notificacion.objects.create(
                        destinatario=sol.companero,
                        tipo='cambio_turno',
                        titulo='Cambio de turno aplicado',
                        mensaje='Se aplico un cambio de turno aprobado en el que participa.',
                    )
                else:
                    titulo = 'Solicitud aprobada por jefatura'
                    mensaje = 'Su solicitud fue aprobada y enviada a administracion.'

            tipo_notificacion = {
                'cambio-turno': 'cambio_turno',
                'vacaciones': 'vacaciones',
                'descanso-medico': 'descanso',
            }[tipo]
            Notificacion.objects.create(
                destinatario=sol.solicitante,
                tipo=tipo_notificacion,
                titulo=titulo,
                mensaje=mensaje,
            )
    except ValidationError as exc:
        return JsonResponse({'error': exc.messages[0]}, status=400)

    return JsonResponse({
        'ok': True,
        'estado': sol.estado,
        'estado_display': sol.get_estado_display(),
    })
