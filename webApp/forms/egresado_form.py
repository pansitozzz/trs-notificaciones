from django import forms
from webApp.models.egresado import Egresado

class EgresadoForm(forms.ModelForm):
    # Agregamos campos "extra" que irán a la tabla User
    nombres = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    apellidos = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Egresado
        # Agregamos 'telefono' a la lista
        fields = ['nombres', 'apellidos', 'email', 'telefono', 'codigo_alumno', 'carrera', 'anio_egreso', 'empresa_actual', 'cargo', 'linkedin_url']
        
        widgets = {
            'codigo_alumno': forms.TextInput(attrs={'class': 'form-control'}),
            'carrera': forms.TextInput(attrs={'class': 'form-control'}),
            'anio_egreso': forms.NumberInput(attrs={'class': 'form-control'}),
            'empresa_actual': forms.TextInput(attrs={'class': 'form-control'}),
            'cargo': forms.TextInput(attrs={'class': 'form-control'}),
            'linkedin_url': forms.URLInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 999-999-999'}),
        }
    
    # Esto ordena los campos para que salgan bonitos en el HTML
    field_order = ['nombres', 'apellidos', 'email', 'telefono', 'codigo_alumno', 'carrera', 'anio_egreso']