from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import (
    Area,
    Departamento,
    Notificacion,
    ProgramacionVacaciones,
    Sala,
    SolicitudCambioTurno,
    SolicitudDescansoMedico,
    SolicitudVacaciones,
    Turno,
    Usuario,
)

class ReglasProgramacionTests(TestCase):
    def setUp(self):
        self.departamento = Departamento.objects.create(
            nombre='Enfermeria',
            tipo='enfermeria',
        )
        self.area = Area.objects.create(
            nombre='Emergencia',
            departamento=self.departamento,
        )
        self.sala = Sala.objects.create(nombre='Sala A', area=self.area)
        self.admin = Usuario.objects.create_user(
            email='admin@turniomed.pe',
            password='test',
            nombre='Ana',
            apellidos='Admin',
            dni='10000001',
            rol='admin',
        )
        self.jefe = Usuario.objects.create_user(
            email='jefe@turniomed.pe',
            password='test',
            nombre='Julia',
            apellidos='Jefa',
            dni='10000002',
            rol='jefe_area',
            tipo_trabajador='licenciada_enfermeria',
            condicion='nombrado',
            departamento=self.departamento,
            area=self.area,
        )
        self.trabajador = Usuario.objects.create_user(
            email='asistencial@turniomed.pe',
            password='test',
            nombre='Mario',
            apellidos='Diaz',
            dni='10000003',
            rol='asistencial',
            tipo_trabajador='tecnico_enfermeria',
            condicion='cas',
            departamento=self.departamento,
            area=self.area,
            sala=self.sala,
            fecha_nacimiento=date(1995, 4, 20),
        )
        self.companero = Usuario.objects.create_user(
            email='companero@turniomed.pe',
            password='test',
            nombre='Lucia',
            apellidos='Perez',
            dni='10000004',
            rol='asistencial',
            tipo_trabajador='tecnico_enfermeria',
            condicion='cas',
            departamento=self.departamento,
            area=self.area,
            sala=self.sala,
        )

    def test_no_permite_turno_en_cumpleanios(self):
        turno = Turno(
            trabajador=self.trabajador,
            fecha=date(2026, 4, 20),
            codigo='D',
            creado_por=self.jefe,
        )

        with self.assertRaises(ValidationError):
            turno.save()

    def test_programar_vacaciones_libera_turnos_y_bloquea_nuevos(self):
        Turno.objects.create(
            trabajador=self.trabajador,
            fecha=date(2026, 6, 10),
            codigo='D',
            creado_por=self.jefe,
        )

        ProgramacionVacaciones.objects.create(
            trabajador=self.trabajador,
            anio=2026,
            fecha_inicio=date(2026, 6, 1),
            fecha_fin=date(2026, 6, 30),
            programado_por=self.admin,
        )

        self.assertFalse(
            Turno.objects.filter(trabajador=self.trabajador, fecha=date(2026, 6, 10)).exists()
        )
        with self.assertRaises(ValidationError):
            Turno.objects.create(
                trabajador=self.trabajador,
                fecha=date(2026, 6, 10),
                codigo='N',
                creado_por=self.jefe,
            )

    def test_descanso_aprobado_libera_turnos_y_bloquea_nuevos(self):
        Turno.objects.create(
            trabajador=self.trabajador,
            fecha=date(2026, 5, 8),
            codigo='D',
            creado_por=self.jefe,
        )
        solicitud = SolicitudDescansoMedico.objects.create(
            solicitante=self.trabajador,
            motivo='Descanso medico',
            fecha_inicio=date(2026, 5, 7),
            fecha_fin=date(2026, 5, 9),
        )

        solicitud.aprobar_por_jefe(self.jefe)
        solicitud.procesar_por_admin(self.admin)

        self.assertFalse(
            Turno.objects.filter(trabajador=self.trabajador, fecha=date(2026, 5, 8)).exists()
        )
        with self.assertRaises(ValidationError):
            Turno.objects.create(
                trabajador=self.trabajador,
                fecha=date(2026, 5, 8),
                codigo='N',
                creado_por=self.jefe,
            )

    def test_adelanto_descuenta_vacaciones_anuales_y_libera_turnos(self):
        programacion = ProgramacionVacaciones.objects.create(
            trabajador=self.trabajador,
            anio=2026,
            fecha_inicio=date(2026, 6, 1),
            fecha_fin=date(2026, 6, 30),
            programado_por=self.admin,
        )
        Turno.objects.create(
            trabajador=self.trabajador,
            fecha=date(2026, 5, 5),
            codigo='D',
            creado_por=self.jefe,
        )
        solicitud = SolicitudVacaciones.objects.create(
            solicitante=self.trabajador,
            motivo='Adelanto',
            fecha_inicio=date(2026, 5, 1),
            fecha_fin=date(2026, 5, 15),
        )

        solicitud.aprobar_por_jefe(self.jefe)
        solicitud.procesar_por_admin(self.admin)

        programacion.refresh_from_db()
        solicitud.refresh_from_db()
        self.assertEqual(programacion.fecha_inicio, date(2026, 6, 16))
        self.assertEqual(programacion.estado, 'modificado')
        self.assertEqual(solicitud.estado, 'procesado')
        self.assertFalse(
            Turno.objects.filter(trabajador=self.trabajador, fecha=date(2026, 5, 5)).exists()
        )

    def test_solo_existe_un_jefe_departamento_por_departamento(self):
        Usuario.objects.create_user(
            email='jefedep@turniomed.pe',
            password='test',
            nombre='Rosa',
            apellidos='Rios',
            dni='10000005',
            rol='jefe_departamento',
            tipo_trabajador='licenciada_enfermeria',
            condicion='nombrado',
            departamento=self.departamento,
        )

        with self.assertRaises(ValidationError):
            Usuario.objects.create_user(
                email='jefedep2@turniomed.pe',
                password='test',
                nombre='Maria',
                apellidos='Soto',
                dni='10000006',
                rol='jefe_departamento',
                tipo_trabajador='licenciada_enfermeria',
                condicion='nombrado',
                departamento=self.departamento,
            )

    def test_cambio_rechaza_condicion_laboral_distinta(self):
        tercero = Usuario.objects.create_user(
            email='tercero@turniomed.pe',
            password='test',
            nombre='Luis',
            apellidos='Torres',
            dni='10000007',
            rol='asistencial',
            tipo_trabajador='tecnico_enfermeria',
            condicion='tercero',
            departamento=self.departamento,
            area=self.area,
            sala=self.sala,
        )
        original = Turno.objects.create(
            trabajador=self.trabajador, fecha=date(2026, 5, 4), codigo='D', creado_por=self.jefe
        )
        destino = Turno.objects.create(
            trabajador=tercero, fecha=date(2026, 5, 6), codigo='N', creado_por=self.jefe
        )

        with self.assertRaises(ValidationError):
            SolicitudCambioTurno.objects.create(
                solicitante=self.trabajador,
                companero=tercero,
                turno_original=original,
                turno_destino=destino,
                motivo='Cambio',
            )

    def test_cambio_aprobado_en_fechas_distintas_conserva_historial(self):
        original = Turno.objects.create(
            trabajador=self.trabajador, fecha=date(2026, 5, 4), codigo='D', creado_por=self.jefe
        )
        destino = Turno.objects.create(
            trabajador=self.companero, fecha=date(2026, 5, 6), codigo='N', creado_por=self.jefe
        )
        solicitud = SolicitudCambioTurno.objects.create(
            solicitante=self.trabajador,
            companero=self.companero,
            turno_original=original,
            turno_destino=destino,
            motivo='Cambio de fecha',
        )
        self.client.force_login(self.jefe)

        response = self.client.post(
            reverse('revisar_solicitud', kwargs={'tipo': 'cambio-turno', 'id': solicitud.id}),
            {'accion': 'aprobar'},
        )

        self.assertEqual(response.status_code, 200)
        solicitud.refresh_from_db()
        original.refresh_from_db()
        destino.refresh_from_db()
        self.assertEqual(solicitud.estado, 'procesado')
        self.assertEqual(original.trabajador, self.companero)
        self.assertEqual(destino.trabajador, self.trabajador)
        self.assertEqual(Notificacion.objects.count(), 2)

    def test_cambio_misma_fecha_no_admite_codigo_identico(self):
        original = Turno.objects.create(
            trabajador=self.trabajador, fecha=date(2026, 5, 5), codigo='D', creado_por=self.jefe
        )
        destino = Turno.objects.create(
            trabajador=self.companero, fecha=date(2026, 5, 5), codigo='D', creado_por=self.jefe
        )

        with self.assertRaises(ValidationError):
            SolicitudCambioTurno.objects.create(
                solicitante=self.trabajador,
                companero=self.companero,
                turno_original=original,
                turno_destino=destino,
                motivo='Mismo turno',
            )

    def test_cambio_misma_fecha_d_por_n_es_valido(self):
        original = Turno.objects.create(
            trabajador=self.trabajador, fecha=date(2026, 5, 5), codigo='D', creado_por=self.jefe
        )
        destino = Turno.objects.create(
            trabajador=self.companero, fecha=date(2026, 5, 5), codigo='N', creado_por=self.jefe
        )
        solicitud = SolicitudCambioTurno.objects.create(
            solicitante=self.trabajador,
            companero=self.companero,
            turno_original=original,
            turno_destino=destino,
            motivo='Dia por noche',
        )

        solicitud.aprobar_por_jefe(self.jefe)
        solicitud.ejecutar_cambio()
        original.refresh_from_db()
        destino.refresh_from_db()
        self.assertEqual(original.codigo, 'N')
        self.assertEqual(destino.codigo, 'D')

    def test_vacaciones_turnosmed_es_consulta(self):
        self.client.force_login(self.jefe)

        response = self.client.get(reverse('vacaciones'), {'anio': 2026})
        post_response = self.client.post(
            reverse('vacaciones'),
            {'trabajador_id': self.trabajador.id, 'fecha_inicio': '2026-06-01', 'fecha_fin': '2026-06-30'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Guardar')
        self.assertContains(response, 'tabindex="-1"', count=4)
        self.assertEqual(post_response.status_code, 200)
        self.assertFalse(ProgramacionVacaciones.objects.exists())

    def test_sidebar_operativo_usa_acciones_y_flecha_consistentes(self):
        self.client.force_login(self.jefe)

        response = self.client.get(reverse('home'))

        self.assertContains(response, 'Mi perfil')
        self.assertContains(response, 'Cerrar sesión')
        self.assertContains(response, 'user-chevron')

    def test_reporte_pdf_se_descarga_para_jefe(self):
        self.client.force_login(self.jefe)

        html_response = self.client.get(reverse('reportes'), {'categoria': 'cambios', 'anio': 2026, 'mes': 5})
        response = self.client.get(
            reverse('reportes'),
            {'categoria': 'cambios', 'anio': 2026, 'mes': 5, 'export': 'pdf'},
        )

        self.assertEqual(html_response.status_code, 200)
        self.assertContains(html_response, 'Cambios de turno')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF-1.4'))
