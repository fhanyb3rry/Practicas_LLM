import json
from datetime import datetime
from pathlib import Path

import asistente
import clasificador
import reglas

RUTA = Path(__file__).resolve().parent / "configuracion.json"

PREDETERMINADA = {
    "modelo": "llama3.2",
    "intentos_llm": 2,
    "hora_inicio": "10:00",
    "hora_fin": "16:00",
    "dias_por_vencer": 30,
    "simulacion_correo": True,
    "correo_soporte": "soporte@logismart.example",
    "operador": "operador",
}

valores = dict(PREDETERMINADA)


def a_hora(texto):
    try:
        return datetime.strptime(texto.strip(), "%H:%M").time()
    except ValueError:
        raise ValueError("La hora '" + texto + "' no es válida, escríbela como HH:MM, por ejemplo 10:00.")


def revisar(nuevos):
    # regresa los valores ya limpios o lanza ValueError con un mensaje para el usuario
    limpios = dict(valores)

    for campo in nuevos:
        if campo in PREDETERMINADA:
            limpios[campo] = nuevos[campo]

    limpios["modelo"] = str(limpios["modelo"]).strip()
    if limpios["modelo"] == "":
        raise ValueError("El nombre del modelo no puede estar vacío.")

    limpios["operador"] = str(limpios["operador"]).strip()
    if limpios["operador"] == "":
        raise ValueError("Escribe el nombre del operador.")

    inicio = a_hora(str(limpios["hora_inicio"]))
    fin = a_hora(str(limpios["hora_fin"]))
    if inicio >= fin:
        raise ValueError("La hora de inicio tiene que ser antes que la hora de fin.")
    limpios["hora_inicio"] = inicio.strftime("%H:%M")
    limpios["hora_fin"] = fin.strftime("%H:%M")

    try:
        limpios["dias_por_vencer"] = int(limpios["dias_por_vencer"])
        limpios["intentos_llm"] = int(limpios["intentos_llm"])
    except (ValueError, TypeError):
        raise ValueError("Los días y los intentos deben ser números enteros.")

    if limpios["dias_por_vencer"] < 1 or limpios["dias_por_vencer"] > 365:
        raise ValueError("Los días para 'por vencer' deben estar entre 1 y 365.")
    if limpios["intentos_llm"] < 1 or limpios["intentos_llm"] > 5:
        raise ValueError("Los intentos del LLM deben estar entre 1 y 5.")

    limpios["simulacion_correo"] = bool(limpios["simulacion_correo"])

    if "@" not in str(limpios["correo_soporte"]):
        raise ValueError("El correo de soporte no parece un correo válido.")
    limpios["correo_soporte"] = str(limpios["correo_soporte"]).strip()

    return limpios


def aplicar():
    # pasa lo configurado a los módulos que lo usan
    reglas.HORA_INICIO = a_hora(valores["hora_inicio"])
    reglas.HORA_FIN = a_hora(valores["hora_fin"])
    reglas.DIAS_POR_VENCER = valores["dias_por_vencer"]
    clasificador.MODELO = valores["modelo"]
    clasificador.MAX_INTENTOS = valores["intentos_llm"]
    asistente.MODELO = valores["modelo"]


def cargar(ruta=None):
    if ruta is None:
        ruta = RUTA

    if ruta.exists():
        try:
            guardados = json.loads(ruta.read_text(encoding="utf-8"))
            valores.update(revisar(guardados))
        except (ValueError, OSError):
            # si el archivo está dañado nos quedamos con lo de siempre
            valores.clear()
            valores.update(PREDETERMINADA)

    aplicar()
    return valores


def guardar(nuevos, ruta=None):
    if ruta is None:
        ruta = RUTA

    limpios = revisar(nuevos)
    valores.update(limpios)
    aplicar()
    ruta.write_text(json.dumps(valores, indent=2, ensure_ascii=False), encoding="utf-8")
    return valores


def restaurar(ruta=None):
    return guardar(PREDETERMINADA, ruta)
