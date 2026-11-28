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

Ejecución del 25/11/2026, `python -m kalshi_nba.jugadores2`.

**Nota sobre la ejecución.** La primera ejecución solo cubrió el 24% de los picks (2 de 8 fechas). Era un fallo de
datos, no de la prueba: los días del 17 al 22/11 estaban en la caché local de ESPN con el estado «programado», y el
filtro «solo partidos terminados» los descartaba (también del historial). Se corrigió el filtro para usar la hora del
partido (el box score de ESPN ya comprueba que terminó) y se volvió a ejecutar **sin cambiar nada del modelo ni del
protocolo**. Los números de abajo son los de la ejecución corregida. Los de la primera (n = 574) iban en la misma
dirección: A frente a la antigua −0,006 y combinación +0,002 con una sola fecha.

**Parámetros de entrenamiento** (140.587 partidos de jugador anteriores al 17/11/2026):

| Estadística | Dispersión α | β (bajas) |
|---|---|---|
| Puntos | 0,167 | 0,69 |
| Rebotes | 0,113 | 0,67 |
| Asistencias | 0,091 | 0,60 |

**Picks de Kalshi resueltos** (n = 2.413, 8 fechas, cobertura 100%):

| | Log loss | Brier | ECE | Acierto |
|---|---|---|---|---|
| Kalshi | **0,5536** | 0,186 | 0,014 | 72,9% |
| Proyección antigua (media de 10) | 0,6763 | 0,226 | 0,110 | 66,2% |
| **Modelo A** (minutos × ritmo × rival) | 0,6643 | 0,231 | 0,125 | 64,5% |
| Modelo B (A + bajas, descriptivo) | 0,6557 | 0,227 | 0,114 | 65,4% |

| Comparación | Mejora log loss | IC95% por fecha |
|---|---|---|
| A frente a la proyección antigua | +0,012 | [−0,005; +0,024] ❌ (no se confirma) |
| Brecha A frente a Kalshi | −0,111 | [−0,135; −0,087] (antes −0,123) |
| Kalshi + A frente a Kalshi recalibrado (n = 1.177, 4 fechas) | −0,0012 | [−0,0026; +0,0001] ❌ |

**Conclusión (resultado negativo).** Un modelo con minutos previstos, ritmo por minuto y rival se acerca algo más a
Kalshi (la brecha pasa de −0,123 a −0,111), pero:
- no mejora con seguridad a la media simple;
- sigue mal calibrado (ECE 0,12 frente a 0,01 de Kalshi);
- no aporta nada al combinarlo con Kalshi.

Las bajas de compañeros (B) ayudan un poco (0,664 → 0,656), en línea con lo esperado (β ≈ 0,6–0,7).
**No cambia nada:** se sigue publicando el precio de Kalshi y la proyección antigua queda como dato.

**Lectura.** El problema principal es de calibración, no de la media: Kalshi ofrece sobre todo líneas extremas (las
que su precio pone en 75–90%), donde una binomial negativa con dispersión común se equivoca más. Para seguir haría
falta, y queda como idea nueva:
1. dispersión por jugador o por rol;
2. calibrar con las propias líneas de Kalshi cuando haya varios meses de historial de precios;
3. la lista oficial de bajas a la hora del precio.
