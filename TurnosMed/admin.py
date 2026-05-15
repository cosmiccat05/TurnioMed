from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (Usuario, Area, Sala, Turno, SolicitudCambioTurno, SolicitudVacaciones, SolicitudDescansoMedico, ProgramacionVacaciones, Notificacion)

# USUARIO
@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('nombre_completo', 'dni', 'email', 'rol', 'get_condicion', 'area', 'is_active')
    list_filter = ('rol', 'condicion', 'tipo_trabajador', 'area', 'is_active')
    search_fields = ('nombre', 'apellidos', 'dni', 'email')
    ordering = ('apellidos', 'nombre')

    # Columna extra para mostrar condición con display bonito
    @admin.display(description='Condición')
    def get_condicion(self, obj):
        return obj.get_condicion_display() if obj.condicion else '—'

    fieldsets = (
        ('Datos personales', {
            'fields': ('nombre', 'apellidos', 'dni', 'email', 'telefono')
        }),
        ('Rol y ubicación', {
            'fields': ('rol', 'tipo_trabajador', 'condicion', 'area', 'sala')
        }),
        ('Acceso al sistema', {
            'fields': ('password', 'is_active', 'is_staff', 'fecha_ingreso')
        }),
        ('Permisos', {
            'classes': ('collapse',),
            'fields': ('is_superuser', 'groups', 'user_permissions')
        }),
    )

    add_fieldsets = (
        ('Datos personales', {
            'classes': ('wide',),
            'fields': ('nombre', 'apellidos', 'dni', 'email', 'telefono')
        }),
        ('Rol y ubicación', {
            'classes': ('wide',),
            'fields': ('rol', 'tipo_trabajador', 'condicion', 'area', 'sala')
        }),
        ('Contraseña', {
            'classes': ('wide',),
            'fields': ('password1', 'password2')
        }),
    )

# ÁREA con SALA como inline
class SalaInline(admin.TabularInline):
    model = Sala
    extra = 1
    fields = ('nombre', 'activa')
    show_change_link = True


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'activo')
    list_filter = ('tipo', 'activo')
    search_fields = ('nombre',)
    inlines = [SalaInline]


@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'area', 'activa')
    list_filter = ('area', 'activa')
    search_fields = ('nombre', 'area__nombre')

# TURNO
@admin.register(Turno)
class TurnoAdmin(admin.ModelAdmin):
    list_display = ('trabajador', 'fecha', 'codigo', 'get_es_libre', 'get_horas', 'creado_por')
    list_filter = ('codigo', 'fecha', 'trabajador__area')
    search_fields = ('trabajador__nombre', 'trabajador__apellidos', 'trabajador__dni')
    date_hierarchy = 'fecha'
    ordering = ('-fecha',)
    readonly_fields = ('creado_en', 'modificado_en')

    @admin.display(description='Libre', boolean=True)
    def get_es_libre(self, obj):
        return obj.es_libre  # es @property en el modelo

    @admin.display(description='Horas')
    def get_horas(self, obj):
        return f"{obj.horas} h"

# SOLICITUDES
@admin.register(SolicitudCambioTurno)
class SolicitudCambioTurnoAdmin(admin.ModelAdmin):
    list_display = ('solicitante', 'companero', 'turno_original', 'turno_destino', 'estado', 'fecha_solicitud')
    list_filter = ('estado',)
    search_fields = ('solicitante__nombre', 'solicitante__apellidos', 'companero__nombre')
    ordering = ('-fecha_solicitud',)
    readonly_fields = ('fecha_solicitud',)

@admin.register(SolicitudVacaciones)
class SolicitudVacacionesAdmin(admin.ModelAdmin):
    list_display = ('solicitante', 'tipo', 'fecha_inicio', 'fecha_fin', 'dias_totales', 'estado')
    list_filter = ('estado', 'tipo')
    search_fields = ('solicitante__nombre', 'solicitante__apellidos')
    ordering = ('-fecha_solicitud',)
    readonly_fields = ('fecha_solicitud',)

@admin.register(SolicitudDescansoMedico)
class SolicitudDescansoMedicoAdmin(admin.ModelAdmin):
    list_display = ('solicitante', 'fecha_inicio', 'fecha_fin', 'justificacion', 'estado', 'en_curso')
    list_filter  = ('estado',)
    search_fields = ('solicitante__nombre', 'solicitante__apellidos')
    ordering = ('-fecha_solicitud',)
    readonly_fields = ('fecha_solicitud',)

# PROGRAMACIÓN DE VACACIONES
@admin.register(ProgramacionVacaciones)
class ProgramacionVacacionesAdmin(admin.ModelAdmin):
    list_display = ('trabajador', 'anio', 'fecha_inicio', 'fecha_fin', 'dias_totales', 'estado')
    list_filter = ('estado', 'anio')
    search_fields = ('trabajador__nombre', 'trabajador__apellidos')
    ordering = ('-anio', 'trabajador__apellidos')

# NOTIFICACIONES
@admin.register(Notificacion)
class NotificacionAdmin(admin.ModelAdmin):
    list_display = ('destinatario', 'tipo', 'titulo', 'leido', 'creada_en')
    list_filter = ('tipo', 'leido')
    search_fields = ('destinatario__nombre', 'titulo')
    ordering = ('-creada_en',)