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

## Resultados (16/11/2026, temporadas 2021/22 a 2026/27, fuera de muestra)
| Competición | Partidos | Log loss modelo | Referencia | Mejora [IC 95%] | ECE | Acierto | Veredicto |
|---|---|---|---|---|---|---|---|
| Liga Profesional Argentina | 2452 | 1.0650 | 1.0769 | +0.0120 [+0.0024; +0.0216] | 0.034 | 43.7% | ✅ se publica |
| Liga de Bélgica | 1696 | 0.9954 | 1.0730 | +0.0776 [+0.0599; +0.0942] | 0.019 | 52.4% | ✅ se publica |
| Brasileirão | 2169 | 1.0248 | 1.0568 | +0.0320 [+0.0192; +0.0443] | 0.025 | 48.8% | ✅ se publica |
| Copa Libertadores | 678 | 0.9789 | 1.0425 | +0.0636 [+0.0389; +0.0890] | 0.042 | 53.7% | ✅ se publica |
| Championship | 2949 | 1.0597 | 1.0755 | +0.0158 [+0.0066; +0.0250] | 0.022 | 44.4% | ✅ se publica |
| LaLiga 2 | 2487 | 1.0516 | 1.0700 | +0.0184 [+0.0095; +0.0280] | 0.008 | 45.6% | ✅ se publica |
| Ligue 2 | 1859 | 1.0646 | 1.0826 | +0.0180 [+0.0077; +0.0291] | 0.014 | 44.1% | ✅ se publica |
| 2. Bundesliga | 1449 | 1.0529 | 1.0744 | +0.0215 [+0.0063; +0.0352] | 0.024 | 45.7% | ✅ se publica |
| Serie B | 2057 | 1.0624 | 1.0865 | +0.0241 [+0.0134; +0.0346] | 0.034 | 42.9% | ✅ se publica |
| Liga Saudí | 1263 | 0.9476 | 1.0664 | +0.1188 [+0.0982; +0.1396] | 0.043 | 54.2% | ✅ se publica |
| Liga MX | 1831 | 1.0254 | 1.0724 | +0.0470 [+0.0317; +0.0619] | 0.011 | 49.5% | ✅ se publica |
| Eredivisie | 1654 | 0.9541 | 1.0713 | +0.1172 [+0.0948; +0.1385] | 0.019 | 54.3% | ✅ se publica |
| Liga Portugal | 1622 | 0.9252 | 1.0738 | +0.1486 [+0.1274; +0.1683] | 0.028 | 55.4% | ✅ se publica |
| Premiership de Escocia | 1039 | 0.9545 | 1.0605 | +0.1060 [+0.0807; +0.1317] | 0.027 | 53.3% | ✅ se publica |
| Superliga de Turquía | 1849 | 0.9795 | 1.0643 | +0.0848 [+0.0686; +0.1025] | 0.023 | 53.0% | ✅ se publica |
| Copa Sudamericana | 572 | 1.0067 | 1.0599 | +0.0532 [+0.0339; +0.0729] | 0.066 | 52.6% | ❌ solo casas/Kalshi (mal calibrado) |
| FA Cup | 413 | 0.9207 | 0.9589 | +0.0383 [-0.0216; +0.1017] | 0.063 | 61.7% | ❌ solo casas/Kalshi (mejora no significativa, mal calibrado) |
| Copa de la Liga (Inglaterra) | 411 | 0.8720 | 0.9714 | +0.0994 [+0.0452; +0.1675] | 0.105 | 65.5% | ❌ solo casas/Kalshi (mal calibrado) |
| Copa del Rey | 149 | 0.9143 | 0.8433 | -0.0710 [-0.1335; -0.0028] | 0.166 | 66.4% | ❌ solo casas/Kalshi (pocos partidos, mejora no significativa, mal calibrado) |
| Copa de Francia | 108 | 0.7978 | 0.9229 | +0.1251 [+0.0108; +0.2287] | 0.198 | 75.9% | ❌ solo casas/Kalshi (pocos partidos, mal calibrado) |
| Copa de Alemania | 155 | 0.7958 | 0.8785 | +0.0827 [-0.0308; +0.1875] | 0.141 | 72.9% | ❌ solo casas/Kalshi (pocos partidos, mejora no significativa, mal calibrado) |
| Coppa Italia | 165 | 0.7845 | 0.7480 | -0.0365 [-0.0887; +0.0180] | 0.183 | 76.4% | ❌ solo casas/Kalshi (pocos partidos, mejora no significativa, mal calibrado) |
| MLS | 2890 | 1.0496 | 1.0597 | +0.0101 [-0.0017; +0.0213] | 0.016 | 47.4% | ❌ solo casas/Kalshi (mejora no significativa) |

**Resumen:** pasan 15 de 23. Pasan las cinco segundas divisiones (Championship, LaLiga 2, Serie B, 2. Bundesliga, Ligue 2),
Portugal, Países Bajos, Bélgica, Turquía, Escocia, Liga MX, Brasil, Argentina, Arabia Saudí y la Libertadores.
No pasan:
- **Copas nacionales:** hay pocos partidos con historial suficiente y el modelo queda mal calibrado. Las de Italia y España
  incluso empeoran a la referencia.
- **MLS:** la mejora no es significativa; el IC 95% toca el 0.
- **Copa Sudamericana:** está mal calibrada (ECE 0,066).

**Qué se hace con las que no pasan:** se muestran en la página marcadas como BETA, con estadísticas, y su pick sale SOLO de
las casas sin margen o de Kalshi. Si no hay cuotas, no hay pick. Nunca se publica el modelo solo.

**Siguientes pasos:**
- Ajustar el modelo para copas: la diferencia de categoría y la sede, con más temporadas.
- Repetir la validación cada temporada.

## Segunda prueba: copas nacionales (protocolo pre-registrado, escrito antes de ver resultados)
**Cambios del modelo (variante v2, solo en el grupo `ligas`):**
- **Más datos de equipos pequeños:** se agregan al Elo League Two (eng.4), National League (eng.5), Scottish Championship
  (sco.2) y la segunda de Países Bajos (ned.2). Son las divisiones inferiores que publica ESPN.
- **Diferencia de categoría:** nivel de la última liga de cada equipo (1 = primera, 2 = segunda…; sin liga conocida = 6).
  Nueva variable `tier_diff` = nivel del visitante − nivel del local.
- **Indicador de copa nacional:** variable `cup`.

**Evaluación:** el mismo walk-forward (temporadas 2021/22 en adelante, partidos a 90 minutos).
- **Copas:** se evalúan **todas juntas**, en dos subconjuntos:
  - (a) ambos equipos con al menos 10 partidos previos;
  - (b) todos los partidos.

  La referencia es la de cada copa (frecuencias H/D/A de sus temporadas anteriores).
- **Ligas:** se evalúan de nuevo con v2.

**Reglas:**
1. **Copas:** se aplica la misma regla de antes al conjunto de copas: n ≥ 300, IC 95% de la mejora > 0 y ECE ≤ 0,05.
   - Si (b) pasa, se publican todos los partidos de copa.
   - Si solo pasa (a), se publican solo los partidos con historial suficiente.
   - Se excluye cualquier copa cuya mejora individual sea significativamente negativa (IC 95% < 0).
2. **Ligas:** v2 se usa para todo el grupo solo si, en las ligas, v2 no es peor que v1: el IC 95% de la mejora de v2 sobre
   v1 debe tener su extremo superior por encima de 0, y las 15 ligas deben seguir pasando. Si no, las ligas siguen con v1 y
   v2 se usa solo para copas.
3. **MLS y Sudamericana:** se reevalúan con v2 bajo la regla original.

### Resultado de la segunda prueba (v2)
- **Copas (todas juntas):** el modelo mejora con claridad a la referencia.
  - (a) con historial: +0,071 [+0,044; +0,097], n = 1.521.
  - (b) todos los partidos: +0,040 [+0,018; +0,064], n = 2.375.
  - Pero está **mal calibrado**: ECE 0,117 y 0,135, frente al máximo de 0,05. → **No pasa.**
  - La Coppa Italia empeora a la referencia (−0,079 [−0,134; −0,024]).
- **Ligas, v2 frente a v1:** −0,0004 [−0,0009; +0,0001] en 29.266 partidos. Son equivalentes, el extremo superior queda por
  encima de 0 y las 15 ligas siguen pasando. → **Se adopta v2** para todo el grupo.
- **MLS** (+0,011 [+0,0001; +0,023], ECE 0,016) y **Sudamericana** (+0,042 [+0,008; +0,077], ECE 0,031) **pasan con v2**. La
  MLS pasa por muy poco.

## Tercera prueba: calibración para copas (pre-registrada, escrita tras ver que v2 falla SOLO por calibración)
- **Cambio:** a las probabilidades de v2 en copas nacionales se les aplica una recalibración multinomial,
  `p_c ∝ exp(a_c + T · log p_c)`, con a_H = 0 y tres parámetros (T, a_D, a_A).
- **Sin fugas:** para cada temporada, la recalibración se ajusta SOLO con predicciones fuera de muestra de copas de
  temporadas anteriores (desde 2020/21). Se exigen al menos 200 partidos para ajustarla.
- **Evaluación y regla:** la misma de la segunda prueba (copas juntas, subconjuntos a y b, referencia por copa; n ≥ 300,
  IC 95% > 0 y ECE ≤ 0,05). La Coppa Italia queda excluida por empeorar en v2.
- **Aviso honesto:** las temporadas evaluadas son las mismas que en la segunda prueba. Por eso, si pasa, las copas se
  publican marcadas como «en sombra»: con pick y seguimiento prospectivo, y se revisa con 200 partidos nuevos.
