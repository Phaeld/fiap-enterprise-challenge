"""
Gera um CSV com leituras + features e colunas de risco de falha usando o modelo em app/ml.

Como rodar (recomendado):
    docker compose exec web python -m app.generate_csv
Ou do host (estando em ./src):
    python -m app.generate_csv

Ambiente:
    DB_HOST (default: 'db' se em Docker, senão 'localhost')
    DB_USER (default: app)
    DB_PASS (default: app)
    DB_NAME (default: challenge)
    DB_PORT (default: 3306)
    OUTPUT_CSV (default: app/app/database/sensores.csv no container, src/app/database/sensores.csv no host)
    FAIL_THRESHOLD   (default: 0.5)  -> limiar binário do modelo
    RISK_THRESH_HIGH (default: 0.7)  -> risco "alto"
    RISK_THRESH_MED  (default: 0.4)  -> risco "medio"
"""

import os
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine

# --- DB config ---
IN_DOCKER = os.path.exists("/.dockerenv")
DB_HOST = os.getenv("DB_HOST", "db" if IN_DOCKER else "localhost")
DB_USER = os.getenv("DB_USER", "app")
DB_PASS = os.getenv("DB_PASS", "app")
DB_NAME = os.getenv("DB_NAME", "challenge")
DB_PORT = int(os.getenv("DB_PORT", "3306"))

DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

# --- Output path ---
DEFAULT_OUT = "src/app/database/sensores.csv"
if IN_DOCKER:
    DEFAULT_OUT = "/app/app/database/sensores.csv"
OUTPUT_CSV = os.getenv("OUTPUT_CSV", DEFAULT_OUT)

# --- Risk thresholds ---
FAIL_THRESHOLD   = float(os.getenv("FAIL_THRESHOLD", "0.5"))
RISK_THRESH_HIGH = float(os.getenv("RISK_THRESH_HIGH", "0.7"))
RISK_THRESH_MED  = float(os.getenv("RISK_THRESH_MED", "0.4"))

# --- Import do modelo ---
# (execute em modo módulo: `python -m app.generate_csv`)
from app.ml import predict as ml_predict


def load_data(engine):
    """Carrega leituras, ciclos e falhas do banco."""
    # Leituras + metadados do sensor/peça
    sql_readings = """
    SELECT
      l.id_leitura,
      l.id_sensor,
      s.id_peca,
      s.tipo_sensor AS sensor_tipo,
      l.leitura_data_hora,
      l.leitura_valor
    FROM LEITURAS_SENSOR l
    JOIN SENSORES s ON s.id_sensor = l.id_sensor
    ORDER BY s.id_peca, l.leitura_data_hora ASC, l.id_leitura ASC;
    """
    df = pd.read_sql(sql_readings, engine)
    df["leitura_data_hora"] = pd.to_datetime(df["leitura_data_hora"])

    # Ciclos (para tempo_uso e contagem)
    sql_cycles = """
    SELECT id_ciclo, id_peca, data_inicio, data_fim, duracao
    FROM CICLOS_OPERACAO
    ORDER BY id_peca, data_inicio ASC;
    """
    cdf = pd.read_sql(sql_cycles, engine)
    if not cdf.empty:
        cdf["data_inicio"] = pd.to_datetime(cdf["data_inicio"])
        cdf["data_fim"] = pd.to_datetime(cdf["data_fim"])

    # Falhas (eventos reais)
    sql_fail = """
    SELECT id_falha, id_peca, `data`
    FROM FALHAS
    ORDER BY id_peca, `data` ASC;
    """
    fdf = pd.read_sql(sql_fail, engine)
    if not fdf.empty:
        fdf["data"] = pd.to_datetime(fdf["data"])

    return df, cdf, fdf


def asof_fill(base_df, right_df, value_col, by_key="id_peca", time_col="leitura_data_hora"):
    """
    Faz merge_asof por peça para pegar o último valor <= timestamp.
    - Garante sort adequado.
    - Preserva a ordem original do base_df.
    - Fallback por peça se houver qualquer problema de ordenação.
    """
    import pandas as pd

    base = base_df[[by_key, time_col]].copy()
    right = right_df[[by_key, time_col, value_col]].copy()

    base[time_col] = pd.to_datetime(base[time_col], utc=True, errors="coerce")
    right[time_col] = pd.to_datetime(right[time_col], utc=True, errors="coerce")

    base = base.dropna(subset=[time_col])
    right = right.dropna(subset=[time_col])

    base_sorted = base.sort_values([by_key, time_col]).reset_index()  # guarda índice original
    right_sorted = right.sort_values([by_key, time_col])

    try:
        merged = pd.merge_asof(
            base_sorted,
            right_sorted,
            by=by_key,
            on=time_col,
            direction="backward",
        )
        out = merged.set_index("index")[value_col].reindex(base_df.index)
        return out
    except Exception:
        out = pd.Series(index=base_df.index, dtype=float)
        for pid, g in base.groupby(by_key):
            g2 = g.sort_values(time_col).reset_index()  # "index" -> índice original
            r2 = right[right[by_key] == pid].sort_values(time_col)
            if r2.empty:
                continue
            m = pd.merge_asof(g2, r2, on=time_col, direction="backward")
            out.loc[m["index"]] = m[value_col].values
        return out.reindex(base_df.index)


def compute_usage_and_cycles_for_piece(base_piece: pd.DataFrame, cycles_piece: pd.DataFrame):
    """Acumula tempo_uso (min) e contagem de ciclos até cada timestamp."""
    if cycles_piece.empty:
        return (
            pd.Series([0.0] * len(base_piece), index=base_piece.index),
            pd.Series([0] * len(base_piece), index=base_piece.index),
        )

    starts = cycles_piece["data_inicio"].tolist()
    ends   = cycles_piece["data_fim"].tolist()
    durs   = cycles_piece["duracao"].tolist()

    tempo_uso, ciclos = [], []
    for t in base_piece["leitura_data_hora"]:
        ciclos_count = sum(1 for st in starts if pd.notna(st) and st <= t)
        ciclos.append(int(ciclos_count))

        acc = 0.0
        for st, fi, dur in zip(starts, ends, durs):
            if pd.isna(st):
                continue
            if pd.isna(fi):  # ciclo aberto
                if t >= st:
                    acc += max(0.0, (t - st).total_seconds() / 60.0)
            else:
                if fi <= t:
                    acc += float(dur if not pd.isna(dur) else max(0.0, (fi - st).total_seconds() / 60.0))
                elif st <= t < fi:
                    acc += max(0.0, (t - st).total_seconds() / 60.0)
        tempo_uso.append(acc)

    return pd.Series(tempo_uso, index=base_piece.index), pd.Series(ciclos, index=base_piece.index)


def build_dataset(df: pd.DataFrame, cdf: pd.DataFrame, fdf: pd.DataFrame) -> pd.DataFrame:
    """Monta dataset base e acrescenta falha_evento a partir da tabela FALHAS."""
    df["sensor_tipo_norm"] = df["sensor_tipo"].str.lower()

    # Base: linhas de temperatura (se não houver, usa vibração)
    base = df[df["sensor_tipo_norm"].str.contains("temper", na=False)].copy()
    if base.empty:
        base = df[df["sensor_tipo_norm"].str.contains("vibra", na=False)].copy()

    # Séries por tipo para preencher colunas de features
    temp = df[df["sensor_tipo_norm"].str.contains("temper", na=False)][
        ["id_peca", "leitura_data_hora", "leitura_valor"]
    ].rename(columns={"leitura_valor": "temperatura"})
    vib = df[df["sensor_tipo_norm"].str.contains("vibra", na=False)][
        ["id_peca", "leitura_data_hora", "leitura_valor"]
    ].rename(columns={"leitura_valor": "vibracao"})

    base["temperatura"] = asof_fill(base, temp, "temperatura")
    base["vibracao"]    = asof_fill(base, vib,  "vibracao")

    base = base.sort_values(["id_peca", "leitura_data_hora"]).copy()
    base["tempo_uso"] = 0.0
    base["ciclos"]    = 0

    if not cdf.empty:
        for peca_id, grp in base.groupby("id_peca"):
            ciclos_piece = cdf[cdf["id_peca"] == peca_id].copy()
            tuso, cc = compute_usage_and_cycles_for_piece(grp, ciclos_piece)
            base.loc[grp.index, "tempo_uso"] = tuso
            base.loc[grp.index, "ciclos"]    = cc

    out = base[
        ["id_leitura","id_sensor","id_peca","sensor_tipo","leitura_data_hora",
         "tempo_uso","ciclos","temperatura","vibracao"]
    ].sort_values(["id_peca","leitura_data_hora","id_leitura"])

    out["tempo_uso"]   = out["tempo_uso"].round(2)
    out["temperatura"] = out["temperatura"].astype(float).round(2)
    out["vibracao"]    = out["vibracao"].astype(float).round(2)

    # ---- falha_evento (1 se há falha real próximo ao timestamp) ----
    out["falha_evento"] = 0
    if fdf is not None and not fdf.empty:
        tol = pd.Timedelta("60s")  # tolerância para casar exatamente o timestamp
        for peca_id, grp in out.groupby("id_peca"):
            eventos = fdf[fdf["id_peca"] == peca_id][["data"]].sort_values("data")
            if eventos.empty:
                continue
            m = pd.merge_asof(
                grp[["leitura_data_hora"]].sort_values("leitura_data_hora").reset_index(),
                eventos.rename(columns={"data": "falha_data"}).sort_values("falha_data"),
                left_on="leitura_data_hora",
                right_on="falha_data",
                direction="nearest",
                tolerance=tol,
            )
            idx_hit = m.loc[m["falha_data"].notna(), "index"]
            out.loc[idx_hit, "falha_evento"] = 1

    return out


def add_failure_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Imputa faltantes (por peça) e calcula:
      - falha (0/1), risco_falha (baixo/medio/alto), falha_prob (score do modelo)
    """
    df = df.copy().sort_values(["id_peca", "leitura_data_hora"])

    # ffill/bfill por peça
    df["temperatura"] = df.groupby("id_peca")["temperatura"].ffill().bfill()
    df["vibracao"]    = df.groupby("id_peca")["vibracao"].ffill().bfill()

    # fallback global
    for col in ["temperatura", "vibracao", "tempo_uso", "ciclos"]:
        med = df[col].median() if col in df and not df[col].dropna().empty else 0.0
        df[col] = df[col].fillna(med).fillna(0.0).astype(float)

    probs, flags, risks = [], [], []

    for _, r in df.iterrows():
        payload = {
            "tempo_uso": float(r["tempo_uso"]),
            "ciclos": float(r["ciclos"]),
            "temperatura": float(r["temperatura"]),
            "vibracao": float(r["vibracao"]),
        }
        res  = ml_predict.predict_failure_24h(payload, threshold=FAIL_THRESHOLD)
        prob = float(res["prob"])
        flag = int(res["falha_prox_24h"])

        if prob >= RISK_THRESH_HIGH:
            risk = "alto"
        elif prob >= RISK_THRESH_MED:
            risk = "medio"
        else:
            risk = "baixo"

        probs.append(round(prob, 3))
        flags.append(flag)
        risks.append(risk)

    df["falha"] = flags              # 0/1 (pela regra do threshold)
    df["risco_falha"] = risks        # baixo/medio/alto
    df["falha_prob"] = probs         # score contínuo
    return df


def main():
    print(f"→ Lendo do MySQL {DB_URL}")
    engine = create_engine(DB_URL)

    df, cdf, fdf = load_data(engine)
    if df.empty:
        print("⚠️  Nenhuma leitura encontrada. Rode o simulador primeiro.")
        return

    out = build_dataset(df, cdf, fdf)
    out = add_failure_columns(out)

    Path(os.path.dirname(OUTPUT_CSV)).mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_CSV, index=False, encoding="utf-8")
    print(f"✅ CSV gerado em {OUTPUT_CSV} com {len(out)} linhas.")
    print("   Colunas:", ", ".join(out.columns))


if __name__ == "__main__":
    main()
