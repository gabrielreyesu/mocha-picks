# Modelo de jugadores NBA con minutos, rival y bajas (idea 18, issue #82)

## Protocolo pre-registrado (escrito y subido ANTES de ver resultados, 25/11/2026)

**Contexto.** En `JUGADORES_RESEARCH.md`, la proyección actual (media y desviación de los últimos 10 partidos) quedó
muy lejos de Kalshi:
- log loss 0,6865 frente a 0,5469;
- brecha −0,140;
- no aportó al combinarse con Kalshi.

Aquí se prueba un modelo con lo que ve el mercado: minutos previstos, producción por minuto, rival y bajas.

**Modelo A (principal, fijado).** Para cada jugador y estadística (puntos, rebotes, asistencias), solo con partidos
anteriores:
1. **Minutos previstos:** promedio exponencial de sus minutos (media vida de 5 partidos jugados).
2. **Producción por minuto:** promedio exponencial ponderado por minutos (media vida de 10 partidos), encogido hacia la
   media de la liga con un peso de 150 minutos.
3. **Rival:** lo que concede el rival en esa estadística por partido (media vida de 15 partidos) dividido por la media
   de la liga.
4. **Media prevista** = minutos × producción por minuto × factor del rival.
5. **Probabilidad:** P(X ≥ línea) con una binomial negativa de media μ. La dispersión de cada estadística se estima
   con los partidos de entrenamiento.

**Variante B (descriptiva, no decide).** A + bajas de compañeros: la parte de la producción del equipo (promedio
reciente) que corresponde a compañeros marcados como no disponibles en el box score. Se multiplica μ por
(1 + β · parte), con β estimado en entrenamiento. Es descriptiva porque la lista oficial de bajas se publica unos 30 min
antes del partido y puede ser posterior al precio de Kalshi que registramos.

**Entrenamiento.** Todos los box scores de la NBA en caché anteriores al 17/11/2026, el primer día con picks de
Kalshi registrados: dispersión y β. No se usa ningún precio de Kalshi para construir el modelo.

**Evaluación.** Los picks NBA resueltos de `predictions/jugadores_resultados.csv` (puntos, rebotes y asistencias, desde
el 17/11/2026), con la misma receta que `JUGADORES_RESEARCH.md`:
1. **Brecha:** log loss del modelo A solo frente a Kalshi, y frente a la proyección antigua (`p_modelo`), con IC95% por
   fecha.
2. **Combinación:** logística de logit(Kalshi) + logit(modelo A) frente a Kalshi recalibrado, con walk-forward por fecha
   (40% de calentamiento) e IC95% por fecha.
3. Se informan también ECE, Brier y acierto.

**Criterio.**
- Si el modelo A mejora a la proyección antigua con IC95% > 0, sustituye a la antigua como dato informativo en la
  página (no cambia ningún pick).
- Si la combinación mejora a Kalshi recalibrado con IC95% > 0: solo sombra. Cambiar la probabilidad publicada
  requiere n ≥ 300 en sombra y la autorización del dueño.
- **Aviso:** hay pocas fechas (8 días), así que el IC95% por fecha es aproximado. Se informa igual.

## Resultados

(pendiente — una sola ejecución de `python -m kalshi_nba.jugadores2`)
