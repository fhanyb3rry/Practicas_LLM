import sys
import time

import clasificador
from correos_etiquetados import CORREOS

NOMBRES_CATEGORIAS = ["materiales_peligrosos", "sobrepeso", "acceso_no_autorizado",
                      "falla_hardware", "falla_software", "somnolencia_conductor", "otro"]

METODOS = ["reglas", "llm", "hibrido"]


def predecir(metodo, correo, chat=None):
    # regresa categoria, prioridad, latencia en ms
    asunto = correo["asunto"]
    cuerpo = correo["cuerpo"]

    if metodo == "reglas":
        inicio = time.perf_counter()
        r = clasificador.clasificar_reglas(asunto, cuerpo)
        latencia = (time.perf_counter() - inicio) * 1000
        return r["categoria"], r["prioridad"], latencia

    if metodo == "llm":
        r = clasificador.clasificar_llm(asunto, cuerpo, chat)
        if r["ok"]:
            return r["datos"]["categoria"], r["datos"]["prioridad"], r["latencia_ms"]
        return "sin_respuesta", "sin_respuesta", r["latencia_ms"]

    inicio = time.perf_counter()
    r = clasificador.clasificar_hibrido(asunto, cuerpo, chat)
    latencia = (time.perf_counter() - inicio) * 1000
    return r["categoria"], r["prioridad"], latencia


def evaluar(metodo, correos=None, chat=None):
    if correos is None:
        correos = CORREOS

    aciertos_categoria = 0
    aciertos_prioridad = 0
    total_latencia = 0.0
    errores = []

    
    matriz = {}
    for real in NOMBRES_CATEGORIAS:
        matriz[real] = {}
        for predicha in NOMBRES_CATEGORIAS + ["sin_respuesta"]:
            matriz[real][predicha] = 0

    for correo in correos:
        categoria, prioridad, latencia = predecir(metodo, correo, chat)

        matriz[correo["categoria"]][categoria] += 1
        total_latencia = total_latencia + latencia

        if categoria == correo["categoria"]:
            aciertos_categoria += 1
        else:
            errores.append({"asunto": correo["asunto"], "real": correo["categoria"], "predicha": categoria})

        if prioridad == correo["prioridad"]:
            aciertos_prioridad += 1

    total = len(correos)
    return {
        "metodo": metodo,
        "total": total,
        "exactitud_categoria": aciertos_categoria / total,
        "exactitud_prioridad": aciertos_prioridad / total,
        "latencia_promedio_ms": total_latencia / total,
        "matriz": matriz,
        "errores": errores,
    }


def imprimir_resultado(r):
    print("=" * 60)
    print("Método:", r["metodo"], "| correos:", r["total"])
    print("Exactitud categoría: " + str(round(r["exactitud_categoria"] * 100, 1)) + "%")
    print("Exactitud prioridad: " + str(round(r["exactitud_prioridad"] * 100, 1)) + "%")
    print("Latencia promedio: " + str(round(r["latencia_promedio_ms"], 1)) + " ms")

    print("\nMatriz de confusión (filas = real, columnas = predicha)")
    columnas = []
    for nombre in r["matriz"]["otro"]:
        if nombre != "sin_respuesta" or r["metodo"] == "llm":
            columnas.append(nombre)

    encabezado = " " * 24
    for c in columnas:
        encabezado = encabezado + c[:6].ljust(7)
    print(encabezado)
    for real in r["matriz"]:
        fila = real.ljust(24)
        for c in columnas:
            fila = fila + str(r["matriz"][real][c]).ljust(7)
        print(fila)

    if len(r["errores"]) > 0:
        print("\nSe equivocó en:")
        for e in r["errores"]:
            print(" - " + e["asunto"] + "  (real: " + e["real"] + ", predijo: " + e["predicha"] + ")")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    metodos = ["reglas"]
    if "--llm" in sys.argv:
        metodos = METODOS

    for metodo in metodos:
        imprimir_resultado(evaluar(metodo))
