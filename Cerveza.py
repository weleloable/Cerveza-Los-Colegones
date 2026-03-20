import streamlit as st
import pandas as pd
import time
import base64
import json
import os
from streamlit_autorefresh import st_autorefresh

# ==========================================
# 1. CONFIGURACIÓN Y ESTILOS
# ==========================================
st.set_page_config(page_title="Cerveza LOS COLEGONES", page_icon="🍺", layout="wide")
st_autorefresh(interval=1000, key="datarefresh")

NOMBRE_ARCHIVO = "Recetas_Cerveza.json"

def aplicar_estilo_fondo():
    color = "rgba(255, 0, 0, 0.7)" if st.session_state.get('alerta_disparada', False) else "white"
    st.markdown(f"""
        <style>
        .stApp {{ background-color: {color} !important; transition: background-color 0.5s ease; }}
        </style>
    """, unsafe_allow_html=True)

def reproducir_sonido():
    try:
        with open("Heartsteel_trigger_SFX_2.ogg", "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode()
            st.components.v1.html(f"""
                <audio autoplay><source src="data:audio/ogg;base64,{audio_base64}" type="audio/ogg"></audio>
            """, height=0)
            time.sleep(3)
    except FileNotFoundError:
        st.error("Archivo de sonido no encontrado")

# ==========================================
# 2. GESTIÓN DE DATOS (JSON)
# ==========================================
def cargar_recetas():
    if os.path.exists(NOMBRE_ARCHIVO):
        with open(NOMBRE_ARCHIVO, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "IPA": [
            {"paso": "Macerado", "objetivo": "65°C / 60 min", "instruccion": "Añadir Malta.", "tiempo_min": 60},
            {"paso": "Hervido", "objetivo": "96°C / 60 min", "instruccion": "Lúpulos.", "tiempo_min": 60, 
             "hitos": [{"minuto": 60, "nombre": "Lúpulo Amargor"}, {"minuto": 10, "nombre": "Lúpulo Sabor"}]}
        ]
    }

if 'mis_recetas' not in st.session_state:
    st.session_state.mis_recetas = cargar_recetas()

# ==========================================
# 3. GESTIÓN DEL ESTADO Y NAVEGACIÓN
# ==========================================
if 'paso_actual' not in st.session_state: st.session_state.paso_actual = 0
if 'timer_inicio' not in st.session_state: st.session_state.timer_inicio = None
if 'alerta_disparada' not in st.session_state: st.session_state.alerta_disparada = False
if 'mostrar_celebracion' not in st.session_state: st.session_state.mostrar_celebracion = False
if 'tiempo_acumulado' not in st.session_state: st.session_state.tiempo_acumulado = 0
if 'ultima_actualizacion' not in st.session_state: st.session_state.ultima_actualizacion = time.time()
if 'pausado' not in st.session_state: st.session_state.pausado = False

def reset_paso(nuevo_paso):
    st.session_state.paso_actual = nuevo_paso
    st.session_state.timer_inicio = None
    st.session_state.alerta_disparada = False
    st.session_state.tiempo_acumulado = 0
    st.session_state.ultima_actualizacion = time.time()
    st.session_state.pausado = False
    st.rerun()

with st.sidebar:
    st.header("⚙️ Configuración")
    receta_activa = st.selectbox("Selecciona tu receta:", list(st.session_state.mis_recetas.keys()))
    if st.button("🔄 Reiniciar Proceso"):
        reset_paso(0)

# Obtener datos del paso actual
pasos = st.session_state.mis_recetas[receta_activa]
datos_paso = pasos[st.session_state.paso_actual]

# ==========================================
# 4. INTERFAZ PRINCIPAL
# ==========================================
aplicar_estilo_fondo()

st.title("🍺 Cerveza: LOS COLEGONES")
st.progress((st.session_state.paso_actual + 1) / len(pasos))
st.subheader(f"Paso {st.session_state.paso_actual + 1}: {datos_paso['paso']}")

c1, c2 = st.columns([1, 2])
c1.metric("Objetivo", datos_paso['objetivo'])
c2.warning(f"👉 **Instrucción:** {datos_paso['instruccion']}")

paso_listo = False

# --- CASO A: TEMPORIZADOR ---
if "tiempo_min" in datos_paso:
    factor = 60 # Cambiar a 1 para testeo rápido, 60 para minutos reales
    duracion_seg = int(datos_paso["tiempo_min"]) * factor
    ahora = time.time()

    if st.session_state.timer_inicio is None:
        if st.button("🚀 INICIAR TEMPORIZADOR", type="primary", use_container_width=True):
            st.session_state.timer_inicio = ahora
            st.session_state.ultima_actualizacion = ahora
            st.rerun()
    else:
        # Lógica de tiempo y pausa
        delta = ahora - st.session_state.ultima_actualizacion
        st.session_state.ultima_actualizacion = ahora
        if not st.session_state.pausado:
            st.session_state.tiempo_acumulado += delta

        restante = max(0, duracion_seg - st.session_state.tiempo_acumulado)
        mins, segs = divmod(int(restante), 60)
        
        st.metric("Tiempo Restante", f"{mins:02d}:{segs:02d}", 
                  delta="PAUSADO" if st.session_state.pausado else None, delta_color="inverse")
        st.progress(min(st.session_state.tiempo_acumulado / duracion_seg, 1.0))

        # CONTROL DE HITOS (Lúpulos)
        if "hitos" in datos_paso:
            st.write("### 🌿 Adiciones de Lúpulo")
            for hito in datos_paso["hitos"]:
                key_h = f"h_{st.session_state.paso_actual}_{hito['minuto']}"
                confirmado = st.checkbox(f"✅ {hito['nombre']}", key=key_h)
                
                # Disparar Alerta: Si tiempo restante <= tiempo del hito
                # Usamos 'and' lógico para mayor seguridad
                if int(restante) <= (int(hito['minuto']) * factor) and not confirmado:
                    if not st.session_state.pausado:
                        st.session_state.pausado = True
                        st.session_state.alerta_disparada = True
                        reproducir_sonido()
                        st.rerun()
                
                # Quitar Alerta al confirmar
                if confirmado and st.session_state.pausado:
                    st.session_state.pausado = False
                    st.session_state.alerta_disparada = False
                    st.rerun()

        if restante <= 0:
            st.success("🔔 ¡TIEMPO COMPLETADO!")
            paso_listo = True
            if not st.session_state.alerta_disparada:
                st.session_state.alerta_disparada = True
                reproducir_sonido()
                st.rerun()

# --- CASO B: PESADO ---
elif "granos" in datos_paso:
    st.subheader("⚖️ Control de Pesado")
    checks = []
    for i, g in enumerate(datos_paso["granos"]):
        checks.append(st.checkbox(f"Pesado: {g['nombre']} ({g['cantidad']})", key=f"g_{st.session_state.paso_actual}_{i}"))
    if all(checks):
        st.success("✅ Pesado completado.")
        paso_listo = st.checkbox("**¿Confirmar fin de pesaje?**", key=f"conf_grano_{st.session_state.paso_actual}")

# --- CASO C: NORMAL ---
else:
    paso_listo = st.checkbox("✅ **Objetivo OK**", key=f"ok_{st.session_state.paso_actual}")

# ==========================================
# 5. NAVEGACIÓN Y CELEBRACIÓN
# ==========================================
st.divider()
col_prev, col_next = st.columns(2)

with col_prev:
    if st.button("⬅️ Paso Anterior") and st.session_state.paso_actual > 0:
        reset_paso(st.session_state.paso_actual - 1)

with col_next:
    if st.session_state.paso_actual < len(pasos) - 1:
        if st.button("Siguiente Paso ➡️", type="primary" if paso_listo else "secondary", use_container_width=True):
            reset_paso(st.session_state.paso_actual + 1)
    else:
        if st.button("🎉 Finalizar Lote", disabled=not paso_listo, type="primary", use_container_width=True):
            st.session_state.mostrar_celebracion = True
            st.rerun()

@st.dialog("¡LOTE TERMINADO CON ÉXITO! 🍻")
def ventana_celebracion():
    try:
        st.image("FotoEquipo.jpeg", use_container_width=True)
    except:
        st.error("No se encontró 'FotoEquipo.jpeg'")
    st.write("¡Felicidades Colegón! El proceso ha finalizado correctamente.")
    if st.button("Cerrar"):
        st.session_state.mostrar_celebracion = False
        st.rerun()

if st.session_state.mostrar_celebracion:
    ventana_celebracion()
