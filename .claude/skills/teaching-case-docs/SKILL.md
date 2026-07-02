---
name: teaching-case-docs
description: >
  Documenta todo el proyecto AVA como caso de estudio de investigación en docencia
  y produce el artículo científico en inglés (LaTeX) con diagramas TikZ. Usar SIEMPRE
  que el usuario mencione documentación, caso de estudio, artículo, paper, metodología,
  LaTeX, TikZ, diagramas del proceso, o cierre de una etapa del proyecto. También
  activar proactivamente al final de cada sesión de trabajo sustantiva para actualizar
  la bitácora.
---

# Teaching Case Docs — Documentación y artículo científico

## Objetivo
Que el proyecto se autodocumente de forma continua (no retrospectiva) para producir
un artículo en inglés sobre la metodología de AVAs interactivos y transferencia de
investigación estudiantil al aula (venue objetivo: *Education for Chemical Engineers*,
*International Journal of Mechanical Engineering Education*, *Computer Applications
in Engineering Education*, o LACCEI).

## Artefactos del repositorio `docs/`
```
docs/
├── methodology.tex        # Documento maestro LaTeX del caso de estudio
├── figures/tikz/          # Un .tex por diagrama TikZ (standalone class)
├── case_study_log.md      # Bitácora cronológica (alimentada por las otras skills)
├── traceability.md        # Fuente investigativa → módulo → semana del curso
├── metrics.csv            # Métricas por notebook: prosa antes/después, nº ecuaciones,
│                          #   nº widgets, tiempo de ejecución, cobertura del sílabo
├── modules_registry.bib   # BibTeX de tesis/artículos estudiantiles incorporados
└── paper/
    ├── main.tex           # Artículo en inglés (elsarticle o IEEEtran según venue)
    └── references.bib
```

## Reglas LaTeX
- Compilar con `latexmk -pdf`; verificar cero warnings de referencias.
- Diagramas SIEMPRE en TikZ como archivos `standalone` incluidos con `\input` o `\includestandalone`; nunca capturas de pantalla para diagramas conceptuales.
- Diagramas TikZ requeridos del caso de estudio:
  1. Arquitectura del AVA (notebook → widgets → CoolProp → estudiante) — `tikz` con `positioning`, `arrows.meta`.
  2. Pipeline de transferencia (tesis estudiantil → validación → módulo → aula) — flowchart.
  3. Línea de tiempo de la metodología por semestres — `pgfgantt` o eje temporal TikZ.
  4. Diagramas termodinámicos vectoriales para el paper con `pgfplots` (exportar datos desde los notebooks a `.dat`).
- Figuras de resultados del paper: generarlas por script (`paper/scripts/`) desde `metrics.csv` con `pgfplots`, garantizando reproducibilidad total.

## Estructura del artículo (inglés)
1. Introduction — active learning, virtual learning environments (VLE/AVA), gap: research-to-classroom transfer in thermal sciences.
2. Context — Mechanical Engineering, Pontificia Universidad Javeriana; course description.
3. Methodology — (a) notebook interactivity redesign, (b) student-research incorporation pipeline, (c) documentation-as-code. Aquí van los TikZ 1–3.
4. Implementation — stack, ejemplos representativos (Rankine widget, módulo sCO2/ORC).
5. Results & metrics — tabla desde `metrics.csv`; opcionalmente percepción estudiantil si hay datos de encuesta.
6. Discussion — transferability, limitations (no controlled experiment salvo que exista), ethics/IRB note si se reportan datos de estudiantes.
7. Conclusions & future work.

## Disciplina de bitácora (obligatoria en cada sesión)
Al cerrar cualquier tarea sustantiva de las otras skills, añadir a `case_study_log.md`:
fecha, notebook/módulo afectado, decisión pedagógica tomada y su justificación,
métricas antes/después. El paper se escribe desde la bitácora, no desde la memoria.

## Idioma
- Notebooks y docs internos: español.
- `paper/` y abstracts: inglés académico, voz activa moderada, sin retórica inflada.
