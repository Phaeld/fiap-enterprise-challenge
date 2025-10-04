import os
class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///local.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "dev")

    # >>> ALERTAS
    ALERT_THRESH_TEMPERATURA = float(os.getenv("ALERT_THRESH_TEMPERATURA", "80"))
    ALERT_THRESH_VIBRACAO = float(os.getenv("ALERT_THRESH_VIBRACAO", "80"))
    ALERT_MIN_STREAK = int(os.getenv("ALERT_MIN_STREAK", "3"))
    ALERT_WINDOW_SECONDS = int(os.getenv("ALERT_WINDOW_SECONDS", "120"))
