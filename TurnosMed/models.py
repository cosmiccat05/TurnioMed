from datetime import timedelta
from decimal import Decimal
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone


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


# ---------------------------------------------------------------------------
# Estructura organizacional: Departamento → Área → Sala
# Roles:  Jefe de Departamento → Jefe(s) de Área → Personal asistencial
# ---------------------------------------------------------------------------
class Departamento(models.Model):
    TIPO = [
        ('enfermeria', 'Enfermería'),
        ('medicina', 'Medicina'),
    ]

    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO)
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
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='salas')
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


# -------------------------
# USUARIO
# -------------------------

class Usuario(AbstractBaseUser, PermissionsMixin):
    ROL = [
        ('admin', 'Administrador'), #Jefe de Personal
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
        ('cas', 'CAS'),
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
        Departamento, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='personal'
    )
    area = models.ForeignKey(
        Area, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='personal'
    )
    sala = models.ForeignKey(
        Sala, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='personal'
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'apellidos', 'dni']

    objects = UsuarioManager()

    # --- Propiedades de tipo ---
    @property
    def requiere_medio_turno(self):
        # Los terceros deben tener al menos 1 turno M o T por mes
        return self.condicion == 'tercero'

    @property
    def es_tipo_enfermeria(self):
        # Conforman el personal de enfermería: licenciadas y técnicos
        return self.tipo_trabajador in ['licenciada_enfermeria', 'tecnico_enfermeria']

    @property
    def es_tipo_medico(self):
        return self.tipo_trabajador == 'medico'

    # --- Helpers de rol ---
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

    # --- Validaciones ---
    def clean(self):
        if self.rol in ['jefe_departamento', 'jefe_area']:
            if not self.tipo_trabajador:
                raise ValidationError('Un jefe debe tener tipo de trabajador.')
            if self.tipo_trabajador == 'tecnico_enfermeria':
                raise ValidationError('Un jefe no puede ser técnico de enfermería.')
            if self.condicion != 'nombrado':
                raise ValidationError('Un jefe debe tener condición nombrado.')
            if not self.departamento:
                raise ValidationError('Un jefe debe tener departamento asignado.')

        if self.rol == 'jefe_area' and not self.area:
            raise ValidationError('Un jefe de área debe tener área asignada.')

        if self.rol == 'jefe_area' and self.sala:
            raise ValidationError('Un jefe de área no debe tener sala asignada.')

        if self.rol == 'jefe_departamento':
            if self.area:
                raise ValidationError('Un jefe de departamento no debe tener área asignada.')
            if self.sala:
                raise ValidationError('Un jefe de departamento no debe tener sala asignada.')
            if (
                self.departamento_id
                and Usuario.objects.filter(
                    rol='jefe_departamento',
                    departamento_id=self.departamento_id,
                ).exclude(pk=self.pk).exists()
            ):
                raise ValidationError(
                    'Solo puede existir un jefe de departamento por departamento.'
                )

        if self.rol == 'asistencial':
            if not self.tipo_trabajador:
                raise ValidationError('El personal asistencial debe tener tipo de trabajador.')
            if not self.departamento:
                raise ValidationError('El personal asistencial debe tener departamento asignado.')
            if not self.area:
                raise ValidationError('El personal asistencial debe tener área asignada.')
            if not self.sala:
                raise ValidationError('El personal asistencial debe tener sala asignada.')

        if self.area and self.departamento:
            if self.area.departamento_id != self.departamento_id:
                raise ValidationError('El área seleccionada no pertenece al departamento asignado.')

        if self.sala and self.area:
            if self.sala.area_id != self.area_id:
                raise ValidationError('La sala seleccionada no pertenece al área asignada.')

        if self.departamento and self.tipo_trabajador:
            if self.departamento.tipo == 'enfermeria' and not self.es_tipo_enfermeria:
                raise ValidationError(
                    'Un departamento de enfermería solo admite licenciadas '
                    'o técnicos de enfermería.'
                )
            if self.departamento.tipo == 'medicina' and not self.es_tipo_medico:
                raise ValidationError(
                    'Un departamento médico solo admite personal médico.'
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.nombre_completo()} ({self.get_rol_display()})'

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        constraints = [
            models.UniqueConstraint(
                fields=['departamento'],
                condition=Q(rol='jefe_departamento'),
                name='un_jefe_departamento_por_departamento',
            ),
        ]


# -------------------------
# TURNO
# -------------------------

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
        'D4': {'nombre': 'Día completo', 'hora_inicio': '07:00', 'hora_fin': '19:30', 'horas': Decimal('12.5')},
        'D':  {'nombre': 'Día', 'hora_inicio': '07:00', 'hora_fin': '19:00', 'horas': Decimal('12')},
        'T':  {'nombre': 'Tarde', 'hora_inicio': '13:00', 'hora_fin': '19:00', 'horas': Decimal('6')},
        'M':  {'nombre': 'Medio día', 'hora_inicio': '07:00', 'hora_fin': '13:00', 'horas': Decimal('6')},
        'N4': {'nombre': 'Noche completa', 'hora_inicio': '19:00', 'hora_fin': '07:30', 'horas': Decimal('12.5')},
        'N':  {'nombre': 'Noche', 'hora_inicio': '19:00', 'hora_fin': '07:00', 'horas': Decimal('12')},
    }

    trabajador = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name='turnos'
    )
    creado_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='turnos_creados'
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
        return self.DATOS_TURNOS[self.codigo]['nombre'] if self.codigo else 'Libre'

    @property
    def hora_inicio(self):
        return self.DATOS_TURNOS[self.codigo]['hora_inicio'] if self.codigo else None

    @property
    def hora_fin(self):
        return self.DATOS_TURNOS[self.codigo]['hora_fin'] if self.codigo else None

    @property
    def horas(self):
        return self.DATOS_TURNOS[self.codigo]['horas'] if self.codigo else Decimal('0')

    def motivo_bloqueo(self):
        if not self.codigo:
            return ''

        if self.trabajador.fecha_nacimiento:
            fn = self.trabajador.fecha_nacimiento
            if self.fecha.month == fn.month and self.fecha.day == fn.day:
                return 'el día de su cumpleaños'

        if ProgramacionVacaciones.objects.filter(
            trabajador=self.trabajador,
            fecha_inicio__lte=self.fecha,
            fecha_fin__gte=self.fecha,
        ).exists():
            return 'un día de vacaciones programadas'

        if SolicitudVacaciones.objects.filter(
            solicitante=self.trabajador,
            estado='procesado',
            fecha_inicio__lte=self.fecha,
            fecha_fin__gte=self.fecha,
        ).exists():
            return 'un día de adelanto de vacaciones aprobado'

        if SolicitudDescansoMedico.objects.filter(
            solicitante=self.trabajador,
            estado='procesado',
            fecha_inicio__lte=self.fecha,
        ).filter(
            Q(fecha_fin__isnull=True) | Q(fecha_fin__gte=self.fecha)
        ).exists():
            return 'un día de descanso médico aprobado'

        return ''

    def clean(self):
        if self.trabajador.rol in ['admin', 'jefe_departamento']:
            raise ValidationError('Este usuario no recibe programación de turnos.')

        if self.codigo and self.codigo not in self.DATOS_TURNOS:
            raise ValidationError('Código de turno inválido.')

        motivo_bloqueo = self.motivo_bloqueo()
        if motivo_bloqueo:
            raise ValidationError(
                f'{self.trabajador.nombre_completo()} no puede tener turno '
                f'el {self.fecha}: corresponde a {motivo_bloqueo}.'
            )

    def save(self, *args, **kwargs):
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


# -------------------------
# SOLICITUDES
# -------------------------
# Flujo de estados:
#   pendiente
#       ↓ jefe de área aprueba       ↓ jefe de área rechaza
#   aprobado_jefe               rechazado_jefe  (fin)
#       ↓ admin procesa              ↓ admin rechaza
#   procesado  (fin)            rechazado_admin (fin)
#
# PD: SolicitudCambioTurno NO pasa por el admin, esto se maneja
# directamente con el jefe de área que aprueba/rechaza.
# ---------------------------------------------------------------------------

class Solicitud(models.Model):
    ESTADO = [
        ('pendiente', 'Pendiente'),
        ('aprobado_jefe', 'Aprobado por jefe'),
        ('rechazado_jefe', 'Rechazado por jefe'),
        ('procesado', 'Procesado'),
        ('rechazado_admin', 'Rechazado por administrador'),
    ]

    solicitante = models.ForeignKey(
        Usuario, on_delete=models.CASCADE,
        related_name='%(class)s_solicitudes'
    )

    estado = models.CharField(max_length=20, choices=ESTADO, default='pendiente')
    motivo = models.TextField()

    # Fase 1 — jefe de área
    revisado_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='%(class)s_revisadas'
    )
    comentario_jefe = models.TextField(blank=True)
    fecha_revision = models.DateTimeField(null=True, blank=True)

    # Fase 2 — admin/jefe de personal (solo aplica si requiere_admin = True)
    procesado_por    = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='%(class)s_procesadas'
    )
    comentario_admin = models.TextField(blank=True)
    fecha_procesado = models.DateTimeField(null=True, blank=True)

    fecha_solicitud = models.DateTimeField(auto_now_add=True)

    # --- Propiedades de estado ---
    @property
    def pendiente_jefe(self):
        #Esperando revisión del jefe de área.
        return self.estado == 'pendiente'

    @property
    def pendiente_admin(self):
        #Aprobada por el jefe, esperando que el admin la procese.
        return self.estado == 'aprobado_jefe'

    @property
    def finalizada(self):
        #El proceso terminó.
        return self.estado in ['procesado', 'rechazado_jefe', 'rechazado_admin']

    @property
    def aprobada(self):
        #Procesada favorablemente por el admin.
        return self.estado == 'procesado'

    #Sobreescribir en subclases según corresponda
    @property
    def requiere_admin(self):
        raise NotImplementedError

    def _validar_revisor(self, revisor):
        if self.solicitante.es_asistencial():
            if not revisor.es_jefe_area() or revisor.area_id != self.solicitante.area_id:
                raise ValidationError('La solicitud debe ser revisada por el jefe del área.')
        elif self.solicitante.es_jefe_area():
            if (
                not revisor.es_jefe_departamento()
                or revisor.departamento_id != self.solicitante.departamento_id
            ):
                raise ValidationError(
                    'La solicitud debe ser revisada por el jefe del departamento.'
                )
        else:
            raise ValidationError('Este cargo no tiene flujo de solicitudes habilitado.')

    def _validar_admin(self, administrador):
        if not administrador.es_admin():
            raise ValidationError('Solo el administrador puede procesar esta solicitud.')
        if self.estado != 'aprobado_jefe':
            raise ValidationError(
                'Solo se pueden procesar solicitudes aprobadas por el jefe correspondiente.'
            )

    def aprobar_por_jefe(self, revisor, comentario=''):
        if not self.pendiente_jefe:
            raise ValidationError('Esta solicitud ya fue revisada.')
        self._validar_revisor(revisor)
        self.estado = 'aprobado_jefe' if self.requiere_admin else 'procesado'
        self.revisado_por = revisor
        self.comentario_jefe = comentario
        self.fecha_revision = timezone.now()
        self.save()

    def rechazar_por_jefe(self, revisor, comentario=''):
        if not self.pendiente_jefe:
            raise ValidationError('Esta solicitud ya fue revisada.')
        self._validar_revisor(revisor)
        self.estado = 'rechazado_jefe'
        self.revisado_por = revisor
        self.comentario_jefe = comentario
        self.fecha_revision = timezone.now()
        self.save()

    def clean(self):
        if self.revisado_por:
            self._validar_revisor(self.revisado_por)
        if self.procesado_por and not self.procesado_por.es_admin():
            raise ValidationError('Solo el administrador puede procesar solicitudes.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        abstract = True
        ordering = ['-fecha_solicitud']

# -------------------------
# SOLICITUDES: CAMBIO TURNO
# -------------------------

class SolicitudCambioTurno(Solicitud):
    turno_original = models.ForeignKey(
        Turno, on_delete=models.CASCADE, related_name='solicitudes_cambio_origen'
    )
    turno_destino = models.ForeignKey(
        Turno, on_delete=models.CASCADE, related_name='solicitudes_cambio_destino'
    )
    companero = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name='companero_cambio'
    )

    @property
    def requiere_admin(self):
        # El cambio de turno lo resuelve únicamente el jefe de área.
        return False

    def clean(self):
        super().clean()
        if (
            self.estado != 'procesado'
            and self.turno_original_id
            and self.turno_original.trabajador_id != self.solicitante_id
        ):
            raise ValidationError('El turno original debe pertenecer al solicitante.')
        if (
            self.estado != 'procesado'
            and self.turno_destino_id
            and self.turno_destino.trabajador_id != self.companero_id
        ):
            raise ValidationError('El turno destino debe pertenecer al compañero indicado.')
        if self.solicitante_id and self.companero_id:
            if self.solicitante_id == self.companero_id:
                raise ValidationError('El cambio de turno requiere otro trabajador.')
            if self.solicitante.condicion != self.companero.condicion:
                raise ValidationError(
                    'Los cambios de turno solo pueden realizarse entre personal '
                    'con la misma condicion laboral.'
                )
            if (
                self.solicitante.area_id != self.companero.area_id
                or self.solicitante.departamento_id != self.companero.departamento_id
            ):
                raise ValidationError('Los cambios de turno deben realizarse dentro de la misma área.')
        if self.turno_original_id and self.turno_destino_id:
            if not self.turno_original.codigo or not self.turno_destino.codigo:
                raise ValidationError('Ambos turnos deben estar programados para solicitar un cambio.')
            if self.turno_original.horas != self.turno_destino.horas:
                raise ValidationError('Los turnos a intercambiar deben tener la misma cantidad de horas.')
            if (
                self.turno_original.fecha == self.turno_destino.fecha
                and self.turno_original.codigo == self.turno_destino.codigo
            ):
                raise ValidationError(
                    'No se puede intercambiar el mismo tipo de turno en una misma fecha.'
                )

    def ejecutar_cambio(self):
        if self.estado != 'procesado':
            raise ValidationError('El cambio debe estar aprobado antes de ejecutarse.')

        original = Turno.objects.select_for_update().get(id=self.turno_original_id)
        destino = Turno.objects.select_for_update().get(id=self.turno_destino_id)

        if original.fecha == destino.fecha:
            codigo_original = original.codigo
            original.codigo = destino.codigo
            destino.codigo = codigo_original
            original.save()
            destino.save()
            return

        if Turno.objects.filter(
            trabajador=self.solicitante,
            fecha=destino.fecha,
        ).exclude(id=original.id).exists():
            raise ValidationError(
                'El solicitante ya tiene un turno en la fecha que recibira.'
            )
        if Turno.objects.filter(
            trabajador=self.companero,
            fecha=original.fecha,
        ).exclude(id=destino.id).exists():
            raise ValidationError(
                'El companero ya tiene un turno en la fecha que recibira.'
            )

        # Los registros se conservan porque la solicitud los usa como historial.
        original.trabajador = self.companero
        destino.trabajador = self.solicitante
        original.save()
        destino.save()

    def __str__(self):
        return f'Cambio: {self.solicitante} ↔ {self.companero} ({self.estado})'

    class Meta:
        verbose_name = 'Solicitud de cambio de turno'
        verbose_name_plural = 'Solicitudes de cambio de turno'

# --------------------------------
# SOLICITUDES: ADELANTO VACACIONES
# --------------------------------

class SolicitudVacaciones(Solicitud):
    # Solo adelanto por ahora; 'cambio' queda para versiones futuras.
    TIPO = [
        ('adelanto', 'Adelanto'),
    ]

    tipo = models.CharField(max_length=15, choices=TIPO, default='adelanto')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()

    @property
    def dias_totales(self):
        return (self.fecha_fin - self.fecha_inicio).days + 1

    @property
    def requiere_admin(self):
        # El jefe aprueba/rechaza; si aprueba, el admin lo procesa.
        return True

    def clean(self):
        super().clean()
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValidationError('La fecha final no puede ser anterior a la fecha inicial.')
        if (
            self.fecha_inicio
            and self.fecha_fin
            and self.fecha_inicio.year != self.fecha_fin.year
        ):
            raise ValidationError('El adelanto de vacaciones debe pertenecer a un solo año.')

    def procesar_por_admin(self, administrador, aprobar=True, comentario=''):
        self._validar_admin(administrador)
        if not aprobar:
            self.estado = 'rechazado_admin'
            self.procesado_por = administrador
            self.comentario_admin = comentario
            self.fecha_procesado = timezone.now()
            self.save()
            return

        with transaction.atomic():
            programacion = ProgramacionVacaciones.objects.select_for_update().filter(
                trabajador=self.solicitante,
                anio=self.fecha_inicio.year,
            ).first()
            if not programacion:
                raise ValidationError(
                    'No existe una programación anual de vacaciones de la cual descontar días.'
                )
            if self.fecha_fin >= programacion.fecha_inicio:
                raise ValidationError(
                    'El adelanto debe ubicarse antes de las vacaciones anuales pendientes.'
                )
            if self.dias_totales > programacion.dias_totales:
                raise ValidationError(
                    'El adelanto solicitado excede los días de vacaciones pendientes.'
                )

            Turno.objects.filter(
                trabajador=self.solicitante,
                fecha__range=(self.fecha_inicio, self.fecha_fin),
            ).delete()

            if self.dias_totales == programacion.dias_totales:
                programacion.delete()
            else:
                programacion.fecha_inicio += timedelta(days=self.dias_totales)
                programacion.estado = 'modificado'
                programacion.save()

            self.estado = 'procesado'
            self.procesado_por = administrador
            self.comentario_admin = comentario
            self.fecha_procesado = timezone.now()
            self.save()

    def __str__(self):
        return f'Vacaciones: {self.solicitante} ({self.fecha_inicio} – {self.fecha_fin})'

    class Meta:
        verbose_name = 'Solicitud de vacaciones'
        verbose_name_plural = 'Solicitudes de vacaciones'

# ----------------------------
# SOLICITUDES: DESCANSO MEDICO
# ----------------------------

class SolicitudDescansoMedico(Solicitud):
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)

    @property
    def en_curso(self):
        return self.fecha_fin is None

    @property
    def dias_totales(self):
        if self.fecha_fin:
            return (self.fecha_fin - self.fecha_inicio).days + 1
        return None

    @property
    def requiere_admin(self):
        # El jefe aprueba/rechaza; si aprueba, el admin bloquea esos días en turnos.
        return True

    def clean(self):
        super().clean()
        if self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValidationError('La fecha final no puede ser anterior a la fecha inicial.')

    def procesar_por_admin(self, administrador, aprobar=True, comentario=''):
        self._validar_admin(administrador)
        if not aprobar:
            self.estado = 'rechazado_admin'
            self.procesado_por = administrador
            self.comentario_admin = comentario
            self.fecha_procesado = timezone.now()
            self.save()
            return

        filtros_turno = {
            'trabajador': self.solicitante,
            'fecha__gte': self.fecha_inicio,
        }
        if self.fecha_fin:
            filtros_turno['fecha__lte'] = self.fecha_fin

        with transaction.atomic():
            Turno.objects.filter(**filtros_turno).delete()
            self.estado = 'procesado'
            self.procesado_por = administrador
            self.comentario_admin = comentario
            self.fecha_procesado = timezone.now()
            self.save()

    def __str__(self):
        return f'Descanso: {self.solicitante} ({self.estado})'

    class Meta:
        verbose_name = 'Descanso médico'
        verbose_name_plural = 'Descansos médicos'


# -------------------------
# PROGRAMACION VACACIONES
# Solo el admin (jefe de personal) programa vacaciones en el sistema.
# ---------------------------------------------------------------------------

class ProgramacionVacaciones(models.Model):
    ESTADO = [
        ('programado', 'Programado'),
        ('modificado', 'Modificado'),
    ]

    trabajador = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name='vacaciones'
    )
    anio = models.PositiveSmallIntegerField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    estado = models.CharField(max_length=15, choices=ESTADO, default='programado')
    observaciones = models.TextField(blank=True)

    programado_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='vacaciones_programadas'
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    modificado_en = models.DateTimeField(auto_now=True)

    @property
    def dias_totales(self):
        return (self.fecha_fin - self.fecha_inicio).days + 1

    def clean(self):
        if self.fecha_fin and self.fecha_inicio and self.fecha_fin < self.fecha_inicio:
            raise ValidationError('La fecha final no puede ser anterior a la fecha inicial.')
        if self.fecha_inicio and self.fecha_inicio.year != self.anio:
            raise ValidationError('La fecha inicial debe pertenecer al año programado.')
        if self.fecha_fin and self.fecha_fin.year != self.anio:
            raise ValidationError('La fecha final debe pertenecer al año programado.')
        if self.trabajador_id and self.trabajador.rol in ['admin', 'jefe_departamento']:
            raise ValidationError('Este usuario no recibe programación de vacaciones.')

    def save(self, *args, **kwargs):
        self.full_clean()
        with transaction.atomic():
            super().save(*args, **kwargs)
            Turno.objects.filter(
                trabajador=self.trabajador,
                fecha__range=(self.fecha_inicio, self.fecha_fin),
            ).delete()

    def __str__(self):
        return f'{self.trabajador} – {self.anio} ({self.estado})'

    class Meta:
        verbose_name = 'Programación de vacaciones'
        verbose_name_plural = 'Programación de vacaciones'
        unique_together = ('trabajador', 'anio')


# -------------------------
# NOTIFICACIONES
# -------------------------

class Notificacion(models.Model):
    TIPO = [
        ('cambio_turno', 'Cambio de turno'),
        ('vacaciones', 'Vacaciones'),
        ('descanso', 'Descanso médico'),
        ('general', 'General'),
    ]

    destinatario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name='notificaciones'
    )
    tipo = models.CharField(max_length=20, choices=TIPO)
    titulo = models.CharField(max_length=150)
    mensaje = models.TextField()
    leido = models.BooleanField(default=False)
    url_destino = models.CharField(max_length=200, blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'[{self.tipo}] {self.titulo} → {self.destinatario}'

    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-creada_en']
