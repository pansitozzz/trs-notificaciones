from datetime import date

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand

from webApp.models.usuario_model import Privilegio, StatusTra, Trabajador


class Command(BaseCommand):
    help = (
        "Crea el primer usuario para iniciar sesion en la app (modelo "
        "Trabajador, no el auth.User de Django). Util al levantar el "
        "proyecto por primera vez en una base de datos nueva."
    )

    def add_arguments(self, parser):
        parser.add_argument("--usuario", default="admin", help="Usuario de login (default: admin)")
        parser.add_argument("--password", default="admin1234", help="Password de login (default: admin1234)")
        parser.add_argument("--nombre", default="Administrador", help="Nombre de pila")

    def handle(self, *args, **options):
        usuario = options["usuario"]
        password = options["password"]
        nombre = options["nombre"]

        status_activo, _ = StatusTra.objects.get_or_create(status_tra="Activo")
        privilegio_admin, _ = Privilegio.objects.get_or_create(privilegio="Administrador")

        trabajador, creado = Trabajador.objects.get_or_create(
            usuario=usuario,
            defaults=dict(
                dni="00000000",
                first_name=nombre,
                apellido_pat="Demo",
                apellido_mat="Demo",
                ocupacion="Administrador",
                fec_init=date.today(),
                contra=make_password(password),
                id_status_tra=status_activo,
                id_privilegio=privilegio_admin,
            ),
        )

        if not creado:
            trabajador.contra = make_password(password)
            trabajador.id_status_tra = status_activo
            trabajador.id_privilegio = privilegio_admin
            trabajador.save()
            self.stdout.write(self.style.WARNING(f"El usuario '{usuario}' ya existia, se actualizo su password."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Usuario '{usuario}' creado correctamente."))

        self.stdout.write(f"Inicia sesion en la app con usuario='{usuario}' y la password indicada.")
