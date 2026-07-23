from django import forms
from webApp.models.encuesta import Encuesta

class EncuestaForm(forms.ModelForm):
    class Meta:
        model = Encuesta
        fields = ['tiempo_empleo', 'es_relacionado', 'calificacion_prep', 'competencias', 'recomendaria']
        
        widgets = {
            'tiempo_empleo': forms.Select(choices=[
                ('inmediato', 'Inmediatamente'),
                ('1-3 meses', '1 a 3 meses'),
                ('3-6 meses', '3 a 6 meses'),
                ('+6 meses', 'Más de 6 meses')
            ], attrs={'class': 'form-input'}),
            
            'es_relacionado': forms.Select(choices=[('Si', 'Sí'), ('No', 'No')], attrs={'class': 'form-input'}),
            'calificacion_prep': forms.NumberInput(attrs={'class': 'form-input', 'min': 1, 'max': 5}),
            'competencias': forms.Textarea(attrs={'class': 'form-input', 'rows': 3}),
            'recomendaria': forms.Select(choices=[('Si', 'Sí'), ('No', 'No')], attrs={'class': 'form-input'}),
        }