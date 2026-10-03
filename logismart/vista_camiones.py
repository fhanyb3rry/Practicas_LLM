import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import messagebox

import ttkbootstrap as ttk

import base_datos
import reglas


def mensaje_de(error, general):
    if isinstance(error, base_datos.ErrorBD):
        return str(error)
    return general


def formato_fecha(fecha):
    fecha = base_datos.a_local(fecha)
    if fecha is None:
        return "sin fecha"
    return fecha.strftime("%d/%m/%Y %H:%M")


class PaginaCamiones:

    def __init__(self, padre, app):
        self.app = app
        self.marco = ttk.Frame(padre, padding=12)
        self.docs = {}
        self.seleccionado = None

        fila = ttk.Frame(self.marco)
        fila.pack(fill="x")
        ttk.Label(fila, text="Camiones registrados", font=("Segoe UI", 13, "bold")).pack(side="left")
        ttk.Button(fila, text="🔄", command=self.cargar, bootstyle="info-outline").pack(side="right")
        self.lbl_lista = ttk.Label(self.marco, text="", bootstyle="secondary")
        self.lbl_lista.pack(anchor="w")

        zona = ttk.Frame(self.marco)
        zona.pack(fill="x", pady=(4, 0))
        columnas = ("camion_id", "placa", "empresa", "autorizado", "conductor", "certificacion")
        self.tabla = ttk.Treeview(zona, columns=columnas, show="headings", height=7, bootstyle="info",
                                  selectmode="browse")
        titulos = {"camion_id": "ID", "placa": "Placa", "empresa": "Empresa", "autorizado": "Autorizado",
                   "conductor": "Conductor", "certificacion": "Certificación"}
        anchos = {"camion_id": 80, "placa": 100, "empresa": 160, "autorizado": 80, "conductor": 140,
                  "certificacion": 190}
        for columna in columnas:
            self.tabla.heading(columna, text=titulos[columna])
            self.tabla.column(columna, width=anchos[columna], anchor="center")
        self.tabla.pack(side="left", fill="x", expand=True)
        self.tabla.bind("<<TreeviewSelect>>", self.seleccionar)
        self.tabla.tag_configure("vencida", foreground="#ff3b5c")
        self.tabla.tag_configure("por_vencer", foreground="#ffd43b")

        barra = ttk.Scrollbar(zona, command=self.tabla.yview)
        barra.pack(side="right", fill="y")
        self.tabla.configure(yscrollcommand=barra.set)

        caja = ttk.Labelframe(self.marco, text=" Camión ", padding=10, bootstyle="info")
        caja.pack(fill="x", pady=(10, 0))
        caja.columnconfigure(1, weight=1)
        caja.columnconfigure(3, weight=1)

        ttk.Label(caja, text="Placa:").grid(row=0, column=0, sticky="w", pady=3)
        self.placa = ttk.Entry(caja)
        self.placa.grid(row=0, column=1, sticky="ew", padx=(6, 14))
        ttk.Label(caja, text="ID del camión:").grid(row=0, column=2, sticky="w")
        self.camion_id = ttk.Entry(caja)
        self.camion_id.grid(row=0, column=3, sticky="ew", padx=6)

        ttk.Label(caja, text="Empresa:").grid(row=1, column=0, sticky="w", pady=3)
        self.empresa = ttk.Entry(caja)
        self.empresa.grid(row=1, column=1, sticky="ew", padx=(6, 14))
        ttk.Label(caja, text="Conductor:").grid(row=1, column=2, sticky="w")
        self.conductor = ttk.Entry(caja)
        self.conductor.grid(row=1, column=3, sticky="ew", padx=6)

        ttk.Label(caja, text="Certificación vence:").grid(row=2, column=0, sticky="w", pady=3)
        self.vence = ttk.DateEntry(caja, date_format="%d/%m/%Y", bootstyle="info",
                                   start_date=datetime.now() + timedelta(days=365))
        self.vence.grid(row=2, column=1, sticky="w", padx=(6, 14))
        self.var_autorizado = tk.BooleanVar(value=True)
        ttk.Checkbutton(caja, text="Tiene autorización previa", variable=self.var_autorizado,
                        bootstyle="round-toggle").grid(row=2, column=2, columnspan=2, sticky="w")

        botones = ttk.Frame(caja)
        botones.grid(row=3, column=0, columnspan=4, sticky="w", pady=(8, 0))
        ttk.Button(botones, text="➕ Agregar", command=self.agregar, bootstyle="success").pack(side="left")
        self.btn_guardar = ttk.Button(botones, text="💾 Guardar cambios", command=self.guardar_cambios,
                                      bootstyle="primary", state="disabled")
        self.btn_guardar.pack(side="left", padx=8)
        self.btn_borrar = ttk.Button(botones, text="🗑️ Eliminar", command=self.eliminar,
                                     bootstyle="danger-outline", state="disabled")
        self.btn_borrar.pack(side="left")
        ttk.Button(botones, text="🧹", command=self.limpiar, bootstyle="secondary-outline").pack(side="left", padx=8)

        self.lbl_estado = ttk.Label(caja, text="", bootstyle="secondary")
        self.lbl_estado.grid(row=4, column=0, columnspan=4, sticky="w", pady=(6, 0))

    def al_conectar(self):
        self.cargar()

    def cargar(self):
        if not self.app.hay_conexion():
            self.lbl_lista.configure(text="Sin conexión con MongoDB")
            return

        def consultar():
            return self.app.db.listar("camiones", {}, limite=500, campo_orden="camion_id")

        self.lbl_lista.configure(text="Cargando...")
        self.app.en_segundo_plano(consultar, self.mostrar)

    def mostrar(self, docs, error):
        if error is not None:
            self.lbl_lista.configure(text=mensaje_de(error, "No se pudieron cargar los camiones."))
            return

        anterior = self.seleccionado
        self.docs = {}
        for item in self.tabla.get_children():
            self.tabla.delete(item)

        docs.sort(key=lambda doc: doc["camion_id"])
        for doc in docs:
            iid = str(doc["_id"])
            self.docs[iid] = doc

            texto = "sin fecha"
            etiqueta = ""
            if doc.get("cert_vence") is not None:
                vigente, por_vencer, dias = reglas.estado_certificacion(doc["cert_vence"].date())
                fecha = doc["cert_vence"].strftime("%d/%m/%Y")
                if not vigente:
                    texto = fecha + " (vencida)"
                    etiqueta = "vencida"
                elif por_vencer:
                    texto = fecha + " (faltan " + str(dias) + " días)"
                    etiqueta = "por_vencer"
                else:
                    texto = fecha
            self.tabla.insert("", "end", iid=iid, tags=(etiqueta,), values=(
                doc["camion_id"], doc["placa"], doc["empresa"], "Sí" if doc["autorizacion"] else "No",
                doc.get("conductor", ""), texto))

        self.lbl_lista.configure(text=str(len(docs)) + " camiones")
        if anterior in self.docs:
            self.tabla.selection_set(anterior)

    def _poner(self, caja, valor):
        caja.delete(0, "end")
        caja.insert(0, str(valor))

    def seleccionar(self, evento):
        elegido = self.tabla.selection()
        if len(elegido) == 0:
            return

        self.seleccionado = elegido[0]
        doc = self.docs[self.seleccionado]
        self._poner(self.placa, doc["placa"])
        self._poner(self.camion_id, doc["camion_id"])
        self._poner(self.empresa, doc["empresa"])
        self._poner(self.conductor, doc.get("conductor", ""))
        self.var_autorizado.set(doc["autorizacion"])
        if doc.get("cert_vence") is not None:
            self.vence.set_date(doc["cert_vence"])

        self.btn_guardar.configure(state="normal")
        self.btn_borrar.configure(state="normal")
        self.lbl_estado.configure(text="")

    def leer_formulario(self):
        fecha = self.vence.get_date()
        if fecha is None:
            messagebox.showwarning("Camión", "Elige la fecha en que vence la certificación.")
            return None
        return (self.placa.get(), self.camion_id.get(), self.empresa.get(), self.var_autorizado.get(),
                self.conductor.get(), fecha)

    def agregar(self):
        datos = self.leer_formulario()
        if datos is None:
            return

        def crear():
            return self.app.db.crear_camion(datos[0], datos[1], datos[2], datos[3], datos[4], datos[5])

        self.app.en_segundo_plano(crear, self.despues_de_cambio)

    def guardar_cambios(self):
        if self.seleccionado is None:
            return
        datos = self.leer_formulario()
        if datos is None:
            return
        id_camion = self.seleccionado

        def editar():
            return self.app.db.editar_camion(id_camion, datos[0], datos[1], datos[2], datos[3], datos[4], datos[5])

        self.app.en_segundo_plano(editar, self.despues_de_cambio)

    def eliminar(self):
        if self.seleccionado is None:
            return
        doc = self.docs[self.seleccionado]
        if not messagebox.askyesno("Eliminar", "¿Eliminar el camión " + doc["camion_id"] + "?\n"
                                   "Sus accesos ya guardados se quedan en la bitácora."):
            return
        id_camion = self.seleccionado

        def borrar():
            return self.app.db.eliminar("camiones", id_camion)

        self.seleccionado = None
        self.app.en_segundo_plano(borrar, self.despues_de_cambio)

    def despues_de_cambio(self, resultado, error):
        if error is not None:
            messagebox.showwarning("Camión", mensaje_de(error, "No se pudo guardar el cambio."))
            return

        self.limpiar()
        self.lbl_estado.configure(text="Listo ✅")
        self.cargar()

    def limpiar(self):
        self.seleccionado = None
        for caja in [self.placa, self.camion_id, self.empresa, self.conductor]:
            caja.delete(0, "end")
        self.var_autorizado.set(True)
        self.vence.set_date(datetime.now() + timedelta(days=365))
        self.btn_guardar.configure(state="disabled")
        self.btn_borrar.configure(state="disabled")
        self.lbl_estado.configure(text="")
        for item in self.tabla.selection():
            self.tabla.selection_remove(item)


class PaginaBitacora:

    def __init__(self, padre, app):
        self.app = app
        self.colores = app.colores
        self.marco = ttk.Frame(padre, padding=12)
        self.docs = {}
        self.seleccionado = None

        fila = ttk.Frame(self.marco)
        fila.pack(fill="x")
        ttk.Label(fila, text="Bitácora de accesos", font=("Segoe UI", 13, "bold")).pack(side="left")
        ttk.Button(fila, text="🔍", command=self.cargar, bootstyle="info").pack(side="right")
        self.filtro = ttk.Entry(fila, width=16)
        self.filtro.pack(side="right", padx=6)
        self.filtro.bind("<Return>", lambda evento: self.cargar())
        ttk.Label(fila, text="Placa o ID:").pack(side="right")

        self.lbl_lista = ttk.Label(self.marco, text="", bootstyle="secondary")
        self.lbl_lista.pack(anchor="w")

        zona = ttk.Frame(self.marco)
        zona.pack(fill="x", pady=(4, 0))
        columnas = ("fecha", "camion", "placa", "resultado", "semaforo", "operador")
        self.tabla = ttk.Treeview(zona, columns=columnas, show="headings", height=7, bootstyle="info",
                                  selectmode="browse")
        titulos = {"fecha": "Fecha", "camion": "Camión", "placa": "Placa", "resultado": "Resultado",
                   "semaforo": "Semáforo", "operador": "Operador"}
        anchos = {"fecha": 130, "camion": 90, "placa": 100, "resultado": 200, "semaforo": 80, "operador": 100}
        for columna in columnas:
            self.tabla.heading(columna, text=titulos[columna])
            self.tabla.column(columna, width=anchos[columna], anchor="center")
        self.tabla.pack(side="left", fill="x", expand=True)
        self.tabla.bind("<<TreeviewSelect>>", self.seleccionar)
        self.tabla.tag_configure("rojo", foreground="#ff3b5c")
        self.tabla.tag_configure("amarillo", foreground="#ffd43b")
        self.tabla.tag_configure("verde", foreground="#2bff88")

        barra = ttk.Scrollbar(zona, command=self.tabla.yview)
        barra.pack(side="right", fill="y")
        self.tabla.configure(yscrollcommand=barra.set)

        ttk.Label(self.marco, text="Explicación de la decisión", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(10, 2))
        self.explicacion = tk.Text(self.marco, height=7, wrap="word", state="disabled", font=("Consolas", 10),
                                   bg=self.colores.inputbg, fg=self.colores.inputfg, relief="flat", padx=10, pady=8)
        self.explicacion.pack(fill="both", expand=True)

        self.btn_borrar = ttk.Button(self.marco, text="🗑️ Eliminar este registro", command=self.eliminar,
                                     bootstyle="danger-outline", state="disabled")
        self.btn_borrar.pack(anchor="w", pady=(8, 0))

    def al_conectar(self):
        self.cargar()

    def cargar(self):
        if not self.app.hay_conexion():
            self.lbl_lista.configure(text="Sin conexión con MongoDB")
            return

        texto = self.filtro.get().strip().upper()
        filtro = {}
        if texto != "":
            filtro = {"$or": [{"camion_id": texto}, {"placa": texto}]}

        def consultar():
            return self.app.db.listar("accesos", filtro, limite=200)

        self.lbl_lista.configure(text="Cargando...")
        self.app.en_segundo_plano(consultar, self.mostrar)

    def mostrar(self, docs, error):
        if error is not None:
            self.lbl_lista.configure(text=mensaje_de(error, "No se pudo cargar la bitácora."))
            return

        self.docs = {}
        for item in self.tabla.get_children():
            self.tabla.delete(item)

        for doc in docs:
            iid = str(doc["_id"])
            self.docs[iid] = doc
            self.tabla.insert("", "end", iid=iid, tags=(doc.get("semaforo", ""),), values=(
                formato_fecha(doc.get("creado")), doc.get("camion_id") or "", doc.get("placa") or "",
                doc.get("resultado", ""), doc.get("semaforo", ""), doc.get("operador", "")))

        self.lbl_lista.configure(text=str(len(docs)) + " accesos")
        self.seleccionado = None
        self.btn_borrar.configure(state="disabled")

    def seleccionar(self, evento):
        elegido = self.tabla.selection()
        if len(elegido) == 0:
            return

        self.seleccionado = elegido[0]
        doc = self.docs[self.seleccionado]
        self.explicacion.configure(state="normal")
        self.explicacion.delete("1.0", "end")
        self.explicacion.insert("1.0", "\n".join(doc.get("explicacion", [])))
        self.explicacion.configure(state="disabled")
        self.btn_borrar.configure(state="normal")

    def eliminar(self):
        if self.seleccionado is None:
            return
        if not messagebox.askyesno("Eliminar", "¿Eliminar este registro de la bitácora?"):
            return
        id_acceso = self.seleccionado

        def borrar():
            return self.app.db.eliminar("accesos", id_acceso)

        self.btn_borrar.configure(state="disabled")
        self.app.en_segundo_plano(borrar, self.despues_de_borrar)

    def despues_de_borrar(self, resultado, error):
        if error is not None:
            messagebox.showwarning("Bitácora", mensaje_de(error, "No se pudo eliminar."))
            return

        self.explicacion.configure(state="normal")
        self.explicacion.delete("1.0", "end")
        self.explicacion.configure(state="disabled")
        self.cargar()


class VistaCamiones:

    def __init__(self, padre, app):
        self.marco = ttk.Frame(padre, padding=10)
        paginas = ttk.Notebook(self.marco, bootstyle="secondary")
        paginas.pack(fill="both", expand=True)

        self.camiones = PaginaCamiones(paginas, app)
        self.bitacora = PaginaBitacora(paginas, app)
        paginas.add(self.camiones.marco, text="  🚛 Camiones  ")
        paginas.add(self.bitacora.marco, text="  🗂️ Bitácora de accesos  ")

    def al_conectar(self):
        self.camiones.al_conectar()
        self.bitacora.al_conectar()
