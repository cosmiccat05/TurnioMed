from TurnosMed.models import SolicitudDescansoMedico, SolicitudVacaciones


def total_pendientes_admin():
    return (
        SolicitudVacaciones.objects.filter(estado='aprobado_jefe').count()
        + SolicitudDescansoMedico.objects.filter(estado='aprobado_jefe').count()
    )
