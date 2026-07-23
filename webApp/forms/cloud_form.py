# webApp/forms/cloud_form.py

from django import forms
# Importamos el modelo desde su ubicación
from ..models.usuario_model import Asignacion 

class FotoAsignacionForm(forms.ModelForm):
    class Meta:
        model = Asignacion
        fields = ['foto_finalizada']
        widgets = {
            'foto_finalizada': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
        }
        labels = {
            'foto_finalizada': 'Seleccionar imagen de finalización',
        }