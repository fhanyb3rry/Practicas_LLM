import itertools
import unittest
from datetime import date, time

import reglas


class TestReglasOriginales(unittest.TestCase):

    # (P,Q,R,S) -> (A,E) escrito a mano
    ESPERADO = {
        (1, 1, 1, 1): (0, 1), (1, 1, 1, 0): (0, 1), (1, 1, 0, 1): (0, 1), (1, 1, 0, 0): (0, 1),
        (1, 0, 1, 1): (1, 1), (1, 0, 1, 0): (0, 1), (1, 0, 0, 1): (1, 0), (1, 0, 0, 0): (0, 0),
        (0, 1, 1, 1): (0, 0), (0, 1, 1, 0): (0, 0), (0, 1, 0, 1): (0, 0), (0, 1, 0, 0): (0, 0),
        (0, 0, 1, 1): (0, 0), (0, 0, 1, 0): (0, 0), (0, 0, 0, 1): (0, 0), (0, 0, 0, 0): (0, 0),
    }

    def test_tabla_original(self):
        for (p, q, r, s), (a, e) in self.ESPERADO.items():
            res = reglas.evaluar_camion(bool(p), bool(q), bool(r), bool(s))
            self.assertEqual(res["acceso_estandar"], bool(a), (p, q, r, s))
            self.assertEqual(res["inspeccion_especial"], bool(e), (p, q, r, s))

    def test_decidir_no_cambia_A_y_E(self):
        for (p, q, r, s), (a, e) in self.ESPERADO.items():
            d = reglas.decidir(bool(p), bool(q), bool(r), bool(s), H=True)
            self.assertEqual((d["A"], d["E"]), (bool(a), bool(e)))

    def test_tipo_invalido(self):
        with self.assertRaises(TypeError):
            reglas.evaluar_camion(1, False, False, True)


class TestHorario(unittest.TestCase):

    def test_limites(self):
        self.assertTrue(reglas.hora_permitida(time(10, 0)))
        self.assertTrue(reglas.hora_permitida(time(16, 0)))
        self.assertFalse(reglas.hora_permitida(time(9, 59)))
        self.assertFalse(reglas.hora_permitida(time(16, 1)))

    def test_tabla_regla_3(self):
        esperado = {(True, True): False, (True, False): True, (False, True): False, (False, False): False}
        for f in reglas.tabla_regla_horario():
            self.assertEqual(f["B"], esperado[(f["R"], f["H"])])

    def test_peligroso_fuera_de_horario_se_bloquea(self):
        d = reglas.decidir(True, False, True, True, H=False)
        self.assertTrue(d["B"])
        self.assertFalse(d["acceso_final"])
        self.assertEqual(d["semaforo"], "rojo")

    def test_sin_peligrosos_la_hora_no_importa(self):
        d = reglas.decidir(True, False, False, True, H=False)
        self.assertFalse(d["B"])
        self.assertEqual(d["resultado"], "ACCESO ESTÁNDAR")


class TestMotivo(unittest.TestCase):

    def test_motivo_solo_trae_las_conclusiones(self):
        d = reglas.decidir(True, False, True, True, H=False)
        self.assertEqual(len(d["motivo"]), 1)
        self.assertIn("fuera del horario", d["motivo"][0])
        self.assertEqual(d["pasos"][-1], d["motivo"][-1])

    def test_motivo_incluye_el_aviso_de_vencimiento(self):
        d = reglas.decidir(True, False, False, True, H=True, W=True)
        self.assertEqual(len(d["motivo"]), 2)


class TestVigencia(unittest.TestCase):

    HOY = date(2026, 10, 3)

    def test_estados(self):
        self.assertEqual(reglas.estado_certificacion(date(2027, 1, 1), self.HOY)[:2], (True, False))
        self.assertEqual(reglas.estado_certificacion(date(2026, 10, 20), self.HOY)[:2], (True, True))
        self.assertEqual(reglas.estado_certificacion(date(2026, 10, 3), self.HOY)[:2], (True, True))
        self.assertEqual(reglas.estado_certificacion(date(2026, 10, 2), self.HOY)[:2], (False, False))

    def test_alerta_pone_amarillo(self):
        d = reglas.decidir(True, False, False, True, H=True, W=True)
        self.assertTrue(d["L"])
        self.assertEqual(d["semaforo"], "amarillo")

    def test_vencida_no_pasa(self):
        d = reglas.decidir(True, False, False, False, H=True, W=False)
        self.assertEqual(d["resultado"], "ACCESO DENEGADO")


class TestTablaCompleta(unittest.TestCase):

    def test_tiene_64_filas(self):
        self.assertEqual(len(reglas.tabla_completa()), 64)

    def test_sin_autorizacion_nunca_pasa(self):
        for f in reglas.tabla_completa():
            if not f["P"]:
                self.assertFalse(f["acceso_final"])

    def test_explicacion_siempre_trae_pasos(self):
        for p, q, r, s, h, w in itertools.product([True, False], repeat=6):
            self.assertGreaterEqual(len(reglas.decidir(p, q, r, s, h, w)["pasos"]), 7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
