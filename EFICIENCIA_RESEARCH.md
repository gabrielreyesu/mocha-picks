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

## Resultados
(pendiente)
