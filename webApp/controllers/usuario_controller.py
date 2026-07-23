from webApp.models.usuario_model import Trabajador, Privilegio
from django.shortcuts import redirect
from django.contrib.auth.hashers import make_password, check_password

def autenticar_usuario(request, username, password):
    try:
        trabajador = Trabajador.objects.get(usuario=username)
    except Trabajador.DoesNotExist:
        return None, "Usuario no encontrado"

    if not check_password(password, trabajador.contra):
        return None, "Contrasena incorrecta"

    # Guardamos ID del trabajador en la sesión
    request.session["usuario_id"] = trabajador.id_emp
    return trabajador, None

# Función para guardar una nueva contrasena de forma segura
def guardar_contrasena_segura(trabajador, nueva_contrasena):
    # Encripta la contrasena antes de guardarla
    trabajador.contra = make_password(nueva_contrasena)
    trabajador.save()

def update_pw_creden(username, dni, nueva_contrasena):
    """
    Verifica que el usuario y DNI coincidan y actualiza la contrasena.
    """
    try:
        # Busca un trabajador que coincida con el usuario y el DNI.
        trabajador = Trabajador.objects.get(usuario=username, dni=dni)
    except Trabajador.DoesNotExist:
        return False, "Usuario o DNI incorrectos."

    # Encripta la nueva contrasena.
    trabajador.contra = make_password(nueva_contrasena)
    # Guarda los cambios en la base de datos.
    trabajador.save()

    return True, None
    
def obtener_usuario_y_rol(usuario_id):
    try:
        trabajador = Trabajador.objects.get(id_emp=usuario_id)
        rol = trabajador.id_privilegio.privilegio  # Accedemos al campo 'privilegio'
        return trabajador, rol  # Devolvemos ambos valores
    except Trabajador.DoesNotExist:
        return None, None


def logout_controller(request):
    """Cierra sesión y redirige al login"""
    if "usuario_id" in request.session:
        del request.session["usuario_id"]
    return redirect("login")
