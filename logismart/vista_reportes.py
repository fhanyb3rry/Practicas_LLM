import os
import tkinter as tk
from datetime import datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox

import ttkbootstrap as ttk

import base_datos
import reportes

NOMBRES = [("accesos", "Bitácora de accesos"), ("incidentes", "Incidentes"),
           ("riesgos_eticos", "Riesgos éticos"), ("camiones", "Camiones")]

FORMATOS = [("pdf", "PDF"), ("csv", "CSV (Excel)"), ("json", "JSON")]


def mensaje_de(error, general):
    if isinstance(error, base_datos.ErrorBD):
        return str(error)
    return general


class VistaReportes:

    def __init__(self, padre, app):
        self.app = app
        self.marco = ttk.Frame(padre, padding=20)
        self.carpeta = None

        ttk.Label(self.marco, text="📄 Reportes", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(self.marco, text="Elige qué quieres sacar, de qué fechas y en qué formato.",
                  bootstyle="secondary").pack(anchor="w", pady=(0, 12))

        columnas = ttk.Frame(self.marco)
        columnas.pack(fill="x")
        columnas.columnconfigure(0, weight=1, uniform="col")
        columnas.columnconfigure(1, weight=1, uniform="col")

        izquierda = ttk.Labelframe(columnas, text=" 1. ¿Qué exportar? ", padding=12, bootstyle="info")
        izquierda.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        derecha = ttk.Labelframe(columnas, text=" 2. Fechas (accesos e incidentes) ", padding=12, bootstyle="info")
        derecha.grid(row=0, column=1, sticky="nsew")

        self.variables = {}
        self.cuentas = {}
        for numero, (clave, nombre) in enumerate(NOMBRES):
            self.variables[clave] = tk.BooleanVar(value=True)
            ttk.Checkbutton(izquierda, text=nombre, variable=self.variables[clave],
                            bootstyle="round-toggle").grid(row=numero, column=0, sticky="w", pady=3)
            self.cuentas[clave] = ttk.Label(izquierda, text="", bootstyle="secondary")
            self.cuentas[clave].grid(row=numero, column=1, sticky="w", padx=12)

        ttk.Label(derecha, text="Desde:").grid(row=0, column=0, sticky="w")
        self.desde = ttk.DateEntry(derecha, date_format="%d/%m/%Y", bootstyle="info",
                                   start_date=datetime.now() - timedelta(days=30))
        self.desde.grid(row=0, column=1, padx=8, pady=3)
        ttk.Label(derecha, text="Hasta:").grid(row=1, column=0, sticky="w")
        self.hasta = ttk.DateEntry(derecha, date_format="%d/%m/%Y", bootstyle="info", start_date=datetime.now())
        self.hasta.grid(row=1, column=1, padx=8, pady=3)
        ttk.Button(derecha, text="🔄 Contar registros", command=self.contar,
                   bootstyle="info-outline").grid(row=2, column=0, columnspan=2, sticky="w", pady=(10, 0))

        formato = ttk.Labelframe(self.marco, text=" 3. Formato ", padding=12, bootstyle="info")
        formato.pack(fill="x", pady=(12, 0))
        self.formato = tk.StringVar(value="pdf")
        for clave, nombre in FORMATOS:
            ttk.Radiobutton(formato, text=nombre, variable=self.formato, value=clave,
                            bootstyle="info").pack(side="left", padx=(0, 24))
        self.lbl_ayuda = ttk.Label(formato, text="PDF y JSON van en un solo archivo. En CSV, cada cosa va en su archivo.",
                                   bootstyle="secondary")
        self.lbl_ayuda.pack(side="left")

        acciones = ttk.Frame(self.marco)
        acciones.pack(fill="x", pady=(16, 0))
        self.btn_exportar = ttk.Button(acciones, text="📄 Exportar", command=self.exportar, bootstyle="success")
        self.btn_exportar.pack(side="left")
        self.btn_abrir = ttk.Button(acciones, text="📂 Abrir carpeta", command=self.abrir_carpeta,
                                    bootstyle="secondary-outline")

        self.lbl_estado = ttk.Label(self.marco, text="", wraplength=900, justify="left", bootstyle="secondary")
        self.lbl_estado.pack(anchor="w", pady=(10, 0))

    def al_conectar(self):
        self.contar()

    def rango_de_fechas(self):
        desde = self.desde.get_date()
        hasta = self.hasta.get_date()
        if desde is None or hasta is None:
            messagebox.showwarning("Fechas", "Elige las dos fechas.")
            return None
        if desde > hasta:
            messagebox.showwarning("Fechas", "La fecha 'Desde' no puede ser después de 'Hasta'.")
            return None
        return desde, hasta + timedelta(days=1)

    def filtro_de(self, coleccion, desde, hasta):
        if coleccion in ("accesos", "incidentes"):
            return {"creado": base_datos.filtro_fechas(desde, hasta)}
        return {}

    def contar(self):
        if not self.app.hay_conexion():
            self.lbl_estado.configure(text="Sin conexión con MongoDB", bootstyle="danger")
            return
        fechas = self.rango_de_fechas()
        if fechas is None:
            return
        desde, hasta = fechas

        def consultar():
            cuentas = {}
            for clave, nombre in NOMBRES:
                cuentas[clave] = self.app.db.contar(clave, self.filtro_de(clave, desde, hasta))
            return cuentas

        self.app.en_segundo_plano(consultar, self.mostrar_cuentas)

    def mostrar_cuentas(self, cuentas, error):
        if error is not None:
            self.lbl_estado.configure(text=mensaje_de(error, "No se pudo contar."), bootstyle="danger")
            return
        for clave in cuentas:
            self.cuentas[clave].configure(text=str(cuentas[clave]) + " registros")

    def elegidos(self):
        lista = []
        for clave, nombre in NOMBRES:
            if self.variables[clave].get():
                lista.append(clave)
        return lista

    def pedir_destino(self, elegidos):
        # regresa un diccionario coleccion -> ruta, o None si cancela
        formato = self.formato.get()
        marca = datetime.now().strftime("%Y%m%d_%H%M")

        if formato == "csv" and len(elegidos) > 1:
            carpeta = filedialog.askdirectory(title="¿En qué carpeta guardo los CSV?")
            if not carpeta:
                return None
            rutas = {}
            for clave in elegidos:
                rutas[clave] = str(Path(carpeta) / (clave + "_" + marca + ".csv"))
            return rutas

        if formato == "csv":
            nombre = elegidos[0] + "_" + marca + ".csv"
        else:
            nombre = "reporte_" + marca + "." + formato

        ruta = filedialog.asksaveasfilename(title="Guardar reporte", initialfile=nombre,
                                            defaultextension="." + formato,
                                            filetypes=[(formato.upper(), "*." + formato)])
        if not ruta:
            return None
        if formato == "csv":
            return {elegidos[0]: ruta}
        return {"todo": ruta}

    def exportar(self):
        elegidos = self.elegidos()
        if len(elegidos) == 0:
            messagebox.showwarning("Reportes", "Elige al menos una cosa para exportar.")
            return
        if not self.app.hay_conexion():
            messagebox.showwarning("Sin conexión", "No hay conexión con MongoDB, no puedo traer los datos.")
            return
        fechas = self.rango_de_fechas()
        if fechas is None:
            return
        desde, hasta = fechas

        destino = self.pedir_destino(elegidos)
        if destino is None:
            return
        formato = self.formato.get()

        def generar():
            datos = {}
            for clave in elegidos:
                filtro = self.filtro_de(clave, desde, hasta)
                if clave == "riesgos_eticos":
                    datos[clave] = self.app.db.listar(clave, filtro, limite=5000, campo_orden="puntaje")
                else:
                    datos[clave] = self.app.db.listar(clave, filtro, limite=5000)

            indicadores = self.app.db.indicadores(desde, hasta)
            if formato == "pdf":
                reportes.exportar_pdf(destino["todo"], datos, indicadores, desde, hasta - timedelta(days=1))
            elif formato == "json":
                reportes.exportar_json(destino["todo"], datos, indicadores)
            else:
                for clave in elegidos:
                    reportes.exportar_csv(destino[clave], clave, datos[clave])

            total = 0
            for clave in datos:
                total += len(datos[clave])
            return list(destino.values()), total

        self.btn_exportar.configure(state="disabled")
        self.btn_abrir.pack_forget()
        self.lbl_estado.configure(text="Generando el reporte...", bootstyle="secondary")
        self.app.en_segundo_plano(generar, self.despues_de_exportar)

    def despues_de_exportar(self, resultado, error):
        self.btn_exportar.configure(state="normal")

        if error is not None:
            if isinstance(error, OSError):
                mensaje = "No se pudo escribir el archivo. ¿Está abierto en otro programa o la carpeta es de solo lectura?"
            else:
                mensaje = mensaje_de(error, "No se pudo generar el reporte.")
            self.lbl_estado.configure(text=mensaje, bootstyle="danger")
            return

        rutas, total = resultado
        self.carpeta = str(Path(rutas[0]).parent)
        self.lbl_estado.configure(text="Listo ✅ " + str(total) + " registros guardados en:\n" + "\n".join(rutas),
                                  bootstyle="success")
        self.btn_abrir.pack(side="left", padx=10)

    def abrir_carpeta(self):
        if self.carpeta is None:
            return
        try:
            os.startfile(self.carpeta)
        except (OSError, AttributeError):
            messagebox.showinfo("Carpeta", "El reporte está en: " + self.carpeta)
