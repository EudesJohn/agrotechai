"""
Vercel serverless entry point for the PlantGuard Django API.
Wraps the WSGI application using Mangum (serverless adapter).
"""
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'plantguard.settings')

from mangum import Mangum
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
handler = Mangum(application)
