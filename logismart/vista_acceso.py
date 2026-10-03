import tkinter as tk
from datetime import datetime
from tkinter import messagebox

import ttkbootstrap as ttk

import base_datos
import reglas

COLORES = {"rojo": "#ff3b5c", "amarillo": "#ffd43b", "verde": "#2bff88"}
APAGADO = "#2b2b3d"


class VistaAcceso:

    def __init__(self, padre, app):
        self.app = app
        self.colores = app.colores
        self.marco = ttk.Frame(padre, padding=20)

        self.camion = None
        self.por_vencer = False
        self.premisas = None
        self.decision = None

        self.marco.columnconfigure(0, weight=2, uniform="col")
        self.marco.columnconfigure(1, weight=3, uniform="col")
        self.marco.rowconfigure(0, weight=1)

        izquierda = ttk.Frame(self.marco)
        izquierda.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        derecha = ttk.Frame(self.marco)
        derecha.grid(row=0, column=1, sticky="nsew")

        self._armar_formulario(izquierda)
        self._armar_resultado(derecha)

    def _armar_formulario(self, padre):
        ttk.Label(padre, text="Buscar camión", font=("Segoe UI", 14, "bold")).pack(anchor="w")

        fila = ttk.Frame(padre)
        fila.pack(fill="x", pady=(6, 8))
        self.busqueda = ttk.Entry(fila)
        self.busqueda.pack(side="left", fill="x", expand=True)
        self.busqueda.bind("<Return>", lambda evento: self.buscar())
        self.btn_buscar = ttk.Button(fila, text="🔍 Buscar", command=self.buscar, bootstyle="info")
        self.btn_buscar.pack(side="left", padx=(8, 0))
        ttk.Label(padre, text="Placa o ID, por ejemplo ABC-123-D o CAM-102", bootstyle="secondary").pack(anchor="w")

        self.lbl_camion = ttk.Label(padre, text="Sin camión seleccionado, puedes evaluar a mano.",
                                    wraplength=380, justify="left", bootstyle="secondary")
        self.lbl_camion.pack(anchor="w", pady=14)

        ttk.Separator(padre).pack(fill="x", pady=4)
        ttk.Label(padre, text="Datos de la revisión", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(10, 6))

        self.var_p = tk.BooleanVar(value=False)
        self.var_q = tk.BooleanVar(value=False)
        self.var_r = tk.BooleanVar(value=False)
        self.var_s = tk.BooleanVar(value=False)

        ttk.Checkbutton(padre, text="P  Tiene autorización previa", variable=self.var_p,
                        bootstyle="round-toggle").pack(anchor="w", pady=4)
        ttk.Checkbutton(padre, text="Q  El peso excede el límite", variable=self.var_q,
                        bootstyle="round-toggle").pack(anchor="w", pady=4)
        ttk.Checkbutton(padre, text="R  Lleva materiales peligrosos", variable=self.var_r,
                        bootstyle="round-toggle").pack(anchor="w", pady=4)
        ttk.Checkbutton(padre, text="S  Conductor con certificación vigente", variable=self.var_s,
                        bootstyle="round-toggle").pack(anchor="w", pady=4)

        hora = ttk.Frame(padre)
        hora.pack(fill="x", pady=(14, 4))
        ttk.Label(hora, text="Hora (HH:MM):").pack(side="left")
        self.hora = ttk.Entry(hora, width=8)
        self.hora.pack(side="left", padx=8)
        ttk.Label(hora, text="vacío = la hora de ahorita", bootstyle="secondary").pack(side="left")

        botones = ttk.Frame(padre)
        botones.pack(fill="x", pady=(18, 0))
        ttk.Button(botones, text="✅ Evaluar", command=self.evaluar, bootstyle="primary").pack(side="left")
        self.btn_guardar = ttk.Button(botones, text="💾 Guardar en bitácora", command=self.guardar,
                                      bootstyle="success", state="disabled")
        self.btn_guardar.pack(side="left", padx=8)
        ttk.Button(botones, text="🧹", command=self.limpiar, bootstyle="secondary-outline").pack(side="left")

        self.lbl_estado = ttk.Label(padre, text="", bootstyle="secondary")
        self.lbl_estado.pack(anchor="w", pady=(10, 0))

    def _armar_resultado(self, padre):
        arriba = ttk.Frame(padre)
        arriba.pack(fill="x")

        self.semaforo = tk.Canvas(arriba, width=110, height=290, bg=self.colores.bg, highlightthickness=0)
        self.semaforo.pack(side="left")
        self.pintar_semaforo(None)

        textos = ttk.Frame(arriba)
        textos.pack(side="left", fill="both", expand=True, padx=20)
        self.lbl_resultado = ttk.Label(textos, text="Sin evaluar", font=("Segoe UI", 24, "bold"),
                                       bootstyle="secondary", wraplength=420, justify="left")
        self.lbl_resultado.pack(anchor="w", pady=(30, 8))
        self.lbl_detalle = ttk.Label(textos, text="Llena los datos y pulsa Evaluar.",
                                     wraplength=420, justify="left", bootstyle="secondary")
        self.lbl_detalle.pack(anchor="w")

        ttk.Label(padre, text="Explicación paso a paso", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(14, 4))

        self.explicacion = tk.Text(padre, height=12, wrap="word", state="disabled", font=("Consolas", 10),
                                   bg=self.colores.inputbg, fg=self.colores.inputfg, relief="flat", padx=12, pady=10)
        self.explicacion.pack(fill="both", expand=True)

    def pintar_semaforo(self, color):
        self.semaforo.delete("all")
        self.semaforo.create_rectangle(10, 5, 100, 285, fill="#15102a", outline="#444466", width=2)

        luces = [("rojo", 55), ("amarillo", 145), ("verde", 235)]
        for nombre, y in luces:
            relleno = APAGADO
            borde = "#444466"
            if nombre == color:
                relleno = COLORES[nombre]
                borde = "white"
            self.semaforo.create_oval(25, y - 30, 85, y + 30, fill=relleno, outline=borde, width=2)

    def buscar(self):
        texto = self.busqueda.get().strip()
        if texto == "":
            self.lbl_estado.configure(text="Escribe una placa o un ID.")
            return
        if not self.app.hay_conexion():
            messagebox.showwarning("Sin conexión", "No hay conexión con MongoDB, pero puedes evaluar a mano.")
            return

        def consultar():
            return self.app.db.buscar_camion(texto)

        self.btn_buscar.configure(state="disabled")
        self.lbl_estado.configure(text="Buscando...")
        self.app.en_segundo_plano(consultar, self.mostrar_camion)

    def mostrar_camion(self, camion, error):
        self.btn_buscar.configure(state="normal")

        if error is not None:
            if isinstance(error, base_datos.ErrorBD):
                self.lbl_estado.configure(text=str(error))
            else:
                self.lbl_estado.configure(text="No se pudo buscar.")
            return

        self.camion = camion
        self.por_vencer = False

        if camion is None:
            self.lbl_camion.configure(text="No encontré ese camión. Puedes evaluar a mano.")
            self.lbl_estado.configure(text="")
            return

        vigente = False
        certificacion = "Sin fecha de certificación."
        if camion.get("cert_vence") is not None:
            vigente, self.por_vencer, dias = reglas.estado_certificacion(camion["cert_vence"].date())
            fecha = camion["cert_vence"].strftime("%d/%m/%Y")
            if vigente:
                certificacion = "Certificación vence el " + fecha + " (faltan " + str(dias) + " días)."
            else:
                certificacion = "Certificación vencida desde el " + fecha + "."

        self.var_p.set(bool(camion.get("autorizacion")))
        self.var_s.set(vigente)

        self.lbl_camion.configure(
            text=camion["camion_id"] + " · " + camion["placa"] + "\n" + camion["empresa"] +
                 "\nConductor: " + camion.get("conductor", "") + "\n" + certificacion,
            bootstyle="info")
        self.lbl_estado.configure(text="P y S se llenaron solos, falta Q y R.")

    def evaluar(self):
        texto = self.hora.get().strip()
        if texto == "":
            hora = datetime.now().time()
        else:
            try:
                hora = datetime.strptime(texto, "%H:%M").time()
            except ValueError:
                messagebox.showwarning("Hora", "Escribe la hora como HH:MM, por ejemplo 14:30.")
                return

        H = reglas.hora_permitida(hora)
        self.premisas = {
            "P": self.var_p.get(), "Q": self.var_q.get(), "R": self.var_r.get(),
            "S": self.var_s.get(), "H": H, "W": self.por_vencer and self.var_s.get(),
        }
        p = self.premisas
        self.decision = reglas.decidir(p["P"], p["Q"], p["R"], p["S"], p["H"], p["W"])

        semaforo = self.decision["semaforo"]
        self.pintar_semaforo(semaforo)
        self.lbl_resultado.configure(text=self.decision["resultado"], foreground=COLORES[semaforo])
        self.lbl_detalle.configure(text="Hora evaluada: " + hora.strftime("%H:%M") + ". " + " ".join(self.decision["motivo"]))

        self.explicacion.configure(state="normal")
        self.explicacion.delete("1.0", "end")
        self.explicacion.insert("1.0", "\n".join(self.decision["pasos"]))
        self.explicacion.configure(state="disabled")

        self.btn_guardar.configure(state="normal")
        self.lbl_estado.configure(text="")

    def guardar(self):
        if self.decision is None:
            return
        if not self.app.hay_conexion():
            messagebox.showwarning("Sin conexión", "No hay conexión con MongoDB, no se pudo guardar.")
            return

        def registrar():
            return self.app.db.registrar_acceso(self.camion, self.premisas, self.decision, self.app.operador)

        self.btn_guardar.configure(state="disabled")
        self.lbl_estado.configure(text="Guardando...")
        self.app.en_segundo_plano(registrar, self.despues_de_guardar)

    def despues_de_guardar(self, resultado, error):
        if error is not None:
            self.btn_guardar.configure(state="normal")
            if isinstance(error, base_datos.ErrorBD):
                self.lbl_estado.configure(text=str(error))
            else:
                self.lbl_estado.configure(text="No se pudo guardar.")
            return

        self.lbl_estado.configure(text="Guardado en la bitácora ✅")

    def limpiar(self):
        self.camion = None
        self.por_vencer = False
        self.premisas = None
        self.decision = None

        self.busqueda.delete(0, "end")
        self.hora.delete(0, "end")
        self.var_p.set(False)
        self.var_q.set(False)
        self.var_r.set(False)
        self.var_s.set(False)

        self.lbl_camion.configure(text="Sin camión seleccionado, puedes evaluar a mano.", bootstyle="secondary")
        self.lbl_resultado.configure(text="Sin evaluar", foreground=self.colores.secondary)
        self.lbl_detalle.configure(text="Llena los datos y pulsa Evaluar.")
        self.pintar_semaforo(None)

        self.explicacion.configure(state="normal")
        self.explicacion.delete("1.0", "end")
        self.explicacion.configure(state="disabled")

        self.btn_guardar.configure(state="disabled")
        self.lbl_estado.configure(text="")
