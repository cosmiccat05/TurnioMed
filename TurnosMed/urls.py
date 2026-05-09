from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('signin/', views.signin, name='signin'),
    path('logout/', views.signout, name='logout'),

    path('home/', views.home, name='home'),
    path('turnos/', views.turnos, name='turnos'),
    path('solicitudes/', views.solicitudes, name='solicitudes'),
    path('vacaciones/', views.vacaciones, name='vacaciones'),
    path('reportes/', views.reportes, name='reportes'),
]