import unittest
from datetime import datetime

import asistente

CAMION = {"_id": "c1aaaa", "camion_id": "CAM-102", "placa": "ABC-123-D", "empresa": "Transportes UTVT",
          "autorizacion": True, "conductor": "Juan Pérez", "cert_vence": datetime(2026, 12, 1)}

ACCESO = {"_id": "a1bbbb", "camion_id": "CAM-102", "placa": "ABC-123-D", "creado": datetime(2026, 10, 3, 18, 0),
          "resultado": "INSPECCIÓN ESPECIAL", "semaforo": "amarillo",
          "explicacion": ["E = P ∧ (R ∨ Q) = V", "Lleva materiales peligrosos (R=V): entra, pero con inspección."],
          "motivo": ["Lleva materiales peligrosos (R=V): entra, pero con inspección."]}

INCIDENTE = {"_id": "i1cccc", "creado": datetime(2026, 10, 2, 12, 0), "estado": "nuevo",
             "correo_original": {"asunto": "derrame en andén 3"},
             "clasificacion": {"categoria": "materiales_peligrosos", "prioridad": "critica"}}

RIESGO = {"_id": "r1dddd", "modulo": "Clasificador", "descripcion": "Alucinaciones del LLM",
          "categoria": "seguridad", "puntaje": 20, "puntaje_residual": 6, "mitigacion": "Revisión humana"}


class FalsaBD:
    # regresa lo mismo sin importar el filtro, solo anota qué le pidieron
    def __init__(self, camiones=None, accesos=None, incidentes=None, riesgos=None):
        self.datos = {
            "camiones": camiones or [],
            "accesos": accesos or [],
            "incidentes": incidentes or [],
            "riesgos_eticos": riesgos or [],
        }
        self.consultas = []

    def buscar_camion(self, texto):
        for c in self.datos["camiones"]:
            if texto in (c["camion_id"], c["placa"]):
                return c
        return None

    def listar(self, coleccion, filtro=None, limite=200, campo_orden="creado"):
        self.consultas.append((coleccion, filtro, campo_orden))
        return self.datos[coleccion][:limite]


def chat_con(texto):
    llamadas = []

    def chat(model, messages, options=None):
        llamadas.append(messages)
        if isinstance(texto, Exception):
            raise texto
        return {"message": {"content": texto}}

    chat.llamadas = llamadas
    return chat


def bd_con_camion():
    return FalsaBD([CAMION], [ACCESO], [INCIDENTE], [RIESGO])


class TestSinInformacion(unittest.TestCase):

    def test_camion_que_no_existe_no_llama_al_llm(self):
        chat = chat_con("inventando")
        r = asistente.responder(FalsaBD(), "¿Por qué CAM-999 fue a inspección?", [], chat)
        self.assertEqual(r["respuesta"], asistente.SIN_INFORMACION)
        self.assertEqual(len(chat.llamadas), 0)
        self.assertFalse(r["uso_llm"])
        self.assertEqual(r["fuentes"], [])

    def test_pregunta_sin_relacion_con_los_datos(self):
        chat = chat_con("inventando")
        r = asistente.responder(bd_con_camion(), "¿Cuál es la capital de Francia?", [], chat)
        self.assertEqual(r["respuesta"], asistente.SIN_INFORMACION)
        self.assertEqual(len(chat.llamadas), 0)

    def test_pregunta_vacia(self):
        chat = chat_con("x")
        r = asistente.responder(bd_con_camion(), "   ", [], chat)
        self.assertEqual(len(chat.llamadas), 0)
        self.assertIn("pregunta", r["respuesta"])

    def test_si_el_llm_dice_que_no_sabe_no_se_citan_fuentes(self):
        chat = chat_con("No tengo información sobre eso en los registros.")
        r = asistente.responder(bd_con_camion(), "¿De qué color es CAM-102?", [], chat)
        self.assertTrue(r["uso_llm"])
        self.assertEqual(r["fuentes"], [])


class TestConDatos(unittest.TestCase):

    def test_el_prompt_lleva_los_datos_de_la_base(self):
        chat = chat_con("Porque lleva peligrosos [2].")
        asistente.responder(bd_con_camion(), "¿Por qué CAM-102 fue enviado a inspección?", [], chat)
        prompt = chat.llamadas[0][-1]["content"]
        self.assertIn("INSPECCIÓN ESPECIAL", prompt)
        self.assertIn("Transportes UTVT", prompt)
        self.assertIn("MOTIVO: Lleva materiales peligrosos", prompt)

    def test_si_el_acceso_viejo_no_trae_motivo_usa_la_explicacion(self):
        viejo = dict(ACCESO)
        del viejo["motivo"]
        self.assertIn("Explicación:", asistente.texto_acceso(viejo))

    def test_el_primer_mensaje_es_el_system(self):
        chat = chat_con("ok [1]")
        asistente.responder(bd_con_camion(), "¿Qué pasó con CAM-102?", [], chat)
        self.assertEqual(chat.llamadas[0][0]["role"], "system")

    def test_solo_cuenta_las_fuentes_citadas(self):
        chat = chat_con("Lo mandaron a inspección [2].")
        r = asistente.responder(bd_con_camion(), "¿Por qué CAM-102 fue a inspección?", [], chat)
        self.assertEqual(len(r["fuentes"]), 1)
        self.assertEqual(r["fuentes"][0]["coleccion"], "accesos")

    def test_cita_inventada_se_ignora(self):
        chat = chat_con("Según [9] fue por peso.")
        r = asistente.responder(bd_con_camion(), "¿Qué pasó con CAM-102?", [], chat)
        self.assertEqual(len(r["fuentes"]), 3)

    def test_sin_citas_se_muestran_todas_las_consultadas(self):
        chat = chat_con("Lo mandaron a inspección.")
        r = asistente.responder(bd_con_camion(), "¿Qué pasó con CAM-102?", [], chat)
        self.assertEqual(len(r["fuentes"]), 3)

    def test_busca_tambien_por_placa(self):
        chat = chat_con("Es de Transportes UTVT [1].")
        r = asistente.responder(bd_con_camion(), "¿De quién es la placa ABC-123-D?", [], chat)
        self.assertEqual(r["fuentes"][0]["coleccion"], "camiones")

    def test_historial_guarda_pregunta_y_respuesta_sin_contexto(self):
        historial = []
        asistente.responder(bd_con_camion(), "¿Qué pasó con CAM-102?", historial, chat_con("Respuesta [1]"))
        self.assertEqual(len(historial), 2)
        self.assertEqual(historial[0]["content"], "¿Qué pasó con CAM-102?")
        self.assertNotIn("Contexto", historial[0]["content"])

    def test_el_historial_se_recorta_a_los_ultimos_6(self):
        historial = []
        for i in range(10):
            historial.append({"role": "user", "content": "p" + str(i)})
        chat = chat_con("ok [1]")
        asistente.responder(bd_con_camion(), "¿Qué pasó con CAM-102?", historial, chat)
        # system + 6 del historial + la pregunta nueva
        self.assertEqual(len(chat.llamadas[0]), 8)

    def test_si_el_llm_falla_se_enseñan_los_registros(self):
        r = asistente.responder(bd_con_camion(), "¿Qué pasó con CAM-102?", [], chat_con(ConnectionError("apagado")))
        self.assertFalse(r["uso_llm"])
        self.assertIn("INSPECCIÓN ESPECIAL", r["respuesta"])
        self.assertIn("apagado", r["error"])
        self.assertEqual(len(r["fuentes"]), 3)


class TestPreguntasGenerales(unittest.TestCase):

    def test_incidentes_abiertos_filtra_los_no_cerrados(self):
        bd = bd_con_camion()
        asistente.responder(bd, "¿Cuántos incidentes abiertos hay?", [], chat_con("Hay 1 [1]"))
        self.assertEqual(bd.consultas[0], ("incidentes", {"estado": {"$ne": "cerrado"}}, "creado"))

    def test_riesgos_se_ordenan_por_puntaje(self):
        bd = bd_con_camion()
        r = asistente.responder(bd, "¿Cuáles son los riesgos más altos?", [], chat_con("Alucinaciones [1]"))
        self.assertEqual(bd.consultas[0][2], "puntaje")
        self.assertEqual(r["fuentes"][0]["coleccion"], "riesgos_eticos")

    def test_texto_fuentes_lo_arma_el_codigo(self):
        r = asistente.responder(bd_con_camion(), "¿Qué pasó con CAM-102?", [], chat_con("ok"))
        texto = asistente.texto_fuentes(r["fuentes"])
        self.assertIn("[1] camiones", texto)
        self.assertIn("accesos", texto)


if __name__ == "__main__":
    unittest.main(verbosity=2)
