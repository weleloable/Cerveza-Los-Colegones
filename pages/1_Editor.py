import streamlit as st
import json
import os
import pandas as pd
import copy

st.set_page_config(page_title="Editor Maestro - Los Colegones", page_icon="📝", layout="wide")

NOMBRE_ARCHIVO = "Recetas_Cerveza.json"

password = st.text_input("Contraseña de Maestro Cervecero", type="password")
if password != "colegones":
    st.stop()

# --- FUNCIONES DE PERSISTENCIA ---
def cargar_todo():
    if os.path.exists(NOMBRE_ARCHIVO):
        with open(NOMBRE_ARCHIVO, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return {}
    return {}

def guardar_todo(diccionario):
    with open(NOMBRE_ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(diccionario, f, indent=4, ensure_ascii=False)

# Inicializar base de datos en el estado de la sesión
if 'db' not in st.session_state:
    st.session_state.db = cargar_todo()

st.title("📝 Panel de Control de Recetas")
st.markdown("---")

# --- BARRA LATERAL: OPERACIONES ---
with st.sidebar:
    st.header("🛠️ Operaciones")
    menu = ["Editar Receta", "Duplicar Receta", "Crear desde Cero", "Borrar Receta"]
    opcion = st.radio("Selecciona una acción:", menu)
    st.divider()
    if st.button("🔄 Recargar desde Archivo"):
        st.session_state.db = cargar_todo()
        st.rerun()

# --- LÓGICA DE DUPLICAR RECETA ---
if opcion == "Duplicar Receta":
    st.subheader("👯 Clonar una Receta Existente")
    receta_origen = st.selectbox("Receta base para duplicar:", list(st.session_state.db.keys()))
    nuevo_nombre = st.text_input("Nombre de la nueva versión (ej: IPA Tropical v2):")
    
    if st.button("Copiar Receta"):
        if nuevo_nombre and nuevo_nombre not in st.session_state.db:
            # Hacemos una 'deep copy' para que no se vinculen los datos
            st.session_state.db[nuevo_nombre] = copy.deepcopy(st.session_state.db[receta_origen])
            guardar_todo(st.session_state.db)
            st.success(f"✅ Se ha creado '{nuevo_nombre}' basada en '{receta_origen}'")
            st.balloons()
        else:
            st.error("Error: El nombre está vacío o ya existe una receta con ese nombre.")

# --- LÓGICA DE EDITAR (MEJORADA) ---
elif opcion == "Editar Receta":
    nombres_recetas = list(st.session_state.db.keys())
    if not nombres_recetas:
        st.warning("No hay recetas guardadas. Crea una primero.")
    else:
        seleccion = st.selectbox("Selecciona receta:", nombres_recetas)
        receta_data = st.session_state.db[seleccion]
        
        # Usamos columnas para organizar el editor
        col_tabla, col_json = st.columns([2, 1])
        
        with col_tabla:
            st.write("### ⏱️ Pasos y Tiempos")
            df = pd.DataFrame(receta_data)
            # Editor de tabla para campos simples
            columnas_visibles = [c for c in df.columns if c not in ['granos', 'hitos']]
            df_editado = st.data_editor(df[columnas_visibles], num_rows="dynamic", use_container_width=True)
            
        with col_json:
            st.write("### 🧬 Estructura Completa")
            st.caption("Usa este bloque para editar Granos e Hitos (formato JSON)")
            # Editor de texto para el JSON completo (permite editar listas anidadas)
            texto_json = st.text_area(
                "JSON de la Receta", 
                value=json.dumps(receta_data, indent=4, ensure_ascii=False),
                height=500
            )

        if st.button("💾 SOBRESCRIBIR RECETA", type="primary", use_container_width=True):
            try:
                # Validamos que el JSON sea correcto
                nueva_receta = json.loads(texto_json)
                st.session_state.db[seleccion] = nueva_receta
                guardar_todo(st.session_state.db)
                st.success("¡Receta guardada!")
            except Exception as e:
                st.error(f"Error en el formato JSON: {e}")

# --- CREAR DESDE CERO ---
elif opcion == "Crear desde Cero":
    st.subheader("🆕 Nueva Receta Vacía")
    nombre_nueva = st.text_input("Nombre de la cerveza:")
    if st.button("Crear"):
        if nombre_nueva and nombre_nueva not in st.session_state.db:
            st.session_state.db[nombre_nueva] = [{"paso": "Inicio", "objetivo": "0", "instruccion": "Nueva"}]
            guardar_todo(st.session_state.db)
            st.rerun()

# --- BORRAR ---
elif opcion == "Borrar Receta":
    st.subheader("⚠️ Zona de Peligro")
    receta_borrar = st.selectbox("Selecciona receta a eliminar:", list(st.session_state.db.keys()))
    confirmar = st.checkbox("Confirmo que quiero borrar esta receta para siempre")
    if st.button("🗑️ ELIMINAR", disabled=not confirmar):
        del st.session_state.db[receta_borrar]
        guardar_todo(st.session_state.db)
        st.rerun()
