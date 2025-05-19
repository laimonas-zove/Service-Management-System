import os
import uuid
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import request, g
from flask_mail import Message
from Management_system import get_translations, mail, db, models, bcrypt
from .models import OneTimeLink
from markupsafe import Markup

def create_default_admin():
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

def localization(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        view_args = request.view_args or {}
        lang = kwargs.get('lang') or view_args.get('lang') or 'en'
        g.lang = lang
        g.tr = get_translations(lang)
        return func(*args, **kwargs)
    return wrapper

def strip_tags(html):
    return Markup(html).striptags()

def send_email(subject, recipients, html):
    if isinstance(recipients, str):
        recipients = [recipients]

    msg = Message(subject=subject, recipients=recipients)
    msg.html = html

    try:
        mail.send(msg)
        log_mail_sender(recipients, subject, "Sent")
    except Exception as e:
        log_mail_sender(recipients, subject, f"Failed to send: {e}")


def generate_link(purpose, user_id=None):
    token = str(uuid.uuid4())
    created_at = datetime.now()
    link = OneTimeLink(
        token=token,
        purpose=purpose,
        created_at = created_at,
        user_id=user_id,
        expires_at=datetime.utcnow() + timedelta(hours=6)
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


def log_user_action(user, action, details="", level="info"):
    if details:
        details = f"({details})"
    message = f"USER: {user} | ACTION: {action} | DETAILS: {details}"
    if level == "warning":
        user_logger.warning(message)
    else:
        user_logger.info(message)

def log_mail_sender(email, subject, status):

    mail_logger.info(f"TO: {email} | SUBJECT: {subject} | STATUS: {status}")
