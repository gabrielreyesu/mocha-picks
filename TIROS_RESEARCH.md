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

## Resultados (17/11/2026)
- **Cobertura:** el 76% de los partidos terminados tiene tiros en ESPN. Las ligas menores no los
  miden; ahí la variable vale lo mismo para los dos equipos y no aporta nada.
- **Desarrollo** (21,490 partidos): A +0.0019 [+0.0013; +0.0026], **B +0.0034 [+0.0024; +0.0045]**, C +0.0019 [+0.0013; +0.0026]. Se elige B.
- **Confirmación** (17,254 partidos, 2024/25 en adelante, una sola vez): **+0.0050 [+0.0037; +0.0062]**.
  Log loss 1.0144 → 1.0095, ECE 0.0069 → 0.0073. → **✅ SUPERA EL CRITERIO (sombra).**
- **Frente al mercado** (5 grandes ligas, 7,494 partidos): casas + tiros frente a casas recalibradas, -0.0003 [-0.0008; +0.0002].
  No aporta: las casas ya ven los tiros.
- **Brecha del modelo frente a las casas** (5 grandes, 9,320 partidos): modelo 0.9912 → con tiros
  0.9869, frente a casas 0.9669. La brecha baja de 0.0243 a
  0.0200, alrededor de un 18% menos.

**Decisión:** pasa a **sombra** en el grupo `ligas` (ligas nuevas y copas nacionales). `cli predict` registra `s_H/s_D/s_A`
junto a la probabilidad actual, sin cambiar el pick.

**Regla de activación (pre-registrada):** con al menos 300 partidos resueltos con sombra, log loss de la sombra frente al
modelo actual con IC 95% > 0, y autorización del dueño.

**Siguiente:** probar lo mismo en el modelo de las 5 grandes ligas (`kalshi_soccer`) y en copas europeas y selecciones.
