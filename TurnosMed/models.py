from decimal import Decimal
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models

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

class Departamento(models.Model):
    TIPO = [
        ('enfermeria', 'Enfermería'),
        ('medicina', 'Medicina'),
    ]

    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = 'Departamento'
        verbose_name_plural = 'Departamentos'
        ordering = ['nombre']


class Area(models.Model):
    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.CASCADE,
        related_name='areas',
        null=True,
        blank=True,
    )
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        if self.departamento:
            return f'{self.departamento.nombre} - {self.nombre}'
        return self.nombre

    class Meta:
        verbose_name = 'Área'
        verbose_name_plural = 'Áreas'
        ordering = ['departamento', 'nombre']
        unique_together = ('departamento', 'nombre')


class Sala(models.Model):
    area = models.ForeignKey(
        Area,
        on_delete=models.CASCADE,
        related_name='salas'
    )
    nombre = models.CharField(max_length=50)
    activa = models.BooleanField(default=True)

    def __str__(self):
        if self.area:
            return f'{self.area.nombre} - {self.nombre}'
        return self.nombre

    class Meta:
        verbose_name = 'Sala'
        verbose_name_plural = 'Salas'
        unique_together = ('area', 'nombre')
        ordering = ['area', 'nombre']


class Usuario(AbstractBaseUser, PermissionsMixin):
    ROL = [
        ('admin', 'Administrador'),
        ('jefe_departamento', 'Jefe de departamento'),
        ('jefe_area', 'Jefe de área'),
        ('asistencial', 'Personal asistencial'),
    ]

    TIPO_TRABAJADOR = [
        ('licenciada_enfermeria', 'Licenciada de Enfermería'),
        ('tecnico_enfermeria', 'Técnico de Enfermería'),
        ('medico', 'Médico'),
    ]

    CONDICION = [
        ('tercero', 'Tercero'),
        ('nombrado', 'Nombrado'),
    ]

    nombre = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    telefono = models.CharField(max_length=9, blank=True)
    dni = models.CharField(max_length=8, unique=True)
    email = models.EmailField(unique=True)

    fecha_nacimiento = models.DateField(null=True, blank=True)
    fecha_ingreso = models.DateField(null=True, blank=True)

    rol = models.CharField(max_length=25, choices=ROL)
    cargo = models.CharField(max_length=100, blank=True)
    tipo_trabajador = models.CharField(max_length=30, choices=TIPO_TRABAJADOR, blank=True)
    condicion = models.CharField(max_length=10, choices=CONDICION, blank=True)

    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='personal'
    )

    area = models.ForeignKey(
        Area,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='personal'
    )

    sala = models.ForeignKey(
        Sala,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='personal'
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'apellidos', 'dni']

    objects = UsuarioManager()

    @property
    def requiere_medio_turno(self):
        return self.condicion == 'tercero'

    @property
    def es_tipo_enfermeria(self):
        return self.tipo_trabajador in ['licenciada_enfermeria', 'tecnico_enfermeria']

    @property
    def es_tipo_medico(self):
        return self.tipo_trabajador == 'medico'

    def nombre_completo(self):
        return f'{self.nombre} {self.apellidos}'

    def es_admin(self):
        return self.rol == 'admin'

    def es_jefe_departamento(self):
        return self.rol == 'jefe_departamento'

    def es_jefe_area(self):
        return self.rol == 'jefe_area'

    def es_jefe(self):
        return self.rol in ['jefe_departamento', 'jefe_area']

    def es_asistencial(self):
        return self.rol == 'asistencial'

    def cargo_display(self):
        if self.rol == 'admin':
            return 'Administrador'

        partes = []

        if self.cargo:
            partes.append(self.cargo)

        if self.rol == 'jefe_departamento' and self.departamento:
            partes.append(f'Jefe de {self.departamento.nombre}')

        elif self.rol == 'jefe_area' and self.area:
            partes.append(f'Jefe de {self.area.nombre}')

        elif self.tipo_trabajador:
            partes.append(self.get_tipo_trabajador_display())

        return ' · '.join(partes)

    def clean(self):
        if self.rol in ['jefe_departamento', 'jefe_area']:
            if self.tipo_trabajador == 'tecnico_enfermeria':
                raise ValidationError('Un jefe no puede ser técnico de enfermería.')

            if self.condicion != 'nombrado':
                raise ValidationError('Un jefe debe tener condición nombrado.')

            if not self.departamento:
                raise ValidationError('Un jefe debe tener departamento asignado.')

        if self.rol == 'jefe_area' and not self.area:
            raise ValidationError('Un jefe de área debe tener área asignada.')

        if self.rol == 'jefe_departamento':
            if self.area:
                raise ValidationError('Un jefe de departamento no debe tener área asignada.')

            if self.sala:
                raise ValidationError('Un jefe de departamento no debe tener sala asignada.')

        if self.rol == 'asistencial':
            if not self.tipo_trabajador:
                raise ValidationError('El personal asistencial debe tener tipo de trabajador.')

            if not self.departamento:
                raise ValidationError('El personal asistencial debe tener departamento asignado.')

            if not self.area:
                raise ValidationError('El personal asistencial debe tener área asignada.')

        if self.area and self.departamento:
            if self.area.departamento_id != self.departamento_id:
                raise ValidationError('El área seleccionada no pertenece al departamento asignado.')

        if self.sala and self.area:
            if self.sala.area_id != self.area_id:
                raise ValidationError('La sala seleccionada no pertenece al área asignada.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.nombre_completo()} ({self.get_rol_display()})'

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'


class Turno(models.Model):
    CODIGOS = [
        ('D4', 'Día completo'),
        ('D', 'Día'),
        ('T', 'Tarde'),
        ('M', 'Medio día'),
        ('N4', 'Noche completa'),
        ('N', 'Noche'),
    ]

    DATOS_TURNOS = {
        'D4': {
            'nombre': 'Día completo',
            'hora_inicio': '07:00',
            'hora_fin': '19:30',
            'horas': Decimal('12.5'),
        },
        'D': {
            'nombre': 'Día',
            'hora_inicio': '07:00',
            'hora_fin': '19:00',
            'horas': Decimal('12'),
        },
        'T': {
            'nombre': 'Tarde',
            'hora_inicio': '13:00',
            'hora_fin': '19:00',
            'horas': Decimal('6'),
        },
        'M': {
            'nombre': 'Medio día',
            'hora_inicio': '07:00',
            'hora_fin': '13:00',
            'horas': Decimal('6'),
        },
        'N4': {
            'nombre': 'Noche completa',
            'hora_inicio': '19:00',
            'hora_fin': '07:30',
            'horas': Decimal('12.5'),
        },
        'N': {
            'nombre': 'Noche',
            'hora_inicio': '19:00',
            'hora_fin': '07:00',
            'horas': Decimal('12'),
        },
    }

    trabajador = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='turnos'
    )

    creado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='turnos_creados'
    )

    fecha = models.DateField()
    codigo = models.CharField(max_length=2, choices=CODIGOS, blank=True)

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

    @staticmethod
    def normalizar_codigo(codigo, trabajador):
        return codigo or ''

    def clean(self):
        if self.trabajador.rol in ['admin', 'jefe_departamento']:
            raise ValidationError('Este usuario no recibe programación de turnos.')

        if self.codigo and self.trabajador.fecha_nacimiento:
            nacimiento = self.trabajador.fecha_nacimiento
            if self.fecha.month == nacimiento.month and self.fecha.day == nacimiento.day:
                raise ValidationError(
                    f'{self.trabajador.nombre_completo()} tiene cumpleaños '
                    f'el {self.fecha} - ese día debe ser libre.'
                )

        if self.codigo and self.codigo not in self.DATOS_TURNOS:
            raise ValidationError('Código de turno inválido.')

    def save(self, *args, **kwargs):
        self.codigo = self.normalizar_codigo(self.codigo, self.trabajador)
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        tipo = self.codigo if self.codigo else 'Libre'
        return f'{self.trabajador.nombre_completo()} – {self.fecha} – {tipo}'

    class Meta:
        verbose_name = 'Turno'
        verbose_name_plural = 'Turnos'
        ordering = ['fecha', 'trabajador']
        unique_together = ('trabajador', 'fecha')


class Solicitud(models.Model):
    ESTADO = [
        ('pendiente', 'Pendiente'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
    ]

    solicitante = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='%(class)s_solicitudes'
    )
    estado = models.CharField(max_length=20, choices=ESTADO, default='pendiente')
    motivo = models.TextField()
    comentario_jefe = models.TextField(blank=True)

    revisado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_revisadas'
    )

    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_revision = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True
        ordering = ['-fecha_solicitud']


class SolicitudCambioTurno(Solicitud):
    turno_original = models.ForeignKey(
        Turno,
        on_delete=models.CASCADE,
        related_name='solicitudes_cambio_origen'
    )
    turno_destino = models.ForeignKey(
        Turno,
        on_delete=models.CASCADE,
        related_name='solicitudes_cambio_destino'
    )
    companero = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='companero_cambio'
    )

    def __str__(self):
        return f'Cambio: {self.solicitante} - {self.companero} ({self.estado})'

    class Meta:
        verbose_name = 'Solicitud de cambio de turno'
        verbose_name_plural = 'Solicitudes de cambio de turno'


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
        return (self.fecha_fin - self.fecha_inicio).days + 1

    def __str__(self):
        return f'Vacaciones: {self.solicitante} ({self.fecha_inicio} - {self.fecha_fin})'

    class Meta:
        verbose_name = 'Solicitud de vacaciones'
        verbose_name_plural = 'Solicitudes de vacaciones'


class SolicitudDescansoMedico(Solicitud):
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
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
        return f'Descanso: {self.solicitante} - {self.justificacion} ({self.estado})'

    class Meta:
        verbose_name = 'Descanso médico'
        verbose_name_plural = 'Descansos médicos'


class ProgramacionVacaciones(models.Model):
    ESTADO = [
        ('sin_programar', 'Sin programar'),
        ('programado', 'Programado'),
    ]

    trabajador = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='vacaciones'
    )
    anio = models.PositiveSmallIntegerField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    estado = models.CharField(max_length=15, choices=ESTADO, default='sin_programar')
    observaciones = models.TextField(blank=True)

    aprobado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vacaciones_aprobadas'
    )

    creado_en = models.DateTimeField(auto_now_add=True)

    @property
    def dias_totales(self):
        return (self.fecha_fin - self.fecha_inicio).days + 1

    def __str__(self):
        return f'{self.trabajador} - {self.anio} ({self.estado})'

    class Meta:
        verbose_name = 'Programación de vacaciones'
        verbose_name_plural = 'Programación de vacaciones'


class Notificacion(models.Model):
    TIPO = [
        ('cambio_turno', 'Cambio de turno'),
        ('vacaciones', 'Vacaciones'),
        ('descanso', 'Descanso médico'),
        ('general', 'General'),
    ]

    destinatario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='notificaciones'
    )
    tipo = models.CharField(max_length=20, choices=TIPO)
    titulo = models.CharField(max_length=150)
    mensaje = models.TextField()
    leido = models.BooleanField(default=False)
    creada_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'[{self.tipo}] {self.titulo} - {self.destinatario}'

    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-creada_en']