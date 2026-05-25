from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from AdminPanel.views.helpers import total_pendientes_admin
from TurnosMed.models import Notificacion, SolicitudDescansoMedico, SolicitudVacaciones


TIPOS_SOLICITUD = {
    'vacaciones': SolicitudVacaciones,
    'descanso-medico': SolicitudDescansoMedico,
}
ESTADOS_ADMIN = ['aprobado_jefe', 'procesado', 'rechazado_admin']


def _solicitudes_unificadas(estado, buscar):
    vacaciones = SolicitudVacaciones.objects.filter(estado=estado).select_related(
        'solicitante', 'revisado_por', 'procesado_por'
    )
    descansos = SolicitudDescansoMedico.objects.filter(estado=estado).select_related(
        'solicitante', 'revisado_por', 'procesado_por'
    )
    if buscar:
        filtro = (
            Q(solicitante__nombre__icontains=buscar)
            | Q(solicitante__apellidos__icontains=buscar)
            | Q(solicitante__dni__icontains=buscar)
        )
        vacaciones = vacaciones.filter(filtro)
        descansos = descansos.filter(filtro)
    lista = [
        {'tipo': 'vacaciones', 'tipo_label': 'Adelanto de vacaciones', 'sol': sol}
        for sol in vacaciones
    ]
    lista += [
        {'tipo': 'descanso-medico', 'tipo_label': 'Descanso medico', 'sol': sol}
        for sol in descansos
    ]
    return sorted(lista, key=lambda item: item['sol'].fecha_solicitud, reverse=True)


@login_required
def solicitudes(request):
    if not request.user.es_admin():
        return redirect('home')
    estado = request.GET.get('estado', 'aprobado_jefe')
    if estado not in ESTADOS_ADMIN:
        estado = 'aprobado_jefe'
    buscar = request.GET.get('buscar', '').strip()
    return render(request, 'panel/solicitudes.html', {
        'hoy': timezone.localdate(),
        'estado_actual': estado,
        'buscar': buscar,
        'solicitudes_lista': _solicitudes_unificadas(estado, buscar),
        'total_pendientes': total_pendientes_admin(),
    })


@login_required
def detalle_solicitud(request, tipo, id):
    if not request.user.es_admin():
        return redirect('home')
    modelo = TIPOS_SOLICITUD.get(tipo)
    if not modelo:
        return redirect('admin_solicitudes')
    sol = get_object_or_404(
        modelo.objects.select_related('solicitante', 'revisado_por', 'procesado_por'),
        id=id,
    )
    template = 'panel/detalle_vacaciones.html' if tipo == 'vacaciones' else 'panel/detalle_descanso.html'
    return render(request, template, {
        'hoy': timezone.localdate(),
        'sol': sol,
        'tipo': tipo,
        'total_pendientes': total_pendientes_admin(),
    })


@login_required
def procesar_solicitud(request, tipo, id):
    es_json = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    if not request.user.es_admin():
        return JsonResponse({'ok': False, 'error': 'Sin permisos.'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Metodo no permitido.'}, status=405)
    modelo = TIPOS_SOLICITUD.get(tipo)
    if not modelo:
        return JsonResponse({'ok': False, 'error': 'Tipo de solicitud no valido.'}, status=404)
    solicitud = get_object_or_404(modelo, id=id)
    accion = request.POST.get('accion', '').strip()
    if accion not in ['aprobar', 'rechazar']:
        return JsonResponse({'ok': False, 'error': 'Accion no valida.'}, status=400)
    try:
        solicitud.procesar_por_admin(
            request.user,
            aprobar=accion == 'aprobar',
            comentario=request.POST.get('comentario', '').strip(),
        )
    except ValidationError as exc:
        if es_json:
            return JsonResponse({'ok': False, 'error': exc.messages[0]}, status=400)
        messages.error(request, exc.messages[0])
        return redirect('admin_detalle_solicitud', tipo=tipo, id=id)

    etiqueta = 'adelanto de vacaciones' if tipo == 'vacaciones' else 'descanso medico'
    resultado = 'aprobado' if accion == 'aprobar' else 'rechazado'
    Notificacion.objects.create(
        destinatario=solicitud.solicitante,
        tipo='vacaciones' if tipo == 'vacaciones' else 'descanso',
        titulo=f'Solicitud de {etiqueta} {resultado}',
        mensaje=f'Su solicitud de {etiqueta} fue {resultado} por administracion.',
    )
    messages.success(request, f'La solicitud fue {resultado} correctamente.')
    if es_json:
        return JsonResponse({'ok': True, 'estado': solicitud.estado})
    return redirect('admin_detalle_solicitud', tipo=tipo, id=id)
