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

Transforma notebooks_originales/01_Lección_Procesos_Politrópicos.ipynb según la skill ava-notebook-enhancer.
Primero preséntame el plan de transformación celda por celda (qué prosa se elimina, qué ecuaciones se añaden, qué widgets se crean) y espera mi aprobación. Requisitos específicos: widget de los procesos termodinámicos con sliders de P, T sobre los diagramas P-V y T-s. Algunos sobre el domo de saturación CoolProp;
Demostraciones de las integrales bajo el área P-V que conforman el cálculo del trabajo involucrado en cada proceso.
widget de trabajo del proceso comparado contra las integrales manuales; 
Reflexiones sobre la minimización o maximización del trabajo de cada proceso.
Generalización de los procesos en un proceso politrópico con la tabla específica de cada proceso y trabajo.
Al terminar: ejecuta el notebook completo, actualiza metrics.csv y la bitácora.


Transforma notebooks_originales/2_Lección_Ciclos_Termodinámicos.ipynb según la skill ava-notebook-enhancer.
Primero preséntame el plan de transformación celda por celda (no elimines prosa, pero si revisa qué ecuaciones se añaden, qué widgets se crean para visualizar mejor los conceptos) y espera mi aprobación. 
Requisitos específicos: widget de los procesos termodinámicos con sliders de P, T sobre los diagramas P-V y T-s. Algunos sobre el domo de saturación CoolProp, por ejemplo cuando explicamos Rankine y Rankine inverso para refrigeración;
Demostraciones de las integrales bajo el área P-V que conforman el cálculo del trabajo involucrado en cada ciclo, así como el calor recibido o rechazado, el cálculo de las eficiencias, etc.
widget de trabajo del proceso comparado contra las integrales manuales; 
Reflexiones sobre la minimización o maximización del trabajo de cada ciclo termodinámico.
Generalización de los procesos en un proceso politrópico con la tabla específica de cada proceso y trabajo completo para los ciclos, así, reflexionando cómo varían las eficiencias si se juega con la constante de los procesos.
Revisa que se cumpla perfectamente el objetivo de aprendizaje: comparar la eficiencia de todos los ciclos entre si, haciéndo un escenario comparable entre ellos: siendo todos máquinas térmicas que operan entre una fuente y un sumidero de calor. Ojalá igualar las temperaturas y presiones de la fuente y el sumidero de calor y realizar una formulación adaptada a esas condiciones de operación para todos los ciclos y así hacer comparativas sus eficiencias como máquinas térmicas. Revisa muy bien que esto sea claro, tanto en la demostración teórica de la formulación de todos los ciclos en estos términos, así como en la comparación mediante el juego de fuente y sumidero a través de un widget, así como la comparación de los ciclos variándole las constantes particulares a algunos de ellos (como la relación de compresión, corte, etc) en un widget.
Al terminar: ejecuta el notebook completo, actualiza metrics.csv y la bitácora.

Transforma notebooks_originales/3_Lección_Ciclos_Biogeoquímicos.ipynb según la skill ava-notebook-enhancer.
Primero preséntame el plan de transformación celda por celda (no elimines prosa, no elimines mi declaración de autor, pero si revisa qué ecuaciones se añaden, genera los diagramas propios que actualmente se enlazan desde internet, qué widgets se crean para visualizar mejor los conceptos) y espera mi aprobación.
Requisitos específicos: Separa los contenidos, el actual cuadernillo debería se sólo de ciclos biogeoquímicos, separar e indipendizar el contenido de los combustibles fósiles. Además, genera widget de los diagramas geológicos actuales de los compuestos o elementos químicos, incluso genera algunos nuevos explicando la cosmología de los elementos químicos y especialmente del carbono (producido en el interior de estrellas pesadas) y de las concentraciones a lo largo de las eras geológicas en la atmósfera terrestre. Sería ideal que los widgets de los ciclos pudieran tener algo más de interactividad, o inclusive de tener las capas de rótulos con los flujos másicos, energéticos o temporales.
Los balances simplificados actualmente sobran, mejorarlos o quitarlos.
Genera entonces el nuevo notebook 4_Lección_Combustibles_Fósiles.ipynb según la skill ava-notebook-enhancer con el contenido que separaste del notebook original 03.

Transforma notebooks_originales/4_Lección_Repaso_Química.ipynb según la skill ava-notebook-enhancer.
Primero preséntame el plan de transformación celda por celda (no elimines prosa, no elimines mi declaración de autor, pero si revisa qué ecuaciones se añaden, genera los diagramas propios que actualmente se enlazan desde internet, qué widgets se crean para visualizar mejor los conceptos) y espera mi aprobación.
Requisitos específicos: Separa este cuaderno de repaso de conceptos químicos de otro nuevo que sea de cinética de reacción. Para el cuaderno de conceptos químicos, mejora la explicación científica (física electrónica o nuclear) de los distintos conceptos químicos. Además, genera widget de los fenómenos para que se puedan visualizar muy bien, incluso genera algunos nuevos explicando la física nuclear y los fenómenos que producen dichos elementos y relaciones químicas y especialmente de los enlaces de carbono. Sería ideal que los widgets pudieran tener algo más de interactividad y rotación o visualización 3d para las uniones atómicas. Aparte, quiero que mejores muchísimo la visualización de las rupturas electrónicas y formaciones electrónicas que generan las reacciones químicas.
En términos de exposición, las conexiones lógicas entre los conceptos están débiles, están muy dadas como listado de conceptos, por lo que es mejor hilar lógicamente la exposición.

Transforma notebooks_originales/5_Lección_Modelación_Combustión.ipynb según la skill ava-notebook-enhancer.
Primero preséntame el plan de transformación celda por celda (no elimines prosa, no elimines mi declaración de autor, pero si revisa qué ecuaciones se añaden, genera los diagramas propios que actualmente se enlazan desde internet, qué widgets se crean para visualizar mejor los conceptos) y espera mi aprobación.
Requisitos específicos: Separa este cuaderno de modelación de la cinética (balance de masa y energía) mediante ecuaciones diferenciales de otro nuevo que sea de cinética de combustión de un hidrocarburo con oxidante (y luego aire). Para el cuaderno de conceptos químicos de la cinética de la reacción, mejora la explicación/visualización científica de los distintos conceptos de ecuaciones diferenciales acopladas para modelar los cambios de concentración y aporte de energía en el tiempo. Además, genera widget de los fenómenos para que se puedan visualizar muy bien, incluso genera algunos nuevos explicando los conjuntos del modelo SIR (y sus concentraciones en el tiempo) y los fenómenos que producen dichas relaciones de contagio, recuperación etc y cómo estas se modelan como productos entre las concentraciones (positivas o negativas) en las relaciones diferenciales químicas. Sería ideal que los widgets pudieran tener algo más de interactividad y visualización de las dinámicas de los conjuntos para visualizar los cambios en las concentraciones.
En términos de exposición, las conexiones lógicas entre los conceptos están bien logradas actualmente: pasando desde la reacción más sencilla hasta la más compleja (con cualquier hidrocarburo como combustible).

Ayúdame a hacer un nuevo notebook (bonus) sobre reacciones nucleares de fisión y fusión, que el estudiante encuentre tras estudiar el nuevo notebook de Repaso de Química. Toma los conceptos, simulaciones y resultados de /research_sources/EntregasCurso/ENTREGA_..

Transforma notebooks_originales/6_Lección_Tecnología_Combustión.ipynb según la skill ava-notebook-enhancer.
Primero preséntame el plan de transformación celda por celda (no elimines prosa, no elimines mi declaración de autor, pero si revisa qué ecuaciones se añaden, genera los diagramas propios que actualmente se enlazan desde internet, qué widgets se crean para visualizar mejor los conceptos) y espera mi aprobación.
Requisitos específicos: Edita todo lo que ya se contó sobre combustibles fósiles en el cuadernillo 04. Para el cuaderno de tecnología mejora la explicación/visualización científica de los distintos conceptos tecnológicos de mejora de la inyección de combustible, aire, remoción de cenizas, precalentamiento y economizadores, mejora en la turbulencia y mezcla, entre otras tecnologías que permiten la mejor combustión (estequiométrica). Quiero ser muy claro y lógico en todas las ideas/razones físicoquimicas que explican el funcionamiento de dichas tecnologías con respecto a la teoría de la combustión. Además, genera widget de los fenómenos para que se puedan visualizar muy bien, incluso genera algunos nuevos explicando los fenómenos de interacción entre el combustible y el aire, o la generación de ceniza e impermeabilización del combustible respecto del aire. Entre otros fenómenos que son importantes. Sería ideal que los widgets pudieran tener algo más de interactividad y visualización de las dinámicas de los conjuntos para visualizar los cambios en las concentraciones.
En términos de exposición, las conexiones lógicas deberían mejorarse: contando cada fenómeno o razón por la cual cada inclusión tecnológica es importante (más allá de organizar el cuadernillo respecto del tipo de hidrocarburo como combustible sólido, líquido y gaseoso).




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
