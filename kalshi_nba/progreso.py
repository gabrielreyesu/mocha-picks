"""Mocha Picks — página de PROGRESO (docs/progreso.html): pruebas en sombra, acierto real y resultados de investigación.

Separada de la página de picks. Solo lee predictions/*.json; no usa internet.   Uso:  python -m kalshi_nba.progreso
"""
from __future__ import annotations

import html
import json
import os
import math
from pathlib import Path

import pandas as pd

P = Path("predictions")
TARGET_N = 200

SHADOWS = [
    {"id": "nba", "titulo": "NBA · jugadores disponibles", "archivo": "nba_lineup_shadow_scoreboard.json",
     "que": "Modelo NBA + fuerza de los jugadores disponibles según el informe de lesiones antes del partido.",
     "base": "logloss_base", "nuevo": "logloss_lineup", "acc_b": "acierto_base", "acc_n": "acierto_lineup"},
    {"id": "nfl", "titulo": "NFL · quarterback titular", "archivo": "nfl_qb_shadow_scoreboard.json",
     "que": "Modelo NFL + nivel del QB titular previsto (depth chart y lesiones de ESPN).",
     "base": "logloss_base", "nuevo": "logloss_lineup", "acc_b": "acierto_base", "acc_n": "acierto_lineup"},
    {"id": "copas", "titulo": "Copas europeas · once titular", "archivo": "soccer_xi_shadow_scoreboard.json",
     "que": "Motor de copas + continuidad del once oficial publicado antes del inicio.",
     "base": "logloss_base", "nuevo": "logloss_xi", "acc_b": "acierto_base", "acc_n": "acierto_xi"},
]

# Resultados del backtest histórico pre-registrado (LINEUP_RESEARCH.md). Se actualizan a mano tras cada prueba nueva.
BACKTESTS = [
    {"prueba": "NBA · jugadores disponibles", "partidos": 2817, "acierto": "67,0% → 67,4%", "mejora": "0,0098 [0,0054; 0,0142]", "veredicto": "supera"},
    {"prueba": "NFL · quarterback titular", "partidos": 707, "acierto": "65,9% → 66,9%", "mejora": "0,0133 [0,0037; 0,0237]", "veredicto": "supera"},
    {"prueba": "Copas europeas · once titular", "partidos": 1234, "acierto": "56,7% → 56,8%", "mejora": "0,0030 [0,0002; 0,0059]", "veredicto": "supera (débil)"},
    {"prueba": "Selecciones · once titular", "partidos": 1321, "acierto": "58,7% → 58,6%", "mejora": "0,0008 [−0,0001; 0,0017]", "veredicto": "descartada"},
    {"prueba": "Selecciones · sede neutral", "partidos": 3714, "acierto": "57,9% → 58,0%", "mejora": "0,0000 [−0,0019; 0,0019]", "veredicto": "no concluyente"},
    {"prueba": "Ligas · qué se juega cada equipo", "partidos": 5437, "acierto": "52,6% → 52,6%", "mejora": "0,0003 [−0,0004; 0,0010]", "veredicto": "no concluyente"},
    {"prueba": "Nations League · qué se juega cada selección", "partidos": 495, "acierto": "63,4% → 63,4%", "mejora": "−0,0015 [−0,0040; 0,0004]", "veredicto": "descartada"},
    {"prueba": "NBA · modelo+alineación vs Kalshi (60 min antes)", "partidos": 1559, "acierto": "Kalshi 68,7% · modelo 67,0%", "mejora": "−0,0159 [−0,0235; −0,0085]", "veredicto": "Kalshi gana"},
    {"prueba": "NBA · Kalshi + modelo (mezcla)", "partidos": 1018, "acierto": "70,5% → 71,2%", "mejora": "−0,0004 [−0,0017; 0,0010]", "veredicto": "descartada"},
    {"prueba": "NFL · modelo+QB vs Kalshi (60 min antes)", "partidos": 410, "acierto": "Kalshi 65,6% · modelo 65,6%", "mejora": "−0,0020 [−0,0110; 0,0071]", "veredicto": "empate"},
    {"prueba": "NFL · Kalshi + modelo (mezcla)", "partidos": 245, "acierto": "64,5% → 64,1%", "mejora": "0,0027 [−0,0006; 0,0058]", "veredicto": "no concluyente"},
    {"prueba": "NBA/NFL · viajes, husos y hora del partido", "partidos": 2817, "acierto": "67,0% → 67,3%", "mejora": "−0,0002 [−0,0010; 0,0006]", "veredicto": "descartada"},
    {"prueba": "NBA/NFL · racha, forma, descanso, H2H, Elo vs mercado", "partidos": 2816, "acierto": "—", "mejora": "−0,0006 [−0,0017; 0,0006]", "veredicto": "descartada"},
    {"prueba": "Fútbol · goles con casas + modelo", "partidos": 7769, "acierto": "—", "mejora": "+0,0113 vs modelo [0,0079; 0,0145]", "veredicto": "supera"},
    {"prueba": "Fútbol · pick con Kalshi + casas + modelo", "partidos": 1794, "acierto": "55,5% → 57,1%", "mejora": "+0,0147 [0,0054; 0,0240]", "veredicto": "supera"},
    {"prueba": "NBA · árbitros (totales)", "partidos": 2812, "acierto": "—", "mejora": "+0,50 pts² [−0,30; 1,31]", "veredicto": "no concluyente"},
    {"prueba": "NFL · distribución real de márgenes", "partidos": 991, "acierto": "—", "mejora": "+0,0001 [−0,0010; 0,0012]", "veredicto": "descartada"},
    {"prueba": "Selecciones · excluir prórrogas (V7)", "partidos": 3703, "acierto": "57,9% → 58,0%", "mejora": "−0,0003 [−0,0005; −0,0002]", "veredicto": "descartada"},
]

NEXT = [
    ("En curso", "Acumular 200 partidos por prueba en sombra (NBA ~2–3 semanas; copas ~2 meses; NFL varios meses)."),
    ("Siguiente", "Mostrar en la página de picks la probabilidad ajustada por bajas, marcada como «en prueba», cuando NBA llegue a 200 partidos con mejora."),
    ("Hecho", "Comparación con precios reales de Kalshi: el mercado 60 min antes acierta más que el modelo; la mezcla no aporta (NBA) o no es concluyente (NFL)."),
    ("Siguiente", "Picks con el precio más reciente posible (Kalshi cerca del inicio), ya que el mercado mejora al acercarse el partido."),
    ("Siguiente", "Repetir con más partidos: árbitros (NBA/NFL), clima NFL frente a la línea de apertura y modelo de QB dentro del combinador."),
    ("Pendiente", "Repetir la sede neutral de selecciones cuando haya más partidos de torneo."),
]


def _clean(o):
    if isinstance(o, float) and not math.isfinite(o):
        return None
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_clean(v) for v in o]
    return o


def _load(name):
    p = P / name
    if not p.exists():
        return None
    try:
        return _clean(json.loads(p.read_text(encoding="utf8")))      # json de Python acepta NaN; lo limpiamos
    except ValueError:
        return None


def collect(now=None) -> dict:
    now = now or pd.Timestamp.now(tz="UTC")
    shadows = []
    for s in SHADOWS:
        b = _load(s["archivo"]) or {}
        r = b.get("resultado") or {}
        ci = r.get("mejora_logloss") or {}
        shadows.append({"id": s["id"], "titulo": s["titulo"], "que": s["que"], "n": int(r.get("n") or 0), "objetivo": TARGET_N,
                        "actualizado": b.get("updated_utc"), "acc_base": r.get(s["acc_b"]), "acc_nuevo": r.get(s["acc_n"]),
                        "ll_base": r.get(s["base"]), "ll_nuevo": r.get(s["nuevo"]),
                        "mejora": ci.get("mejora"), "ic_inf": ci.get("ic95_inf"), "ic_sup": ci.get("ic95_sup"),
                        "minutos_antes": r.get("minutos_antes_mediana")})
    fs = _load("final_shadow_scoreboard.json") or {}
    names = {"nba": "NBA", "nfl": "NFL", "club": "Copas europeas", "intl": "Selecciones"}
    picks = [{"deporte": names.get(x.get("sport"), x.get("sport")), "n": x.get("n"), "acierto": x.get("acierto_final"),
              "logloss": x.get("logloss_final"), "con_mercado": x.get("con_mercado")} for x in fs.get("by_sport", [])]
    fia = Path(__file__).with_name("fiabilidad.json")
    fiab = json.loads(fia.read_text()).get("deportes", {}) if fia.exists() else {}
    return {"updated": now.isoformat(), "shadows": shadows, "picks": picks, "picks_updated": fs.get("updated_utc"), "fiabilidad": fiab,
            "backtests": BACKTESTS, "next": NEXT}


PRIVATE = ("shadows", "backtests", "next")       # solo con la clave del dueño
CLAVE_ENV = "PROGRESO_CLAVE"                     # secreto de GitHub Actions; nunca se guarda en el repositorio
ITER = 250_000


def _b64(b: bytes) -> str:
    import base64
    return base64.b64encode(b).decode()


def encrypt(obj, password: str) -> dict:
    """AES-256-GCM con clave derivada por PBKDF2-SHA256: en la página solo queda el texto cifrado."""
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    salt, iv = os.urandom(16), os.urandom(12)
    key = PBKDF2HMAC(hashes.SHA256(), 32, salt, ITER).derive(password.encode("utf-8"))
    ct = AESGCM(key).encrypt(iv, json.dumps(obj, ensure_ascii=False, allow_nan=False).encode("utf-8"), None)
    return {"salt": _b64(salt), "iv": _b64(iv), "ct": _b64(ct), "iter": ITER}


def render(data: dict, password: str | None = None) -> str:
    """Público: fiabilidad y acierto real. Privado (cifrado): pruebas en sombra, investigación y próximos pasos.
    Sin clave configurada, la parte privada simplemente no se publica."""
    pub = {k: v for k, v in data.items() if k not in PRIVATE}
    priv = {k: data[k] for k in PRIVATE if k in data}
    pub["lock"] = encrypt(priv, password) if password else None
    payload = json.dumps(pub, ensure_ascii=False, allow_nan=False).replace("</", "<\\/")
    return TEMPLATE.replace("__DATA__", payload)


TEMPLATE = r"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex">
<meta name="theme-color" content="#000000">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22%3E%3Ctext y=%22.9em%22 font-size=%2290%22%3E%E2%98%95%3C/text%3E%3C/svg%3E">
<title>Mocha Picks · Progreso</title>
<style>
:root{--bg:#000;--card:#0b0f17;--ink:#eef3fb;--muted:#8796ad;--line:#1c2738;--accent:#2f7bff;--good:#36d07f;--bad:#ff5d6c;--mid:#f5b942;--chip:#172235;--bar:#2f7bff}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
header,main,footer{max-width:720px;margin:0 auto;padding:0 16px}header{padding-top:14px}
h1{font-size:20px;margin:0}h2{font-size:15px;text-transform:uppercase;letter-spacing:.04em;color:var(--muted);margin:24px 2px 10px}
.sub{color:var(--muted);font-size:12px;margin-top:2px}a{color:var(--accent)}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:13px 14px;margin-bottom:10px}
.row{display:flex;justify-content:space-between;align-items:baseline;gap:8px}.t{font-weight:650}.small{font-size:12px;color:var(--muted)}
.prog{height:10px;background:var(--chip);border-radius:6px;overflow:hidden;margin:10px 0 4px}.prog i{display:block;height:100%;background:var(--bar)}
.badge{font-size:11px;font-weight:700;border:1px solid currentColor;border-radius:999px;padding:2px 8px;white-space:nowrap}
.good{color:var(--good)}.bad{color:var(--bad)}.mid{color:var(--mid)}.muted{color:var(--muted)}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:6px 12px;margin-top:10px;font-size:13px}.grid b{font-variant-numeric:tabular-nums}
table{width:100%;border-collapse:collapse;font-size:13px}td,th{padding:8px 4px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{color:var(--muted);font-weight:600;font-size:12px}td.n{font-variant-numeric:tabular-nums;white-space:nowrap}
.bt{padding:9px 0;border-bottom:1px solid var(--line)}.bt:last-child{border-bottom:0}
.list{padding-left:18px;margin:0}.list li{margin:6px 0}.tag{font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;margin-right:6px}
footer{color:var(--muted);font-size:12px;padding-bottom:30px}
.lockf{display:flex;gap:8px;margin-top:10px}.lockf input{flex:1;min-width:0;padding:11px 12px;border-radius:10px;border:1px solid var(--line);background:#000;color:var(--ink);font:inherit}
.btn{padding:10px 14px;border-radius:10px;border:0;background:var(--accent);color:#fff;font:inherit;font-weight:700;cursor:pointer}
.btn.ghost{background:transparent;border:1px solid var(--line);color:var(--muted)}#priv{display:none}
</style>
</head>
<body>
<header>
  <h1>☕ Mocha Picks · Progreso</h1>
  <div class="sub" id="upd"></div>
  <div class="sub"><a href="./">← Volver a los picks</a></div>
</header>
<main>
  <h2>¿Se cumplen nuestras probabilidades?</h2>
  <div class="card" id="fiab"></div>
  <h2>Acierto real de los picks publicados</h2>
  <div class="card" id="picks"></div>
  <div id="lockbox"></div>
  <div id="priv">
  <h2>Pruebas en sombra</h2>
  <p class="small">Cada prueba calcula, antes de cada partido, la probabilidad del modelo actual y la del modelo mejorado,
  sin cambiar los picks publicados. Se activa solo con 200 partidos, mejora con IC 95% por encima de 0 y tu autorización.</p>
  <div id="shadows"></div>
  <h2>Investigación histórica (backtests)</h2>
  <div class="card"><div id="bt"></div>
  <p class="small">Mejora = reducción de log loss frente al modelo actual en temporadas no usadas para elegir la variante, con IC 95% por fecha.</p></div>
  <h2>Qué sigue</h2>
  <div class="card"><ul class="list" id="next"></ul></div>
  </div>
</main>
<footer><p>No es una recomendación de apuesta. Mocha Picks no ejecuta apuestas.</p></footer>
<script>
const D = __DATA__;
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const pc = v => v == null ? "—" : (100 * v).toFixed(1) + "%";
const f4 = v => v == null ? "—" : v.toFixed(4);
const when = s => s ? new Date(s).toLocaleString("es", {day: "numeric", month: "short", hour: "2-digit", minute: "2-digit"}) : "sin datos aún";
document.getElementById("upd").textContent = "Actualizado " + when(D.updated);
function status(s) {
  if (!s.n) return ["Esperando partidos", "muted"];
  if (s.ic_inf != null && s.ic_inf > 0 && s.n >= s.objetivo) return ["Lista para revisar", "good"];
  if (s.ic_sup != null && s.ic_sup < 0) return ["Va empeorando", "bad"];
  if (s.mejora != null && s.mejora > 0) return ["Va mejorando (sin confirmar)", "mid"];
  if (s.mejora != null && s.mejora < 0) return ["Por ahora no mejora", "mid"];
  return ["Acumulando partidos", "muted"];
}
function drawPrivate(X) {
document.getElementById("shadows").innerHTML = X.shadows.map(s => {
  const [lab, cls] = status(s), p = Math.min(100, 100 * s.n / s.objetivo);
  const ci = s.ic_inf == null ? "" : ` [${f4(s.ic_inf)}; ${f4(s.ic_sup)}]`;
  return `<div class="card"><div class="row"><span class="t">${esc(s.titulo)}</span><span class="badge ${cls}">${lab}</span></div>
    <div class="small">${esc(s.que)}</div>
    <div class="prog" role="progressbar" aria-valuenow="${s.n}" aria-valuemax="${s.objetivo}"><i style="width:${p.toFixed(1)}%"></i></div>
    <div class="row small"><span>${s.n} de ${s.objetivo} partidos</span><span>última foto: ${when(s.actualizado)}</span></div>
    ${s.n ? `<div class="grid"><span>Acierto actual / mejorado</span><b>${pc(s.acc_base)} / ${pc(s.acc_nuevo)}</b>
      <span>Log loss actual / mejorado</span><b>${f4(s.ll_base)} / ${f4(s.ll_nuevo)}</b>
      <span>Mejora (más es mejor)</span><b class="${s.mejora > 0 ? "good" : s.mejora < 0 ? "bad" : ""}">${f4(s.mejora)}${ci}</b>
      ${s.minutos_antes != null ? `<span>Minutos antes del inicio (mediana)</span><b>${Math.round(s.minutos_antes)}</b>` : ""}</div>` : ""}
  </div>`;
}).join("");
}
const F = D.fiabilidad || {};
document.getElementById("fiab").innerHTML = Object.keys(F).length ? Object.entries(F).map(([dep, x]) => `
  <div class="t" style="margin-top:6px">${esc(dep)} · ${x.n.toLocaleString("es")} partidos · acierto total ${pc(x.acierto_total)}</div>
  ${x.tramos.map(t => `<div class="row small" style="margin-top:6px"><span>Pick con ${esc(t.tramo)} <span class="muted">(${t.n})</span></span>
    <span>dijimos <b>${pc(t.prob_media)}</b> · acertó <b class="${Math.abs(t.acierto - t.prob_media) <= .05 ? "good" : "mid"}">${pc(t.acierto)}</b></span></div>
    <div class="prog" style="margin:4px 0 0"><i style="width:${(100 * t.acierto).toFixed(1)}%"></i></div>`).join("")}`).join("<hr style='border:0;border-top:1px solid var(--line);margin:12px 0'>")
  + `<p class="small">Validación fuera de muestra del pick final (Kalshi + casas + modelo), con pesos entrenados solo con partidos anteriores. Si "acertó" ≈ "dijimos", las probabilidades son fiables.</p>`
  : `<p class="small">Aún sin datos.</p>`;
const pk = D.picks.filter(x => x.n);
document.getElementById("picks").innerHTML = pk.length
  ? `<table><tr><th>Deporte</th><th>Partidos</th><th>Acierto</th><th>Log loss</th></tr>${pk.map(x => `<tr><td>${esc(x.deporte)}</td><td class="n">${x.n}</td><td class="n">${pc(x.acierto)}</td><td class="n">${f4(x.logloss)}</td></tr>`).join("")}</table>
     <p class="small">Pick de ganador publicado (casas si existen, modelo si no), última foto antes del inicio. Actualizado ${when(D.picks_updated)}. Con pocos partidos el acierto varía mucho.</p>`
  : `<p class="small">Aún no hay partidos resueltos.</p>`;
const vcls = v => v.startsWith("supera") ? "good" : (v === "descartada" || v === "Kalshi gana") ? "bad" : "mid";
function drawPrivate2(X) {
document.getElementById("bt").innerHTML = X.backtests.map(b => `<div class="bt"><div class="row"><span class="t">${esc(b.prueba)}</span>
  <span class="badge ${vcls(b.veredicto)}">${esc(b.veredicto)}</span></div>
  <div class="small">${b.partidos.toLocaleString("es")} partidos · acierto ${esc(b.acierto)} · mejora ${esc(b.mejora)}</div></div>`).join("");
document.getElementById("next").innerHTML = X.next.map(([t, x]) => `<li><span class="tag">${esc(t)}</span>${esc(x)}</li>`).join("");
}
const KEY = "mocha-progreso";
const b64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
async function unlock(pw) {
  const L = D.lock;
  const base = await crypto.subtle.importKey("raw", new TextEncoder().encode(pw), "PBKDF2", false, ["deriveKey"]);
  const key = await crypto.subtle.deriveKey({name: "PBKDF2", salt: b64(L.salt), iterations: L.iter, hash: "SHA-256"}, base,
    {name: "AES-GCM", length: 256}, false, ["decrypt"]);
  return JSON.parse(new TextDecoder().decode(await crypto.subtle.decrypt({name: "AES-GCM", iv: b64(L.iv)}, key, b64(L.ct))));
}
function lockForm(msg) {
  document.getElementById("priv").style.display = "none";
  document.getElementById("lockbox").innerHTML = D.lock ? `<div class="card"><div class="t">🔒 Detalles privados</div>
    <div class="small">Pruebas en sombra, investigación y próximos pasos. Solo con la clave.</div>
    <form class="lockf" id="lockf"><input type="password" id="pw" placeholder="Clave" autocomplete="current-password" aria-label="Clave"><button class="btn">Ver</button></form>
    <label class="small" style="display:block;margin-top:8px"><input type="checkbox" id="rem" checked> Recordar en este dispositivo</label>
    ${msg ? `<div class="small bad" style="margin-top:6px">${esc(msg)}</div>` : ""}</div>` : "";
  const f = document.getElementById("lockf");
  if (f) f.onsubmit = async e => { e.preventDefault(); const pw = document.getElementById("pw").value; await tryOpen(pw, document.getElementById("rem").checked); };
}
async function tryOpen(pw, remember) {
  try {
    const X = await unlock(pw);
    try { if (remember) localStorage.setItem(KEY, pw); } catch (e) {}
    drawPrivate(X); drawPrivate2(X);
    document.getElementById("priv").style.display = "block";
    document.getElementById("lockbox").innerHTML = `<div class="card row"><span class="small">🔓 Detalles privados visibles</span><button class="btn ghost" id="lockbtn">Bloquear</button></div>`;
    document.getElementById("lockbtn").onclick = () => { try { localStorage.removeItem(KEY); } catch (e) {} lockForm(); };
  } catch (e) {
    try { localStorage.removeItem(KEY); } catch (e2) {}
    lockForm(pw ? "Clave incorrecta" : "");
  }
}
let saved = null; try { saved = localStorage.getItem(KEY); } catch (e) {}
if (D.lock && saved) tryOpen(saved, true); else lockForm();
</script>
</body>
</html>
"""


def main(out="docs/progreso.html"):
    p = Path(out); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render(collect(), os.environ.get(CLAVE_ENV) or None), encoding="utf-8")
    print(f"{out} generado")


if __name__ == "__main__":
    main()
