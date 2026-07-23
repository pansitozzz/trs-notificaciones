from django.urls import path
from . import views
from .views import dashboard

urlpatterns = [

    # ================== LOGIN / HOME ==================
    path("", views.login_view, name="login"),
    path("home/", views.home_view, name="home"),
    path("cambiar-contrasena/", views.cambiar_contrasena_view, name="cambiar_contrasena"),
    
    path('toggle-demo/', views.toggle_demo_mode, name='toggle_demo'),
    path('cambiar-rol-auditor/<int:rol_id>/', views.cambiar_rol_auditor, name='cambiar_rol_auditor'),
    
    # ================== AUTENTICACIÓN ==================
    path("logout/", views.logout_view, name="logout"),

    # ================== TRABAJADOR ==================
    path("trabajadores/", views.listar_trabajadores, name="listar_trabajadores"),
    path("crear-trabajador/", views.crear_trabajador_view, name="crear_trabajador"),
    path("trabajador/<int:id_emp>/detalle/", views.trabajador_detalle, name="trabajador_detalle"),
    path("trabajador/<int:id_emp>/exportar/", views.exportar_ficha, name="exportar_ficha"),
    path("editar_trabajador/", views.editar_trabajador, name="editar_trabajador"),
    path("cambiar-estado/", views.cambiar_estado_trabajador_view, name="cambiar_estado_trabajador"),

    # ================== MAQUINARIA ==================
    path("maquinaria/", views.maquinaria_list, name="maquinaria_list"),
    path("maquinaria/crear/", views.crear_maquinaria_view, name="crear_maquinaria"),
    path("maquinaria/editar/", views.editar_maquinaria, name="editar_maquinaria"),
    path("maquinaria/<int:id_maq>/detalle/", views.maquinaria_detalle, name="maquinaria_detalle"),
    path("maquinaria/<int:id_maq>/toggle-estado/", views.toggle_estado_maquinaria, name="toggle_estado_maquinaria"),
    path('maquinaria/editar_estado/', views.editar_maquinaria_estado, name='editar_maquinaria_estado'),
    
    # ================== ASIGNACIONES ==================
    path("asignaciones/", views.listar_asignaciones, name="listar_asignaciones"),
    path("crear_asignacion/", views.crear_asignacion_view, name="crear_asignacion"),
    path('asignacion/cambiar_estado/', views.cambiar_estado_asignacion, name='cambiar_estado_asignacion'),
    path('asignacion/subir_foto/<int:id_asig>/', views.subir_foto_asignacion, name='subir_foto_asignacion'),
    path('asignaciones/editar/<int:id_asig>/', views.editar_asignacion_view, name='editar_asignacion'),

    # ================== DASHBOARD ==================
    path('dashboard/', dashboard, name='dashboard'),
    
    # ================== CAPACITACIONES ==================
    path('capacitaciones/', views.capacitaciones_view, name='capacitaciones'),
    path('notificaciones/', views.notificaciones_view, name='notificaciones'),

    # ================== HISTORIAL CONEXION ==================
    path('historial-logins/', views.historial_login_view, name='historial_logins'),
    
    # ================== BACKUP ==================
    path("backup/", views.backup_view, name="backup"),
    path("backup/csv/", views.exportar_backup_csv, name="exportar_backup_csv"),
    path("backup/json/", views.exportar_backup_json, name="exportar_backup_json"),

    #================== APIs PARA DASHBOARD (AJAX) ==================
    #Estas son las rutas invisibles que usan los gráficos para pedir datos al hacer clic

]


# from django.urls import path
# # Importamos el controlador específico
# from webApp.controllers import egresado_controller
# from webApp.controllers import encuesta_controller

# urlpatterns = [
#     # Ruta para registrarse
#     # path('registro-egresado/', egresado_controller.registrar_egresado, name='registro_egresado'),
#     path("", egresado_controller.registrar_egresado, name='registro_egresado'),
#     path('logout/', egresado_controller.cerrar_sesion, name='logout'),
#     path('editar-egresado/<int:id>/', egresado_controller.editar_egresado, name='editar_egresado'),
#     path('encuesta/<int:id>/', encuesta_controller.realizar_encuesta, name='realizar_encuesta'),
# ]