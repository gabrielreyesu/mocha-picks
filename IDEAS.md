# Ideas de mejora — lista priorizada (la usa la rutina de investigación)

**Meta (CLAUDE.md):** cerrar la **brecha del modelo propio frente al mercado** y mantener el pick combinado lo más
fiable posible.

**Cómo se trabaja cada idea:**
1. Protocolo pre-registrado, en su propio commit, antes de ver resultados.
2. Walk-forward sin fugas, probando frente al **mercado** y frente al modelo actual.
3. Resultado en `FACTORES.md`, también si sale negativo.
4. PR para el dueño. Nunca se activa en producción sin pasar la regla y sin su autorización.

Estados: ⬜ pendiente · 🔄 en curso · ✅ hecho (aporta) · ❌ hecho (no aporta) · ⏳ esperando datos

| # | Idea | Deporte | Por qué podría aportar | Estado |
|---|---|---|---|---|
| 1 | Eficiencia ofensiva/defensiva y ritmo desde las estadísticas de cada partido (box score), en vez de solo puntos | NBA | Mide la calidad real mejor que el Elo; puede cerrar la brecha | ❌ no aporta (EFICIENCIA_RESEARCH.md) |
| 2 | Tiros y tiros a puerta como «xG aproximado» del equipo (ESPN), como variables del modelo de fútbol | fútbol | Los goles tienen mucho azar; los tiros predicen mejor la fuerza | ✅ aporta al modelo (−18% de brecha); en sombra (TIROS_RESEARCH.md) |
| 3 | Modelado del empate (Dixon-Coles / inflación de empates) por liga | fútbol | El 1X2 depende mucho de acertar el empate | ⬜ |
| 4 | Ventaja de local variable por liga y por temporada (post-COVID) | todos | La ventaja de local cambió en los últimos años | ⬜ |
| 5 | Ajuste de K y de la ventaja de local del Elo por liga (walk-forward) | fútbol | Hoy se usa una configuración común | ⬜ |
| 6 | Impacto de lesiones ponderado por minutos y +/- del jugador dentro del modelo (no solo en sombra) | NBA | Es lo que hoy solo sabe el mercado | ⏳ sombra de alineaciones (30/200) |
| 7 | QB titular dentro del combinador NFL | NFL | La sombra va mejorando | ⏳ sombra QB (12/200) |
| 8 | Polymarket como cuarta fuente del combinador | NBA/NFL | Otra visión del mercado | ⏳ ~200 partidos con resultado |
| 9 | Recalibración por mercado (doble oportunidad, goles, hándicap) | todos | Los primeros datos sugieren que somos algo prudentes | ⏳ ~300 jugadas por mercado |
| 10 | Reentrenar los pesos del combinador con datos nuevos | todos | Cambian los mercados y las fuentes | ⬜ mensual |
| 11 | Árbitros (totales) y clima (totales NFL) con más temporadas | NBA/NFL | Hubo señales sin confirmar | ⏳ nuevas temporadas |
| 12 | Motivación de final de temporada (nada en juego / descenso / clasificación) | fútbol | Se descartó en ligas a mitad de temporada; revisar en mayo | ⏳ final de temporada |
| 13 | Viaje y husos horarios en copas europeas y selecciones | fútbol | Probado en NBA/NFL, no en fútbol internacional | ⬜ |
| 14 | Mercado de córners y tarjetas con modelo propio frente a las casas (si hay cuotas) | fútbol | Mercados menos eficientes que el 1X2 | ⬜ |
| 15 | Proyección propia de jugadores (NBA) frente a Kalshi en los picks de jugadores | NBA | Medir si nuestro modelo de jugador iguala al mercado (JUGADORES_RESEARCH.md) | ⏳ 300 picks resueltos |
| 16 | Tiros en el modelo de las 5 grandes ligas (`kalshi_soccer`) y en copas europeas / selecciones | fútbol | Lo mismo que funcionó en el grupo `ligas` | ⬜ |
| 17 | Activar la sombra de tiros del grupo `ligas` | fútbol | Pasó la prueba histórica | ⏳ 300 partidos resueltos con sombra |
