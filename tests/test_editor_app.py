"""Ejecuta el editor Streamlit real (AppTest) en modo local y en modo GitHub.

    python -m unittest tests.test_editor_app -v
"""
import hashlib
import http.server
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from tests.test_almacen_recetas import TOKEN, GitHubFalso  # noqa: E402

EDITOR = str(RAIZ / "pages" / "1_Editor.py")


def abrir_editor(secretos=None):
    at = AppTest.from_file(EDITOR, default_timeout=30)
    for k, v in (secretos or {}).items():
        at.secrets[k] = v
    at.run()
    at.text_input[0].set_value("colegones").run()
    return at


def crear_receta(at, nombre):
    at.sidebar.radio[0].set_value("Crear desde Cero").run()
    at.text_input[1].set_value(nombre).run()
    [b for b in at.button if b.label == "Crear"][0].click().run()
    return at


class CarpetaTemporal(unittest.TestCase):
    """Ejecuta cada test en una carpeta temporal: un fallo nunca toca el JSON real."""

    def setUp(self):
        self.cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp()
        shutil.copy(RAIZ / "Recetas_Cerveza.json", self.tmp)
        os.chdir(self.tmp)

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestEditorModoLocal(CarpetaTemporal):
    def test_sin_token_edita_el_archivo_local_con_backup(self):
        at = abrir_editor()
        self.assertFalse(at.exception)
        self.assertIn("archivo local", at.sidebar.caption[0].value)
        crear_receta(at, "Cerveza de Prueba")
        self.assertFalse(at.exception)
        with open("Recetas_Cerveza.json", encoding="utf-8") as f:
            self.assertIn("Cerveza de Prueba", json.load(f))
        self.assertTrue(list(Path(".").glob("Recetas_Cerveza_*.json")), "no se creo backup")


class TestEditorModoGitHub(CarpetaTemporal):
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
        super().setUp()
        inicial = json.dumps({"IPA": [{"paso": "Macerar", "objetivo": "60", "instruccion": "x"}]}).encode()
        GitHubFalso.estado.clear()
        GitHubFalso.estado.update(contenido=inicial, sha=hashlib.sha1(inicial).hexdigest())
        self.secretos = {"GITHUB_TOKEN": TOKEN, "GITHUB_REPO": "yo/repo", "GITHUB_API": self.api}

    def test_con_token_carga_de_github_y_guarda_con_commit(self):
        at = abrir_editor(self.secretos)
        self.assertFalse(at.exception)
        self.assertIn("GitHub", at.sidebar.caption[0].value)
        crear_receta(at, "Vermut 5")
        self.assertFalse(at.exception)
        guardado = json.loads(GitHubFalso.estado["contenido"])
        self.assertEqual(set(guardado), {"IPA", "Vermut 5"})
        self.assertEqual(GitHubFalso.estado["ultimo_put"]["branch"], "main")

    def test_conflicto_muestra_error_y_no_pisa_lo_del_otro(self):
        at = abrir_editor(self.secretos)
        otro = json.dumps({"IPA": [], "de_otro": []}).encode()
        GitHubFalso.estado.update(contenido=otro, sha=hashlib.sha1(otro).hexdigest())
        crear_receta(at, "Mia")
        self.assertTrue(any("Otra persona guardó" in e.value for e in at.error))
        self.assertEqual(json.loads(GitHubFalso.estado["contenido"]), {"IPA": [], "de_otro": []})

    def test_token_malo_muestra_error_y_no_arranca(self):
        at = abrir_editor({**self.secretos, "GITHUB_TOKEN": "malo"})
        self.assertTrue(any("No pude cargar" in e.value for e in at.error))


if __name__ == "__main__":
    unittest.main()
