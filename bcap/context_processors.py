# bcap/context_processors.py
from django.conf import settings

def vite(request):
    return {
        "USE_VITE": getattr(settings, "USE_VITE", False),
        "VITE_BASE": getattr(settings, "VITE_BASE", "/bcap/@vite/"),
    }