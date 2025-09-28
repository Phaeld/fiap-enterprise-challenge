# FIAP - Faculdade de Informática e Administração Paulista 

<p align="center">
<a href= "https://www.fiap.com.br/"><img src="assets/logo-fiap.png" alt="FIAP - Faculdade de Informática e Admnistração Paulista" border="0" width=40% height=40%></a>
</p>

<br>

# FIAP x Hermes Reply — Monitoramento de Deterioração e Vida Útil das Peças

## Grupo Sp e Interior

## 👨‍🎓 Integrantes: 
- <a href="https://www.linkedin.com/in/jonastadeufernandes/?locale=en_US">Jonas Tadeu V Fernandes</a>
- <a href="">Levi Passos Silveira Marques</a>
- <a href="">Raphael da Silva</a> 
- <a href="[https://www.linkedin.com/company/inova-fusca](https://www.linkedin.com/in/raphael-dinelli-8a01b278/)">Raphael Dinelli Neto</a>

**Curso:** FIAP — Fase 6  
**Empresa parceira:** Hermes Reply  
**Tema:** Criação MVP ESP32 + Sensores IoT, Banco de Dados, modelo Machine Learning e dashboard/relatório

## 👩‍🏫 Professores:
### Tutor(a) 
- <a href="https://www.linkedin.com/company/inova-fusca">Leonardo Ruiz Orbana</a>
### Coordenador(a)
- <a href="https://www.linkedin.com/company/inova-fusca">André Godoi Chiovato</a>

## 📜 Descrição

# 🚜 Monitoramento de Deterioração e Vida Útil das Peças

Este projeto foi desenvolvido pelo grupo **SP e Interior** como parte do desafio proposto pela empresa **Hermes Reply**, em parceria com a FIAP. A proposta visa aplicar técnicas de **Machine Learning** e **IoT** para prever falhas e estimar a vida útil de componentes mecânicos utilizados em ambientes industriais.

Nosso objetivo é permitir **manutenção preditiva**, minimizando o tempo de máquina parada e reduzindo custos operacionais.

---

## 🎯 Objetivo do Sistema

Estimar a vida útil de peças e componentes com base em:

- Tempo de uso (em horas)
- Número de ciclos de operação (liga/desliga)
- Registro de temperatura durante o funcionamento
- Dados de vibração (opcional)
- Histórico de falhas anteriores

Esses dados serão processados por modelos de Machine Learning que irão prever o risco de falha iminente e gerar alertas automatizados.

---

## 🧠 Tecnologias Utilizadas

| Camada             | Tecnologia                          | Justificativa |
|--------------------|-------------------------------------|---------------|
| **Sensoriamento**  | ESP32                               | Coleta local de tempo, ciclos, temperatura e vibração |
| **Armazenamento**  | AWS RDS (MySQL) ou DynamoDB         | Armazenamento confiável e escalável |
| **Backend**        | Python                              | Processamento dos dados e integração com IA |
| **Machine Learning**| Scikit-learn / TensorFlow          | Modelagem e predição de falhas |
| **Análise de Dados**| Pandas / NumPy                     | Manipulação e análise de dados históricos |
| **Visualização**   | Matplotlib / Seaborn                | Geração de gráficos e dashboards |
| **Nuvem**          | AWS EC2                             | Processamento remoto e simulação de ambiente industrial |

---

## 🔌 Pipeline de Dados

1. **Coleta de Dados (ESP32)**  
   - Tempo de uso
   - Temperatura
   - Ciclos de operação
   - Vibração (opcional)

2. **Envio dos Dados (simulado via script Python)**  
   - Comunicação com o banco de dados

3. **Armazenamento (AWS RDS / DynamoDB)**  
   - Histórico estruturado e seguro

4. **Processamento (EC2)**  
   - Modelos de ML treinados para predição de falhas. A predileção por EC2 ao invés de ambiente local é devido a custos e facilidade de manutenção da infra-estrutura.

5. **Visualização e Alertas**  
   - Dashboards e alertas automatizados com base nas previsões

---

## 🖼️ Arquitetura da Solução

A imagem abaixo representa a arquitetura proposta do sistema, integrando sensores, banco de dados e modelos de IA:

<img src="./assets/enterprise-challenge.JPG">

---

## 📆 Plano de Desenvolvimento

1. Simulação dos dados de sensores
2. Modelagem relacional do banco de dados
3. Criação do pipeline de ingestão e armazenamento
4. Desenvolvimento do modelo de IA
5. Criação de dashboards com alertas preditivos
6. Integração final e testes

---

# Objetivo desta etapa
Construir um **banco de dados relacional** normalizado para armazenar leituras de sensores industriais e, a partir desses dados, treinar **dois modelos de ML**:
1. **Classificação** do estado da peça (**Saudável / Desgastada / Crítica**).
2. **Previsão** de falha em horizonte fixo (**próximas 24h**).

## Visão Geral da Solução
- **Coleta (simulada):** leituras de temperatura/vibração + tempo de uso e ciclos.  
- **Armazenamento:** modelo relacional com tabelas de peças, sensores, ciclos, leituras, falhas e alertas.  
- **ML:**  
  - Modelo 1: RandomForest multiclasse (estado da peça).  
  - Modelo 2: GradientBoosting binário (falha em 24h) com features de janela.  
- **Documentação:** DER exportado, DDL, CSV e gráficos de resultado.

## 🧱 Modelagem de Banco de Dados

### Principais Entidades:

- **PECAS**: id_peca (PK), tipo, fabricante, tempo_uso_total
- **SENSORES**: id_sensor (PK), tipo_sensor, id_peca (FK -> PECAS)
- **CICLOS_OPERACAO**: id_ciclo (PK), id_peca (FK -> PECAS), data_inicio, data_fim, duracao
- **LEITURAS_SENSOR**: id_leitura (PK), id_sensor (FK -> SENSORES), leitura_valor, leitura_data_hora
- **FALHAS**: id_falha (PK), id_peca (FK PECAS), descricao, data
- **ALERTAS**: id_alerta (PK), id_falha (FK -> FALHAS), nivel_risco

### Relacionamentos:

- Uma peça possui vários sensores (1:N)
- Uma peça possui vários ciclos de operação (1:N)
- Cada ciclo possui várias leituras (1:N)
- Uma peça pode ter várias falhas (1:N)
- Cada falha pode gerar múltiplos alertas (1:N)

### DDL
 - `src/database/DDL.sql`

### DER
Imagem exportada do Oracle SQL Developer Data Modeler:
- `assets/Diagrama-ER.png`

<p align="center">
  <img src="assets/Diagrama-ER.png" alt="DER" width="85%">
</p>

### Script DDL
- `src/database/DDL.sql`  

---

## 📊 Estratégia de Coleta de Dados

Nesta fase inicial, os dados serão **simulados** por meio de scripts Python que imitam a operação dos sensores conectados a um ESP32.
Devido a quantidade de sensores e dados necessários para treinar os modelos, optamos pela simulação via script, pois permite maior aleatóriedade dos dados.

Serão gerados:

- Ciclos de operação aleatórios
- Leituras de temperatura variando com o tempo
- Eventos de falha simulados para treinar o modelo

Em fases futuras, será possível realizar a **integração real com sensores físicos ESP32**, via conexão Wi-Fi e envio dos dados diretamente para o banco na nuvem.

**Script para consolidação dos dados das tabelas sql em arquivo csv**: `src/database/csv_create.sql`

---

## ESP32 e Sensores IoT

<img src="./assets/esp.png">

### Microcontrolador ESP323

O microcontrolador ESP32 é o hardware principal, sendo ele responsável pegar os dados analisar e enviar via internet os dados a uma planilha do Google Sheet.

### Sensor DHT22 (Leitura de temperatura)

O sensor DHT22 é utilizado para fazer a leitura da temperatura da peça, fazendo controle total do equipamento.

### Sensor MPU6050 (Simulando sensor de vibração nós 3 eixos)

A utilização do MPU é pela vantagem de trabalhar com os 3 eixos, sem a necessidade de implementar 3 potenciometro. Assim, sendo que em cada eixo é analisando individualmente, caso um dos eixos não esteja no limite padrão, aparecerá na planilha **"HIGH" para uma alta vibração** e **"NORMAL" caso esteja na vibração limite**. 

### Módulo SD Card (Para backup)

Pensando em modo de backup, será gravado num cartão SD as informçãoes dos sensores, em paralelo a gravação na planilha do Google, abrindo o arquivo **data.csv** para gravação.

### Google Sheet

Utilizando a extensão do Google Sheet, o **App Script**, é capaz de receber os dados do ESP32 via WiFi e assim, fazer a gravação na planilha. <br>
link planilha: https://docs.google.com/spreadsheets/d/1SxSW1ptz34iY43gRZqWlB8mrXascj9ZLxu0J4P3hlF8/edit?usp=sharing


---
## Dados Utilizados
- **CSV**: `src/database/sensores.csv`  
  - Colunas: `id_leitura, id_sensor, id_peca, sensor_tipo, leitura_data_hora, tempo_uso, ciclos, temperatura, vibracao, falha, risco_falha`  
  - **Observação:** as colunas `temperatura` e `vibracao` são valores consolidados “último conhecido por peça” até o timestamp.

---

## Machine Learning

### Modelo 1 — Classificação do estado da peça
- **Arquivo:** `src/machine-learning/part_status_classifier.py`  
- **Problema:** multiclasse (Saudável / Desgastada / Crítica), mapeado do rótulo `risco_falha`.  
- **Features:** `tempo_uso`, `ciclos`, `temperatura`, `vibracao`.  
- **Algoritmo:** `RandomForestClassifier`.  
- **Split temporal:** 70% início → treino; 30% final → teste.  
- **Artefatos gerados:**  
  - `assets/matriz_confusao_estado.png`  
    <p align="center"><img src="assets/matriz_confusao_estado.png" alt="DER" width="85%"></p>

  - `assets/feature_importance_estado.png`  
    <p align="center"><img src="assets/feature_importance_estado.png" alt="DER" width="85%"></p>

  - `src/machine-learning/models/modelo_estado_peca.joblib`

### Modelo 2 — Previsão de falha nas próximas 24h
- **Arquivo:** `src/machine-learning/failure_predict24_hours.py`  
- **Problema:** binário (falha nas próximas 24h).  
- **Rótulo:** `fail_next_h` (1 se existir `falha==1` para a **mesma peça** em `(t, t+24h]`).  
- **Features:** básicas + janelas móveis (médias, desvios e deltas 3/6/12 passos).  
- **Algoritmo:** `GradientBoostingClassifier`.  
- **Split temporal:** 70%/30%.  
- **Artefatos:**  
  - `assets/matriz_confusao_falha_24h.png`  
    <p align="center"><img src="assets/matriz_confusao_falha_24h.png" alt="DER" width="85%"></p>

  - `assets/roc_falha_24h.png` 
    <p align="center"><img src="assets/roc_falha_24h.png" alt="DER" width="85%"></p>

  - `src/machine-learning/models/modelo_falha_24h.joblib`

### Resultados

- **Classificação (estado da peça):**  
  - Accuracy = **1.00**  
  - Macro-F1 = **1.00**  
  - Principais variáveis: tempo_uso (46.6%), ciclos (38.6%), vibração (12.6%), temperatura (2.1%).  

- **Previsão de falha (24h):**  
  - Accuracy = **0.967**  
  - ROC-AUC = **0.50**  
  - F1 (classe 1 = falha) = **0.983**  
  - Observação: o modelo aprendeu quase apenas a prever a classe “falha”. Isso ocorreu devido ao forte **desbalanceamento de classes** (378 falhas vs. 13 não-falhas). Em projetos reais, técnicas de reamostragem, ajuste de limiar e uso de métricas específicas (F1/Recall da classe minoritária) seriam necessárias.

  > **Justificativa dos gráficos**  
> - **Matriz de confusão:** mostra acertos/erros por classe.  
> - **Importância de features:** explica a contribuição relativa de cada variável no modelo 1.  
> - **Curva ROC/AUC:** avalia separação entre classes no modelo 2 para diferentes limiares.

---

## Como Reproduzir

### Ambiente Local
```bash
# Python 3.9+
pip install -r requirements.txt
# Rodar modelo 1
python src/machine-learning/part_status_classifier.py
# Rodar modelo 2
python src/machine-learning/failure_predict24_hours.py
```

**requirements.txt** sugerido

```bash
pandas
numpy
scikit-learn
matplotlib
joblib
```

### Google Colab
 - Faça upload de sensores.csv e copie para src/database/sensores.csv.
 - Instale dependências: !pip -q install pandas numpy scikit-learn matplotlib joblib.
 - Execute os scripts (células fornecidas neste repositório/README).
 - Baixe os gráficos de assets/ e faça commit no repositório.

---

## Estrutura do Repositório

```bash
assets/
  Diagrama-ER.png
  feature_importance_estado.png
  matriz_confusao_estado.png
  matriz_confusao_falha_24h.png
  roc_falha_24h.png

src/
  database/
    DDL.sql
    sensores.csv
  machine-learning/
    part_status_classifier.py
    failure_predict24_hours.py
    models/
      modelo_estado_peca.joblib
      modelo_falha_24h.joblib

README.md

```

## Link do video explicativo: 

- https://www.youtube.com/watch?v=gZ8fwobi3Y4

## ✅ Status da Entrega

- ✅ Definição da arquitetura da solução
- ✅ Modelagem inicial do banco de dados
- ✅ Escolha das tecnologias e justificação
- ✅ README documentado
- ✅ Diagrama DER
- ✅ Script SQL inicial com o código de criação das tabelas
- ✅ Algoritmos de classificação e predição dos estados das peças
- ✅ Implementação do MVP (futuro)

---

## 📎 Observações
- Dados utilizados nesta fase são simulados, devido a quantidade de dados necessárias para cada sensor.
---


## 🗃 Histórico de lançamentos
* 0.2.0 - 09/09/2025
* 0.3.0 - 28/09/2025

## 📋 Licença

<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1"><p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/agodoi/template">MODELO GIT FIAP</a> por <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://fiap.com.br">Fiap</a> está licenciado sobre <a href="http://creativecommons.org/licenses/by/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">Attribution 4.0 International</a>.</p>


