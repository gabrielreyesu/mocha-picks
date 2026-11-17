# NBA: eficiencia ofensiva/defensiva y ritmo desde el box score (IDEAS.md n.º 1)

## Pregunta
El modelo NBA usa Elo, forma por puntos y descanso. ¿Mejora si sabe **cuántos puntos anota y recibe cada equipo por cada
100 posesiones** (eficiencia), que mide la calidad con menos ruido que el marcador?

## Variables (sin fugas)
- **Box score de ESPN** (`data/nba/box`). Para cada equipo y partido:
  - posesiones ≈ FGA + 0,44·FTA − OREB + TOV;
  - ORtg = 100·puntos/posesiones y DRtg = 100·puntos recibidos/posesiones del rival.
- **Promedio exponencial** de los partidos ANTERIORES del equipo (media vida de 10 partidos), con regresión a la media
  de la liga al inicio de temporada. Los partidos de un día se incorporan después de generar las variables de ese día.
- Variantes:
  - **A** `eff_diff` = (ORtg − DRtg) local − (ORtg − DRtg) visitante;
  - **B** A + `pace_avg` (ritmo medio de los dos);
  - **C** `ortg_diff` y `drtg_diff` por separado.

## Protocolo (pre-registrado, escrito antes de ver resultados; el mismo de LINEUP_RESEARCH.md)
- **Walk-forward por temporada.**
- **Desarrollo:** temporadas 2019–2024, donde se elige UNA variante (la de mayor mejora media de log loss).
- **Confirmación:** temporadas 2025 en adelante, una sola vez.
- **Éxito frente al modelo:** IC 95% de la mejora de log loss > 0 en confirmación, Brier no peor y ECE no peor en más de
  0,005.
- **Frente al mercado:** mercado de cierre recalibrado + variante, frente al mercado recalibrado solo, con walk-forward.
  Solo se informa: se espera poco, porque el mercado ya ve la eficiencia.
- **Si supera el criterio frente al modelo:** se propone en sombra para el modelo NBA, porque reduce la brecha con el
  mercado. Producción no cambia sin autorización.

## Resultados (17/11/2026)
- **Cobertura:** box score en 14.180 de 14.184 partidos.
- **Desarrollo** (2019–2024): A +0.00021 [-0.00005; +0.00047]. B y C quedan peor. Se elige A.
- **Confirmación** (2025 en adelante, 2,834 partidos): +0.00050 [-0.00015; +0.00120],
  Brier +0.00026. → **❌ NO SUPERA EL CRITERIO.** La mejora es pequeña y no confirmada.
- **Frente al mercado:** mercado + eficiencia frente al mercado recalibrado, -0.00011 [-0.00031; +0.00010]. No aporta.
- **Brecha actual del modelo** (mismos 10,246 partidos con mercado): modelo 0.6213 frente a mercado
  0.5982, una diferencia de +0.0231.

**Conclusión:** el Elo con margen y la forma por puntos (`net15_diff`) ya recogen casi toda la información de eficiencia.
Los puntos por posesión no cierran la brecha. Lo que el mercado sabe y el modelo no está, sobre todo, en **quién juega**
(lesiones, descansos, alineaciones): la idea 6, que ya está en sombra.

Durante la ejecución se encontró y corrigió un error: las estadísticas vacías (NaN) de los jugadores que no jugaron
contaminaban todos los promedios. La primera ejecución, con todas las variables vacías, se descartó.
