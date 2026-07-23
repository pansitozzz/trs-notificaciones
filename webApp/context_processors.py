# webApp/context_processors.py

# IMPORTAMOS EL NUEVO MODELO
from webApp.models.usuario_model import Maquina, AlertaMaquinaria, Asignacion, Notificacion

def global_notificaciones(request):
    """
    Context processor para cargar notificaciones en todas las páginas.
    """
    # Solo ejecutar si el usuario está logueado
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return {}

    # 1. Alertas de Mantenimiento Próximo (de home.html)
    alertas_mantenimiento = list(
        m for m in Maquina.objects.all() if m.necesita_mantenimiento()
    )

    # 2. Historial de Alertas (de maquinaria.html)
    alertas_historial = AlertaMaquinaria.objects.filter(leida=False).order_by('-fecha')[:10]

    # 3. Alertas de Órdenes de Trabajo (de asignaciones.html)
    alertas_asignaciones = Asignacion.objects.filter(
        id_status__nombre__iexact='Pendiente'
    ).order_by('-fecha_asig')[:5]

    # ===============================================
    # === 4. NUEVAS NOTIFICACIONES DE EVENTOS (AÑADIDO) ===
    # ===============================================
    # Buscamos las 10 notificaciones de eventos más recientes no leídas
    # (Excluimos las del propio usuario para no notificarle de sus acciones)
    alertas_eventos = Notificacion.objects.filter(
        leida=False
    ).exclude(
        usuario_origen_id=usuario_id
    ).select_related('usuario_origen', 'asignacion').order_by('-fecha_creacion')[:10]
    
    # Contamos solo las que no son del usuario actual
    total_eventos_nuevos = alertas_eventos.count()
    # ===============================================


    # 5. Calcular el total (MODIFICADO)
    total_notificaciones = (
        len(alertas_mantenimiento) + 
        alertas_historial.count() + 
        alertas_asignaciones.count() +
        total_eventos_nuevos # <-- SUMAMOS EL NUEVO CONTEO
    )

    # Devolver el diccionario de contexto
    return {
        'global_alertas_mantenimiento': alertas_mantenimiento,
        'global_alertas_historial': alertas_historial,
        'global_alertas_asignaciones': alertas_asignaciones,
        
        # --- NUEVOS DATOS PARA EL TEMPLATE ---
        'global_alertas_eventos': alertas_eventos,
        # 'global_total_notificaciones' ahora incluye el nuevo conteo
        'global_total_notificaciones': total_notificaciones,
    }