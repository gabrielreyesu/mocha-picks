# Corrección del 1X2 a 90 minutos en eliminatorias (grupos `clubes` y `selecciones`)

## Contexto
En `NUEVAS_LIGAS.md` se encontró un sesgo. Al evaluar «a 90 minutos» se **descartaban** los partidos con prórroga o
penales, que son empates a los 90'. Este documento revisa si el mismo sesgo afecta a las copas europeas y a las
selecciones.

## Protocolo (pre-registrado, escrito antes de ver resultados)
1. **Medir cuántos partidos se descartaban.** Walk-forward del modelo actual de cada grupo, sin cambiar el modelo,
   evaluado de dos formas:
   - A) como hasta ahora (sin prórrogas);
   - B) corregida (`et_as_draw=True`: prórroga o penales = empate a los 90').
2. **Comparar con la evaluación corregida B.** Log loss del modelo frente a las frecuencias base, con IC 95% por fecha,
   ECE y acierto, en total y solo en los partidos afectados.
3. **Regla:**
   - Si con B el modelo sigue mejorando a la referencia (IC 95% > 0) y el ECE es ≤ 0,05, el modelo **no se cambia**; solo
     se corrigen las evaluaciones y los marcadores.
   - Si no, se marca como problema abierto y el pick de esas competiciones se apoya más en el mercado.
4. **Otros sitios con el mismo error** (siempre se corrigen, porque son errores de etiqueta y no cambian el modelo):
   - el contador de aciertos de la página (`marcadores.hit`);
   - la evaluación del pick final en sombra (`kalshi_external/outcomes.py`);
   - el reentrenamiento de los pesos del combinador de fútbol (`kalshi_lineup/soccer_kalshi_bench.py`).

   Los pesos actuales se reentrenan con las etiquetas corregidas **solo si** la nueva validación no empeora al
   combinador actual (IC 95% de la mejora con extremo superior > 0).

## Resultados
(pendiente)
