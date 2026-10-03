import unittest
from unittest import mock

import base_datos
import datos_demo
import reglas
from base_en_memoria import BaseEnMemoria


class TestDatosDemo(unittest.TestCase):

    def setUp(self):
        self.db = BaseEnMemoria()
        self.cuantos = datos_demo.cargar(self.db)

    def test_cantidades(self):
        self.assertEqual(self.cuantos, {"camiones": 8, "accesos": 12, "incidentes": 14, "riesgos_eticos": 6})
        for coleccion in self.cuantos:
            self.assertEqual(len(self.db.docs[coleccion]), self.cuantos[coleccion])

    def test_todo_esta_marcado_como_demo(self):
        for coleccion in self.cuantos:
            for doc in self.db.docs[coleccion]:
                self.assertTrue(doc["demo"], coleccion)

    def test_no_inventa_evaluaciones_del_llm(self):
        self.assertEqual(self.db.docs["evaluaciones_llm"], [])

    def test_placas_e_ids_no_se_repiten(self):
        placas = set()
        ids = set()
        for c in self.db.docs["camiones"]:
            placas.add(c["placa"])
            ids.add(c["camion_id"])
        self.assertEqual(len(placas), 8)
        self.assertEqual(len(ids), 8)

    def test_hay_de_todos_los_colores_de_semaforo(self):
        colores = set()
        for a in self.db.docs["accesos"]:
            colores.add(a["semaforo"])
        self.assertEqual(colores, {"rojo", "amarillo", "verde"})

    def test_hay_bloqueo_por_horario_y_alerta(self):
        resultados = []
        alertas = 0
        for a in self.db.docs["accesos"]:
            resultados.append(a["resultado"])
            if a["L"]:
                alertas += 1
        self.assertIn("BLOQUEADO POR HORARIO", resultados)
        self.assertIn("INSPECCIÓN ESPECIAL", resultados)
        self.assertGreaterEqual(alertas, 1)

    def test_cada_acceso_coincide_con_lo_que_diria_el_motor_de_reglas(self):
        for a in self.db.docs["accesos"]:
            p = a["premisas"]
            esperado = reglas.decidir(p["P"], p["Q"], p["R"], p["S"], p["H"], p["W"])
            self.assertEqual(a["resultado"], esperado["resultado"])
            self.assertEqual(a["motivo"], esperado["motivo"])

    def test_el_cam_102_sale_a_inspeccion_como_en_el_ejemplo_del_profe(self):
        resultados = []
        for a in self.db.docs["accesos"]:
            if a["camion_id"] == "CAM-102":
                resultados.append(a["resultado"])
        self.assertIn("INSPECCIÓN ESPECIAL", resultados)

    def test_incidentes_en_los_tres_estados_con_su_historial(self):
        estados = {}
        for inc in self.db.docs["incidentes"]:
            estados[inc["estado"]] = estados.get(inc["estado"], 0) + 1
            if inc["estado"] == "nuevo":
                self.assertEqual(len(inc["historial"]), 1)
            if inc["estado"] == "en_atencion":
                self.assertEqual(len(inc["historial"]), 2)
            if inc["estado"] == "cerrado":
                self.assertEqual(len(inc["historial"]), 3)
        self.assertEqual(set(estados), set(base_datos.ESTADOS_INCIDENTE))

    def test_incidentes_en_varias_semanas(self):
        semanas = set()
        for inc in self.db.docs["incidentes"]:
            semanas.add(inc["creado"].isocalendar()[1])
        self.assertGreaterEqual(len(semanas), 3)

    def test_riesgos_criticos_y_riesgo_residual_menor(self):
        criticos = 0
        for r in self.db.docs["riesgos_eticos"]:
            if r["puntaje"] >= base_datos.NIVEL_CRITICO:
                criticos += 1
            self.assertLess(r["puntaje_residual"], r["puntaje"])
        self.assertGreaterEqual(criticos, 2)

    def test_estan_los_riesgos_de_la_propia_implementacion(self):
        texto = ""
        for r in self.db.docs["riesgos_eticos"]:
            texto += r["descripcion"].lower() + " "
        for palabra in ["alucinaciones", "ortografía informal", "privacidad", "dependencia"]:
            self.assertIn(palabra, texto)

    def test_cargar_dos_veces_choca_por_las_placas_repetidas(self):
        with self.assertRaises(base_datos.ErrorBD):
            datos_demo.cargar(self.db)


class TestConfirmacion(unittest.TestCase):

    def test_solo_acepta_si(self):
        with mock.patch("builtins.input", return_value="si"):
            self.assertTrue(datos_demo.pedir_confirmacion("x"))
        with mock.patch("builtins.input", return_value=" SI "):
            self.assertTrue(datos_demo.pedir_confirmacion("x"))
        for respuesta in ["no", "", "s", "claro", "yes"]:
            with mock.patch("builtins.input", return_value=respuesta):
                self.assertFalse(datos_demo.pedir_confirmacion("x"), respuesta)


if __name__ == "__main__":
    unittest.main(verbosity=2)
