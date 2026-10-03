import queue
import threading
import tkinter as tk
from tkinter import messagebox

import ollama
import ttkbootstrap as ttk

# CONFIGURACIÓN

MODELO = "llama3.2"

mensaje_sistema = """
Eres el Chef Remy, un chef mexicano muy amable y paciente que ayuda
a estudiantes universitarios que apenas están aprendiendo a cocinar.

Debes:

1. Responder siempre en español, con un tono cálido y cercano.
2. Explicar las recetas paso a paso y con ingredientes claros.
3. Usar ingredientes baratos y fáciles de conseguir.
4. Dar tiempos y temperaturas aproximadas.
5. Si el estudiante comete un error, explicarle con cariño cómo corregirlo.
6. Explicar el porqué de cada paso, no solo qué hacer.
7. Avisar de riesgos (cuchillos, aceite caliente, comida mal cocida).
8. Si te preguntan algo que no tiene que ver con cocina, decir amablemente
   que solo sabes de cocina y regresar al tema.
"""

SUGERENCIAS = [
    "¿Qué puedo cocinar con huevo y tortillas?",
    "¿Cómo cocino arroz que no quede pegajoso?",
    "Dame una receta fácil para una comida rápida",
]


# VENTANA

def dibujar_remy(canvas):
    gris = "#8f9bb3"
    claro = "#d8dbe6"
    rosa = "#ff9ab8"

    canvas.create_oval(8, 36, 34, 62, fill=gris, outline="")
    canvas.create_oval(14, 42, 28, 56, fill=rosa, outline="")
    canvas.create_oval(56, 36, 82, 62, fill=gris, outline="")
    canvas.create_oval(62, 42, 76, 56, fill=rosa, outline="")

    canvas.create_oval(17, 40, 73, 90, fill=gris, outline="")
    canvas.create_oval(32, 64, 58, 88, fill=claro, outline="")

    # ojitos con brillo
    canvas.create_oval(31, 54, 39, 63, fill="black", outline="")
    canvas.create_oval(51, 54, 59, 63, fill="black", outline="")
    canvas.create_oval(34, 56, 37, 59, fill="white", outline="")
    canvas.create_oval(54, 56, 57, 59, fill="white", outline="")

    canvas.create_oval(40, 70, 50, 77, fill="#ff6f9f", outline="")
    canvas.create_line(45, 77, 45, 82, fill="#5a5a70", width=2)
    canvas.create_line(45, 82, 40, 86, 36, 84, smooth=True, fill="#5a5a70", width=2)
    canvas.create_line(45, 82, 50, 86, 54, 84, smooth=True, fill="#5a5a70", width=2)

    canvas.create_line(30, 76, 6, 71, fill="#e8e8f0", width=1)
    canvas.create_line(30, 80, 6, 82, fill="#e8e8f0", width=1)
    canvas.create_line(60, 76, 84, 71, fill="#e8e8f0", width=1)
    canvas.create_line(60, 80, 84, 82, fill="#e8e8f0", width=1)

    # gorro de chef
    canvas.create_oval(18, 12, 42, 34, fill="white", outline="#dcdcf0")
    canvas.create_oval(48, 12, 72, 34, fill="white", outline="#dcdcf0")
    canvas.create_oval(30, 2, 60, 30, fill="white", outline="#dcdcf0")
    canvas.create_rectangle(24, 26, 66, 42, fill="white", outline="#dcdcf0")
    canvas.create_line(25, 36, 65, 36, fill="#dcdcf0")


class ChefApp:

    def __init__(self, ventana):
        self.ventana = ventana
        self.colores = ventana.style.colors

        self.mensajes = [{"role": "system", "content": mensaje_sistema}]

        self.preguntas = []

        # hilo anticongelante:)
        self.cola = queue.Queue()
        self.ocupado = False

        self._armar_ventana()
        self._mensaje_bienvenida()

        self.ventana.after(100, self._revisar_cola)

    def _armar_ventana(self):
        self.ventana.columnconfigure(0, weight=3)
        self.ventana.columnconfigure(1, weight=1)
        self.ventana.rowconfigure(1, weight=1)

        encabezado = ttk.Frame(self.ventana, padding=(20, 15, 20, 5))
        encabezado.grid(row=0, column=0, columnspan=2, sticky="ew")

        remy = tk.Canvas(encabezado, width=90, height=96, bg=self.colores.bg, highlightthickness=0)
        remy.pack(side="left", padx=(0, 12))
        dibujar_remy(remy)

        ttk.Label(
            encabezado,
            text="Chef Virtual",
            font=("Segoe UI", 24, "bold"),
            bootstyle="info",
        ).pack(side="left")

        ttk.Label(
            encabezado,
            text=f"Modelo: {MODELO}",
            bootstyle="secondary",
        ).pack(side="right", pady=(12, 0))

        zona_chat = ttk.Frame(self.ventana, padding=(20, 5, 10, 5))
        zona_chat.grid(row=1, column=0, sticky="nsew")
        zona_chat.rowconfigure(0, weight=1)
        zona_chat.columnconfigure(0, weight=1)

        self.chat = tk.Text(
            zona_chat,
            wrap="word",
            state="disabled",
            font=("Segoe UI", 11),
            bg=self.colores.inputbg,
            fg=self.colores.inputfg,
            relief="flat",
            padx=15,
            pady=15,
            spacing3=4,
        )
        self.chat.grid(row=0, column=0, sticky="nsew")

        barra = ttk.Scrollbar(zona_chat, command=self.chat.yview)
        barra.grid(row=0, column=1, sticky="ns")
        self.chat.configure(yscrollcommand=barra.set)

        self.chat.tag_configure(
            "tu", foreground=self.colores.warning, font=("Segoe UI", 11, "bold")
        )
        self.chat.tag_configure(
            "chef", foreground=self.colores.info, font=("Segoe UI", 11, "bold")
        )
        self.chat.tag_configure("texto", lmargin1=10, lmargin2=10)
        self.chat.tag_configure(
            "aviso", foreground=self.colores.secondary, font=("Segoe UI", 10, "italic")
        )
        self.chat.tag_configure("error", foreground=self.colores.danger)

        panel = ttk.Frame(self.ventana, padding=(10, 5, 20, 5))
        panel.grid(row=1, column=1, sticky="nsew")
        panel.rowconfigure(2, weight=1)
        panel.columnconfigure(0, weight=1)

        ttk.Label(
            panel, text="📜 Tu historial", font=("Segoe UI", 14, "bold")
        ).grid(row=0, column=0, sticky="w")

        self.lbl_contador = ttk.Label(panel, text="Aún no preguntas nada", bootstyle="secondary")
        self.lbl_contador.grid(row=1, column=0, sticky="w", pady=(0, 8))

        self.lista = tk.Listbox(
            panel,
            font=("Segoe UI", 10),
            bg=self.colores.inputbg,
            fg=self.colores.inputfg,
            selectbackground=self.colores.primary,
            relief="flat",
            highlightthickness=0,
            activestyle="none",
        )
        self.lista.grid(row=2, column=0, sticky="nsew")

        ttk.Button(
            panel, text="📝 Resumen", command=self.pedir_resumen, bootstyle="success"
        ).grid(row=3, column=0, sticky="ew", pady=(10, 4))

        ttk.Button(
            panel, text="🧹 Limpiar chat", command=self.limpiar, bootstyle="danger-outline"
        ).grid(row=4, column=0, sticky="ew")

        sugerencias = ttk.Frame(self.ventana, padding=(20, 0, 20, 0))
        sugerencias.grid(row=2, column=0, columnspan=2, sticky="ew")

        self.botones_sugerencia = []
        for texto in SUGERENCIAS:
            boton = ttk.Button(
                sugerencias,
                text=texto,
                bootstyle="info-outline",
                command=lambda t=texto: self.usar_sugerencia(t),
            )
            boton.pack(side="left", padx=(0, 8), pady=5)
            self.botones_sugerencia.append(boton)

        abajo = ttk.Frame(self.ventana, padding=(20, 5, 20, 5))
        abajo.grid(row=3, column=0, columnspan=2, sticky="ew")
        abajo.columnconfigure(0, weight=1)

        self.entrada = ttk.Entry(abajo, font=("Segoe UI", 12))
        self.entrada.grid(row=0, column=0, sticky="ew", ipady=6)
        self.entrada.bind("<Return>", lambda evento: self.enviar())
        self.entrada.focus()

        self.btn_enviar = ttk.Button(
            abajo, text="Enviar  ➤", command=self.enviar, bootstyle="primary"
        )
        self.btn_enviar.grid(row=0, column=1, padx=(10, 0), ipady=4)

        estado = ttk.Frame(self.ventana, padding=(20, 0, 20, 12))
        estado.grid(row=4, column=0, columnspan=2, sticky="ew")
        estado.columnconfigure(1, weight=1)

        self.lbl_estado = ttk.Label(estado, text="Listo para cocinar 🍳", bootstyle="secondary")
        self.lbl_estado.grid(row=0, column=0, sticky="w")

        self.carga = ttk.Progressbar(estado, mode="indeterminate", bootstyle="info-striped")
        self.carga.grid(row=0, column=1, sticky="ew", padx=(15, 0))
        self.carga.grid_remove()

    def _escribir(self, texto, tag="texto"):
        self.chat.configure(state="normal")
        self.chat.insert("end", texto, tag)
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def _mensaje_bienvenida(self):
        self._escribir("Chef Remy\n", "chef")
        self._escribir(
            "¡Hola! Soy el Chef Remy 👨‍🍳 Pregúntame lo que quieras de cocina: "
            "recetas, trucos, qué hacer con lo que tengas en el refri...\n\n"
        )

    def _set_ocupado(self, valor, texto="Listo para cocinar 🍳"):
        self.ocupado = valor
        estado = "disabled" if valor else "normal"

        self.entrada.configure(state=estado)
        self.btn_enviar.configure(state=estado)
        for boton in self.botones_sugerencia:
            boton.configure(state=estado)

        self.lbl_estado.configure(text=texto)

        if valor:
            self.carga.grid()
            self.carga.start(12)
        else:
            self.carga.stop()
            self.carga.grid_remove()
            self.entrada.focus()

    def usar_sugerencia(self, texto):
        self.entrada.delete(0, "end")
        self.entrada.insert(0, texto)
        self.enviar()

    def enviar(self):
        if self.ocupado:
            return

        pregunta = self.entrada.get().strip()

        if not pregunta:
            self.lbl_estado.configure(text="Escribe algo primero 😅")
            return

        self.entrada.delete(0, "end")

        self.mensajes.append({"role": "user", "content": pregunta})
        self.preguntas.append(pregunta)
        self._actualizar_lista()

        self._escribir("Tú\n", "tu")
        self._escribir(pregunta + "\n\n")

        self._set_ocupado(True, "El chef está pensando... 🍳")
        self._llamar_llm(list(self.mensajes), "respuesta")

    def _llamar_llm(self, mensajes, tipo):
        
        def trabajo():
            try:
                respuesta = ollama.chat(model=MODELO, messages=mensajes)
                self.cola.put((tipo, respuesta["message"]["content"], None))
            except Exception as error:
                self.cola.put((tipo, None, error))

        threading.Thread(target=trabajo, daemon=True).start()

    def _revisar_cola(self):
        try:
            while True:
                tipo, contenido, error = self.cola.get_nowait()
                self._procesar(tipo, contenido, error)
        except queue.Empty:
            pass

        self.ventana.after(100, self._revisar_cola)

    def _procesar(self, tipo, contenido, error):
        if tipo == "respuesta":
            self._procesar_respuesta(contenido, error)
        else:
            self._procesar_resumen(contenido, error)

    def _procesar_respuesta(self, contenido, error):
        if error is not None:
            
            self.mensajes.pop()
            self.preguntas.pop()
            self._actualizar_lista()

            self._escribir("Ups, no pude conectarme con el chef 😢\n", "error")
            self._escribir(self._explicar_error(error) + "\n\n", "aviso")
            self._set_ocupado(False, "Hubo un error")
            return

        self.mensajes.append({"role": "assistant", "content": contenido})

        self._escribir("Chef Remy\n", "chef")
        self._escribir(contenido.strip() + "\n\n")
        self._set_ocupado(False)

    def _explicar_error(self, error):
        texto = str(error).lower()

        if "not found" in texto:
            return f"Parece que falta el modelo. Escribe en la terminal: ollama pull {MODELO}"

        return "Revisa que Ollama esté abierto y vuelve a intentar."

    def _actualizar_lista(self):
        self.lista.delete(0, "end")

        for i, pregunta in enumerate(self.preguntas, start=1):
            corta = pregunta if len(pregunta) <= 40 else pregunta[:37] + "..."
            self.lista.insert("end", f"{i}. {corta}")

        total = len(self.preguntas)
        if total == 0:
            self.lbl_contador.configure(text="Aún no preguntas nada")
        elif total == 1:
            self.lbl_contador.configure(text="1 pregunta")
        else:
            self.lbl_contador.configure(text=f"{total} preguntas")

    def pedir_resumen(self):
        if self.ocupado:
            return

        if not self.preguntas:
            messagebox.showinfo("Resumen", "Todavía no hay nada que resumir, ¡pregúntale algo al chef primero!")
            return

        
        peticion = self.mensajes + [{
            "role": "user",
            "content": (
                "Hazme un resumen muy breve de lo que hemos platicado, en máximo "
                "5 viñetas cortas. Solo con lo que ya se dijo, sin agregar nada nuevo."
            ),
        }]

        self._set_ocupado(True, "Preparando tu resumen... 📝")
        self._llamar_llm(peticion, "resumen")

    def _procesar_resumen(self, contenido, error):
        self._set_ocupado(False)

        if error is not None:
            
            texto = "No pude pedirle el resumen al chef, pero esto fue lo que preguntaste:\n\n"
            texto += "\n".join(f"• {p}" for p in self.preguntas)
        else:
            texto = contenido.strip()

        self._mostrar_resumen(texto)

    def _mostrar_resumen(self, texto):
        popup = ttk.Toplevel(title="Resumen de tu historial", size=(520, 420))
        popup.place_window_center()

        ttk.Label(
            popup, text="📝 Resumen de tu historial", font=("Segoe UI", 16, "bold"), bootstyle="success"
        ).pack(pady=(15, 5))

        ttk.Label(
            popup, text=f"Preguntas hechas: {len(self.preguntas)}", bootstyle="secondary"
        ).pack()

        caja = tk.Text(
            popup,
            wrap="word",
            font=("Segoe UI", 11),
            bg=self.colores.inputbg,
            fg=self.colores.inputfg,
            relief="flat",
            padx=15,
            pady=15,
        )
        caja.pack(fill="both", expand=True, padx=20, pady=15)
        caja.insert("1.0", texto)
        caja.configure(state="disabled")

        ttk.Button(popup, text="Cerrar", command=popup.destroy, bootstyle="secondary").pack(pady=(0, 15))

    def limpiar(self):
        if self.ocupado:
            return

        if not messagebox.askyesno("Limpiar chat", "¿Seguro? Se borra toda la conversación."):
            return

        self.mensajes = [{"role": "system", "content": mensaje_sistema}]
        self.preguntas = []
        self._actualizar_lista()

        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.configure(state="disabled")

        self._mensaje_bienvenida()
        self.lbl_estado.configure(text="Chat limpio, ¡a cocinar! 🍳")


# ARRANCA AQUi

if __name__ == "__main__":
    ventana = ttk.Window(
        title="Chef Virtual",
        themename="vapor",
        size=(1050, 720),
        minsize=(800, 550),
    )
    ChefApp(ventana)
    ventana.mainloop()
