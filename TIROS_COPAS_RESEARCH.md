# Tiros en copas europeas y selecciones (idea 16, parte 2; issue #80)

## Protocolo pre-registrado (escrito y subido ANTES de ver resultados, 25/11/2026)

**Contexto.** Los tiros (variante B: tiros a puerta y tiros totales, promedio exponencial) pasaron en el grupo
`ligas` (+0,0050, `TIROS_RESEARCH.md`) y en las 5 grandes (+0,0067, `TIROS5_RESEARCH.md`). Aquí se prueba lo
mismo en los otros dos grupos del modelo internacional.

**Grupos.**
- `clubes`: evaluación en Champions League, Europa League y Conference League.
- `selecciones`: evaluación en sus competiciones objetivo (Mundial, eliminatorias UEFA y CONMEBOL, Nations
  League, Eurocopa y su clasificación, Copa América, amistosos).

Cada grupo se evalúa por separado. Los tiros se calculan con todas las competiciones del grupo que tengan datos en
ESPN, también las de alimentación.

**Variable (fijada, sin elegir).** La variante B de `kalshi_intl/tiros.py` (`sot_diff` y `sh_diff`), con la misma
receta:
- media vida de 8 partidos;
- solo días anteriores;
- 50% hacia la media al cambiar de temporada;
- sin dato, valor 0.

**Modelo.** El de producción de cada grupo (`GROUP_FEATURES`) frente al mismo modelo + variante B, con walk-forward
por temporada y partidos a 90' (`et_as_draw=True`: prórroga o penales cuentan como empate).

**Ventanas.** Desarrollo 2021/22–2023/24 (solo para mirar). Confirmación **una sola vez**: 2024/25 en adelante.

**Criterio (cada grupo por separado).**
- Pasa si, en confirmación, el IC95% de la mejora de log loss (bootstrap pareado por fecha) es > 0 y el ECE no
  empeora más de 0,005.
- Si pasa, entra solo en sombra. Para llegar a producción hacen falta n ≥ 300 en sombra y la autorización del dueño.
- Descriptivo, donde haya cuotas en caché o en ESPN: casas recalibradas + tiros frente a casas recalibradas, y la
  brecha con las casas.

**Cobertura mínima.** Si menos del 50% de los partidos evaluados en confirmación tiene historial de tiros para los
dos equipos, ese grupo no se evalúa y se informa como «sin datos suficientes».

## Resultados

(pendiente — una sola ejecución de `python -m kalshi_intl.tiros_grupos`)
