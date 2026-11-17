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

## Resultados (17/11/2026)
| Grupo | Evaluación | Partidos | Log loss modelo | Referencia | Mejora [IC 95%] | ECE | Acierto |
|---|---|---|---|---|---|---|---|
| clubes | A sin prorrogas | 2770 | 0.9529 | 1.0424 | +0.0895 [+0.0753; +0.1039] | 0.038 | 56.2% |
| clubes | B corregida | 2835 | 0.9619 | 1.0519 | +0.0900 [+0.0769; +0.1044] | 0.028 | 54.9% |
| selecciones | A sin prorrogas | 3769 | 0.9187 | 1.0495 | +0.1309 [+0.1123; +0.1512] | 0.022 | 58.2% |
| selecciones | B corregida | 3852 | 0.9279 | 1.0571 | +0.1291 [+0.1102; +0.1472] | 0.030 | 56.9% |

- **Partidos afectados:** 65 en copas europeas (Europa League 28, Conference 24, Champions 13) y 83 en selecciones.
  Es alrededor del 2% del total.
- **El modelo no se cambia:** con la evaluación corregida sigue mejorando con claridad a la referencia y está bien
  calibrado (ECE 0,028 y 0,030).
- **Etiquetas corregidas:**
  - el contador ✅/❌ de la página: una prórroga o penales cuenta como empate a los 90'; antes quedaba sin decidir;
  - la evaluación del pick en sombra (`outcomes.py`): esos partidos ahora sí cuentan;
  - el reentrenamiento futuro del combinador (`soccer_kalshi_bench.py`).
- **Pesos del combinador: no se reentrenan.** Con las etiquetas corregidas, el walk-forward de pesos nuevos dio
  0,9346 frente a 0,9304 de los pesos actuales (−0,0042 [−0,0065; −0,0019], 1.803 partidos). Los actuales tienen ventaja
  porque se ajustaron con casi los mismos partidos, pero la regla exige no empeorar. Se mantienen y se volverán a probar
  en el próximo reentrenamiento periódico.
