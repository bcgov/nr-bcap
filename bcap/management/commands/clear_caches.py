"""Clear all configured Django cache backends."""

from django.conf import settings
from django.core.cache import caches
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Clear all configured Django cache backends. "
        "Iterates over every backend in settings.CACHES (not just 'default'), "
        "so separate session, view, and custom caches are all flushed."
    )

    def handle(self, *args, **options):
        cache_aliases = list(settings.CACHES.keys())

        if not cache_aliases:
            self.stdout.write("No caches configured in settings.CACHES.")
            return

        self.stdout.write(
            f"Clearing {len(cache_aliases)} cache backend(s):"
            f" {', '.join(cache_aliases)}\n"
        )

        cleared, failed = 0, 0
        for alias in cache_aliases:
            backend = settings.CACHES[alias].get("BACKEND", "unknown backend")
            try:
                caches[alias].clear()
                cleared += 1
                self.stdout.write(self.style.SUCCESS(f"  {alias:<15} ({backend})"))
            except Exception as exc:
                failed += 1
                self.stderr.write(
                    self.style.ERROR(
                        f"  {alias:<15} ({backend})"
                        f" -- {exc.__class__.__name__}: {exc}"
                    )
                )

        summary = f"\nDone. Cleared {cleared}, failed {failed}."
        if failed:
            self.stderr.write(self.style.WARNING(summary))
        else:
            self.stdout.write(summary)
