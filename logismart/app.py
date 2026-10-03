import queue
import threading
import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk

import base_datos
import configuracion
from vista_acceso import VistaAcceso
from vista_asistente import VistaAsistente
from vista_camiones import VistaCamiones
from vista_config import VistaConfig
from vista_incidentes import VistaIncidentes
from vista_panel import VistaPanel
from vista_reportes import VistaReportes
from vista_riesgos import VistaRiesgos
from vista_simulador import VistaSimulador


class AppLogiSmart:

    def __init__(self, ventana):
        self.ventana = ventana
        self.colores = ventana.style.colors
        self.db = base_datos.BaseDatos()
        configuracion.cargar()
        self.operador = configuracion.valores["operador"]

        self.cola = queue.Queue()
        self.vistas = []

        self._armar_encabezado()
        self._armar_pestanas()

        self.ventana.protocol("WM_DELETE_WINDOW", self.cerrar)
        self.ventana.after(100, self._revisar_cola)
        self.conectar()

    def _armar_encabezado(self):
        encabezado = ttk.Frame(self.ventana, padding=(20, 12, 20, 0))
        encabezado.pack(fill="x")

        ttk.Label(encabezado, text="🚚 LogiSmart", font=("Segoe UI", 24, "bold"), bootstyle="info").pack(side="left")
        ttk.Label(encabezado, text="  Centro de control de accesos", bootstyle="secondary").pack(side="left", pady=(10, 0))

        self.btn_reintentar = ttk.Button(encabezado, text="Reintentar", command=self.conectar, bootstyle="warning-outline")
        self.lbl_conexion = ttk.Label(encabezado, text="", bootstyle="secondary")
        self.lbl_conexion.pack(side="right")

    def _armar_pestanas(self):
        self.pestanas = ttk.Notebook(self.ventana, bootstyle="info")
        self.pestanas.pack(fill="both", expand=True, padx=15, pady=15)

        self._agregar("📊 Panel", VistaPanel(self.pestanas, self))
        self._agregar("🚦 Acceso", VistaAcceso(self.pestanas, self))
        self._agregar("🧮 Simulador", VistaSimulador(self.pestanas, self))
        self._agregar("🚛 Camiones", VistaCamiones(self.pestanas, self))
        self._agregar("📥 Incidentes", VistaIncidentes(self.pestanas, self))
        self._agregar("💬 Asistente", VistaAsistente(self.pestanas, self))
        self._agregar("⚖️ Riesgos", VistaRiesgos(self.pestanas, self))
        self._agregar("📄 Reportes", VistaReportes(self.pestanas, self))
        self._agregar("⚙️ Config", VistaConfig(self.pestanas, self))

    def _agregar(self, titulo, vista):
        self.pestanas.add(vista.marco, text=" " + titulo + " ")
        self.vistas.append(vista)

    def conectar(self):
        self.btn_reintentar.pack_forget()
        self.lbl_conexion.configure(text="Conectando a MongoDB...", bootstyle="warning")
        self.en_segundo_plano(self._conectar_y_preparar, self._termino_conexion)

    def _conectar_y_preparar(self):
        self.db.conectar()
        self.db.preparar()

    def _termino_conexion(self, resultado, error):
        if error is not None:
            if isinstance(error, base_datos.ErrorBD):
                mensaje = str(error)
            else:
                mensaje = "No se pudo conectar con MongoDB."
            self.lbl_conexion.configure(text="🔴 Sin conexión", bootstyle="danger")
            self.btn_reintentar.pack(side="right", padx=(0, 10))
            messagebox.showwarning("Sin conexión", mensaje)
            return

        self.lbl_conexion.configure(text="🟢 Conectado a MongoDB", bootstyle="success")
        for vista in self.vistas:
            if hasattr(vista, "al_conectar"):
                vista.al_conectar()

    def hay_conexion(self):
        return self.db.conectado()

    def en_segundo_plano(self, trabajo, al_terminar):
        
        def correr():
            try:
                self.cola.put((al_terminar, trabajo(), None))
            except Exception as error:
                self.cola.put((al_terminar, None, error))

        threading.Thread(target=correr, daemon=True).start()

    def _revisar_cola(self):
        try:
            while True:
                al_terminar, resultado, error = self.cola.get_nowait()
                al_terminar(resultado, error)
        except queue.Empty:
            pass

        self.ventana.after(100, self._revisar_cola)

    def cerrar(self):
        self.db.cerrar()
        self.ventana.destroy()


if __name__ == "__main__":
    ventana = ttk.Window(title="LogiSmart", themename="vapor", size=(1200, 800), minsize=(1050, 700))
    AppLogiSmart(ventana)
    ventana.mainloop()
