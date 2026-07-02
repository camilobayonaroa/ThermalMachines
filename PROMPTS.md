# Prompts para Claude Code — Proyecto AVA Máquinas Térmicas

Prompts listos para copiar. Asumen que CLAUDE.md y las tres skills están instalados
en el repositorio (`.claude/skills/`).

## Fase 0 — Auditoría inicial (una sola vez)
```
Haz un inventario completo de notebooks_originales/: para cada .ipynb reporta en una tabla (docs/audit.md) número de celdas markdown/código, palabras de prosa, ecuaciones LaTeX existentes, figuras estáticas vs. generadas por código, widgets existentes, dependencias importadas, y si ejecuta sin errores en el entorno de env/.
Prioriza los notebooks en un ranking de esfuerzo/impacto para la transformación interactiva. No modifiques nada todavía.
```
```
Haz un inventario completo de research_sources/: para cada tema reporta en una tabla (docs/newsources.md) número de temas incluidos en las investigaciones que se explican en el curso, palabras de prosa, ecuaciones LaTeX existentes, figuras estáticas vs. generadas por código, widgets existentes, dependencias importadas, y si hay código ejecutable.
Lista e inventaría los temas en research_sources/ para que puedan luego ser incluidos como ejemplos, códigos widgets, o ejercicios dentro de los nuevos notebooks en un ranking de esfuerzo/impacto para la transformación interactiva. No modifiques nada todavía.
```

## Fase 1 — Transformación de un notebook
```
Transforma notebooks_originales/03_ciclo_rankine.ipynb según la skill ava-notebook-enhancer.
Primero preséntame el plan de transformación celda por celda (qué prosa se elimina,
qué ecuaciones se añaden, qué widgets se crean) y espera mi aprobación.
Requisitos específicos: widget del ciclo Rankine con sliders de P_caldera, P_cond
y T_sobrecalentamiento sobre diagrama T-s con domo de saturación CoolProp;
widget de Rankine con recalentamiento comparado contra el simple; tabla de estados
autocalculada; celda de verificación contra el ejemplo 10-1 de Cengel.
Al terminar: ejecuta el notebook completo, actualiza metrics.csv y la bitácora.
```

Variante para lote:
```
Aplica el mismo proceso, uno por uno con plan+aprobación, a los notebooks 04 (Brayton),
05 (Otto/Diesel) y 06 (refrigeración por compresión de vapor). En Brayton incluye
widget de regeneración/interenfriamiento; en refrigeración, comparador de refrigerantes
(R134a, R410A, R290, R744) en diagrama P-h.
```

## Fase 2 — Módulo de frontera desde investigación estudiantil
```
En research_sources/tesis_perez_2025_ORC.pdf está la tesis de un egresado sobre
ciclos Rankine orgánicos para recuperación de calor residual. Siguiendo la skill
research-to-classroom: extrae el modelo, los supuestos y los datos de validación;
propónme el anclaje al sílabo; reimplementa el modelo en Python+CoolProp validando
contra al menos una figura de la tesis con % de error documentado; y crea el módulo
notebooks/frontera_ORC.ipynb con el widget comparativo Rankine-agua vs. ORC
(tolueno, R245fa, ciclopentano) en el mismo diagrama T-s. Registra la cita BibTeX
y la trazabilidad.
```

## Fase 3 — Documentación y artículo
```
Según la skill teaching-case-docs, inicializa docs/ completo: methodology.tex,
los tres diagramas TikZ standalone (arquitectura del AVA, pipeline de transferencia,
línea de tiempo), metrics.csv con lo acumulado en la bitácora, y paper/main.tex
en elsarticle con la estructura del artículo en inglés. Redacta ya Introduction
y Methodology en borrador a partir de case_study_log.md. Compila todo con latexmk
y corrige warnings.
```

Actualización periódica:
```
Cierra la sesión: actualiza case_study_log.md y metrics.csv con lo hecho hoy,
regenera las figuras pgfplots del paper desde metrics.csv y recompila paper/main.tex.
Dame un resumen de avance del caso de estudio en 5 líneas.
```

## Prompts de calidad transversales
```
Ejecuta todos los notebooks de notebooks/ de punta a punta y repórtame cualquier
error, warning de deprecación o widget sin valores por defecto razonables.
```
```
Revisa el paper/main.tex como revisor par exigente de una revista de educación
en ingeniería: señala afirmaciones sin evidencia en metrics.csv, retórica inflada,
y claims metodológicos no soportados por la bitácora.
```
