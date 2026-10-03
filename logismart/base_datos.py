import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus

from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, PyMongoError

RUTA_ENV = Path(__file__).resolve().parent.parent / ".env"

COLECCIONES = ["camiones", "accesos", "incidentes", "riesgos_eticos", "evaluaciones_llm"]
ESTADOS_INCIDENTE = ["nuevo", "en_atencion", "cerrado"]
NIVEL_CRITICO = 17

MENSAJE_FALLO = "Falló la operación con MongoDB, revisa tu internet y vuelve a intentar."


class ErrorBD(Exception):
    pass


def ahora():
    return datetime.now(timezone.utc)


def a_local(fecha):
    # hora de la compu no utc
    if fecha is None:
        return None
    return fecha.replace(tzinfo=timezone.utc).astimezone().replace(tzinfo=None)


def puntaje(probabilidad, impacto):
    return probabilidad * impacto


def a_object_id(valor):
    try:
        return ObjectId(str(valor))
    except Exception:
        raise ErrorBD("El ID del registro no es válido.") from None


def a_datetime(valor):
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor
    return datetime(valor.year, valor.month, valor.day)


def validar_escala(probabilidad, impacto):
    if type(probabilidad) != int or probabilidad < 1 or probabilidad > 5:
        raise ErrorBD("La probabilidad debe ser un número entero del 1 al 5.")
    if type(impacto) != int or impacto < 1 or impacto > 5:
        raise ErrorBD("El impacto debe ser un número entero del 1 al 5.")


def agregar_extra(documento, extra):
    if extra is not None:
        for campo in extra:
            documento[campo] = extra[campo]


def datos_camion(placa, camion_id, empresa, autorizado, conductor, cert_vence):
    placa = (placa or "").strip().upper()
    camion_id = (camion_id or "").strip().upper()
    empresa = (empresa or "").strip()

    if placa == "" or camion_id == "":
        raise ErrorBD("La placa y el ID del camión son obligatorios.")
    if empresa == "":
        raise ErrorBD("Falta la empresa.")

    return {
        "placa": placa,
        "camion_id": camion_id,
        "empresa": empresa,
        "autorizacion": bool(autorizado),
        "conductor": (conductor or "").strip(),
        "cert_vence": a_datetime(cert_vence),
    }


def hacer_evento(estado, nota, usuario):
    return {"estado": estado, "nota": nota, "usuario": usuario, "fecha": ahora()}


def filtro_fechas(desde, hasta):
    rango = {}
    if desde:
        # las fechas del filtro son de la compu, mongo guarda en utc
        rango["$gte"] = a_datetime(desde).astimezone(timezone.utc)
    if hasta:
        rango["$lt"] = a_datetime(hasta).astimezone(timezone.utc)
    return rango


class BaseDatos:

    def __init__(self, prefijo="", timeout_ms=8000):
        self.prefijo = prefijo
        self.timeout_ms = timeout_ms
        self.cliente = None
        self.db = None

    def conectado(self):
        return self.db is not None

    def conectar(self):
        load_dotenv(RUTA_ENV)

        variables = ["MONGO_USER", "MONGO_PASSWORD", "MONGO_CLUSTER", "MONGO_DB"]
        faltan = []
        for variable in variables:
            if not os.getenv(variable):
                faltan.append(variable)
        if len(faltan) > 0:
            raise ErrorBD("Falta en el archivo .env: " + ", ".join(faltan))

        usuario = quote_plus(os.environ["MONGO_USER"])
        clave = quote_plus(os.environ["MONGO_PASSWORD"])
        uri = "mongodb+srv://" + usuario + ":" + clave + "@" + os.environ["MONGO_CLUSTER"] + "/?retryWrites=true&w=majority"

        try:
            self.cliente = MongoClient(uri, serverSelectionTimeoutMS=self.timeout_ms)
            self.cliente.admin.command("ping")
        except PyMongoError:
            self.cliente = None
            self.db = None
            # sin el error original por si trae la contraseña
            raise ErrorBD("No me pude conectar a MongoDB. Revisa tu internet y tu archivo .env.") from None

        self.db = self.cliente[os.environ["MONGO_DB"]]

    def cerrar(self):
        if self.cliente is not None:
            self.cliente.close()
        self.cliente = None
        self.db = None

    def _col(self, nombre):
        if nombre not in COLECCIONES:
            raise ErrorBD("La colección '" + nombre + "' no existe en LogiSmart.")
        if not self.conectado():
            raise ErrorBD("No hay conexión con MongoDB.")
        return self.db[self.prefijo + nombre]

    def preparar(self):
        try:
            self._col("camiones").create_index("placa", unique=True)
            self._col("camiones").create_index("camion_id", unique=True)
            self._col("accesos").create_index([("creado", -1)])
            self._col("incidentes").create_index([("estado", 1)])
            self._col("incidentes").create_index([("creado", -1)])
            self._col("riesgos_eticos").create_index([("puntaje", -1)])
        except PyMongoError:
            raise ErrorBD(MENSAJE_FALLO)

    def crear(self, coleccion, documento):
        try:
            documento = dict(documento)
            if "creado" not in documento:
                documento["creado"] = ahora()
            resultado = self._col(coleccion).insert_one(documento)
            return str(resultado.inserted_id)
        except DuplicateKeyError:
            raise ErrorBD("Ya existe un registro con esa placa o ID de camión.")
        except PyMongoError:
            raise ErrorBD(MENSAJE_FALLO)

    def obtener(self, coleccion, id_):
        try:
            return self._col(coleccion).find_one({"_id": a_object_id(id_)})
        except PyMongoError:
            raise ErrorBD(MENSAJE_FALLO)

    def listar(self, coleccion, filtro=None, limite=200, campo_orden="creado"):
        try:
            if filtro is None:
                filtro = {}
            cursor = self._col(coleccion).find(filtro)
            cursor = cursor.sort(campo_orden, -1).limit(limite)
            return list(cursor)
        except PyMongoError:
            raise ErrorBD(MENSAJE_FALLO)

    def actualizar(self, coleccion, id_, cambios):
        try:
            cambios = dict(cambios)
            cambios["actualizado"] = ahora()
            resultado = self._col(coleccion).update_one({"_id": a_object_id(id_)}, {"$set": cambios})
            return resultado.matched_count > 0
        except DuplicateKeyError:
            raise ErrorBD("Ya existe un registro con esa placa o ID de camión.")
        except PyMongoError:
            raise ErrorBD(MENSAJE_FALLO)

    def eliminar(self, coleccion, id_):
        try:
            resultado = self._col(coleccion).delete_one({"_id": a_object_id(id_)})
            return resultado.deleted_count > 0
        except PyMongoError:
            raise ErrorBD(MENSAJE_FALLO)

    def contar(self, coleccion, filtro=None):
        try:
            if filtro is None:
                filtro = {}
            return self._col(coleccion).count_documents(filtro)
        except PyMongoError:
            raise ErrorBD(MENSAJE_FALLO)

    def crear_camion(self, placa, camion_id, empresa, autorizado, conductor, cert_vence, extra=None):
        camion = datos_camion(placa, camion_id, empresa, autorizado, conductor, cert_vence)
        agregar_extra(camion, extra)
        return self.crear("camiones", camion)

    def editar_camion(self, id_, placa, camion_id, empresa, autorizado, conductor, cert_vence):
        camion = datos_camion(placa, camion_id, empresa, autorizado, conductor, cert_vence)
        return self.actualizar("camiones", id_, camion)

    def buscar_camion(self, texto):
        try:
            texto = (texto or "").strip().upper()
            if texto == "":
                return None
            return self._col("camiones").find_one({"$or": [{"placa": texto}, {"camion_id": texto}]})
        except PyMongoError:
            raise ErrorBD(MENSAJE_FALLO)

    def registrar_acceso(self, camion, premisas, decision, operador="operador", extra=None):
        acceso = {
            "camion_id": None,
            "placa": None,
            "premisas": dict(premisas),
            "A": decision["A"],
            "E": decision["E"],
            "B": decision["B"],
            "L": decision["L"],
            "resultado": decision["resultado"],
            "semaforo": decision["semaforo"],
            "explicacion": decision["pasos"],
            "motivo": decision["motivo"],
            "operador": operador,
        }
        if camion is not None:
            acceso["camion_id"] = camion.get("camion_id")
            acceso["placa"] = camion.get("placa")

        agregar_extra(acceso, extra)
        return self.crear("accesos", acceso)

    def crear_incidente(self, correo, clasificacion, datos_extraidos, usuario="operador", extra=None):
        incidente = {
            "correo_original": dict(correo),
            "clasificacion": dict(clasificacion),
            "datos_extraidos": dict(datos_extraidos),
            "estado": "nuevo",
            "historial": [hacer_evento("nuevo", "Incidente creado", usuario)],
        }
        agregar_extra(incidente, extra)
        return self.crear("incidentes", incidente)

    def cambiar_estado_incidente(self, id_, estado, nota="", usuario="operador"):
        if estado not in ESTADOS_INCIDENTE:
            raise ErrorBD("Estado inválido, usa: " + ", ".join(ESTADOS_INCIDENTE))
        if nota == "":
            nota = "Cambió a " + estado

        try:
            resultado = self._col("incidentes").update_one(
                {"_id": a_object_id(id_)},
                {"$set": {"estado": estado, "actualizado": ahora()},
                 "$push": {"historial": hacer_evento(estado, nota, usuario)}},
            )
            return resultado.matched_count > 0
        except PyMongoError:
            raise ErrorBD(MENSAJE_FALLO)

    def agregar_evento_incidente(self, id_, nota, usuario="operador"):
        try:
            resultado = self._col("incidentes").update_one(
                {"_id": a_object_id(id_)},
                {"$push": {"historial": hacer_evento(None, nota, usuario)}},
            )
            return resultado.matched_count > 0
        except PyMongoError:
            raise ErrorBD(MENSAJE_FALLO)

    def editar_clasificacion(self, id_, clasificacion, usuario="operador"):
        try:
            resultado = self._col("incidentes").update_one(
                {"_id": a_object_id(id_)},
                {"$set": {"clasificacion": dict(clasificacion), "actualizado": ahora()},
                 "$push": {"historial": hacer_evento(None, "Clasificación editada a mano", usuario)}},
            )
            return resultado.matched_count > 0
        except PyMongoError:
            raise ErrorBD(MENSAJE_FALLO)

    def crear_riesgo(self, modulo, descripcion, categoria, probabilidad, impacto,
                     mitigacion="", prob_residual=None, impacto_residual=None, extra=None):
        if prob_residual is None:
            prob_residual = probabilidad
        if impacto_residual is None:
            impacto_residual = impacto

        validar_escala(probabilidad, impacto)
        validar_escala(prob_residual, impacto_residual)

        riesgo = {
            "modulo": modulo.strip(),
            "descripcion": descripcion.strip(),
            "categoria": categoria,
            "probabilidad": probabilidad,
            "impacto": impacto,
            "puntaje": puntaje(probabilidad, impacto),
            "mitigacion": mitigacion,
            "prob_residual": prob_residual,
            "impacto_residual": impacto_residual,
            "puntaje_residual": puntaje(prob_residual, impacto_residual),
            "historico": [],
        }
        agregar_extra(riesgo, extra)
        return self.crear("riesgos_eticos", riesgo)

    def editar_riesgo(self, id_, cambios):
        try:
            actual = self._col("riesgos_eticos").find_one({"_id": a_object_id(id_)})
            if actual is None:
                return False

            # los valores nuevos encima de los de antes
            nuevo = dict(actual)
            for campo in cambios:
                nuevo[campo] = cambios[campo]

            validar_escala(nuevo["probabilidad"], nuevo["impacto"])
            validar_escala(nuevo["prob_residual"], nuevo["impacto_residual"])

            # lo de antes se guarda en el histórico
            foto = {}
            campos = ["probabilidad", "impacto", "puntaje", "prob_residual",
                      "impacto_residual", "puntaje_residual", "mitigacion"]
            for campo in campos:
                foto[campo] = actual.get(campo)
            foto["fecha"] = ahora()

            cambios = dict(cambios)
            cambios["puntaje"] = puntaje(nuevo["probabilidad"], nuevo["impacto"])
            cambios["puntaje_residual"] = puntaje(nuevo["prob_residual"], nuevo["impacto_residual"])
            cambios["actualizado"] = ahora()

            self._col("riesgos_eticos").update_one(
                {"_id": actual["_id"]},
                {"$set": cambios, "$push": {"historico": foto}},
            )
            return True
        except PyMongoError:
            raise ErrorBD(MENSAJE_FALLO)

    def registrar_evaluacion_llm(self, prompt, respuesta, modelo, latencia_ms, coincidio_con_reglas):
        evaluacion = {
            "prompt": prompt,
            "respuesta": respuesta,
            "modelo": modelo,
            "latencia_ms": round(latencia_ms, 1),
            "coincidio_con_reglas": coincidio_con_reglas,
        }
        return self.crear("evaluaciones_llm", evaluacion)

    def incidentes_por_categoria_y_semana(self, desde=None, hasta=None):
        try:
            pipeline = []

            rango = filtro_fechas(desde, hasta)
            if rango:
                pipeline.append({"$match": {"creado": rango}})

            pipeline.append({"$group": {
                "_id": {
                    "semana": {"$dateToString": {"format": "%G-W%V", "date": "$creado"}},
                    "categoria": "$clasificacion.categoria",
                },
                "total": {"$sum": 1},
            }})
            pipeline.append({"$sort": {"_id.semana": 1, "total": -1}})
            pipeline.append({"$project": {
                "_id": 0,
                "semana": "$_id.semana",
                "categoria": "$_id.categoria",
                "total": 1,
            }})

            return list(self._col("incidentes").aggregate(pipeline))
        except PyMongoError:
            raise ErrorBD(MENSAJE_FALLO)

    def indicadores(self, desde=None, hasta=None):
        try:
            filtro_fecha = {}
            rango = filtro_fechas(desde, hasta)
            if rango:
                filtro_fecha = {"creado": rango}

            filtro_abiertos = dict(filtro_fecha)
            filtro_abiertos["estado"] = {"$ne": "cerrado"}

            return {
                "camiones_atendidos": self._col("accesos").count_documents(filtro_fecha),
                "incidentes_abiertos": self._col("incidentes").count_documents(filtro_abiertos),
                "riesgos_criticos": self._col("riesgos_eticos").count_documents(
                    {"puntaje": {"$gte": NIVEL_CRITICO}}),
            }
        except PyMongoError:
            raise ErrorBD(MENSAJE_FALLO)

    def limpiar_demo(self):
        try:
            total = 0
            for nombre in COLECCIONES:
                resultado = self._col(nombre).delete_many({"demo": True})
                total = total + resultado.deleted_count
            return total
        except PyMongoError:
            raise ErrorBD(MENSAJE_FALLO)

    def borrar_todo_el_prefijo(self):
        if self.prefijo == "":
            raise ErrorBD("Por seguridad, esto solo funciona con un prefijo de pruebas.")
        try:
            for nombre in COLECCIONES:
                self._col(nombre).drop()
        except PyMongoError:
            raise ErrorBD(MENSAJE_FALLO)
