"""Outbound port for delivering a single email message."""
from __future__ import annotations

from abc import ABC, abstractmethod


class EmailSender(ABC):
    """Send one email. Implementations raise ``EmailDeliveryError`` on transport failure."""

    @abstractmethod
    def send(self, *, subject: str, to: str, html: str, text: str) -> None:
        """Deliver one email; raise ``EmailDeliveryError`` if the transport fails."""
