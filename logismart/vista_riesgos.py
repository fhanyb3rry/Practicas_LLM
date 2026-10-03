import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk

import base_datos
import graficas
import riesgos


def mensaje_de(error, general):
    if isinstance(error, base_datos.ErrorBD):
        return str(error)
    return general


class VistaRiesgos:

    def __init__(self, padre, app):
        self.app = app
        self.colores = app.colores
        self.marco = ttk.Frame(padre, padding=15)

        self.lista = []
        self.docs = {}
        self.seleccionado = None

        self.marco.columnconfigure(0, weight=3, uniform="col")
        self.marco.columnconfigure(1, weight=2, uniform="col")
        self.marco.rowconfigure(0, weight=1)

        izquierda = ttk.Frame(self.marco)
        izquierda.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        derecha = ttk.Frame(self.marco)
        derecha.grid(row=0, column=1, sticky="nsew")

        self._armar_tabla(izquierda)
        self._armar_formulario(izquierda)
        self._armar_graficas(derecha)

    def _armar_tabla(self, padre):
        fila = ttk.Frame(padre)
        fila.pack(fill="x")
        ttk.Label(fila, text="⚖️ Matriz de riesgos éticos", font=("Segoe UI", 14, "bold")).pack(side="left")
        ttk.Button(fila, text="🔄", command=self.cargar, bootstyle="info-outline").pack(side="right")

        self.lbl_resumen = ttk.Label(padre, text="", bootstyle="secondary")
        self.lbl_resumen.pack(anchor="w", pady=(2, 6))

        zona = ttk.Frame(padre)
        zona.pack(fill="x")

        columnas = ("n", "modulo", "descripcion", "antes", "despues", "nivel")
        self.tabla = ttk.Treeview(zona, columns=columnas, show="headings", height=6, bootstyle="info",
                                  selectmode="browse")
        titulos = {"n": "#", "modulo": "Módulo", "descripcion": "Riesgo", "antes": "Antes",
                   "despues": "Después", "nivel": "Nivel"}
        anchos = {"n": 30, "modulo": 150, "descripcion": 210, "antes": 55, "despues": 65, "nivel": 65}
        for columna in columnas:
            self.tabla.heading(columna, text=titulos[columna])
            self.tabla.column(columna, width=anchos[columna], anchor="center" if columna != "descripcion" else "w")
        self.tabla.pack(side="left", fill="x", expand=True)
        self.tabla.bind("<<TreeviewSelect>>", self.seleccionar)

        for nombre in riesgos.NIVELES:
            self.tabla.tag_configure(nombre, foreground=riesgos.COLORES[nombre])

        barra = ttk.Scrollbar(zona, command=self.tabla.yview)
        barra.pack(side="right", fill="y")
        self.tabla.configure(yscrollcommand=barra.set)

    def _armar_formulario(self, padre):
        caja = ttk.Labelframe(padre, text=" Riesgo ", padding=10, bootstyle="info")
        caja.pack(fill="both", expand=True, pady=(10, 0))
        caja.columnconfigure(1, weight=1)

        ttk.Label(caja, text="Módulo:").grid(row=0, column=0, sticky="w", pady=3)
        self.modulo = ttk.Entry(caja)
        self.modulo.grid(row=0, column=1, sticky="ew", padx=(6, 12))
        ttk.Label(caja, text="Categoría:").grid(row=0, column=2, sticky="w")
        self.categoria = ttk.Combobox(caja, values=riesgos.CATEGORIAS, width=15, state="readonly")
        self.categoria.grid(row=0, column=3, sticky="w", padx=6)

        ttk.Label(caja, text="Descripción:").grid(row=1, column=0, sticky="w", pady=3)
        self.descripcion = ttk.Entry(caja)
        self.descripcion.grid(row=1, column=1, columnspan=3, sticky="ew", padx=6)

        antes = ttk.Frame(caja)
        antes.grid(row=2, column=0, columnspan=4, sticky="w", pady=(8, 2))
        ttk.Label(antes, text="Antes de mitigar:   Probabilidad").pack(side="left")
        self.prob = self._caja_numero(antes)
        ttk.Label(antes, text="Impacto").pack(side="left", padx=(8, 0))
        self.impacto = self._caja_numero(antes)

        despues = ttk.Frame(caja)
        despues.grid(row=3, column=0, columnspan=4, sticky="w", pady=2)
        ttk.Label(despues, text="Después de mitigar:   Probabilidad").pack(side="left")
        self.prob_res = self._caja_numero(despues)
        ttk.Label(despues, text="Impacto").pack(side="left", padx=(8, 0))
        self.impacto_res = self._caja_numero(despues)

        ttk.Label(caja, text="Mitigación:").grid(row=4, column=0, sticky="w", pady=3)
        self.mitigacion = ttk.Entry(caja)
        self.mitigacion.grid(row=4, column=1, columnspan=3, sticky="ew", padx=6)

        botones = ttk.Frame(caja)
        botones.grid(row=5, column=0, columnspan=4, sticky="w", pady=(10, 0))
        ttk.Button(botones, text="➕ Agregar", command=self.agregar, bootstyle="success").pack(side="left")
        self.btn_guardar = ttk.Button(botones, text="💾 Guardar cambios", command=self.guardar_cambios,
                                      bootstyle="primary", state="disabled")
        self.btn_guardar.pack(side="left", padx=8)
        self.btn_borrar = ttk.Button(botones, text="🗑️ Eliminar", command=self.eliminar,
                                     bootstyle="danger-outline", state="disabled")
        self.btn_borrar.pack(side="left")
        ttk.Button(botones, text="🧹", command=self.limpiar, bootstyle="secondary-outline").pack(side="left", padx=8)

        self.lbl_estado = ttk.Label(caja, text="Puntaje = probabilidad × impacto (1 a 5 cada uno).",
                                    bootstyle="secondary", wraplength=520, justify="left")
        self.lbl_estado.grid(row=6, column=0, columnspan=4, sticky="w", pady=(8, 0))

        self.limpiar()

    def _caja_numero(self, padre):
        caja = ttk.Spinbox(padre, from_=1, to=5, width=3)
        caja.pack(side="left", padx=4)
        return caja

    def _armar_graficas(self, padre):
        padre.rowconfigure(0, weight=3)
        padre.rowconfigure(1, weight=2)
        padre.columnconfigure(0, weight=1)

        self.lienzo_matriz = tk.Canvas(padre, width=420, height=330, bg=graficas.FONDO, highlightthickness=0)
        self.lienzo_matriz.grid(row=0, column=0, sticky="nsew")
        self.lienzo_barras = tk.Canvas(padre, width=420, height=250, bg=graficas.FONDO, highlightthickness=0)
        self.lienzo_barras.grid(row=1, column=0, sticky="nsew", pady=(10, 0))

        self.lienzo_matriz.bind("<Configure>", lambda evento: self.dibujar())
        self.lienzo_barras.bind("<Configure>", lambda evento: self.dibujar())

    def dibujar(self):
        graficas.dibujar_matriz(self.lienzo_matriz, self.lista)
        graficas.dibujar_barras(self.lienzo_barras, self.lista)

    def al_conectar(self):
        self.cargar()

    def cargar(self):
        if not self.app.hay_conexion():
            self.lbl_resumen.configure(text="Sin conexión con MongoDB")
            return

        def consultar():
            return self.app.db.listar("riesgos_eticos", {}, limite=200, campo_orden="puntaje")

        self.lbl_resumen.configure(text="Cargando...")
        self.app.en_segundo_plano(consultar, self.mostrar)

    def mostrar(self, docs, error):
        if error is not None:
            self.lbl_resumen.configure(text=mensaje_de(error, "No se pudieron cargar los riesgos."))
            return

        anterior = self.seleccionado
        self.lista = docs
        self.docs = {}
        for item in self.tabla.get_children():
            self.tabla.delete(item)

        for numero, doc in enumerate(docs, start=1):
            iid = str(doc["_id"])
            self.docs[iid] = doc
            self.tabla.insert("", "end", iid=iid, tags=(riesgos.nivel(doc["puntaje"]),), values=(
                numero, doc["modulo"], doc["descripcion"], doc["puntaje"], doc["puntaje_residual"],
                riesgos.nivel(doc["puntaje"])))

        r = riesgos.resumen(docs)
        self.lbl_resumen.configure(
            text=str(r["total"]) + " riesgos · promedio " + str(r["promedio_antes"]) + " → " +
                 str(r["promedio_despues"]) + " · críticos " + str(r["criticos_antes"]) + " → " +
                 str(r["criticos_despues"]))

        self.dibujar()
        if anterior in self.docs:
            self.tabla.selection_set(anterior)

    def seleccionar(self, evento):
        elegido = self.tabla.selection()
        if len(elegido) == 0:
            return

        self.seleccionado = elegido[0]
        doc = self.docs[self.seleccionado]

        self._poner(self.modulo, doc["modulo"])
        self._poner(self.descripcion, doc["descripcion"])
        self._poner(self.mitigacion, doc.get("mitigacion", ""))
        self.categoria.set(doc["categoria"])
        self._poner(self.prob, doc["probabilidad"])
        self._poner(self.impacto, doc["impacto"])
        self._poner(self.prob_res, doc["prob_residual"])
        self._poner(self.impacto_res, doc["impacto_residual"])

        cambios = len(doc.get("historico", []))
        self.lbl_estado.configure(text="Este riesgo se ha modificado " + str(cambios) + " veces.")
        self.btn_guardar.configure(state="normal")
        self.btn_borrar.configure(state="normal")

    def _poner(self, caja, valor):
        caja.delete(0, "end")
        caja.insert(0, str(valor))

    def leer_formulario(self):
        modulo = self.modulo.get().strip()
        descripcion = self.descripcion.get().strip()
        if modulo == "" or descripcion == "":
            messagebox.showwarning("Riesgo", "El módulo y la descripción son obligatorios.")
            return None
        if self.categoria.get() == "":
            messagebox.showwarning("Riesgo", "Elige una categoría.")
            return None

        try:
            datos = {
                "modulo": modulo,
                "descripcion": descripcion,
                "categoria": self.categoria.get(),
                "probabilidad": int(self.prob.get()),
                "impacto": int(self.impacto.get()),
                "mitigacion": self.mitigacion.get().strip(),
                "prob_residual": int(self.prob_res.get()),
                "impacto_residual": int(self.impacto_res.get()),
            }
        except ValueError:
            messagebox.showwarning("Riesgo", "La probabilidad y el impacto deben ser números del 1 al 5.")
            return None

        return datos

    def agregar(self):
        d = self.leer_formulario()
        if d is None:
            return

        def crear():
            return self.app.db.crear_riesgo(d["modulo"], d["descripcion"], d["categoria"], d["probabilidad"],
                                            d["impacto"], d["mitigacion"], d["prob_residual"], d["impacto_residual"])

        self.app.en_segundo_plano(crear, self.despues_de_cambio)

    def guardar_cambios(self):
        if self.seleccionado is None:
            return
        d = self.leer_formulario()
        if d is None:
            return
        id_riesgo = self.seleccionado

        def editar():
            return self.app.db.editar_riesgo(id_riesgo, d)

        self.app.en_segundo_plano(editar, self.despues_de_cambio)

    def eliminar(self):
        if self.seleccionado is None:
            return
        doc = self.docs[self.seleccionado]
        if not messagebox.askyesno("Eliminar", "¿Eliminar el riesgo '" + doc["descripcion"] + "'?"):
            return
        id_riesgo = self.seleccionado

        def borrar():
            return self.app.db.eliminar("riesgos_eticos", id_riesgo)

        self.seleccionado = None
        self.app.en_segundo_plano(borrar, self.despues_de_cambio)

    def despues_de_cambio(self, resultado, error):
        if error is not None:
            messagebox.showwarning("Riesgo", mensaje_de(error, "No se pudo guardar el cambio."))
            return

        self.limpiar()
        self.lbl_estado.configure(text="Listo ✅")
        self.cargar()

    def limpiar(self):
        self.seleccionado = None
        for caja in [self.modulo, self.descripcion, self.mitigacion]:
            caja.delete(0, "end")
        self.categoria.set("")
        for caja in [self.prob, self.impacto, self.prob_res, self.impacto_res]:
            self._poner(caja, 1)

        self.btn_guardar.configure(state="disabled")
        self.btn_borrar.configure(state="disabled")
        self.lbl_estado.configure(text="Puntaje = probabilidad × impacto (1 a 5 cada uno).")
        for item in self.tabla.selection():
            self.tabla.selection_remove(item)
