"use strict";

// ==========================================
// 0. CONSTANTES Y ESTADO PERSISTENTE
// ==========================================
const RECETA_URL = "../Recetas_Cerveza.json";
const STORAGE_KEY = "colegones_estado_v1";
const CHECKS_KEY = "colegones_checks_v1";
const SONIDO_KEY = "colegones_sonido_ok";

let recetas = {};
let checks = cargarJSON(CHECKS_KEY, {});
let estado = cargarJSON(STORAGE_KEY, {
  receta: null,
  paso: 0,
  timerInicioMs: null,   // epoch ms de cuándo arrancó el temporizador de este paso
  tiempoAcumuladoMs: 0,  // ms acumulados (permite pausa)
  pausado: false,
  alertaDisparada: false,
});

function cargarJSON(clave, valorPorDefecto) {
  try {
    const raw = localStorage.getItem(clave);
    return raw ? JSON.parse(raw) : valorPorDefecto;
  } catch { return valorPorDefecto; }
}
function guardarEstado() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(estado)); } catch {}
}
function guardarChecks() {
  try { localStorage.setItem(CHECKS_KEY, JSON.stringify(checks)); } catch {}
}
function claveCheck(sufijo) {
  return `${estado.receta}|${estado.paso}|${sufijo}`;
}

// ==========================================
// 1. ELEMENTOS DEL DOM
// ==========================================
const el = {
  selectReceta: document.getElementById("select-receta"),
  btnSync: document.getElementById("btn-sync"),
  btnReiniciar: document.getElementById("btn-reiniciar"),
  barraProgreso: document.getElementById("barra-progreso"),
  tituloPaso: document.getElementById("titulo-paso"),
  valorObjetivo: document.getElementById("valor-objetivo"),
  instruccion: document.getElementById("instruccion"),
  alertaBanner: document.getElementById("alerta-banner"),
  btnRepetirSonido: document.getElementById("btn-repetir-sonido"),
  zonaDinamica: document.getElementById("zona-dinamica"),
  btnAnterior: document.getElementById("btn-anterior"),
  btnSiguiente: document.getElementById("btn-siguiente"),
  btnSonido: document.getElementById("btn-sonido"),
  modal: document.getElementById("modal-celebracion"),
  btnCerrarModal: document.getElementById("btn-cerrar-modal"),
  audio: document.getElementById("audio-alarma"),
};

let pasoListo = false;
let tickInterval = null;

// ==========================================
// 2. CARGA DE LA RECETA
// ==========================================
async function cargarRecetas() {
  const resp = await fetch(RECETA_URL, { cache: "no-store" });
  if (!resp.ok) throw new Error("No se pudo cargar la receta");
  recetas = await resp.json();
}

async function iniciar() {
  try {
    await cargarRecetas();
  } catch (e) {
    el.instruccion.textContent = "⚠️ No se pudo cargar Recetas_Cerveza.json. ¿Estás sirviendo esta carpeta junto a la raíz del proyecto?";
    return;
  }

  const nombres = Object.keys(recetas);
  if (!nombres.length) return;

  if (!estado.receta || !recetas[estado.receta]) {
    estado.receta = nombres[0];
    estado.paso = 0;
  }

  el.selectReceta.innerHTML = nombres.map(n => `<option value="${n}">${n}</option>`).join("");
  el.selectReceta.value = estado.receta;

  if (Notification && Notification.permission === "granted") {
    el.btnSonido.classList.add("activo");
    el.btnSonido.textContent = "🔔 Sonido activo";
  }
  if (localStorage.getItem(SONIDO_KEY) === "1") {
    el.btnSonido.classList.add("activo");
    el.btnSonido.textContent = "🔔 Sonido activo";
  }

  render();
  if (tickInterval) clearInterval(tickInterval);
  tickInterval = setInterval(tick, 1000);
}

// ==========================================
// 3. NAVEGACIÓN
// ==========================================
function resetPaso(nuevoPaso) {
  estado.paso = nuevoPaso;
  estado.timerInicioMs = null;
  estado.tiempoAcumuladoMs = 0;
  estado.pausado = false;
  estado.alertaDisparada = false;
  document.body.classList.remove("en-alerta");
  guardarEstado();
  render();
}

el.selectReceta.addEventListener("change", () => {
  estado.receta = el.selectReceta.value;
  resetPaso(0);
});

el.btnReiniciar.addEventListener("click", () => resetPaso(0));

el.btnSync.addEventListener("click", async () => {
  el.btnSync.textContent = "⏳";
  try {
    await cargarRecetas();
    if (!recetas[estado.receta]) { estado.receta = Object.keys(recetas)[0]; estado.paso = 0; }
    const pasos = recetas[estado.receta] || [];
    if (estado.paso >= pasos.length) estado.paso = Math.max(0, pasos.length - 1);
    guardarEstado();
    render();
  } catch (e) { /* silencioso: nos quedamos con la última copia válida */ }
  el.btnSync.textContent = "↻";
});

el.btnAnterior.addEventListener("click", () => {
  if (estado.paso > 0) resetPaso(estado.paso - 1);
});

el.btnSiguiente.addEventListener("click", () => {
  const pasos = recetas[estado.receta];
  if (estado.paso < pasos.length - 1) {
    resetPaso(estado.paso + 1);
  } else {
    el.modal.classList.remove("oculto");
  }
});

el.btnCerrarModal.addEventListener("click", () => {
  el.modal.classList.add("oculto");
  resetPaso(0);
});

// ==========================================
// 4. SONIDO Y ALARMA
// ==========================================
el.btnSonido.addEventListener("click", async () => {
  // Truco estándar de PWA: reproducir+pausar dentro de un gesto de usuario
  // "desbloquea" el autoplay de audio para el resto de la sesión.
  try {
    el.audio.muted = true;
    await el.audio.play();
    el.audio.pause();
    el.audio.currentTime = 0;
    el.audio.muted = false;
    localStorage.setItem(SONIDO_KEY, "1");
  } catch {}

  if ("Notification" in window && Notification.permission === "default") {
    try { await Notification.requestPermission(); } catch {}
  }

  if (Notification.permission === "granted") {
    el.btnSonido.classList.add("activo");
    el.btnSonido.textContent = "🔔 Sonido activo";
  } else {
    el.btnSonido.textContent = "🔈 Sonido (sin notificaciones)";
  }
});

el.btnRepetirSonido.addEventListener("click", reproducirSonido);

function reproducirSonido() {
  try {
    el.audio.currentTime = 0;
    el.audio.play().catch(() => {});
  } catch {}
  if (navigator.vibrate) navigator.vibrate([250, 100, 250, 100, 250]);
}

function notificarSistema(titulo, cuerpo) {
  if (!("Notification" in window) || Notification.permission !== "granted") return;
  if (navigator.serviceWorker && navigator.serviceWorker.controller) {
    navigator.serviceWorker.controller.postMessage({ type: "SHOW_NOTIFICATION", title: titulo, body: cuerpo });
  } else {
    try { new Notification(titulo, { body: cuerpo, icon: "./icons/icon-192.png" }); } catch {}
  }
}

function dispararAlerta(titulo, cuerpo) {
  estado.alertaDisparada = true;
  estado.pausado = true;
  document.body.classList.add("en-alerta");
  guardarEstado();
  reproducirSonido();
  notificarSistema(titulo, cuerpo);
  render();
}

function limpiarAlerta() {
  estado.alertaDisparada = false;
  estado.pausado = false;
  document.body.classList.remove("en-alerta");
  guardarEstado();
}

// ==========================================
// 5. RENDER PRINCIPAL
// ==========================================
function render() {
  const pasos = recetas[estado.receta];
  if (!pasos) return;
  if (estado.paso > pasos.length - 1) estado.paso = pasos.length - 1;
  const paso = pasos[estado.paso];

  el.barraProgreso.style.width = `${((estado.paso + 1) / pasos.length) * 100}%`;
  el.tituloPaso.textContent = `Paso ${estado.paso + 1}: ${paso.paso}`;
  el.valorObjetivo.textContent = paso.objetivo || "-";
  el.instruccion.innerHTML = `👉 <strong>Instrucción:</strong> ${escapeHTML(paso.instruccion || "")}`;

  el.alertaBanner.classList.toggle("oculto", !estado.alertaDisparada);
  el.btnAnterior.disabled = estado.paso === 0;
  el.btnSiguiente.textContent = estado.paso < pasos.length - 1 ? "Siguiente ➡️" : "🎉 Finalizar Lote";

  pasoListo = false;
  el.zonaDinamica.innerHTML = "";

  if ("tiempo_min" in paso) {
    renderTemporizador(paso);
  } else if ("granos" in paso) {
    renderPesado(paso);
  } else {
    renderNormal(paso);
  }

  el.btnSiguiente.disabled = !pasoListo;
  el.btnSiguiente.classList.toggle("primario", pasoListo);
}

function escapeHTML(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

// --- CASO A: TEMPORIZADOR ---
function renderTemporizador(paso) {
  const duracionMs = Number(paso.tiempo_min) * 60 * 1000;

  if (estado.timerInicioMs === null) {
    const btn = document.createElement("button");
    btn.className = "btn primario";
    btn.style.width = "100%";
    btn.textContent = "🚀 INICIAR TEMPORIZADOR";
    btn.onclick = () => {
      estado.timerInicioMs = Date.now();
      estado.pausado = false;
      guardarEstado();
      render();
    };
    el.zonaDinamica.appendChild(btn);
    return;
  }

  const restanteMs = Math.max(0, duracionMs - estado.tiempoAcumuladoMs);
  const totalSeg = Math.ceil(restanteMs / 1000);
  const mins = String(Math.floor(totalSeg / 60)).padStart(2, "0");
  const segs = String(totalSeg % 60).padStart(2, "0");

  const wrap = document.createElement("div");
  wrap.innerHTML = `
    <div class="timer-valor">${mins}:${segs}</div>
    <div class="timer-estado">${estado.pausado ? "⏸️ PAUSADO" : "⏱️ En marcha"}</div>
  `;
  el.zonaDinamica.appendChild(wrap);

  if (Array.isArray(paso.hitos) && paso.hitos.length) {
    const titulo = document.createElement("div");
    titulo.className = "subtitulo";
    titulo.textContent = "🌿 Adiciones de Lúpulo";
    el.zonaDinamica.appendChild(titulo);

    paso.hitos.forEach((hito) => {
      const key = claveCheck(`hito_${hito.minuto}_${hito.nombre}`);
      const confirmado = !!checks[key];
      const fila = document.createElement("label");
      fila.className = "fila-check";
      fila.innerHTML = `<input type="checkbox" ${confirmado ? "checked" : ""}> ✅ ${escapeHTML(hito.nombre)}`;
      fila.querySelector("input").addEventListener("change", (e) => {
        checks[key] = e.target.checked;
        guardarChecks();
        if (e.target.checked && estado.alertaDisparada) limpiarAlerta();
        render();
      });
      el.zonaDinamica.appendChild(fila);

      const umbralMs = Number(hito.minuto) * 60 * 1000;
      if (restanteMs <= umbralMs && !confirmado && !estado.pausado) {
        dispararAlerta("🌿 ¡Toca añadir lúpulo!", hito.nombre);
      }
    });
  }

  if (restanteMs <= 0) {
    const ok = document.createElement("div");
    ok.className = "tarjeta";
    ok.style.color = "var(--verde)";
    ok.style.fontWeight = "700";
    ok.textContent = "🔔 ¡TIEMPO COMPLETADO!";
    el.zonaDinamica.appendChild(ok);
    pasoListo = true;
    if (!estado.alertaDisparada) {
      dispararAlerta("⏰ ¡Tiempo completado!", `${paso.paso} ha terminado.`);
    }
  }
}

// --- CASO B: PESADO ---
function renderPesado(paso) {
  const titulo = document.createElement("div");
  titulo.className = "subtitulo";
  titulo.textContent = "⚖️ Control de Pesado";
  el.zonaDinamica.appendChild(titulo);

  let todosMarcados = true;
  (paso.granos || []).forEach((g, i) => {
    const key = claveCheck(`grano_${i}`);
    const marcado = !!checks[key];
    if (!marcado) todosMarcados = false;
    const fila = document.createElement("label");
    fila.className = "fila-check";
    fila.innerHTML = `<input type="checkbox" ${marcado ? "checked" : ""}> Pesado: ${escapeHTML(g.nombre)} (${escapeHTML(g.cantidad)})`;
    fila.querySelector("input").addEventListener("change", (e) => {
      checks[key] = e.target.checked;
      guardarChecks();
      render();
    });
    el.zonaDinamica.appendChild(fila);
  });

  if (todosMarcados && (paso.granos || []).length) {
    const ok = document.createElement("div");
    ok.className = "tarjeta";
    ok.style.color = "var(--verde)";
    ok.textContent = "✅ Pesado completado.";
    el.zonaDinamica.appendChild(ok);

    const keyConf = claveCheck("confirmar_pesaje");
    const confirmado = !!checks[keyConf];
    const filaConf = document.createElement("label");
    filaConf.className = "fila-check";
    filaConf.innerHTML = `<input type="checkbox" ${confirmado ? "checked" : ""}> <strong>¿Confirmar fin de pesaje?</strong>`;
    filaConf.querySelector("input").addEventListener("change", (e) => {
      checks[keyConf] = e.target.checked;
      guardarChecks();
      render();
    });
    el.zonaDinamica.appendChild(filaConf);
    pasoListo = confirmado;
  }
}

// --- CASO C: NORMAL ---
function renderNormal(paso) {
  const key = claveCheck("ok");
  const marcado = !!checks[key];
  const fila = document.createElement("label");
  fila.className = "fila-check";
  fila.innerHTML = `<input type="checkbox" ${marcado ? "checked" : ""}> ✅ <strong>Objetivo OK</strong>`;
  fila.querySelector("input").addEventListener("change", (e) => {
    checks[key] = e.target.checked;
    guardarChecks();
    render();
  });
  el.zonaDinamica.appendChild(fila);
  pasoListo = marcado;
}

// ==========================================
// 6. TICK DEL TEMPORIZADOR (reloj real, no cuenta de ticks)
// ==========================================
let ultimoTickMs = Date.now();
function tick() {
  const ahora = Date.now();
  const delta = ahora - ultimoTickMs;
  ultimoTickMs = ahora;

  const paso = (recetas[estado.receta] || [])[estado.paso];
  if (paso && "tiempo_min" in paso && estado.timerInicioMs !== null && !estado.pausado) {
    estado.tiempoAcumuladoMs += delta;
    guardarEstado();
    render();
  }
}

// Al volver de segundo plano, recalculamos con el reloj real (por si el
// navegador congeló el setInterval mientras la pantalla estaba bloqueada).
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) {
    ultimoTickMs = Date.now();
    render();
  }
});

// ==========================================
// 7. SERVICE WORKER (offline + notificaciones)
// ==========================================
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("./sw.js").catch(() => {});
  });
}

// Ganchos de depuración: útil para probar desde la consola del navegador.
window.__debug = {
  get recetas() { return recetas; },
  get estado() { return estado; },
  get checks() { return checks; },
  render, guardarEstado,
};

iniciar();
