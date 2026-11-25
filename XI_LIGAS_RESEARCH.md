# Continuidad del once en las 5 grandes ligas (issue #68)

## Protocolo pre-registrado (escrito y subido ANTES de ver resultados, 25/11/2026)

**Pregunta.** ¿Saber cuánto se parece el once oficial de hoy a los onces habituales del equipo (rotaciones, bajas
de titulares) mejora la predicción 1X2 en Premier, LaLiga, Serie A, Bundesliga y Ligue 1, frente al modelo propio
y frente a las casas?

**Variable (fijada, no se ajusta):** `xi_cont` de `kalshi_lineup/soccer_xi.py` (variante A, ya usada en copas
europeas): peso decaído (0,85 por partido) de titularidades de los 11 de hoy sobre los 11 más habituales, local
menos visitante. Solo usa onces de partidos anteriores; el once del propio partido es el oficial (ESPN lo publica
25–60 min antes del inicio, comprobado en la auditoría). Si un equipo tiene <3 onces previos, `xi_cont = 0`.
Se mantiene la variante B (`xi_cont` + `xi_ga`) solo como descriptiva.

**Datos.** Grupo `ligas` (motor actual, `et_as_draw=True`), evaluación solo en `eng.1, esp.1, ita.1, ger.1, fra.1`.
Onces: resúmenes de ESPN (`/summary`) de todos los partidos de esas ligas desde 2020-07 (caché en `data/intl_box/`).
Cuotas de casas: caché de `data/intl/odds` (mediana sin margen, cierre ESPN).

**Ventanas.** Desarrollo 2021/22–2023/24 (solo para mirar). Confirmación **una sola vez**: 2024/25 en adelante.

**Comparaciones (confirmación):**
1. Modelo + `xi_cont` frente a modelo (walk-forward por temporada).
2. Casas recalibradas + `xi_cont` frente a casas recalibradas (regresión logística sobre log(H/D), log(A/D),
   entrenada con temporadas anteriores; misma receta que `TIROS_RESEARCH.md`).

**Métrica y criterio.** Mejora de log loss con IC95% por bootstrap pareado por fecha.
- (1) pasa si IC95% inferior > 0 y ECE no empeora más de 0,005.
- (2) pasa si IC95% inferior > 0.
- Si pasa (1) y/o (2): entra **solo en sombra** (registro prospectivo), nunca directo al pick. Promoción con
  n ≥ 300 en sombra, IC95% > 0 y autorización del dueño.
- Si no pasa: se documenta como resultado negativo en `FACTORES.md`.

**Cobertura mínima.** Si menos del 60% de los partidos evaluados tiene once válido (11+11 titulares), no se evalúa.

## Resultados

(pendiente — se rellena tras una sola ejecución de `python -m kalshi_lineup.xi_ligas`)
