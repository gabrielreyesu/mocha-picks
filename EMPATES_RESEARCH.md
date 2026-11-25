# Empates por liga (ideas 3 y 19, issue #71)

## Protocolo pre-registrado (escrito y subido ANTES de ver resultados, 25/11/2026)

**Contexto.** La sesión automática del 21/11 probó un ajuste parecido (+0,00003 [−0,00004; +0,00011], sin efecto)
pero no pudo subir su código. Se repite aquí con un protocolo escrito, para dejarlo en el repositorio.

**Pregunta.** ¿Hay ligas donde el modelo infravalora o sobrevalora sistemáticamente el empate, de forma que un
ajuste por liga mejore el 1X2?

**Ajuste (fijado).** Sobre las probabilidades fuera de muestra del modelo `ligas` (walk-forward, `et_as_draw=True`):
`p_D' ∝ p_D · exp(δ_liga)` y se renormaliza. `δ_liga` se estima por máxima verosimilitud **solo con temporadas
anteriores** de esa liga (predicciones fuera de muestra de esas temporadas), con penalización L2 (λ = 50, equivale a
encoger hacia 0 con ~50 partidos de peso) y solo si la liga tiene ≥ 300 partidos previos; si no, δ = 0.

**Datos.** Competiciones evaluadas del grupo `ligas`: 5 grandes + `league_targets`. Desde 2021/22.

**Ventanas.** Desarrollo 2021/22–2023/24 (para mirar). Confirmación **una sola vez**: 2024/25 en adelante.

**Criterio.** Mejora de log loss con IC95% por bootstrap pareado por fecha: pasa si IC95% inferior > 0 y ECE no
empeora más de 0,005. Si pasa: solo sombra. Si no: resultado negativo en `FACTORES.md`.
Descriptivo (no decide): el mismo ajuste sobre las casas (5 grandes ligas, cuotas en caché).

## Resultados

Una sola ejecución (25/11/2026), `python -m kalshi_intl.empates`. 20 competiciones de liga.

| Ventana | n | Mejora log loss | IC95% | ECE base → ajuste |
|---|---|---|---|---|
| Desarrollo 2021/22–2023/24 | 21.490 | +0,00012 | [−0,00025; +0,00047] | 0,0089 → 0,0064 |
| **Confirmación 2024/25+** | 17.448 | **−0,00001** | [−0,00045; +0,00044] | 0,0076 → 0,0090 ❌ |
| Descriptivo: mismo ajuste sobre las casas (5 grandes) | 4.021 | −0,00041 | [−0,00105; +0,00027] | — |

Empate real frente a previsto por el modelo (2021/22+): casi todas las ligas están dentro de ±1 punto. Las
únicas desviaciones visibles son Serie B (31,7% real frente a 27,7%), Argentina (31,2% frente a 28,9%), Arabia
Saudí (22,2% frente a 24,8%) y Escocia (23,0% frente a 25,3%), pero corregirlas con temporadas anteriores no mejora
la temporada siguiente: la desviación no es estable.

**Conclusión (resultado negativo, igual que la prueba automática del 21/11).** El modelo ya acierta la frecuencia
del empate por liga; un ajuste por liga no aporta, ni al modelo ni a las casas. **No entra en sombra.**
