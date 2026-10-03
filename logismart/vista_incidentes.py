import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk

import base_datos
import clasificador
import configuracion
import correo as modulo_correo

CATEGORIAS = list(clasificador.CATEGORIAS) + ["otro"]
PRIORIDADES = clasificador.ORDEN_PRIORIDAD
ESTADOS = base_datos.ESTADOS_INCIDENTE

COLORES_PRIORIDAD = {"critica": "#ff3b5c", "alta": "#ff9f43", "media": "#ffd43b"}


def formato_fecha(fecha):
    fecha = base_datos.a_local(fecha)
    if fecha is None:
        return "sin fecha"
    return fecha.strftime("%d/%m %H:%M")


def mensaje_de(error, general):
    if isinstance(error, base_datos.ErrorBD):
        return str(error)
    return general


class VistaIncidentes:

    def __init__(self, padre, app):
        self.app = app
        self.colores = app.colores
        self.marco = ttk.Frame(padre, padding=15)

        self.docs = {}
        self.seleccionado = None
        self.resultado = None

        self.marco.columnconfigure(0, weight=3, uniform="col")
        self.marco.columnconfigure(1, weight=2, uniform="col")
        self.marco.rowconfigure(0, weight=1)

        izquierda = ttk.Frame(self.marco)
        izquierda.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        derecha = ttk.Frame(self.marco)
        derecha.grid(row=0, column=1, sticky="nsew")

        self._armar_lista(izquierda)
        self._armar_detalle(izquierda)
        self._armar_nuevo(derecha)

    def _armar_lista(self, padre):
        fila = ttk.Frame(padre)
        fila.pack(fill="x")
        ttk.Label(fila, text="📥 Bandeja", font=("Segoe UI", 14, "bold")).pack(side="left")

        self.btn_recargar = ttk.Button(fila, text="🔄", command=self.cargar_lista, bootstyle="info-outline")
        self.btn_recargar.pack(side="right")
        self.filtro_estado = ttk.Combobox(fila, values=["todos"] + ESTADOS, width=12, state="readonly")
        self.filtro_estado.set("todos")
        self.filtro_estado.pack(side="right", padx=8)
        self.filtro_estado.bind("<<ComboboxSelected>>", lambda evento: self.cargar_lista())
        ttk.Label(fila, text="Estado:").pack(side="right")

        zona = ttk.Frame(padre)
        zona.pack(fill="x", pady=(8, 0))

        columnas = ("fecha", "categoria", "prioridad", "estado", "asunto")
        self.tabla = ttk.Treeview(zona, columns=columnas, show="headings", height=5, bootstyle="info",
                                  selectmode="browse")
        self.tabla.heading("fecha", text="Fecha")
        self.tabla.heading("categoria", text="Categoría")
        self.tabla.heading("prioridad", text="Prioridad")
        self.tabla.heading("estado", text="Estado")
        self.tabla.heading("asunto", text="Asunto")
        self.tabla.column("fecha", width=90, anchor="center")
        self.tabla.column("categoria", width=150)
        self.tabla.column("prioridad", width=75, anchor="center")
        self.tabla.column("estado", width=90, anchor="center")
        self.tabla.column("asunto", width=230)
        self.tabla.pack(side="left", fill="x", expand=True)
        self.tabla.bind("<<TreeviewSelect>>", self.seleccionar)

        for nombre in COLORES_PRIORIDAD:
            self.tabla.tag_configure(nombre, foreground=COLORES_PRIORIDAD[nombre])

        barra = ttk.Scrollbar(zona, command=self.tabla.yview)
        barra.pack(side="right", fill="y")
        self.tabla.configure(yscrollcommand=barra.set)

        self.lbl_lista = ttk.Label(padre, text="", bootstyle="secondary")
        self.lbl_lista.pack(anchor="w", pady=(4, 0))

    def _armar_detalle(self, padre):
        caja = ttk.Labelframe(padre, text=" Detalle del incidente ", padding=10, bootstyle="info")
        caja.pack(fill="both", expand=True, pady=(8, 0))

        self.correo = tk.Text(caja, height=3, wrap="word", state="disabled", font=("Segoe UI", 10),
                              bg=self.colores.inputbg, fg=self.colores.inputfg, relief="flat", padx=8, pady=6)
        self.correo.pack(fill="x")

        fila = ttk.Frame(caja)
        fila.pack(fill="x", pady=(8, 0))
        ttk.Label(fila, text="Categoría:").pack(side="left")
        self.det_categoria = ttk.Combobox(fila, values=CATEGORIAS, width=22, state="readonly")
        self.det_categoria.pack(side="left", padx=(4, 12))
        ttk.Label(fila, text="Prioridad:").pack(side="left")
        self.det_prioridad = ttk.Combobox(fila, values=PRIORIDADES, width=8, state="readonly")
        self.det_prioridad.pack(side="left", padx=(4, 12))
        self.btn_clasif = ttk.Button(fila, text="💾 Guardar", command=self.guardar_clasificacion,
                                     bootstyle="primary", state="disabled")
        self.btn_clasif.pack(side="left")
        self.btn_borrar = ttk.Button(fila, text="🗑️", command=self.eliminar, bootstyle="danger-outline",
                                     state="disabled")
        self.btn_borrar.pack(side="left", padx=(8, 0))

        fila = ttk.Frame(caja)
        fila.pack(fill="x", pady=(8, 0))
        ttk.Label(fila, text="Estado:").pack(side="left")
        self.det_estado = ttk.Combobox(fila, values=ESTADOS, width=12, state="readonly")
        self.det_estado.pack(side="left", padx=(4, 8))
        self.det_nota = ttk.Entry(fila)
        self.det_nota.pack(side="left", fill="x", expand=True)
        self.btn_estado = ttk.Button(fila, text="Cambiar estado", command=self.cambiar_estado,
                                     bootstyle="success", state="disabled")
        self.btn_estado.pack(side="left", padx=(8, 0))
        ttk.Label(caja, text="La nota es opcional", bootstyle="secondary").pack(anchor="e")

        ttk.Label(caja, text="Historial", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(4, 2))
        self.historial = tk.Text(caja, height=3, wrap="word", state="disabled", font=("Consolas", 9),
                                 bg=self.colores.inputbg, fg=self.colores.inputfg, relief="flat", padx=8, pady=6)
        self.historial.pack(fill="both", expand=True)

        self.lbl_detalle = ttk.Label(caja, text="Elige un incidente de la bandeja.", bootstyle="secondary")
        self.lbl_detalle.pack(anchor="w", pady=(4, 0))

    def _armar_nuevo(self, padre):
        ttk.Label(padre, text="✉️ Nuevo correo", font=("Segoe UI", 14, "bold")).pack(anchor="w")

        ttk.Label(padre, text="De:").pack(anchor="w", pady=(6, 0))
        self.remitente = ttk.Entry(padre)
        self.remitente.pack(fill="x")

        ttk.Label(padre, text="Asunto:").pack(anchor="w", pady=(6, 0))
        self.asunto = ttk.Entry(padre)
        self.asunto.pack(fill="x")

        ttk.Label(padre, text="Mensaje:").pack(anchor="w", pady=(6, 0))
        self.cuerpo = tk.Text(padre, height=3, wrap="word", font=("Segoe UI", 10),
                              bg=self.colores.inputbg, fg=self.colores.inputfg, relief="flat", padx=8, pady=6)
        self.cuerpo.pack(fill="x")

        self.var_llm = tk.BooleanVar(value=True)

        fila = ttk.Frame(padre)
        fila.pack(fill="x", pady=(8, 0))
        self.btn_clasificar = ttk.Button(fila, text="🔍 Clasificar", command=self.clasificar, bootstyle="primary")
        self.btn_clasificar.pack(side="left")
        ttk.Button(fila, text="🧹", command=self.limpiar_nuevo, bootstyle="secondary-outline").pack(side="left", padx=8)
        ttk.Checkbutton(fila, text="Usar el LLM (~20 s)", variable=self.var_llm,
                        bootstyle="round-toggle").pack(side="left", padx=8)

        self.carga = ttk.Progressbar(padre, mode="indeterminate", bootstyle="info-striped")

        self.caja_resultado = ttk.Labelframe(padre, text=" Resultado ", padding=10, bootstyle="success")
        self.caja_resultado.pack(fill="x", pady=(10, 0))

        fila = ttk.Frame(self.caja_resultado)
        fila.pack(fill="x")
        ttk.Label(fila, text="Categoría:").pack(side="left")
        self.res_categoria = ttk.Combobox(fila, values=CATEGORIAS, width=22, state="readonly")
        self.res_categoria.pack(side="left", padx=(4, 10))
        ttk.Label(fila, text="Prioridad:").pack(side="left")
        self.res_prioridad = ttk.Combobox(fila, values=PRIORIDADES, width=8, state="readonly")
        self.res_prioridad.pack(side="left", padx=4)

        ttk.Label(self.caja_resultado, text="Resumen:").pack(anchor="w", pady=(8, 0))
        self.res_resumen = ttk.Entry(self.caja_resultado)
        self.res_resumen.pack(fill="x")

        self.lbl_info = ttk.Label(self.caja_resultado, text="Aquí sale la clasificación.", wraplength=420,
                                  justify="left", bootstyle="secondary")
        self.lbl_info.pack(anchor="w", pady=8)

        self.btn_guardar = ttk.Button(self.caja_resultado, text="💾 Guardar incidente", command=self.guardar_incidente,
                                      bootstyle="success", state="disabled")
        self.btn_guardar.pack(anchor="w")

    def al_conectar(self):
        self.cargar_lista()

    def cargar_lista(self):
        if not self.app.hay_conexion():
            self.lbl_lista.configure(text="Sin conexión con MongoDB")
            return

        filtro = {}
        if self.filtro_estado.get() != "todos":
            filtro = {"estado": self.filtro_estado.get()}

        def consultar():
            return self.app.db.listar("incidentes", filtro, limite=100)

        self.lbl_lista.configure(text="Cargando...")
        self.app.en_segundo_plano(consultar, self.mostrar_lista)

    def mostrar_lista(self, docs, error):
        if error is not None:
            self.lbl_lista.configure(text=mensaje_de(error, "No se pudo cargar la bandeja."))
            return

        anterior = self.seleccionado
        self.docs = {}
        for item in self.tabla.get_children():
            self.tabla.delete(item)

        for doc in docs:
            iid = str(doc["_id"])
            self.docs[iid] = doc
            clasif = doc.get("clasificacion", {})
            asunto = doc.get("correo_original", {}).get("asunto", "")
            prioridad = clasif.get("prioridad", "")
            self.tabla.insert("", "end", iid=iid, tags=(prioridad,), values=(
                formato_fecha(doc.get("creado")), clasif.get("categoria", ""), prioridad,
                doc.get("estado", ""), asunto))

        self.lbl_lista.configure(text=str(len(docs)) + " incidentes")
        if anterior in self.docs:
            self.tabla.selection_set(anterior)

    def seleccionar(self, evento):
        elegido = self.tabla.selection()
        if len(elegido) == 0:
            return

        self.seleccionado = elegido[0]
        doc = self.docs[self.seleccionado]
        correo = doc.get("correo_original", {})
        clasif = doc.get("clasificacion", {})

        texto = "De: " + str(correo.get("remitente")) + "\nAsunto: " + str(correo.get("asunto"))
        texto += "\n\n" + str(correo.get("cuerpo"))
        self._escribir(self.correo, texto)

        self.det_categoria.set(clasif.get("categoria", ""))
        self.det_prioridad.set(clasif.get("prioridad", ""))
        self.det_estado.set(doc.get("estado", ""))
        self.det_nota.delete(0, "end")

        lineas = []
        for evento_hist in doc.get("historial", []):
            estado = evento_hist.get("estado") or "edición"
            lineas.append(formato_fecha(evento_hist.get("fecha")) + " · " + str(evento_hist.get("usuario")) +
                          " · " + estado + ": " + str(evento_hist.get("nota")))
        self._escribir(self.historial, "\n".join(lineas))

        self.btn_clasif.configure(state="normal")
        self.btn_estado.configure(state="normal")
        self.btn_borrar.configure(state="normal")

        detalle = ""
        if clasif.get("requiere_revision_humana"):
            detalle = "⚠️ Marcado para revisión humana. "
        if clasif.get("editado_a_mano"):
            detalle += "Clasificación editada a mano."
        self.lbl_detalle.configure(text=detalle)

    def _escribir(self, caja, texto):
        caja.configure(state="normal")
        caja.delete("1.0", "end")
        caja.insert("1.0", texto)
        caja.configure(state="disabled")

    def guardar_clasificacion(self):
        if self.seleccionado is None:
            return

        doc = self.docs[self.seleccionado]
        clasif = dict(doc.get("clasificacion", {}))
        clasif["categoria"] = self.det_categoria.get()
        clasif["prioridad"] = self.det_prioridad.get()
        clasif["editado_a_mano"] = True
        id_incidente = self.seleccionado

        def guardar():
            return self.app.db.editar_clasificacion(id_incidente, clasif, self.app.operador)

        self.btn_clasif.configure(state="disabled")
        self.app.en_segundo_plano(guardar, self.despues_de_editar)

    def cambiar_estado(self):
        if self.seleccionado is None:
            return

        estado = self.det_estado.get()
        nota = self.det_nota.get().strip()
        id_incidente = self.seleccionado

        def cambiar():
            return self.app.db.cambiar_estado_incidente(id_incidente, estado, nota, self.app.operador)

        self.btn_estado.configure(state="disabled")
        self.app.en_segundo_plano(cambiar, self.despues_de_editar)

    def despues_de_editar(self, resultado, error):
        if error is not None:
            messagebox.showwarning("Incidentes", mensaje_de(error, "No se pudo guardar el cambio."))
            self.btn_clasif.configure(state="normal")
            self.btn_estado.configure(state="normal")
            return

        self.lbl_detalle.configure(text="Cambio guardado ✅")
        self.cargar_lista()
        self.btn_clasif.configure(state="normal")
        self.btn_estado.configure(state="normal")

    def eliminar(self):
        if self.seleccionado is None:
            return

        asunto = self.docs[self.seleccionado].get("correo_original", {}).get("asunto", "")
        if not messagebox.askyesno("Eliminar", "¿Eliminar el incidente '" + asunto + "'?"):
            return
        id_incidente = self.seleccionado

        def borrar():
            return self.app.db.eliminar("incidentes", id_incidente)

        self.seleccionado = None
        self.btn_borrar.configure(state="disabled")
        self.app.en_segundo_plano(borrar, self.despues_de_borrar)

    def despues_de_borrar(self, resultado, error):
        if error is not None:
            messagebox.showwarning("Incidentes", mensaje_de(error, "No se pudo eliminar el incidente."))
            return

        self._escribir(self.correo, "")
        self._escribir(self.historial, "")
        self.lbl_detalle.configure(text="Incidente eliminado ✅")
        self.btn_clasif.configure(state="disabled")
        self.btn_estado.configure(state="disabled")
        self.cargar_lista()

    def clasificar(self):
        asunto = self.asunto.get().strip()
        cuerpo = self.cuerpo.get("1.0", "end").strip()
        if asunto == "" and cuerpo == "":
            messagebox.showwarning("Correo", "Escribe el asunto o el mensaje del correo.")
            return

        usar_llm = self.var_llm.get()

        def trabajo():
            if usar_llm:
                return clasificador.clasificar_hibrido(asunto, cuerpo)
            return clasificador.clasificar_solo_reglas(asunto, cuerpo)

        self.btn_clasificar.configure(state="disabled")
        self.btn_guardar.configure(state="disabled")
        self.carga.pack(fill="x", pady=(8, 0), before=self.caja_resultado)
        self.carga.start(12)
        self.lbl_info.configure(text="Clasificando...", bootstyle="secondary")
        self.app.en_segundo_plano(trabajo, self.mostrar_resultado)

    def mostrar_resultado(self, resultado, error):
        self.carga.stop()
        self.carga.pack_forget()
        self.btn_clasificar.configure(state="normal")

        if error is not None:
            self.lbl_info.configure(text="No se pudo clasificar el correo.", bootstyle="danger")
            return

        self.resultado = resultado
        self.res_categoria.set(resultado["categoria"])
        self.res_prioridad.set(resultado["prioridad"])
        self.res_resumen.delete(0, "end")
        self.res_resumen.insert(0, resultado["resumen"])

        texto = "Método: " + resultado["metodo"] + "."
        llm = resultado["llm"]
        if llm is not None and not llm["ok"]:
            texto += " El LLM no respondió bien (" + llm["error"] + "), se usaron las reglas."
        if resultado["coincidio_con_reglas"] is False:
            texto += " El LLM y las reglas no coinciden, se quedó la prioridad más alta."
        if resultado["requiere_revision_humana"]:
            texto += " ⚠️ Requiere revisión humana."

        datos = []
        for campo in resultado["entidades"]:
            if resultado["entidades"][campo] is not None:
                datos.append(campo + ": " + str(resultado["entidades"][campo]))
        if len(datos) > 0:
            texto += "\nDatos encontrados: " + ", ".join(datos)

        self.lbl_info.configure(text=texto, bootstyle="warning" if resultado["requiere_revision_humana"] else "success")
        self.btn_guardar.configure(state="normal")

    def guardar_incidente(self):
        if self.resultado is None:
            return
        if not self.app.hay_conexion():
            messagebox.showwarning("Sin conexión", "No hay conexión con MongoDB, no se pudo guardar.")
            return

        resultado = self.resultado
        categoria = self.res_categoria.get()
        prioridad = self.res_prioridad.get()

        clasif = {
            "categoria": categoria,
            "prioridad": prioridad,
            "metodo": resultado["metodo"],
            "requiere_revision_humana": resultado["requiere_revision_humana"],
            "resumen": self.res_resumen.get().strip(),
            "palabras_clave": resultado["palabras_clave"],
        }
        if categoria != resultado["categoria"] or prioridad != resultado["prioridad"]:
            clasif["editado_a_mano"] = True

        remitente = self.remitente.get().strip()
        if remitente == "":
            remitente = "sin remitente"
        correo = {"remitente": remitente, "asunto": self.asunto.get().strip(),
                  "cuerpo": self.cuerpo.get("1.0", "end").strip()}

        def guardar():
            id_nuevo = self.app.db.crear_incidente(correo, clasif, resultado["entidades"], self.app.operador)
            llm = resultado["llm"]
            if llm is not None and llm["ok"]:
                self.app.db.registrar_evaluacion_llm(llm["prompt"], llm["respuesta"], llm["modelo"],
                                                     llm["latencia_ms"], resultado["coincidio_con_reglas"])

            asunto_soporte, cuerpo_soporte = modulo_correo.armar_correo(correo, clasif, resultado["entidades"])
            destino = configuracion.valores["correo_soporte"]
            envio = modulo_correo.enviar(remitente, destino, asunto_soporte, cuerpo_soporte,
                                         configuracion.valores["simulacion_correo"])
            if envio["enviado"] and envio["modo"] == "simulacion":
                nota = "Correo a soporte simulado (" + destino + ")"
            elif envio["enviado"]:
                nota = "Correo enviado a soporte (" + destino + ")"
            else:
                nota = "No se pudo mandar el correo a soporte: " + envio["error"]
            self.app.db.agregar_evento_incidente(id_nuevo, nota, self.app.operador)
            return nota

        self.btn_guardar.configure(state="disabled")
        self.app.en_segundo_plano(guardar, self.despues_de_guardar)

    def despues_de_guardar(self, resultado, error):
        if error is not None:
            self.btn_guardar.configure(state="normal")
            messagebox.showwarning("Incidentes", mensaje_de(error, "No se pudo guardar el incidente."))
            return

        self.limpiar_nuevo()
        self.lbl_info.configure(text="Incidente guardado ✅  " + resultado, bootstyle="success")
        self.cargar_lista()

    def limpiar_nuevo(self):
        self.resultado = None
        self.remitente.delete(0, "end")
        self.asunto.delete(0, "end")
        self.cuerpo.delete("1.0", "end")
        self.res_categoria.set("")
        self.res_prioridad.set("")
        self.res_resumen.delete(0, "end")
        self.lbl_info.configure(text="Aquí sale la clasificación.", bootstyle="secondary")
        self.btn_guardar.configure(state="disabled")
