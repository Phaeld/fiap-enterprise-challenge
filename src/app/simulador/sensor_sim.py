# app/simulator/sensor_sim.py
import os, time, random
import requests
from datetime import datetime, timezone, timedelta

API = os.getenv("API_URL", "http://web:5000/api/readings")

def parse_sensors(env):
    try:
        return [int(x) for x in env.split(",") if x.strip()]
    except:
        return [1]
SENSORS = parse_sensors(os.getenv("SENSORS", "1,2,3,4"))

INTERVAL = float(os.getenv("INTERVAL_SEC", "2"))
CYCLE_SECONDS = int(os.getenv("CYCLE_SECONDS", "120"))
ALERT_THRESH = float(os.getenv("ALERT_THRESH", "80"))
ALERT_MIN_STREAK = int(os.getenv("ALERT_MIN_STREAK", "3"))
API_CYCLE = os.getenv("API_CYCLE_URL", "http://web:5000/api/cycle-events")
API_ALERT = os.getenv("API_ALERT_URL", "http://web:5000/api/alerts")

def post_json(url, payload):
    r = requests.post(url, json=payload, timeout=5)
    r.raise_for_status()
    return r.json()

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def main():
    print(f"[sim] Enviando leituras p/ {API} a cada {INTERVAL}s. Sensores: {SENSORS}")
    # Para demo: iniciamos um "ciclo" por peça a cada CYCLE_SECONDS
    last_cycle_start = datetime.now(timezone.utc)
    over_thresh_streak = {sid: 0 for sid in SENSORS}

    while True:
        # 1) Ciclo: abre/fecha de tempos em tempos
        if (datetime.now(timezone.utc) - last_cycle_start).total_seconds() >= CYCLE_SECONDS:
            try:
                # encerra e inicia um novo ciclo (evento)
                post_json(API_CYCLE, {"event": "end_all", "ts": now_iso()})
                post_json(API_CYCLE, {"event": "start_all", "ts": now_iso()})
                print("[sim] Ciclo reiniciado para todas as peças.")
            except Exception as e:
                print("[sim] Falha ao registrar ciclo:", e)
            last_cycle_start = datetime.now(timezone.utc)

        # 2) Leituras
        sensor_id = random.choice(SENSORS)
        # exemplo: simulando valor "temperatura/vibração"
        base = 50 + 15*random.random()            # 50~65
        spike = 35 if random.random() < 0.1 else 0  # 10% chance de spike
        valor = round(base + spike, 2)
        ts = now_iso()

        payload = {
            "id_sensor": sensor_id,
            "leitura_valor": valor,
            "leitura_data_hora": ts
        }

        try:
            post_json(API, payload)
            # 3) Limiar -> ALARMEs simples (popular ALERTAS)
            if valor >= ALERT_THRESH:
                over_thresh_streak[sensor_id] += 1
            else:
                over_thresh_streak[sensor_id] = 0

            if over_thresh_streak[sensor_id] >= ALERT_MIN_STREAK:
                try:
                    post_json(API_ALERT, {
                        "id_sensor": sensor_id,
                        "nivel_risco": "ALTO",
                        "valor": valor,
                        "ts": ts
                    })
                    print(f"[sim] ALERTA gerado sensor={sensor_id}, valor={valor}")
                    over_thresh_streak[sensor_id] = 0
                except Exception as e:
                    print("[sim] Falha ao criar alerta:", e)

            print("[sim] OK", payload)
        except Exception as e:
            print("[sim] Erro:", e)

        time.sleep(INTERVAL)

if __name__ == "__main__":
    main()
