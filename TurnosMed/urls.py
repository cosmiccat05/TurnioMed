from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('signin/', views.signin, name='signin'),
    path('logout/', views.signout, name='logout'),

    path('home/', views.home, name='home'),
    path('turnos/', views.turnos, name='turnos'),
    path('solicitudes/', views.solicitudes, name='solicitudes'),

    path('solicitudes/<int:id>/detalle/descanso-medico/', views.detalle_descanso_medico, name='detalle_descanso_medico'),
    path('solicitudes/<int:id>/detalle/cambio-turno/', views.detalle_cambio_turno, name='detalle_cambio_turno'),
    path('solicitudes/<int:id>/detalle/vacaciones/', views.detalle_vacaciones, name='detalle_vacaciones'),

    path('solicitudes/<str:tipo>/<int:id>/revisar/',views.revisar_solicitud, name='revisar_solicitud'),

    path('vacaciones/', views.vacaciones, name='vacaciones'),
    path('reportes/', views.reportes, name='reportes'),
]