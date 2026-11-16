import json, os, re, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from kalshi_nba import progreso


class TestProgreso(unittest.TestCase):
    def test_renders_with_nan_and_missing_files(self):
        with tempfile.TemporaryDirectory() as d:
            old = progreso.P; progreso.P = Path(d)
            try:
                Path(d, "final_shadow_scoreboard.json").write_text('{"by_sport":[{"sport":"nba","n":4,"acierto_final":1.0,"ic95_inf":NaN}]}')
                Path(d, "nba_lineup_shadow_scoreboard.json").write_text(json.dumps({"updated_utc": "2026-11-13T00:00Z", "resultado": {
                    "n": 12, "logloss_base": .6, "logloss_lineup": .59, "acierto_base": .6, "acierto_lineup": .62,
                    "mejora_logloss": {"mejora": .01, "ic95_inf": -.01, "ic95_sup": .03}}}))
                data = progreso.collect()
                html = progreso.render(data)
                locked = progreso.render(data, "clave-de-prueba")
            finally:
                progreso.P = old
        d = json.loads(re.search(r"const D = (.*?);\n", html, re.S).group(1))
        self.assertNotIn("shadows", d); self.assertIsNone(d["lock"])        # sin clave: lo privado no se publica
        L = json.loads(re.search(r"const D = (.*?);\n", locked, re.S).group(1))["lock"]
        self.assertNotIn("logloss_base", locked)
        import base64
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        b = base64.b64decode
        key = PBKDF2HMAC(hashes.SHA256(), 32, b(L["salt"]), L["iter"]).derive(b"clave-de-prueba")
        d = json.loads(AESGCM(key).decrypt(b(L["iv"]), b(L["ct"]), None))
        nba = d["shadows"][0]
        self.assertEqual((nba["n"], nba["mejora"], nba["ic_inf"]), (12, .01, -.01))
        self.assertEqual(d["shadows"][1]["n"], 0)                      # NFL sin archivo: 0, no error
        self.assertEqual(data["picks"][0]["acierto"], 1.0)
        self.assertIn('href="./"', html)


if __name__ == "__main__":
    unittest.main()
