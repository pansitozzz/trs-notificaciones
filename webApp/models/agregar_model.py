# from django.db import models


# class StatusTra(models.Model):
#     nombre = models.CharField(max_length=50)

#     def __str__(self):
#         return self.nombre


# class Privilegio(models.Model):
#     nombre = models.CharField(max_length=50)

#     def __str__(self):
#         return self.nombre


# class Trabajador(models.Model):
#     dni = models.CharField(max_length=8, unique=True)
#     first_name = models.CharField(max_length=50)
#     apellido_pat = models.CharField(max_length=50)
#     apellido_mat = models.CharField(max_length=50)
#     ocupacion = models.CharField(max_length=100)
#     fec_init = models.DateField()
#     usuario = models.CharField(max_length=50)
#     contra = models.CharField(max_length=200)
#     id_status_tra = models.ForeignKey(StatusTra, on_delete=models.SET_NULL, null=True, blank=True)
#     id_privilegio = models.ForeignKey(Privilegio, on_delete=models.SET_NULL, null=True, blank=True)

#     def __str__(self):
#         return f"{self.first_name} {self.apellido_pat}"
