from bson import ObjectId
from pymongo.errors import DuplicateKeyError

import base_datos

BaseReal = base_datos.BaseDatos


def valor_de(doc, campo):
    valor = doc
    for parte in campo.split("."):
        if isinstance(valor, dict) and parte in valor:
            valor = valor[parte]
        else:
            return None
    return valor


def coincide(doc, filtro):
    if "$or" in filtro:
        alguno = False
        for opcion in filtro["$or"]:
            if coincide(doc, opcion):
                alguno = True
        if not alguno:
            return False

    for campo in filtro:
        if campo.startswith("$"):
            continue
        condicion = filtro[campo]
        valor = valor_de(doc, campo)
        if isinstance(condicion, dict):
            if "$ne" in condicion and valor == condicion["$ne"]:
                return False
            if "$gte" in condicion and (valor is None or valor < condicion["$gte"]):
                return False
            if "$lt" in condicion and (valor is None or valor >= condicion["$lt"]):
                return False
        elif valor != condicion:
            return False
    return True


class Resultado:
    def __init__(self, encontrados=0, borrados=0):
        self.matched_count = encontrados
        self.deleted_count = borrados


class ColeccionFalsa:
    # lo mínimo de una colección de mongo: buscar, actualizar y borrar por _id
    def __init__(self, docs, unicos=None):
        self.docs = docs
        self.unicos = unicos or []

    def find_one(self, filtro):
        for doc in self.docs:
            if doc["_id"] == filtro["_id"]:
                return doc
        return None

    def update_one(self, filtro, cambios):
        doc = self.find_one(filtro)
        if doc is None:
            return Resultado()

        if "$set" in cambios:
            for campo in self.unicos:
                for otro in self.docs:
                    if otro is not doc and campo in cambios["$set"] and otro.get(campo) == cambios["$set"][campo]:
                        raise DuplicateKeyError("duplicado en " + campo)
            for campo in cambios["$set"]:
                doc[campo] = cambios["$set"][campo]
        if "$push" in cambios:
            for campo in cambios["$push"]:
                doc[campo].append(cambios["$push"][campo])
        return Resultado(encontrados=1)

    def delete_one(self, filtro):
        doc = self.find_one(filtro)
        if doc is None:
            return Resultado()
        self.docs.remove(doc)
        return Resultado(borrados=1)


class BaseEnMemoria(BaseReal):
    # misma clase de la base pero guarda en listas, para probar sin tocar el cluster
    def __init__(self):
        BaseReal.__init__(self)
        self.docs = {}
        for nombre in base_datos.COLECCIONES:
            self.docs[nombre] = []

    def conectado(self):
        return True

    def conectar(self):
        pass

    def preparar(self):
        pass

    def cerrar(self):
        pass

    def _col(self, nombre):
        if nombre not in base_datos.COLECCIONES:
            raise base_datos.ErrorBD("La colección '" + nombre + "' no existe en LogiSmart.")
        if nombre == "camiones":
            return ColeccionFalsa(self.docs[nombre], ["placa", "camion_id"])
        return ColeccionFalsa(self.docs[nombre])

    def crear(self, coleccion, documento):
        documento = dict(documento)
        if "creado" not in documento:
            documento["creado"] = base_datos.ahora()
        if coleccion == "camiones":
            for c in self.docs["camiones"]:
                if c["placa"] == documento["placa"]:
                    raise base_datos.ErrorBD("Ya existe un registro con esa placa o ID de camión.")
        documento["_id"] = ObjectId()
        self.docs[coleccion].append(documento)
        return str(documento["_id"])

    def listar(self, coleccion, filtro=None, limite=200, campo_orden="creado"):
        if filtro is None:
            filtro = {}
        encontrados = []
        for doc in self.docs[coleccion]:
            if coincide(doc, filtro):
                encontrados.append(doc)
        encontrados.sort(key=lambda doc: doc.get(campo_orden), reverse=True)
        return encontrados[:limite]

    def contar(self, coleccion, filtro=None):
        return len(self.listar(coleccion, filtro, limite=100000))

    def buscar_camion(self, texto):
        texto = (texto or "").strip().upper()
        for c in self.docs["camiones"]:
            if texto in (c["camion_id"], c["placa"]):
                return c
        return None

    def indicadores(self, desde=None, hasta=None):
        return {
            "camiones_atendidos": len(self.docs["accesos"]),
            "incidentes_abiertos": self.contar("incidentes", {"estado": {"$ne": "cerrado"}}),
            "riesgos_criticos": len(self.docs["riesgos_eticos"]),
        }

    def incidentes_por_categoria_y_semana(self, desde=None, hasta=None):
        return []
