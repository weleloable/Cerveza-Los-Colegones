"""Tests de almacen_recetas contra un GitHub falso (Contents API).

    python -m unittest tests.test_almacen_recetas -v
"""
import base64
import hashlib
import http.server
import json
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from almacen_recetas import AlmacenGitHub, ConflictoGitHub, crear_almacen_github  # noqa: E402

TOKEN = "ghp_TOKEN_SECRETO_DE_PRUEBA"
RUTA = "/repos/yo/repo/contents/Recetas_Cerveza.json"


class GitHubFalso(http.server.BaseHTTPRequestHandler):
    estado = {}

    def log_message(self, *a):
        pass

    def _responder(self, codigo, cuerpo):
        datos = json.dumps(cuerpo).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def _autorizado(self):
        GitHubFalso.estado.setdefault("auth", []).append(self.headers.get("Authorization"))
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            self._responder(401, {"message": "Bad credentials"})
            return False
        return True

    def do_GET(self):
        if not self._autorizado():
            return
        if self.path.split("?")[0] != RUTA:
            return self._responder(404, {"message": "Not Found"})
        GitHubFalso.estado["get_query"] = self.path.split("?", 1)[-1]
        e = GitHubFalso.estado
        self._responder(200, {"sha": e["sha"], "content": base64.encodebytes(e["contenido"]).decode()})

    def do_PUT(self):
        if not self._autorizado():
            return
        cuerpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        e = GitHubFalso.estado
        if cuerpo["sha"] != e["sha"]:
            return self._responder(409, {"message": "sha does not match"})
        e["contenido"] = base64.b64decode(cuerpo["content"])
        e["sha"] = hashlib.sha1(e["contenido"]).hexdigest()
        e["ultimo_put"] = cuerpo
        self._responder(200, {"content": {"sha": e["sha"]}})


class TestAlmacenGitHub(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), GitHubFalso)
        cls.api = f"http://127.0.0.1:{cls.server.server_address[1]}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        inicial = json.dumps({"IPA": [{"paso": "Macerar"}]}).encode()
        GitHubFalso.estado.clear()
        GitHubFalso.estado.update(contenido=inicial, sha=hashlib.sha1(inicial).hexdigest())
        self.almacen = AlmacenGitHub(TOKEN, "yo/repo", api=self.api)

    def test_cargar_devuelve_recetas_y_sha(self):
        recetas, sha = self.almacen.cargar()
        self.assertEqual(recetas, {"IPA": [{"paso": "Macerar"}]})
        self.assertEqual(sha, GitHubFalso.estado["sha"])
        self.assertEqual(GitHubFalso.estado["get_query"], "ref=main")

    def test_guardar_hace_commit_y_devuelve_sha_nuevo(self):
        _, sha = self.almacen.cargar()
        nuevo = self.almacen.guardar({"Vermut": [{"paso": "Añadir ñoras"}]}, sha)
        self.assertNotEqual(nuevo, sha)
        self.assertEqual(GitHubFalso.estado["ultimo_put"]["branch"], "main")
        self.assertTrue(GitHubFalso.estado["ultimo_put"]["message"])
        recetas, sha2 = self.almacen.cargar()
        self.assertEqual(recetas, {"Vermut": [{"paso": "Añadir ñoras"}]})
        self.assertEqual(sha2, nuevo)

    def test_guardado_conserva_tildes_y_enes_sin_escapar(self):
        _, sha = self.almacen.cargar()
        self.almacen.guardar({"Cerveza": [{"paso": "Cocción"}]}, sha)
        self.assertIn("Cocción", GitHubFalso.estado["contenido"].decode("utf-8"))

    def test_guardar_encadenado_con_el_sha_devuelto(self):
        _, sha = self.almacen.cargar()
        sha = self.almacen.guardar({"A": []}, sha)
        sha = self.almacen.guardar({"B": []}, sha)
        self.assertEqual(self.almacen.cargar()[0], {"B": []})

    def test_conflicto_si_otra_persona_guardo_antes(self):
        _, sha_viejo = self.almacen.cargar()
        self.almacen.guardar({"de_otro": []}, sha_viejo)
        with self.assertRaises(ConflictoGitHub):
            self.almacen.guardar({"mio": []}, sha_viejo)
        self.assertEqual(self.almacen.cargar()[0], {"de_otro": []})

    def test_token_malo_da_error_claro_sin_filtrar_el_token(self):
        malo = AlmacenGitHub("otro_token", "yo/repo", api=self.api)
        with self.assertRaises(RuntimeError) as ctx:
            malo.cargar()
        self.assertIn("401", str(ctx.exception))
        self.assertNotIn("otro_token", str(ctx.exception))

    def test_repo_inexistente_da_404(self):
        with self.assertRaises(RuntimeError) as ctx:
            AlmacenGitHub(TOKEN, "yo/no-existe", api=self.api).cargar()
        self.assertIn("404", str(ctx.exception))

    def test_sin_red_da_error_claro(self):
        with self.assertRaises(RuntimeError) as ctx:
            AlmacenGitHub(TOKEN, "yo/repo", api="http://127.0.0.1:9").cargar()
        self.assertIn("No se pudo contactar", str(ctx.exception))


class TestCrearAlmacen(unittest.TestCase):
    def test_sin_token_es_modo_local(self):
        self.assertIsNone(crear_almacen_github({}))

    def test_con_token_usa_valores_por_defecto(self):
        a = crear_almacen_github({"GITHUB_TOKEN": "t"})
        self.assertEqual((a.repo, a.rama), ("weleloable/Cerveza-Los-Colegones", "main"))

    def test_secretos_ausentes_no_revientan(self):
        class SinSecretos:
            def get(self, *a):
                raise FileNotFoundError("no secrets.toml")
        self.assertIsNone(crear_almacen_github(SinSecretos()))


if __name__ == "__main__":
    unittest.main()
