from flask import Flask, Response
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_admin import Admin
from werkzeug.exceptions import HTTPException
from typing import Any
from .localization import get_translations
from .config import Config


app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
admin = Admin(app)
mail = Mail(app)

login_manager = LoginManager(app)
login_manager.login_message_category = "warning"
login_manager.login_view = 'login'

@login_manager.unauthorized_handler
def unauthorized_callback() -> Response:
    """
    Redirect unauthorized users to the login page and store the original URL.

    Returns:
        Response: A redirect response to the login page.
    """
    session['next'] = request.url
    return redirect(lang_url_for('login'))

@app.context_processor
def inject_translations() -> dict[str, str]:
    """
    Inject translations and current language into the template context.

    Returns:
        dict: A dictionary with translation mappings and the current language.
    """
    lang = getattr(g, 'lang', 'en')
    tr = get_translations(lang)
    return dict(tr=tr, lang=lang)

def lang_url_for(endpoint: str, **values: Any) -> str:
    """
    Generate a URL with the current language included in the path.

    Args:
        endpoint (str): Flask endpoint name.
        **values: Additional parameters to include in the URL.

    Returns:
        str: A localized URL string.
    """
    lang = g.get('lang', 'en')
    values['lang'] = lang
    return url_for(endpoint, **values)

@app.context_processor
def inject_utilities() -> dict[str, Any]:
    """
    Inject utility functions into the template context.

    Returns:
        dict: A dictionary with callable utilities (e.g., lang_url_for).
    """
    return dict(lang_url_for=lang_url_for)

@app.before_request
def set_language() -> None:
    """
    Set the current language for the request based on the URL or session.
    Defaults to 'en' if no language is specified.
    """
    lang = None

    path_parts = request.path.strip('/').split('/')
    if path_parts and path_parts[0] in ['en', 'lt']:
        lang = path_parts[0]

    if not lang:
        lang = session.get('lang')

    g.lang = lang or 'en'
    session['lang'] = g.lang

from .routes import *

@app.errorhandler(404)
def not_found(e: HTTPException) -> Response:
    """
    Custom 404 error handler that renders a localized error page.

    Args:
        e (HTTPException): The HTTP error object.

    Returns:
        Response: A rendered 404 error page with language context.
    """
    path_parts = request.path.strip('/').split('/')
    lang = path_parts[0] if path_parts and path_parts[0] in ['en', 'lt'] else None
    lang = lang or session.get('lang', 'lt')
    session['lang'] = lang
    g.lang = lang

    tr = get_translations(lang)
    return render_template("errors/404.html", tr=tr, lang=lang), 404