# Picks de jugadores — proyección propia frente a Kalshi (protocolo pre-registrado)

## Qué se publica hoy
- La probabilidad de cada pick de jugador es el **precio de Kalshi**: punto medio, con diferencia entre compra y venta
  ≤ 10¢.
- Nuestra **proyección NBA** se muestra al lado, pero **no cambia el pick**. Es la media y la desviación de sus últimos
  10 partidos, convertidas con P(X ≥ línea) mediante una aproximación normal.
- Cada pick resuelto se registra en `predictions/jugadores_resultados.csv`, con la probabilidad de Kalshi (`p`), la del
  modelo (`p_modelo`) y si acertó. En NBA se resuelven puntos, rebotes y asistencias con el box score de ESPN.

## Protocolo (pre-registrado, escrito antes de ver resultados)
1. **Cuándo:** con al menos 300 picks NBA resueltos que tengan las dos probabilidades.
2. **Comparación:** log loss y ECE de Kalshi, del modelo y de la combinación logística de ambos (logit de Kalshi + logit
   del modelo), con walk-forward por fecha (40% de calentamiento) y IC 95% por fecha.
3. **Regla:** la combinación sustituye al precio de Kalshi en la página solo si mejora a Kalshi recalibrado con
   IC 95% > 0, y con la autorización del dueño. Si no, se sigue publicando solo Kalshi y el modelo queda como dato.
4. **Brecha:** el log loss del modelo solo frente a Kalshi se informa siempre, como en los partidos.

## Resultados (25/11/2026)
- **Muestra:** 2,370 picks NBA resueltos en 8 días; 1,491 evaluados con walk-forward (40% de calentamiento).
- **Kalshi:** log loss 0.5469, ECE 0.021, acierto 73.0%. Muy bien calibrado.
- **Proyección propia sola:** log loss 0.6865, ECE 0.102. Mucho peor y demasiado segura de sí
  misma. Brecha frente a Kalshi: -0.140 [-0.186; -0.096].
- **Kalshi + proyección frente a Kalshi recalibrado:** -0.00054 [-0.00190; +0.00056]. → **❌ No aporta.**
  Se sigue publicando solo Kalshi.
- **Aviso:** solo hay 8 fechas, así que el intervalo por fecha es aproximado. Aun así, la diferencia del modelo solo es
  enorme y clara.

**Lectura:** una media de 10 partidos con desviación no sabe lo que sabe el mercado: minutos previstos, rival, bajas de
compañeros y rol. Para cerrar esta brecha haría falta un modelo de minutos y de uso por rival, que queda como idea nueva
(IDEAS.md).
