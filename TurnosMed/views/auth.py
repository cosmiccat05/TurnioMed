# views/auth.py
from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render

from TurnosMed.forms import LoginForm


def _redirigir_segun_rol(request, user):
    """Redirige al usuario según su rol, o lo desconecta si no tiene acceso."""
    if user.is_superuser:
        return redirect('/admin/')
    if user.es_admin():
        return redirect('admin_home')
    if user.es_jefe():
        return redirect('home')
    logout(request)
    messages.error(request, 'No tiene permisos para acceder al sistema.')
    return redirect('signin')


def landing(request):
    return render(request, 'landing.html')


def signin(request):
    if request.user.is_authenticated:
        return _redirigir_segun_rol(request, request.user)

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return _redirigir_segun_rol(request, user)
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})


def signout(request):
    logout(request)
    return redirect('signin')
