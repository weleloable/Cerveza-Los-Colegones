const CACHE_NAME = "colegones-v2";
const APP_SHELL = [
  "./index.html",
  "./style.css",
  "./app.js",
  "./manifest.json",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "../Heartsteel_trigger_SFX_2.ogg",
  "../FotoEquipo.jpeg",
];
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Receta: red primero (para recoger ediciones nuevas), caché como respaldo
  // si no hay conexión durante la cocción.
  if (url.pathname.endsWith("/Recetas_Cerveza.json")) {
    event.respondWith(
      fetch(event.request)
        .then((resp) => {
          const copia = resp.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copia));
          return resp;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // Resto de recursos: caché primero (app shell), red como respaldo.
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});

// Permite que la app le pida al Service Worker que muestre una notificación
// del sistema (más fiable que Notification() directa cuando la pestaña está
// en segundo plano, sobre todo en Android).
self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "SHOW_NOTIFICATION") {
    const { title, body } = event.data;
    self.registration.showNotification(title, {
      body,
      icon: "./icons/icon-192.png",
      badge: "./icons/icon-192.png",
      vibrate: [200, 100, 200, 100, 200],
      tag: "colegones-alerta",
      renotify: true,
    });
  }
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: "window" }).then((clientList) => {
      if (clientList.length > 0) return clientList[0].focus();
      return self.clients.openWindow("./index.html");
    })
  );
});
