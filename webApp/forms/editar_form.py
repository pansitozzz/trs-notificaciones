from django import forms
from webApp.models.usuario_model import Trabajador

class TrabajadorForm(forms.ModelForm):
    class Meta:
        model = Trabajador
        fields = [
            'ocupacion', 
            'id_status_tra', 
            'id_privilegio', 
            'sueldo', 
            'cuenta_bancaria', 
            'celular', 
            'id_afp', 
            'id_banco', 
            'id_distrito'
        ]