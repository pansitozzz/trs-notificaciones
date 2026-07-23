from django.db import models
from datetime import date, timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from cloudinary.models import CloudinaryField

# =========================================================
# 1. TABLAS MAESTRAS (STATUS, TIPOS, ETC.)
# =========================================================

class StatusTra(models.Model):
    id_status_tra = models.AutoField(primary_key=True)
    status_tra = models.CharField(max_length=50)
    class Meta:
        db_table = 'status_tra'
        managed = False
    def __str__(self):
        return self.status_tra

class Privilegio(models.Model):
    id_privilegio = models.AutoField(primary_key=True)
    privilegio = models.CharField(max_length=50)
    class Meta:
        db_table = 'privilegios'
        managed = False
    def __str__(self):
        return self.privilegio

class AFP(models.Model):
    id_afp = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)
    class Meta:
        db_table = 'afp'
        managed = False
    def __str__(self):
        return self.nombre

class Banco(models.Model):
    id_banco = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)
    class Meta:
        db_table = 'banco'
        managed = False
    def __str__(self):
        return self.nombre

class DistritoResidencia(models.Model):
    id_distrito = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)
    class Meta:
        db_table = 'distrito_residencia'
        managed = False
    def __str__(self):
        return self.nombre

class EstadoMaquina(models.Model):
    id_estado = models.AutoField(primary_key=True)
    estado = models.CharField(max_length=50)
    class Meta:
        db_table = 'status_maq'
        managed = False
    def __str__(self):
        return self.estado

class StatusAsignacion(models.Model):
    id_status = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)
    class Meta:
        db_table = 'status_asig'
        managed = False
        verbose_name = 'Estado de Asignación'
        verbose_name_plural = 'Estados de Asignaciones'
    def __str__(self):
        return self.nombre

# --- CORRECCIÓN AQUÍ: Usamos 'id' que es lo que hay en la BD ---
class StatusCapacitacion(models.Model):
    id = models.BigAutoField(primary_key=True) # Cambiado de id_status a id
    nombre = models.CharField(max_length=50)
    
    class Meta:
        db_table = "webApp_statuscapacitacion"
        managed = False # Ya existe en la BD, así que False para no migrarla

    def __str__(self):
        return self.nombre
# ---------------------------------------------------------------


# =========================================================
# 2. ENTIDADES PRINCIPALES (TRABAJADOR, MAQUINA)
# =========================================================

class Trabajador(models.Model):
    id_emp = models.AutoField(primary_key=True)
    dni = models.CharField(max_length=15)
    first_name = models.CharField(max_length=100)
    apellido_pat = models.CharField(max_length=100)
    apellido_mat = models.CharField(max_length=100)
    ocupacion = models.CharField(max_length=100)
    fec_init = models.DateField()
    usuario = models.CharField(max_length=100)
    contra = models.CharField(max_length=100)

    # Relaciones
    id_status_tra = models.ForeignKey(StatusTra, on_delete=models.CASCADE, db_column="id_status_tra")
    id_privilegio = models.ForeignKey(Privilegio, on_delete=models.CASCADE, db_column="id_privilegio")
    id_afp = models.ForeignKey(AFP, on_delete=models.CASCADE, db_column="id_afp", null=True, blank=True)
    id_banco = models.ForeignKey(Banco, on_delete=models.CASCADE, db_column="id_banco", null=True, blank=True)
    id_distrito = models.ForeignKey(DistritoResidencia, on_delete=models.CASCADE, db_column="id_distrito", null=True, blank=True)

    # Otros campos
    sueldo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cuenta_bancaria = models.CharField(max_length=50, null=True, blank=True)
    celular = models.CharField(max_length=15, null=True, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    
    # === [NUEVO] CAMPO PARA US-011 (RRHH) ===
    fecha_cese = models.DateField(null=True, blank=True, verbose_name="Fecha de Cese")
    # ========================================

    class Meta:
        db_table = 'webApp_trabajador'
        managed = False

    def __str__(self):
        return f"{self.first_name} {self.apellido_pat}"

class Maquina(models.Model):
    id_maq = models.AutoField(primary_key=True)
    equipo = models.CharField(max_length=100)
    marca = models.CharField(max_length=100, blank=True, null=True)
    modelo = models.CharField(max_length=100, blank=True, null=True)
    codigo = models.CharField(max_length=50, blank=True, null=True)
    
    id_estado = models.ForeignKey(
        EstadoMaquina,
        on_delete=models.SET_NULL,
        db_column='id_estado',
        null=True,
        blank=True
    )
    
    ult_mant = models.DateField(blank=True, null=True)
    consu_combus = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    
    # === [NUEVOS] CAMPOS PARA US-018 (GERENCIA FLOTA) ===
    anio_fabricacion = models.IntegerField(default=2020, verbose_name="Año Fabricación")
    vida_util_estimada = models.IntegerField(default=10, verbose_name="Vida Útil (Años)")
    costo_mantenimiento = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Costo Mantenimiento")
    # ====================================================

    class Meta:
        db_table = 'maquinaria'
        managed = False

    def __str__(self):
        return f"{self.equipo} ({self.marca} {self.modelo})"

    def proximo_mantenimiento(self):
        if self.ult_mant:
            return self.ult_mant + timedelta(days=180)
        return None

    def necesita_mantenimiento(self):
        proximo = self.proximo_mantenimiento()
        if proximo:
            return date.today() >= proximo
        return True


# =========================================================
# 3. OPERACIONES (ASIGNACIONES, HORAS)
# =========================================================

class Asignacion(models.Model):
    id_asig = models.AutoField(primary_key=True)
    id_emp = models.ForeignKey('Trabajador', db_column='id_emp', on_delete=models.CASCADE, related_name='asignaciones_recibidas')
    id_maq = models.ForeignKey('Maquina', db_column='id_maq', on_delete=models.CASCADE, related_name='asignaciones')
    fecha_asig = models.DateField(db_column='fecha_asig')
    fin_asig = models.DateField(db_column='fin_asig', null=True, blank=True)
    descripcion = models.TextField(db_column='descripcion', blank=True, null=True)
    id_creador = models.ForeignKey('Trabajador', db_column='id_creador', on_delete=models.SET_NULL, null=True, blank=True, related_name='asignaciones_creadas')
    id_status = models.ForeignKey('StatusAsignacion', db_column='id_status', on_delete=models.SET_NULL, null=True, blank=True)
    
    foto_finalizada = CloudinaryField(
        'imagen_finalizacion',
        null=True,
        blank=True,
        folder='trs_maquinaria/finalizadas/'
    )

    class Meta:
        db_table = 'asignacion'
        managed = False
        ordering = ['-fecha_asig']

    def __str__(self):
        return f"Asignación #{self.id_asig}"

class RegistroHoras(models.Model):
    id_registro = models.AutoField(primary_key=True)
    trabajador = models.ForeignKey('Trabajador', on_delete=models.CASCADE, related_name='registrohoras')
    asignacion = models.ForeignKey('Asignacion', on_delete=models.CASCADE)
    fecha = models.DateField()
    horas = models.IntegerField(default=6) # Por defecto 6 horas

    class Meta:
        db_table = 'registro_horas'
        managed = False

    def __str__(self):
        return f"{self.trabajador} - {self.fecha} - {self.horas}hrs"


# =========================================================
# 4. CAPACITACIONES (MATRIZ DE HABILIDADES)
# =========================================================

class Capacitacion(models.Model):
    id_capacitacion = models.AutoField(primary_key=True)
    
    # Relación con el trabajador
    trabajador = models.ForeignKey(
        'Trabajador',
        on_delete=models.CASCADE,
        db_column='id_emp',
        db_constraint=False 
    )

    # Relación con la máquina
    maquina = models.ForeignKey(
        'Maquina',
        on_delete=models.CASCADE,
        db_column='id_maq',
        null=True, 
        blank=True,
        db_constraint=False
    )

    # Relación con Estado (Ahora apunta al modelo corregido StatusCapacitacion con 'id')
    estado = models.ForeignKey(
        StatusCapacitacion,
        on_delete=models.CASCADE,
        db_column='estado_id'
    )
    
    fecha_inicio = models.DateField(default=timezone.now)
    fecha_fin = models.DateField(null=True, blank=True)
    observacion = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "webApp_capacitacion"
        managed = False

    def __str__(self):
        return f"{self.trabajador} - {self.maquina} ({self.estado})"


# =========================================================
# 5. SISTEMA Y ALERTAS
# =========================================================

class AlertaMaquinaria(models.Model):
    id_alerta = models.AutoField(primary_key=True)
    mensaje = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    leida = models.BooleanField(default=False)
    maquina = models.ForeignKey('Maquina', db_column='id_maq', on_delete=models.CASCADE)
    trabajador = models.ForeignKey('Trabajador', db_column='id_emp', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'alertas_maquinaria'
        managed = False 

class Notificacion(models.Model):
    id = models.AutoField(primary_key=True)
    usuario_origen = models.ForeignKey('Trabajador', on_delete=models.SET_NULL, null=True, blank=True, related_name='notificaciones_creadas')
    asignacion = models.ForeignKey('Asignacion', on_delete=models.CASCADE, null=True, blank=True, related_name='notificaciones')
    tipo_evento = models.CharField(max_length=50, db_index=True) 
    mensaje = models.CharField(max_length=255)
    leida = models.BooleanField(default=False, db_index=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'notificaciones_eventos' 
        ordering = ['-fecha_creacion']
        verbose_name = 'Notificación de Evento'
        verbose_name_plural = 'Notificaciones de Eventos'
        managed = False

    def __str__(self):
        return f"Notificación: {self.mensaje}"

class HistorialLogin(models.Model):
    id = models.AutoField(primary_key=True)
    trabajador = models.ForeignKey(Trabajador, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora")
    ip_address = models.GenericIPAddressField(verbose_name="Dirección IP", null=True, blank=True)
    user_agent = models.TextField(verbose_name="Dispositivo/Navegador", null=True, blank=True)

    def __str__(self):
        nombre = self.trabajador.first_name if self.trabajador else "Usuario desconocido"
        return f"Login de {nombre} en {self.timestamp}"

    class Meta:
        verbose_name = "Historial de Login"
        verbose_name_plural = "Historiales de Login"
        ordering = ['-timestamp']
        managed = False
        


       

