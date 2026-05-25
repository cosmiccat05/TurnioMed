from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from TurnosMed.models import ProgramacionVacaciones, SolicitudVacaciones
from TurnosMed.views.utils import get_iniciales, get_personal, get_total_pendientes


def _serialize_personal(personal):
    return [
        {
            'id': persona.id,
            'nombre': f'{persona.apellidos}, {persona.nombre}',
            'iniciales': get_iniciales(persona),
            'cargo': persona.cargo_display(),
        }
        for persona in personal
    ]


def _serialize_periodos(programaciones, adelantos):
    periodos = [
        {
            'trabajador_id': item.trabajador_id,
            'fecha_inicio': item.fecha_inicio.isoformat(),
            'fecha_fin': item.fecha_fin.isoformat(),
            'dias_totales': item.dias_totales,
            'estado': item.estado,
            'observaciones': item.observaciones or '',
            'tipo': 'programacion',
        }
        for item in programaciones
    ]
    periodos.extend(
        {
            'trabajador_id': item.solicitante_id,
            'fecha_inicio': item.fecha_inicio.isoformat(),
            'fecha_fin': item.fecha_fin.isoformat(),
            'dias_totales': item.dias_totales,
            'estado': item.estado,
            'observaciones': item.motivo or '',
            'tipo': 'adelanto',
        }
        for item in adelantos
    )
    return periodos


@login_required
def vacaciones(request):
    usuario = request.user

    if not usuario.es_jefe():
        messages.error(request, 'No tiene permisos para acceder.')
        return redirect('home')

    hoy = timezone.localdate()
    anio = int(request.GET.get('anio', hoy.year))

    areas = []
    salas = []
    area_id = request.GET.get('area')
    sala_id = request.GET.get('sala')
    area_seleccionada = None
    sala_seleccionada = None

    if usuario.es_jefe_departamento():
        if not usuario.departamento:
            messages.error(request, 'Su usuario no tiene un departamento asignado.')
            return redirect('home')

        areas = usuario.departamento.areas.filter(activo=True).order_by('nombre')
        if area_id and area_id != 'all':
            area_seleccionada = areas.filter(id=area_id).first()

    elif usuario.es_jefe_area():
        if not usuario.area:
            messages.error(request, 'Su usuario no tiene un area asignada.')
            return redirect('home')

        area_seleccionada = usuario.area
        salas = usuario.area.salas.filter(activa=True).order_by('nombre')
        if sala_id and sala_id != 'all':
            sala_seleccionada = salas.filter(id=sala_id).first()

    personal = get_personal(usuario)
    if usuario.es_jefe_departamento() and area_seleccionada:
        personal = personal.filter(area=area_seleccionada)
    if usuario.es_jefe_area() and sala_seleccionada:
        personal = personal.filter(sala=sala_seleccionada)
    personal = personal.order_by('apellidos', 'nombre')

    programaciones = ProgramacionVacaciones.objects.filter(
        trabajador__in=personal,
        anio=anio,
    ).select_related('trabajador', 'programado_por')
    adelantos = SolicitudVacaciones.objects.filter(
        solicitante__in=personal,
        estado='procesado',
        fecha_inicio__year=anio,
    ).select_related('solicitante')

    context = {
        'usuario': usuario,
        'hoy': hoy,
        'anio': anio,
        'anio_anterior': anio - 1,
        'anio_siguiente': anio + 1,
        'areas': areas,
        'area_id': area_id,
        'area_seleccionada': area_seleccionada,
        'salas': salas,
        'sala_id': sala_id,
        'sala_seleccionada': sala_seleccionada,
        'personal_json': _serialize_personal(personal),
        'programaciones_json': _serialize_periodos(programaciones, adelantos),
        'sin_programar': personal.count() - programaciones.count(),
        'total_pendientes': get_total_pendientes(usuario),
    }
    return render(request, 'vacaciones.html', context)
