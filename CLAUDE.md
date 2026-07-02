# Proyecto AVA — Máquinas Térmicas (Pontificia Universidad Javeriana)

## Contexto
Soy el profesor del curso de Máquinas Térmicas (Ingeniería Mecánica). Este repositorio contiene los AVA del curso: Jupyter Notebooks ya formateados que estamos transformando en recursos interactivos de alto nivel, incorporando investigación de estudiantes egresados del curso, y documentando todo como caso de estudio para un artículo científico de docencia en inglés.

## Tres líneas de trabajo (skills asociadas)
1. `ava-notebook-enhancer` — interactividad (ipywidgets + CoolProp), texto condensado, ecuaciones en Markdown.
2. `research-to-classroom` — módulos de frontera desde tesis/artículos estudiantiles.
3. `teaching-case-docs` — documentación continua, LaTeX/TikZ, artículo en inglés.

## Estructura del repositorio
```
notebooks_originales/          # AVAs originales del curso, numerados por semana (01_..., 02_...)
notebooks/          # nuevos AVAs del curso desarrollados en este proyecto, numerados por semana (01_..., 02_...)
research_sources/   # PDFs de tesis y artículos estudiantiles (solo lectura)
docs/               # Caso de estudio, bitácora, métricas, paper (ver skill teaching-case-docs)
env/                # environment.yml / requirements.txt del JupyterHub del curso
```

## Reglas globales
- Termodinámica siempre con CoolProp; unidades SI; convención de estados numerados coherente con Cengel & Boles.
- Antes de editar un notebook original: leerlo completo, leer los research_sources que puedan mejorar o complementar el notebook original, proponer plan de transformación e inclusión de nuevos contenidos, esperar aprobación.
- Después de editar: ejecutar el notebook completo sin errores y actualizar `docs/metrics.csv` y `docs/case_study_log.md`.
- Nunca modificar `research_sources/`. Nunca borrar ejercicios/evaluaciones sin confirmación.
- Todo diagrama conceptual del proyecto: TikZ standalone. Todo gráfico dentro de notebooks: generado por código.
- Commits en español, mensajes descriptivos por notebook/módulo; una rama por notebook grande.
- La bitácora (`docs/case_study_log.md`) se actualiza en CADA sesión: el paper se escribe desde ella.

## Definición de "terminado" para un notebook
Ejecuta sin errores de punta a punta; ≥1 widget interactivo por concepto central;
prosa reducida ≥40% respecto a la versión original (registrar en metrics.csv);
celda de verificación contra caso de referencia con error <1%; bitácora actualizada.
