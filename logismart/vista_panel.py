from datetime import datetime, timedelta
from tkinter import messagebox

import ttkbootstrap as ttk

import base_datos


class VistaPanel:

    def __init__(self, padre, app):
        self.app = app
        self.marco = ttk.Frame(padre, padding=20)

        filtros = ttk.Frame(self.marco)
        filtros.pack(fill="x")

        ttk.Label(filtros, text="Desde:").pack(side="left")
        self.desde = ttk.DateEntry(filtros, date_format="%d/%m/%Y", bootstyle="info",
                                   start_date=datetime.now() - timedelta(days=30))
        self.desde.pack(side="left", padx=(6, 18))

        ttk.Label(filtros, text="Hasta:").pack(side="left")
        self.hasta = ttk.DateEntry(filtros, date_format="%d/%m/%Y", bootstyle="info",
                                   start_date=datetime.now())
        self.hasta.pack(side="left", padx=(6, 18))

        self.btn_actualizar = ttk.Button(filtros, text="🔄 Actualizar", command=self.actualizar, bootstyle="primary")
        self.btn_actualizar.pack(side="left")

        self.lbl_estado = ttk.Label(filtros, text="", bootstyle="secondary")
        self.lbl_estado.pack(side="right")

        tarjetas = ttk.Frame(self.marco)
        tarjetas.pack(fill="x", pady=20)
        for columna in range(3):
            tarjetas.columnconfigure(columna, weight=1, uniform="tarjeta")

        self.num_camiones = self._tarjeta(tarjetas, 0, "🚛 Camiones atendidos", "info")
        self.num_incidentes = self._tarjeta(tarjetas, 1, "📥 Incidentes abiertos", "warning")
        self.num_riesgos = self._tarjeta(tarjetas, 2, "⚠️ Riesgos críticos", "danger")

        ttk.Label(self.marco, text="Incidentes por categoría y semana", font=("Segoe UI", 14, "bold")).pack(anchor="w")

        zona = ttk.Frame(self.marco)
        zona.pack(fill="both", expand=True, pady=(8, 0))

        self.tabla = ttk.Treeview(zona, columns=("semana", "categoria", "total"), show="headings", bootstyle="info")
        self.tabla.heading("semana", text="Semana")
        self.tabla.heading("categoria", text="Categoría")
        self.tabla.heading("total", text="Total")
        self.tabla.column("semana", width=140, anchor="center")
        self.tabla.column("categoria", width=300)
        self.tabla.column("total", width=100, anchor="center")
        self.tabla.pack(side="left", fill="both", expand=True)

        barra = ttk.Scrollbar(zona, command=self.tabla.yview)
        barra.pack(side="right", fill="y")
        self.tabla.configure(yscrollcommand=barra.set)

    def _tarjeta(self, padre, columna, titulo, estilo):
        tarjeta = ttk.Labelframe(padre, text=" " + titulo + " ", bootstyle=estilo, padding=15)
        tarjeta.grid(row=0, column=columna, sticky="ew", padx=8)

        numero = ttk.Label(tarjeta, text="-", font=("Segoe UI", 40, "bold"), bootstyle=estilo)
        numero.pack()
        return numero

    def al_conectar(self):
        self.actualizar()

    def actualizar(self):
        if not self.app.hay_conexion():
            self.lbl_estado.configure(text="Sin conexión con MongoDB")
            return

        desde = self.desde.get_date()
        hasta = self.hasta.get_date()

        if desde is None or hasta is None:
            messagebox.showwarning("Fechas", "Elige las dos fechas.")
            return
        if desde > hasta:
            messagebox.showwarning("Fechas", "La fecha 'Desde' no puede ser después de 'Hasta'.")
            return

        # el día final tiene que contar completo
        hasta = hasta + timedelta(days=1)

        def consultar():
            indicadores = self.app.db.indicadores(desde, hasta)
            filas = self.app.db.incidentes_por_categoria_y_semana(desde, hasta)
            return indicadores, filas

        self.btn_actualizar.configure(state="disabled")
        self.lbl_estado.configure(text="Cargando...")
        self.app.en_segundo_plano(consultar, self.mostrar)

    def mostrar(self, resultado, error):
        self.btn_actualizar.configure(state="normal")

        if error is not None:
            if isinstance(error, base_datos.ErrorBD):
                self.lbl_estado.configure(text=str(error))
            else:
                self.lbl_estado.configure(text="No se pudo cargar el panel.")
            return

        indicadores, filas = resultado
        self.num_camiones.configure(text=str(indicadores["camiones_atendidos"]))
        self.num_incidentes.configure(text=str(indicadores["incidentes_abiertos"]))
        self.num_riesgos.configure(text=str(indicadores["riesgos_criticos"]))

        for item in self.tabla.get_children():
            self.tabla.delete(item)
        for fila in filas:
            self.tabla.insert("", "end", values=(fila["semana"], fila["categoria"], fila["total"]))

        self.lbl_estado.configure(text="Actualizado " + datetime.now().strftime("%H:%M:%S"))
