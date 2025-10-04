from .extensions import db

class Peca(db.Model):
    __tablename__ = "PECAS"
    id_peca = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(100), nullable=False)
    fabricante = db.Column(db.String(100))
    tempo_uso_total = db.Column(db.Integer)

class Sensor(db.Model):
    __tablename__ = "SENSORES"
    id_sensor = db.Column(db.Integer, primary_key=True)
    tipo_sensor = db.Column(db.String(50), nullable=False)
    id_peca = db.Column(db.Integer, db.ForeignKey("PECAS.id_peca"))
    peca = db.relationship("Peca", backref="sensores")

class Ciclo(db.Model):
    __tablename__ = "CICLOS_OPERACAO"
    id_ciclo = db.Column(db.Integer, primary_key=True)
    id_peca = db.Column(db.Integer, db.ForeignKey("PECAS.id_peca"))
    data_inicio = db.Column(db.DateTime)
    data_fim = db.Column(db.DateTime)
    duracao = db.Column(db.Integer)

class Leitura(db.Model):
    __tablename__ = "LEITURAS_SENSOR"
    id_leitura = db.Column(db.Integer, primary_key=True)
    id_sensor = db.Column(db.Integer, db.ForeignKey("SENSORES.id_sensor"))
    leitura_valor = db.Column(db.Float)
    leitura_data_hora = db.Column(db.DateTime)

class Falha(db.Model):
    __tablename__ = "FALHAS"
    id_falha = db.Column(db.Integer, primary_key=True)
    id_peca = db.Column(db.Integer, db.ForeignKey("PECAS.id_peca"))
    descricao = db.Column(db.String(255))
    data = db.Column(db.DateTime)

class Alerta(db.Model):
    __tablename__ = "ALERTAS"
    id_alerta = db.Column(db.Integer, primary_key=True)
    id_falha = db.Column(db.Integer, db.ForeignKey("FALHAS.id_falha"))
    nivel_risco = db.Column(db.String(20))
