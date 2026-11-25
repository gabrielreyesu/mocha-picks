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

Una sola ejecución (25/11/2026), `python -m kalshi_lineup.xi_ligas`.

**Cobertura:** 100% de los 11.498 partidos con once válido (98,8% de los evaluados con ≥3 onces previos por equipo).
Desarrollo n = 5.400; confirmación n = 4.051 (2024/25 y 2025/26 hasta hoy).

| Comparación | Mejora log loss | IC95% | Veredicto |
|---|---|---|---|
| Desarrollo: modelo + `xi_cont` frente a modelo | +0,00105 | [+0,00014; +0,00200] | (solo para mirar) |
| **Confirmación: modelo + `xi_cont` frente a modelo** | +0,00114 | [−0,00038; +0,00255] | ❌ IC incluye 0; ECE 0,012 → 0,026 |
| (descriptivo) variante B, con ataque | +0,00124 | [−0,00028; +0,00268] | — |
| **Confirmación: casas recalibradas + `xi_cont`** (n = 4.021) | −0,00011 | [−0,00065; +0,00037] | ❌ nada |

Brecha en confirmación (log loss): casas 0,9665 · modelo 0,9909 · modelo + once 0,9897 (cierra ~5% de la brecha).

**Conclusión (resultado negativo).** En las 5 grandes ligas, la continuidad del once aporta como mucho una mejora
mínima al modelo propio, que no se confirma y además empeora la calibración. Frente a las casas no aporta nada: el
mercado de cierre ya incorpora las rotaciones y los titulares ausentes (igual que vimos con racha, descanso, viajes
y suspensiones). **No entra en sombra.** Se mantiene la sombra de copas europeas, que es independiente.

**Qué queda abierto.** El valor del once, si existe, está en el *momento*: el mercado se mueve cuando sale el once
oficial. Probarlo exige precios de antes y después de la publicación del once (por ejemplo, Kalshi histórico por
minuto), no la cuota de cierre. Queda anotado en `IDEAS.md`.
