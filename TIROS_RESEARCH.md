# Fútbol: tiros y tiros a puerta como medida de la fuerza (IDEAS.md n.º 2)

## Pregunta
Los goles tienen mucho azar. ¿Mejora el modelo de fútbol si sabe cuántos **tiros a puerta** genera y concede cada equipo
(una aproximación a los «goles esperados»), y cierra algo de la brecha frente al mercado?

## Datos (sin fugas)
- Marcador de ESPN por mes (`data/stats`) con tiros y tiros a puerta por equipo y partido, desde julio de 2018, para todas
  las ligas y copas del grupo `ligas`.
- Por equipo: promedio exponencial (media vida de 8 partidos) de tiros a puerta a favor y en contra y de tiros a favor y
  en contra. Solo usa partidos de días anteriores y se reinicia parcialmente cada temporada (50% hacia la media).
- Variantes:
  - **A** `sot_diff` = (TP a favor − TP en contra) local − (TP a favor − TP en contra) visitante;
  - **B** A + `sh_diff` (lo mismo con todos los tiros);
  - **C** A + `sot_share_diff` (porcentaje de tiros a puerta de cada partido que son suyos).

## Protocolo (pre-registrado, escrito antes de ver resultados)
- **Modelo base:** el de producción del grupo `ligas` (v2: Elo, forma, categoría, copa), walk-forward por temporada y
  partidos a 90' (prórroga o penales = empate).
- **Evaluación:** las 5 grandes ligas y las ligas objetivo del grupo.
- **Desarrollo:** temporadas 2021/22–2023/24, donde se elige UNA variante (la de mayor mejora media de log loss).
- **Confirmación:** temporadas 2024/25 en adelante, una sola vez.
- **Éxito frente al modelo:** IC 95% de la mejora de log loss > 0 en confirmación y ECE no peor en más de 0,005.
- **Frente al mercado:** en las 5 grandes ligas con cuotas de casas (ESPN, sin margen), casas recalibradas + variante
  frente a casas recalibradas solas, con walk-forward por temporada. Se informa también cuánto se reduce la brecha del
  modelo frente a las casas.
- **Si pasa frente al modelo:** se propone en sombra para el grupo `ligas`. Producción no cambia sin autorización.

## Resultados
(pendiente)
