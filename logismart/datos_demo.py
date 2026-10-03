import os
import sys
from datetime import date, datetime, time, timedelta, timezone

import base_datos
import clasificador
import reglas
from correos_etiquetados import CORREOS

# placa, id, empresa, autorizado, conductor, días para que venza la certificación
CAMIONES = [
    ("ABC-101-A", "CAM-101", "Transportes UTVT", True, "Juan Pérez", 200),
    ("ABC-123-D", "CAM-102", "Transportes UTVT", True, "Ana Ruiz", 15),
    ("XYZ-456-A", "CAM-103", "Fletes del Norte", True, "Luis Soto", -10),
    ("QWE-789-B", "CAM-104", "Cargas MX", False, "María López", 300),
    ("LMN-222-C", "CAM-105", "Quimex Logística", True, "Pedro Díaz", 90),
    ("RTY-333-D", "CAM-106", "Fletes del Norte", True, "Sofía Cruz", 25),
    ("UIO-444-E", "CAM-107", "Transportes UTVT", True, "Diego Mora", 400),
    ("GHJ-555-F", "CAM-108", "Cargas MX", True, "Elena Ríos", 60),
]

# camión, peso excedido, peligrosos, hora, días atrás
ACCESOS = [
    ("CAM-101", False, False, "10:30", 0),
    ("CAM-102", False, True, "12:15", 0),
    ("CAM-103", False, False, "11:00", 1),
    ("CAM-104", False, False, "13:00", 1),
    ("CAM-105", False, True, "17:45", 2),
    ("CAM-105", False, True, "14:20", 3),
    ("CAM-106", True, False, "10:10", 4),
    ("CAM-107", False, False, "15:30", 5),
    ("CAM-108", False, False, "09:15", 6),
    ("CAM-101", True, True, "11:40", 8),
    ("CAM-107", False, True, "16:30", 9),
    ("CAM-102", False, False, "10:45", 12),
]

# número de correo en correos_etiquetados, días atrás, estado final
INCIDENTES = [
    (0, 1, "en_atencion"), (1, 2, "nuevo"), (5, 3, "nuevo"), (6, 5, "cerrado"),
    (8, 6, "cerrado"), (11, 8, "en_atencion"), (12, 9, "cerrado"), (14, 10, "cerrado"),
    (15, 12, "cerrado"), (16, 13, "cerrado"), (20, 15, "nuevo"), (21, 17, "cerrado"),
    (2, 19, "cerrado"), (29, 4, "nuevo"),
]

# módulo, descripción, categoría, prob, impacto, mitigación, prob residual, impacto residual
RIESGOS = [
    ("Clasificador LLM", "Alucinaciones: el LLM inventa datos o razones", "seguridad", 4, 5,
     "Validar con pydantic, el asistente solo responde con datos de la base y cita fuentes", 2, 3),
    ("Clasificador LLM", "Sesgo con correos de ortografía informal", "sesgo", 4, 4,
     "Probar con correos informales y revisión humana de los casos 'otro'", 3, 3),
    ("Datos del conductor", "Privacidad: nombre y certificación del conductor expuestos", "privacidad", 4, 5,
     "Guardar solo lo necesario, acceso con usuario y no mostrar estos datos en reportes", 2, 3),
    ("Motor de reglas", "Dependencia excesiva de la automatización", "responsabilidad", 3, 4,
     "Revisión humana en los casos dudosos y bitácora con la explicación", 2, 3),
    ("Cámara de somnolencia", "Sesgo en visión nocturna (falsos positivos)", "sesgo", 4, 4,
     "Auditar con datos nocturnos diversos y umbral ajustable", 2, 4),
    ("Lector de placas", "Lectura errónea que niega el acceso sin razón", "responsabilidad", 3, 3,
     "Revisión humana y canal para apelar", 2, 2),
]


def fecha_de(dias_atras, hora="12:00"):
    # la fecha va en hora de la compu y se guarda en utc, como lo hace la app
    horas, minutos = hora.split(":")
    local = datetime.now().replace(hour=int(horas), minute=int(minutos), second=0, microsecond=0)
    local = local - timedelta(days=dias_atras)
    return local.astimezone(timezone.utc)


def cargar(db):
    marca = {"demo": True}
    cuantos = {"camiones": 0, "accesos": 0, "incidentes": 0, "riesgos_eticos": 0}

    camiones = {}
    for placa, camion_id, empresa, autorizado, conductor, dias in CAMIONES:
        vence = date.today() + timedelta(days=dias)
        db.crear_camion(placa, camion_id, empresa, autorizado, conductor, vence, extra={"demo": True})
        camiones[camion_id] = {"camion_id": camion_id, "placa": placa, "autorizado": autorizado, "vence": vence}
        cuantos["camiones"] += 1

    for camion_id, Q, R, hora, dias_atras in ACCESOS:
        camion = camiones[camion_id]
        fecha = fecha_de(dias_atras, hora)
        horas, minutos = hora.split(":")

        S, W, dias = reglas.estado_certificacion(camion["vence"], fecha.astimezone().date())
        H = reglas.hora_permitida(time(int(horas), int(minutos)))

        premisas = {"P": camion["autorizado"], "Q": Q, "R": R, "S": S, "H": H, "W": W}
        decision = reglas.decidir(premisas["P"], Q, R, S, H, W)
        extra = {"demo": True, "creado": fecha}
        db.registrar_acceso(camion, premisas, decision, "demo", extra)
        cuantos["accesos"] += 1

    for numero, dias_atras, estado in INCIDENTES:
        correo = CORREOS[numero]
        clasificacion = {
            "categoria": correo["categoria"],
            "prioridad": correo["prioridad"],
            "metodo": "demo",
            "requiere_revision_humana": correo["categoria"] == "otro",
            "resumen": correo["asunto"],
        }
        datos = clasificador.extraer_datos(correo["asunto"], correo["cuerpo"])
        correo_original = {"remitente": "operador.caseta@logismart.example",
                           "asunto": correo["asunto"], "cuerpo": correo["cuerpo"]}

        extra = {"demo": True, "creado": fecha_de(dias_atras)}
        id_incidente = db.crear_incidente(correo_original, clasificacion, datos, "demo", extra)
        if estado == "en_atencion":
            db.cambiar_estado_incidente(id_incidente, "en_atencion", "Ya se envió a alguien", "demo")
        if estado == "cerrado":
            db.cambiar_estado_incidente(id_incidente, "en_atencion", "Ya se envió a alguien", "demo")
            db.cambiar_estado_incidente(id_incidente, "cerrado", "Resuelto", "demo")
        cuantos["incidentes"] += 1

    for modulo, descripcion, categoria, prob, impacto, mitigacion, prob_res, impacto_res in RIESGOS:
        db.crear_riesgo(modulo, descripcion, categoria, prob, impacto, mitigacion, prob_res, impacto_res, marca)
        cuantos["riesgos_eticos"] += 1

    return cuantos


def pedir_confirmacion(pregunta):
    respuesta = input(pregunta + "\nEscribe SI para continuar: ")
    return respuesta.strip().upper() == "SI"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    borrar = "--borrar" in sys.argv

    db = base_datos.BaseDatos()
    try:
        db.conectar()
    except base_datos.ErrorBD as error:
        print(error)
        return

    nombre_bd = os.environ["MONGO_DB"]
    demo_actuales = 0
    for coleccion in ["camiones", "accesos", "incidentes", "riesgos_eticos"]:
        demo_actuales += db.contar(coleccion, {"demo": True})

    if borrar:
        print("Hay", demo_actuales, "registros demo en la base '" + nombre_bd + "'.")
        if demo_actuales == 0:
            return
        if pedir_confirmacion("Se van a borrar SOLO los registros marcados como demo."):
            print("Borrados:", db.limpiar_demo())
        else:
            print("No se borró nada.")
        return

    if demo_actuales > 0:
        print("Ya hay datos demo en '" + nombre_bd + "'. Para volver a cargarlos primero corre:")
        print("  python datos_demo.py --borrar")
        return

    print("Se van a CREAR en la base '" + nombre_bd + "' del cluster:")
    print("  ", len(CAMIONES), "camiones,", len(ACCESOS), "accesos,", len(INCIDENTES), "incidentes,",
          len(RIESGOS), "riesgos éticos")
    print("Todo queda marcado como demo y se borra con:  python datos_demo.py --borrar")

    if not pedir_confirmacion("Esto escribe en el cluster."):
        print("No se cargó nada.")
        return

    db.preparar()
    cuantos = cargar(db)
    print("Listo:", cuantos)


if __name__ == "__main__":
    main()
