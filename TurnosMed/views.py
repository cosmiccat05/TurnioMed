from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm

def signin(request):
    """
    Maneja el inicio de sesión único para el sistema.
    Redirige al Admin al panel de gestión y al Jefe al Home.
    """
    if request.method == 'GET':
        # Si ya está logueado, lo sacamos del login según su rol
        if request.user.is_authenticated:
            return redirect('/admin/') if request.user.is_staff else redirect('home')

        return render(request, 'login.html', {
            'form': AuthenticationForm()
        })
    else:
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Validación de Rol para redirección
            if user.is_staff:
                return redirect('/admin/')  # Panel de gestión (CRUD)
            else:
                return redirect('home')  # Interfaz de Jefe de Área
        else:
            return render(request, 'login.html', {
                'form': AuthenticationForm(),
                'error': 'Usuario o contraseña incorrectos'
            })

def signout(request):
    """Cierra la sesión y manda al usuario al login"""
    logout(request)
    return redirect('signin')

@login_required
def home(request):
    return render(request, 'home.html')


@login_required
def turnos(request):
    return render(request, 'turnos.html')


@login_required
def vacaciones(request):
    return render(request, 'vacaciones.html')


@login_required
def solicitudes(request):
    return render(request, 'solicitudes.html')


@login_required
def reportes(request):
    return render(request, 'reportes.html')
