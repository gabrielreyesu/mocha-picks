# Tiros en el modelo de las 5 grandes ligas (idea 16, issue #78)

## Protocolo pre-registrado (escrito y subido ANTES de ver resultados, 25/11/2026)

**Contexto.** En el grupo `ligas` (`TIROS_RESEARCH.md`), los tiros mejoraron el modelo +0,0050 [+0,0037; +0,0062]
y redujeron un 18% la brecha con las casas, aunque frente a las casas no aportaron. Las 5 grandes ligas usan otro
modelo de producción (`kalshi_soccer`: Elo + Poisson/Dixon-Coles + regresión logística). Aquí se prueba lo mismo en
ese modelo.

**Datos.** Los CSV de football-data.co.uk que ya usa `kalshi_soccer` traen los tiros de cada partido (HS, AS, HST,
AST). Temporadas desde 2015/16.

**Variable (fijada, sin elegir de nuevo).** La variante **B** de `TIROS_RESEARCH.md`:
- por equipo, un promedio exponencial (media vida de 8 partidos) de tiros a puerta y de tiros, a favor y en contra;
- solo con partidos de días anteriores;
- al empezar cada temporada se acerca un 50% a la media de la liga;
- `sot_diff` = (TP a favor − TP en contra) local − (TP a favor − TP en contra) visitante; `sh_diff` igual, con todos
  los tiros.

**Modelo.** `Soccer1X2` con `NUM_1X2 + [sot_diff, sh_diff]` frente a `Soccer1X2` con `NUM_1X2`, con el mismo
walk-forward por temporada de `kalshi_soccer.backtest`.

**Ventanas.** Desarrollo 2021/22–2023/24 (solo para mirar, no se elige nada). Confirmación **una sola vez**:
2024/25 en adelante.

**Criterios.**
1. **Frente al modelo:** pasa si el IC95% de la mejora de log loss (bootstrap pareado por fecha) es > 0 y el ECE no
   empeora más de 0,005. Si pasa, entra **solo en sombra**. Producción no cambia sin n ≥ 300 en sombra y autorización
   del dueño.
2. **Frente a las casas** (las del propio CSV: cierre de Pinnacle o la media, sin margen): casas recalibradas +
   tiros frente a casas recalibradas. Se usa una regresión logística entrenada con temporadas anteriores.
3. **Brecha:** cuánto se reduce el log loss del modelo frente a las casas.

Si no pasa, se documenta como resultado negativo en `FACTORES.md`.

## Resultados

Una sola ejecución (25/11/2026), `python -m kalshi_soccer.tiros5`. 20.311 partidos desde 2015/16; el 100% trae tiros.

| Ventana | n | Mejora log loss | IC95% | ECE base → tiros | Acierto base → tiros |
|---|---|---|---|---|---|
| Desarrollo 2021/22–2023/24 | 5.404 | +0,0061 | [+0,0030; +0,0090] | 0,0165 → 0,0138 | 52,2% → 53,0% |
| **Confirmación 2024/25+** | 4.052 | **+0,0067** | **[+0,0030; +0,0104]** | 0,0110 → 0,0142 | 52,5% → 53,5% |
| Frente a las casas (recalibradas + tiros) | 4.052 | −0,0001 | [−0,0004; +0,0002] | — | — |

**Brecha con las casas (confirmación):** casas 0,9665 · modelo 0,9887 → modelo con tiros 0,9821. La brecha baja de
0,0222 a 0,0156 (**−30%**).

**Veredicto.** ✅ **Pasa frente al modelo** (IC95% > 0; el ECE sube 0,003, dentro del margen de 0,005). Igual que en
el grupo `ligas`, **frente a las casas no aporta**: el mercado ya ve los tiros. Por eso no cambia el pick final
(que ya combina con las casas), pero sí acerca el modelo propio al mercado, que es el indicador para algún día
publicar.

**Sombra (desde este PR).** `kalshi_soccer.cli predict` guarda, en `predictions/soccer_tiros_shadow.csv` (archivo
aparte, solo añade, solo partidos que aún no empezaron), la predicción del modelo con tiros. El pick publicado no
cambia. El informe semanal cuenta los partidos jugados y avisa al llegar a 300. Entonces se evalúa y, si se
confirma, se pide autorización al dueño para pasarlo a producción.
