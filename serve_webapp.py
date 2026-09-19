"""
Sirve la carpeta del proyecto (recetas + webapp/) por HTTP en la red local,
para poder abrir la PWA de seguimiento desde el móvil.

Uso:
    python serve_webapp.py            # puerto 8000 por defecto
    python serve_webapp.py 8080       # puerto a medida

Luego, en el móvil (misma red WiFi que el ordenador):
    http://<IP-de-este-ordenador>:8000/webapp/index.html
y "Añadir a pantalla de inicio" desde el navegador para instalarla como app.
"""
import http.server
import socket
import sys

# La consola de Windows a veces usa cp1252, que no sabe imprimir emoji.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PUERTO = int(sys.argv[1]) if len(sys.argv) > 1 else 8000


def ip_local():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


if __name__ == "__main__":
    ip = ip_local()
    print("=" * 60)
    print("🍺 Servidor de la PWA 'Los Colegones' en marcha")
    print(f"   Local:  http://localhost:{PUERTO}/webapp/index.html")
    print(f"   Móvil:  http://{ip}:{PUERTO}/webapp/index.html")
    print("   (el móvil debe estar en la misma red WiFi)")
    print("   Ctrl+C para detener")
    print("=" * 60)

    handler = http.server.SimpleHTTPRequestHandler
    with http.server.ThreadingHTTPServer(("0.0.0.0", PUERTO), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido.")
