import json
import os
import tempfile
import unittest
from datetime import date, time
from pathlib import Path
from unittest import mock

import asistente
import clasificador
import configuracion
import correo
import reglas


class TestConfiguracion(unittest.TestCase):

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta = Path(self.carpeta.name) / "configuracion.json"
        self.guardados = dict(configuracion.valores)

    def tearDown(self):
        configuracion.valores.clear()
        configuracion.valores.update(self.guardados)
        configuracion.aplicar()
        self.carpeta.cleanup()

    def test_los_valores_de_siempre_son_validos(self):
        limpios = configuracion.revisar(configuracion.PREDETERMINADA)
        self.assertEqual(limpios["hora_inicio"], "10:00")
        self.assertEqual(limpios["hora_fin"], "16:00")

    def test_rechaza_valores_malos(self):
        malos = [
            {"hora_inicio": "25:00"},
            {"hora_inicio": "abc"},
            {"hora_inicio": "17:00", "hora_fin": "09:00"},
            {"hora_inicio": "10:00", "hora_fin": "10:00"},
            {"dias_por_vencer": 0},
            {"dias_por_vencer": "muchos"},
            {"intentos_llm": 9},
            {"correo_soporte": "no-es-correo"},
            {"modelo": "   "},
            {"operador": ""},
        ]
        for cambio in malos:
            with self.assertRaises(ValueError, msg=str(cambio)):
                configuracion.revisar(cambio)

    def test_un_valor_malo_no_cambia_nada(self):
        antes = dict(configuracion.valores)
        with self.assertRaises(ValueError):
            configuracion.guardar({"hora_inicio": "99:99"}, self.ruta)
        self.assertEqual(configuracion.valores, antes)
        self.assertFalse(self.ruta.exists())

    def test_guardar_cambia_el_horario_de_verdad(self):
        self.assertFalse(reglas.hora_permitida(time(18, 0)))
        configuracion.guardar({"hora_inicio": "08:00", "hora_fin": "20:00"}, self.ruta)
        self.assertTrue(reglas.hora_permitida(time(18, 0)))
        self.assertFalse(reglas.hora_permitida(time(21, 0)))

    def test_guardar_cambia_los_dias_por_vencer(self):
        hoy = date(2026, 10, 3)
        vence = date(2026, 11, 20)
        self.assertEqual(reglas.estado_certificacion(vence, hoy)[:2], (True, False))
        configuracion.guardar({"dias_por_vencer": 60}, self.ruta)
        self.assertEqual(reglas.estado_certificacion(vence, hoy)[:2], (True, True))

    def test_guardar_cambia_el_modelo_del_clasificador_y_del_asistente(self):
        configuracion.guardar({"modelo": "otro-modelo", "intentos_llm": 3}, self.ruta)
        self.assertEqual(clasificador.MODELO, "otro-modelo")
        self.assertEqual(asistente.MODELO, "otro-modelo")

        usados = []

        def chat(model, messages, format=None, options=None):
            usados.append(model)
            return {"message": {"content": "no es json"}}

        r = clasificador.clasificar_llm("a", "b", chat)
        self.assertEqual(usados, ["otro-modelo"] * 3)
        self.assertEqual(r["intentos"], 3)

    def test_se_guarda_en_archivo_y_se_vuelve_a_leer(self):
        configuracion.guardar({"operador": "Stephany", "dias_por_vencer": 45}, self.ruta)
        contenido = json.loads(self.ruta.read_text(encoding="utf-8"))
        self.assertEqual(contenido["operador"], "Stephany")

        configuracion.valores.clear()
        configuracion.valores.update(configuracion.PREDETERMINADA)
        configuracion.cargar(self.ruta)
        self.assertEqual(configuracion.valores["operador"], "Stephany")
        self.assertEqual(configuracion.valores["dias_por_vencer"], 45)

    def test_archivo_dañado_vuelve_a_lo_de_siempre(self):
        self.ruta.write_text("{ esto no es json", encoding="utf-8")
        configuracion.cargar(self.ruta)
        self.assertEqual(configuracion.valores, configuracion.PREDETERMINADA)

    def test_archivo_con_valores_malos_vuelve_a_lo_de_siempre(self):
        self.ruta.write_text(json.dumps({"hora_inicio": "99:00"}), encoding="utf-8")
        configuracion.cargar(self.ruta)
        self.assertEqual(configuracion.valores["hora_inicio"], "10:00")

    def test_restaurar(self):
        configuracion.guardar({"hora_fin": "22:00"}, self.ruta)
        configuracion.restaurar(self.ruta)
        self.assertEqual(configuracion.valores["hora_fin"], "16:00")
        self.assertTrue(reglas.hora_permitida(time(16, 0)))
        self.assertFalse(reglas.hora_permitida(time(17, 0)))


class TestCorreo(unittest.TestCase):

    CORREO = {"remitente": "guardia@planta.example", "asunto": "derrame", "cuerpo": "hay una fuga"}
    CLASIF = {"categoria": "materiales_peligrosos", "prioridad": "critica", "requiere_revision_humana": True}
    DATOS = {"placa": None, "camion_id": "CAM-102", "peso_kg": None, "ubicacion": "anden 3"}

    def test_armar_correo(self):
        asunto, cuerpo = correo.armar_correo(self.CORREO, self.CLASIF, self.DATOS)
        self.assertEqual(asunto, "[CRITICA] materiales_peligrosos - derrame")
        self.assertIn("REQUIERE REVISIÓN HUMANA", cuerpo)
        self.assertIn("camion_id: CAM-102", cuerpo)
        self.assertNotIn("placa:", cuerpo)
        self.assertIn("hay una fuga", cuerpo)

    def test_simulacion_no_se_conecta_a_nada(self):
        with mock.patch("smtplib.SMTP", side_effect=AssertionError("no debía conectarse")):
            r = correo.enviar("a@b.c", "soporte@x.c", "asunto", "cuerpo", simulacion=True)
        self.assertEqual(r, {"enviado": True, "modo": "simulacion", "error": None})

    def test_envio_real_sin_variables_avisa_sin_romper(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            r = correo.enviar("a@b.c", "soporte@x.c", "asunto", "cuerpo", simulacion=False)
        self.assertFalse(r["enviado"])
        self.assertIn("SMTP_HOST", r["error"])

    def test_envio_real_con_red_caida_avisa_sin_romper_ni_filtrar_la_clave(self):
        variables = {"SMTP_HOST": "x", "SMTP_USER": "u", "SMTP_PASSWORD": "clave-super-secreta"}
        with mock.patch.dict(os.environ, variables, clear=True):
            with mock.patch("smtplib.SMTP", side_effect=OSError("fallo con clave-super-secreta")):
                r = correo.enviar("a@b.c", "soporte@x.c", "asunto", "cuerpo", simulacion=False)
        self.assertFalse(r["enviado"])
        self.assertNotIn("clave-super-secreta", r["error"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
