from django.db import models
from django.contrib.auth.models import User

class Egresado(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    
    nombres = models.CharField(max_length=255, blank=True, null=False)
    apellidos = models.CharField(max_length=255, blank=True, null=False)
    
    # --- CORRECCIÓN AQUÍ: Cambiamos 'email' por 'correo' ---
    correo = models.CharField(max_length=255, blank=True, null=False) 
    
    # Datos Académicos
    codigo_alumno = models.CharField(max_length=20, unique=True)
    carrera = models.CharField(max_length=100)
    anio_egreso = models.IntegerField()
    
    # Información Laboral
    empresa_actual = models.CharField(max_length=100, blank=True)
    cargo = models.CharField(max_length=100, blank=True)
    linkedin_url = models.URLField(blank=True, null=True)
    
    telefono = models.CharField(max_length=15, blank=True, null=True)

    class Meta:
        verbose_name = "Egresado"
        verbose_name_plural = "Egresados"

    def __str__(self):
        return f"{self.codigo_alumno} - {self.carrera}"