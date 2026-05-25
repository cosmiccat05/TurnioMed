from datetime import date

from django.test import TestCase
from django.urls import reverse

from TurnosMed.models import (
    Area,
    Departamento,
    Notificacion,
    ProgramacionVacaciones,
    Sala,
    SolicitudVacaciones,
    Turno,
    Usuario,
)


class AdminPanelTests(TestCase):
    def setUp(self):
        self.departamento = Departamento.objects.create(nombre='Enfermeria', tipo='enfermeria')
        self.area = Area.objects.create(nombre='Emergencia', departamento=self.departamento)
        self.sala = Sala.objects.create(nombre='Sala A', area=self.area)
        self.admin = Usuario.objects.create_user(
            email='personal@turniomed.pe',
            password='clave-segura',
            nombre='Ada',
            apellidos='Admin',
            dni='20000001',
            rol='admin',
        )
        self.jefe = Usuario.objects.create_user(
            email='jefe@turniomed.pe',
            password='clave-segura',
            nombre='Juana',
            apellidos='Supervisora',
            dni='20000002',
            rol='jefe_area',
            tipo_trabajador='licenciada_enfermeria',
            condicion='nombrado',
            departamento=self.departamento,
            area=self.area,
        )
        self.trabajador = Usuario.objects.create_user(
            email='tec@turniomed.pe',
            password='clave-segura',
            nombre='Luis',
            apellidos='Tecnico',
            dni='20000003',
            rol='asistencial',
            tipo_trabajador='tecnico_enfermeria',
            condicion='cas',
            departamento=self.departamento,
            area=self.area,
            sala=self.sala,
        )
        self.client.force_login(self.admin)

    def test_admin_regular_ingresa_al_panel_propio(self):
        self.client.logout()
        response = self.client.post(reverse('signin'), {
            'email': self.admin.email,
            'password': 'clave-segura',
        })

        self.assertRedirects(response, reverse('admin_home'))

    def test_paginas_principales_del_panel_renderizan(self):
        for url in [
            reverse('admin_home'),
            reverse('admin_personal'),
            reverse('admin_vacaciones'),
            reverse('admin_vacaciones_programar'),
            reverse('admin_solicitudes'),
        ]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)

    def test_home_no_renderiza_encabezado_de_pagina_vacio(self):
        home = self.client.get(reverse('admin_home'))
        personal = self.client.get(reverse('admin_personal'))

        self.assertNotContains(home, 'class="page-header"')
        self.assertContains(personal, 'class="page-header"')

    def test_sidebar_admin_muestra_solo_acciones_de_cuenta(self):
        response = self.client.get(reverse('admin_home'))

        self.assertContains(response, 'Mi perfil')
        self.assertContains(response, 'Cerrar sesión')
        self.assertNotContains(response, 'dropdown-user-header')

    def test_programar_vacaciones_desde_panel_libera_turno(self):
        Turno.objects.create(
            trabajador=self.trabajador,
            fecha=date(2026, 6, 12),
            codigo='D',
            creado_por=self.jefe,
        )
        response = self.client.post(reverse('admin_vacaciones_programar'), {
            'trabajador': self.trabajador.id,
            'anio': 2026,
            'fecha_inicio': '2026-06-01',
            'fecha_fin': '2026-06-30',
            'observaciones': '',
        })

        self.assertRedirects(response, reverse('admin_vacaciones'))
        self.assertTrue(ProgramacionVacaciones.objects.filter(trabajador=self.trabajador).exists())
        self.assertFalse(Turno.objects.filter(trabajador=self.trabajador).exists())

    def test_aprobar_adelanto_desde_panel_genera_notificacion(self):
        ProgramacionVacaciones.objects.create(
            trabajador=self.trabajador,
            anio=2026,
            fecha_inicio=date(2026, 6, 1),
            fecha_fin=date(2026, 6, 30),
            programado_por=self.admin,
        )
        solicitud = SolicitudVacaciones.objects.create(
            solicitante=self.trabajador,
            motivo='Necesidad familiar',
            fecha_inicio=date(2026, 5, 1),
            fecha_fin=date(2026, 5, 15),
        )
        solicitud.aprobar_por_jefe(self.jefe)

        response = self.client.post(
            reverse('admin_procesar_solicitud', kwargs={'tipo': 'vacaciones', 'id': solicitud.id}),
            {'accion': 'aprobar', 'comentario': 'Conforme'},
        )

        self.assertRedirects(
            response,
            reverse('admin_detalle_solicitud', kwargs={'tipo': 'vacaciones', 'id': solicitud.id}),
        )
        solicitud.refresh_from_db()
        self.assertEqual(solicitud.estado, 'procesado')
        self.assertTrue(Notificacion.objects.filter(destinatario=self.trabajador).exists())

    def test_eliminar_personal_lo_desactiva_sin_borrarlo(self):
        response = self.client.post(reverse('admin_personal_eliminar', args=[self.trabajador.id]))

        self.assertRedirects(response, reverse('admin_personal'))
        self.trabajador.refresh_from_db()
        self.assertFalse(self.trabajador.is_active)

    def test_ruta_de_desactivacion_no_expone_confirmacion_por_get(self):
        response = self.client.get(reverse('admin_personal_eliminar', args=[self.trabajador.id]))

        self.assertRedirects(response, reverse('admin_personal'))
        self.trabajador.refresh_from_db()
        self.assertTrue(self.trabajador.is_active)

    def test_superusuario_django_no_es_personal_administrable(self):
        superusuario = Usuario.objects.create_superuser(
            email='root@turniomed.pe',
            password='clave-segura',
            nombre='Cuenta',
            apellidos='Sistema',
            dni='20000009',
        )

        listado = self.client.get(reverse('admin_personal'))
        editar = self.client.get(reverse('admin_personal_editar', args=[superusuario.id]))
        eliminar = self.client.post(reverse('admin_personal_eliminar', args=[superusuario.id]))

        self.assertNotContains(listado, 'Cuenta Sistema')
        self.assertEqual(editar.status_code, 404)
        self.assertEqual(eliminar.status_code, 404)

    def test_formularios_cargan_scripts_y_etiqueta_anio_visibles(self):
        personal = self.client.get(reverse('admin_personal_agregar'))
        vacaciones = self.client.get(reverse('admin_vacaciones_programar'))

        self.assertContains(personal, 'panel/js/personal.js')
        self.assertNotContains(personal, 'name="cargo"')
        self.assertContains(vacaciones, 'Año')
