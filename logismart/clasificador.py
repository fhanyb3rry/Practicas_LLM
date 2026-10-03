import json
import re
import time
from typing import Literal, Optional

import ollama
from pydantic import BaseModel, ValidationError

MODELO = "llama3.2"
MAX_INTENTOS = 2

CATEGORIAS = {
    "materiales_peligrosos": ["peligroso", "derrame", "fuga", "quimico", "inflamable", "toxico", "corrosivo"],
    "sobrepeso": ["sobrepeso", "excede", "bascula", "exceso de peso", "sobrecarga"],
    "acceso_no_autorizado": ["sin autorizacion", "no autorizado", "acceso denegado", "barrera", "intruso"],
    "falla_hardware": ["camara", "sensor", "lector", "rfid", "no enciende", "apagado", "danado", "falla electrica"],
    "falla_software": ["sistema", "error", "pantalla", "caido", "no carga", "lento", "software", "aplicacion"],
    "somnolencia_conductor": ["somnolencia", "dormido", "cansancio", "fatiga", "sueno"],
}

PALABRAS_URGENTES = ["urgente", "emergencia", "accidente", "incendio", "herido", "critico", "inmediato"]

PRIORIDAD_BASE = {
    "materiales_peligrosos": "critica",
    "somnolencia_conductor": "alta",
    "acceso_no_autorizado": "alta",
    "sobrepeso": "media",
    "falla_hardware": "media",
    "falla_software": "baja",
    "otro": "baja",
}

ORDEN_PRIORIDAD = ["baja", "media", "alta", "critica"]


# lo que el LLM tiene que devolver y si trae algo distinto pydantic lo rechaza
class Entidades(BaseModel):
    model_config = {"extra": "forbid"}

    placa: Optional[str] = None
    camion_id: Optional[str] = None
    peso_kg: Optional[float] = None
    ubicacion: Optional[str] = None


class RespuestaLLM(BaseModel):
    model_config = {"extra": "forbid"}

    categoria: Literal["materiales_peligrosos", "sobrepeso", "acceso_no_autorizado",
                       "falla_hardware", "falla_software", "somnolencia_conductor", "otro"]
    prioridad: Literal["baja", "media", "alta", "critica"]
    entidades: Entidades
    resumen: str


MENSAJE_SISTEMA = """
Eres un clasificador de incidentes de un centro logístico. Recibes un correo
y respondes SOLO con un JSON válido, sin texto antes ni después.

El JSON debe tener exactamente estos campos:
{
  "categoria": una de: materiales_peligrosos, sobrepeso, acceso_no_autorizado,
               falla_hardware, falla_software, somnolencia_conductor, otro,
  "prioridad": una de: baja, media, alta, critica,
  "entidades": {"placa": texto o null, "camion_id": texto o null,
                "peso_kg": número o null, "ubicacion": texto o null},
  "resumen": una frase corta en español
}

Reglas:
- Si un dato no aparece en el correo, pon null. No inventes nada.
- Si hay riesgo para personas o carga peligrosa, la prioridad es critica.
- Si el correo es una duda o un saludo, la categoria es otro.
"""


def normalizar(texto):
    tabla = str.maketrans("áéíóúüñ", "aeiouun")
    return texto.lower().translate(tabla)


def clasificar_reglas(asunto, cuerpo):
    texto = normalizar(asunto + " " + cuerpo)

    mejor_categoria = "otro"
    mejores_palabras = []

    for categoria in CATEGORIAS:
        encontradas = []
        for palabra in CATEGORIAS[categoria]:
            if palabra in texto:
                encontradas.append(palabra)
        # si empatan se queda la primera y materiales peligrosos va primero
        if len(encontradas) > len(mejores_palabras):
            mejor_categoria = categoria
            mejores_palabras = encontradas

    prioridad = PRIORIDAD_BASE[mejor_categoria]

    urgentes = []
    for palabra in PALABRAS_URGENTES:
        if palabra in texto:
            urgentes.append(palabra)

    if len(urgentes) > 0:
        posicion = ORDEN_PRIORIDAD.index(prioridad) + 1
        if posicion > 3:
            posicion = 3
        prioridad = ORDEN_PRIORIDAD[posicion]

    return {
        "categoria": mejor_categoria,
        "prioridad": prioridad,
        "palabras_clave": mejores_palabras + urgentes,
    }


def extraer_datos(asunto, cuerpo):
    texto = asunto + "\n" + cuerpo

    placa = None
    buscar = re.search(r"\b[A-Z0-9]{2,3}-\d{2,3}-[A-Z0-9]{1,2}\b", texto.upper())
    if buscar:
        placa = buscar.group(0)

    camion_id = None
    buscar = re.search(r"\bCAM-\d+\b", texto.upper())
    if buscar:
        camion_id = buscar.group(0)

    peso_kg = None
    buscar = re.search(r"(\d+(?:[.,]\d+)?)\s*(toneladas|tonelada|ton|t|kg)\b", texto.lower())
    if buscar:
        valor = float(buscar.group(1).replace(",", "."))
        if buscar.group(2) == "kg":
            peso_kg = valor
        else:
            peso_kg = valor * 1000

    ubicacion = None
    buscar = re.search(r"\b(anden|puerta|muelle|caseta|dock)\s+([a-z0-9]+)", normalizar(texto))
    if buscar:
        ubicacion = buscar.group(1) + " " + buscar.group(2)

    return {"placa": placa, "camion_id": camion_id, "peso_kg": peso_kg, "ubicacion": ubicacion}


def clasificar_llm(asunto, cuerpo, chat=None, modelo=MODELO, intentos=MAX_INTENTOS):
    
    if chat is None:
        chat = ollama.chat

    correo = "Asunto: " + asunto + "\n\n" + cuerpo
    mensajes = [
        {"role": "system", "content": MENSAJE_SISTEMA},
        {"role": "user", "content": correo},
    ]

    resultado = {"ok": False, "datos": None, "error": "", "prompt": correo,
                 "respuesta": "", "modelo": modelo, "intentos": 0, "latencia_ms": 0.0}

    inicio = time.perf_counter()

    for intento in range(1, intentos + 1):
        resultado["intentos"] = intento

        try:
            respuesta = chat(model=modelo, messages=mensajes, format="json", options={"temperature": 0})
            texto = respuesta["message"]["content"]
        except Exception as error:
            
            resultado["error"] = "No se pudo conectar con Ollama: " + str(error)
            break

        resultado["respuesta"] = texto

        try:
            datos = json.loads(texto)
            validado = RespuestaLLM.model_validate(datos)
            resultado["ok"] = True
            resultado["datos"] = validado.model_dump()
            resultado["error"] = ""
            break
        except (json.JSONDecodeError, ValidationError):
            resultado["error"] = "El LLM no devolvió un JSON válido"
            mensajes.append({"role": "assistant", "content": texto})
            mensajes.append({"role": "user",
                             "content": "Tu respuesta no cumple el esquema. Responde SOLO con el JSON válido."})

    resultado["latencia_ms"] = (time.perf_counter() - inicio) * 1000
    return resultado


def mayor_prioridad(a, b):
    if ORDEN_PRIORIDAD.index(a) >= ORDEN_PRIORIDAD.index(b):
        return a
    return b


def completar_entidades(entidades, entidades_llm, texto):
   
    texto_mayus = texto.upper()
    texto_normal = normalizar(texto)

    if entidades["placa"] is None and entidades_llm["placa"]:
        if entidades_llm["placa"].upper() in texto_mayus:
            entidades["placa"] = entidades_llm["placa"].upper()

    if entidades["camion_id"] is None and entidades_llm["camion_id"]:
        if entidades_llm["camion_id"].upper() in texto_mayus:
            entidades["camion_id"] = entidades_llm["camion_id"].upper()

    if entidades["ubicacion"] is None and entidades_llm["ubicacion"]:
        if normalizar(entidades_llm["ubicacion"]) in texto_normal:
            entidades["ubicacion"] = normalizar(entidades_llm["ubicacion"])

    return entidades


def clasificar_hibrido(asunto, cuerpo, chat=None, modelo=MODELO):
    reglas = clasificar_reglas(asunto, cuerpo)
    entidades = extraer_datos(asunto, cuerpo)
    llm = clasificar_llm(asunto, cuerpo, chat, modelo)

    resultado = {
        "categoria": reglas["categoria"],
        "prioridad": reglas["prioridad"],
        "entidades": entidades,
        "resumen": asunto.strip()[:120],
        "metodo": "reglas",
        "requiere_revision_humana": False,
        "coincidio_con_reglas": None,
        "palabras_clave": reglas["palabras_clave"],
        "reglas": reglas,
        "llm": llm,
    }

    if llm["ok"]:
        datos = llm["datos"]
        resultado["metodo"] = "hibrido"
        resultado["resumen"] = datos["resumen"]
        resultado["entidades"] = completar_entidades(entidades, datos["entidades"], asunto + " " + cuerpo)

        coinciden = datos["categoria"] == reglas["categoria"] and datos["prioridad"] == reglas["prioridad"]
        resultado["coincidio_con_reglas"] = coinciden

        if not coinciden:
           
            resultado["requiere_revision_humana"] = True
            resultado["prioridad"] = mayor_prioridad(datos["prioridad"], reglas["prioridad"])

            if ORDEN_PRIORIDAD.index(datos["prioridad"]) > ORDEN_PRIORIDAD.index(reglas["prioridad"]):
                resultado["categoria"] = datos["categoria"]
            else:
                resultado["categoria"] = reglas["categoria"]

    if resultado["categoria"] == "otro":
        resultado["requiere_revision_humana"] = True

    return resultado
