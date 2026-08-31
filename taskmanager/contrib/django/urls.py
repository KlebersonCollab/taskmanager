from __future__ import annotations

from pathlib import Path

try:
    from django.http import FileResponse, HttpResponse
    from django.urls import path
    DJANGO_AVAILABLE = True
except ImportError:
    DJANGO_AVAILABLE = False


app_name = "taskmanager"


def dashboard_view(request):
    """Serves the TaskManager SPA dashboard in standard Django setups."""
    ui_dir = Path(__file__).resolve().parent.parent.parent / "ui"
    index_file = ui_dir / "index.html"
    if index_file.exists():
        return FileResponse(open(index_file, "rb"), content_type="text/html")
    return HttpResponse("TaskManager Dashboard UI not found.", status=404)


if DJANGO_AVAILABLE:
    urlpatterns = [
        path("", dashboard_view, name="dashboard"),
    ]
else:
    urlpatterns = []
