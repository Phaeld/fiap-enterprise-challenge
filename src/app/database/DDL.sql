-- =========================================================
-- DDL MySQL – challenge DB
-- Compatível com MySQL 8.x
-- =========================================================

CREATE DATABASE IF NOT EXISTS challenge;
USE challenge;

-- Tabela: PECAS
CREATE TABLE IF NOT EXISTS PECAS (
    id_peca INT AUTO_INCREMENT PRIMARY KEY,
    tipo VARCHAR(100) NOT NULL,
    fabricante VARCHAR(100),
    tempo_uso_total INT
);

-- Tabela: SENSORES
CREATE TABLE IF NOT EXISTS SENSORES (
    id_sensor INT AUTO_INCREMENT PRIMARY KEY,
    tipo_sensor VARCHAR(50) NOT NULL,
    id_peca INT,
    CONSTRAINT FK_SENSORES_PECAS
        FOREIGN KEY (id_peca) REFERENCES PECAS(id_peca)
        ON DELETE SET NULL
);

CREATE INDEX IX_SENSORES_ID_PECA ON SENSORES(id_peca);

-- Tabela: CICLOS_OPERACAO
CREATE TABLE IF NOT EXISTS CICLOS_OPERACAO (
    id_ciclo INT AUTO_INCREMENT PRIMARY KEY,
    id_peca INT,
    data_inicio DATETIME,
    data_fim DATETIME,
    duracao INT,
    CONSTRAINT FK_CICLOS_PECAS
        FOREIGN KEY (id_peca) REFERENCES PECAS(id_peca)
        ON DELETE CASCADE
);

CREATE INDEX IX_CICLOS_ID_PECA ON CICLOS_OPERACAO(id_peca);

-- Tabela: LEITURAS_SENSOR
CREATE TABLE IF NOT EXISTS LEITURAS_SENSOR (
    id_leitura INT AUTO_INCREMENT PRIMARY KEY,
    id_sensor INT,
    leitura_valor DECIMAL(12,4),
    leitura_data_hora DATETIME,
    CONSTRAINT FK_LEITURAS_SENSORES
        FOREIGN KEY (id_sensor) REFERENCES SENSORES(id_sensor)
        ON DELETE CASCADE
);

CREATE INDEX IX_LEITURAS_ID_SENSOR ON LEITURAS_SENSOR(id_sensor);

-- Tabela: FALHAS
CREATE TABLE IF NOT EXISTS FALHAS (
    id_falha INT AUTO_INCREMENT PRIMARY KEY,
    id_peca INT,
    descricao VARCHAR(255),
    data DATETIME,
    CONSTRAINT FK_FALHAS_PECAS
        FOREIGN KEY (id_peca) REFERENCES PECAS(id_peca)
        ON DELETE CASCADE
);

CREATE INDEX IX_FALHAS_ID_PECA ON FALHAS(id_peca);

-- Tabela: ALERTAS
CREATE TABLE IF NOT EXISTS ALERTAS (
    id_alerta INT AUTO_INCREMENT PRIMARY KEY,
    id_falha INT,
    nivel_risco VARCHAR(20),
    CONSTRAINT FK_ALERTAS_FALHAS
        FOREIGN KEY (id_falha) REFERENCES FALHAS(id_falha)
        ON DELETE CASCADE
);

CREATE INDEX IX_ALERTAS_ID_FALHA ON ALERTAS(id_falha);
