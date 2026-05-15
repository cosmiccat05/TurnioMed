from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models

# MANAGER PERSONALIZADO
class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El email es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('rol', 'admin')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

# USUARIO
class Usuario(AbstractBaseUser, PermissionsMixin):
    ROL = [
        ('admin', 'Administrador'),
        ('jefe_area', 'Jefe de área'),
        ('asistencial', 'Personal asistencial'),
    ]
    TIPO_TRABAJADOR = [
        ('licenciada_enfermeria', 'Licenciada de Enfermería'),
        ('tecnico_efermeria', 'Técnico de Efermería'),
        ('medico', 'Medico'),
    ]
    CONDICION = [
        ('tercero', 'Tercero'),
        ('nombrado', 'Nombrado'),
    ]
    HORAS_POR_CONDICION = {
        'tercero': 12.0,
        'nombrado': 12.5,
    }

    nombre = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    telefono = models.CharField(max_length=9, blank=True)
    dni = models.CharField(max_length=8, unique=True)
    email = models.EmailField(unique=True)
    rol  = models.CharField(max_length=20, choices=ROL)
    cargo = models.CharField(max_length=100, blank=True)
    tipo_trabajador = models.CharField(max_length=30, choices=TIPO_TRABAJADOR, blank=True)
    condicion = models.CharField(max_length=10, choices=CONDICION, blank=True)
    area = models.ForeignKey('Area', on_delete=models.SET_NULL, null=True, blank=True, related_name='personal')
    sala = models.ForeignKey('Sala', on_delete=models.SET_NULL, null=True, blank=True, related_name='personal')

    # Campos requeridos por AbstractBaseUser y PermissionsMixin
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # acceso al admin de Django

    fecha_ingreso = models.DateField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'apellidos', 'dni']

    objects = UsuarioManager()

    @property
    def horas_turno(self):
        return self.HORAS_POR_CONDICION.get(self.condicion, 12.0)

    @property
    def requiere_medio_turno(self):
        return self.condicion == 'tercero'

    def nombre_completo(self):
        return f"{self.nombre} {self.apellidos}"

    def es_admin(self): return self.rol == 'admin'
    def es_jefe(self): return self.rol == 'jefe_area'
    def es_asistencial(self): return self.rol == 'asistencial'

    def cargo_display(self):
        if self.rol == 'admin':
            return 'Administrador'
        partes = []
        if self.cargo:
            partes.append(self.cargo)  # "Ej: Lic. de Enfermería"
        if self.rol == 'jefe_area' and self.area:
            partes.append(f"Jefe de {self.area.nombre}")  # "Ej: Jefe de Emergencia"
        elif self.tipo_trabajador:
            partes.append(self.get_tipo_trabajador_display())
        return ' · '.join(partes)

    def __str__(self):
        return f"{self.nombre_completo()} ({self.get_rol_display()})"

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

# ÁREA
class Area(models.Model):
    TIPO = [
        ('enfermeria', 'Enfermería'),
        ('medicina',   'Medicina'),
    ]
    nombre = models.CharField(max_length=100)  # Emergencia, Sala de Operaciones
    tipo = models.CharField(max_length=20, choices=TIPO)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Área'
        verbose_name_plural = 'Áreas'
        ordering = ['nombre']

# SALA
class Sala(models.Model):
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='salas')
    nombre = models.CharField(max_length=50)
    activa = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.area.nombre} - {self.nombre}"

    class Meta:
        verbose_name = 'Sala'
        verbose_name_plural = 'Salas'
        unique_together = ('area', 'nombre')
        ordering = ['area', 'nombre']

# TURNO
class Turno(models.Model):
    CODIGOS = [
        ('D4', 'Día completo'),
        ('D', 'Día (Terceros)'),
        ('T', 'Tarde'),
        ('M', 'Medio día'),
        ('N4', 'Noche completa'),
        ('N', 'Noche (Terceros)'),
    ]

    DATOS_TURNOS = {
        'D4': {'nombre': 'Día completo', 'hora_inicio': '07:00', 'hora_fin': '19:30', 'horas': Decimal('12.5')},
        'D': {'nombre': 'Día (Terceros)', 'hora_inicio': '07:00', 'hora_fin': '19:00', 'horas': Decimal('12')},
        'T': {'nombre': 'Tarde', 'hora_inicio': '13:00', 'hora_fin': '19:00', 'horas': Decimal('6')},
        'M': {'nombre': 'Medio día', 'hora_inicio': '07:00', 'hora_fin': '13:00', 'horas': Decimal('6')},
        'N4': {'nombre': 'Noche completa', 'hora_inicio': '19:00', 'hora_fin': '07:30', 'horas': Decimal('12.5')},
        'N': {'nombre': 'Noche (Terceros)', 'hora_inicio': '19:00', 'hora_fin': '07:00', 'horas': Decimal('12')},
    }

    trabajador = models.ForeignKey(
        'Usuario',
        on_delete=models.CASCADE,
        related_name='turnos'
    )

    creado_por = models.ForeignKey(
        'Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='turnos_creados'
    )

    fecha = models.DateField()

    codigo = models.CharField(
        max_length=2,
        choices=CODIGOS,
        blank=True
    )

    observaciones = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    modificado_en = models.DateTimeField(auto_now=True)

    @property
    def es_libre(self):
        return not self.codigo

    @property
    def nombre(self):
        if self.codigo:
            return self.DATOS_TURNOS[self.codigo]['nombre']
        return 'Libre'

    @property
    def hora_inicio(self):
        if self.codigo:
            return self.DATOS_TURNOS[self.codigo]['hora_inicio']
        return None

    @property
    def hora_fin(self):
        if self.codigo:
            return self.DATOS_TURNOS[self.codigo]['hora_fin']
        return None

    @property
    def horas(self):
        if self.codigo:
            return self.DATOS_TURNOS[self.codigo]['horas']
        return Decimal('0')

    def clean(self):
        if self.trabajador.rol == 'admin':
            raise ValidationError('El administrador no recibe programación de turnos.')
        if self.codigo:
            if self.trabajador.condicion == 'tercero' and self.codigo not in ['D', 'N', 'M', 'T']:
                raise ValidationError('Los terceros solo pueden tener turnos D, N, M o T.')
            if self.trabajador.condicion == 'nombrado' and self.codigo not in ['D4', 'N4', 'T', 'M']:
                raise ValidationError('Los nombrados solo pueden tener turnos D4, N4, T o M.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        tipo = self.codigo if self.codigo else 'Libre'
        return f"{self.trabajador.nombre_completo()} – {self.fecha} – {tipo}"

    class Meta:
        verbose_name = 'Turno'
        verbose_name_plural = 'Turnos'
        ordering = ['fecha', 'trabajador']
        unique_together = ('trabajador', 'fecha')

# SOLICITUD (Base, de aqui parten los tipos de solicitud)
class Solicitud(models.Model):
    ESTADO = [
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
    ]

    solicitante = models.ForeignKey(
        Usuario, on_delete=models.CASCADE,
        related_name='%(class)s_solicitudes'
    )
    estado          = models.CharField(max_length=20, choices=ESTADO, default='pendiente')
    motivo          = models.TextField()
    comentario_jefe = models.TextField(blank=True)
    revisado_por    = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='%(class)s_revisadas'
    )
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_revision  = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True
        ordering = ['-fecha_solicitud']

#SOLICITUD TIPO: CAMBIO DE TURNO
class SolicitudCambioTurno(Solicitud):
    turno_original = models.ForeignKey(
        Turno, on_delete=models.CASCADE,
        related_name='solicitudes_cambio_origen'
    )
    turno_destino = models.ForeignKey(
        Turno, on_delete=models.CASCADE,
        related_name='solicitudes_cambio_destino'
    )
    companero = models.ForeignKey(
        Usuario, on_delete=models.CASCADE,
        related_name='companero_cambio'
    )

    def __str__(self):
        return f"Cambio: {self.solicitante} - {self.companero} ({self.estado})"

    class Meta:
        verbose_name = 'Solicitud de cambio de turno'
        verbose_name_plural = 'Solicitudes de cambio de turno'

#SOLICITUD TIPO: VACACIONES
class SolicitudVacaciones(Solicitud):
    TIPO = [
        ('ordinaria', 'Ordinarias'),
        ('adelanto', 'Adelanto'),
        ('cambio', 'Cambio de fecha'),
    ]

    tipo = models.CharField(max_length=15, choices=TIPO, default='ordinaria')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()

    @property
    def dias_totales(self):
        # Se calcula solo, no puede desincronizarse con las fechas
        return (self.fecha_fin - self.fecha_inicio).days + 1

    def __str__(self):
        return f"Vacaciones: {self.solicitante} ({self.fecha_inicio} - {self.fecha_fin})"

    class Meta:
        verbose_name = 'Solicitud de vacaciones'
        verbose_name_plural = 'Solicitudes de vacaciones'

#SOLICITUD TIPO: DESCANSO MÉDICO
class SolicitudDescansoMedico(Solicitud):
    fecha_inicio  = models.DateField()
    fecha_fin     = models.DateField(null=True, blank=True)  # null = en curso
    justificacion = models.CharField(max_length=200)

    @property
    def en_curso(self):
        return self.fecha_fin is None

    @property
    def dias_totales(self):
        if self.fecha_fin:
            return (self.fecha_fin - self.fecha_inicio).days + 1
        return None

    def __str__(self):
        return f"Descanso: {self.solicitante} - {self.justificacion} ({self.estado})"

    class Meta:
        verbose_name = 'Descanso médico'
        verbose_name_plural = 'Descansos médicos'

# PROGRAMACIÓN DE VACACIONES
class ProgramacionVacaciones(models.Model):
    ESTADO = [
        ('sin_programar', 'Sin programar'),
        ('programado', 'Programado'),
    ]

    trabajador = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='vacaciones')
    anio = models.PositiveSmallIntegerField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    estado = models.CharField(max_length=15, choices=ESTADO, default='sin_programar')
    observaciones = models.TextField(blank=True)
    aprobado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name='vacaciones_aprobadas')
    creado_en = models.DateTimeField(auto_now_add=True)

    @property
    def dias_totales(self):
        return (self.fecha_fin - self.fecha_inicio).days + 1

    def __str__(self):
        return f"{self.trabajador} - {self.anio} ({self.estado})"

    class Meta:
        verbose_name = 'Programación de vacaciones'
        verbose_name_plural = 'Programación de vacaciones'

# NOTIFICACIONES
class Notificacion(models.Model):
    TIPO = [
        ('cambio_turno', 'Cambio de turno'),
        ('vacaciones', 'Vacaciones'),
        ('descanso', 'Descanso médico'),
        ('general', 'General'),
    ]

    destinatario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='notificaciones')
    tipo = models.CharField(max_length=20, choices=TIPO)
    titulo = models.CharField(max_length=150)
    mensaje = models.TextField()
    leido = models.BooleanField(default=False)
    creada_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.tipo}] {self.titulo} - {self.destinatario}"

    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-creada_en']