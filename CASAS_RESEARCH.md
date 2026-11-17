# ¿Hay casas de apuestas más precisas que otras? (NBA/NFL) — protocolo y resultados

## Pregunta
Hoy la probabilidad de «las casas» es la **mediana** entre todas las casas que publica ESPN. ¿Mejoraría el pick si
algunas casas pesaran más que otras?

## Datos (sin fugas)
- Moneylines por casa guardadas en caché (`data/nba/odds`, `data/nfl/odds`) para cada partido, y resultados de ESPN.
- Probabilidad de cada casa: moneyline sin margen (normalización proporcional).
- Se excluyen los sitios de pronósticos que no son casas (teamrankings, accuscore, numberfire, consensus).

## Protocolo (pre-registrado, escrito antes de ver resultados)
1. **Referencia:** la mediana de las casas, como en producción.
2. **Cada casa por separado:** log loss frente a la mediana en los mismos partidos, con IC 95% por fecha. Solo casas con al
   menos 500 partidos.
3. **Combinación ponderada:** regresión logística sobre el logit de la mediana más el logit de cada una de las 6 casas con
   más partidos (si falta una, se usa la mediana).
   - Walk-forward por temporada: se entrena con las temporadas anteriores y se evalúa la siguiente.
   - Se compara con la mediana recalibrada de la misma forma (solo el logit de la mediana), para no confundir
     recalibración con ponderación.
4. **Regla:** se adopta (primero en sombra) solo si la combinación ponderada mejora a la mediana recalibrada con
   IC 95% > 0, en NBA y en NFL por separado. Si no, ❌ y se mantiene la mediana.
5. **Fútbol:** ESPN no trae casas de referencia como Pinnacle ni historial por casa. Desde ahora se puede registrar la
   cuota por casa que trae The Odds API, para probarlo de forma prospectiva.

## Resultados
(pendiente)
