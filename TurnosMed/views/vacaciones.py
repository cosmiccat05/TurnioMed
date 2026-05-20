from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def vacaciones(request):
    return render(request, 'vacaciones.html')