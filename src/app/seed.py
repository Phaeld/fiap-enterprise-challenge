# app/seed.py
import time
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from flask import current_app
from .wsgi import app
from .extensions import db
from .models import Peca, Sensor

PEÇAS_PADRÃO = [
    {"tipo": "Conjunto A", "fabricante": "Hermes", "tempo_uso_total": 0},
    {"tipo": "Conjunto B", "fabricante": "Hermes", "tempo_uso_total": 0},
    {"tipo": "Conjunto C", "fabricante": "Hermes", "tempo_uso_total": 0},
]
TIPOS_SENSORES = ["vibracao", "temperatura"]

def wait_for_db(max_tries=30, sleep=2):
    for i in range(max_tries):
        try:
            with app.app_context():
                # força uma conexão simples
                db.session.execute(text("SELECT 1"))
                return
        except OperationalError as e:
            print(f"[seed] aguardando DB... ({i+1}/{max_tries}) {e}")
            time.sleep(sleep)
    raise RuntimeError("[seed] DB não respondeu a tempo")

def ensure_seed():
    with app.app_context():
        # 1) se não houver ao menos 1 peça E 1 sensor, criamos 3 peças e 2 sensores/peça
        qtd_pecas = db.session.query(Peca).count()
        qtd_sensores = db.session.query(Sensor).count()
        if qtd_pecas == 0 and qtd_sensores == 0:
            print("[seed] criando 3 peças e 2 sensores (vibração/temperatura) para cada...")
            pecas = []
            for data in PEÇAS_PADRÃO:
                p = Peca(**data)
                db.session.add(p)
                pecas.append(p)
            db.session.flush()  # garante IDs

            for p in pecas:
                for tipo in TIPOS_SENSORES:
                    db.session.add(Sensor(tipo_sensor=tipo, id_peca=p.id_peca))
            db.session.commit()
            print("[seed] seed inicial criado.")
            return

        # 2) caso já existam peças, completa sensores faltantes por peça
        if qtd_pecas > 0:
            print("[seed] verificando sensores faltantes por peça...")
            pecas = db.session.query(Peca).all()
            criados = 0
            for p in pecas:
                existentes = {s.tipo_sensor for s in p.sensores}
                faltantes = [t for t in TIPOS_SENSORES if t not in existentes]
                for t in faltantes:
                    db.session.add(Sensor(tipo_sensor=t, id_peca=p.id_peca))
                    criados += 1
            if criados:
                db.session.commit()
                print(f"[seed] sensores adicionados: {criados}")
            else:
                print("[seed] nada a completar.")
        else:
            print("[seed] há sensores mas nenhuma peça — sem alterações.")

if __name__ == "__main__":
    print("[seed] iniciando...")
    wait_for_db()
    ensure_seed()
    print("[seed] ok.")
