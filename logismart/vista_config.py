import tkinter as tk
from tkinter import messagebox

import ollama
import ttkbootstrap as ttk

import configuracion


def nombres_modelos(respuesta):
    # según la versión de ollama la lista viene como objeto o como diccionario
    nombres = []
    modelos = getattr(respuesta, "models", None)
    if modelos is None:
        modelos = respuesta["models"]

    for modelo in modelos:
        nombre = getattr(modelo, "model", None)
        if nombre is None:
            nombre = modelo["name"]
        nombres.append(nombre)
    return nombres


class VistaConfig:

    def __init__(self, padre, app):
        self.app = app
        self.marco = ttk.Frame(padre, padding=20)

        ttk.Label(self.marco, text="⚙️ Configuración", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(self.marco, text="Los cambios se aplican al guardar y se quedan para la próxima vez.",
                  bootstyle="secondary").pack(anchor="w", pady=(0, 10))

        columnas = ttk.Frame(self.marco)
        columnas.pack(fill="x")
        columnas.columnconfigure(0, weight=1, uniform="col")
        columnas.columnconfigure(1, weight=1, uniform="col")

        izquierda = ttk.Labelframe(columnas, text=" Modelo de IA ", padding=12, bootstyle="info")
        izquierda.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        derecha = ttk.Labelframe(columnas, text=" Reglas y umbrales ", padding=12, bootstyle="info")
        derecha.grid(row=0, column=1, sticky="nsew")
        abajo = ttk.Labelframe(self.marco, text=" Correo a soporte y operador ", padding=12, bootstyle="info")
        abajo.pack(fill="x", pady=(12, 0))

        self._armar_modelo(izquierda)
        self._armar_reglas(derecha)
        self._armar_correo(abajo)

        botones = ttk.Frame(self.marco)
        botones.pack(fill="x", pady=(14, 0))
        ttk.Button(botones, text="💾 Guardar", command=self.guardar, bootstyle="success").pack(side="left")
        ttk.Button(botones, text="↩️ Restaurar valores de fábrica", command=self.restaurar,
                   bootstyle="secondary-outline").pack(side="left", padx=10)

        self.lbl_estado = ttk.Label(self.marco, text="", wraplength=900, justify="left", bootstyle="secondary")
        self.lbl_estado.pack(anchor="w", pady=(10, 0))

        self.mostrar_valores()

    def _armar_modelo(self, padre):
        ttk.Label(padre, text="Modelo de Ollama:").grid(row=0, column=0, sticky="w")
        self.modelo = ttk.Combobox(padre, width=24)
        self.modelo.grid(row=0, column=1, sticky="w", padx=8, pady=3)

        self.btn_modelos = ttk.Button(padre, text="🔎 Ver los instalados", command=self.buscar_modelos,
                                      bootstyle="info-outline")
        self.btn_modelos.grid(row=1, column=1, sticky="w", padx=8, pady=3)

        ttk.Label(padre, text="Intentos si el JSON viene mal:").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.intentos = ttk.Spinbox(padre, from_=1, to=5, width=4)
        self.intentos.grid(row=2, column=1, sticky="w", padx=8, pady=(8, 0))

    def _armar_reglas(self, padre):
        ttk.Label(padre, text="Horario para materiales peligrosos:").grid(row=0, column=0, sticky="w")
        horas = ttk.Frame(padre)
        horas.grid(row=0, column=1, sticky="w", padx=8)
        self.hora_inicio = ttk.Entry(horas, width=7)
        self.hora_inicio.pack(side="left")
        ttk.Label(horas, text=" a ").pack(side="left")
        self.hora_fin = ttk.Entry(horas, width=7)
        self.hora_fin.pack(side="left")

        ttk.Label(padre, text="Días para 'certificación por vencer':").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.dias = ttk.Spinbox(padre, from_=1, to=365, width=6)
        self.dias.grid(row=1, column=1, sticky="w", padx=8, pady=(8, 0))

    def _armar_correo(self, padre):
        padre.columnconfigure(1, weight=1)

        self.var_simulacion = tk.BooleanVar(value=True)
        ttk.Checkbutton(padre, text="Modo simulación (no se manda ningún correo de verdad)",
                        variable=self.var_simulacion, bootstyle="round-toggle").grid(row=0, column=0,
                                                                                     columnspan=2, sticky="w")

        ttk.Label(padre, text="Correo de soporte:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.correo = ttk.Entry(padre)
        self.correo.grid(row=1, column=1, sticky="ew", padx=8, pady=(8, 0))

        ttk.Label(padre, text="Nombre del operador:").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.operador = ttk.Entry(padre)
        self.operador.grid(row=2, column=1, sticky="ew", padx=8, pady=(8, 0))

    def _poner(self, caja, valor):
        caja.delete(0, "end")
        caja.insert(0, str(valor))

    def mostrar_valores(self):
        v = configuracion.valores
        self.modelo.set(v["modelo"])
        self._poner(self.intentos, v["intentos_llm"])
        self._poner(self.hora_inicio, v["hora_inicio"])
        self._poner(self.hora_fin, v["hora_fin"])
        self._poner(self.dias, v["dias_por_vencer"])
        self.var_simulacion.set(v["simulacion_correo"])
        self._poner(self.correo, v["correo_soporte"])
        self._poner(self.operador, v["operador"])

    def buscar_modelos(self):
        def consultar():
            return nombres_modelos(ollama.list())

        self.btn_modelos.configure(state="disabled")
        self.lbl_estado.configure(text="Buscando modelos instalados...", bootstyle="secondary")
        self.app.en_segundo_plano(consultar, self.mostrar_modelos)

    def mostrar_modelos(self, nombres, error):
        self.btn_modelos.configure(state="normal")
        if error is not None:
            self.lbl_estado.configure(text="No pude hablar con Ollama. Revisa que esté abierto.", bootstyle="danger")
            return

        self.modelo.configure(values=nombres)
        if len(nombres) == 0:
            self.lbl_estado.configure(text="No hay modelos instalados todavía.", bootstyle="warning")
        else:
            self.lbl_estado.configure(text="Instalados: " + ", ".join(nombres), bootstyle="success")

    def guardar(self):
        if not self.var_simulacion.get():
            if not messagebox.askyesno("Correo real", "Con la simulación apagada se mandarán correos de verdad "
                                                        "con el SMTP de tu archivo .env. ¿Seguro?"):
                return

        nuevos = {
            "modelo": self.modelo.get(),
            "intentos_llm": self.intentos.get(),
            "hora_inicio": self.hora_inicio.get(),
            "hora_fin": self.hora_fin.get(),
            "dias_por_vencer": self.dias.get(),
            "simulacion_correo": self.var_simulacion.get(),
            "correo_soporte": self.correo.get(),
            "operador": self.operador.get(),
        }

        try:
            configuracion.guardar(nuevos)
        except ValueError as error:
            messagebox.showwarning("Configuración", str(error))
            return
        except OSError:
            messagebox.showwarning("Configuración", "No se pudo guardar el archivo de configuración.")
            return

        self.app.operador = configuracion.valores["operador"]
        self.mostrar_valores()
        self.lbl_estado.configure(text="Configuración guardada ✅", bootstyle="success")

    def restaurar(self):
        if not messagebox.askyesno("Restaurar", "¿Volver a los valores de fábrica?"):
            return

        try:
            configuracion.restaurar()
        except OSError:
            messagebox.showwarning("Configuración", "No se pudo guardar el archivo de configuración.")
            return

        self.app.operador = configuracion.valores["operador"]
        self.mostrar_valores()
        self.lbl_estado.configure(text="Valores de fábrica restaurados ✅", bootstyle="success")
