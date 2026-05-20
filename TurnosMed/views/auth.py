from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from TurnosMed.forms import LoginForm


def landing(request):
    return render(request, 'landing.html')

def signin(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('/admin/')
        elif request.user.es_jefe():
            return redirect('home')
        else:
            logout(request)
            messages.error(
                request,
                'No tiene permisos para acceder al sistema.'
            )
            return redirect('signin')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if user.is_staff:
                return redirect('/admin/')
            elif user.es_jefe():
                return redirect('home')
            else:
                logout(request)
                messages.error(
                    request,
                    'No tiene permisos para acceder al sistema.'
                )
                return redirect('signin')

    else:
        form = LoginForm()

    return render(request, 'login.html', {
        'form': form
    })

def signout(request):
    logout(request)
    return redirect('signin')