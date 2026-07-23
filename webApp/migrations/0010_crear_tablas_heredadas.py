"""
Varios modelos de esta app (StatusTra, Privilegio, AFP, Banco,
DistritoResidencia, EstadoMaquina, StatusAsignacion, StatusCapacitacion,
Trabajador, Maquina, Asignacion, RegistroHoras, Capacitacion,
AlertaMaquinaria, Notificacion, HistorialLogin) están marcados como
`managed = False` porque en el despliegue original esas tablas ya
existían en una base de datos MySQL creada aparte (no por Django).

Eso significa que un clon nuevo del repositorio, con una base de datos
vacía, nunca las tiene: `migrate` por sí solo no las crea porque Django
no gestiona el esquema de modelos no administrados.

Esta migración las crea explícitamente, usando la definición ACTUAL de
los modelos (no el estado histórico de la migración 0001, que quedó
desactualizado porque estos modelos se editaron directamente sin
generar migraciones mientras estuvieron en managed=False).

Es idempotente: si una tabla ya existe (como en el servidor de
producción original), esta migración no hace nada con ella. Por eso es
segura de aplicar tanto en una base de datos nueva como en una que ya
tenía estas tablas desde antes.
"""

from django.db import migrations


MODELOS_EN_ORDEN = [
    "StatusTra",
    "Privilegio",
    "AFP",
    "Banco",
    "DistritoResidencia",
    "EstadoMaquina",
    "StatusAsignacion",
    "StatusCapacitacion",
    "Trabajador",
    "Maquina",
    "Asignacion",
    "RegistroHoras",
    "Capacitacion",
    "AlertaMaquinaria",
    "Notificacion",
    "HistorialLogin",
]


def crear_tablas_heredadas(apps, schema_editor):
    # Importamos las clases de modelo reales (no las históricas de esta
    # migración) porque varias de ellas ganaron campos nuevos con el
    # tiempo sin que existiera una migración que lo registrara.
    from webApp.models import usuario_model

    connection = schema_editor.connection
    tablas_existentes = set(connection.introspection.table_names())

    for nombre_modelo in MODELOS_EN_ORDEN:
        modelo = getattr(usuario_model, nombre_modelo)
        if modelo._meta.db_table in tablas_existentes:
            continue
        modelo._meta.managed = True
        try:
            schema_editor.create_model(modelo)
        finally:
            modelo._meta.managed = False


def no_revertir(apps, schema_editor):
    # No borramos nada al revertir: estas tablas pueden ser las mismas
    # que ya existían antes de que este proyecto Django existiera, así
    # que un rollback nunca debe eliminarlas.
    pass


class Migration(migrations.Migration):

    # MySQL no puede ejecutar DDL (CREATE TABLE) dentro de una
    # transacción con posibilidad de rollback real, así que esta
    # migración corre fuera de una transacción.
    atomic = False

    dependencies = [
        ("webApp", "0009_encuesta"),
    ]

    operations = [
        migrations.RunPython(crear_tablas_heredadas, no_revertir),
    ]
