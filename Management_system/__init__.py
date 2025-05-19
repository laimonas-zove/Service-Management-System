from flask import Flask
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_admin import Admin
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
def unauthorized_callback():
    session['next'] = request.url
    return redirect(lang_url_for('login'))

@app.context_processor
def inject_translations():
    lang = getattr(g, 'lang', 'en')
    tr = get_translations(lang)
    return dict(tr=tr, lang=lang)

def lang_url_for(endpoint, **values):
    lang = g.get('lang', 'en')
    values['lang'] = lang
    return url_for(endpoint, **values)

@app.context_processor
def inject_utilities():
    return dict(lang_url_for=lang_url_for)

from .routes import *