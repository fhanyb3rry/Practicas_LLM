import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk

import asistente
import base_datos

SUGERENCIAS = [
    "¿Por qué CAM-102 fue enviado a inspección?",
    "¿Cuántos incidentes abiertos hay?",
    "¿Cuáles son los riesgos más altos?",
]


class VistaAsistente:

    def __init__(self, padre, app):
        self.app = app
        self.colores = app.colores
        self.marco = ttk.Frame(padre, padding=15)

        self.historial = []
        self.ocupado = False

        self.marco.columnconfigure(0, weight=3, uniform="col")
        self.marco.columnconfigure(1, weight=2, uniform="col")
        self.marco.rowconfigure(0, weight=1)

        izquierda = ttk.Frame(self.marco)
        izquierda.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        derecha = ttk.Frame(self.marco)
        derecha.grid(row=0, column=1, sticky="nsew")

        self._armar_chat(izquierda)
        self._armar_fuentes(derecha)
        self._bienvenida()

    def _armar_chat(self, padre):
        fila = ttk.Frame(padre)
        fila.pack(fill="x")
        ttk.Label(fila, text="💬 Asistente", font=("Segoe UI", 14, "bold")).pack(side="left")
        ttk.Button(fila, text="🧹 Limpiar chat", command=self.limpiar, bootstyle="secondary-outline").pack(side="right")

        # lo de abajo se empaca primero para que el chat no lo empuje fuera de la ventana
        self.lbl_estado = ttk.Label(padre, text="", bootstyle="secondary")
        self.lbl_estado.pack(side="bottom", anchor="w", pady=(6, 0))
        self.carga = ttk.Progressbar(padre, mode="indeterminate", bootstyle="info-striped")

        entrada = ttk.Frame(padre)
        entrada.pack(side="bottom", fill="x", pady=(8, 0))
        entrada.columnconfigure(0, weight=1)
        self.entrada = ttk.Entry(entrada, font=("Segoe UI", 11))
        self.entrada.grid(row=0, column=0, sticky="ew", ipady=4)
        self.entrada.bind("<Return>", lambda evento: self.enviar())
        self.btn_enviar = ttk.Button(entrada, text="Enviar ➤", command=self.enviar, bootstyle="primary")
        self.btn_enviar.grid(row=0, column=1, padx=(8, 0))

        sugerencias = ttk.Frame(padre)
        sugerencias.pack(side="bottom", fill="x", pady=(8, 0))
        self.botones_sugerencia = []
        for texto in SUGERENCIAS:
            boton = ttk.Button(sugerencias, text=texto, bootstyle="info-outline",
                               command=lambda t=texto: self.usar_sugerencia(t))
            boton.pack(anchor="w", pady=2)
            self.botones_sugerencia.append(boton)

        zona = ttk.Frame(padre)
        zona.pack(fill="both", expand=True, pady=(8, 0))
        zona.rowconfigure(0, weight=1)
        zona.columnconfigure(0, weight=1)

        self.chat = tk.Text(zona, wrap="word", state="disabled", font=("Segoe UI", 11), height=8,
                            bg=self.colores.inputbg, fg=self.colores.inputfg, relief="flat",
                            padx=12, pady=10, spacing3=4)
        self.chat.grid(row=0, column=0, sticky="nsew")
        barra = ttk.Scrollbar(zona, command=self.chat.yview)
        barra.grid(row=0, column=1, sticky="ns")
        self.chat.configure(yscrollcommand=barra.set)

        self.chat.tag_configure("tu", foreground=self.colores.warning, font=("Segoe UI", 11, "bold"))
        self.chat.tag_configure("asistente", foreground=self.colores.info, font=("Segoe UI", 11, "bold"))
        self.chat.tag_configure("aviso", foreground=self.colores.secondary, font=("Segoe UI", 9, "italic"))

    def _armar_fuentes(self, padre):
        ttk.Label(padre, text="📚 Fuentes consultadas", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(padre, text="Lo que sacó de la base de datos para responder.", bootstyle="secondary").pack(anchor="w")

        self.fuentes = tk.Text(padre, wrap="word", state="disabled", font=("Segoe UI", 10),
                               bg=self.colores.inputbg, fg=self.colores.inputfg, relief="flat", padx=10, pady=8)
        self.fuentes.pack(fill="both", expand=True, pady=(8, 0))
        self.fuentes.tag_configure("titulo", foreground=self.colores.info, font=("Segoe UI", 10, "bold"))

    def _bienvenida(self):
        self._escribir("Asistente\n", "asistente")
        self._escribir("Pregúntame por qué se tomó una decisión, por los incidentes o por los riesgos. "
                       "Solo respondo con lo que hay en la base de datos.\n\n")

    def _escribir(self, texto, tag=None):
        self.chat.configure(state="normal")
        if tag is None:
            self.chat.insert("end", texto)
        else:
            self.chat.insert("end", texto, tag)
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def usar_sugerencia(self, texto):
        self.entrada.delete(0, "end")
        self.entrada.insert(0, texto)
        self.enviar()

    def _bloquear(self, valor):
        self.ocupado = valor
        estado = "normal"
        if valor:
            estado = "disabled"

        self.entrada.configure(state=estado)
        self.btn_enviar.configure(state=estado)
        for boton in self.botones_sugerencia:
            boton.configure(state=estado)

        if valor:
            self.carga.pack(side="bottom", fill="x", pady=(6, 0), after=self.lbl_estado)
            self.carga.start(12)
        else:
            self.carga.stop()
            self.carga.pack_forget()
            self.entrada.focus()

    def enviar(self):
        if self.ocupado:
            return

        pregunta = self.entrada.get().strip()
        if pregunta == "":
            self.lbl_estado.configure(text="Escribe una pregunta primero 😅")
            return

        self.entrada.delete(0, "end")
        self._escribir("Tú\n", "tu")
        self._escribir(pregunta + "\n\n")

        if not self.app.hay_conexion():
            self._escribir("No hay conexión con MongoDB, así que no puedo consultar los registros.\n\n", "aviso")
            return

        def consultar():
            return asistente.responder(self.app.db, pregunta, self.historial)

        self._bloquear(True)
        self.lbl_estado.configure(text="Consultando la base de datos y pensando...")
        self.app.en_segundo_plano(consultar, self.mostrar)

    def mostrar(self, resultado, error):
        self._bloquear(False)

        if error is not None:
            if isinstance(error, base_datos.ErrorBD):
                mensaje = str(error)
            else:
                mensaje = "Ups, algo falló al consultar."
            self._escribir(mensaje + "\n\n", "aviso")
            self.lbl_estado.configure(text="")
            return

        self._escribir("Asistente\n", "asistente")
        self._escribir(resultado["respuesta"] + "\n")

        if len(resultado["fuentes"]) > 0:
            self._escribir("Fuentes: " + asistente.texto_fuentes(resultado["fuentes"]).replace("\n", "  ") + "\n", "aviso")
        self._escribir("\n")
        self._mostrar_fuentes(resultado["fuentes"])

        if resultado["uso_llm"]:
            self.lbl_estado.configure(text="Respondió en " + str(round(resultado["latencia_ms"] / 1000, 1)) + " s")
            self._guardar_evaluacion(resultado)
        else:
            self.lbl_estado.configure(text="")

    def _mostrar_fuentes(self, fuentes):
        self.fuentes.configure(state="normal")
        self.fuentes.delete("1.0", "end")
        if len(fuentes) == 0:
            self.fuentes.insert("end", "Sin fuentes: no se usó ningún registro.")
        for f in fuentes:
            self.fuentes.insert("end", "[" + str(f["n"]) + "] " + f["coleccion"] + " · " + f["id"][-6:] + "\n", "titulo")
            self.fuentes.insert("end", f["texto"] + "\n\n")
        self.fuentes.configure(state="disabled")

    def _guardar_evaluacion(self, resultado):
        def guardar():
            return self.app.db.registrar_evaluacion_llm(resultado["prompt"], resultado["respuesta"],
                                                        resultado["modelo"], resultado["latencia_ms"], None)

        self.app.en_segundo_plano(guardar, self._ignorar)

    def _ignorar(self, resultado, error):
        pass

    def limpiar(self):
        if self.ocupado:
            return
        if not messagebox.askyesno("Limpiar chat", "¿Seguro? Se borra la conversación de esta pantalla."):
            return

        self.historial = []
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.configure(state="disabled")
        self._mostrar_fuentes([])
        self._bienvenida()
        self.lbl_estado.configure(text="")
