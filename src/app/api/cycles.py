# app/api/cycles.py
from flask import Blueprint, request, jsonify
from datetime import datetime
from ..extensions import db
from ..models import Peca, Ciclo, Sensor

bp_cycles = Blueprint("cycles", __name__, url_prefix="/api")

def parse_ts(ts):
    return datetime.fromisoformat(ts.replace("Z","+00:00"))

@bp_cycles.post("/cycle-events")
def cycle_events():
    data = request.get_json() or {}
    event = data.get("event")
    ts = parse_ts(data.get("ts"))
    if event == "start_all":
        # cria um ciclo por peça que NÃO esteja com ciclo aberto
        pecas = db.session.query(Peca).all()
        for p in pecas:
            c = Ciclo(id_peca=p.id_peca, data_inicio=ts, data_fim=None, duracao=None)
            db.session.add(c)
        db.session.commit()
        return jsonify({"ok": True, "created": len(pecas)})

    if event == "end_all":
        # fecha todos os ciclos abertos e calcula duração (minutos)
        abertos = db.session.query(Ciclo).filter(Ciclo.data_fim.is_(None)).all()
        for c in abertos:
            c.data_fim = ts
            if c.data_inicio and c.data_fim:
                c.duracao = int((c.data_fim - c.data_inicio).total_seconds() // 60)
        db.session.commit()
        return jsonify({"ok": True, "closed": len(abertos)})

    return jsonify({"error":"evento inválido"}), 400
