# Imports the create_app() function defined in app/app.py (. means from the same package).
from .app import create_app
# This is the flask application object used by the Gunicorn: gunicorn app:app
app = create_app() # This makes the flask app discoverable for Gunicorn

