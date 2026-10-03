CATEGORIAS = ["sesgo", "privacidad", "transparencia", "seguridad", "responsabilidad", "otro"]
NIVELES = ["bajo", "medio", "alto", "crítico"]

COLORES = {"bajo": "#2bff88", "medio": "#ffd43b", "alto": "#ff9f43", "crítico": "#ff3b5c"}


def nivel(puntaje):
    if puntaje >= 17:
        return "crítico"
    if puntaje >= 10:
        return "alto"
    if puntaje >= 5:
        return "medio"
    return "bajo"


def contar_por_nivel(riesgos, campo="puntaje"):
    cuentas = {}
    for nombre in NIVELES:
        cuentas[nombre] = 0

    for riesgo in riesgos:
        cuentas[nivel(riesgo[campo])] += 1

    return cuentas


def resumen(riesgos):
    total = len(riesgos)
    if total == 0:
        return {"total": 0, "promedio_antes": 0, "promedio_despues": 0, "criticos_antes": 0, "criticos_despues": 0}

    suma_antes = 0
    suma_despues = 0
    for riesgo in riesgos:
        suma_antes += riesgo["puntaje"]
        suma_despues += riesgo["puntaje_residual"]

    return {
        "total": total,
        "promedio_antes": round(suma_antes / total, 1),
        "promedio_despues": round(suma_despues / total, 1),
        "criticos_antes": contar_por_nivel(riesgos, "puntaje")["crítico"],
        "criticos_despues": contar_por_nivel(riesgos, "puntaje_residual")["crítico"],
    }
