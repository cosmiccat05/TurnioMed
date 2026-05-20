import json
import calendar
from datetime import date, datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone

from TurnosMed.models import (
    Area, Usuario, Turno,
    SolicitudCambioTurno, SolicitudVacaciones, SolicitudDescansoMedico,
)

MESES_ES = [
    '', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
]

DIAS_ES = {0:'Lun', 1:'Mar', 2:'Mié', 3:'Jue', 4:'Vie', 5:'Sáb', 6:'Dom'}

# Códigos válidos
CODIGOS_VALIDOS  = ['D', 'N', 'M', 'T', 'D4', 'N4']


def codigo_para_pantalla(codigo_bd):
    """Convierte D4→D y N4→N para mostrar en la tabla."""
    if codigo_bd == 'D4':
        return 'D4'  # ahora los mostramos tal cual
    if codigo_bd == 'N4':
        return 'N4'
    return codigo_bd or ''


def _get_personal(usuario):
    """Devuelve el queryset de personal filtrado por tipo del jefe."""
    qs = Usuario.objects.filter(
        area=usuario.area,
        rol='asistencial',
        is_active=True
    )
    if usuario.tipo_trabajador == 'medico':
        return qs.filter(tipo_trabajador='medico')
    if usuario.tipo_trabajador in ['licenciada_enfermeria', 'tecnico_enfermeria']:
        return qs.filter(
            tipo_trabajador__in=['licenciada_enfermeria', 'tecnico_enfermeria']
        )
    return qs


def _total_pendientes(area):
    """Cuenta solicitudes pendientes del área para el badge del sidebar."""
    return (
        SolicitudCambioTurno.objects.filter(
            solicitante__area=area, estado='pendiente').count()
        + SolicitudVacaciones.objects.filter(
            solicitante__area=area, estado='pendiente').count()
        + SolicitudDescansoMedico.objects.filter(
            solicitante__area=area, estado='pendiente').count()
    )


@login_required
def turnos(request):
    usuario = request.user

    if not usuario.es_jefe():
        messages.error(request, 'No tiene permisos para acceder.')
        return redirect('signin')

    if not usuario.area:
        messages.error(request, 'Su usuario no tiene un área asignada.')
        return redirect('home')

    hoy  = timezone.now().date()
    anio = int(request.GET.get('anio', hoy.year))
    mes  = int(request.GET.get('mes',  hoy.month))

    area_seleccionada = usuario.area
    salas             = area_seleccionada.salas.filter(activa=True).order_by('nombre')

    sala_id          = request.GET.get('sala')
    sala_seleccionada = None
    if sala_id and sala_id != 'all':
        sala_seleccionada = salas.filter(id=sala_id).first()

    # Días del mes
    primer_dia = date(anio, mes, 1)
    ultimo_dia = date(anio, mes, calendar.monthrange(anio, mes)[1])

    dias_mes = [
        {
            'fecha':         date(anio, mes, d),
            'nombre_dia':    DIAS_ES[date(anio, mes, d).weekday()],
            'numero':        d,
            'es_fin_semana': date(anio, mes, d).weekday() in [5, 6],
            'es_domingo':    date(anio, mes, d).weekday() == 6,
        }
        for d in range(1, ultimo_dia.day + 1)
    ]

    # Navegación de meses
    mes_anterior  = mes - 1 or 12
    anio_anterior = anio if mes > 1 else anio - 1
    mes_siguiente = mes + 1 if mes < 12 else 1
    anio_siguiente = anio if mes < 12 else anio + 1

    # Personal filtrado
    personal = _get_personal(usuario).order_by('apellidos', 'nombre')
    if sala_seleccionada:
        personal = personal.filter(sala=sala_seleccionada)

    # Turnos del mes
    turnos_mes = Turno.objects.filter(
        trabajador__in=personal,
        fecha__range=(primer_dia, ultimo_dia)
    ).select_related('trabajador')

    turnos_map = {
        f'{t.trabajador_id}-{t.fecha.isoformat()}': codigo_para_pantalla(t.codigo)
        for t in turnos_mes
    }

    # Manejo del POST (guardar programación)
    if request.method == 'POST':
        try:
            data             = json.loads(request.body)
            turnos_recibidos = data.get('turnos', [])
            ids_validos      = set(personal.values_list('id', flat=True))

            errores = []

            with transaction.atomic():
                for item in turnos_recibidos:
                    trabajador_id   = int(item.get('trabajador_id'))
                    fecha_texto     = item.get('fecha')
                    codigo_pantalla = (item.get('codigo') or '').strip().upper()

                    if trabajador_id not in ids_validos:
                        continue

                    # Celda vacía = turno libre
                    if codigo_pantalla == '':
                        Turno.objects.filter(
                            trabajador_id=trabajador_id,
                            fecha=datetime.strptime(fecha_texto, '%Y-%m-%d').date()
                        ).delete()
                        continue

                    # Código no reconocido
                    if codigo_pantalla not in CODIGOS_VALIDOS:
                        errores.append(f'Código inválido: {codigo_pantalla}')
                        continue

                    trabajador  = personal.get(id=trabajador_id)
                    fecha_turno = datetime.strptime(fecha_texto, '%Y-%m-%d').date()

                    if codigo_pantalla not in CODIGOS_VALIDOS:
                        errores.append(f'Código inválido: {codigo_pantalla}')
                        continue

                    # Validar cumpleaños
                    if trabajador.fecha_nacimiento:
                        fn = trabajador.fecha_nacimiento
                        if fecha_turno.month == fn.month and fecha_turno.day == fn.day:
                            errores.append(
                                f'{trabajador.nombre_completo()} cumple años '
                                f'el {fecha_turno.strftime("%d/%m")} — debe ser día libre.'
                            )
                            continue

                    # Validar que terceros tengan al menos un M o T en el mes
                    # (advertencia, no bloqueo — se avisa al final)

                    Turno.objects.update_or_create(
                        trabajador_id=trabajador_id,
                        fecha=fecha_turno,
                        defaults={
                            'codigo':     codigo_pantalla,
                            'creado_por': usuario,
                        }
                    )

            # Verificar terceros sin M/T después de guardar
            advertencias = []
            for p in personal.filter(condicion='tercero'):
                tiene_medio = Turno.objects.filter(
                    trabajador=p,
                    fecha__year=anio,
                    fecha__month=mes,
                    codigo__in=['M', 'T']
                ).exists()
                if not tiene_medio:
                    advertencias.append(
                        f'{p.nombre_completo()} (tercero) no tiene turno M o T en el mes.'
                    )

            return JsonResponse({
                'ok':          True,
                'errores':     errores,
                'advertencias': advertencias,
                'message':     'Programación guardada.' if not errores else
                               f'Guardado con {len(errores)} error(es).'
            })

        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=400)

    # Construir filas para el template
    filas = []
    for idx, persona in enumerate(personal):
        celdas = []
        for dia in dias_mes:
            clave  = f'{persona.id}-{dia["fecha"].isoformat()}'
            codigo = turnos_map.get(clave, '')
            celdas.append({
                'fecha':         dia['fecha'],
                'codigo':        codigo,
                'es_fin_semana': dia['es_fin_semana'],
                'es_domingo':    dia['es_domingo'],
            })
        filas.append({'index': idx, 'persona': persona, 'celdas': celdas})

    context = {
        'usuario':          usuario,
        'hoy':              hoy,
        'area_seleccionada': area_seleccionada,
        'salas':            salas,
        'sala_seleccionada': sala_seleccionada,
        'dias_mes':         dias_mes,
        'filas':            filas,
        'anio':             anio,
        'mes':              mes,
        'nombre_mes':       MESES_ES[mes],
        'mes_anterior':     mes_anterior,
        'anio_anterior':    anio_anterior,
        'mes_siguiente':    mes_siguiente,
        'anio_siguiente':   anio_siguiente,
        'total_pendientes': _total_pendientes(area_seleccionada),
        'codigos_validos': CODIGOS_VALIDOS,
    }
    return render(request, 'turnos.html', context)


@login_required
def importar_excel(request):
    return redirect('turnos')


@login_required
def exportar_excel(request):
    return redirect('turnos')