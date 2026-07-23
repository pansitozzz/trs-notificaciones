from django import forms

class LoginForm(forms.Form):
    usuario = forms.CharField(
        label="Usuario",
        max_length=20,
        widget=forms.TextInput(attrs={'placeholder': 'Usuario'})
    )
    contra = forms.CharField(
        label="Contraseña",
        max_length=15,
        widget=forms.PasswordInput(attrs={'placeholder': 'Contraseña'})
    )
