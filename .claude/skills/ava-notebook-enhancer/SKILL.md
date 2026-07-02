---
name: ava-notebook-enhancer
description: >
  Transforma Jupyter Notebooks de Máquinas Térmicas (AVA) en recursos interactivos:
  widgets dinámicos (ipywidgets), gráficos termodinámicos renderizados con código
  (CoolProp + matplotlib/plotly), texto condensado y ecuaciones en LaTeX/Markdown.
  Usar SIEMPRE que el usuario mencione notebooks, AVA, widgets, interactividad,
  ciclos termodinámicos (Rankine, Brayton, Otto, Diesel, refrigeración), diagramas
  T-s/P-v/h-s, o pida reducir texto retórico y aumentar ecuaciones en un .ipynb.
---

# AVA Notebook Enhancer — Máquinas Térmicas

## Objetivo
Convertir notebooks expositivos en notebooks interactivos de nivel de ingeniería:
menos retórica, más ecuaciones, más simulación manipulable por el estudiante.

## Stack obligatorio
- `CoolProp` para propiedades termodinámicas reales (nunca tablas hardcodeadas salvo validación).
- `ipywidgets` (`interact`, `FloatSlider`, `Dropdown`, `interactive_output` con `VBox/HBox`) para exploración paramétrica.
- `matplotlib` para diagramas T-s, P-v, h-s con domos de saturación calculados con CoolProp; `plotly` cuando convenga hover/zoom.
- `numpy` vectorizado; nada de bucles innecesarios.
- Verificar entorno antes: `pip list | grep -iE "coolprop|ipywidgets|plotly"`.

## Reglas de transformación de celdas Markdown
1. **Ratio texto/ecuación**: máximo 2–3 frases de prosa por bloque de ecuaciones. Eliminar párrafos introductorios retóricos ("A lo largo de la historia...", "Es importante destacar que...").
2. Toda relación física va en display math numerable:
   ```
   $$\eta_{th} = 1 - \frac{q_{out}}{q_{in}} = 1 - \frac{h_4 - h_1}{h_3 - h_2}$$
   ```
3. Definir variables inmediatamente después de la ecuación en una línea compacta: "donde $h_i$ [kJ/kg] son las entalpías en cada estado."
4. Usar tablas Markdown para estados termodinámicos (Estado | P | T | h | s | x).
5. Convención de unidades: SI, con unidades entre corchetes. CoolProp devuelve SI base (Pa, J/kg, K) — convertir explícitamente a kPa/kJ/°C al mostrar.
6. Mantener objetivos de aprendizaje al inicio, en ≤4 viñetas.

## Patrón de celda interactiva (plantilla)
```python
import numpy as np, matplotlib.pyplot as plt
from CoolProp.CoolProp import PropsSI
from ipywidgets import interact, FloatSlider

def rankine(P_boiler_kPa=8000, P_cond_kPa=10, T3_C=500):
    P3, P1 = P_boiler_kPa*1e3, P_cond_kPa*1e3
    h1 = PropsSI('H','P',P1,'Q',0,'Water'); s1 = PropsSI('S','P',P1,'Q',0,'Water')
    v1 = 1/PropsSI('D','P',P1,'Q',0,'Water')
    h2 = h1 + v1*(P3-P1)
    h3 = PropsSI('H','P',P3,'T',T3_C+273.15,'Water'); s3 = PropsSI('S','P',P3,'T',T3_C+273.15,'Water')
    h4 = PropsSI('H','P',P1,'S',s3,'Water')
    eta = ((h3-h4)-(h2-h1))/(h3-h2)
    # ... plot T-s con domo de saturación + ciclo, anotar eta
interact(rankine,
         P_boiler_kPa=FloatSlider(3000, min=1000, max=20000, step=500, description='P caldera [kPa]'),
         P_cond_kPa=FloatSlider(10, min=5, max=100, step=5, description='P cond [kPa]'),
         T3_C=FloatSlider(500, min=300, max=650, step=10, description='T₃ [°C]'));
```
Cada widget debe: (a) recalcular todo el ciclo, (b) redibujar el diagrama, (c) mostrar métricas clave ($\eta_{th}$, $w_{net}$, BWR) como texto anotado en la figura, no solo `print`.

## Domo de saturación reutilizable
Crear una vez por notebook una función `plot_dome(fluid, ax)` que barre calidad 0 y 1 entre el punto triple y crítico con `PropsSI`. Reutilizarla en todos los diagramas.

## Esquemas de máquinas (no gráficos de datos)
Para esquemas de plantas (caldera-turbina-condensador-bomba), usar `schemdraw` o matplotlib con `FancyArrowPatch`; alternativamente celdas con diagramas SVG generados por código. Nunca imágenes estáticas pegadas si pueden generarse por código.

## Flujo de trabajo por notebook
1. Leer el .ipynb completo (`jupyter nbconvert --to script` o parsear JSON) y hacer inventario: celdas de texto, longitud, ecuaciones existentes, figuras estáticas.
2. Proponer al usuario un plan de transformación celda por celda ANTES de editar.
3. Editar preservando la estructura pedagógica (objetivos → teoría → ejemplo resuelto → widget exploratorio → ejercicios).
4. Ejecutar el notebook completo (`jupyter nbconvert --to notebook --execute`) y verificar cero errores.
5. Añadir al final una celda de "Verificación" que compara resultados del widget con un caso de referencia de Cengel/Moran (valores tabulados) con tolerancia <1%.

## No hacer
- No borrar ejercicios ni evaluaciones existentes sin confirmar.
- No introducir dependencias exóticas no disponibles en el JupyterHub del curso sin avisar.
- No dejar widgets sin valores por defecto físicamente razonables.
