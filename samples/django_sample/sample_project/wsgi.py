import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "samples.django_sample.sample_project.settings")

application = get_wsgi_application()
