class Config:
    SECRET_KEY = 'a3f62129e1a81c8f3b1e6d65f498bd2fdf9db4ff0d3bde17'
    SQLALCHEMY_DATABASE_URI = "sqlite:///demo.db"

    MAIL_SERVER = "smtp.example.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_DEFAULT_SENDER = "your_email@example.com"
    MAIL_USERNAME = "your_email_username"
    MAIL_PASSWORD = "your_email_password"
