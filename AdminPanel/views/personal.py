from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from AdminPanel.forms import UsuarioForm
from AdminPanel.views.helpers import total_pendientes_admin
from TurnosMed.models import Usuario, Area, Sala


def _solo_admin(usuario):
    return usuario.es_admin()

@login_required
def lista_personal(request):
    usuario = request.user
    if not _solo_admin(usuario):
        return redirect('home')

    qs = (
        Usuario.objects.filter(is_superuser=False)
        .select_related('departamento', 'area', 'sala')
        .order_by('apellidos', 'nombre')
    )

    # Filtros GET
    buscar = request.GET.get('buscar', '').strip()
    tipo   = request.GET.get('tipo', '').strip()
    area   = request.GET.get('area', '').strip()

    if buscar:
        qs = qs.filter(
            Q(nombre__icontains=buscar)
            | Q(apellidos__icontains=buscar)
            | Q(dni__icontains=buscar)
            | Q(email__icontains=buscar)
        )

    if tipo:
        qs = qs.filter(tipo_trabajador=tipo)

    if area:
        qs = qs.filter(area_id=area)

    # Paginación
    paginator = Paginator(qs, 20)
    pagina_num = request.GET.get('pagina', 1)
    personal = paginator.get_page(pagina_num)

    # Preservar filtros en los links de paginación
    query_params = '&'.join(
        f'{k}={v}' for k, v in request.GET.items() if k != 'pagina'
    )

    context = {
        'usuario': usuario,
        'hoy': timezone.localdate(),
        'personal': personal,
        'query_params': query_params,
        'tipos_trabajador': Usuario.TIPO_TRABAJADOR,
        'areas': Area.objects.filter(activo=True).order_by('nombre'),
        'buscar': buscar,
        'tipo': tipo,
        'area': area,
        'total_pendientes': total_pendientes_admin(),
    }
    return render(request, 'panel/lista_personal.html', context)

@login_required
def crear_personal(request):
    usuario = request.user
    if not _solo_admin(usuario):
        return redirect('home')

    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            trabajador = form.save(commit=False)
            # Asignar contraseña temporal = DNI
            trabajador.set_password(form.cleaned_data['dni'])
            trabajador.is_active = True
            trabajador.save()
            messages.success(request, f'Trabajador {trabajador.nombre_completo()} agregado correctamente.')
            return redirect('admin_personal')
    else:
        form = UsuarioForm()

    context = {
        'usuario': usuario,
        'hoy': timezone.localdate(),
        'form': form,
        'es_edicion': False,
        'total_pendientes': total_pendientes_admin(),
    }
    return render(request, 'panel/form_personal.html', context)

@login_required
def editar_personal(request, id):
    usuario  = request.user
    if not _solo_admin(usuario):
        return redirect('home')

    trabajador = get_object_or_404(Usuario, id=id, is_superuser=False)

    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=trabajador)
        if form.is_valid():
            form.save()
            messages.success(request, f'Datos de {trabajador.nombre_completo()} actualizados.')
            return redirect('admin_personal')
    else:
        form = UsuarioForm(instance=trabajador)

    context = {
        'usuario': usuario,
        'hoy': timezone.localdate(),
        'form': form,
        'trabajador': trabajador,
        'es_edicion': True,
        'total_pendientes': total_pendientes_admin(),
    }
    return render(request, 'panel/form_personal.html', context)

@login_required
def eliminar_personal(request, id):
    usuario = request.user
    if not _solo_admin(usuario):
        return redirect('home')

    trabajador = get_object_or_404(Usuario, id=id, is_superuser=False)

    if request.method == 'POST':
        if trabajador.id == usuario.id:
            messages.error(request, 'No puede desactivar su propia cuenta.')
            return redirect('admin_personal')
        nombre = trabajador.nombre_completo()
        trabajador.is_active = False
        trabajador.save()
        messages.success(request, f'El trabajador {nombre} fue desactivado.')
        return redirect('admin_personal')

    messages.warning(request, 'Utilice la accion de desactivar desde la lista de personal.')
    return redirect('admin_personal')

# APIS
# API: cargar áreas por departamento (para el select dinámico del form)
@login_required
def api_areas_por_departamento(request):
    if not _solo_admin(request.user):
        return JsonResponse({'areas': []}, status=403)
    dep_id = request.GET.get('departamento_id')
    if not dep_id:
        return JsonResponse({'areas': []})
    areas = Area.objects.filter(
        departamento_id=dep_id,
        activo=True,
    ).order_by('nombre').values('id', 'nombre')
    return JsonResponse({'areas': list(areas)})

# API: cargar salas por área (para el select dinámico del form)
@login_required
def api_salas_por_area(request):
    if not _solo_admin(request.user):
        return JsonResponse({'salas': []}, status=403)
    area_id = request.GET.get('area_id')
    if not area_id:
        return JsonResponse({'salas': []})
    salas = Sala.objects.filter(
        area_id=area_id,
        activa=True,
    ).order_by('nombre').values('id', 'nombre')
    return JsonResponse({'salas': list(salas)})
