from flask import Flask
from .config import Config
from .extensions import db, migrate, admin, cors
from .api.routes import bp as api_bp
from .views.routes import views
from .models import Peca, Sensor, Ciclo, Leitura, Falha, Alerta
from flask_admin.contrib.sqla import ModelView
from .api.cycles import bp_cycles
from .api.alerts import bp_alerts

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    cors.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(api_bp)
    app.register_blueprint(views)
    app.register_blueprint(bp_cycles)
    app.register_blueprint(bp_alerts)

    admin.init_app(app)
    admin.add_view(ModelView(Peca, db.session))
    admin.add_view(ModelView(Sensor, db.session))
    admin.add_view(ModelView(Ciclo, db.session))
    admin.add_view(ModelView(Leitura, db.session))
    admin.add_view(ModelView(Falha, db.session))
    admin.add_view(ModelView(Alerta, db.session))

    @app.get("/health")
    def health(): return {"status": "ok"}
    return app

app = create_app()
