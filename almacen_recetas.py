"""Guardar y cargar Recetas_Cerveza.json directamente en GitHub (Contents API).

Streamlit Community Cloud tiene disco efimero: lo que se escribe ahi se pierde al
reiniciar y la PWA (GitHub Pages) nunca lo veria. Cada guardado es un commit.
Solo libreria estandar.
"""
import base64
import json
import urllib.error
import urllib.request

API = "https://api.github.com"
RUTA = "Recetas_Cerveza.json"


class ConflictoGitHub(Exception):
    """El archivo cambio en GitHub desde que se cargo (otra persona guardo antes)."""


class AlmacenGitHub:
    def __init__(self, token, repo, rama="main", ruta=RUTA, api=API):
        self.token, self.repo, self.rama, self.ruta, self.api = token, repo, rama, ruta, api

    def _peticion(self, metodo, cuerpo=None):
        url = f"{self.api}/repos/{self.repo}/contents/{self.ruta}"
        if metodo == "GET":
            url += f"?ref={self.rama}"
        datos = json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None
        req = urllib.request.Request(url, data=datos, method=metodo, headers={
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "colegones-editor",
        })
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if metodo == "PUT" and e.code in (409, 422):
                raise ConflictoGitHub("El archivo cambio en GitHub desde que lo cargaste.") from None
            detalle = ""
            try:
                detalle = json.loads(e.read().decode("utf-8")).get("message", "")
            except Exception:
                pass
            raise RuntimeError(f"GitHub respondio {e.code}: {detalle}") from None
        except urllib.error.URLError as e:
            raise RuntimeError(f"No se pudo contactar con GitHub: {e.reason}") from None

    def cargar(self):
        """Devuelve (recetas: dict, sha: str). El sha se pasa luego a guardar()."""
        resp = self._peticion("GET")
        contenido = base64.b64decode(resp["content"]).decode("utf-8")
        return json.loads(contenido), resp["sha"]

    def guardar(self, recetas, sha, mensaje="Editar recetas desde el editor online"):
        """Hace commit del JSON. Devuelve el sha nuevo. ConflictoGitHub si sha ya no es el vigente."""
        texto = json.dumps(recetas, indent=4, ensure_ascii=False)
        resp = self._peticion("PUT", {
            "message": mensaje,
            "content": base64.b64encode(texto.encode("utf-8")).decode("ascii"),
            "sha": sha,
            "branch": self.rama,
        })
        return resp["content"]["sha"]


def crear_almacen_github(secretos):
    """AlmacenGitHub si hay GITHUB_TOKEN en los secretos; None si no (modo archivo local)."""
    try:
        token = secretos.get("GITHUB_TOKEN")
        if not token:
            return None
        return AlmacenGitHub(
            token=token,
            repo=secretos.get("GITHUB_REPO", "weleloable/Cerveza-Los-Colegones"),
            rama=secretos.get("GITHUB_RAMA", "main"),
            api=secretos.get("GITHUB_API", API),
        )
    except Exception:
        return None
