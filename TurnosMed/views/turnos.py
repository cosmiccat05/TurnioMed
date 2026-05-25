# views/turnos.py
import json
import calendar
from datetime import date, datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone

from TurnosMed.models import Turno
from TurnosMed.views.utils import DIAS_ES, MESES_ES, get_personal, get_total_pendientes

CODIGOS_VALIDOS = ['D', 'N', 'M', 'T', 'D4', 'N4']


@login_required
def turnos(request):
    usuario = request.user

    if not usuario.es_jefe():
        messages.error(request, 'No tiene permisos para acceder.')
        return redirect('signin')

    if usuario.es_jefe_departamento() and not usuario.departamento:
        messages.error(request, 'Su usuario no tiene un departamento asignado.')
        return redirect('home')

    if usuario.es_jefe_area() and not usuario.area:
        messages.error(request, 'Su usuario no tiene un área asignada.')
        return redirect('home')

    hoy = timezone.localdate()
    anio = int(request.GET.get('anio', hoy.year))
    mes = int(request.GET.get('mes', hoy.month))

    # Filtros de área / sala
    areas = []
    salas = []
    area_id = request.GET.get('area')
    sala_id = request.GET.get('sala')
    area_seleccionada = None
    sala_seleccionada = None

    if usuario.es_jefe_departamento():
        areas = usuario.departamento.areas.filter(activo=True).order_by('nombre')
        if area_id and area_id != 'all':
            area_seleccionada = areas.filter(id=area_id).first()

    elif usuario.es_jefe_area():
        area_seleccionada = usuario.area
        salas = usuario.area.salas.filter(activa=True).order_by('nombre')
        if sala_id and sala_id != 'all':
            sala_seleccionada = salas.filter(id=sala_id).first()

    # Días del mes
    primer_dia = date(anio, mes, 1)
    ultimo_dia = date(anio, mes, calendar.monthrange(anio, mes)[1])

    dias_mes = [
        {
            'fecha': date(anio, mes, d),
            'nombre_dia': DIAS_ES[date(anio, mes, d).weekday()],
            'numero': d,
            'es_fin_semana': date(anio, mes, d).weekday() in [5, 6],
            'es_domingo': date(anio, mes, d).weekday() == 6,
        }
        for d in range(1, ultimo_dia.day + 1)
    ]

    # Navegación de meses
    mes_anterior = mes - 1 or 12
    anio_anterior = anio if mes > 1 else anio - 1
    mes_siguiente = mes + 1 if mes < 12 else 1
    anio_siguiente = anio if mes < 12 else anio + 1

    # Personal filtrado
    personal = get_personal(usuario)

    if usuario.es_jefe_departamento() and area_seleccionada:
        personal = personal.filter(area=area_seleccionada)

    if usuario.es_jefe_area() and sala_seleccionada:
        personal = personal.filter(sala=sala_seleccionada)

    personal = personal.order_by('rol', 'apellidos', 'nombre')

    # Turnos del mes
    turnos_mes = Turno.objects.filter(
        trabajador__in=personal,
        fecha__range=(primer_dia, ultimo_dia)
    ).select_related('trabajador')

    turnos_map = {
        f'{t.trabajador_id}-{t.fecha.isoformat()}': t.codigo or ''
        for t in turnos_mes
    }

    # POST: guardar programación
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            turnos_recibidos = data.get('turnos', [])
            ids_validos = set(personal.values_list('id', flat=True))
            errores = []

            with transaction.atomic():
                for item in turnos_recibidos:
                    trabajador_id = int(item.get('trabajador_id'))
                    fecha_texto = item.get('fecha')
                    codigo = (item.get('codigo') or '').strip().upper()

                    if trabajador_id not in ids_validos:
                        continue

                    fecha_turno = datetime.strptime(fecha_texto, '%Y-%m-%d').date()

                    # Celda vacía → turno libre (borrar si existía)
                    if not codigo:
                        Turno.objects.filter(
                            trabajador_id=trabajador_id,
                            fecha=fecha_turno
                        ).delete()
                        continue

                    if codigo not in CODIGOS_VALIDOS:
                        errores.append(f'Código inválido: {codigo}')
                        continue

                    trabajador = personal.get(id=trabajador_id)

                    # Validar cumpleaños
                    if trabajador.fecha_nacimiento:
                        fn = trabajador.fecha_nacimiento
                        if fecha_turno.month == fn.month and fecha_turno.day == fn.day:
                            errores.append(
                                f'{trabajador.nombre_completo()} cumple años '
                                f'el {fecha_turno.strftime("%d/%m")} — debe ser día libre.'
                            )
                            continue

                    turno, creado = Turno.objects.get_or_create(
                        trabajador_id=trabajador_id,
                        fecha=fecha_turno,
                        defaults={'codigo': ''},
                    )
                    turno.codigo = codigo
                    turno.creado_por = usuario
                    try:
                        turno.save()
                    except ValidationError as exc:
                        if creado:
                            turno.delete()
                        errores.extend(exc.messages)

            return JsonResponse({
                'ok': True,
                'errores': errores,
                'advertencias': [],
                'message': (
                    'Programación guardada.'
                    if not errores
                    else f'Guardado con {len(errores)} error(es).'
                ),
            })

        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=400)

    # Construir filas para el template
    filas = [
        {
            'index': idx,
            'persona': persona,
            'celdas': [
                {
                    'fecha': dia['fecha'],
                    'codigo': turnos_map.get(f'{persona.id}-{dia["fecha"].isoformat()}', ''),
                    'bloqueo': Turno(
                        trabajador=persona,
                        fecha=dia['fecha'],
                        codigo='D',
                    ).motivo_bloqueo(),
                    'es_fin_semana': dia['es_fin_semana'],
                    'es_domingo': dia['es_domingo'],
                }
                for dia in dias_mes
            ],
        }
        for idx, persona in enumerate(personal)
    ]

    context = {
        'usuario': usuario,
        'hoy': hoy,
        'areas': areas,
        'area_id': area_id,
        'area_seleccionada': area_seleccionada,
        'salas': salas,
        'sala_id': sala_id,
        'sala_seleccionada': sala_seleccionada,
        'dias_mes': dias_mes,
        'filas': filas,
        'anio': anio,
        'mes': mes,
        'nombre_mes': MESES_ES[mes],
        'mes_anterior': mes_anterior,
        'anio_anterior': anio_anterior,
        'mes_siguiente': mes_siguiente,
        'anio_siguiente': anio_siguiente,
        'total_pendientes': get_total_pendientes(usuario),
        'codigos_validos': CODIGOS_VALIDOS,
    }
    return render(request, 'turnos.html', context)


@login_required
def importar_excel(request):
    # implementar importación desde Excel
    return redirect('turnos')


@login_required
def exportar_excel(request):
    # implementar exportación a Excel
    return redirect('turnos')
