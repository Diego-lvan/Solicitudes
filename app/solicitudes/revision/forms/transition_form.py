"""Single-field form for state-transition observaciones."""
from __future__ import annotations

from django import forms


class TransitionForm(forms.Form):
    observaciones = forms.CharField(
        label="Observaciones (opcional)",
        required=False,
        max_length=2000,
        widget=forms.Textarea(
            attrs={"class": "form-control", "rows": 3, "maxlength": 2000}
        ),
    )
