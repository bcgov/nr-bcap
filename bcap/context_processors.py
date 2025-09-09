from django.conf import settings


def vueEntrypointsForPath(request):
    return (
        settings.VITE_ENTRYPOINTS[request.path]
        if hasattr(settings, "VITE_ENTRYPOINTS")
        and request.path in settings.VITE_ENTRYPOINTS
        else []
    )


def vite(request):
    return {
        "USE_VITE": getattr(settings, "USE_VITE", False),
        "VITE_BASE": getattr(settings, "VITE_BASE", "/bcap/@vite/"),
        "VUE_ENTRYPOINTS": vueEntrypointsForPath(request),
    }
