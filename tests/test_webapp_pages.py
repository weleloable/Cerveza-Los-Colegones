"""Comprueba que la PWA funciona bajo el subpath de GitHub Pages.

Pages sirve el repo en /Cerveza-Los-Colegones/. Este test levanta un servidor
HTTP que emula ese prefijo y resuelve cada referencia como lo haría el navegador.

    python -m unittest tests.test_webapp_pages -v
"""
import functools
import http.server
import json
import re
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urljoin

RAIZ = Path(__file__).resolve().parent.parent
PREFIJO = "/Cerveza-Los-Colegones"


class _HandlerConPrefijo(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        if path == PREFIJO:
            path = "/"
        elif path.startswith(PREFIJO + "/"):
            path = path[len(PREFIJO):]
        else:
            return str(RAIZ / "__fuera_del_prefijo__")
        return super().translate_path(path)

    def log_message(self, *args):
        pass


class TestWebappBajoSubpath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        handler = functools.partial(_HandlerConPrefijo, directory=str(RAIZ))
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}{PREFIJO}/"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def get(self, url):
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, r.read()

    def test_raiz_redirige_a_la_app(self):
        _, html = self.get(self.base)
        self.assertIn(b"./webapp/index.html", html)
        self.get(urljoin(self.base, "./webapp/index.html"))

    def test_referencias_del_html_resuelven(self):
        pagina = urljoin(self.base, "webapp/index.html")
        _, html = self.get(pagina)
        refs = re.findall(rb'(?:href|src)="([^"#]+)"', html)
        self.assertGreater(len(refs), 4)
        for ref in refs:
            ref = ref.decode()
            self.assertFalse(ref.startswith("/"), f"ruta absoluta que rompe bajo subpath: {ref}")
            if ref.startswith("http"):
                continue
            with self.subTest(ref=ref):
                self.assertEqual(self.get(urljoin(pagina, ref))[0], 200)

    def test_receta_se_carga_como_lo_hace_app_js(self):
        codigo = (RAIZ / "webapp" / "app.js").read_text(encoding="utf-8")
        ruta = re.search(r'const RECETA_URL = "([^"]+)"', codigo).group(1)
        self.assertFalse(ruta.startswith("/"), "RECETA_URL absoluta: rompe bajo subpath")
        status, cuerpo = self.get(urljoin(urljoin(self.base, "webapp/index.html"), ruta))
        self.assertEqual(status, 200)
        self.assertIsInstance(json.loads(cuerpo), dict)

    def test_manifest_e_iconos(self):
        url = urljoin(self.base, "webapp/manifest.json")
        _, cuerpo = self.get(url)
        manifest = json.loads(cuerpo)
        self.assertFalse(manifest["start_url"].startswith("/"))
        self.assertFalse(manifest["scope"].startswith("/"))
        self.assertEqual(self.get(urljoin(url, manifest["start_url"]))[0], 200)
        for icono in manifest["icons"]:
            with self.subTest(icono=icono["src"]):
                self.assertEqual(self.get(urljoin(url, icono["src"]))[0], 200)

    def test_service_worker_app_shell_completo(self):
        url = urljoin(self.base, "webapp/sw.js")
        _, cuerpo = self.get(url)
        js = cuerpo.decode("utf-8")
        shell = re.search(r"const APP_SHELL = \[(.*?)\];", js, re.S).group(1)
        rutas = re.findall(r'"([^"]+)"', shell)
        self.assertGreater(len(rutas), 5)
        for ruta in rutas:
            with self.subTest(ruta=ruta):
                self.assertFalse(ruta.startswith("/"))
                self.assertEqual(self.get(urljoin(url, ruta))[0], 200)
        self.assertNotRegex(js, r'=\s*"/Recetas', "ruta absoluta a la receta en sw.js")

    def test_fuera_del_prefijo_da_404(self):
        # Garantiza que el emulador es estricto: la raíz del dominio no sirve nada.
        base = self.base.replace(PREFIJO + "/", "/")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.get(base + "Recetas_Cerveza.json")
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
