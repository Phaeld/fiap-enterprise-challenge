"""
Classificação do estado da peça (Saudável / Desgastada / Crítica)
- Lê app/app/database/sensores.csv (ou CSV_PATH)
- Consolida leituras por (id_peca, leitura_data_hora)
- Usa 'risco_falha' do CSV como rótulo (mapeado para nomes de negócio)
- Treina RandomForest e avalia com split temporal
- Salva gráficos (matriz de confusão, importância das features) e o modelo .joblib

Como rodar (no container):
    docker compose exec web python -m app.ml.piece_state_classifier

Ambiente (opcional):
    CSV_PATH  (default: /app/app/database/sensores.csv)
    MODEL_DIR (default: /app/app/ml)
    ASSETS_DIR(default: /app/assets)
"""

import os
from pathlib import Path
import numpy as np
import pandas as pd
import joblib

# Matplotlib headless
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix

RANDOM_SEED = 42

# ---------------- utils de caminho ----------------
def _resolve_csv() -> str:
    env = os.getenv("CSV_PATH")
    if env:
        return env
    here = Path(__file__).resolve()
    candidates = [
        Path("/app/app/database/sensores.csv"),                # container
        here.parents[1] / "database" / "sensores.csv",         # app/database
        Path.cwd() / "app" / "database" / "sensores.csv",      # se cwd=/app
        Path.cwd() / "src" / "app" / "database" / "sensores.csv",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    # fallback padrão no container
    return "/app/app/database/sensores.csv"


CSV_PATH   = Path(_resolve_csv())
MODEL_DIR  = Path(os.getenv("MODEL_DIR", "/app/app/ml"))
ASSETS_DIR = Path(os.getenv("ASSETS_DIR", "/app/assets"))
MODEL_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

print(f"[estado] Lendo CSV: {CSV_PATH}")
df = pd.read_csv(CSV_PATH, parse_dates=["leitura_data_hora"])

required = {
    "id_peca", "leitura_data_hora",
    "tempo_uso", "ciclos", "temperatura", "vibracao",
    "risco_falha"
}
missing = required - set(df.columns)
if missing:
    raise RuntimeError(
        f"CSV sem colunas obrigatórias: {missing}. "
        "Gere o CSV novamente com `docker compose exec web python -m app.generate_csv`."
    )

# Ordenação canônica
df = df.sort_values(["id_peca", "leitura_data_hora"]).reset_index(drop=True)

# ---------------- agregação por timestamp/peça ----------------
agg_cols = ["tempo_uso", "ciclos", "temperatura", "vibracao", "risco_falha"]
df_agg = (
    df.groupby(["id_peca", "leitura_data_hora"], as_index=False)[agg_cols]
      .agg({
          "tempo_uso": "max",
          "ciclos": "max",
          "temperatura": "max",
          "vibracao": "max",
          "risco_falha": "last"   # string: pega a última etiqueta conhecida
      })
)

# ---------------- rótulo de negócio ----------------
map_rotulos = {"baixo": "Saudável", "medio": "Desgastada", "alto": "Crítica"}
df_agg["estado_peca"] = df_agg["risco_falha"].map(map_rotulos)

# Remove linhas sem rótulo (se houver)
df_agg = df_agg.dropna(subset=["estado_peca"]).reset_index(drop=True)

# ---------------- features e imputação ----------------
feature_cols = ["tempo_uso", "ciclos", "temperatura", "vibracao"]

# Imputação leve:
# - ffill/bfill por peça para temperatura/vibração
# - median global + 0.0 como fallbac
