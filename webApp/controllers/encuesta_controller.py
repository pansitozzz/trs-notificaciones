from django.shortcuts import render, redirect, get_object_or_404
from webApp.models.egresado import Egresado
from webApp.forms.encuesta_form import EncuestaForm
from django.contrib import messages

def realizar_encuesta(request, id):
    egresado = get_object_or_404(Egresado, id=id)

    # Validación de Seguridad: ¿Ya tiene encuesta?
    # Si intentan entrar por URL directa a una encuesta hecha, los botamos
    if hasattr(egresado, 'encuesta'):
        messages.warning(request, f'El egresado {egresado.nombres} ya completó la encuesta.')
        return redirect('registro_egresado')

    if request.method == 'POST':
        form = EncuestaForm(request.POST)
        if form.is_valid():
            encuesta = form.save(commit=False)
            encuesta.egresado = egresado # Vinculamos la encuesta al alumno
            encuesta.save()
            
            messages.success(request, f'✅ Encuesta registrada para {egresado.nombres}')
            return redirect('registro_egresado')
    else:
        form = EncuestaForm()

    return render(request, 'webApp/realizar_encuesta.html', {'form': form, 'egresado': egresado})