# Equipo de agentes: Claude + ChatGPT (Codex)

Este repositorio lo trabajan **dos agentes de IA** para el dueño, Gabriel. **Antes de hacer nada**, lee las reglas del
proyecto en `CLAUDE.md`: meta, sin fugas de datos, protocolo pre-registrado, todo frente al mercado, nada en
producción sin pruebas ni autorización. Valen igual para los dos.
El registro de factores está en `FACTORES.md` y la lista de ideas en `IDEAS.md`.

## Cómo nos coordinamos (solo a través de GitHub)
1. **Tablero = issues de GitHub.** Cada tarea es un issue. Etiquetas:
   - `claude` o `chatgpt`: quién la tiene asignada;
   - `en-curso`: alguien ya está trabajando en ella (no la toques);
   - `revisar`: hay un PR esperando la revisión del otro agente;
   - `investigacion`, `bot`, `pagina`: tipo de tarea.
2. **Antes de empezar una tarea:** comprueba que no tenga `en-curso`. Ponle tu etiqueta y `en-curso`, y comenta
   «Tomo esta tarea» con la rama que usarás.
3. **Ramas:** `claude/<tema>` o `chatgpt/<tema>`. Las investigaciones llevan además su `<TEMA>_RESEARCH.md`, con el
   protocolo en un commit **anterior** a los resultados.
4. **PR:**
   - descripción en español, clara, con números;
   - cita el issue («Closes #N», en inglés: GitHub no reconoce «Cierra»);
   - sin archivos generados (`docs/*.html`, `PREDICCIONES.md`, `predictions/*`, salvo arreglos de datos explicados);
   - la batería de pruebas (`python -m pytest -q tests`) en verde.
5. **Revisión cruzada obligatoria:** cada PR lo revisa **el otro agente** con un comentario que diga ✅ (correcto) o
   ⚠️ (problemas concretos, con archivo y línea). Mira sobre todo:
   - fugas de datos futuros;
   - fechas simuladas que escriban en registros reales;
   - NaN que contaminen promedios;
   - prórroga y penales = empate a 90';
   - uniones de partidos por fecha.
6. **Solo el dueño fusiona.** Ningún agente fusiona, hace push a `main` ni activa nada en producción sin la
   autorización escrita del dueño.
7. **No duplicar:** si ves un PR o issue abierto sobre lo mismo, coméntalo en lugar de empezar otro.
8. **Resultados negativos también se publican**, en el `.md` de la investigación y en `FACTORES.md`.

## Reparto inicial (se puede cambiar en los issues)
- **Claude:** investigación de modelos y factores (backtests pre-registrados), la página y la revisión semanal.
- **ChatGPT:** robustez de los bots y workflows (fallos de ESPN, Kalshi o The Odds API), pruebas automáticas y
  limpieza de código; también investigación cuando haya tareas libres.
- **Los dos:** revisar los PRs del otro.

## Comunicación con el dueño
Siempre en español, claro y sin jerga. Cada PR termina con: qué cambia, cómo se comprobó y qué tiene que hacer él, si
hace falta algo.
