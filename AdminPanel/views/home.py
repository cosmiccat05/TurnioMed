from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from TurnosMed.models import (
    ProgramacionVacaciones,
    SolicitudDescansoMedico,
    SolicitudVacaciones,
    Usuario,
)
from AdminPanel.views.helpers import total_pendientes_admin


@login_required
def home(request):
    if not request.user.es_admin():
        return redirect('home')

    hoy = timezone.localdate()
    limite_proximos = hoy + timedelta(days=30)
    programaciones = ProgramacionVacaciones.objects.select_related('trabajador')
    adelantos_aprobados = SolicitudVacaciones.objects.filter(estado='procesado')
    proximos_programados = programaciones.filter(
        fecha_inicio__gt=hoy,
        fecha_inicio__lte=limite_proximos,
    ).order_by('fecha_inicio')
    proximos_adelantos = adelantos_aprobados.filter(
        fecha_inicio__gt=hoy,
        fecha_inicio__lte=limite_proximos,
    ).select_related('solicitante').order_by('fecha_inicio')
    proximos = sorted(
        [
            {
                'trabajador': item.trabajador,
                'fecha_inicio': item.fecha_inicio,
                'dias_totales': item.dias_totales,
                'estado_display': item.get_estado_display(),
            }
            for item in proximos_programados
        ] + [
            {
                'trabajador': item.solicitante,
                'fecha_inicio': item.fecha_inicio,
                'dias_totales': item.dias_totales,
                'estado_display': 'Adelanto aprobado',
            }
            for item in proximos_adelantos
        ],
        key=lambda item: item['fecha_inicio'],
    )[:5]
    vacaciones_recientes = SolicitudVacaciones.objects.filter(
        fecha_procesado__isnull=False,
    ).select_related('solicitante').order_by('-fecha_procesado')[:5]
    descansos_recientes = SolicitudDescansoMedico.objects.filter(
        fecha_procesado__isnull=False,
    ).select_related('solicitante').order_by('-fecha_procesado')[:5]
    actividad_reciente = sorted(
        [
            {
                'trabajador': sol.solicitante,
                'tipo_display': 'Adelanto de vacaciones',
                'estado': sol.estado,
                'fecha_actualizacion': sol.fecha_procesado,
            }
            for sol in vacaciones_recientes
        ] + [
            {
                'trabajador': sol.solicitante,
                'tipo_display': 'Descanso medico',
                'estado': sol.estado,
                'fecha_actualizacion': sol.fecha_procesado,
            }
            for sol in descansos_recientes
        ],
        key=lambda item: item['fecha_actualizacion'],
        reverse=True,
    )[:5]

    context = {
        'hoy': hoy,
        'total_pendientes': total_pendientes_admin(),
        'total_trabajadores': Usuario.objects.exclude(rol='admin').count(),
        'trabajadores_activos': Usuario.objects.exclude(rol='admin').filter(is_active=True).count(),
        'en_vacaciones': programaciones.filter(
            fecha_inicio__lte=hoy,
            fecha_fin__gte=hoy,
        ).count() + adelantos_aprobados.filter(
            fecha_inicio__lte=hoy,
            fecha_fin__gte=hoy,
        ).count(),
        'proximos_vacaciones': programaciones.filter(
            fecha_inicio__gt=hoy,
            fecha_inicio__lte=limite_proximos,
        ).count() + adelantos_aprobados.filter(
            fecha_inicio__gt=hoy,
            fecha_inicio__lte=limite_proximos,
        ).count(),
        'proximos_lista': proximos,
        'actividad_reciente': actividad_reciente,
    }
    return render(request, 'panel/home.html', context)
