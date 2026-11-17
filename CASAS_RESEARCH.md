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

## Resultados (17/11/2026)
- **NBA** (11,285 partidos):
  - Ninguna casa mejora a la mediana de forma significativa. Las mejores: Caesars Sportsbook +0.0011 [-0.0004; +0.0026]; SugarHouse +0.0009 [-0.0002; +0.0022]; DraftKings +0.0005 [-0.0003; +0.0014].
  - Pinnacle: +0.0001 [-0.0012; +0.0013] en 931 partidos.
  - Combinación ponderada frente a la mediana recalibrada: -0.0011 [-0.0026; +0.0004]. → **❌**
- **NFL** (2,181 partidos):
  - SugarHouse, DraftKings y Caesars sí mejoran a la mediana: SugarHouse +0.0205 [+0.0091; +0.0333]; DraftKings +0.0197 [+0.0084; +0.0332]; Caesars Sportsbook +0.0053 [+0.0017; +0.0092].
  - Combinación ponderada: -0.0010 [-0.0047; +0.0024]. → **❌**

**Interpretación.** Las casas que «ganan» (DraftKings, Caesars, SugarHouse) son justo aquellas de las que ESPN guarda la
cuota de **cierre**, la última antes del partido. De muchas otras guarda la de **apertura**, y la propia línea «Opening»
es la peor (-0.0048 en NBA). Así que la ventaja no es de una casa: es del **momento** de la cuota. La más
cercana al inicio es la más precisa.

**Decisión:**
- No se ponderan casas, tal como dice la regla.
- La mejora real está en tomar los precios lo más cerca posible del inicio, que es lo que hace el nuevo flujo
  **prepartido**: refresca los precios en las 2,5 h previas a cada partido.
