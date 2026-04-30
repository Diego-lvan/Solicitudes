from notificaciones.services.email_sender.interface import EmailSender
from notificaciones.services.email_sender.smtp_implementation import SmtpEmailSender

__all__ = ["EmailSender", "SmtpEmailSender"]
