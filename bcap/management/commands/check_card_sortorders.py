"""
Management command: check_card_sortorders

Checks all package graph cards for NULL sortorder values. Cards with NULL
sortorders produce non-deterministic field ordering in the generated API
schema because the query in arches-querysets has no ORDER BY, so PostgreSQL
falls back to physical row insertion order — which differs between a fresh CI
database (JSON file order) and a local database built up over time.

By default the command reports problems and exits non-zero if any are found.
Pass --fix to assign explicit sortorder values and update both the package
JSON files and the live DB rows.

Fix strategy: for each graph, null-sortorder cards are assigned integers
starting from max(existing_sortorders) + 1, in the order they appear in the
graph JSON file. This preserves all existing explicit ordering and pins the
previously-null cards to stable values at the end of the sequence — consistent
with how PostgreSQL was already sorting them (NULLS LAST) but now deterministic.

    python3 manage.py check_card_sortorders           # check only (CI-safe)
    python3 manage.py check_card_sortorders --fix     # fix JSON + DB
"""

import json
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction

from arches.app.models import models as arches_models


def _pkg():
    return Path(apps.get_app_config("bcap").path) / "pkg"


def _all_package_graphs():
    """Yield (doc, graphid, slug, path) for every graph JSON in the package."""
    for path in sorted((_pkg() / "graphs").rglob("*.json")):
        try:
            doc = json.loads(path.read_text())
            graph = doc["graph"][0]
            yield doc, graph["graphid"], graph["slug"], path
        except (KeyError, IndexError, ValueError):
            continue


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Assign explicit sortorders and update the JSON files and DB.",
        )

    def handle(self, *args, **options):
        fix = options["fix"]
        problems = []

        for doc, graphid, slug, path in _all_package_graphs():
            null_cards = {
                str(card.cardid): card
                for card in arches_models.CardModel.objects.filter(
                    graph_id=graphid,
                    source_identifier__isnull=True,
                    sortorder__isnull=True,
                )
            }
            if not null_cards:
                continue

            for card in null_cards.values():
                problems.append((slug, card.cardid, str(card.name)))
                self.stdout.write(
                    self.style.WARNING(
                        f"  NULL sortorder: {slug} / {card.name} ({card.cardid})"
                    )
                )

            if not fix:
                continue

            # Max explicit sortorder already assigned in this graph.
            max_sortorder = (
                arches_models.CardModel.objects.filter(
                    graph_id=graphid,
                    source_identifier__isnull=True,
                    sortorder__isnull=False,
                )
                .order_by("-sortorder")
                .values_list("sortorder", flat=True)
                .first()
                or -1
            )

            # Walk JSON cards in file order; assign to null-sortorder ones.
            next_sortorder = max_sortorder + 1
            db_updates = []
            for json_card in doc["graph"][0].get("cards", []):
                card_id = str(json_card.get("cardid", ""))
                if card_id not in null_cards:
                    continue
                card = null_cards[card_id]
                self.stdout.write(f"    {slug} / {card.name}: NULL -> {next_sortorder}")
                json_card["sortorder"] = next_sortorder
                card.sortorder = next_sortorder
                db_updates.append(card)
                next_sortorder += 1

            with transaction.atomic():
                arches_models.CardModel.objects.bulk_update(db_updates, ["sortorder"])
            path.write_text(json.dumps(doc, indent=4, ensure_ascii=False) + "\n")
            self.stdout.write(
                self.style.SUCCESS(f"  updated: {path.relative_to(_pkg().parent)}")
            )

        if not problems:
            self.stdout.write(
                self.style.SUCCESS("All package graph cards have explicit sortorders.")
            )
        elif fix:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n{len(problems)} card(s) updated. Commit the JSON changes."
                )
            )
        else:
            self.stdout.write("")
            self.stdout.write(
                self.style.ERROR(
                    f"{len(problems)} card(s) with NULL sortorder. "
                    "Run with --fix to assign explicit sortorders."
                )
            )
            raise SystemExit(1)
