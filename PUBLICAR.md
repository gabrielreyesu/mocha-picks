# Lista para convertir Mocha Picks en una página pública

Ya hecho:
- [x] Aviso legal y juego responsable (`docs/legal.html`, enlazado desde las dos páginas).
- [x] Acierto medido y publicado (Progreso): por mercado, por competición y en las combinadas.
- [x] Sin cookies ni analítica; los detalles internos de Progreso, protegidos con clave.

Antes de abrirla al público:
- [ ] **Datos de ESPN:** las API públicas de ESPN no tienen licencia para uso comercial. Para una página pública o con
      ingresos hay que contratar un proveedor con licencia (por ejemplo Sportradar, API-Football de pago u Opta).
- [ ] **Escudos y logos:** son marcas registradas. Para uso público o comercial, retirarlos (dejar iniciales) u obtener
      licencia.
- [ ] **Cuotas de casas:** revisar los términos de The Odds API (plan de pago para uso comercial) y los de Kalshi.
- [ ] **Leyes de pronósticos y publicidad de apuestas:** cada país o estado tiene reglas (edad mínima, avisos obligatorios,
      prohibición de afiliados). Consultar a un abogado del país donde se publique.
- [ ] **Repositorio público:** el código y los datos de `predictions/` se ven en GitHub. Para ocultarlos, hacer privado
      el repositorio (GitHub Pages en privado requiere plan de pago) o publicar desde otro servicio.
- [ ] **Dominio propio, HTTPS y página de contacto.**
- [ ] **Capacidad:** la página es un solo archivo estático (unos 0,5–1 MB). Con muchas visitas conviene un CDN (por
      ejemplo Cloudflare Pages).
