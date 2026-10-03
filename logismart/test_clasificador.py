import json
import unittest

import clasificador
import evaluacion
from correos_etiquetados import CORREOS

BUENO = {
    "categoria": "materiales_peligrosos",
    "prioridad": "critica",
    "entidades": {"placa": None, "camion_id": "CAM-102", "peso_kg": None, "ubicacion": None},
    "resumen": "Derrame de químico en el andén 3",
}


def chat_con(*respuestas):
    # chat falso: va soltando las respuestas en orden y guarda las llamadas
    llamadas = []

    def chat(model, messages, format=None, options=None):
        llamadas.append(messages)
        i = min(len(llamadas) - 1, len(respuestas) - 1)
        r = respuestas[i]
        if isinstance(r, Exception):
            raise r
        if isinstance(r, dict):
            r = json.dumps(r)
        return {"message": {"content": r}}

    chat.llamadas = llamadas
    return chat


class TestReglas(unittest.TestCase):

    def test_derrame_es_critico(self):
        r = clasificador.clasificar_reglas("URGENTE: derrame en andén 3", "fuga de químico inflamable")
        self.assertEqual(r["categoria"], "materiales_peligrosos")
        self.assertEqual(r["prioridad"], "critica")

    def test_sin_palabras_es_otro(self):
        r = clasificador.clasificar_reglas("Hola", "una duda general")
        self.assertEqual((r["categoria"], r["prioridad"]), ("otro", "baja"))

    def test_urgencia_sube_un_nivel(self):
        normal = clasificador.clasificar_reglas("Pantalla lenta", "El sistema carga lento")
        urgente = clasificador.clasificar_reglas("Pantalla lenta urgente", "El sistema carga lento")
        self.assertEqual((normal["prioridad"], urgente["prioridad"]), ("baja", "media"))

    def test_extraccion(self):
        d = clasificador.extraer_datos("derrame en andén 3",
                                       "El camión CAM-102 con placas ABC-123-D pesó 48.5 toneladas")
        self.assertEqual(d["placa"], "ABC-123-D")
        self.assertEqual(d["camion_id"], "CAM-102")
        self.assertEqual(d["peso_kg"], 48500.0)
        self.assertEqual(d["ubicacion"], "anden 3")

    def test_solo_reglas_no_llama_al_llm(self):
        r = clasificador.clasificar_solo_reglas("URGENTE: derrame", "fuga de químico")
        self.assertEqual(r["metodo"], "reglas")
        self.assertIsNone(r["llm"])
        self.assertEqual((r["categoria"], r["prioridad"]), ("materiales_peligrosos", "critica"))

    def test_solo_reglas_marca_otro_para_revision(self):
        r = clasificador.clasificar_solo_reglas("Hola", "una duda")
        self.assertTrue(r["requiere_revision_humana"])

    def test_dato_que_no_esta_queda_en_none(self):
        d = clasificador.extraer_datos("Hola", "una duda")
        self.assertEqual(d, {"placa": None, "camion_id": None, "peso_kg": None, "ubicacion": None})


class TestLLM(unittest.TestCase):

    def test_json_valido(self):
        r = clasificador.clasificar_llm("a", "b", chat_con(BUENO))
        self.assertTrue(r["ok"])
        self.assertEqual(r["intentos"], 1)
        self.assertEqual(r["datos"]["categoria"], "materiales_peligrosos")

    def test_json_roto_reintenta_y_luego_funciona(self):
        chat = chat_con("esto no es json", BUENO)
        r = clasificador.clasificar_llm("a", "b", chat)
        self.assertTrue(r["ok"])
        self.assertEqual(r["intentos"], 2)
        self.assertEqual(len(chat.llamadas), 2)

    def test_categoria_inventada_no_pasa(self):
        malo = dict(BUENO)
        malo["categoria"] = "ovnis"
        r = clasificador.clasificar_llm("a", "b", chat_con(malo))
        self.assertFalse(r["ok"])
        self.assertEqual(r["intentos"], clasificador.MAX_INTENTOS)

    def test_campo_extra_no_pasa(self):
        malo = dict(BUENO)
        malo["opinion"] = "me cae mal"
        self.assertFalse(clasificador.clasificar_llm("a", "b", chat_con(malo))["ok"])

    def test_falta_campo_no_pasa(self):
        malo = dict(BUENO)
        del malo["resumen"]
        self.assertFalse(clasificador.clasificar_llm("a", "b", chat_con(malo))["ok"])

    def test_ollama_apagado_no_reintenta(self):
        chat = chat_con(ConnectionError("apagado"))
        r = clasificador.clasificar_llm("a", "b", chat)
        self.assertFalse(r["ok"])
        self.assertIn("Ollama", r["error"])
        self.assertEqual(len(chat.llamadas), 1)


class TestHibrido(unittest.TestCase):

    def test_si_el_llm_falla_cae_a_reglas(self):
        r = clasificador.clasificar_hibrido("URGENTE: derrame", "fuga de químico", chat_con("basura", "basura"))
        self.assertEqual(r["metodo"], "reglas")
        self.assertEqual(r["categoria"], "materiales_peligrosos")
        self.assertFalse(r["llm"]["ok"])

    def test_si_coinciden_no_pide_revision(self):
        r = clasificador.clasificar_hibrido("URGENTE: derrame en andén 3", "fuga de químico inflamable CAM-102",
                                            chat_con(BUENO))
        self.assertEqual(r["metodo"], "hibrido")
        self.assertTrue(r["coincidio_con_reglas"])
        self.assertFalse(r["requiere_revision_humana"])

    def test_si_no_coinciden_gana_la_prioridad_mas_alta(self):
        # las reglas ven una falla de software (baja), el LLM dice que es crítico
        llm = dict(BUENO)
        llm["categoria"] = "somnolencia_conductor"
        llm["prioridad"] = "critica"
        r = clasificador.clasificar_hibrido("sistema lento", "la pantalla carga lento", chat_con(llm))
        self.assertEqual(r["prioridad"], "critica")
        self.assertEqual(r["categoria"], "somnolencia_conductor")
        self.assertTrue(r["requiere_revision_humana"])

    def test_si_las_reglas_son_mas_graves_ganan_ellas(self):
        llm = dict(BUENO)
        llm["categoria"] = "otro"
        llm["prioridad"] = "baja"
        r = clasificador.clasificar_hibrido("derrame", "fuga de químico", chat_con(llm))
        self.assertEqual(r["prioridad"], "critica")
        self.assertEqual(r["categoria"], "materiales_peligrosos")
        self.assertTrue(r["requiere_revision_humana"])

    def test_otro_siempre_se_revisa(self):
        llm = dict(BUENO)
        llm["categoria"] = "otro"
        llm["prioridad"] = "baja"
        r = clasificador.clasificar_hibrido("Hola", "una duda", chat_con(llm))
        self.assertTrue(r["requiere_revision_humana"])

    def test_no_se_cree_entidades_inventadas(self):
        llm = dict(BUENO)
        llm["entidades"] = {"placa": "ZZZ-999-Z", "camion_id": "CAM-555", "peso_kg": 99999, "ubicacion": "puerta Z"}
        r = clasificador.clasificar_hibrido("derrame", "fuga de químico en el CAM-102", chat_con(llm))
        self.assertIsNone(r["entidades"]["placa"])
        self.assertEqual(r["entidades"]["camion_id"], "CAM-102")
        self.assertIsNone(r["entidades"]["peso_kg"])
        self.assertIsNone(r["entidades"]["ubicacion"])


class TestEvaluacion(unittest.TestCase):

    def test_hay_al_menos_30_correos_bien_etiquetados(self):
        self.assertGreaterEqual(len(CORREOS), 30)
        for c in CORREOS:
            self.assertIn(c["categoria"], evaluacion.NOMBRES_CATEGORIAS)
            self.assertIn(c["prioridad"], clasificador.ORDEN_PRIORIDAD)

    def test_todas_las_categorias_aparecen(self):
        usadas = set()
        for c in CORREOS:
            usadas.add(c["categoria"])
        self.assertEqual(usadas, set(evaluacion.NOMBRES_CATEGORIAS))

    def test_evaluar_reglas(self):
        r = evaluacion.evaluar("reglas")
        self.assertEqual(r["total"], len(CORREOS))
        total_matriz = 0
        for real in r["matriz"]:
            total_matriz += sum(r["matriz"][real].values())
        self.assertEqual(total_matriz, len(CORREOS))

    def test_llm_perfecto_saca_100(self):
        etiquetas = {}
        for c in CORREOS:
            etiquetas[c["asunto"]] = c

        # un chat que contesta justo la etiqueta correcta
        def chat_perfecto(model, messages, format=None, options=None):
            asunto = messages[1]["content"].split("\n")[0].replace("Asunto: ", "")
            c = etiquetas[asunto]
            datos = {"categoria": c["categoria"], "prioridad": c["prioridad"],
                     "entidades": {"placa": None, "camion_id": None, "peso_kg": None, "ubicacion": None},
                     "resumen": "x"}
            return {"message": {"content": json.dumps(datos)}}

        r = evaluacion.evaluar("llm", chat=chat_perfecto)
        self.assertEqual(r["exactitud_categoria"], 1.0)
        self.assertEqual(r["exactitud_prioridad"], 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
