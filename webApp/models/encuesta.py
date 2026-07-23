from django.db import models
from webApp.models.egresado import Egresado

class Encuesta(models.Model):
    # Relación Uno a Uno: Un egresado = Una encuesta
    egresado = models.OneToOneField(Egresado, on_delete=models.CASCADE)
    
    # Preguntas del Caso Práctico
    tiempo_empleo = models.CharField(max_length=50, verbose_name="Tiempo en conseguir empleo")
    es_relacionado = models.CharField(max_length=2, verbose_name="¿Trabajo relacionado con carrera?") # Si/No
    calificacion_prep = models.IntegerField(verbose_name="Calificación de la preparación (1-5)")
    competencias = models.TextField(verbose_name="Competencias adicionales necesarias")
    recomendaria = models.CharField(max_length=2, verbose_name="¿Recomendaría la universidad?") # Si/No
    
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Encuesta de {self.egresado}"