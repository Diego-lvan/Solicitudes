"""In-memory fakes for notificaciones service tests."""
from __future__ import annotations

from notificaciones.exceptions import EmailDeliveryError
from notificaciones.services.email_sender.interface import EmailSender
from notificaciones.services.recipient_resolver.interface import RecipientResolver
from usuarios.constants import Role
from usuarios.schemas import UserDTO


class StubRecipientResolver(RecipientResolver):
    def __init__(self, by_role: dict[Role, list[UserDTO]] | None = None) -> None:
        self._by_role = by_role or {}

    def resolve_by_role(self, role: Role) -> list[UserDTO]:
        return list(self._by_role.get(role, []))


class RecordingEmailSender(EmailSender):
    """Captures every send call; can be configured to raise."""

    def __init__(self, *, fail_for: set[str] | None = None) -> None:
        self.sent: list[dict[str, str]] = []
        self._fail_for = fail_for or set()

    def send(self, *, subject: str, to: str, html: str, text: str) -> None:
        if to in self._fail_for:
            raise EmailDeliveryError(f"stubbed failure for {to}")
        self.sent.append({"subject": subject, "to": to, "html": html, "text": text})
