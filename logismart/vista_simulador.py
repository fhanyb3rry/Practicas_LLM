import tkinter as tk

import ttkbootstrap as ttk

import reglas
from vista_acceso import COLORES

NOMBRES = ["P", "Q", "R", "S", "H", "W"]

DESCRIPCIONES = {
    "P": "Tiene autorización previa",
    "Q": "El peso excede el límite",
    "R": "Lleva materiales peligrosos",
    "S": "Conductor con certificación vigente",
    "H": "Está dentro del horario permitido",
    "W": "La certificación vence pronto",
}

# (letra, nombre, estilo cuando vale V)
RESULTADOS = [
    ("A", "Acceso estándar", "success"),
    ("E", "Inspección especial", "warning"),
    ("B", "Bloqueo por horario", "danger"),
    ("L", "Alerta de renovación", "warning"),
    ("acceso_final", "Acceso final", "success"),
]


def vf(valor):
    if valor:
        return "V"
    return "F"


class VistaSimulador:

    def __init__(self, padre, app):
        self.colores = app.colores
        self.marco = ttk.Frame(padre, padding=20)

        self.variables = {}
        self.insignias = {}
        self.filas_tabla = {}

        arriba = ttk.Frame(self.marco)
        arriba.pack(fill="x")
        arriba.columnconfigure(0, weight=1, uniform="col")
        arriba.columnconfigure(1, weight=1, uniform="col")

        izquierda = ttk.Frame(arriba)
        izquierda.grid(row=0, column=0, sticky="nw", padx=(0, 20))
        derecha = ttk.Frame(arriba)
        derecha.grid(row=0, column=1, sticky="nw")

        self._armar_interruptores(izquierda)
        self._armar_resultados(derecha)
        self._armar_tabla()
        self.actualizar()

    def _armar_interruptores(self, padre):
        ttk.Label(padre, text="Mueve los interruptores", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 8))

        valores_iniciales = {"P": True, "Q": False, "R": False, "S": True, "H": True, "W": False}

        for nombre in NOMBRES:
            self.variables[nombre] = tk.BooleanVar(value=valores_iniciales[nombre])
            check = ttk.Checkbutton(padre, text=nombre + "  " + DESCRIPCIONES[nombre],
                                    variable=self.variables[nombre], command=self.actualizar,
                                    bootstyle="round-toggle")
            check.pack(anchor="w", pady=4)
            if nombre == "W":
                self.check_w = check

        self.lbl_aviso = ttk.Label(padre, text="", bootstyle="secondary")
        self.lbl_aviso.pack(anchor="w", pady=(8, 0))

    def _armar_resultados(self, padre):
        ttk.Label(padre, text="Lo que sale", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 8))

        for letra, nombre, estilo in RESULTADOS:
            fila = ttk.Frame(padre)
            fila.pack(fill="x", pady=3)
            ttk.Label(fila, text=nombre, width=22).pack(side="left")
            insignia = ttk.Label(fila, text="F", width=3, anchor="center", font=("Segoe UI", 12, "bold"))
            insignia.pack(side="left")
            self.insignias[letra] = insignia

        self.lbl_resultado = ttk.Label(padre, text="", font=("Segoe UI", 20, "bold"))
        self.lbl_resultado.pack(anchor="w", pady=(14, 4))

        self.motivo = ttk.Label(padre, text="", wraplength=430, justify="left", bootstyle="secondary")
        self.motivo.pack(anchor="w")

    def _armar_tabla(self):
        ttk.Label(self.marco, text="Tabla de verdad completa (la fila de ahorita está marcada)",
                  font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(18, 6))

        zona = ttk.Frame(self.marco)
        zona.pack(fill="both", expand=True)

        columnas = NOMBRES + ["A", "E", "B", "L", "Final", "Resultado"]
        self.tabla = ttk.Treeview(zona, columns=columnas, show="headings", bootstyle="info", height=8)
        for columna in columnas:
            self.tabla.heading(columna, text=columna)
            self.tabla.column(columna, width=45, anchor="center")
        self.tabla.column("Resultado", width=220, anchor="w")
        self.tabla.pack(side="left", fill="both", expand=True)

        barra = ttk.Scrollbar(zona, command=self.tabla.yview)
        barra.pack(side="right", fill="y")
        self.tabla.configure(yscrollcommand=barra.set)

        for fila in reglas.tabla_completa():
            valores = []
            for nombre in NOMBRES:
                valores.append(vf(fila[nombre]))
            valores += [vf(fila["A"]), vf(fila["E"]), vf(fila["B"]), vf(fila["L"]),
                        vf(fila["acceso_final"]), fila["resultado"]]

            item = self.tabla.insert("", "end", values=valores)
            clave = (fila["P"], fila["Q"], fila["R"], fila["S"], fila["H"], fila["W"])
            self.filas_tabla[clave] = item

    def actualizar(self):
        # sin vigencia no puede estar por vencer
        if not self.variables["S"].get():
            self.variables["W"].set(False)
            self.check_w.configure(state="disabled")
            self.lbl_aviso.configure(text="W se apaga porque sin certificación vigente no puede estar por vencer.")
        else:
            self.check_w.configure(state="normal")
            self.lbl_aviso.configure(text="")

        P = self.variables["P"].get()
        Q = self.variables["Q"].get()
        R = self.variables["R"].get()
        S = self.variables["S"].get()
        H = self.variables["H"].get()
        W = self.variables["W"].get()

        decision = reglas.decidir(P, Q, R, S, H, W)

        for letra, nombre, estilo in RESULTADOS:
            valor = decision[letra]
            if valor:
                self.insignias[letra].configure(text="V", bootstyle=estilo)
            else:
                self.insignias[letra].configure(text="F", bootstyle="secondary")

        self.lbl_resultado.configure(text=decision["resultado"], foreground=COLORES[decision["semaforo"]])
        self.motivo.configure(text=" ".join(decision["motivo"]))

        item = self.filas_tabla[(P, Q, R, S, H, W)]
        self.tabla.selection_set(item)
        self.tabla.see(item)
