from django.urls import path
from AdminPanel.views import home, solicitudes, vacaciones, personal

urlpatterns = [
    path('', home.home, name='admin_home'),

    path('personal/', personal.lista_personal, name='admin_personal'),
    path('personal/agregar/', personal.crear_personal, name='admin_personal_agregar'),
    path('personal/<int:id>/editar/', personal.editar_personal, name='admin_personal_editar'),
    path('personal/<int:id>/eliminar/', personal.eliminar_personal, name='admin_personal_eliminar'),

    path('api/areas/', personal.api_areas_por_departamento, name='admin_api_areas'),
    path('api/salas/', personal.api_salas_por_area, name='admin_api_salas'),

    path('solicitudes/',  solicitudes.solicitudes, name='admin_solicitudes'),
    path('solicitudes/<str:tipo>/<int:id>/', solicitudes.detalle_solicitud, name='admin_detalle_solicitud'),
    path('solicitudes/<str:tipo>/<int:id>/procesar/', solicitudes.procesar_solicitud, name='admin_procesar_solicitud'),

    path('vacaciones/', vacaciones.vacaciones, name='admin_vacaciones'),
    path('vacaciones/programar/', vacaciones.programar_vacaciones, name='admin_vacaciones_programar'),
    path('vacaciones/<int:id>/editar/', vacaciones.editar_vacaciones, name='admin_vacaciones_editar'),
    path('vacaciones/eliminar/<int:trabajador_id>/<int:anio>/', vacaciones.eliminar_vacaciones, name='admin_eliminar_vacaciones'),
]
