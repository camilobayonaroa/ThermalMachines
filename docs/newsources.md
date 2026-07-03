# Inventario de `research_sources/`

**Generado:** 2026-07-03

## 1. Notas metodológicas

- Este inventario cubre las seis carpetas temáticas de `research_sources/` y no modifica ningún archivo fuente.
- `Temas incluidos` se reporta como conteo curado de subtemas reutilizables en clase, no como número bruto de secciones.
- `Palabras de prosa` excluye bloques de código, ecuaciones y ruido de marcado; en PDF/DOCX es una aproximación razonable basada en extracción de texto.
- `Ecuaciones LaTeX` se cuentan de forma confiable en `.tex` y notebooks; en carpetas basadas solo en PDF se reporta `0 recuperables`.
- `Figuras generadas por código` contabiliza salidas gráficas almacenadas en notebooks y figuras generadas directamente en LaTeX; en PDF solo se reportan como estáticas recuperables.
- `Widgets existentes` se reporta como celdas de código que implementan widgets, con referencias detectadas entre paréntesis cuando aporta contexto.
- Carpetas con versiones redundantes:
  - `Biofuels Combustion`: se usa `Taylor&Francis_R1.tex` como manuscrito principal.
  - `Wankel`: se usa `main.tex` + `Anexos.tex`; se excluye `Correcciones.tex` para no duplicar el mismo trabajo.
  - `TRABAJO DE GRADO SERPA + ROJAS`: se trata como carpeta archivo/documental; parte de su contenido se superpone temáticamente con `Wankel`.

## 2. Tabla principal

| Fuente | Archivo(s) primario(s) usados | Temas incluidos | Palabras de prosa | Ecuaciones | Figuras estáticas | Figuras generadas por código | Widgets existentes | Dependencias importadas | Código ejecutable |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| `Biofuels Combustion` | `Taylor&Francis_R1.tex` | 7 | 5,644 | 59 | 13 | 0 | 0 | `amsmath`, `amssymb`, `hyperref`, `tabularx`, `tikz`, `xcolor` | No |
| `RAMJET Engine` | `main.tex` | 8 | 7,360 | 60 | 6 | 3 | 0 | `amsmath`, `amssymb`, `pgfplots`, `pgfplotstable`, `siunitx`, `tikz` | No |
| `Turboprop Engine` | `main.tex`, `RadialBEMT-Picard.ipynb`, `.mlx/.slx` | 10 | 15,416 | 38 | 41 | 41 | 0 | `MATLAB/Simulink`, `numpy`, `pandas`, `matplotlib`, `dolfin`, `gmsh`, `mshr` | Sí |
| `Wankel` | `main.tex`, `Anexos.tex` | 10 | 14,143 | 50 | 43 | 0 | 0 | `amsmath`, `tikz`, `pgfgantt`, `natbib`, `biblatex`, `tabularx` | No |
| `TRABAJO DE GRADO SERPA + ROJAS` | `TG253011__FINAL.pdf`, `ANEXOS.pdf`, `PG251011_DIAPOSITIVAS.pdf`, `Motor_rotativo_Wankel.pdf`, `Ejercicios seminario .docx` | 6 | 29,812 | 0 recuperables | ~64 | 0 recuperables | 0 | Archivo PDF/DOCX; sin imports reutilizables | No |
| `EntregasCurso` | 6 notebooks `.ipynb` | 8 | 102,754 | 562 | 21 | 101 | 11 celdas (114 refs.) | `CoolProp`, `ipywidgets`, `numpy`, `pandas`, `scipy`, `matplotlib`, `plotly` | Sí |

## 3. Temas por fuente

### `Biofuels Combustion`

- Composición elemental de EFB y PMF.
- Estequiometría y relación aire-combustible.
- Modelado cinético de combustión.
- Estimación de energía liberada y potencia.
- Evolución temporal de especies químicas.
- Efecto del AFR sobre calor liberado y temperatura adiabática.
- Efecto de humedad y comparación energética entre biomásicos.

### `RAMJET Engine`

- Arquitectura funcional del motor RAMJET.
- Variables operativas y supuestos de modelado.
- Flujo compresible en inlet y corriente libre.
- Modelo de compresión aerodinámica.
- Modelo de cámara de combustión.
- Tobera convergente-divergente.
- Empuje y métricas globales de desempeño.
- Geometría paramétrica, discretización y análisis de sensibilidad.

### `Turboprop Engine`

- Ciclo Brayton aplicado al PT6A.
- Compresión axial y centrífuga.
- Cámara de combustión y sección de turbina.
- Ejes rotativos y balance de potencia.
- Hélice McCauley y teoría BEMT.
- Implementación Traub/XFOIL/FEniCS.
- Modelado atmosférico y condiciones operativas.
- Control de combustible y velocidad.
- Gobernador y control PID.
- Validación integral y evaluación con mezclas de combustibles.

### `Wankel`

- Geometría rotor-estator y parámetros geométricos.
- Desarrollo conceptual del ciclo Wankel de seis tiempos.
- Ley de volumen y modelo termodinámico.
- Caso A: sobrealimentación con `supercharger`.
- Caso B: inyección de agua.
- Caso C: válvula de expansión.
- Torque, potencia y eficiencia térmica.
- Implementación discreta y simulación computacional.
- Comparación entre motor Wankel 6T y 4T.
- Extensiones futuras: configuraciones 3-4 y 4-5, manufacturabilidad y validación experimental.

### `TRABAJO DE GRADO SERPA + ROJAS`

- Problema, justificación y contexto energético.
- Estado del arte del motor Wankel.
- Modelo termo-mecánico y ciclo de combustión.
- Líneas de continuidad y trabajo futuro.
- Material de seminario para estructurar contexto general, tecnológico y técnico-científico.
- Diapositivas de síntesis para comunicación y defensa del proyecto.

### `EntregasCurso`

- Combustibles y cinética para Fórmula 1.
- Turboalimentación en Fórmula 1.
- Intercoolers en Fórmula 1.
- Intercooler aire-aire acoplado a motor diésel.
- Planta termoeléctrica Brayton-Rankine con equipos integrados.
- Fisión, fusión y ciclo Rankine en planta nuclear.
- Condensador de superficie y modelación termo-fluida.
- Disipación térmica en dispositivos electrónicos.

## 4. Desagregado de `EntregasCurso`

| Notebook | Temas incluidos | Prosa | Ecuaciones | Figuras estáticas | Figuras generadas por código | Widgets existentes | Dependencias importadas | Código ejecutable |
|---|---:|---:|---:|---:|---:|---:|---|---|
| `ProyectoTérmicas1.ipynb` | 3 | 14,056 | 40 | 11 | 13 | 6 celdas (87 refs.) | `ipywidgets`, `numpy`, `pandas`, `scipy`, `matplotlib`, `plotly` | Sí |
| `Entrega_Final_Proyecto_Planta_del_señor_Vernns_.ipynb` | 4 | 12,708 | 103 | 4 | 41 | 5 celdas (27 refs.) | `CoolProp`, `ipywidgets`, `numpy`, `pandas`, `scipy`, `matplotlib`, `plotly` | Sí |
| `ENTREGA_FINAL_TERMICAS.ipynb` | 4 | 7,075 | 201 | 0 | 18 | 0 | `numpy`, `pandas`, `matplotlib` | Sí |
| `Entrega_3_Proyecto_Maquinas_Termicas.ipynb` | 6 | 65,366 | 196 | 5 | 17 | 0 | `numpy`, `pandas`, `scipy`, `matplotlib`, `math` | Sí |
| `ProyectoCorte3 (1).ipynb` | 4 | 2,593 | 15 | 1 | 4 | 0 | `numpy`, `pandas`, `scipy`, `matplotlib`, `itertools` | Sí |
| `Taller_Tercer_Corte_Intercooler.ipynb` | 4 | 956 | 7 | 0 | 8 | 0 | `numpy`, `scipy`, `matplotlib` | Sí |

## 5. Ranking de esfuerzo / impacto para transformación interactiva

| Rank | Fuente candidata | Potencial de reutilización | Impacto | Esfuerzo | Justificación |
|---|---|---|---|---|---|
| 1 | `EntregasCurso/ProyectoTérmicas1.ipynb` | Widgets de AFR, LHV, HRR, emisiones, turbo e intercooler | Muy alto | Medio | Ya contiene widgets y comparaciones directas entre combustibles; es el puente más corto a notebooks interactivos. |
| 2 | `EntregasCurso/Entrega_Final_Proyecto_Planta_del_señor_Vernns_.ipynb` | Fisión, fusión, Rankine nuclear y condensador | Muy alto | Medio | Tiene base matemática fuerte y widgets ya implementados para convertir en módulos avanzados. |
| 3 | `Turboprop Engine` | PT6A + BEMT + gobernador + validación | Muy alto | Alto | Es la fuente más rica para un notebook de frontera, pero exige traducción desde Matlab/Simulink y notebook técnico. |
| 4 | `RAMJET Engine/main.tex` | Flujo compresible 1D y sensibilidad geométrica | Alto | Medio | Modelo bien estructurado, con parametrización clara y buen potencial para sliders y estudios paramétricos. |
| 5 | `ENTREGA_FINAL_TERMICAS.ipynb` | Intercooler `epsilon-NTU` + transitorio + acople combustión | Alto | Medio | El modelo ya está organizado por balances y resultados; requiere empaquetar visualizaciones y controles. |
| 6 | `Wankel` + `Taller_Tercer_Corte_Intercooler.ipynb` | Geometría, P-V, torque y acople turbo/intercooler | Alto | Alto | Muy atractivo pedagógicamente, pero la migración a notebooks reproducibles demanda reconstrucción gráfica y modularización. |
| 7 | `Entrega_3_Proyecto_Maquinas_Termicas.ipynb` | Planta combinada Brayton-Rankine por equipos | Alto | Alto | Puede desagregarse en varios notebooks temáticos, aunque hoy está demasiado denso y textual. |
| 8 | `Biofuels Combustion/Taylor&Francis_R1.tex` | Cinética, estequiometría, AFR y humedad en biomasa | Medio-alto | Alto | Excelente fuente para modelación de combustión, pero requiere migrar de artículo a notebook reproducible. |
| 9 | `ProyectoCorte3 (1).ipynb` | Resistencias térmicas y disipación electrónica | Medio | Bajo-medio | Buen caso corto para ejercicios o laboratorio computacional. |
| 10 | `TRABAJO DE GRADO SERPA + ROJAS` | Lecturas, contexto y ejercicios de discusión | Bajo-medio | Bajo | Aporta narrativa, estado del arte y discusión, más que código o widgets listos para reutilizar. |

## 6. Recomendación de uso pedagógico

- `Ejemplos interactivos inmediatos`: `ProyectoTérmicas1.ipynb`, `Entrega_Final_Proyecto_Planta_del_señor_Vernns_.ipynb`, `ENTREGA_FINAL_TERMICAS.ipynb`.
- `Módulos avanzados de modelación`: `Turboprop Engine`, `RAMJET Engine`, `Wankel`.
- `Ejercicios o talleres cortos`: `ProyectoCorte3 (1).ipynb`, `Taller_Tercer_Corte_Intercooler.ipynb`.
- `Lecturas de frontera y contexto`: `Biofuels Combustion`, `TRABAJO DE GRADO SERPA + ROJAS`.
