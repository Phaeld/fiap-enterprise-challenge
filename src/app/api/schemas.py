from marshmallow import Schema, fields

class ReadingInSchema(Schema):
    id_sensor = fields.Int(required=True)
    leitura_valor = fields.Float(required=True)
    leitura_data_hora = fields.DateTime(required=True)  # ISO 8601

class PredictStateIn(Schema):
    tempo_uso = fields.Float(required=True)
    ciclos = fields.Float(required=True)
    temperatura = fields.Float(required=True)
    vibracao = fields.Float(required=True)
