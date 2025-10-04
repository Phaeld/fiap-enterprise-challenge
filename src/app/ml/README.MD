# Machine Learning

Este diretório contém os modelos da Fase 5:

1) **Classificação do estado da peça** (Saudável / Desgastada / Crítica)  
2) **Previsão de falha em horizonte fixo** (por padrão, próximas 24h)

Os modelos usam o dataset consolidado em `src/app/database/sensores.csv`.

---

## 📦 Requisitos

```bash
python >= 3.9
pip install -r requirements.txt

### Conteúdo sugerido de requirements.txt:
```bash
pandas
numpy
scikit-learn
matplotlib
joblib

Caso esteja em ambiente fechado (ex.: EC2), crie um venv:
python -m venv .venv && source .venv/bin/activate (Linux/Mac)
.\.venv\Scripts\activate (Windows)

machine_learning/
    classificar_estado_peca.py
    prever_falha_proximas_24h.py
    models/
        modelo_estado_peca.joblib
        modelo_falha_24h.joblib
    README.md   <- este arquivo
assets/
    matriz_confusao_estado.png
    feature_importance_estado.png
    matriz_confusao_falha_24h.png
    roc_falha_24h.png

## 🧠 Modelos
1) Classificação do estado da peça

Arquivo: classificar_estado_peca.py

Objetivo: classificar cada peça em Saudável / Desgastada / Crítica
(mapeados do rótulo risco_falha presente no CSV).

Entradas (features): tempo_uso, ciclos, temperatura, vibracao.

Modelo: RandomForestClassifier (sklearn).

Split: temporal — 70% inicial para treino, 30% final para teste.

Saídas:

assets/matriz_confusao_estado.png

assets/feature_importance_estado.png

src/machine_learning/models/modelo_estado_peca.joblib

### Como rodar:
```bash
python src/machine_learning/classificar_estado_peca.py

## 2) Previsão de falha (horizonte fixo)

Arquivo: prever_falha_proximas_24h.py

Objetivo: prever se haverá falha para a mesma peça nas próximas 24h (parâmetro HORIZON_H).

Rótulo: fail_next_h (gerado a partir da coluna falha==1 no futuro da peça).

Features:

Básicas: tempo_uso, ciclos, temperatura, vibracao

De janela: médias e desvios (3, 6, 12 janelas), variações de ciclos/tempo_uso

Modelo: GradientBoostingClassifier (sklearn).

Split: temporal — 70% inicial treino, 30% final teste.

Saídas:

assets/matriz_confusao_falha_24h.png

assets/roc_falha_24h.png

src/machine_learning/models/modelo_falha_24h.joblib

### Como rodar
```bash
python src/machine_learning/prever_falha_proximas_24h.py


##⚙️ Parâmetros e caminhos

Caminho do CSV: src/app/database/sensores.csv
(ajuste a constante CSV_PATH nos scripts, se necessário).

Horizonte de previsão (falha): altere HORIZON_H = 24 para 12/48/etc.

Seed dos modelos: RANDOM_SEED = 42.


## 📊 Métricas & Artefatos

Classificação de estado: relatório de classificação + matriz de confusão; gráfico de importância de features para explicar o modelo.

Previsão de falha: relatório de classificação, ROC-AUC (quando possível), matriz de confusão e curva ROC.

Gráficos são salvos em assets/. Modelos .joblib em src/machine_learning/models/.

## 🧪 Reprodutibilidade

Garanta que sensores.csv está presente e com as colunas:

id_peca, leitura_data_hora, tempo_uso, ciclos, temperatura, vibracao, falha, risco_falha

Rode os dois scripts exatamente nas instruções acima (seed fixa).

Resultados (métricas/plots) serão reprodutíveis para o mesmo CSV.

## 🛠️ Dicas & Troubleshooting

Classe rara (poucas falhas):

Aumente HORIZON_H (ex.: 48h) para ter mais positivos.

Use class_weight='balanced' (ou SMOTE) se necessário.

Vazamento temporal: os splits já são temporais. Evite embaralhar.

Colunas nulas: se temperatura/vibracao tiverem nulos, revise seu processo de consolidação (último valor conhecido).

Ambiente sem GUI: o matplotlib salva imagens em arquivo; não requer display.