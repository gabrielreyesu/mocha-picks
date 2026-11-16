# Nuevas ligas y copas nacionales — protocolo y resultados

## Protocolo (pre-registrado, escrito antes de ver resultados)
**Objetivo:** ampliar la página a más ligas (segundas divisiones, otras primeras divisiones de Europa y América) y a las
copas nacionales, sin publicar picks de competiciones donde el modelo no sea fiable.

**Modelo:** el mismo motor de copas (`kalshi_intl`: Elo con ajuste por fuerza de liga + Poisson), en un grupo NUEVO
(`ligas`) con su propio entrenamiento. Los grupos actuales (`clubes`, `selecciones`) y el modelo de las 5 grandes ligas
**no cambian**.

**Datos:** marcador público de ESPN desde julio de 2018. Alimentan el Elo todas las competiciones del grupo, más las 5
grandes ligas, las copas europeas y las ligas europeas que ya se usaban.

**Validación:** walk-forward por temporada (se entrena con todo lo anterior al 1 de julio y se evalúa la temporada
siguiente), temporadas 2021/22 en adelante. Solo cuentan partidos terminados en 90 minutos.

**Regla para publicar una competición (las tres a la vez):**
1. Al menos 300 partidos fuera de muestra.
2. Mejor log loss que la referencia ingenua **de esa misma competición**: las frecuencias de local, empate y visitante de
   sus temporadas anteriores. Se compara con bootstrap pareado por fecha y el IC 95% de la mejora debe quedar por encima de 0.
3. Calibración aceptable: ECE de la probabilidad del resultado elegido ≤ 0,05.

**Copas:** solo se evalúan y publican partidos en los que ambos equipos tienen al menos 10 partidos previos en los datos.
Así se evitan equipos de divisiones bajas sin historial.

Cuando haya cuotas, el pick final de la página combina casas + Kalshi + modelo, como en el resto de competiciones.

Las que no cumplan la regla no se publican, y el resultado se reporta igual (resultados negativos incluidos).

## Resultados
(pendiente)
