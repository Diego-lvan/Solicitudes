"""GET-bound filter form for the admin user directory list."""
from __future__ import annotations

from django import forms

from usuarios.constants import Role
from usuarios.directory.schemas import UserListFilters


class DirectoryFilterForm(forms.Form):
    """Permissive parsing — invalid values degrade to "no filter" / page 1."""

    role = forms.ChoiceField(
        required=False,
        choices=[("", "Todos los roles"), *Role.choices()],
        label="Rol",
    )
    q = forms.CharField(
        required=False,
        max_length=200,
        strip=True,
        label="Buscar",
    )
    page = forms.IntegerField(required=False, min_value=1)

    def to_filters(self) -> UserListFilters:
        # ``cleaned_data`` exists only after ``is_valid()`` is called; with bad
        # input (e.g. ``page=abc``) the offending key is missing — read defensively.
        data = getattr(self, "cleaned_data", {}) or {}

        role_raw = (data.get("role") or "").strip()
        try:
            role = Role(role_raw) if role_raw else None
        except ValueError:
            role = None

        page = data.get("page") or 1
        if page < 1:
            page = 1

        q = (data.get("q") or "").strip()

        return UserListFilters(role=role, q=q, page=page)
