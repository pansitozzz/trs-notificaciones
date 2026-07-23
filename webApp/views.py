import os
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.contrib.sessions.models import Session
from django.db.models.functions import TruncMonth # <--- NUEVO IMPORT NECESARIO
import json
import logging
import csv
from datetime import datetime, date, timedelta
from io import BytesIO

# --- ReportLab Imports ---
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from PIL import Image # Usada en _header

# --- App Imports ---
from webApp.controllers.usuario_controller import autenticar_usuario, obtener_usuario_y_rol, update_pw_creden
from webApp.models.usuario_model import Trabajador, Privilegio, AFP, Banco, DistritoResidencia, StatusTra, Asignacion, Maquina, EstadoMaquina, StatusAsignacion, AlertaMaquinaria, Capacitacion, StatusCapacitacion, HistorialLogin, Notificacion, RegistroHoras
from webApp.forms.editar_form import TrabajadorForm
from webApp.forms.cloud_form import FotoAsignacionForm


logger = logging.getLogger(__name__)

# =============================================================
# 🛠️ FUNCIONES AUXILIARES GENERALES
# =============================================================

def get_client_ip(request):
    """Obtiene la IP real del cliente, incluso detrás de un proxy."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# =============================================================
# 📄 FUNCIONES DE GENERACIÓN DE PDF (REPORTLAB)
# =============================================================

# -------------------------------------------------------------
# 1. FUNCIÓN DE ENCABEZADO (Header)
# -------------------------------------------------------------
def _header(canvas, doc, trabajador):
    """Dibuja el logo COMPLETO con ruta confirmada y ancho de 1.5 pulgadas."""
    canvas.saveState()
    
    # Imports internos (necesarios para el callback de ReportLab)
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    import os
    from django.conf import settings
    from PIL import Image
    
    # 1. Configuración de la Ruta del Logo
    BASE_DIR = settings.BASE_DIR
    # ¡IMPORTANTE! La ruta se ha corregido a 'TRS.jpg' en el código del usuario.
    logo_file_path = os.path.join(BASE_DIR, 'webApp', 'static', 'img', 'TRS.jpg')
    
    # --- Configuración de Posición Absoluta ---
    PAGE_HEIGHT = letter[1]
    LINE_Y = PAGE_HEIGHT - 70 
    LOGO_Y = LINE_Y + 5 

    # 2. Intentar dibujar la imagen del logo
    try:
        if os.path.exists(logo_file_path):
            
            img = Image.open(logo_file_path)
            img_width, img_height = img.size
            
            # Ajuste de tamaño: 1.5 pulgadas.
            logo_target_width = 1.5 * inch
            
            logo_target_height = (logo_target_width * img_height) / img_width
            
            logo_x = doc.leftMargin
            
            canvas.drawImage(logo_file_path,
                             logo_x,
                             LOGO_Y,
                             width=logo_target_width,
                             height=logo_target_height)
        else:
            # Si no encuentra el archivo, imprime el mensaje de error y la ruta para debug.
            canvas.setFillColor(colors.red)
            canvas.setFont('Helvetica', 8)
            canvas.drawString(doc.leftMargin, LOGO_Y + (0.5 * inch), f"ERROR: LOGO NO ENCONTRADO EN {logo_file_path}")
    
    except Exception as e:
        canvas.setFillColor(colors.red)
        canvas.setFont('Helvetica', 8)
        canvas.drawString(doc.leftMargin, LOGO_Y + (0.5 * inch), f"ERROR AL CARGAR LOGO: {e}")

    # 3. Línea divisoria
    canvas.setStrokeColor(colors.HexColor('#dddddd'))
    canvas.line(doc.leftMargin, LINE_Y, doc.width + doc.leftMargin, LINE_Y)
    
    canvas.restoreState()

# -------------------------------------------------------------
# 2. FUNCIÓN AUXILIAR PARA CREAR TABLA DE DATOS
# -------------------------------------------------------------

def _crear_tabla_datos(datos, styles):
    """Crea y estiliza una tabla de dos columnas (Etiqueta | Valor)"""
    table_data = []
    
    # Formatear los datos con Paragraph
    for label, value in datos:
        label_p = Paragraph(label, styles['Etiqueta'])
        value_p = Paragraph(value, styles['Valor'])
        table_data.append([label_p, value_p])
    
    # Estilo de la tabla
    table_style = TableStyle([
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.HexColor('#eeeeee')),
        ('LINEAFTER', (0,0), (-1,-1), 0.5, colors.HexColor('#eeeeee')),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#fafafa')),
    ])
    
    # Anchos de columna
    col_widths = [2.0 * inch, 5.0 * inch]
    
    ficha_table = Table(table_data, colWidths=col_widths)
    ficha_table.setStyle(table_style)
    return ficha_table


# -------------------------------------------------------------
# 3. VISTA PRINCIPAL DE EXPORTACIÓN
# -------------------------------------------------------------
def exportar_ficha(request, id_emp):
    trabajador = get_object_or_404(Trabajador, id_emp=id_emp)

    # Configurar respuesta HTTP
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="ficha_{trabajador.dni}.pdf"'

    buffer = BytesIO()
    
    # Configuración del documento (margen superior ajustado a 1.5 * inch)
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            rightMargin=inch/2,
                            leftMargin=inch/2,
                            topMargin=1.5 * inch,
                            bottomMargin=inch/2)

    elements = []
    
    # --- Estilos ---
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TituloFicha', fontSize=18, spaceAfter=20, alignment=1, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='SubTitulo', fontSize=12, spaceBefore=15, spaceAfter=8, fontName='Helvetica-Bold', textColor=colors.HexColor('#000000')))
    styles.add(ParagraphStyle(name='Etiqueta', fontSize=10, fontName='Helvetica-Bold', textColor=colors.HexColor('#333333')))
    styles.add(ParagraphStyle(name='Valor', fontSize=10, fontName='Helvetica'))
    
    # Función auxiliar para obtener el valor del campo
    def get_field_value(trabajador, field_name):
        from datetime import date, datetime # Imports internos necesarios
        value = getattr(trabajador, field_name)
        if field_name == 'id_privilegio':
            return str(value.privilegio) if value else "N/A"
        elif field_name == 'id_status_tra':
            return str(value.status_tra) if value else "N/A"
        elif field_name in ('id_afp', 'id_banco', 'id_distrito'):
            return str(value.nombre) if value else "N/A"
        elif isinstance(value, date) or isinstance(value, datetime):
            return value.strftime("%Y-%m-%d")
        elif value is None:
            return "No aplica"
        else:
            if field_name == 'sueldo':
                 return f"S/. {value:.2f}"
            return str(value)

    # --- Contenido Principal ---
    
    elements.append(Paragraph("FICHA DE DATOS DEL TRABAJADOR", styles['TituloFicha']))
    
    # 2. DATOS PERSONALES
    elements.append(Paragraph("DATOS PERSONALES:", styles['SubTitulo']))
    datos_personales = [
        ("DNI:", get_field_value(trabajador, 'dni')),
        ("Nombre:", get_field_value(trabajador, 'first_name')),
        ("Apellido Paterno:", get_field_value(trabajador, 'apellido_pat')),
        ("Apellido Materno:", get_field_value(trabajador, 'apellido_mat')),
        ("Fecha de Nacimiento:", get_field_value(trabajador, 'fecha_nacimiento')),
        ("Celular:", get_field_value(trabajador, 'celular')),
        ("Distrito:", get_field_value(trabajador, 'id_distrito')),
    ]
    elements.append(_crear_tabla_datos(datos_personales, styles))

    # 3. DATOS LABORALES
    elements.append(Paragraph("DATOS LABORALES:", styles['SubTitulo']))
    datos_laborales = [
        ("Ocupación:", get_field_value(trabajador, 'ocupacion')),
        ("Fecha Inicio:", get_field_value(trabajador, 'fec_init')),
    ]
    elements.append(_crear_tabla_datos(datos_laborales, styles))

    # 4. PRIVILEGIO Y STATUS
    elements.append(Paragraph("PRIVILEGIO:", styles['SubTitulo']))
    datos_privilegio = [
        ("Privilegio:", get_field_value(trabajador, 'id_privilegio')),
        ("Status:", get_field_value(trabajador, 'id_status_tra')),
    ]
    elements.append(_crear_tabla_datos(datos_privilegio, styles))

    # 5. DATOS BANCARIOS
    elements.append(Paragraph("DATOS BANCARIOS:", styles['SubTitulo']))
    datos_bancarios = [
        ("AFP:", get_field_value(trabajador, 'id_afp')),
        ("Banco:", get_field_value(trabajador, 'id_banco')),
        ("Sueldo:", get_field_value(trabajador, 'sueldo')),
        ("Cuenta Bancaria:", get_field_value(trabajador, 'cuenta_bancaria')),
    ]
    elements.append(_crear_tabla_datos(datos_bancarios, styles))
    
    # 6. Generar el PDF
    doc.build(elements, onFirstPage=lambda canvas, doc: _header(canvas, doc, trabajador),
                       onLaterPages=lambda canvas, doc: _header(canvas, doc, trabajador))
    
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response

# =============================================================
# 👤 VISTAS DE USUARIO Y AUTENTICACIÓN
# =============================================================

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        trabajador, error = autenticar_usuario(request, username, password)

        if error:
            messages.error(request, error)
            return redirect("login")
            
        # Verificar si el trabajador está inhabilitado
        if trabajador.id_status_tra and trabajador.id_status_tra.id_status_tra == 2:
            messages.error(request, "Tu usuario esta inhabilitado. Contacta con el administrador.")
            return redirect("login")
            
        # --- LÓGICA DE LIMPIEZA DE SESIONES ---
        # Nota: Esto puede ser lento si tienes muchos usuarios, pero funciona para tu caso actual.
        all_sessions = Session.objects.filter(expire_date__gte=timezone.now())
        trabajador_id_a_buscar = str(trabajador.id_emp)
        
        sesiones_cerradas = 0
        for session in all_sessions:
            try:
                session_data = session.get_decoded()
                session_user_id = session_data.get('trabajador_id')
                
                if session_user_id is not None and str(session_user_id) == trabajador_id_a_buscar:
                    session.delete()
                    sesiones_cerradas += 1
            except Exception as e:
                # logger.warning(...) 
                pass
            
        if sesiones_cerradas > 0:
            print(f"Se cerraron {sesiones_cerradas} sesiones antiguas.") # O logger

        # --- LOGIN EXITOSO Y CORRECCIÓN DEL ERROR ---
        
        # 1. IMPORTANTE: Generar una nueva clave de sesión limpia.
        # Esto evita que intentemos actualizar una sesión que acabamos de borrar en el bucle de arriba.
        request.session.cycle_key() 

        # 2. Asignar datos
        request.session["trabajador_id"] = trabajador.id_emp
        
        # 3. Guardar (Ahora hará un INSERT seguro en la DB en vez de un UPDATE fallido)
        request.session.save()
        
        try:
            HistorialLogin.objects.create(
                trabajador=trabajador,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', 'Desconocido')
            )
        except Exception as e:
            print(f"Error historial: {e}") # O logger
            
        return redirect("home")

    return render(request, "webApp/login.html")

def logout_view(request):
    # Elimina toda la sesión actual
    request.session.flush()
    return redirect("login")






def toggle_demo_mode(request):
    # Si la variable existe y es True, la pone False (Apagar)
    # Si no existe o es False, la pone True (Encender)
    estado_actual = request.session.get('modo_demo_operador', False)
    request.session['modo_demo_operador'] = not estado_actual
    
    # Redirigir a la misma página donde estaba
    return redirect(request.META.get('HTTP_REFERER', 'home'))


# =============================================================
# 🏠 VISTAS DE HOME Y DASHBOARD
# =============================================================

# 2. REEMPLAZAR home_view (Arregla cards que no cambian y texto namespace)
def home_view(request):
    usuario_id = request.session.get("trabajador_id")
    if not usuario_id: return redirect("login")

    trabajador_real = Trabajador.objects.filter(pk=usuario_id).first()
    if not trabajador_real:
        request.session.pop("trabajador_id", None)
        return redirect("login")

    # Lógica Rol Simulado
    rol_id = request.session.get('rol_simulado', trabajador_real.id_privilegio.id_privilegio)
    try:
        rol_obj = Privilegio.objects.get(pk=int(rol_id))
    except:
        rol_obj = trabajador_real.id_privilegio

    # Ordenar Trabajadores: Admin(1) -> Super(2) -> Op(3)
    trabajadores = Trabajador.objects.select_related(
        "id_privilegio", "id_afp", "id_banco", "id_distrito", "id_status_tra"
    ).exclude(usuario='docente').order_by('id_privilegio__id_privilegio', 'apellido_pat')

    context = {
        "usuario": trabajador_real, 
        "rol": rol_obj, # <--- IMPORTANTE: Usar esta variable en el HTML
        "privilegios": Privilegio.objects.all(), "afps": AFP.objects.all(),
        "bancos": Banco.objects.all(), "distritos": DistritoResidencia.objects.all(),
        "status_list": StatusTra.objects.all(),
        "trabajadores": trabajadores, 
        "operadores": Trabajador.objects.filter(id_privilegio__id_privilegio=3),
        "maquinas": Maquina.objects.all(), "creador": trabajador_real,
        "alertas_mantenimiento": [m for m in Maquina.objects.all() if m.necesita_mantenimiento()],
    }
    return render(request, "webApp/home.html", context)

def dashboard(request):
    usuario_id = request.session.get("trabajador_id")
    if not usuario_id: return redirect("login")

    trabajador, rol = obtener_usuario_y_rol(usuario_id)
    if not trabajador: return redirect("login")

    # 1. Filtros
    fecha_inicio_str = request.GET.get('fecha_inicio')
    fecha_fin_str = request.GET.get('fecha_fin')
    estado = request.GET.get('estado')
    supervisor_id = request.GET.get('supervisor')

    hoy = date.today()

    if fecha_inicio_str:
        try: start_date = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
        except: start_date = hoy.replace(day=1)
    else: start_date = hoy.replace(day=1)

    if fecha_fin_str:
        try: end_date = datetime.strptime(fecha_fin_str, "%Y-%m-%d").date()
        except: end_date = hoy
    else: end_date = hoy

    if start_date > end_date: start_date = end_date - timedelta(days=30)

    asignacion_filters = Q(fecha_asig__gte=start_date, fecha_asig__lte=end_date)
    if estado: asignacion_filters &= Q(id_status__id_status=estado)
    if supervisor_id: asignacion_filters &= Q(id_creador__id_emp=supervisor_id)
    
    # 2. Consultas Base
    asigs_filtradas = Asignacion.objects.filter(asignacion_filters)
    base_exclude = ~Q(usuario='docente')

    # 3. KPIs (Calculados DESPUÉS de definir asigs_filtradas para evitar NameError)
    pendientes = asigs_filtradas.filter(id_status__nombre='Pendiente').count()
    completadas = asigs_filtradas.filter(id_status__nombre='Completada').count()
    en_mantenimiento = Maquina.objects.filter(id_estado__estado='Mantenimiento').count()
    
    # Top Trabajadores (Excluyendo docente y usando valores de asignación para evitar FieldError)
    top_emp_data = (asigs_filtradas
        .exclude(id_emp__usuario='docente')
        .values('id_emp')
        .annotate(total=Count('id_asig'))
        .order_by('-total')[:5])
    
    top_trabajadores = []
    for d in top_emp_data:
        if d['id_emp']:
            t = Trabajador.objects.get(pk=d['id_emp'])
            t.total_asig = d['total']
            top_trabajadores.append(t)

    # Top Máquinas
    top_maq_data = (asigs_filtradas
        .values('id_maq')
        .annotate(total=Count('id_asig'))
        .order_by('-total')[:5])
    
    top_maquinas = []
    for d in top_maq_data:
        if d['id_maq']:
            m = Maquina.objects.get(pk=d['id_maq'])
            m.total_asig = d['total']
            top_maquinas.append(m)

    # Top Creadores
    top_creadores_data = (asigs_filtradas
        .exclude(id_creador__usuario='docente')
        .values('id_creador')
        .annotate(total=Count('id_asig'))
        .order_by('-total')[:5])
    
    top_creadores = []
    for d in top_creadores_data:
        if d['id_creador']:
            c = Trabajador.objects.get(pk=d['id_creador'])
            c.total_creadas = d['total']
            top_creadores.append(c)

    estado_asig = asigs_filtradas.values('id_status__nombre').annotate(total=Count('id_asig')).order_by('-total')

    # RRHH
    distribucion_cargos = Trabajador.objects.filter(base_exclude).values('id_privilegio__privilegio').annotate(total=Count('id_emp'))
    
    f_historia = end_date - timedelta(days=180)
    contrataciones = (Trabajador.objects.filter(base_exclude, fec_init__range=[f_historia, end_date])
        .annotate(mes=TruncMonth('fec_init')).values('mes').annotate(total=Count('id_emp')).order_by('mes'))
        
    total_activos = Trabajador.objects.filter(base_exclude, id_status_tra__status_tra="Habilitado").count() or 1
    bajas = Trabajador.objects.filter(base_exclude, fecha_cese__range=[start_date, end_date]).count()
    tasa_rotacion = round((bajas / total_activos) * 100, 1)

    # Flota
    maquinas_criticas = Maquina.objects.order_by('-costo_mantenimiento')[:5]
    
    todas_maquinas = Maquina.objects.all()
    anio_actual = date.today().year
    antiguedad = {'menos_2': 0, 'entre_2_5': 0, 'mas_5': 0}
    lista_vida_util = []
    
    for m in todas_maquinas:
        fab = m.anio_fabricacion if m.anio_fabricacion else 2020
        vida_total = m.vida_util_estimada or 10
        edad = anio_actual - fab
        if edad < 2: antiguedad['menos_2'] += 1
        elif 2 <= edad <= 5: antiguedad['entre_2_5'] += 1
        else: antiguedad['mas_5'] += 1
        consumido = (edad / vida_total) * 100
        restante = max(0, 100 - consumido)
        color = 'success' if restante > 50 else 'warning' if restante > 20 else 'danger'
        lista_vida_util.append({'equipo': m.equipo, 'restante': round(restante, 1), 'color': color})

    # Heatmap
    heatmap_series = []
    delta = end_date - start_date
    limit_days = 90
    if delta.days > limit_days:
        hm_query_end = start_date + timedelta(days=limit_days)
        dias_rango = [start_date + timedelta(days=i) for i in range(limit_days + 1)]
    else:
        hm_query_end = end_date
        dias_rango = [start_date + timedelta(days=i) for i in range(delta.days + 1)]

    todas_maquinas_hm = Maquina.objects.all().order_by('equipo')
    asigs_heatmap = Asignacion.objects.filter(fin_asig__gte=start_date, fecha_asig__lte=hm_query_end).exclude(id_status__nombre="Cancelada").select_related('id_maq', 'id_status')

    for maq in todas_maquinas_hm:
        data_points = []
        total_dias_ocupados = 0
        mis_asigs = [a for a in asigs_heatmap if a.id_maq_id == maq.id_maq]
        for dia in dias_rango:
            intensidad = 0
            for a in mis_asigs:
                val_inicio = a.fecha_asig if not isinstance(a.fecha_asig, datetime) else a.fecha_asig.date()
                val_fin = a.fin_asig if not isinstance(a.fin_asig, datetime) else a.fin_asig.date()
                if val_inicio <= dia <= val_fin:
                    intensidad = 50 if a.id_status.nombre.upper() == 'COMPLETADA' else 100
                    break
            if intensidad > 0: total_dias_ocupados += 1
            data_points.append({'x': dia.strftime("%Y-%m-%d"), 'y': intensidad})
        heatmap_series.append({'name': maq.equipo, 'data': data_points, 'total_uso': total_dias_ocupados})
    
    heatmap_series.sort(key=lambda x: x['total_uso'], reverse=True)

    # BI
    datos_hist = (RegistroHoras.objects.filter(fecha__gte=start_date, fecha__lte=end_date)
        .annotate(mes=TruncMonth('fecha')).values('mes').annotate(total_horas=Sum('horas')).order_by('mes'))
    series_x, series_y, cat_meses = [], [], []
    for idx, dato in enumerate(datos_hist):
        if dato['mes']:
            cat_meses.append(dato['mes'].strftime("%b"))
            series_y.append(dato['total_horas'])
            series_x.append(idx + 1)

    mensaje_prevision = "Se requieren al menos 2 meses de datos para proyectar."
    if len(series_x) > 1:
        try:
            n = len(series_x)
            prom_x, prom_y = sum(series_x)/n, sum(series_y)/n
            num = sum((xi - prom_x) * (yi - prom_y) for xi, yi in zip(series_x, series_y))
            den = sum((xi - prom_x) ** 2 for xi in series_x)
            if den != 0:
                m = num / den
                b = prom_y - (m * prom_x)
                proyeccion = round(m * (n + 1) + b, 2)
                cat_meses.append("Proyección")
                series_y.append(proyeccion)
                mensaje_prevision = f"Proyección siguiente mes: {proyeccion} horas."
        except: pass

    uso_por_tipo = {}
    dias_del_rango = (end_date - start_date).days + 1
    horas_teoricas_por_maquina = dias_del_rango * 8 
    for m in todas_maquinas:
        tipo = m.equipo.split()[0].upper()
        if tipo not in uso_por_tipo: uso_por_tipo[tipo] = {'count': 0, 'horas': 0}
        uso_por_tipo[tipo]['count'] += 1
        uso_por_tipo[tipo]['horas'] += RegistroHoras.objects.filter(asignacion__id_maq=m, fecha__gte=start_date, fecha__lte=end_date).aggregate(s=Sum('horas'))['s'] or 0

    sat_labels, sat_data, recomendaciones = [], [], []
    for tipo, d in uso_por_tipo.items():
        cap = d['count'] * horas_teoricas_por_maquina
        pct = round((d['horas']/cap)*100, 1) if cap > 0 else 0
        sat_labels.append(f"{tipo} ({d['count']})")
        sat_data.append(pct)
        if pct > 85: recomendaciones.append(f"URGENTE: Flota {tipo} al {pct}% de capacidad.")

    # Contexto
    context = {
        'usuario': trabajador, 'rol': rol,
        'top_trabajadores': top_trabajadores, 'top_maquinas': top_maquinas, 'top_creadores': top_creadores,
        'estado_asig': estado_asig, 'pendientes': pendientes, 'completadas': completadas,
        'en_mantenimiento': en_mantenimiento, 'alertas_recientes': AlertaMaquinaria.objects.order_by('-fecha')[:5],
        'distribucion_cargos': distribucion_cargos, 'contrataciones': contrataciones, 'tasa_rotacion': tasa_rotacion,
        'maquinas_criticas': maquinas_criticas,
        'fecha_inicio': fecha_inicio_str, 'fecha_fin': fecha_fin_str, 'estado': estado, 'supervisor': supervisor_id,
        'todos_supervisores': Trabajador.objects.filter(id_privilegio__id_privilegio__in=[1, 2]).exclude(usuario='docente'),
        'todos_estados': StatusAsignacion.objects.all(),
        'heatmap_data': json.dumps(heatmap_series), 'chart_labels': json.dumps(cat_meses), 'chart_data': json.dumps(series_y), 
        'mensaje_prevision': mensaje_prevision, 'pie_labels': json.dumps(sat_labels), 'pie_data': json.dumps(sat_data), 
        'recomendaciones': recomendaciones,
        'lista_vida_util': lista_vida_util, 'antiguedad': antiguedad
    }
    return render(request, 'webApp/dashboard.html', context)
    
    
# =============================================================
# 👷 VISTAS DE TRABAJADORES
# =============================================================

def listar_trabajadores(request):
    usuario_id = request.session.get("trabajador_id")
    if not usuario_id:
        return redirect("login")

    usuario, rol = obtener_usuario_y_rol(usuario_id)
    hoy = timezone.now()

    # ANOTAMOS DOS COSAS:
    # 1. total_horas: Suma de horas (para Operadores)
    # 2. total_creadas: Conteo de asignaciones creadas (para Admin/Super)
    
    trabajadores = Trabajador.objects.select_related(
        "id_privilegio", "id_afp", "id_banco", "id_distrito", "id_status_tra"
    ).exclude(usuario='docente').annotate(
        # Suma de horas (Operadores)
        total_horas=Sum('registrohoras__horas',
            filter=Q(
                registrohoras__fecha__month=hoy.month, 
                registrohoras__fecha__year=hoy.year
            )
        ),
        # Conteo de asignaciones creadas (Admin/Super) - Usamos el reverse relation 'asignaciones_creadas'
        total_creadas=Count('asignaciones_creadas',
            filter=Q(
                asignaciones_creadas__fecha_asig__month=hoy.month,
                asignaciones_creadas__fecha_asig__year=hoy.year
            )
        )
    ).order_by('id_status_tra__id_status_tra', 'id_privilegio__id_privilegio', 'apellido_pat')

    context = {
        "usuario": usuario,
        "rol": rol,
        "trabajadores": trabajadores,
        "privilegios": Privilegio.objects.all(),
        "afps": AFP.objects.all(),
        "bancos": Banco.objects.all(),
        "distritos": DistritoResidencia.objects.all(),
        "status_list": StatusTra.objects.all(),
    }
    return render(request, "webApp/trabajadores.html", context)


def trabajador_detalle(request, id_emp):
    trabajador = get_object_or_404(Trabajador, id_emp=id_emp)

    data = {
        "dni": trabajador.dni,
        "nombre": trabajador.first_name,
        "apellido_pat": trabajador.apellido_pat,
        "apellido_mat": trabajador.apellido_mat,
        "ocupacion": trabajador.ocupacion,
        "fec_init": trabajador.fec_init.strftime("%Y-%m-%d") if trabajador.fec_init else "",
        "privilegio": trabajador.id_privilegio.privilegio if hasattr(trabajador, "id_privilegio") and trabajador.id_privilegio else "",
        "afp": trabajador.id_afp.nombre if hasattr(trabajador, "id_afp") and trabajador.id_afp else "",
        "banco": trabajador.id_banco.nombre if hasattr(trabajador, "id_banco") and trabajador.id_banco else "",
        "distrito": trabajador.id_distrito.nombre if hasattr(trabajador, "id_distrito") and trabajador.id_distrito else "",
        "status": trabajador.id_status_tra.status_tra if hasattr(trabajador, "id_status_tra") and trabajador.id_status_tra else "",
        "sueldo": str(trabajador.sueldo) if trabajador.sueldo else "",
        "cuenta_bancaria": trabajador.cuenta_bancaria or "",
        "celular": trabajador.celular or "",
        "fecha_nacimiento": trabajador.fecha_nacimiento.strftime("%Y-%m-%d") if trabajador.fecha_nacimiento else "",
    }

    return JsonResponse(data)


def crear_trabajador_view(request):
    if request.method == "POST":
        try:
            # Datos opcionales
            id_afp = request.POST.get("id_afp")
            id_banco = request.POST.get("id_banco")
            id_distrito = request.POST.get("id_distrito")
            sueldo = request.POST.get("sueldo")
            fecha_nacimiento = request.POST.get("fecha_nacimiento")

            # Crear trabajador
            trabajador = Trabajador.objects.create(
                dni=request.POST["dni"],
                first_name=request.POST["first_name"].upper(),
                apellido_pat=request.POST["apellido_pat"].upper(),
                apellido_mat=request.POST["apellido_mat"].upper(),
                ocupacion=request.POST["ocupacion"],
                fec_init=request.POST["fec_init"],
                usuario=request.POST["usuario"],
                contra=request.POST["contra"],
                id_privilegio_id=int(request.POST["id_privilegio"]),
                id_status_tra_id=1,  # Habilitado por defecto
                sueldo=float(sueldo) if sueldo else 0,
                cuenta_bancaria=request.POST.get("cuenta_bancaria") or "",
                celular=request.POST.get("celular") or "",
                fecha_nacimiento=fecha_nacimiento or None,
                id_afp_id=int(id_afp) if id_afp else None,
                id_banco_id=int(id_banco) if id_banco else None,
                id_distrito_id=int(id_distrito) if id_distrito else None,
            )

            messages.success(request, "Trabajador creado con exito.")
        except Exception as e:
            messages.error(request, f"Error al crear trabajador: {str(e)}")

        return redirect("home")


def editar_trabajador(request):
    try:
        # Petición POST (guardar cambios)
        if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
            id_emp = request.POST.get('id_emp')
            logger.info(f'POST AJAX recibido para id_emp={id_emp}')
            trabajador = get_object_or_404(Trabajador, id_emp=id_emp)

            # Actualizar con los datos del formulario
            form = TrabajadorForm(request.POST, instance=trabajador)
            if form.is_valid():
                form.save()
                logger.info(f'Trabajador {id_emp} actualizado correctamente')
                return JsonResponse({'success': True})
            else:
                logger.warning(f'Errores al actualizar trabajador {id_emp}: {form.errors}')
                return JsonResponse({'success': False, 'errors': form.errors})

        # Petición GET AJAX (cargar datos en modal)
        elif request.method == 'GET' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
            id_emp = request.GET.get('id_emp')
            logger.info(f'GET AJAX recibido para id_emp={id_emp}')
            trabajador = get_object_or_404(Trabajador, id_emp=id_emp)

            # Preparar datos para el modal
            data = {
                'id_emp': trabajador.id_emp,
                'dni': trabajador.dni,
                'first_name': trabajador.first_name,
                'apellido_pat': trabajador.apellido_pat,
                'apellido_mat': trabajador.apellido_mat,
                'id_distrito': trabajador.id_distrito.id_distrito if trabajador.id_distrito else '',
                'ocupacion': trabajador.ocupacion,
                'celular': trabajador.celular,
                # Campos que ya estaban
                'fecha_nacimiento': trabajador.fecha_nacimiento.strftime('%Y-%m-%d') if trabajador.fecha_nacimiento else '',
                'sueldo': trabajador.sueldo,
                'cuenta_bancaria': trabajador.cuenta_bancaria,
                'id_privilegio': trabajador.id_privilegio.id_privilegio,
                'id_status_tra': trabajador.id_status_tra.id_status_tra,
                
                # <--- ¡CAMPOS FALTANTES AÑADIDOS AQUÍ! --->
                'fec_init': trabajador.fec_init.strftime('%Y-%m-%d') if trabajador.fec_init else '',
                'usuario': trabajador.usuario,
                'id_afp': trabajador.id_afp.id_afp if trabajador.id_afp else '', # Para seleccionar en el <select>
                'id_banco': trabajador.id_banco.id_banco if trabajador.id_banco else '', # Para seleccionar en el <select>
                # <--- FIN DE CAMPOS FALTANTES --->
            }
            return JsonResponse(data)

        # Si no es AJAX ni POST, redirige a home
        else:
            logger.info('Petición no AJAX a editar_trabajador, redirigiendo a home')
            return redirect('home')

    except Exception as e:
        logger.error(f'Error en editar_trabajador: {str(e)}', exc_info=True)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': str(e)})
        return redirect('home')
        
        
@csrf_exempt
def cambiar_estado_trabajador_view(request):
    if request.method == "POST":
        try:
            trabajador = get_object_or_404(Trabajador, pk=request.POST["id"])
            
            # Si está Habilitado (1) -> Pasa a Deshabilitado (2)
            if trabajador.id_status_tra.id_status_tra == 1:
                trabajador.id_status_tra_id = 2
                # AUTOMATIZACIÓN CLAVE:
                trabajador.fecha_cese = date.today() # Guardamos la fecha de hoy como baja
            
            # Si está Deshabilitado (2) -> Pasa a Habilitado (1)
            else:
                trabajador.id_status_tra_id = 1
                # Opcional: Limpiar la fecha de cese si se reincorpora
                trabajador.fecha_cese = None 
            
            trabajador.save()
            
            estado_str = "Habilitado" if trabajador.id_status_tra.id_status_tra == 1 else "Deshabilitado"
            messages.success(request, f"Estado actualizado correctamente a {estado_str}.")
            
        except Exception as e:
            messages.error(request, f"No se pudo cambiar el estado: {str(e)}")
            
    return redirect("listar_trabajadores") # O 'home', donde prefieras que redirija


def cambiar_contrasena_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        dni = request.POST.get("dni")
        nueva_contrasena = request.POST.get("nueva_contrasena")
        confirmar_contrasena = request.POST.get("confirmar_contrasena")

        if nueva_contrasena != confirmar_contrasena:
            messages.error(request, "Las contrasenas no coinciden")
            return redirect("cambiar_contrasena")

        exito, error = update_pw_creden(username, dni, nueva_contrasena)
        if exito:
            messages.success(request, "Contrasena actualizada con exito")
            return redirect("login")
        else:
            messages.error(request, error)
            return redirect("cambiar_contrasena")

    return render(request, "webApp/cambiar_contrasena.html")


# =============================================================
# 🚧 VISTAS DE ASIGNACIÓN (ÓRDENES DE TRABAJO)
# =============================================================

def crear_asignacion_view(request):
    if request.method == "POST":
        try:
            # --- 1. Obtención y Validación Inicial de Datos ---
            usuario_id = request.session.get("trabajador_id")
            if not usuario_id:
                # Si falla la sesión, devolvemos JSON de error
                return JsonResponse({'success': False, 'message': "⚠️ No hay sesión activa. Inicia sesión de nuevo."}, status=401)

            creador = get_object_or_404(Trabajador, pk=usuario_id)
            id_emp = request.POST.get("id_emp")
            id_maq = request.POST.get("id_maq")
            fecha_asig = request.POST.get("fecha_asig")
            fin_asig = request.POST.get("fin_asig")
            descripcion = request.POST.get("descripcion", "").strip()

            trabajador_asignado = get_object_or_404(Trabajador, pk=id_emp)
            maquina = get_object_or_404(Maquina, pk=id_maq)

            # Convertir fechas
            fecha_asig = datetime.strptime(fecha_asig, "%Y-%m-%d").date()
            fin_asig = datetime.strptime(fin_asig, "%Y-%m-%d").date() if fin_asig else fecha_asig

            # --- 2. Validación de Conflictos y Solapamientos ---
            
            # CORRECCIÓN: Validamos Mantenimiento usando .upper() para robustez
            if maquina.id_estado.estado.upper() == "MANTENIMIENTO":
                return JsonResponse({'success': False, 'message': "❌ La maquinaria seleccionada está en mantenimiento."}, status=400)

            # Validar solapamientos
            solapadas = Asignacion.objects.filter(
                id_maq=maquina,
                fin_asig__gte=fecha_asig,
                fecha_asig__lte=fin_asig
            ).exclude(id_status__nombre__iexact="Completada")

            if solapadas.exists():
                return JsonResponse({'success': False, 'message': "⚠️ Maquinaria con orden de trabajo activa en ese rango de fechas."}, status=400)

            # --- 3. Creación y Actualización de Estado ---
            
            # 1. CAMBIO AQUÍ: Asignamos la creación a una variable 'nueva_asig'
            nueva_asig = Asignacion.objects.create(
                id_emp=trabajador_asignado,
                id_maq=maquina,
                fecha_asig=fecha_asig,
                fin_asig=fin_asig,
                descripcion=descripcion,
                id_creador=creador
            )

            # 2. LÓGICA NUEVA: Generar horas (Lunes a Viernes, 6 horas diarias)
            fecha_cursor = fecha_asig
            fecha_limite = fin_asig

            while fecha_cursor <= fecha_limite:
                # weekday(): 0=Lunes, 1=Martes ... 5=Sábado, 6=Domingo
                if fecha_cursor.weekday() < 5: # Si es menor a 5 (es decir, Lunes a Viernes)
                    RegistroHoras.objects.create(
                        trabajador=trabajador_asignado,
                        asignacion=nueva_asig,
                        fecha=fecha_cursor,
                        horas=6 # 6 Horas fijas
                    )
                # Pasamos al siguiente día
                fecha_cursor += timedelta(days=1)

            # ... (resto de tu código para cambiar estado de máquina y mensajes) ...
            maquina.id_estado = EstadoMaquina.objects.get(estado__iexact="ORDEN DE TRABAJO")
            maquina.save()

            messages.success(request, "✅ Asignación creada y horas registradas correctamente.")
            return JsonResponse({'success': True, 'message': 'Asignación creada y estado actualizado.'})

        except Exception as e:
            logger.error(f"Error al crear asignación: {str(e)}")
            # Devolvemos un error en formato JSON
            return JsonResponse({'success': False, 'message': f"❌ Error interno al crear asignación: {str(e)}"}, status=500)

    # Si la petición no es POST, redirige (comportamiento normal)
    return redirect("listar_asignaciones")


def listar_asignaciones(request):
    trabajador_id = request.session.get("trabajador_id")
    if not trabajador_id:
        return redirect("login")

    trabajador = get_object_or_404(Trabajador, id_emp=trabajador_id)
    privilegio_val = getattr(trabajador.id_privilegio, "id_privilegio", None) if trabajador.id_privilegio else None

    qs = Asignacion.objects.select_related("id_emp", "id_maq", "id_creador", "id_status")

    # Filtro por estado desde GET (?estado=En+Proceso)
    estado_filtro = request.GET.get("estado")
    if estado_filtro:
        qs = qs.filter(id_status__nombre__iexact=estado_filtro)

    # Si es operador (privilegio 3), solo ve sus asignaciones
    if int(privilegio_val or 0) == 3:
        asignaciones = qs.filter(id_emp_id=trabajador.id_emp)
    else:
        # CORRECCIÓN ADICIONAL: Excluir asignaciones del usuario 'docente' para limpiar la vista del Admin
        asignaciones = qs.exclude(id_emp__usuario='docente').all()

    # --- LÓGICA DE LIMPIEZA Y ACTUALIZACIÓN DE ESTADO ---
    hoy = date.today()
    estado_disponible = EstadoMaquina.objects.filter(estado__iexact="DISPONIBLE").first()
    
    for asig in asignaciones:
        if asig.id_status and asig.id_status.nombre.upper() == "COMPLETADA":
            continue 

        fin_asig_date = asig.fin_asig.date() if isinstance(asig.fin_asig, datetime) else asig.fin_asig

        if fin_asig_date and fin_asig_date < hoy:
            if asig.id_maq.id_estado != estado_disponible and estado_disponible:
                asig.id_maq.id_estado = estado_disponible
                asig.id_maq.save()
                
    # --- FILTRADO DE MÁQUINAS DISPONIBLES PARA ASIGNACIÓN ---
    
    maquinas_ocupadas_ids = Asignacion.objects.filter(
        Q(id_status__nombre__iexact="Pendiente") | Q(id_status__nombre__iexact="En Proceso"),
        fin_asig__gte=hoy 
    ).values_list('id_maq', flat=True).distinct()
    
    maquinas_para_asignar = Maquina.objects.exclude(
        Q(id_estado__estado__iexact="Mantenimiento") | Q(id_maq__in=maquinas_ocupadas_ids)
    )

    # --- CORRECCIÓN PRINCIPAL AQUÍ ---
    # Antes: operadores = Trabajador.objects.filter(id_privilegio__id_privilegio=3)
    # Ahora: Filtramos por Privilegio 3 Y Status 1 (Habilitado)
    operadores = Trabajador.objects.filter(
        id_privilegio__id_privilegio=3, 
        id_status_tra__id_status_tra=1  # <--- ESTO ELIMINA A LOS DESHABILITADOS
    ).exclude(usuario='docente').order_by('apellido_pat')

    status_list = StatusAsignacion.objects.all()

    context = {
        "asignaciones": asignaciones,
        "usuario": trabajador,
        "operadores": operadores, # Ahora esta lista solo tiene operadores activos
        "maquinas": maquinas_para_asignar,
        "status_list": status_list,
        "estado_filtro": estado_filtro,
    }

    return render(request, "webApp/asignaciones.html", context)


def cambiar_estado_asignacion(request):
    if request.method == 'POST':
        id_asig = request.POST.get('id_asig')
        id_status = request.POST.get('id_status')
        try:
            
            usuario_id = request.session.get("trabajador_id")
            trabajador_origen = Trabajador.objects.filter(id_emp=usuario_id).first()
            
            # Cargamos la asignación y la máquina asociada
            asignacion = Asignacion.objects.select_related('id_maq').get(id_asig=id_asig)
            nuevo_estado_asig = StatusAsignacion.objects.get(id_status=id_status)
            
            # Guardamos el nombre del nuevo estado de ASIGNACIÓN
            nuevo_estado_asignacion_nombre = nuevo_estado_asig.nombre.upper()
            maquina = asignacion.id_maq

            # 1. Actualizar el estado de la ASIGNACIÓN (Esto siempre funciona)
            asignacion.id_status = nuevo_estado_asig
            asignacion.save()
            
            # 2. LÓGICA DE ACTUALIZACIÓN DE MÁQUINA (Usando IDs para ser infalible)
            
            if nuevo_estado_asignacion_nombre == "EN PROCESO":
                # Asumimos ID=2 para ORDEN DE TRABAJO
                estado_maq_id = 2 
            elif nuevo_estado_asignacion_nombre == "COMPLETADA":
                # Asumimos ID=1 para DISPONIBLE
                estado_maq_id = 1
            else:
                # Si el estado es Pendiente o cualquier otro, no cambiamos la máquina.
                estado_maq_id = None 

            if estado_maq_id is not None:
                # Buscamos el objeto EstadoMaquina por el ID
                estado_maq_nuevo = EstadoMaquina.objects.get(id_estado=estado_maq_id)
                maquina.id_estado = estado_maq_nuevo
                maquina.save()
            
            # --- DISPARADOR DE NOTIFICACIÓN ---
            Notificacion.objects.create(
                usuario_origen=trabajador_origen,
                asignacion=asignacion,
                tipo_evento='ESTADO',
                mensaje=f"cambió el estado de la Asig. #{asignacion.id_asig} a '{nuevo_estado_asig.nombre}'"
            )
            
            return JsonResponse({'success': True})
            
        except Asignacion.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Asignación no encontrada'})
        except StatusAsignacion.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Estado de Asignación inválido.'})
        except EstadoMaquina.DoesNotExist:
            # Captura si los IDs de estado (1 o 2) son incorrectos.
            return JsonResponse({'success': False, 'message': 'Error: Los IDs de estado de Máquina (1 o 2) no existen en la base de datos.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error inesperado al procesar: {str(e)}'})


def subir_foto_asignacion(request, id_asig):
    """
    Recibe la foto de una asignación completada y la sube a Cloudinary.
    """
    
    # 0. Verificar que sea un envío de formulario (POST)
    if request.method != 'POST':
        messages.error(request, 'Acción no permitida (Debe ser POST).')
        return redirect('listar_asignaciones')

    # 1. Autenticación (adaptado a tu sistema de sesión)
    usuario_id = request.session.get("trabajador_id")
    if not usuario_id:
        messages.error(request, "Sesión no válida. Por favor, inicia sesión.")
        return redirect("login")
    
    try:
        trabajador = get_object_or_404(Trabajador, id_emp=usuario_id)
    except Trabajador.DoesNotExist:
        messages.error(request, "Usuario no encontrado.")
        return redirect("login")

    # 2. Verificar permisos de Operador (Privilegio ID 3)
    privilegio_id = getattr(trabajador.id_privilegio, 'id_privilegio', None)
    if privilegio_id != 3:
        messages.error(request, 'No tiene permisos para subir fotos.')
        return redirect('listar_asignaciones')

    # 3. Obtener la asignación específica
    asignacion = get_object_or_404(Asignacion, id_asig=id_asig)

    # 4. Verificar que la asignación esté "Completada" (Status ID 3)
    status_id = getattr(asignacion.id_status, 'id_status', None)
    if status_id != 3:
        messages.error(request, 'Solo puede subir fotos a asignaciones completadas.')
        return redirect('listar_asignaciones')

    # 5. Procesar el formulario con la foto
    form = FotoAsignacionForm(request.POST, request.FILES, instance=asignacion)

    if form.is_valid():
        form.save()
        messages.success(request, 'Foto subida exitosamente.')
        
        # DISPARADOR DE NOTIFICACIÓN
        Notificacion.objects.create(
            usuario_origen=trabajador,
            asignacion=asignacion,
            tipo_evento='FOTO',
            mensaje=f"subió una foto para la Asig. #{asignacion.id_asig}"
        )
    else:
        # Capturamos el error específico del formulario
        error_msg = form.errors.get('foto_finalizada', ['Error desconocido.'])[0]
        messages.error(request, f'Error al subir la foto: {error_msg}')

    # 6. Devolver al usuario a la lista de asignaciones
    return redirect('listar_asignaciones')


def editar_asignacion_view(request, id_asig):
    if request.method == "POST":
        try:
            usuario_id = request.session.get("trabajador_id")
            if not usuario_id:
                return JsonResponse({'success': False, 'message': 'Sesión expirada'})

            # Obtener la asignación a editar
            asignacion = get_object_or_404(Asignacion, pk=id_asig)
            
            # Obtener datos del formulario
            id_emp = request.POST.get("id_emp")
            id_maq = request.POST.get("id_maq")
            fecha_asig_str = request.POST.get("fecha_asig")
            fin_asig_str = request.POST.get("fin_asig")
            descripcion = request.POST.get("descripcion", "").strip()

            # Validar y convertir datos
            trabajador_asignado = get_object_or_404(Trabajador, pk=id_emp)
            maquina = get_object_or_404(Maquina, pk=id_maq)
            
            fecha_asig = datetime.strptime(fecha_asig_str, "%Y-%m-%d").date()
            fin_asig = datetime.strptime(fin_asig_str, "%Y-%m-%d").date() if fin_asig_str else fecha_asig

            # Validar solapamientos (EXCLUYENDO la asignación actual)
            solapadas = Asignacion.objects.filter(
                id_maq=maquina,
                fin_asig__gte=fecha_asig,
                fecha_asig__lte=fin_asig
            ).exclude(id_status__nombre="Completada").exclude(pk=id_asig)

            if solapadas.exists():
                return JsonResponse({'success': False, 'message': '⚠️ Maquinaria ocupada en ese rango de fechas por otra asignación.'})

            # Actualizar campos
            asignacion.id_emp = trabajador_asignado
            asignacion.id_maq = maquina
            asignacion.fecha_asig = fecha_asig
            asignacion.fin_asig = fin_asig
            asignacion.descripcion = descripcion
            
            asignacion.save()

            messages.success(request, "✅ Asignación actualizada correctamente.")
            return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({'success': False, 'message': f"Error: {str(e)}"})

    return JsonResponse({'success': False, 'message': 'Método no permitido'})


# =============================================================
# 🚜 VISTAS DE MAQUINARIA
# =============================================================

def maquinaria_list(request):
    """Vista principal que carga el listado y el template de maquinaria"""
    usuario_id = request.session.get("trabajador_id")
    if not usuario_id:
        return redirect("login")

    # Obtener el trabajador logueado
    usuario = Trabajador.objects.get(id_emp=usuario_id)
    rol = usuario.id_privilegio

    # Cargar datos de maquinaria
    maquinas = Maquina.objects.all()
    estados = EstadoMaquina.objects.all()
    alertas = AlertaMaquinaria.objects.filter(leida=False).order_by('-fecha')

    context = {
        "usuario": usuario,
        "rol": rol,
        "maquinas": maquinas,
        "estados": estados,
        "alertas": alertas,
    }
    return render(request, "webApp/maquinaria.html", context)


def crear_maquinaria_view(request):
    """Crear maquinaria desde formulario"""
    if request.method == "POST":
        try:
            Maquina.objects.create(
                equipo=request.POST.get("equipo"),
                marca=request.POST.get("marca"),
                modelo=request.POST.get("modelo"),
                codigo=request.POST.get("codigo"),
                id_estado_id=int(request.POST.get("id_estado")) if request.POST.get("id_estado") else None,
                ult_mant=request.POST.get("ult_mant") or None,
                consu_combus=float(request.POST.get("consu_combus")) if request.POST.get("consu_combus") else None,
            )
            messages.success(request, "Maquinaria registrada correctamente.")
        except Exception as e:
            messages.error(request, f"Error al crear maquinaria: {str(e)}")

    return redirect("maquinaria_list")


def maquinaria_detalle(request, id_maq):
    maquina = get_object_or_404(Maquina, id_maq=id_maq)
    data = {
        "id_maq": maquina.id_maq,
        "equipo": maquina.equipo,
        "marca": maquina.marca,
        "modelo": maquina.modelo,
        "codigo": maquina.codigo,
        "ult_mant": maquina.ult_mant.strftime("%Y-%m-%d") if maquina.ult_mant else "",
        "consu_combus": str(maquina.consu_combus) if maquina.consu_combus else "",
        "id_estado": maquina.id_estado.id_estado if maquina.id_estado else None,
        "estado": maquina.id_estado.estado if maquina.id_estado else "",
    }
    return JsonResponse(data)


def editar_maquinaria(request):
    if request.method == "POST":
        try:
            maquina = get_object_or_404(Maquina, id_maq=request.POST.get("id_maq"))
            maquina.equipo = request.POST.get("equipo")
            maquina.marca = request.POST.get("marca")
            maquina.modelo = request.POST.get("modelo")
            maquina.codigo = request.POST.get("codigo")
            maquina.ult_mant = request.POST.get("ult_mant") or None
            maquina.consu_combus = request.POST.get("consu_combus") or 0
            maquina.save()
            messages.success(request, "Maquinaria actualizada con éxito.")
        except Exception as e:
            messages.error(request, f"Error al editar maquinaria: {str(e)}")
    return redirect("maquinaria_list")


def toggle_estado_maquinaria(request, id_maq):
    maquina = get_object_or_404(Maquina, id_maq=id_maq)

    # Estados válidos y su rotación
    estados_rotacion = ["ORDEN DE TRABAJO", "DISPONIBLE", "MANTENIMIENTO"]

    if maquina.id_estado:
        try:
            idx = estados_rotacion.index(maquina.id_estado.estado.upper())
            siguiente_estado = estados_rotacion[(idx + 1) % len(estados_rotacion)]
        except ValueError:
            siguiente_estado = "ORDEN DE TRABAJO"
    else:
        siguiente_estado = "ORDEN DE TRABAJO"

    # Buscar el nuevo estado
    nuevo_estado = EstadoMaquina.objects.filter(estado__iexact=siguiente_estado).first()
    if nuevo_estado:
        maquina.id_estado = nuevo_estado
        maquina.save()

        # Obtener el trabajador (usuario logueado, si existe)
        trabajador_id = request.session.get("trabajador_id")
        trabajador = None
        if trabajador_id:
            trabajador = Trabajador.objects.filter(id_emp=trabajador_id).first()

        # Crear la alerta
        mensaje = f"La máquina '{maquina.equipo}' cambió su estado a '{siguiente_estado}'."
        AlertaMaquinaria.objects.create(
            mensaje=mensaje,
            maquina=maquina,
            trabajador=trabajador
        )

        messages.success(request, f"Estado de maquinaria cambiado a {siguiente_estado} y alerta registrada.")
    else:
        messages.error(request, f"No se encontró el estado '{siguiente_estado}' en la base de datos.")

    return redirect("maquinaria_list")
    
    
@csrf_exempt 
def editar_maquinaria_estado(request):
    if request.method == "POST":
        try:
            id_maq = request.POST.get("id_maq")
            id_estado = request.POST.get("id_estado")
            # --- SE IGNORA ult_mant_str YA QUE EL CAMPO FUE ELIMINADO DEL MODAL ---

            maquina = get_object_or_404(Maquina, id_maq=id_maq)
            nuevo_estado = EstadoMaquina.objects.get(id_estado=id_estado)
            
            # --- LÓGICA CLAVE: SI ES MANTENIMIENTO, USAMOS LA FECHA DE HOY ---
            
            if nuevo_estado.estado.upper() == "MANTENIMIENTO":
                maquina.ult_mant = date.today() # Siempre usamos la fecha actual
            
            # Nota: Si el estado no es MANTENIMIENTO, el campo ult_mant no se toca.
            
            maquina.id_estado = nuevo_estado
            maquina.save()
            
            # Obtener el trabajador (usuario logueado) para registrar la alerta
            trabajador_id = request.session.get("trabajador_id")
            trabajador = Trabajador.objects.filter(id_emp=trabajador_id).first()
            
            # Crear la alerta
            mensaje = f"El estado de la máquina '{maquina.equipo}' fue cambiado a '{nuevo_estado.estado}'. "
            if nuevo_estado.estado.upper() == "MANTENIMIENTO":
                 mensaje += f"(Mantenimiento registrado el {maquina.ult_mant})."

            AlertaMaquinaria.objects.create(
                mensaje=mensaje,
                maquina=maquina,
                trabajador=trabajador
            )
            
            return JsonResponse({'success': True, 'estado': nuevo_estado.estado})

        except EstadoMaquina.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Estado inválido o no encontrado en la base de datos.'})
        except Exception as e:
            logger.error(f'Error al editar estado de maquinaria: {str(e)}')
            return JsonResponse({'success': False, 'message': f'Error al guardar: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'})

def capacitaciones_view(request):
    # 1. VERIFICACIÓN DE SESIÓN
    usuario_id = request.session.get("trabajador_id")
    if not usuario_id:
        messages.error(request, "Tu sesión ha expirado.")
        return redirect("login")

    trabajador_actual, rol = obtener_usuario_y_rol(usuario_id)
    if not trabajador_actual:
        return redirect("login")

    # === LÓGICA DE SIMULACIÓN DE ROL ===
    # Si hay un rol simulado en sesión, lo usamos. Si no, usamos el real.
    rol_id_efectivo = request.session.get('rol_simulado', trabajador_actual.id_privilegio.id_privilegio)
    
    # Gestor es Admin (1) o Supervisor (2)
    # Si el profe elige Operador (3), esto será False y verá las Cards.
    es_gestor = int(rol_id_efectivo) in [1, 2]

    # ==============================================================================
    # 🚑 FIX CRÍTICO: DOCENTE EN MODO OPERADOR
    # ==============================================================================
    # Creamos una variable para el template. Por defecto es el usuario real.
    usuario_para_template = trabajador_actual

    # Si es el docente (o admin auditor) Y está simulando ser Operador (Rol 3)
    # y su propio ID no tiene capacitaciones (porque es docente), suplantamos.
    if trabajador_actual.usuario == 'docente' and int(rol_id_efectivo) == 3:
        # Buscamos al primer operador real habilitado para mostrar sus datos de ejemplo
        operador_demo = Trabajador.objects.filter(
            id_privilegio__id_privilegio=3, 
            id_status_tra__id_status_tra=1
        ).first()
        
        if operador_demo:
            usuario_para_template = operador_demo
    # ==============================================================================

    # === LÓGICA DE SOLICITUD (OPERADOR) ===
    if request.method == 'POST' and 'accion_solicitar' in request.POST:
        try:
            id_maq_sol = request.POST.get('id_maq_solicitud')
            
            # Buscamos si ya existe CUALQUIER registro para esta máquina y trabajador
            # IMPORTANTE: Usamos usuario_para_template si estamos probando, pero para guardar
            # se debería usar el real. Sin embargo, el docente no debería guardar datos.
            # Asumimos que si es docente probando, no debería dar click a guardar, o si lo hace,
            # se guardará a su nombre (lo cual es correcto para evitar corromper datos de otros).
            cap_existente = Capacitacion.objects.filter(trabajador=trabajador_actual, maquina_id=id_maq_sol).first()
            
            if cap_existente:
                if cap_existente.estado.id == 3:
                    messages.warning(request, "Ya estás certificado en esta máquina. No puedes solicitarla de nuevo.")
                else:
                    messages.warning(request, "Ya tienes una solicitud en curso o pendiente para esta máquina.")
            else:
                # Si no existe, creamos la solicitud
                estado_pendiente = StatusCapacitacion.objects.get(pk=1) 
                Capacitacion.objects.create(
                    trabajador=trabajador_actual,
                    maquina_id=id_maq_sol,
                    estado=estado_pendiente,
                    fecha_inicio=timezone.now().date(), 
                    fecha_fin=None 
                )
                messages.success(request, "Solicitud enviada al supervisor correctamente.")
            
            return redirect('capacitaciones')
        except Exception as e:
            messages.error(request, f"Error al solicitar: {e}")

    # 2. OBTENER DATOS
    maquinas = Maquina.objects.all().order_by('equipo')
    
    # EXCLUDE: Ocultar al docente de la matriz de capacitación
    trabajadores = Trabajador.objects.filter(id_status_tra__id_status_tra=1).exclude(usuario='docente').order_by('apellido_pat')
    
    capacitaciones_qs = Capacitacion.objects.select_related('estado', 'maquina', 'trabajador').all()
    
    mapa_capacitaciones = {}
    for c in capacitaciones_qs:
        if c.trabajador and c.maquina:
            mapa_capacitaciones[(c.trabajador.id_emp, c.maquina.id_maq)] = c

    hoy = timezone.now().date()
    matriz = []
    
    # Contadores para Stats
    total_caps = 0
    total_completadas = 0

    for t in trabajadores:
        suma_porcentajes = 0
        conteo_capacitaciones = 0
        celdas = []
        for m in maquinas:
            cap = mapa_capacitaciones.get((t.id_emp, m.id_maq))
            progreso_individual = 0
            
            if cap:
                total_caps += 1
                
                # --- CÁLCULO DE PROGRESO ---
                if cap.estado.id == 3: 
                    progreso_individual = 100
                elif cap.estado.id == 1: 
                    progreso_individual = 0
                elif cap.fecha_inicio and cap.fecha_fin:
                    total_dias = (cap.fecha_fin - cap.fecha_inicio).days + 1
                    dias_pasados = (hoy - cap.fecha_inicio).days + 1
                    
                    if total_dias > 0:
                        porcentaje = (dias_pasados / total_dias) * 100
                        progreso_individual = max(0, min(100, int(porcentaje)))
                    else:
                        progreso_individual = 100 if dias_pasados > 0 else 0
                
                # === TRANSICIÓN AUTOMÁTICA ===
                if progreso_individual >= 100:
                    progreso_individual = 100
                    # Nota: Aquí modificamos el objeto en memoria para mostrarlo completado
                    # Si quisiéramos persistirlo, haríamos cap.save(), pero en un GET es delicado.
                    cap.estado.id = 3
                    cap.estado.nombre = 'Completado'

                if cap.estado.id == 3:
                    total_completadas += 1

                cap.progreso_temp = progreso_individual
                suma_porcentajes += progreso_individual
                conteo_capacitaciones += 1

            celdas.append({
                'maquina_id': m.id_maq,
                'maquina_nombre': f"{m.equipo} ({m.marca})",
                'modelo': m.modelo,
                'capacitacion': cap
            })

        promedio_general = 0
        if conteo_capacitaciones > 0:
            promedio_general = int(suma_porcentajes / conteo_capacitaciones)

        matriz.append({
            'trabajador': t,
            'celdas': celdas,
            'promedio_general': promedio_general
        })

    # 4. PROCESAR FORMULARIO ADMIN (GUARDAR)
    if request.method == 'POST' and es_gestor and 'guardar_capacitacion' in request.POST:
        try:
            id_cap = request.POST.get('id_capacitacion')
            fecha_inicio_str = request.POST.get('fecha_inicio')
            fecha_fin_str = request.POST.get('fecha_fin')
            observacion = request.POST.get('observacion', '')

            id_emp = request.POST.get('id_emp') or request.POST.get('id_emp_manual')
            id_maq = request.POST.get('id_maq') or request.POST.get('id_maq_manual')

            if not id_emp or not id_maq:
                messages.error(request, "Error: Selección inválida.")
                return redirect('capacitaciones')

            f_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
            f_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date() if fecha_fin_str else None
            
            # Lógica estado automático al guardar
            if f_fin and hoy > f_fin: 
                 id_estado_auto = 3 # Completado
            elif hoy < f_inicio:
                 id_estado_auto = 1 # Pendiente
            else:
                 id_estado_auto = 2 # En Curso

            estado_obj = StatusCapacitacion.objects.get(pk=id_estado_auto)

            if id_cap: 
                cap = Capacitacion.objects.get(pk=id_cap)
                cap.estado = estado_obj
                cap.fecha_inicio = fecha_inicio_str
                cap.fecha_fin = fecha_fin_str if fecha_fin_str else None
                cap.observacion = observacion
                cap.save()
                messages.success(request, "Capacitación actualizada.")
            else:
                if not Capacitacion.objects.filter(trabajador_id=id_emp, maquina_id=id_maq).exists():
                    Capacitacion.objects.create(
                        trabajador_id=id_emp,
                        maquina_id=id_maq,
                        estado=estado_obj,
                        fecha_inicio=fecha_inicio_str,
                        fecha_fin=fecha_fin_str if fecha_fin_str else None,
                        observacion=observacion
                    )
                    messages.success(request, "Asignación creada.")
                else:
                    messages.warning(request, "El trabajador ya tiene asignada esta máquina.")

            return redirect('capacitaciones')

        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    # Objeto Rol simulado (para pasarlo al template si es necesario)
    try:
        rol_obj = Privilegio.objects.get(pk=int(rol_id_efectivo))
    except:
        rol_obj = trabajador_actual.id_privilegio

    context = {
        'usuario': usuario_para_template, # <--- AQUÍ PASAMOS EL USUARIO SUPLANTADO SI ES DOCENTE EN MODO OPERADOR
        'rol': rol_obj,
        'es_gestor': es_gestor,
        'maquinas_header': maquinas,
        'matriz': matriz,
        'total_caps': total_caps,
        'total_completadas': total_completadas,
    }
    return render(request, 'webApp/capacitaciones.html', context)

# =============================================================
# 📜 VISTAS DE LOG Y NOTIFICACIONES
# =============================================================

def historial_login_view(request):
    usuario_id = request.session.get("trabajador_id")
    if not usuario_id:
        return redirect("login")

    trabajador, rol = obtener_usuario_y_rol(usuario_id)
    if not trabajador or not trabajador.id_privilegio or trabajador.id_privilegio.id_privilegio != 1:
        messages.error(request, "No tienes permisos para ver esta página.")
        return redirect("home")

    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    historial = HistorialLogin.objects.select_related('trabajador').all()

    if fecha_inicio:
        try:
            inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            historial = historial.filter(timestamp__gte=inicio_dt)
        except ValueError:
            messages.error(request, "Formato de fecha de inicio inválido.")
            fecha_inicio = None

    if fecha_fin:
        try:
            fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d') + timedelta(days=1)
            historial = historial.filter(timestamp__lt=fin_dt)
        except ValueError:
            messages.error(request, "Formato de fecha de fin inválido.")
            fecha_fin = None

    context = {
        'usuario': trabajador,
        'rol': rol,
        'historial': historial,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
    }
    
    return render(request, 'webApp/historial_login.html', context)


def notificaciones_view(request):
    notificaciones = []

    # === Notificaciones de MAQUINARIA ===
    for m in Maquina.objects.select_related('id_estado').all():
        if m.id_estado:
            notificaciones.append({
                'tipo': 'maquinaria',
                'mensaje': f"La maquinaria '{m.equipo}' está en estado '{m.id_estado.estado}'.",
                'fecha': m.ult_mant or timezone.now(),
                'url': '/maquinaria_list/',
            })
        # Verifica si necesita mantenimiento
        if m.necesita_mantenimiento():
            notificaciones.append({
                'tipo': 'mantenimiento',
                'mensaje': f"La maquinaria '{m.equipo}' requiere mantenimiento preventivo.",
                'fecha': m.ult_mant or timezone.now(),
                'url': '/maquinaria_list/',
            })

    # === Notificaciones de ÓRDENES DE TRABAJO ===
    for a in Asignacion.objects.select_related('id_maq', 'id_status', 'id_emp').all():
        if a.id_status and a.id_maq:
            notificaciones.append({
                'tipo': 'orden',
                'mensaje': f"La orden de trabajo #{a.id_asig} para '{a.id_maq.equipo}' está en estado '{a.id_status.nombre}'.",
                'fecha': a.fecha_asig,
                'url': '/listar_asignaciones/',
            })

    # === Alertas automáticas registradas ===
    for alerta in AlertaMaquinaria.objects.select_related('maquina').all():
        notificaciones.append({
            'tipo': 'maquinaria',
            'mensaje': f"[Alerta] {alerta.mensaje}",
            'fecha': alerta.fecha,
            'url': '/maquinaria_list/',
        })

    # Ordenamos todas las notificaciones por fecha descendente
    notificaciones.sort(key=lambda x: x['fecha'], reverse=True)

    return render(request, 'webApp/notificaciones.html', {
        'notificaciones': notificaciones
    })
    
    
def exportar_backup_csv(request):
    fecha = timezone.now().strftime("%Y%m%d_%H%M")
    filename = f"backup_{fecha}.csv"

    response = HttpResponse(
        content_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

    writer = csv.writer(response)
    writer.writerow(["tabla", "id", "datos"])

    # ---------- TRABAJADORES ----------
    for t in Trabajador.objects.all():
        nombre = f"{t.first_name} {t.apellido_pat} {t.apellido_mat}"
        writer.writerow(["trabajador", t.id_emp, nombre])

    # ---------- MAQUINAS ----------
    for m in Maquina.objects.all():
        nombre = f"{m.equipo} {m.marca or ''} {m.modelo or ''}".strip()
        writer.writerow(["maquina", m.id_maq, nombre])

    # ---------- ASIGNACIONES ----------
    for a in Asignacion.objects.all():
        writer.writerow(["asignacion", a.id_asig, a.id_emp_id])

    # ---------- NOTIFICACIONES ----------
    for n in Notificacion.objects.all():
        writer.writerow(["notificacion", n.id, n.mensaje])

    # ---------- HISTORIAL LOGIN ----------
    for h in HistorialLogin.objects.all():
        writer.writerow(["historial_login", h.id, h.timestamp])

    return response
    
    
def exportar_backup_json(request):
    data = {
        "trabajadores": [],
        "maquinas": [],
        "asignaciones": [],
        "notificaciones": [],
        "historial_login": []
    }

    # -------- TRABAJADORES --------
    for t in Trabajador.objects.all():
        data["trabajadores"].append({
            "id": t.id_emp,
            "nombre_completo": f"{t.first_name} {t.apellido_pat} {t.apellido_mat}"
        })

    # -------- MAQUINAS --------
    for m in Maquina.objects.all():
        data["maquinas"].append({
            "id": m.id_maq,
            "maquina": f"{m.equipo} {m.marca or ''} {m.modelo or ''}".strip()
        })

    # -------- ASIGNACIONES --------
    for a in Asignacion.objects.all():
        data["asignaciones"].append({
            "id": a.id_asig,
            "trabajador": a.id_emp_id
        })

    # -------- NOTIFICACIONES --------
    for n in Notificacion.objects.all():
        data["notificaciones"].append({
            "id": n.id,
            "mensaje": n.mensaje
        })

    # -------- HISTORIAL LOGIN --------
    for h in HistorialLogin.objects.all():
        data["historial_login"].append({
            "id": h.id,
            "timestamp": str(h.timestamp)
        })

    return JsonResponse(data, json_dumps_params={"indent": 2})


# ⬇️ ESTA FUNCIÓN DEBE IR AFUERA, NO ADENTRO ⬇️
def backup_view(request):
    return render(request, "webApp/backup.html")

def api_strategic_drilldown(request):
    """
    API para manejar el Drill-down de Estrategia en el Dashboard.
    """
    # --- CORRECCIÓN SEGURIDAD: Solo usuarios logueados ---
    if not request.session.get("trabajador_id"):
        return JsonResponse({'error': 'No autorizado'}, status=401)
    # ----------------------------------------------------

    nivel = request.GET.get('nivel', '0')
    marca_seleccionada = request.GET.get('marca', None)
    
    anio_actual = timezone.now().year
    
    try:
        if nivel == '0':
            data_marcas = (
                RegistroHoras.objects
                .filter(fecha__year=anio_actual)
                .values('asignacion__id_maq__marca') 
                .annotate(total_horas=Sum('horas'))
                .order_by('-total_horas')
            )
            
            labels = []
            series = []
            
            for d in data_marcas:
                marca = d['asignacion__id_maq__marca'] or "Genérico"
                labels.append(marca)
                series.append(d['total_horas'])
                
            return JsonResponse({
                'titulo': f'Participación por Marca ({anio_actual})',
                'tipo': 'pie',
                'labels': labels,
                'series': series
            })

        elif nivel == '1' and marca_seleccionada:
            data_maquinas = (
                RegistroHoras.objects
                .filter(
                    fecha__year=anio_actual,
                    asignacion__id_maq__marca=marca_seleccionada
                )
                .values('asignacion__id_maq__equipo') 
                .annotate(total_horas=Sum('horas'))
                .order_by('-total_horas')
            )
            
            labels = []
            series_data = []
            
            for d in data_maquinas:
                labels.append(d['asignacion__id_maq__equipo'])
                series_data.append(d['total_horas'])
                
            return JsonResponse({
                'titulo': f'Rendimiento Flota: {marca_seleccionada}',
                'tipo': 'bar',
                'labels': labels,
                'series': [{'name': 'Horas Trabajadas', 'data': series_data}]
            })
            
        return JsonResponse({'error': 'Parámetros incorrectos'}, status=400)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
        
# =========================================================
# FUNCIÓN DE CAMBIO DE ROL PARA EL AUDITOR (DOCENTE)
# =========================================================
def cambiar_rol_auditor(request, rol_id):
    """
    Permite al usuario 'docente' cambiar su rol simulado en la sesión.
    """
    usuario_id = request.session.get("trabajador_id")
    if not usuario_id:
        return redirect("login")
    
    # Verificación de seguridad: Solo el usuario 'docente' puede hacer esto
    try:
        trabajador = Trabajador.objects.get(pk=usuario_id)
        if trabajador.usuario != 'docente': 
            return redirect("home") 
    except:
        return redirect("login")

    # Guardamos el rol simulado en la sesión (1=Admin, 2=Supervisor, 3=Operador)
    request.session['rol_simulado'] = int(rol_id)
    
    # Redirigir a la misma página donde estaba
    return redirect(request.META.get('HTTP_REFERER', 'home'))