from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_admin import Admin
from flask_cors import CORS

db = SQLAlchemy()
migrate = Migrate()
admin = Admin(name="Admin", template_mode="bootstrap4")
cors = CORS()
