# Prácticas de IA


- **chef_virtual**: un tutor de cocina con ventana. Usa un modelo que corre en la compu (Ollama con llama3.2), guarda lo que le preguntas y te puede dar un resumen de la plática
- **logismart**: un sistema para controlar la entrada de camiones a un patio logístico. Decide con reglas lógicas si un camión pasa, va a inspección o se bloquea; guarda todo en MongoDB; clasifica correos de incidentes con reglas y con el LLM; tiene un asistente que contesta con lo que hay en la base; una matriz de riesgos éticos con gráfica; y reportes en PDF, CSV y JSON.

## Para correrlo

Necesita Python, Ollama abierto y el modelo descargado:

```
ollama pull llama3.2
pip install -r requirements.txt
```

Para la base de datos copia `.env.example` como `.env` y pon tus datos de MongoDB. El `.env` no se sube a git.

Ya con eso:

```
python chef_virtual/chef_virtual.py
python logismart/app.py
```

La primera respuesta del LLM tarda como un minuto porque tiene que cargar el modelo. Después va más rápido.

## Datos de ejemplo

Para no ver todo vacío hay un script que carga camiones, accesos, incidentes y riesgos de prueba. Te pregunta antes de escribir y todo lo que mete queda marcado como demo.

```
python logismart/datos_demo.py
python logismart/datos_demo.py --borrar
```

El segundo comando borra solo los datos de ejemplo, lo demás no se toca.

## Las reglas

Cada camión se evalúa con estas premisas: P tiene autorización, Q pasa el peso, R lleva materiales peligrosos, S el conductor tiene la certificación vigente, H la hora está dentro del horario (10:00 a 16:00) y W la certificación está por vencer (30 días o menos).

- A = P ∧ S ∧ ¬Q es el acceso estándar
- E = P ∧ (R ∨ Q) es la inspección especial
- B = R ∧ ¬H bloquea los peligrosos fuera de horario (regla nueva)
- L = S ∧ W avisa que hay que renovar la certificación (regla nueva)

El acceso final es A ∧ ¬B.

## El experimento del clasificador

Hay 30 correos etiquetados en `logismart/correos_etiquetados.py`. Para comparar reglas, LLM y la mezcla de los dos:

```
python logismart/evaluacion.py          # solo reglas, es rápido
python logismart/evaluacion.py --llm    # los tres, tarda varios minutos
```

## Pruebas

```
python -m unittest discover -s logismart -p "test_*.py"
```

No usan internet ni Ollama: trabajan con una base falsa en memoria y un LLM de mentiras, así que no tocan el cluster.

## Qué hay en logismart

- `app.py` y los `vista_*.py` son la ventana, uno por pestaña
- `reglas.py` las reglas lógicas y sus tablas de verdad
- `base_datos.py` todo lo de MongoDB
- `clasificador.py` clasifica los correos
- `asistente.py` el chat que consulta la base
- `riesgos.py` y `graficas.py` la matriz de riesgos
- `reportes.py` los PDF, CSV y JSON
- `configuracion.py` y `correo.py` lo de la pestaña Config y el aviso a soporte (en simulación no manda nada)
- `datos_demo.py` y `evaluacion.py` los scripts de arriba
- los `test_*.py` son las pruebas
