import streamlit as st
import json
import os
import sys
import copy
import shutil
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from almacen_recetas import ConflictoGitHub, crear_almacen_github

st.set_page_config(page_title="Editor Maestro - Los Colegones", page_icon="📝", layout="wide")

NOMBRE_ARCHIVO = "Recetas_Cerveza.json"

password = st.text_input("Contraseña de Maestro Cervecero", type="password")
if password != "colegones":
    st.stop()

# Con GITHUB_TOKEN en los secretos (Streamlit Cloud) cada guardado es un commit
# en GitHub; sin token se edita el archivo local como siempre.
ALMACEN_GITHUB = crear_almacen_github(st.secrets)

# --- FUNCIONES DE PERSISTENCIA ---
def cargar_todo():
    if ALMACEN_GITHUB:
        try:
            recetas, st.session_state.sha_github = ALMACEN_GITHUB.cargar()
            return recetas
        except Exception as e:
            st.error(f"No pude cargar las recetas de GitHub: {e}")
            st.stop()
    if os.path.exists(NOMBRE_ARCHIVO):
        with open(NOMBRE_ARCHIVO, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}

def guardar_todo(diccionario):
    if ALMACEN_GITHUB:
        try:
            st.session_state.sha_github = ALMACEN_GITHUB.guardar(diccionario, st.session_state.sha_github)
        except ConflictoGitHub:
            st.error("Otra persona guardó antes que tú. Pulsa «Recargar desde Archivo» en el menú lateral (se pierde tu último cambio) y repítelo.")
            st.stop()
        except Exception as e:
            st.error(f"No se pudo guardar en GitHub: {e}")
            st.stop()
        return
    # Backup con timestamp antes de sobrescribir, por si algo sale mal.
    if os.path.exists(NOMBRE_ARCHIVO):
        base = os.path.splitext(NOMBRE_ARCHIVO)[0]
        tag = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(NOMBRE_ARCHIVO, f"{base}_{tag}.json")
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
    st.caption("Guardando en GitHub (cada cambio es un commit)" if ALMACEN_GITHUB else "Guardando en el archivo local")
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
            st.session_state.db[nuevo_nombre] = copy.deepcopy(st.session_state.db[receta_origen])
            guardar_todo(st.session_state.db)
            st.success(f"✅ Se ha creado '{nuevo_nombre}' basada en '{receta_origen}'")
            st.balloons()
        else:
            st.error("Error: El nombre está vacío o ya existe una receta con ese nombre.")

# --- LÓGICA DE EDITAR (FORMULARIO POR PASO, SIN JSON A MANO) ---
elif opcion == "Editar Receta":
    nombres_recetas = list(st.session_state.db.keys())
    if not nombres_recetas:
        st.warning("No hay recetas guardadas. Crea una primero.")
    else:
        seleccion = st.selectbox("Selecciona receta:", nombres_recetas)

        # Si cambiamos de receta, olvidamos el paso que estábamos editando.
        if st.session_state.get('_receta_activa_editor') != seleccion:
            st.session_state._receta_activa_editor = seleccion
            st.session_state.paso_edit_idx = 0

        receta_data = st.session_state.db[seleccion]
        if not receta_data:
            receta_data.append({"paso": "Nuevo paso", "objetivo": "", "instruccion": ""})

        st.session_state.paso_edit_idx = max(0, min(st.session_state.get('paso_edit_idx', 0), len(receta_data) - 1))

        col_lista, col_form = st.columns([1, 2])

        # --- COLUMNA IZQUIERDA: LISTA DE PASOS (reordenar / seleccionar / borrar) ---
        with col_lista:
            st.write("### 🧭 Pasos de la receta")
            for i, p in enumerate(receta_data):
                es_actual = (i == st.session_state.paso_edit_idx)
                c_sel, c_up, c_down, c_del = st.columns([5, 1, 1, 1])
                with c_sel:
                    if st.button(f"{'👉 ' if es_actual else ''}{i+1}. {p.get('paso', '(sin nombre)')}",
                                 key=f"sel_{seleccion}_{i}", use_container_width=True,
                                 type="primary" if es_actual else "secondary"):
                        st.session_state.paso_edit_idx = i
                        st.rerun()
                with c_up:
                    if st.button("▲", key=f"up_{seleccion}_{i}", disabled=(i == 0), use_container_width=True):
                        receta_data[i - 1], receta_data[i] = receta_data[i], receta_data[i - 1]
                        guardar_todo(st.session_state.db)
                        st.session_state.paso_edit_idx = i - 1
                        st.rerun()
                with c_down:
                    if st.button("▼", key=f"down_{seleccion}_{i}", disabled=(i == len(receta_data) - 1), use_container_width=True):
                        receta_data[i + 1], receta_data[i] = receta_data[i], receta_data[i + 1]
                        guardar_todo(st.session_state.db)
                        st.session_state.paso_edit_idx = i + 1
                        st.rerun()
                with c_del:
                    if st.button("🗑️", key=f"del_{seleccion}_{i}", disabled=(len(receta_data) <= 1), use_container_width=True):
                        receta_data.pop(i)
                        guardar_todo(st.session_state.db)
                        st.session_state.paso_edit_idx = max(0, i - 1)
                        st.rerun()

            st.divider()
            if st.button("➕ Añadir paso al final", use_container_width=True):
                receta_data.append({"paso": "Nuevo paso", "objetivo": "", "instruccion": ""})
                guardar_todo(st.session_state.db)
                st.session_state.paso_edit_idx = len(receta_data) - 1
                st.rerun()

        # --- COLUMNA DERECHA: FORMULARIO DEL PASO SELECCIONADO ---
        with col_form:
            idx = st.session_state.paso_edit_idx
            paso_actual = receta_data[idx]
            clave_paso = f"{seleccion}_{idx}"

            # Cargamos las filas dinámicas (granos/hitos) en session_state solo
            # cuando cambiamos de paso, para no perder ediciones a medio hacer.
            if st.session_state.get('_clave_paso_cargada') != clave_paso:
                st.session_state._clave_paso_cargada = clave_paso
                st.session_state.filas_granos = [
                    {"id": str(uuid.uuid4()), "nombre": g.get("nombre", ""), "cantidad": g.get("cantidad", "")}
                    for g in paso_actual.get("granos", [])
                ]
                st.session_state.filas_hitos = [
                    {"id": str(uuid.uuid4()), "nombre": h.get("nombre", ""), "minuto": h.get("minuto", "")}
                    for h in paso_actual.get("hitos", [])
                ]

            st.write(f"### ✏️ Editando Paso {idx + 1}")

            nombre_paso = st.text_input("Nombre del paso", value=paso_actual.get("paso", ""), key=f"nombre_{clave_paso}")
            objetivo = st.text_input("Objetivo", value=paso_actual.get("objetivo", ""), key=f"obj_{clave_paso}")
            instruccion = st.text_area("Instrucción", value=paso_actual.get("instruccion", ""), key=f"instr_{clave_paso}", height=100)

            st.write("")
            usa_tiempo = st.checkbox("⏱️ Este paso tiene temporizador", value="tiempo_min" in paso_actual, key=f"chk_tiempo_{clave_paso}")
            usa_granos = st.checkbox("⚖️ Este paso requiere pesar algo (granos/lúpulo)", value="granos" in paso_actual, key=f"chk_granos_{clave_paso}")

            tiempo_min_val = None
            if usa_tiempo:
                tiempo_min_val = st.number_input(
                    "Minutos", min_value=1, step=1,
                    value=int(float(paso_actual.get("tiempo_min", 1))), key=f"tiempo_{clave_paso}"
                )
                usa_hitos = st.checkbox("🌿 Tiene alarmas/hitos durante la cuenta atrás (ej. adiciones de lúpulo)",
                                         value="hitos" in paso_actual, key=f"chk_hitos_{clave_paso}")
            else:
                usa_hitos = False
                if "hitos" in paso_actual:
                    st.caption("⚠️ Este paso tenía hitos, pero al desactivar el temporizador se eliminarán al guardar.")

            if usa_granos:
                st.write("#### 📦 Ingredientes a pesar")
                nuevas_filas = []
                for fila in st.session_state.filas_granos:
                    c1, c2, c3 = st.columns([3, 2, 1])
                    n = c1.text_input("Nombre", value=fila["nombre"], key=f"gn_{fila['id']}", label_visibility="collapsed", placeholder="Nombre")
                    c = c2.text_input("Cantidad", value=fila["cantidad"], key=f"gc_{fila['id']}", label_visibility="collapsed", placeholder="Cantidad (ej. 4.5 kg)")
                    borrar = c3.button("🗑️", key=f"gdel_{fila['id']}")
                    if not borrar:
                        nuevas_filas.append({"id": fila["id"], "nombre": n, "cantidad": c})
                st.session_state.filas_granos = nuevas_filas
                if st.button("+ Ingrediente", key=f"addg_{clave_paso}"):
                    st.session_state.filas_granos.append({"id": str(uuid.uuid4()), "nombre": "", "cantidad": ""})
                    st.rerun()

            if usa_hitos:
                st.write("#### 🔔 Alarmas (minutos restantes en los que debe saltar el aviso)")
                nuevas_filas_h = []
                for fila in st.session_state.filas_hitos:
                    c1, c2, c3 = st.columns([3, 2, 1])
                    n = c1.text_input("Nombre alarma", value=fila["nombre"], key=f"hn_{fila['id']}", label_visibility="collapsed", placeholder="Nombre de la alarma")
                    m = c2.text_input("Minuto", value=fila["minuto"], key=f"hm_{fila['id']}", label_visibility="collapsed", placeholder="Min. restantes")
                    borrar = c3.button("🗑️", key=f"hdel_{fila['id']}")
                    if not borrar:
                        nuevas_filas_h.append({"id": fila["id"], "nombre": n, "minuto": m})
                st.session_state.filas_hitos = nuevas_filas_h
                if st.button("+ Alarma", key=f"addh_{clave_paso}"):
                    st.session_state.filas_hitos.append({"id": str(uuid.uuid4()), "nombre": "", "minuto": ""})
                    st.rerun()

            st.divider()
            if st.button("💾 Guardar este paso", type="primary", use_container_width=True):
                nuevo_paso = {
                    "paso": nombre_paso,
                    "objetivo": objetivo,
                    "instruccion": instruccion,
                }
                if usa_tiempo:
                    nuevo_paso["tiempo_min"] = str(int(tiempo_min_val))
                if usa_granos:
                    nuevo_paso["granos"] = [
                        {"nombre": f["nombre"], "cantidad": f["cantidad"]}
                        for f in st.session_state.filas_granos if f["nombre"]
                    ]
                if usa_hitos:
                    nuevo_paso["hitos"] = [
                        {"nombre": f["nombre"], "minuto": f["minuto"]}
                        for f in st.session_state.filas_hitos if f["nombre"]
                    ]

                receta_data[idx] = nuevo_paso
                guardar_todo(st.session_state.db)
                st.success("✅ Paso guardado en GitHub." if ALMACEN_GITHUB else "✅ Paso guardado en disco (con backup automático).")

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
