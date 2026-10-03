# Prácticas de IA

Dos proyectos hechos para la materia de Fundamentos de Inteligencia Artificial.

| Carpeta | Qué es |
|---|---|
| `chef_virtual/` | **Práctica 2.** Tutor de cocina con un LLM local (Ollama), con interfaz gráfica y resumen del historial. |
| `logismart/` | **Proyecto LogiSmart.** Centro de control de accesos para un patio logístico: reglas lógicas, MongoDB, clasificador híbrido (reglas + LLM), asistente con consulta a la base, matriz de riesgos éticos y reportes. |

## Requisitos

- Python 3.10 o más nuevo
- [Ollama](https://ollama.com/download) instalado y abierto, con el modelo `llama3.2`:

```bash
ollama pull llama3.2
```

- Las librerías:

```bash
pip install -r requirements.txt
```

## Configuración de MongoDB

Copia `.env.example` como `.env` (en la raíz) y llena tus datos. El `.env` está en `.gitignore`, no se sube.

```
MONGO_USER=...
MONGO_PASSWORD=...
MONGO_CLUSTER=...
MONGO_DB=...
```

## Cómo se usa

```bash
python chef_virtual/chef_virtual.py     # el tutor de cocina
python logismart/app.py                 # el sistema LogiSmart
```

Datos de demostración (pide confirmación antes de escribir y se pueden borrar):

```bash
python logismart/datos_demo.py
python logismart/datos_demo.py --borrar
```

Evaluación del clasificador con los 30 correos etiquetados (con `--llm` compara también el LLM y el híbrido, tarda varios minutos):

```bash
python logismart/evaluacion.py
python logismart/evaluacion.py --llm
```

## Pruebas

```bash
python -m unittest discover -s logismart -p "test_*.py"
```

Las pruebas no usan el cluster ni Ollama: trabajan con una base en memoria (`base_en_memoria.py`) y un LLM simulado.

## Cómo está organizado LogiSmart

| Capa | Archivos |
|---|---|
| Reglas lógicas | `reglas.py` |
| Datos (MongoDB) | `base_datos.py`, `datos_demo.py` |
| IA | `clasificador.py`, `asistente.py`, `correos_etiquetados.py`, `evaluacion.py` |
| Servicios | `riesgos.py`, `reportes.py`, `correo.py`, `configuracion.py` |
| Interfaz | `app.py`, `vista_*.py`, `graficas.py` |
| Pruebas | `test_*.py`, `base_en_memoria.py` |

Pestañas de la aplicación: Panel, Acceso, Simulador, Camiones (con bitácora), Incidentes, Asistente, Riesgos, Reportes y Config.

### Reglas

- `A = P ∧ S ∧ ¬Q` acceso estándar
- `E = P ∧ (R ∨ Q)` inspección especial
- `B = R ∧ ¬H` bloqueo por horario (materiales peligrosos fuera de 10:00 a 16:00)
- `L = S ∧ W` alerta de renovación (certificación vigente pero por vencer)
- Acceso final: `A ∧ ¬B`

Donde `P` autorización previa, `Q` peso excedido, `R` materiales peligrosos, `S` certificación vigente, `H` dentro del horario y `W` certificación por vencer.
