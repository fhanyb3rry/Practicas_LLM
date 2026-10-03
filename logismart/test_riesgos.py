import unittest

import base_datos
import riesgos
from base_en_memoria import BaseEnMemoria


def riesgo(antes, despues):
    return {"puntaje": antes, "puntaje_residual": despues}


class TestNiveles(unittest.TestCase):

    def test_limites(self):
        casos = {1: "bajo", 4: "bajo", 5: "medio", 9: "medio", 10: "alto", 16: "alto", 17: "crítico", 25: "crítico"}
        for puntaje in casos:
            self.assertEqual(riesgos.nivel(puntaje), casos[puntaje], puntaje)

    def test_contar_por_nivel(self):
        lista = [riesgo(20, 6), riesgo(12, 3), riesgo(4, 1)]
        self.assertEqual(riesgos.contar_por_nivel(lista), {"bajo": 1, "medio": 0, "alto": 1, "crítico": 1})
        self.assertEqual(riesgos.contar_por_nivel(lista, "puntaje_residual"),
                         {"bajo": 2, "medio": 1, "alto": 0, "crítico": 0})

    def test_resumen(self):
        r = riesgos.resumen([riesgo(20, 6), riesgo(10, 4)])
        self.assertEqual(r, {"total": 2, "promedio_antes": 15.0, "promedio_despues": 5.0,
                             "criticos_antes": 1, "criticos_despues": 0})

    def test_resumen_sin_riesgos(self):
        self.assertEqual(riesgos.resumen([])["total"], 0)


class TestCrudRiesgos(unittest.TestCase):

    def setUp(self):
        self.db = BaseEnMemoria()
        self.id = self.db.crear_riesgo("Clasificador", "Alucinaciones", "seguridad", 4, 5, "revisión", 2, 3)

    def test_puntajes_al_crear(self):
        doc = self.db.obtener("riesgos_eticos", self.id)
        self.assertEqual((doc["puntaje"], doc["puntaje_residual"]), (20, 6))

    def test_sin_residual_se_queda_igual_que_el_original(self):
        otro = self.db.obtener("riesgos_eticos", self.db.crear_riesgo("m", "d", "otro", 3, 3))
        self.assertEqual(otro["puntaje_residual"], 9)

    def test_editar_recalcula_y_guarda_el_historico(self):
        self.assertTrue(self.db.editar_riesgo(self.id, {"prob_residual": 1, "mitigacion": "más revisión"}))
        doc = self.db.obtener("riesgos_eticos", self.id)
        self.assertEqual(doc["puntaje_residual"], 3)
        self.assertEqual(doc["mitigacion"], "más revisión")
        self.assertEqual(len(doc["historico"]), 1)
        self.assertEqual(doc["historico"][0]["puntaje_residual"], 6)

    def test_escala_invalida_se_rechaza_al_editar(self):
        with self.assertRaises(base_datos.ErrorBD):
            self.db.editar_riesgo(self.id, {"probabilidad": 9})
        self.assertEqual(self.db.obtener("riesgos_eticos", self.id)["probabilidad"], 4)

    def test_eliminar(self):
        self.assertTrue(self.db.eliminar("riesgos_eticos", self.id))
        self.assertEqual(self.db.docs["riesgos_eticos"], [])
        self.assertFalse(self.db.eliminar("riesgos_eticos", self.id))

    def test_listar_ordenado_por_puntaje(self):
        self.db.crear_riesgo("m", "chico", "otro", 1, 2)
        self.db.crear_riesgo("m", "grande", "otro", 5, 5)
        puntajes = []
        for doc in self.db.listar("riesgos_eticos", {}, campo_orden="puntaje"):
            puntajes.append(doc["puntaje"])
        self.assertEqual(puntajes, [25, 20, 2])


if __name__ == "__main__":
    unittest.main(verbosity=2)
