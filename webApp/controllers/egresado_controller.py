# --- IMPORTACIONES CORREGIDAS ---
from django.shortcuts import render, redirect, get_object_or_404 # <--- ¡AQUÍ ESTABA EL ERROR! Faltaba get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib import messages
from webApp.forms.egresado_form import EgresadoForm
from webApp.models.egresado import Egresado

# ==========================================
# 1. FUNCIÓN PRINCIPAL: LOGIN + REGISTRO + LISTA
# ==========================================
def registrar_egresado(request):
    
    # --- LOGICA DE LOGIN (Si mandan el formulario de entrar) ---
    if request.method == 'POST' and 'btn_login' in request.POST:
        usuario_form = request.POST.get('login_user')
        pass_form = request.POST.get('login_pass')

        # Autenticación estándar de Django contra el usuario admin ya existente
        # en la base de datos. El superusuario se crea una sola vez con
        # `python manage.py createsuperuser` (ver README) y su contraseña
        # se gestiona desde ahí, nunca hardcodeada en el código.
        user = authenticate(request, username=usuario_form, password=pass_form)
        if user is not None and user.is_staff:
            login(request, user)
            messages.success(request, '👋 ¡Bienvenido al Sistema!')
            return redirect('registro_egresado')
        else:
            messages.error(request, '⛔ Usuario o contraseña incorrectos.')

    # --- LOGICA DEL SISTEMA (Solo si ya entraste) ---
    if request.user.is_authenticated:
        # Traemos la lista para la tabla
        lista_egresados = Egresado.objects.all().order_by('-id')

        # Si mandan el formulario de registrar nuevo alumno
        if request.method == 'POST' and 'btn_registro' in request.POST:
            form = EgresadoForm(request.POST)
            if form.is_valid():
                data = form.cleaned_data
                codigo = data['codigo_alumno']
                
                try:
                    # Crear/Actualizar usuario del alumno
                    if User.objects.filter(username=codigo).exists():
                        nuevo_usuario = User.objects.get(username=codigo)
                        nuevo_usuario.email = data['email']
                        nuevo_usuario.first_name = data['nombres']
                        nuevo_usuario.last_name = data['apellidos']
                        nuevo_usuario.save()
                    else:
                        nuevo_usuario = User.objects.create_user(
                            username=codigo, 
                            email=data['email'], 
                            password=codigo
                        )
                        nuevo_usuario.first_name = data['nombres']
                        nuevo_usuario.last_name = data['apellidos']
                        nuevo_usuario.save()

                    # Guardar en tabla Egresado
                    egresado = form.save(commit=False)
                    egresado.usuario = nuevo_usuario
                    
                    # Forzar guardado de campos manuales
                    egresado.nombres = data['nombres']
                    egresado.apellidos = data['apellidos']
                    egresado.correo = data['email']
                    
                    egresado.save()
                    messages.success(request, f'✅ Alumno {data["nombres"]} registrado.')
                    return redirect('registro_egresado')

                except Exception as e:
                    messages.error(request, f'⛔ Error al guardar: {e}')
            else:
                messages.error(request, '⚠️ Revisa el formulario.')
        else:
            form = EgresadoForm()
        
        return render(request, 'webApp/registro_egresado.html', {
            'form': form,
            'egresados': lista_egresados
        })
    
    else:
        # Si no está logueado, mostramos el login azul
        return render(request, 'webApp/registro_egresado.html', {})

# ==========================================
# 2. FUNCIÓN DE EDICIÓN (EL LÁPIZ)
# ==========================================
def editar_egresado(request, id):
    # Busca al alumno por ID, si no existe lanza error 404
    egresado = get_object_or_404(Egresado, id=id)

    if request.method == 'POST':
        form = EgresadoForm(request.POST, instance=egresado)
        if form.is_valid():
            try:
                data = form.cleaned_data
                
                # Actualizar User (Login)
                u = egresado.usuario
                u.email = data['email']
                u.first_name = data['nombres']
                u.last_name = data['apellidos']
                u.save()

                # Actualizar Egresado
                egresado_editado = form.save(commit=False)
                egresado_editado.nombres = data['nombres']
                egresado_editado.apellidos = data['apellidos']
                egresado_editado.correo = data['email']
                egresado_editado.save()

                messages.success(request, '✏️ Cambios guardados correctamente.')
                return redirect('registro_egresado')
            except Exception as e:
                messages.error(request, f'Error al editar: {e}')
    else:
        # Pre-llenar formulario
        initial_data = {
            'email': egresado.correo,
            'nombres': egresado.nombres,
            'apellidos': egresado.apellidos,
            'telefono': egresado.telefono
        }
        form = EgresadoForm(instance=egresado, initial=initial_data)

    return render(request, 'webApp/editar_egresado.html', {'form': form, 'egresado': egresado})

# ==========================================
# 3. FUNCIÓN DE SALIR
# ==========================================
def cerrar_sesion(request):
    logout(request)
    return redirect('registro_egresado')