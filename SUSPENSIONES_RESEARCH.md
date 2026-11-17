# Suspensiones en fútbol (expulsiones y acumulación de amarillas) — protocolo y resultados

## Pregunta
¿Saber que un equipo llega con jugadores suspendidos mejora el pick, **frente al mercado**?

## Datos (sin fugas)
- Marcador de ESPN de las ligas y copas: tarjetas por jugador y partido, ya descargadas en `data/stats`.
- Para cada partido se miran solo partidos anteriores del mismo equipo en la misma competición:
  - **Roja directa o doble amarilla** en el partido anterior del equipo en esa competición → 1 baja probable.
  - **5.ª amarilla** acumulada en la temporada de liga → 1 baja probable. Se usa el umbral de 5 de LaLiga, Premier,
    Serie A y Bundesliga; es aproximado porque las reglas varían por liga.
- La variable es `susp_diff` = bajas probables del local − bajas probables del visitante.
- **Limitación conocida:** no sabemos si el suspendido era titular ni si apeló la sanción. Por eso es una señal débil por
  diseño.

## Protocolo (pre-registrado, escrito antes de ver resultados)
1. **Muestra:** partidos con cuotas de casas sin margen (ESPN) desde 2021/22, en las ligas y copas con datos de tarjetas.
2. **Modelo:** regresión logística multinomial sobre el logit de las casas + `susp_diff`, frente a solo casas. Walk-forward
   por fecha (40% de calentamiento) y log loss con IC 95% por fecha (bootstrap pareado).
3. **Regla:** solo se incorpora (primero en sombra) si mejora a las casas con IC 95% > 0. Si no, ❌ y se reporta.
4. También se informa el efecto frente al modelo propio, como referencia.

## Resultados
(pendiente)
