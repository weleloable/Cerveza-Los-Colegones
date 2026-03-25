import tkinter as tk
import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
import json
import os
import copy
import shutil
from datetime import datetime

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class EditorColegones(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Maestro Cervecero Pro - Editor de Recetas")
        self.geometry("1300x900")

        # Variables de estado
        self.ruta_archivo = None
        self.recetas = {}
        self.receta_actual = None
        self.paso_indice = 0
        self.filas_mmpp = []
        self.filas_hitos = []

        # --- LAYOUT ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # BARRA LATERAL
        self.sidebar = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkButton(self.sidebar, text="📁 Cargar JSON", command=self.seleccionar_archivo).pack(pady=(20, 5), padx=20)
        self.lbl_nombre_archivo = ctk.CTkLabel(self.sidebar, text="Sin archivo", font=("Arial", 11), text_color="gray")
        self.lbl_nombre_archivo.pack()

        ctk.CTkLabel(self.sidebar, text="Recetas:", font=("Arial", 14, "bold")).pack(pady=(20, 0))
        self.option_receta = ctk.CTkOptionMenu(self.sidebar, values=["..."], command=self.cambiar_receta)
        self.option_receta.pack(pady=10, padx=20)

        # Botones de gestión de recetas
        f_btns = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        f_btns.pack(fill="x", padx=20)
        ctk.CTkButton(f_btns, text="➕Nueva", width=40, command=self.nueva_receta).pack(side="left", padx=2)
        ctk.CTkButton(f_btns, text="👯Duplicar", width=40, command=self.duplicar_receta).pack(side="left", padx=2)
        ctk.CTkButton(f_btns, text="🗑️Borrar", width=40, fg_color="#922b21", command=self.borrar_receta).pack(side="left", padx=2)

        self.scroll_pasos = ctk.CTkScrollableFrame(self.sidebar, label_text="Pasos")
        self.scroll_pasos.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkButton(self.sidebar, text="➕ Añadir Paso", command=self.añadir_paso).pack(pady=10)

        # PANEL CENTRAL
        self.main_frame = ctk.CTkScrollableFrame(self)
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        self.crear_interfaz_edicion()

        # BOTONES DE GUARDADO (ABAJO)
        self.f_footer = ctk.CTkFrame(self, height=80)
        self.f_footer.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=10)
        
        

        self.btn_guardar_disco = ctk.CTkButton(self.f_footer, text="💾 GUARDAR TODO EN DISCO (JSON + Backup)", 
                                              fg_color="#28a745", height=45, font=("Arial", 13, "bold"),
                                              command=self.guardar_json)
        self.btn_guardar_disco.pack(side="left", padx=20, expand=True, fill="x")

    def crear_interfaz_edicion(self):
        # Campos básicos
        f = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        f.pack(pady=10, padx=20, fill="x")
        f.columnconfigure(1, weight=1)

        ctk.CTkLabel(f, text="Nombre Paso:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
        self.ent_paso_nombre = ctk.CTkEntry(f, height=35); self.ent_paso_nombre.grid(row=0, column=1, sticky="ew")

        ctk.CTkLabel(f, text="Objetivo:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.ent_objetivo = ctk.CTkEntry(f, height=35); self.ent_objetivo.grid(row=1, column=1, sticky="ew")

        ctk.CTkLabel(f, text="Instrucción:").grid(row=2, column=0, padx=10, pady=5, sticky="ne")
        self.txt_instruccion = ctk.CTkTextbox(f, height=100); self.txt_instruccion.grid(row=2, column=1, sticky="ew")

        # Selectores de sección
        self.f_chks = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.f_chks.pack(pady=10)
        self.check_tiempo = ctk.CTkCheckBox(self.f_chks, text="Tiempo", command=self.toggle_campos)
        self.check_tiempo.pack(side="left", padx=10)
        self.check_mmpp = ctk.CTkCheckBox(self.f_chks, text="Materias Primas", command=self.toggle_campos)
        self.check_mmpp.pack(side="left", padx=10)
        self.check_hitos = ctk.CTkCheckBox(self.f_chks, text="Hitos/Alarmas", command=self.toggle_campos)
        self.check_hitos.pack(side="left", padx=10)

        # Secciones dinámicas
        self.frame_tiempo = ctk.CTkFrame(self.main_frame)
        ctk.CTkLabel(self.frame_tiempo, text="Minutos:").pack(side="left", padx=10)
        self.ent_tiempo = ctk.CTkEntry(self.frame_tiempo, width=80); self.ent_tiempo.pack(side="left", padx=10, pady=10)

        self.frame_mmpp = ctk.CTkFrame(self.main_frame)
        ctk.CTkLabel(self.frame_mmpp, text="📦 Materias Primas", font=("", 12, "bold")).pack(pady=5)
        self.cont_mmpp = ctk.CTkFrame(self.frame_mmpp, fg_color="transparent"); self.cont_mmpp.pack(fill="x", padx=10)
        ctk.CTkButton(self.frame_mmpp, text="+ Ingrediente", command=lambda: self.añadir_fila_mmpp("", "")).pack(pady=5)

        self.frame_hitos = ctk.CTkFrame(self.main_frame)
        ctk.CTkLabel(self.frame_hitos, text="🔔 Alarmas", font=("", 12, "bold")).pack(pady=5)
        self.cont_hitos = ctk.CTkFrame(self.frame_hitos, fg_color="transparent"); self.cont_hitos.pack(fill="x", padx=10)
        ctk.CTkButton(self.frame_hitos, text="+ Alarma", command=lambda: self.añadir_fila_hitos("", "")).pack(pady=5)

        # Espaciador elástico para empujar los botones al final del scroll
        # Esto ayuda a que, si hay poco contenido, los botones se sientan "abajo"
        self.espaciador = ctk.CTkLabel(self.main_frame, text="")
        self.espaciador.pack(pady=20)

        # --- CONTENEDOR DE BOTONES DE ACCIÓN DEL PASO ---
        # Usamos un frame que ocupe todo el ancho disponible
        self.f_botones_paso = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.f_botones_paso.pack(side="bottom", fill="x", padx=20, pady=(10, 20))

        # BOTÓN GUARDAR (A la izquierda)
        # No ponemos width fijo ni expand=True para que se ciña al texto
        self.btn_confirmar_paso = ctk.CTkButton(self.f_botones_paso, 
                                               text="✅ Guardar cambios en este paso", 
                                               fg_color="#2e86c1", 
                                               hover_color="#21618c",
                                               height=35, 
                                               font=("Arial", 12, "bold"),
                                               command=self.salvar_paso_actual_en_memoria)
        self.btn_confirmar_paso.pack(side="left", padx=0)

        # BOTÓN ELIMINAR (A la derecha)
        self.btn_borrar_paso = ctk.CTkButton(self.f_botones_paso, 
                                            text="🗑️ Eliminar Paso", 
                                            fg_color="#922b21", 
                                            hover_color="#7b241c",
                                            height=35,
                                            font=("Arial", 12),
                                            command=self.borrar_paso)
        self.btn_borrar_paso.pack(side="right", padx=0)
        
    # --- LÓGICA DE FILAS ---
    def añadir_fila_mmpp(self, n, c):
        f = ctk.CTkFrame(self.cont_mmpp, fg_color="transparent"); f.pack(fill="x", pady=2)
        en = ctk.CTkEntry(f, placeholder_text="Nombre", width=200); en.insert(0, n); en.pack(side="left", padx=2)
        ec = ctk.CTkEntry(f, placeholder_text="Cant", width=100); ec.insert(0, c); ec.pack(side="left", padx=2)
        ctk.CTkButton(f, text="x", width=25, fg_color="#7b241c", command=lambda: self.eliminar_fila(f, "mmpp")).pack(side="left")
        self.filas_mmpp.append({"frame": f, "nombre": en, "cantidad": ec})
        self.after(10, lambda: self._focus_fix(en, ec))

    def añadir_fila_hitos(self, n, t):
        f = ctk.CTkFrame(self.cont_hitos, fg_color="transparent"); f.pack(fill="x", pady=2)
        en = ctk.CTkEntry(f, placeholder_text="Alarma", width=200); en.insert(0, n); en.pack(side="left", padx=2)
        et = ctk.CTkEntry(f, placeholder_text="Min", width=100); et.insert(0, t); et.pack(side="left", padx=2)
        ctk.CTkButton(f, text="x", width=25, fg_color="#7b241c", command=lambda: self.eliminar_fila(f, "hitos")).pack(side="left")
        self.filas_hitos.append({"frame": f, "nombre": en, "minuto": et})
        self.after(10, lambda: self._focus_fix(en, et))

    def _focus_fix(self, e1, e2): e1.focus_set(); e2.focus_set(); self.focus_set()

    def eliminar_fila(self, frame, tipo):
        if tipo == "mmpp": self.filas_mmpp = [x for x in self.filas_mmpp if x["frame"] != frame]
        else: self.filas_hitos = [x for x in self.filas_hitos if x["frame"] != frame]
        frame.destroy()

    # --- NÚCLEO DE LA APLICACIÓN ---
    def seleccionar_archivo(self):
        r = filedialog.askopenfilename(filetypes=(("JSON", "*.json"),))
        if r:
            self.ruta_archivo = r
            with open(r, "r", encoding="utf-8") as f: self.recetas = json.load(f)
            self.lbl_nombre_archivo.configure(text=os.path.basename(r), text_color="green")
            nombres = list(self.recetas.keys())
            self.option_receta.configure(values=nombres)
            self.cambiar_receta(nombres[0])

    def cambiar_receta(self, nombre):
        self.receta_actual = nombre
        self.option_receta.set(nombre)
        self.paso_indice = 0
        self.actualizar_lista_pasos()
        self.cargar_paso_en_pantalla(0)

    def cargar_paso_en_pantalla(self, index):
        if not self.receta_actual: return
        self.paso_indice = index
        paso = self.recetas[self.receta_actual][index]

        # LIMPIEZA TOTAL
        self.ent_paso_nombre.delete(0, tk.END)
        self.ent_objetivo.delete(0, tk.END)
        self.txt_instruccion.delete("1.0", tk.END)
        self.ent_tiempo.delete(0, tk.END)
        self.check_tiempo.deselect(); self.check_mmpp.deselect(); self.check_hitos.deselect()
        for f in self.filas_mmpp: f["frame"].destroy()
        for f in self.filas_hitos: f["frame"].destroy()
        self.filas_mmpp = []; self.filas_hitos = []

        # CARGA
        self.ent_paso_nombre.insert(0, paso.get('paso', ''))
        self.ent_objetivo.insert(0, paso.get('objetivo', ''))
        self.txt_instruccion.insert("1.0", paso.get('instruccion', ''))
        
        if 'tiempo_min' in paso:
            self.check_tiempo.select(); self.ent_tiempo.insert(0, paso['tiempo_min'])
        if 'granos' in paso:
            self.check_mmpp.select()
            for g in paso['granos']: self.añadir_fila_mmpp(g.get('nombre',''), g.get('cantidad',''))
        if 'hitos' in paso:
            self.check_hitos.select()
            for h in paso['hitos']: self.añadir_fila_hitos(h.get('nombre',''), h.get('minuto',''))
        
        self.toggle_campos()

    def salvar_paso_actual_en_memoria(self):
        if not self.receta_actual: return
        
        # Construimos el objeto del paso desde cero con lo que hay en pantalla
        nuevo_paso = {
            "paso": self.ent_paso_nombre.get(),
            "objetivo": self.ent_objetivo.get(),
            "instruccion": self.txt_instruccion.get("1.0", tk.END).strip()
        }

        if self.check_tiempo.get(): nuevo_paso["tiempo_min"] = self.ent_tiempo.get()
        if self.check_mmpp.get():
            nuevo_paso["granos"] = [{"nombre": f["nombre"].get(), "cantidad": f["cantidad"].get()} 
                                   for f in self.filas_mmpp if f["nombre"].get()]
        if self.check_hitos.get():
            nuevo_paso["hitos"] = [{"nombre": f["nombre"].get(), "minuto": f["minuto"].get()} 
                                  for f in self.filas_hitos if f["nombre"].get()]

        # Reemplazamos en el diccionario global
        self.recetas[self.receta_actual][self.paso_indice] = nuevo_paso
        self.actualizar_lista_pasos()
        messagebox.showinfo("Listo", "Paso actualizado en memoria temporal.")

    def guardar_json(self):
        if not self.ruta_archivo: return
        try:
            # Backup
            base = os.path.splitext(self.ruta_archivo)[0]
            tag = datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.copy2(self.ruta_archivo, f"{base}_{tag}.json")
            # Guardar
            with open(self.ruta_archivo, "w", encoding="utf-8") as f:
                json.dump(self.recetas, f, indent=4, ensure_ascii=False)
            messagebox.showinfo("Éxito", "Archivo guardado y Backup creado.")
        except Exception as e: messagebox.showerror("Error", str(e))

    # --- SOPORTE ---
    def toggle_campos(self):
        if self.check_tiempo.get(): self.frame_tiempo.pack(pady=5, fill="x", padx=40)
        else: self.frame_tiempo.pack_forget()
        if self.check_mmpp.get(): self.frame_mmpp.pack(pady=5, fill="x", padx=40)
        else: self.frame_mmpp.pack_forget()
        if self.check_hitos.get(): self.frame_hitos.pack(pady=5, fill="x", padx=40)
        else: self.frame_hitos.pack_forget()

    def nueva_receta(self):
        n = simpledialog.askstring("Nueva", "Nombre cerveza:")
        if n:
            self.recetas[n] = [{"paso": "Inicio", "objetivo": "-", "instruccion": "..."}]
            self.option_receta.configure(values=list(self.recetas.keys()))
            self.cambiar_receta(n)

    def duplicar_receta(self):
        if self.receta_actual:
            n = simpledialog.askstring("Duplicar", "Nuevo nombre:")
            if n:
                self.recetas[n] = copy.deepcopy(self.recetas[self.receta_actual])
                self.option_receta.configure(values=list(self.recetas.keys()))
                self.cambiar_receta(n)

    def borrar_receta(self):
        if self.receta_actual and messagebox.askyesno("Borrar", f"¿Borrar {self.receta_actual}?"):
            del self.recetas[self.receta_actual]
            n = list(self.recetas.keys())
            self.option_receta.configure(values=n if n else ["..."])
            self.cambiar_receta(n[0] if n else None)

    def añadir_paso(self):
        if self.receta_actual:
            self.recetas[self.receta_actual].append({"paso": "Nuevo", "objetivo": "-", "instruccion": ""})
            self.actualizar_lista_pasos()
            self.cargar_paso_en_pantalla(len(self.recetas[self.receta_actual])-1)

    def borrar_paso(self):
        if self.receta_actual and len(self.recetas[self.receta_actual]) > 1:
            self.recetas[self.receta_actual].pop(self.paso_indice)
            self.actualizar_lista_pasos(); self.cargar_paso_en_pantalla(0)

    def actualizar_lista_pasos(self):
        for c in self.scroll_pasos.winfo_children(): c.destroy()
        if self.receta_actual in self.recetas:
            for i, p in enumerate(self.recetas[self.receta_actual]):
                btn = ctk.CTkButton(self.scroll_pasos, text=f"{i+1}. {p['paso']}", anchor="w",
                                   command=lambda idx=i: self.cargar_paso_en_pantalla(idx))
                btn.pack(pady=2, fill="x", padx=5)

if __name__ == "__main__":
    app = EditorColegones()
    app.mainloop()