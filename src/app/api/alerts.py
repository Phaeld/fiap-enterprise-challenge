# app/api/alerts.py
from flask import Blueprint, request, jsonify
from datetime import datetime
from ..extensions import db
from ..models import Alerta, Falha, Sensor, Peca

bp_alerts = Blueprint("alerts", __name__, url_prefix="/api")

def parse_ts(ts):
    return datetime.fromisoformat(ts.replace("Z","+00:00"))

@bp_alerts.post("/alerts")
def create_alert():
    data = request.get_json() or {}
    id_sensor = data["id_sensor"]
    nivel_risco = data.get("nivel_risco","ALTO")
    valor = data.get("valor")
    ts = parse_ts(data["ts"])

    # Criado para adicionar alertas nos registros de falhas
    alert = Alerta(id_falha=None, nivel_risco=nivel_risco)
    db.session.add(alert)
    db.session.commit()
    return jsonify({"ok": True, "id_alerta": alert.id_alerta})
