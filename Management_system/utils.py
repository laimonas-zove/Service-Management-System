import os
import uuid
import logging
from datetime import datetime, timedelta, timezone, date
from calendar import monthrange
from functools import wraps
from flask import request, g
from flask_mail import Message
from typing import Callable, Union, Optional, Tuple
from Management_system import get_translations, mail, db, models, bcrypt
from .models import OneTimeLink
from markupsafe import Markup

def create_default_admin() -> None:
    """
    Create a default admin user if no admin exists in the database.
    """
    if not models.User.query.filter_by(is_admin=True).first():
        admin = models.User(
            name="Admin",
            surname="Admin",
            email="admin@interatlas.lt",
            phone_number="000000000",
            password=bcrypt.generate_password_hash("admin").decode('utf-8'),
            is_admin=True,
        )
        db.session.add(admin)
        db.session.commit()

def localization(func: Callable) -> Callable:
    """
    Decorator that injects localization data (`lang`, `tr`) into Flask's global `g`.

    Args:
        func: The route function to wrap.

    Returns:
        Callable: The wrapped function with localization context.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        view_args = request.view_args or {}
        lang = kwargs.get('lang') or view_args.get('lang') or 'en'
        g.lang = lang
        g.tr = get_translations(lang)
        return func(*args, **kwargs)
    return wrapper

def strip_tags(html: str) -> str:
    """
    Remove all HTML tags from a string.

    Args:
        html: A string containing HTML content.

    Returns:
        A plain text string with tags stripped.
    """
    return Markup(html).striptags()

def send_email(subject: str, recipients: Union[str, list[str]], html: str) -> None:
    """
    Send an HTML email to one or more recipients.

    Args:
        subject: Email subject.
        recipients: Single email or list of email addresses.
        html: HTML content of the email.
    """
    if isinstance(recipients, str):
        recipients = [recipients]

    msg = Message(subject=subject, recipients=recipients)
    msg.html = html

    try:
        mail.send(msg)
        log_mail_sender(recipients, subject, "Sent")
    except Exception as e:
        log_mail_sender(recipients, subject, f"Failed to send: {e}")


def generate_link(purpose: str, email: str) -> str:
    """
    Generate a one-time token link for a given purpose and store it in the database.

    Args:
        purpose: Purpose of the token (e.g., "registration", "reset_password").
        email: Email address the link is associated with.

    Returns:
        The generated token as a string.
    """
    token = str(uuid.uuid4())
    created_at = datetime.now()
    link = OneTimeLink(
        token=token,
        purpose=purpose,
        created_at=created_at,
        email=email,
        expires_at = datetime.now(timezone.utc) + timedelta(hours=6)
    )
    db.session.add(link)
    db.session.commit()
    return token

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

user_logger = logging.getLogger("user_actions")
user_handler = logging.FileHandler(os.path.join(LOG_DIR, "user_actions.log"), encoding='utf-8')
user_handler.setFormatter(formatter)
user_logger.addHandler(user_handler)
user_logger.setLevel(logging.INFO)

mail_logger = logging.getLogger("mail_sender")
mail_handler = logging.FileHandler(os.path.join(LOG_DIR, "mail_sender.log"), encoding='utf-8')
mail_handler.setFormatter(formatter)
mail_logger.addHandler(mail_handler)
mail_logger.setLevel(logging.INFO)


def log_user_action(user: str, action: str, details: str = "", level: str = "info") -> None:
    """
    Log a user action to the user_actions log.

    Args:
        user: The user name.
        action: Description of the action.
        details: Optional extra information.
        level: Logging level ("info" or "warning").
    """
    if details:
        details = f"({details})"
    message = f"USER: {user} | ACTION: {action} | DETAILS: {details}"
    if level == "warning":
        user_logger.warning(message)
    else:
        user_logger.info(message)

def log_mail_sender(email: Union[str, list[str]], subject: str, status: str) -> None:
    """
    Log the result of a mail sending attempt.

    Args:
        email: Recipient email or list of emails.
        subject: Email subject.
        status: Result status (e.g., "Sent", "Failed to sent").
    """
    mail_logger.info(f"TO: {email} | SUBJECT: {subject} | STATUS: {status}")

def get_month_range(year: Optional[int] = None, month: Optional[int] = None) -> Tuple[date, date]:
    """
    Return the start and end date of a given month.

    Args:
        year: The year to use. Defaults to current year.
        month: The month to use. Defaults to current month.

    Returns:
        A tuple containing the first and last date of the month.
    """
    now = date.today()
    year = year or now.year
    month = month or now.month

    start = date(year, month, 1)
    end_day = monthrange(year, month)[1]
    end = date(year, month, end_day)

    return (start, end)