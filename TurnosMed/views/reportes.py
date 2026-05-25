from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from TurnosMed.models import (
    SolicitudCambioTurno,
    SolicitudDescansoMedico,
    SolicitudVacaciones,
)
from TurnosMed.views.utils import (
    MESES_ES,
    get_filtro_solicitudes,
    get_total_pendientes,
)

CATEGORIAS = {
    'cambios': ('Cambios de turno', SolicitudCambioTurno),
    'vacaciones': ('Vacaciones', SolicitudVacaciones),
    'descansos': ('Descansos medicos', SolicitudDescansoMedico),
}


def _esc_pdf(text):
    return str(text).replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def _pdf_response(lines, filename):
    chunks = [lines[index:index + 38] for index in range(0, len(lines), 38)] or [[]]
    page_ids = [3 + index * 2 for index in range(len(chunks))]
    font_id = 3 + len(chunks) * 2
    objects = [
        '<< /Type /Catalog /Pages 2 0 R >>',
        f'<< /Type /Pages /Kids [{" ".join(f"{item} 0 R" for item in page_ids)}] /Count {len(chunks)} >>',
    ]
    for index, chunk in enumerate(chunks):
        page_id = page_ids[index]
        content_id = page_id + 1
        objects.append(
            f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] '
            f'/Contents {content_id} 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> >>'
        )
        text_ops = ['BT /F1 10 Tf 45 752 Td']
        for line_index, line in enumerate(chunk):
            prefix = '' if line_index == 0 else '0 -18 Td '
            text_ops.append(f'{prefix}({_esc_pdf(line)}) Tj')
        text_ops.append('ET')
        stream = '\n'.join(text_ops)
        objects.append(f'<< /Length {len(stream.encode("latin-1", "replace"))} >>\nstream\n{stream}\nendstream')
    objects.append('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')

    data = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(data))
        data.extend(f'{number} 0 obj\n'.encode())
        data.extend(obj.encode('latin-1', 'replace'))
        data.extend(b'\nendobj\n')
    xref = len(data)
    data.extend(f'xref\n0 {len(objects) + 1}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:
        data.extend(f'{offset:010d} 00000 n \n'.encode())
    data.extend(
        f'trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'.encode()
    )
    response = HttpResponse(bytes(data), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _filtrar_items(usuario, categoria, anio, mes, area_id, sala_id):
    _, modelo = CATEGORIAS[categoria]
    filtros = get_filtro_solicitudes(usuario)
    relaciones = ['solicitante']
    if categoria == 'cambios':
        relaciones.extend(['turno_original', 'turno_destino', 'companero'])
    queryset = modelo.objects.filter(**filtros, fecha_solicitud__year=anio).select_related(
        *relaciones
    )
    if mes:
        queryset = queryset.filter(fecha_solicitud__month=mes)
    if usuario.es_jefe_departamento() and area_id and area_id != 'all':
        queryset = queryset.filter(solicitante__area_id=area_id)
    if usuario.es_jefe_area() and sala_id and sala_id != 'all':
        queryset = queryset.filter(solicitante__sala_id=sala_id)
    return queryset.order_by('-fecha_solicitud')


def _lineas_pdf(titulo, periodo, items, categoria):
    lines = ['TURNIOMED - REPORTE', titulo, periodo, '', 'Registros:']
    for item in items:
        nombre = item.solicitante.nombre_completo()
        estado = item.get_estado_display()
        if categoria == 'cambios':
            detalle = (
                f'{item.turno_original.fecha:%d/%m/%Y} {item.turno_original.codigo} / '
                f'{item.turno_destino.fecha:%d/%m/%Y} {item.turno_destino.codigo}'
            )
        elif categoria == 'vacaciones':
            detalle = f'{item.fecha_inicio:%d/%m/%Y} a {item.fecha_fin:%d/%m/%Y}'
        else:
            final = item.fecha_fin.strftime('%d/%m/%Y') if item.fecha_fin else 'en curso'
            detalle = f'{item.fecha_inicio:%d/%m/%Y} a {final}'
        lines.append(f'- {nombre} | {estado} | {detalle}')
    if not items:
        lines.append('Sin registros en el periodo seleccionado.')
    lines.extend(['', f'Emitido: {timezone.localdate():%d/%m/%Y}'])
    return lines


@login_required
def reportes(request):
    usuario = request.user
    if not usuario.es_jefe():
        messages.error(request, 'No tiene permisos para acceder.')
        return redirect('signin')

    hoy = timezone.localdate()
    categoria = request.GET.get('categoria', 'cambios')
    if categoria not in CATEGORIAS:
        categoria = 'cambios'
    anio = int(request.GET.get('anio', hoy.year))
    mensual = request.GET.get('periodo', 'mensual') != 'anual'
    mes = int(request.GET.get('mes', hoy.month)) if mensual else None
    area_id = request.GET.get('area', 'all')
    sala_id = request.GET.get('sala', 'all')
    items = list(_filtrar_items(usuario, categoria, anio, mes, area_id, sala_id))

    periodo_texto = (
        f'{MESES_ES[mes]} {anio}' if mes else f'Anio {anio}'
    )
    titulo = CATEGORIAS[categoria][0]
    if request.GET.get('export') == 'pdf':
        lines = _lineas_pdf(titulo, periodo_texto, items, categoria)
        return _pdf_response(lines, f'reporte_{categoria}_{anio}.pdf')

    estados_aprobados = {'procesado'}
    aprobados = sum(item.estado in estados_aprobados for item in items)
    pendientes = sum(item.estado in {'pendiente', 'aprobado_jefe'} for item in items)
    rechazados = sum(item.estado in {'rechazado_jefe', 'rechazado_admin'} for item in items)

    context = {
        'usuario': usuario,
        'hoy': hoy,
        'categoria': categoria,
        'titulo': titulo,
        'anio': anio,
        'mes': mes or hoy.month,
        'mensual': mensual,
        'periodo_texto': periodo_texto,
        'items': items,
        'total': len(items),
        'aprobados': aprobados,
        'pendientes': pendientes,
        'rechazados': rechazados,
        'areas': (
            usuario.departamento.areas.filter(activo=True)
            if usuario.es_jefe_departamento() and usuario.departamento else []
        ),
        'salas': (
            usuario.area.salas.filter(activa=True)
            if usuario.es_jefe_area() and usuario.area else []
        ),
        'area_id': area_id,
        'sala_id': sala_id,
        'meses': [(numero, MESES_ES[numero]) for numero in range(1, 13)],
        'total_pendientes': get_total_pendientes(usuario),
    }
    return render(request, 'reportes.html', context)
