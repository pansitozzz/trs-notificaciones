import os
import sys

# Ruta absoluta del proyecto en el servidor de hosting (cPanel).
# Ajusta estas dos rutas a las de tu propia cuenta de hosting.
project_path = os.environ.get('TRS_PROJECT_PATH', os.path.dirname(os.path.abspath(__file__)))
if project_path not in sys.path:
    sys.path.insert(0, project_path)

activate_this = os.environ.get('TRS_VENV_ACTIVATE_PATH')
if activate_this and os.path.exists(activate_this):
    with open(activate_this) as file_:
        exec(file_.read(), dict(__file__=activate_this))

# Configuración de Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "IngSoftware.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()