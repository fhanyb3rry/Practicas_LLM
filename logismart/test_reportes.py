import csv
import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import datos_demo
import reportes
from base_en_memoria import BaseEnMemoria


class TestReportes(unittest.TestCase):

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.dir = Path(self.carpeta.name)

        self.db = BaseEnMemoria()
        datos_demo.cargar(self.db)
        self.datos = {
            "accesos": self.db.listar("accesos"),
            "incidentes": self.db.listar("incidentes"),
            "riesgos_eticos": self.db.listar("riesgos_eticos", campo_orden="puntaje"),
            "camiones": self.db.listar("camiones"),
        }

    def tearDown(self):
        self.carpeta.cleanup()

    def test_csv_trae_encabezado_y_todas_las_filas_de_cada_coleccion(self):
        for coleccion in self.datos:
            ruta = self.dir / (coleccion + ".csv")
            reportes.exportar_csv(ruta, coleccion, self.datos[coleccion])

            with open(ruta, encoding="utf-8-sig", newline="") as archivo:
                lineas = list(csv.reader(archivo))
            self.assertEqual(len(lineas), len(self.datos[coleccion]) + 1, coleccion)

            esperados = []
            for clave, titulo, ancho in reportes.COLUMNAS[coleccion]:
                esperados.append(titulo)
            self.assertEqual(lineas[0], esperados)

    def test_csv_conserva_acentos_y_usa_bom_para_excel(self):
        ruta = self.dir / "riesgos.csv"
        reportes.exportar_csv(ruta, "riesgos_eticos", self.datos["riesgos_eticos"])
        crudo = ruta.read_bytes()
        self.assertTrue(crudo.startswith(b"\xef\xbb\xbf"))
        self.assertIn("Alucinaciones", crudo.decode("utf-8-sig"))
        self.assertIn("Módulo", crudo.decode("utf-8-sig"))

    def test_csv_de_riesgos_calcula_el_nivel(self):
        ruta = self.dir / "riesgos.csv"
        reportes.exportar_csv(ruta, "riesgos_eticos", self.datos["riesgos_eticos"])
        with open(ruta, encoding="utf-8-sig", newline="") as archivo:
            filas = list(csv.DictReader(archivo))
        self.assertEqual(filas[0]["Nivel"], "crítico")

    def test_csv_sin_datos_solo_trae_el_encabezado(self):
        ruta = self.dir / "vacio.csv"
        reportes.exportar_csv(ruta, "accesos", [])
        with open(ruta, encoding="utf-8-sig", newline="") as archivo:
            self.assertEqual(len(list(csv.reader(archivo))), 1)

    def test_json_es_valido_aunque_haya_fechas_e_ids(self):
        ruta = self.dir / "todo.json"
        reportes.exportar_json(ruta, self.datos, {"camiones_atendidos": 12})
        contenido = json.loads(ruta.read_text(encoding="utf-8"))

        self.assertEqual(contenido["indicadores"], {"camiones_atendidos": 12})
        self.assertEqual(len(contenido["colecciones"]["incidentes"]), 14)
        primero = contenido["colecciones"]["incidentes"][0]
        self.assertIsInstance(primero["_id"], str)
        self.assertIsInstance(primero["creado"], str)
        self.assertIn("historial", primero)

    def test_json_deja_los_acentos_sin_escapar(self):
        ruta = self.dir / "todo.json"
        reportes.exportar_json(ruta, self.datos)
        self.assertIn("Lleva materiales peligrosos", ruta.read_text(encoding="utf-8"))
        self.assertIn("Sesgo en visión nocturna", ruta.read_text(encoding="utf-8"))

    def test_pdf_se_genera_con_todas_las_secciones(self):
        ruta = self.dir / "reporte.pdf"
        reportes.exportar_pdf(ruta, self.datos, {"camiones_atendidos": 12, "incidentes_abiertos": 6,
                                                  "riesgos_criticos": 2},
                              datetime.now() - timedelta(days=30), datetime.now())
        crudo = ruta.read_bytes()
        self.assertTrue(crudo.startswith(b"%PDF"))
        self.assertGreater(len(crudo), 5000)

    def test_pdf_con_secciones_vacias_no_truena(self):
        ruta = self.dir / "vacio.pdf"
        reportes.exportar_pdf(ruta, {"accesos": [], "riesgos_eticos": []})
        self.assertTrue(ruta.read_bytes().startswith(b"%PDF"))

    def test_pdf_aguanta_simbolos_que_su_tipografia_no_tiene(self):
        self.db.crear_riesgo("Módulo ñandú", "Riesgo → grave ∧ raro 😀 ✅ ¿qué?", "otro", 2, 2, "mitigación “rara”")
        datos = {"riesgos_eticos": self.db.listar("riesgos_eticos")}
        ruta = self.dir / "raro.pdf"
        reportes.exportar_pdf(ruta, datos)
        self.assertTrue(ruta.read_bytes().startswith(b"%PDF"))

    def test_para_pdf_cambia_lo_que_no_se_puede_dibujar(self):
        self.assertEqual(reportes.para_pdf("A → B"), "A -> B")
        self.assertEqual(reportes.para_pdf("ñandú ¿sí?"), "ñandú ¿sí?")
        self.assertNotIn("😀", reportes.para_pdf("hola 😀"))

    def test_pdf_con_datos_largos_hace_varias_paginas(self):
        for i in range(120):
            self.db.crear_riesgo("Módulo " + str(i), "Descripción larga " * 6, "otro", 2, 3, "mitigación " * 8)
        ruta = self.dir / "largo.pdf"
        reportes.exportar_pdf(ruta, {"riesgos_eticos": self.db.listar("riesgos_eticos", limite=500)})
        self.assertGreater(ruta.read_bytes().count(b"/Type /Page\n"), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
