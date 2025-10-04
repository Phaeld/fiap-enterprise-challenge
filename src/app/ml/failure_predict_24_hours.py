"""
Previsão de falha em horizonte fixo (próximas 24h)
- Lê app/app/database/sensores.csv (ou caminho em CSV_PATH)
- Usa eventos reais de FALHAS (coluna falha_evento) como rótulo base
- Cria rótulo binário: há falha nos próximos HORIZON_H?
- Gera features de janelas, treina GradientBoosting, avalia e salva o modelo

Como rodar (dentro do container):
    docker compose exec web python -m app.ml.failure_predict_24_hours

Ambiente (opcional):
    CSV_PATH=/app/app/database/sensores.csv
    MODEL_DIR=/app/app/ml
    ASSETS_DIR=/app/assets
    HORIZON_H=24
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

from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    roc_curve,
)
from sklearn.ensemble import GradientBoostingClassifier

# ---------------- Config ----------------
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

CSV_PATH  = Path(_resolve_csv())
ASSETS_DIR = Path(os.getenv("ASSETS_DIR", "/app/assets"))
MODEL_DIR  = Path(os.getenv("MODEL_DIR", "/app/app/ml"))

ASSETS_DIR.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

HORIZON_H   = int(os.getenv("HORIZON_H", "24"))
RANDOM_SEED = 42

# -------------- Load ---------------
print(f"[train] Lendo CSV: {CSV_PATH}")
df = pd.read_csv(CSV_PATH, parse_dates=["leitura_data_hora"])

required_cols = {
    "id_peca", "leitura_data_hora",
    "tempo_uso", "ciclos", "temperatura", "vibracao",
    "falha_evento"
}
missing = required_cols - set(df.columns)
if missing:
    raise RuntimeError(
        f"CSV sem colunas obrigatórias: {missing}. "
        "Gere o CSV novamente com `docker compose exec web python -m app.generate_csv`."
    )

# ordenação canônica
df = df.sort_values(["id_peca", "leitura_data_hora"]).reset_index(drop=True)

# -------------- Rótulo: falha nas próximas HORIZON_H horas --------------
def label_next_horizon(piece_df: pd.DataFrame, hours: int = 24) -> pd.DataFrame:
    g = piece_df.sort_values("leitura_data_hora").copy()
    times = g["leitura_data_hora"].to_numpy()
    fail_times = g.loc[g["falha_evento"] == 1, "leitura_data_hora"].to_numpy()

    has_fail_next = np.zeros(len(g), dtype=int)
    if len(fail_times) > 0:
        j = 0
        for i, t in enumerate(times):
            while j < len(fail_times) and fail_times[j] < t:
                j += 1
            k = j
            while k < len(fail_times):
                # diferença em horas (inteiro)
                dt_h = int(((fail_times[k] - t) / np.timedelta64(1, "h")))
                if dt_h <= hours:
                    if dt_h > 0:
                        has_fail_next[i] = 1
                        break
                    k += 1
                else:
                    break
    g["fail_next_h"] = has_fail_next
    return g

pieces = []
for pid, g in df.groupby("id_peca", sort=False):
    pieces.append(label_next_horizon(g, hours=HORIZON_H))
df_labeled = pd.concat(pieces, ignore_index=True)

# -------------- Features de janelas --------------
def add_window_features(piece_df: pd.DataFrame) -> pd.DataFrame:
    g = piece_df.sort_values("leitura_data_hora").copy()
    # janelas em número de linhas (assumindo amostragem “quase regular” por peça)
    windows = [3, 6, 12]
    for w in windows:
        g[f"temp_mean_{w}"] = g["temperatura"].rolling(w, min_periods=1).mean()
        g[f"vib_mean_{w}"]  = g["vibracao"].rolling(w, min_periods=1).mean()
        g[f"temp_std_{w}"]  = g["temperatura"].rolling(w, min_periods=1).std().fillna(0)
        g[f"vib_std_{w}"]   = g["vibracao"].rolling(w, min_periods=1).std().fillna(0)
        g[f"ciclos_delta_{w}"] = g["ciclos"].diff(w).fillna(0)
        g[f"uso_delta_{w}"]    = g["tempo_uso"].diff(w).fillna(0)
    return g

feat_pieces = []
for pid, g in df_labeled.groupby("id_peca", sort=False):
    feat_pieces.append(add_window_features(g))
df_feat = pd.concat(feat_pieces, ignore_index=True)

# -------------- Limpeza / imputação de segurança --------------
feature_cols = [
    "tempo_uso","ciclos","temperatura","vibracao",
    "temp_mean_3","vib_mean_3","temp_std_3","vib_std_3","ciclos_delta_3","uso_delta_3",
    "temp_mean_6","vib_mean_6","temp_std_6","vib_std_6","ciclos_delta_6","uso_delta_6",
    "temp_mean_12","vib_mean_12","temp_std_12","vib_std_12","ciclos_delta_12","uso_delta_12",
]

# ffill/bfill por peça para temp/vib (se necessário)
df_feat["temperatura"] = df_feat.groupby("id_peca")["temperatura"].ffill().bfill()
df_feat["vibracao"]    = df_feat.groupby("id_peca")["vibracao"].ffill().bfill()

# fallback global e sanitização
for col in feature_cols:
    med = df_feat[col].median() if col in df_feat and not df_feat[col].dropna().empty else 0.0
    df_feat[col] = df_feat[col].fillna(med).replace([np.inf, -np.inf], 0.0).astype(float)

df_feat = df_feat.sort_values("leitura_data_hora").reset_index(drop=True)

# -------------- Split temporal --------------
y = df_feat["fail_next_h"].astype(int)
if y.nunique() < 2:
    pos = int(y.sum())
    neg = int((y == 0).sum())
    print(f"  Dataset sem diversidade de classes (positivos={pos}, negativos={neg}).")
    print("   Gere alguns eventos de FALHA (tabela FALHAS) e gere o CSV novamente (app.generate_csv).")
    raise SystemExit(2)

cut_idx = int(len(df_feat) * 0.7) if len(df_feat) > 2 else len(df_feat)
train = df_feat.iloc[:cut_idx]
test  = df_feat.iloc[cut_idx:] if cut_idx < len(df_feat) else df_feat.iloc[-1:]

X_train, y_train = train[feature_cols], train["fail_next_h"].astype(int)
X_test,  y_test  = test[feature_cols],  test["fail_next_h"].astype(int)

if y_train.nunique() < 2:
    pos = int(y_train.sum()); neg = int((y_train == 0).sum())
    print(f"⚠️  Treino sem diversidade de classes (positivos={pos}, negativos={neg}).")
    raise SystemExit(2)

# -------------- Modelo --------------
clf = GradientBoostingClassifier(random_state=RANDOM_SEED)
clf.fit(X_train, y_train)

# -------------- Avaliação --------------
has_proba = hasattr(clf, "predict_proba")
if has_proba and len(X_test) > 0:
    y_prob = clf.predict_proba(X_test)[:, 1]
else:
    # fallback via decisão -> sigmoid
    raw = clf.decision_function(X_test) if hasattr(clf, "decision_function") else clf.predict(X_test)
    y_prob = 1 / (1 + np.exp(-np.array(raw, dtype=float)))

y_pred = (y_prob >= 0.5).astype(int)

print("\n=== Classification Report (Falha próximas {}h) ===".format(HORIZON_H))
print(classification_report(y_test, y_pred, digits=4))

try:
    auc = roc_auc_score(y_test, y_prob)
    print(f"ROC-AUC: {auc:.4f}")
except Exception:
    auc = None
    print("ROC-AUC não pôde ser calculado (talvez apenas uma classe no conjunto de teste).")

cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
plt.figure(figsize=(5, 4))
plt.imshow(cm, interpolation="nearest")
plt.title(f"Matriz de Confusão - Falha próximas {HORIZON_H}h")
plt.colorbar()
plt.xticks([0, 1], ["Sem falha", "Falha"], rotation=45)
plt.yticks([0, 1], ["Sem falha", "Falha"])
plt.ylabel("Real")
plt.xlabel("Previsto")
plt.tight_layout()
plt.savefig(ASSETS_DIR / f"matriz_confusao_falha_{HORIZON_H}h.png", dpi=140)
plt.close()

if auc is not None:
    try:
        fpr, tpr, _ = roc_curve(y_test, y_prob)
        plt.figure(figsize=(5, 4))
        plt.plot(fpr, tpr, label=f"AUC={auc:.3f}")
        plt.plot([0, 1], [0, 1], linestyle="--")
        plt.xlabel("FPR")
        plt.ylabel("TPR")
        plt.title(f"ROC - Falha próximas {HORIZON_H}h")
        plt.legend(loc="lower right")
        plt.tight_layout()
        plt.savefig(ASSETS_DIR / f"roc_falha_{HORIZON_H}h.png", dpi=140)
        plt.close()
    except Exception:
        pass

# -------------- Salvar modelo --------------
out_path = MODEL_DIR / "modelo_falha_24h.joblib"
joblib.dump(clf, out_path)
print(f"\n Modelo salvo em {out_path}")
print(f" Gráficos salvos em {ASSETS_DIR}/matriz_confusao_falha_{HORIZON_H}h.png"
      f"{' e ' + str(ASSETS_DIR / f'roc_falha_{HORIZON_H}h.png') if auc is not None else ''}")
