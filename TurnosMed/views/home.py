from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from TurnosMed.models import Turno
from TurnosMed.views.utils import get_personal, get_total_pendientes


@login_required
def home(request):
    usuario = request.user
    if not usuario.es_jefe():
        messages.error(request, 'No tiene permisos para acceder.')
        return redirect('signin')

    hoy = timezone.localdate()

    fecha_param = request.GET.get('fecha')
    fecha_base = datetime.strptime(fecha_param, '%Y-%m-%d').date() if fecha_param else hoy

    # Personal según rol
    personal = get_personal(usuario)

    area_id = request.GET.get('area')
    sala_id = request.GET.get('sala')

    if usuario.es_jefe_departamento() and area_id and area_id != 'all':
        personal = personal.filter(area_id=area_id)

    elif usuario.es_jefe_area() and sala_id and sala_id != 'all':
        personal = personal.filter(sala_id=sala_id)

    personal = personal.order_by('rol', 'apellidos', 'nombre')

    # Turnos de hoy (solo los que tienen código, los libres no cuentan)
    turnos_hoy = Turno.objects.filter(
        trabajador__in=personal,
        fecha=hoy
    ).exclude(codigo='').count()
    turnos_mes = Turno.objects.filter(
        trabajador__in=personal,
        fecha__year=fecha_base.year,
        fecha__month=fecha_base.month,
    ).exclude(codigo='')
    horas_mes = sum(turno.horas for turno in turnos_mes)

    # Semana actual
    inicio_semana = fecha_base - timezone.timedelta(days=fecha_base.weekday())
    fin_semana = inicio_semana + timezone.timedelta(days=6)
    dias_semana = [inicio_semana + timezone.timedelta(days=i) for i in range(7)]

    turnos_semana = Turno.objects.filter(
        trabajador__in=personal,
        fecha__range=(inicio_semana, fin_semana)
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
        'usuario': usuario,
        'hoy': hoy,
        'dias_semana': dias_semana,
        'inicio_semana': inicio_semana,
        'fin_semana': fin_semana,
        'semana_anterior': inicio_semana - timezone.timedelta(days=7),
        'semana_siguiente': inicio_semana + timezone.timedelta(days=7),
        'turnos_hoy': turnos_hoy,
        'horas_mes': horas_mes,
        'total_pendientes': get_total_pendientes(usuario),
        'filas': filas,
        'areas': (
            usuario.departamento.areas.filter(activo=True)
            if usuario.es_jefe_departamento() and usuario.departamento
            else []
        ),
        'salas': (
            usuario.area.salas.filter(activa=True)
            if usuario.es_jefe_area() and usuario.area
            else []
        ),
        'area_id': area_id,
        'sala_id': sala_id,
        'filtro_actual': (
            f'area={area_id}' if area_id and area_id != 'all'
            else f'sala={sala_id}' if sala_id and sala_id != 'all'
            else ''
        ),
    }
    return render(request, 'home.html', context)
