from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from AdminPanel.forms import ProgramacionVacacionesForm
from AdminPanel.views.helpers import total_pendientes_admin
from TurnosMed.models import Area, ProgramacionVacaciones


@login_required
def vacaciones(request):
    if not request.user.es_admin():
        return redirect('home')
    programaciones = ProgramacionVacaciones.objects.select_related(
        'trabajador', 'trabajador__area', 'trabajador__departamento', 'programado_por'
    ).order_by('-anio', 'fecha_inicio', 'trabajador__apellidos')
    buscar = request.GET.get('buscar', '').strip()
    area = request.GET.get('area', '').strip()
    anio = request.GET.get('anio', '').strip()
    if buscar:
        programaciones = programaciones.filter(
            Q(trabajador__nombre__icontains=buscar)
            | Q(trabajador__apellidos__icontains=buscar)
            | Q(trabajador__dni__icontains=buscar)
        )
    if area:
        programaciones = programaciones.filter(trabajador__area_id=area)
    if anio:
        programaciones = programaciones.filter(anio=anio)
    return render(request, 'panel/vacaciones.html', {
        'hoy': timezone.localdate(),
        'programaciones': programaciones,
        'areas': Area.objects.filter(activo=True).order_by('nombre'),
        'buscar': buscar,
        'area': area,
        'anio': anio,
        'total_pendientes': total_pendientes_admin(),
    })


def _guardar_programacion(request, instance=None):
    form = ProgramacionVacacionesForm(request.POST or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        programacion = form.save(commit=False)
        programacion.programado_por = request.user
        programacion.estado = 'modificado' if instance else 'programado'
        programacion.save()
        accion = 'actualizada' if instance else 'registrada'
        messages.success(request, f'Programacion de vacaciones {accion} correctamente.')
        return form, redirect('admin_vacaciones')
    return form, None


@login_required
def programar_vacaciones(request):
    if not request.user.es_admin():
        return redirect('home')
    form, response = _guardar_programacion(request)
    if response:
        return response
    return render(request, 'panel/form_vacaciones.html', {
        'hoy': timezone.localdate(),
        'form': form,
        'es_edicion': False,
        'total_pendientes': total_pendientes_admin(),
    })


@login_required
def editar_vacaciones(request, id):
    if not request.user.es_admin():
        return redirect('home')
    programacion = get_object_or_404(ProgramacionVacaciones, id=id)
    form, response = _guardar_programacion(request, instance=programacion)
    if response:
        return response
    return render(request, 'panel/form_vacaciones.html', {
        'hoy': timezone.localdate(),
        'form': form,
        'programacion': programacion,
        'es_edicion': True,
        'total_pendientes': total_pendientes_admin(),
    })


@login_required
def eliminar_vacaciones(request, trabajador_id, anio):
    if not request.user.es_admin():
        return JsonResponse({'ok': False, 'error': 'Sin permisos.'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'Metodo no permitido.'}, status=405)
    eliminadas, _ = ProgramacionVacaciones.objects.filter(
        trabajador_id=trabajador_id,
        anio=anio,
    ).delete()
    if not eliminadas:
        return JsonResponse({'ok': False, 'error': 'Programacion no encontrada.'}, status=404)
    messages.success(request, 'Programacion eliminada.')
    return redirect('admin_vacaciones')
