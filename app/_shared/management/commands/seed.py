"""``manage.py seed`` — populate the dev/test database with sample data.

Each app may expose a ``seeders`` module with a ``run(*, fresh: bool) -> None``
function. This command discovers them by scanning ``settings.INSTALLED_APPS``
and invokes them in dependency order: any app whose ``seeders`` module
declares ``DEPENDS_ON: list[str]`` (a list of app labels) is run after its
dependencies.

Default mode is ``get_or_create`` — preserves rows you've added by hand.
Pass ``--fresh`` to wipe seeded rows and rebuild from scratch.

This command refuses to run with ``DEBUG=False`` to avoid accidentally
seeding production data; pass ``--allow-prod`` to override (you should
basically never need this).
"""
from __future__ import annotations

from importlib import import_module
from typing import Any

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Seed dev/test database with sample data from each app's seeders module."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--fresh",
            action="store_true",
            help="Delete previously seeded rows before recreating them.",
        )
        parser.add_argument(
            "--allow-prod",
            action="store_true",
            help="Permit running with DEBUG=False (use with care).",
        )
        parser.add_argument(
            "--only",
            metavar="APP_LABEL",
            action="append",
            default=[],
            help="Only run this app's seeder. Repeatable.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG and not options["allow_prod"]:
            raise CommandError(
                "Refusing to seed with DEBUG=False. Pass --allow-prod to override."
            )

        only = set(options["only"])
        seeders = self._discover_seeders()
        if only:
            seeders = [(label, mod) for label, mod in seeders if label in only]
            unknown = only - {label for label, _ in seeders}
            if unknown:
                raise CommandError(f"No seeders found for: {', '.join(sorted(unknown))}")

        ordered = self._topological_sort(seeders)

        for label, module in ordered:
            self.stdout.write(self.style.MIGRATE_HEADING(f"Seeding {label} ..."))
            module.run(fresh=options["fresh"])
            self.stdout.write(self.style.SUCCESS(f"  [done] {label}"))

        self.stdout.write(self.style.SUCCESS("Seed complete."))

    @staticmethod
    def _discover_seeders() -> list[tuple[str, Any]]:
        """Return ``[(app_label, seeders_module), ...]`` for every app that has one."""
        found: list[tuple[str, Any]] = []
        for app_config in apps.get_app_configs():
            try:
                module = import_module(f"{app_config.name}.seeders")
            except ModuleNotFoundError:
                continue
            if not hasattr(module, "run"):
                continue
            found.append((app_config.label, module))
        return found

    @staticmethod
    def _topological_sort(
        seeders: list[tuple[str, Any]],
    ) -> list[tuple[str, Any]]:
        """Order seeders so any app listed in another's ``DEPENDS_ON`` runs first."""
        by_label = dict(seeders)
        visited: set[str] = set()
        order: list[tuple[str, Any]] = []

        def visit(label: str, stack: tuple[str, ...]) -> None:
            if label in visited:
                return
            if label in stack:
                cycle = " → ".join([*stack, label])
                raise CommandError(f"Seeder dependency cycle: {cycle}")
            module = by_label[label]
            for dep in getattr(module, "DEPENDS_ON", []):
                if dep in by_label:
                    visit(dep, (*stack, label))
            visited.add(label)
            order.append((label, module))

        for label, _ in seeders:
            visit(label, ())
        return order
