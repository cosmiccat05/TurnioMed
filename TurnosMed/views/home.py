from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from TurnosMed.models import (
    Usuario, Turno,
    SolicitudCambioTurno, SolicitudVacaciones, SolicitudDescansoMedico
)

@login_required
def home(request):
    usuario = request.user
    hoy     = timezone.now().date()

    # Filtro base de personal según rol del usuario logueado
    if usuario.es_jefe_departamento():
        personal = Usuario.objects.filter(
            departamento=usuario.departamento,
            rol__in=['jefe_area', 'asistencial'],
            is_active=True
        ).exclude(id=usuario.id)

    elif usuario.es_jefe_area():
        personal = Usuario.objects.filter(
            departamento=usuario.departamento,
            area=usuario.area,
            rol='asistencial',
            is_active=True
        )

    else:
        personal = Usuario.objects.none()

    area_id = request.GET.get('area')
    sala_id = request.GET.get('sala')

    if usuario.es_jefe_departamento():
        if area_id and area_id != 'all':
            personal = personal.filter(area_id=area_id)

    elif usuario.es_jefe_area():
        if sala_id and sala_id != 'all':
            personal = personal.filter(sala_id=sala_id)

    personal = personal.order_by('rol', 'apellidos', 'nombre')

    # Turnos de hoy
    turnos_hoy = Turno.objects.filter(
        trabajador__in=personal,
        fecha=hoy
    ).exclude(codigo='')

    # Solicitudes pendientes
    if usuario.es_jefe_departamento():
        filtro_solicitudes = {
            'solicitante__departamento': usuario.departamento,
            'estado': 'pendiente'
        }
    elif usuario.es_jefe_area():
        filtro_solicitudes = {
            'solicitante__departamento': usuario.departamento,
            'solicitante__area': usuario.area,
            'estado': 'pendiente'
        }
    else:
        filtro_solicitudes = {
            'id__isnull': True
        }

    total_pendientes = (
            SolicitudCambioTurno.objects.filter(**filtro_solicitudes).count()
            + SolicitudVacaciones.objects.filter(**filtro_solicitudes).count()
            + SolicitudDescansoMedico.objects.filter(**filtro_solicitudes).count()
    )

    # Semana actual
    inicio_semana = hoy - timezone.timedelta(days=hoy.weekday())
    dias_semana   = [inicio_semana + timezone.timedelta(days=i) for i in range(7)]

    turnos_semana = Turno.objects.filter(
        trabajador__in=personal,
        fecha__range=(inicio_semana, inicio_semana + timezone.timedelta(days=6))
    ).select_related('trabajador')

    tabla = {p.id: {dia: None for dia in dias_semana} for p in personal}
    for turno in turnos_semana:
        if turno.trabajador_id in tabla:
            tabla[turno.trabajador_id][turno.fecha] = turno

    filas = [
        {'persona': p, 'turnos': [tabla[p.id][dia] for dia in dias_semana]}
        for p in personal
    ]

    context = {
        'usuario':          usuario,
        'hoy':              hoy,
        'dias_semana':      dias_semana,
        'turnos_hoy':       turnos_hoy.count(),
        'total_pendientes': total_pendientes,
        'filas':            filas,
        'areas': usuario.departamento.areas.filter(activo=True) if usuario.es_jefe_departamento() and usuario.departamento else [],
        'salas': usuario.area.salas.filter(activa=True) if usuario.es_jefe_area() and usuario.area else [],
        'area_id': area_id,
        'sala_id': sala_id,
    }
    return render(request, 'home.html', context)