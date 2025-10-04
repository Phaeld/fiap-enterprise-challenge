WITH base_leituras AS (
  SELECT
    ls.id_leitura,
    s.id_sensor,
    s.id_peca,
    s.tipo_sensor,
    ls.leitura_data_hora,
    ls.leitura_valor
  FROM LEITURAS_SENSOR ls
  JOIN SENSORES s
    ON s.id_sensor = ls.id_sensor
),

leituras_com_preenchimento AS (
  SELECT
    b.*,
    CASE WHEN b.tipo_sensor = 'temperatura' THEN b.leitura_valor END AS current_temp,
    CASE WHEN b.tipo_sensor = 'vibracao'   THEN b.leitura_valor END AS current_vib,
    /* último valor de temperatura conhecido para a peça */
    MAX(CASE WHEN b.tipo_sensor = 'temperatura' THEN b.leitura_valor END)
      OVER (PARTITION BY b.id_peca ORDER BY b.leitura_data_hora
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS temp_ate_agora,
    /* último valor de vibração conhecido para a peça */
    MAX(CASE WHEN b.tipo_sensor = 'vibracao' THEN b.leitura_valor END)
      OVER (PARTITION BY b.id_peca ORDER BY b.leitura_data_hora
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS vib_ate_agora
  FROM base_leituras b
),

leituras_com_acumulados AS (
  SELECT
    l.*,
    /* soma de duração de ciclos encerrados até a data/hora da leitura */
    COALESCE((
      SELECT SUM(c.duracao)
      FROM CICLOS_OPERACAO c
      WHERE c.id_peca = l.id_peca
        AND c.data_fim <= l.leitura_data_hora
    ), 0) AS tempo_uso,
    /* número de ciclos concluídos até a data/hora da leitura */
    COALESCE((
      SELECT COUNT(*)
      FROM CICLOS_OPERACAO c
      WHERE c.id_peca = l.id_peca
        AND c.data_fim <= l.leitura_data_hora
    ), 0) AS ciclos
  FROM leituras_com_preenchimento l
),

leituras_com_falha AS (
  SELECT
    a.*,
    CASE WHEN EXISTS (
      SELECT 1
      FROM FALHAS f
      WHERE f.id_peca = a.id_peca
        AND f.data BETWEEN a.leitura_data_hora - INTERVAL 15 MINUTE
                        AND a.leitura_data_hora + INTERVAL 15 MINUTE
    ) THEN 1 ELSE 0 END AS falha
  FROM leituras_com_acumulados a
),

dataset_final AS (
  SELECT
    lcf.id_leitura,
    lcf.id_sensor,
    lcf.id_peca,
    lcf.tipo_sensor AS sensor_tipo,
    lcf.leitura_data_hora,
    ROUND(lcf.tempo_uso, 2) AS tempo_uso,
    lcf.ciclos,
    /* Se ainda não havia valor conhecido, pode sair NULL; ajuste COALESCE se quiser default */
    ROUND(lcf.temp_ate_agora, 2) AS temperatura,
    ROUND(lcf.vib_ate_agora, 3)  AS vibracao,
    lcf.falha,
    /* risco calculado */
    CASE
      WHEN (
        0.030 * lcf.tempo_uso +
        0.015 * lcf.ciclos +
        0.080 * (COALESCE(lcf.temp_ate_agora, 50) - 50) +
        0.60  * (COALESCE(lcf.vib_ate_agora, 2.0) - 2.0)
      ) > 9.0
      THEN 'alto'
      WHEN (
        0.030 * lcf.tempo_uso +
        0.015 * lcf.ciclos +
        0.080 * (COALESCE(lcf.temp_ate_agora, 50) - 50) +
        0.60  * (COALESCE(lcf.vib_ate_agora, 2.0) - 2.0)
      ) > 6.0
      THEN 'medio'
      ELSE 'baixo'
    END AS risco_falha
  FROM leituras_com_falha lcf
)

SELECT *
FROM dataset_final
ORDER BY id_sensor, leitura_data_hora;
