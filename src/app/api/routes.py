from flask import Blueprint, request, jsonify, current_app
from marshmallow import ValidationError
from .schemas import ReadingInSchema, PredictStateIn
from ..extensions import db
from sqlalchemy import and_
from sqlalchemy import func
from ..models import Peca, Sensor, Ciclo, Leitura, Falha, Alerta  # já deve ter, garanta Peca e Ciclo também
from datetime import datetime, timedelta
from ..ml import predict

bp = Blueprint("api", __name__, url_prefix="/api")

@bp.errorhandler(ValidationError)
def handle_validation_error(err):
    return jsonify({"error": "validation_error", "messages": err.messages}), 400

def _parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(str(ts).replace("Z", "+00:00"))

def _threshold_for(tipo_sensor: str) -> float:
    cfg = current_app.config
    tipo = (tipo_sensor or "").strip().lower()
    if "temp" in tipo:         # temperatura
        return cfg["ALERT_THRESH_TEMPERATURA"]
    if "vibra" in tipo:        # vibração
        return cfg["ALERT_THRESH_VIBRACAO"]
    # default se vier outro tipo
    return max(cfg["ALERT_THRESH_TEMPERATURA"], cfg["ALERT_THRESH_VIBRACAO"])

def _check_and_create_alert(sensor: Sensor, leitura: Leitura):
    """Dispara alerta + falha se houver 'streak' leituras >= threshold dentro da janela."""
    cfg = current_app.config
    threshold = _threshold_for(sensor.tipo_sensor)
    streak = int(cfg["ALERT_MIN_STREAK"])
    window = int(cfg["ALERT_WINDOW_SECONDS"])

    # Só vale a pena checar se a leitura atual já excede o limiar
    if leitura.leitura_valor < threshold:
        return None

    # Pega as N leituras mais recentes (incluindo a atual)
    recentes = (
        db.session.query(Leitura)
        .filter(Leitura.id_sensor == sensor.id_sensor)
        .order_by(Leitura.leitura_data_hora.desc())
        .limit(streak)
        .all()
    )
    if len(recentes) < streak:
        return None

    # Todas precisam estar >= threshold e dentro da janela (do 1º ao N-ésimo)
    if not all(r.leitura_valor >= threshold for r in recentes):
        return None

    intervalo = (recentes[0].leitura_data_hora - recentes[-1].leitura_data_hora).total_seconds()
    if intervalo > window:
        return None

    # Dispara: cria FALHA descritiva + ALERTA (nivel ALTO)
    falha = Falha(
        id_peca=sensor.id_peca,
        descricao=f"Excedido limiar ({threshold}) em {streak} leituras para o sensor {sensor.id_sensor} ({sensor.tipo_sensor}). Valor atual={leitura.leitura_valor}",
        data=leitura.leitura_data_hora,
    )
    db.session.add(falha)
    db.session.flush()  # obtém id_falha

    alerta = Alerta(id_falha=falha.id_falha, nivel_risco="ALTO")
    db.session.add(alerta)
    # não commitamos aqui; quem chama commit já

    return {"id_alerta": alerta.id_alerta, "id_falha": falha.id_falha, "nivel": "ALTO"}

@bp.post("/readings")
def ingest_reading():
    data = request.get_json() or {}
    payload = ReadingInSchema().load(data)

    sensor = Sensor.query.get(payload["id_sensor"])
    if not sensor:
        return jsonify({"error": "id_sensor inexistente"}), 400

    leitura = Leitura(
        id_sensor=payload["id_sensor"],
        leitura_valor=payload["leitura_valor"],
        leitura_data_hora=payload["leitura_data_hora"],
    )
    db.session.add(leitura)
    db.session.flush()  # garante que a leitura já está visível para as consultas de checagem

    alerta_info = _check_and_create_alert(sensor, leitura)

    db.session.commit()
    resp = {"ok": True, "id_leitura": leitura.id_leitura}
    if alerta_info:
        resp["alerta"] = alerta_info
    return jsonify(resp), 201

@bp.post("/predict/state")
def predict_state():
    data = PredictStateIn().load(request.get_json() or {})
    return jsonify(predict.predict_state(data))

@bp.post("/predict/failure24h")
def predict_failure():
    data = PredictStateIn().load(request.get_json() or {})
    th = float(request.args.get("threshold", 0.5))
    return jsonify(predict.predict_failure_24h(data, threshold=th))

@bp.get("/sensors")
def sensors_list():
    sensors = db.session.query(Sensor).order_by(Sensor.id_sensor).all()
    return jsonify([
        {"id_sensor": s.id_sensor, "tipo_sensor": s.tipo_sensor, "id_peca": s.id_peca}
        for s in sensors
    ])

# SÉRIE TEMPORAL (x=timestamp, y=valor) do sensor escolhido
@bp.get("/readings/series")
def readings_series():
    sensor_id = request.args.get("sensor_id", type=int)
    minutes = request.args.get("minutes", default=60, type=int)
    limit = request.args.get("limit", default=1000, type=int)

    # se não informaram sensor, pega o primeiro
    if not sensor_id:
        first = db.session.query(Sensor.id_sensor).order_by(Sensor.id_sensor).first()
        if not first:
            return jsonify({"sensor_id": None, "x": [], "y": []})
        sensor_id = first[0]

    since = datetime.utcnow() - timedelta(minutes=minutes)
    rows = (
        db.session.query(Leitura.leitura_data_hora, Leitura.leitura_valor)
        .filter(and_(Leitura.id_sensor == sensor_id,
                     Leitura.leitura_data_hora >= since))
        .order_by(Leitura.leitura_data_hora.asc())
        .limit(limit)
        .all()
    )
    x = [dt.isoformat() for dt, _ in rows]     # timestamps ISO-8601
    y = [float(v) for _, v in rows]            # valores

    return jsonify({"sensor_id": sensor_id, "x": x, "y": y})

# helpers internos
def _now_utc():
    return datetime.utcnow()

def _avg_for(peca_id: int, tipo_like: str, minutes: int) -> float:
    """Média das últimas N min para sensores da peça (tipo LIKE 'temper%' ou 'vibra%')."""
    since = _now_utc() - timedelta(minutes=minutes)
    q = (
        db.session.query(func.avg(Leitura.leitura_valor))
        .join(Sensor, Sensor.id_sensor == Leitura.id_sensor)
        .filter(Sensor.id_peca == peca_id)
        .filter(Sensor.tipo_sensor.ilike(tipo_like))
        .filter(Leitura.leitura_data_hora >= since)
    ).scalar()
    if q is None:
        # cai para último valor disponível
        q = (
            db.session.query(Leitura.leitura_valor)
            .join(Sensor, Sensor.id_sensor == Leitura.id_sensor)
            .filter(Sensor.id_peca == peca_id)
            .filter(Sensor.tipo_sensor.ilike(tipo_like))
            .order_by(Leitura.leitura_data_hora.desc())
            .limit(1).scalar()
        )
    return float(q) if q is not None else 0.0

def _tempo_uso_minutos(peca_id: int) -> float:
    """Soma dos minutos dos ciclos; inclui ciclo aberto."""
    total = (
        db.session.query(func.coalesce(func.sum(Ciclo.duracao), 0))
        .filter(Ciclo.id_peca == peca_id).scalar()
    ) or 0
    # ciclo aberto
    aberto = (
        db.session.query(Ciclo)
        .filter(Ciclo.id_peca == peca_id, Ciclo.data_fim.is_(None))
        .order_by(Ciclo.data_inicio.desc())
        .first()
    )
    if aberto and aberto.data_inicio:
        total += int((_now_utc() - aberto.data_inicio).total_seconds() // 60)
    return float(total)

def _ciclos_count(peca_id: int) -> float:
    return float(db.session.query(func.count(Ciclo.id_ciclo)).filter(Ciclo.id_peca == peca_id).scalar() or 0)

@bp.get("/predict/snapshot")
def predict_snapshot():
    """
    Calcula features por peça e retorna:
    - estado_pred (predict_state)
    - falha24_prob / falha24_flag (predict_failure_24h)
    """
    # parâmetros (ajuste se quiser)
    temp_min = int(request.args.get("temp_minutes", 15))   # janela p/ temperatura
    vib_min  = int(request.args.get("vib_minutes", 5))     # janela p/ vibração
    threshold = float(request.args.get("threshold", 0.5))  # p/ falha24

    pecas = db.session.query(Peca).order_by(Peca.id_peca).all()
    out = []
    for p in pecas:
        temperatura = _avg_for(p.id_peca, "%temper%", temp_min)
        vibracao    = _avg_for(p.id_peca, "%vibra%",  vib_min)
        tempo_uso   = _tempo_uso_minutos(p.id_peca)
        ciclos      = _ciclos_count(p.id_peca)

        payload = {
            "tempo_uso": tempo_uso,
            "ciclos": ciclos,
            "temperatura": temperatura,
            "vibracao": vibracao
        }

        estado = predict.predict_state(payload)["estado"]
        falha  = predict.predict_failure_24h(payload, threshold=threshold)

        out.append({
            "id_peca": p.id_peca,
            "tipo": p.tipo,
            "features": payload,
            "estado_pred": int(estado) if isinstance(estado, bool) or hasattr(estado, "bit_length") else estado,
            "falha24_prob": falha["prob"],
            "falha24_flag": falha["falha_prox_24h"]
        })
    return jsonify(out)


