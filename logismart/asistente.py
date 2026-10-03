import re
import time

import ollama

import clasificador
from base_datos import a_local

MODELO = "llama3.2"
SIN_INFORMACION = "No tengo información sobre eso en los registros."

MENSAJE_SISTEMA = """
Eres el asistente del centro de control LogiSmart. Respondes preguntas de los
operadores usando SOLO el contexto numerado que te doy.

Reglas:
- Si la respuesta no está en el contexto, responde exactamente: No tengo información sobre eso en los registros.
- No inventes datos y no uses conocimiento externo.
- Si te preguntan por qué pasó algo, copia el MOTIVO que aparece en el contexto, sin agregar explicaciones nuevas.
- El semáforo solo es un color de aviso, no lo expliques.
- Cita las fuentes con su número, por ejemplo [1].
- Responde en español, corto y claro.
"""


def fecha_texto(fecha):
    fecha = a_local(fecha)
    if fecha is None:
        return "sin fecha"
    return fecha.strftime("%d/%m/%Y %H:%M")


def si_no(valor):
    if valor:
        return "sí"
    return "no"


def texto_camion(doc):
    texto = "Camión " + str(doc.get("camion_id")) + " (placa " + str(doc.get("placa")) + ") "
    texto += "de la empresa " + str(doc.get("empresa")) + ". "
    texto += "Autorización previa: " + si_no(doc.get("autorizacion")) + ". "
    texto += "Conductor: " + str(doc.get("conductor")) + ". "

    vence = doc.get("cert_vence")
    if vence is not None:
        texto += "Su certificación vence el " + vence.strftime("%d/%m/%Y") + "."
    return texto


def texto_acceso(doc):
    texto = "Acceso del " + fecha_texto(doc.get("creado")) + " del camión " + str(doc.get("camion_id"))
    texto += " (placa " + str(doc.get("placa")) + "). "
    texto += "Resultado: " + str(doc.get("resultado")) + " (semáforo " + str(doc.get("semaforo")) + "). "

    motivo = doc.get("motivo")
    if motivo:
        texto += "MOTIVO: " + " ".join(motivo)
    else:
        texto += "Explicación: " + " | ".join(doc.get("explicacion", []))
    return texto


def texto_incidente(doc):
    correo = doc.get("correo_original", {})
    clasif = doc.get("clasificacion", {})

    texto = "Incidente del " + fecha_texto(doc.get("creado")) + ", estado " + str(doc.get("estado")) + ". "
    texto += "Categoría: " + str(clasif.get("categoria")) + ", prioridad: " + str(clasif.get("prioridad")) + ". "
    texto += "Asunto del correo: " + str(correo.get("asunto")) + ". "

    if clasif.get("resumen"):
        texto += "Resumen: " + str(clasif.get("resumen")) + "."
    return texto


def texto_riesgo(doc):
    texto = "Riesgo del módulo " + str(doc.get("modulo")) + ": " + str(doc.get("descripcion")) + ". "
    texto += "Categoría " + str(doc.get("categoria")) + ", puntaje " + str(doc.get("puntaje"))
    texto += " (residual " + str(doc.get("puntaje_residual")) + "). "
    texto += "Mitigación: " + str(doc.get("mitigacion"))
    return texto


def agregar_fuentes(fuentes, coleccion, documentos, hacer_texto):
    for doc in documentos:
        ya_esta = False
        for f in fuentes:
            if f["coleccion"] == coleccion and f["id"] == str(doc["_id"]):
                ya_esta = True
        if not ya_esta:
            fuentes.append({
                "n": len(fuentes) + 1,
                "coleccion": coleccion,
                "id": str(doc["_id"]),
                "texto": hacer_texto(doc),
            })


def buscar_contexto(db, pregunta):
    # primero se consulta la base, el LLM solo ve lo que sale de aquí
    fuentes = []
    texto = clasificador.normalizar(pregunta)
    datos = clasificador.extraer_datos(pregunta, "")

    placa = datos["placa"]
    camion_id = datos["camion_id"]

    if placa is not None or camion_id is not None:
        condiciones = []
        if camion_id is not None:
            condiciones.append({"camion_id": camion_id})
        if placa is not None:
            condiciones.append({"placa": placa})

        camion = None
        if camion_id is not None:
            camion = db.buscar_camion(camion_id)
        if camion is None and placa is not None:
            camion = db.buscar_camion(placa)
        if camion is not None:
            agregar_fuentes(fuentes, "camiones", [camion], texto_camion)

        accesos = db.listar("accesos", {"$or": condiciones}, limite=5)
        agregar_fuentes(fuentes, "accesos", accesos, texto_acceso)

        condiciones_inc = []
        if camion_id is not None:
            condiciones_inc.append({"datos_extraidos.camion_id": camion_id})
        if placa is not None:
            condiciones_inc.append({"datos_extraidos.placa": placa})
        incidentes = db.listar("incidentes", {"$or": condiciones_inc}, limite=3)
        agregar_fuentes(fuentes, "incidentes", incidentes, texto_incidente)

        return fuentes

    if "incidente" in texto or "correo" in texto:
        filtro = {}
        if "abierto" in texto or "pendiente" in texto:
            filtro = {"estado": {"$ne": "cerrado"}}
        agregar_fuentes(fuentes, "incidentes", db.listar("incidentes", filtro, limite=5), texto_incidente)

    if "riesgo" in texto:
        riesgos = db.listar("riesgos_eticos", {}, limite=5, campo_orden="puntaje")
        agregar_fuentes(fuentes, "riesgos_eticos", riesgos, texto_riesgo)

    if "acceso" in texto or "camion" in texto or "inspeccion" in texto:
        agregar_fuentes(fuentes, "accesos", db.listar("accesos", {}, limite=5), texto_acceso)

    return fuentes


def armar_mensajes(fuentes, pregunta, historial):
    contexto = ""
    for f in fuentes:
        contexto += "[" + str(f["n"]) + "] (" + f["coleccion"] + ") " + f["texto"] + "\n"

    mensajes = [{"role": "system", "content": MENSAJE_SISTEMA}]
    mensajes += historial[-6:]
    mensajes.append({"role": "user", "content": "Contexto:\n" + contexto + "\nPregunta: " + pregunta})
    return mensajes


def numeros_citados(respuesta, fuentes):
    validos = []
    for f in fuentes:
        validos.append(f["n"])

    citados = []
    for numero in re.findall(r"\[(\d+)\]", respuesta):
        if int(numero) in validos and int(numero) not in citados:
            citados.append(int(numero))
    return citados


def responder(db, pregunta, historial, chat=None, modelo=MODELO):
    if chat is None:
        chat = ollama.chat

    resultado = {"respuesta": "", "fuentes": [], "uso_llm": False, "error": "",
                 "prompt": "", "modelo": modelo, "latencia_ms": 0.0}

    pregunta = pregunta.strip()
    if pregunta == "":
        resultado["respuesta"] = "Escribe una pregunta primero."
        return resultado

    fuentes = buscar_contexto(db, pregunta)

    # sin datos no se llama al LLM, así no tiene de dónde inventar
    if len(fuentes) == 0:
        resultado["respuesta"] = SIN_INFORMACION
        historial.append({"role": "user", "content": pregunta})
        historial.append({"role": "assistant", "content": SIN_INFORMACION})
        return resultado

    mensajes = armar_mensajes(fuentes, pregunta, historial)
    resultado["prompt"] = mensajes[-1]["content"]

    inicio = time.perf_counter()
    try:
        respuesta = chat(model=modelo, messages=mensajes, options={"temperature": 0})
        texto = respuesta["message"]["content"].strip()
        resultado["uso_llm"] = True
    except Exception as error:
        resultado["error"] = str(error)
        texto = "No pude consultar al LLM, pero esto encontré en los registros:\n"
        for f in fuentes:
            texto += "[" + str(f["n"]) + "] " + f["texto"] + "\n"
        resultado["respuesta"] = texto.strip()
        resultado["fuentes"] = fuentes
        resultado["latencia_ms"] = (time.perf_counter() - inicio) * 1000
        return resultado

    resultado["latencia_ms"] = (time.perf_counter() - inicio) * 1000

    if "no tengo informacion" in clasificador.normalizar(texto):
        resultado["respuesta"] = texto
        historial.append({"role": "user", "content": pregunta})
        historial.append({"role": "assistant", "content": texto})
        return resultado

    citados = numeros_citados(texto, fuentes)
    usadas = []
    for f in fuentes:
        if len(citados) == 0 or f["n"] in citados:
            usadas.append(f)

    resultado["respuesta"] = texto
    resultado["fuentes"] = usadas

    historial.append({"role": "user", "content": pregunta})
    historial.append({"role": "assistant", "content": texto})
    return resultado


def texto_fuentes(fuentes):
    # las fuentes las escribe el código, no el LLM
    lineas = []
    for f in fuentes:
        lineas.append("[" + str(f["n"]) + "] " + f["coleccion"] + " · " + f["id"][-6:])
    return "\n".join(lineas)
