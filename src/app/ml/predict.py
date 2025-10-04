# app/ml/predict.py
from pathlib import Path
import os
import numpy as np
import joblib

MODEL_DIR = Path(os.getenv("MODEL_DIR", Path(__file__).parent))
BASE_FEATURES = ["tempo_uso", "ciclos", "temperatura", "vibracao"]

# Lazy loading para performance
_modelo_estado = None
_modelo_falha24 = None

def _load(path):
    p = MODEL_DIR / path
    if not p.exists():
        raise FileNotFoundError(f"Modelo não encontrado: {p}")
    return joblib.load(p)

def _ensure_loaded():
    global _modelo_estado, _modelo_falha24
    if _modelo_estado is None:
        _modelo_estado = _load("modelo_estado_peca.joblib")
    if _modelo_falha24 is None:
        _modelo_falha24 = _load("modelo_falha_24h.joblib")

def _make_X(payload: dict, model) -> np.ndarray:
    cols = getattr(model, "feature_names_in_", None)
    if cols is None:
        row = [float(payload.get(f, 0.0)) for f in BASE_FEATURES]
    else:
        alias = {
            "tempo_uso_total": "tempo_uso",
            "qtd_ciclos": "ciclos",
            "temp": "temperatura",
            "vib": "vibracao",
        }
        row = []
        for c in cols:
            v = payload.get(c, payload.get(alias.get(c, ""), 0.0))
            row.append(float(v) if v is not None else 0.0)

    X = np.array([row], dtype=float)
    # blindagem contra NaN/Inf
    X = np.nan_to_num(X, nan=0.0, posinf=1e9, neginf=-1e9)
    return X


def predict_state(payload: dict):
    _ensure_loaded()
    X = _make_X(payload, _modelo_estado)
    y = _modelo_estado.predict(X)[0]
    try:
        return {"estado": int(y)}
    except Exception:
        return {"estado": y}

def predict_failure_24h(payload: dict, threshold: float = 0.5):
    _ensure_loaded()
    X = _make_X(payload, _modelo_falha24)
    proba = getattr(_modelo_falha24, "predict_proba", None)
    if proba is None:
        raw = _modelo_falha24.decision_function(X)
        # sigmoid
        prob = float(1 / (1 + np.exp(-raw)) if np.ndim(raw)==0 else 1/(1+np.exp(-raw[0])))
    else:
        prob = float(_modelo_falha24.predict_proba(X)[0, 1])
    return {"falha_prox_24h": int(prob >= threshold), "prob": prob, "threshold": threshold}
