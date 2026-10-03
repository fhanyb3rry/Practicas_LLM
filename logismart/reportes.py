import csv
import json
from datetime import datetime

from bson import ObjectId
from fpdf import FPDF

import base_datos
import riesgos

TITULOS = {
    "accesos": "Bitácora de accesos",
    "incidentes": "Incidentes",
    "riesgos_eticos": "Riesgos éticos",
    "camiones": "Camiones",
}

# clave, encabezado, ancho relativo en el pdf
COLUMNAS = {
    "accesos": [("fecha", "Fecha", 3), ("camion_id", "Camión", 2), ("placa", "Placa", 2),
                ("resultado", "Resultado", 4), ("semaforo", "Semáforo", 2), ("motivo", "Motivo", 8),
                ("operador", "Operador", 2)],
    "incidentes": [("fecha", "Fecha", 3), ("estado", "Estado", 2), ("categoria", "Categoría", 3),
                   ("prioridad", "Prioridad", 2), ("asunto", "Asunto", 5), ("remitente", "Remitente", 4),
                   ("revision", "Revisión humana", 2), ("resumen", "Resumen", 5)],
    "riesgos_eticos": [("modulo", "Módulo", 3), ("descripcion", "Riesgo", 6), ("categoria", "Categoría", 3),
                       ("probabilidad", "Prob.", 1), ("impacto", "Impacto", 1), ("puntaje", "Puntaje", 1),
                       ("puntaje_residual", "Residual", 1), ("nivel", "Nivel", 2), ("mitigacion", "Mitigación", 7)],
    "camiones": [("camion_id", "ID", 2), ("placa", "Placa", 2), ("empresa", "Empresa", 4),
                 ("autorizacion", "Autorizado", 2), ("conductor", "Conductor", 3),
                 ("cert_vence", "Certificación vence", 3)],
}

CAMBIOS_PDF = {"→": "->", "∧": "y", "∨": "o", "≥": ">=", "…": "...", "•": "-", "✅": "", "⚠️": "!", "⚠": "!"}


def texto_fecha(fecha, con_hora=True):
    if fecha is None:
        return ""
    if con_hora:
        fecha = base_datos.a_local(fecha)
        return fecha.strftime("%d/%m/%Y %H:%M")
    return fecha.strftime("%d/%m/%Y")


def si_no(valor):
    if valor:
        return "Sí"
    return "No"


def fila(coleccion, doc):
    if coleccion == "accesos":
        return {
            "fecha": texto_fecha(doc.get("creado")), "camion_id": str(doc.get("camion_id") or ""),
            "placa": str(doc.get("placa") or ""), "resultado": doc.get("resultado", ""),
            "semaforo": doc.get("semaforo", ""), "motivo": " ".join(doc.get("motivo", [])),
            "operador": doc.get("operador", ""),
        }

    if coleccion == "incidentes":
        correo = doc.get("correo_original", {})
        clasif = doc.get("clasificacion", {})
        return {
            "fecha": texto_fecha(doc.get("creado")), "estado": doc.get("estado", ""),
            "categoria": clasif.get("categoria", ""), "prioridad": clasif.get("prioridad", ""),
            "asunto": correo.get("asunto", ""), "remitente": correo.get("remitente", ""),
            "revision": si_no(clasif.get("requiere_revision_humana")), "resumen": clasif.get("resumen", ""),
        }

    if coleccion == "riesgos_eticos":
        return {
            "modulo": doc.get("modulo", ""), "descripcion": doc.get("descripcion", ""),
            "categoria": doc.get("categoria", ""), "probabilidad": doc.get("probabilidad", ""),
            "impacto": doc.get("impacto", ""), "puntaje": doc.get("puntaje", ""),
            "puntaje_residual": doc.get("puntaje_residual", ""),
            "nivel": riesgos.nivel(doc.get("puntaje", 0)), "mitigacion": doc.get("mitigacion", ""),
        }

    return {
        "camion_id": doc.get("camion_id", ""), "placa": doc.get("placa", ""), "empresa": doc.get("empresa", ""),
        "autorizacion": si_no(doc.get("autorizacion")), "conductor": doc.get("conductor", ""),
        "cert_vence": texto_fecha(doc.get("cert_vence"), False),
    }


def filas(coleccion, docs):
    resultado = []
    for doc in docs:
        resultado.append(fila(coleccion, doc))
    return resultado


def limpiar(valor):
    # para el json: los ObjectId y las fechas no se pueden escribir tal cual
    if isinstance(valor, ObjectId):
        return str(valor)
    if isinstance(valor, datetime):
        return valor.isoformat()
    if isinstance(valor, dict):
        nuevo = {}
        for clave in valor:
            nuevo[clave] = limpiar(valor[clave])
        return nuevo
    if isinstance(valor, list):
        nuevo = []
        for elemento in valor:
            nuevo.append(limpiar(elemento))
        return nuevo
    return valor


def exportar_csv(ruta, coleccion, docs):
    columnas = COLUMNAS[coleccion]
    # utf-8-sig para que Excel respete los acentos
    with open(ruta, "w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.writer(archivo)
        encabezados = []
        for clave, titulo, ancho in columnas:
            encabezados.append(titulo)
        escritor.writerow(encabezados)

        for datos in filas(coleccion, docs):
            linea = []
            for clave, titulo, ancho in columnas:
                linea.append(datos[clave])
            escritor.writerow(linea)


def exportar_json(ruta, datos, indicadores=None):
    contenido = {"generado": datetime.now().isoformat(timespec="seconds"), "indicadores": indicadores,
                 "colecciones": limpiar(datos)}
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(contenido, archivo, ensure_ascii=False, indent=2)


def para_pdf(texto):
    texto = str(texto)
    for caracter in CAMBIOS_PDF:
        texto = texto.replace(caracter, CAMBIOS_PDF[caracter])
    return texto.encode("latin-1", "replace").decode("latin-1")


def exportar_pdf(ruta, datos, indicadores=None, desde=None, hasta=None):
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 10, para_pdf("LogiSmart - Reporte"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, para_pdf("Generado el " + datetime.now().strftime("%d/%m/%Y %H:%M")),
             new_x="LMARGIN", new_y="NEXT")

    if desde is not None and hasta is not None:
        pdf.cell(0, 6, para_pdf("Periodo: " + texto_fecha(desde, False) + " al " + texto_fecha(hasta, False)),
                 new_x="LMARGIN", new_y="NEXT")

    if indicadores is not None:
        resumen = ("Camiones atendidos: " + str(indicadores["camiones_atendidos"]) +
                   "   |   Incidentes abiertos: " + str(indicadores["incidentes_abiertos"]) +
                   "   |   Riesgos críticos: " + str(indicadores["riesgos_criticos"]))
        pdf.cell(0, 6, para_pdf(resumen), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    for coleccion in datos:
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, para_pdf(TITULOS[coleccion] + " (" + str(len(datos[coleccion])) + ")"),
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8)

        if len(datos[coleccion]) == 0:
            pdf.cell(0, 6, "Sin registros.", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)
            continue

        columnas = COLUMNAS[coleccion]
        anchos = []
        for clave, titulo, ancho in columnas:
            anchos.append(ancho)

        with pdf.table(col_widths=anchos, line_height=4.5, text_align="LEFT") as tabla:
            encabezado = tabla.row()
            for clave, titulo, ancho in columnas:
                encabezado.cell(para_pdf(titulo))

            for datos_fila in filas(coleccion, datos[coleccion]):
                renglon = tabla.row()
                for clave, titulo, ancho in columnas:
                    renglon.cell(para_pdf(datos_fila[clave]))
        pdf.ln(5)

    pdf.output(ruta)
