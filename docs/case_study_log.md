# Bitácora del caso de estudio

## 2026-07-03 — Transformación Lección 1 (Procesos Politrópicos)

- **Módulo afectado:** `notebooks/01_Lección_Procesos_Politrópicos.ipynb` (nuevo AVA interactivo, derivado de `notebooks_originales/1_Lección_Procesos_Politrópicos.ipynb`).
- **Decisión pedagógica:** convertir la lección expositiva en recurso interactivo con 5 widgets `ipywidgets` (familia politrópica; explorador de procesos en $P$-$v$ y $T$-$s$; integral numérica vs fórmula cerrada; procesos reales del agua sobre el domo de saturación CoolProp; curva $w_{in}(n)$ de mínimo isotérmico / máximo adiabático). Se conservaron las 3 secciones de procesos elementales pero condensadas; se fusionaron las dos derivaciones duplicadas (celdas 7+8) en una sola; se añadió tabla maestra de generalización ($w,q,\Delta u$ por proceso) y recuadro de investigación (eficiencia politrópica de compresores, línea `research-to-classroom`).
- **Correcciones técnicas:** el original NO ejecutaba en el entorno del curso (NumPy 1.26 sin `np.trapezoid`, usado en 2 celdas) → helper `trapz = getattr(np,'trapezoid',np.trapz)`. Arreglados 3 bugs de LaTeX/typo (derivación §5 `R·T/(1-n)`→`R/(1-n)`; `\$4pt]` en isotérmico; encabezados `##1.3`/`##1.5` sin espacio) y ecuaciones movidas a display `$$`.
- **Verificación:** ejecución completa con `nbconvert --execute` sin errores (kernel `thermal-machines`); celda de verificación cruzada fórmula cerrada vs integración numérica de alta resolución, error 0.0000 % (<1 %).
- **Métricas antes/después:** prosa 786→435 palabras (**−44.7 %**, cumple ≥40 %); celdas 20→30; widgets interactivos 0→5; llamadas CoolProp 0→13; figuras generadas por código 5; registrado en `docs/metrics.csv`.
- **Fuentes de investigación:** revisadas `research_sources/` (Wankel, RAMJET, Turboprop, Biofuels, tesis Serpa+Rojas); son ciclos/motores avanzados, no aplican al fundamento politrópico salvo el recuadro breve de compresores incluido.

## 2026-07-03

- **Módulo afectado:** `docs/newsources.md`
- **Decisión pedagógica:** consolidar `research_sources/` en un inventario único orientado a reutilización docente, separando evidencia reutilizable en ejemplos, widgets, código y ejercicios.
- **Justificación:** antes de transformar notebooks conviene hacer trazable qué investigaciones estudiantiles ya contienen modelación, visualización, widgets o código ejecutable, y cuáles solo aportan contexto o estado del arte.
- **Métricas antes/después:** antes no existía un inventario estructurado de `research_sources/`; después existe un documento con 6 fuentes principales, 1 tabla global, 1 tabla desagregada para `EntregasCurso`, taxonomía temática y ranking de esfuerzo/impacto.
