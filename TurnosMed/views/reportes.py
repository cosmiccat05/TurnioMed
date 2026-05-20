from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def reportes(request):
    return render(request, 'reportes.html')