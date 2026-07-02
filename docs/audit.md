# Auditoría de notebooks_originales/
**Generado:** 2026-07-02 | **Entorno analizado:** miniconda Python 3.11.4 (env/ vacío)

---

## 1. Inventario completo

> Notas metodológicas: palabras de prosa excluyen bloques base64, URLs y bloques de código; ecuaciones contabilizadas sobre markdown limpio; imágenes estáticas = embebidas como base64 en markdown + URLs externas; "widgets reales" = celdas de código con `import ipywidgets` o `@interact` (otros notebooks mencionan widgets en prosa pero no los implementan); ejecución = presencia de outputs almacenados en el JSON (no implica que el entorno actual sea suficiente).

### 1.1 Tabla principal

| # | Notebook | MD | Código | Palabras prosa | Ecuac. display | Ecuac. inline | Total ecuac. | Imgs estáticas | Figs generadas | Widgets (celdas) | Dependencias importadas | Estado ejecución |
|---|----------|----|--------|---------------|----------------|---------------|--------------|----------------|----------------|-------------------|-------------------------|-----------------|
| 01 | [1\_Lección\_Procesos\_Politrópicos](../notebooks_originales/1_Lección_Procesos_Politrópicos.ipynb) | 13 | 7 | 1 212 | 10 | 111 | **121** | 0 | 7 | 0 | matplotlib, numpy | ✓ outputs b64 |
| 02 | [2\_Lección\_Ciclos\_Termodinámicos](../notebooks_originales/2_Lección_Ciclos_Termodinámicos.ipynb) | 14 | 14 | 1 259 | 4 | 7 | 11 | 8 | 2 | **1** | CoolProp, ipywidgets, math, matplotlib | ✓ outputs b64 |
| 03 | [3\_Lección\_Ciclos\_Biogeoquímicos](../notebooks_originales/3_Lección_Ciclos_Biogeoquímicos.ipynb) | 26 | 13 | 1 538 | 0 | 0 | 0 | 9 | 10 | 0 | graphviz, matplotlib, networkx, numpy, pandas | ✓ outputs b64 |
| 04 | [4\_Lección\_Repaso\_Química](../notebooks_originales/4_Lección_Repaso_Química.ipynb) | 18 | 13 | 1 473 | 0 | 35 | 35 | 17 | 2 | 0 | graphviz, matplotlib, numpy | ✓ outputs texto |
| 05 | [5\_Lección\_Modelación\_Combustión](../notebooks_originales/5_Lección_Modelación_Combustión.ipynb) | 33 | 17 | 4 482 | 20 | 77 | **97** | 3 | 7 | 0 | matplotlib, numpy, scipy, sklearn | ✗ sin outputs |
| 06 | [6\_Lección\_Tecnología\_Combustión](../notebooks_originales/6_Lección_Tecnología_Combustión.ipynb) | 53 | 1 | 4 603 | 8 | 57 | 65 | **35** | 0 | 0 | graphviz | ✗ sin outputs |
| 07 | [7\_Lección\_Máquinas\_Compresores/Turbinas](../notebooks_originales/7_Lección_Máquinas_CompresoresTurbinasReciprocantes.ipynb) | 38 | 1 | 2 647 | 42 | 82 | **124** | 11 | 1 | 0 | IPython, matplotlib, numpy | ✗ sin outputs |
| 08 | [8\_Lección\_Motores\_Reciprocantes](../notebooks_originales/8_Lección_Motores_Reciprocantes.ipynb) | 36 | 10 | 5 607 | 30 | 99 | **129** | **26** | 7 | 0 | CoolProp, matplotlib, numpy | ✓ outputs b64 |
| 09 | [9\_Lección\_Ensayo\_de\_Motores](../notebooks_originales/9_Leccion_Ensayo_de_motores.ipynb) | 15 | 3 | 987 | 5 | 43 | 48 | 3 | 1 | 0 | math, matplotlib, numpy | ✓ outputs b64 |
| 10 | [10\_Lección\_Plantas\_Turbinas\_Gas](../notebooks_originales/10_Lección_Plantas_Turbinas_Gas.ipynb) | 13 | **0** | 2 502 | 0 | 5 | 5 | **22** | 0 | 0 | — | ✗ sin outputs |
| 11 | [11\_Lección\_Modelamiento\_Turbina\_Gas](../notebooks_originales/11_Lección_Modelamiento_Turbina_de_gas.ipynb) | 37 | 1 | 5 700 | 27 | 106 | **133** | 13 | 0 | 0 | IPython, math, pandas | ✗ sin outputs |
| 12 | [12\_Lección\_Plantas\_Turbinas\_Vapor](../notebooks_originales/12_Leccion_Plantas_Turbinas_Vapor.ipynb) | 18 | **0** | 2 327 | 0 | 0 | 0 | **31** | 0 | 0 | — | ✗ sin outputs |
| 13 | [13\_Lección\_Mejoras\_Ciclos\_Vapor](../notebooks_originales/13_Lección_Mejoras_Ciclos_de_Vapor.ipynb) | 21 | 1 | 2 055 | 7 | 36 | 43 | 5 | 1 | 0 | CoolProp, matplotlib, numpy | ✗ sin outputs |
| 14 | [14\_Lección\_Modelación\_Intercambiador](../notebooks_originales/14_Lección_Modelación_Intercambiador.ipynb) | 31 | 3 | 4 312 | 20 | 121 | **141** | 10 | 2 | 0 | CoolProp, IPython, math, matplotlib, numpy, pandas | ✗ sin outputs |
| 15 | [15\_Lección\_Ciclos\_Refrigeración](../notebooks_originales/15_Lección_Ciclos_de_Refrigeración.ipynb) | 45 | **0** | 4 390 | 3 | 9 | 12 | **30** | 0 | 0 | — | ✗ sin outputs |
| | **TOTALES** | **420** | **78** | **45 577** | **136** | **837** | **973** | **213** | **40** | **1** | | 6/15 ✓ |

### 1.2 Estado del entorno de ejecución

El directorio `env/` está **vacío** — no existe `environment.yml` ni `requirements.txt`.
El Python disponible (miniconda 3.11.4) carece de los siguientes paquetes necesarios:

| Paquete | Notebooks que lo requieren | Estado |
|---------|---------------------------|--------|
| `matplotlib` | 01 02 03 04 05 06 07 08 09 13 14 | ✗ ausente |
| `CoolProp` | 02 08 13 14 | ✗ ausente |
| `ipywidgets` | 02 | ✗ ausente |
| `pandas` | 03 11 14 | ✗ ausente |
| `graphviz` (Python) | 03 04 06 | ✗ ausente |
| `networkx` | 03 | ✗ ausente |
| `scipy` | 05 | ✗ ausente |
| `sklearn` | 05 | ✗ ausente |
| `numpy` | 01 03 04 05 07 08 09 13 14 | ✓ presente |
| `sympy` | — | ✓ presente |

**Conclusión:** Ningún notebook ejecuta sin errores en el entorno actual. Los 6 marcados con ✓ tienen outputs guardados de una ejecución previa en otro entorno. **Acción necesaria:** poblar `env/` con `environment.yml` o `requirements.txt` antes de la fase de transformación.

---

## 2. Hallazgos destacados

| Hallazgo | Detalle |
|----------|---------|
| **Único notebook con widgets reales** | NB02 (1 celda con `import ipywidgets`) |
| **Notebooks sin ninguna celda de código** | NB10, NB12, NB15 — son exclusivamente markdown + imágenes estáticas |
| **Mayor densidad de ecuaciones** | NB14 (141), NB11 (133), NB08 (129), NB01 (121) |
| **Mayor cantidad de imágenes estáticas** | NB06 (35), NB12 (31), NB15 (30) — candidatos prioritarios a reemplazo por código |
| **Mayor número de celdas de código** | NB02 (14), NB03 (13), NB04 (13) — bases de código reutilizables |
| **NB03 sin ecuaciones LaTeX** | Único notebook sin ecuaciones; sus figuras son grafos de red (biogeoquímica/carbono) — verificar relevancia en el sílabo |
| **NB12 sin ecuaciones ni código** | Solo prosa y 31 imágenes estáticas embebidas; requiere reconstrucción completa |
| **Prosa más extensa** | NB11 (5 700 palabras), NB08 (5 607), NB06 (4 603) tras limpiar base64 |
| **Figuras generadas por código más activas** | NB01 (7), NB03 (10), NB05 (7), NB08 (7) |

---

## 3. Ranking de prioridad — Esfuerzo / Impacto para transformación interactiva

**Criterios:**
- **Impacto (1–5):** Importancia del tema en el sílabo de TM + ganancia pedagógica de hacer el contenido interactivo con widgets/CoolProp.
- **Esfuerzo (1–5):** Trabajo de transformación (1 = mínimo; 5 = reconstrucción desde cero). Considera: código existente, imágenes estáticas a reemplazar, prosa a condensar, modelos a implementar.
- **Ratio I/E:** Mayor = mejor retorno de inversión. Empates resueltos por peso temático en el sílabo.

| Rank | NB | Nombre | Impacto | Esfuerzo | Ratio | Palanca principal | Tier |
|------|----|--------|---------|----------|-------|-------------------|------|
| 1 | 02 | Ciclos Termodinámicos | 5 | 1 | **5.0** | Ya tiene widgets + CoolProp + 14 celdas código; solo extender y mejorar | ⭐ Quick win |
| 2 | 01 | Procesos Politrópicos | 5 | 2 | **2.5** | 7 celdas generan figuras; envolver con sliders; 121 ecuaciones ya formateadas | ⭐ Quick win |
| 3 | 13 | Mejoras Ciclos Vapor (Rankine) | 5 | 2 | **2.5** | CoolProp ya importado; 1 celda de código base; tema explícito en PROMPTS.md | ⭐ Quick win |
| 4 | 09 | Ensayo de Motores | 4 | 2 | **2.0** | Notebook pequeño (987 palabras); 3 celdas código; añadir viz interactiva de curvas de motor | ⭐ Quick win |
| 5 | 05 | Modelación Combustión | 4 | 3 | **1.3** | 17 celdas código con scipy/sklearn; añadir CoolProp + widgets de parámetros de llama | Alto impacto |
| 6 | 14 | Modelación Intercambiador | 4 | 3 | **1.3** | CoolProp listo + 3 celdas código; 141 ecuaciones formateadas; NTU/LMTD interactivo | Alto impacto |
| 7 | 15 | Ciclos de Refrigeración | 5 | 4 | **1.25** | Tema ideal para diagrama P-h interactivo con comparador de refrigerantes (PROMPTS.md); 0 código | Alto impacto |
| 8 | 08 | Motores Reciprocantes | 5 | 4 | **1.25** | CoolProp presente + 10 celdas código; reemplazar 26 imgs estáticas; condensar 5 607 palabras | Alto impacto |
| 9 | 11 | Modelamiento Turbina Gas | 5 | 4 | **1.25** | 133 ecuaciones, 1 celda código; implementar modelo Brayton en Python+CoolProp desde cero | Alto impacto |
| 10 | 07 | Máquinas — Compresores/Turbinas | 5 | 4 | **1.25** | 124 ecuaciones; casi sin código; crear widgets compresión/expansión politrópica | Alto impacto |
| 11 | 04 | Repaso Química | 3 | 3 | **1.0** | 13 celdas código; 17 imgs estáticas que reemplazar; material de soporte | Soporte |
| 12 | 12 | Plantas Turbinas Vapor | 5 | 5 | **1.0** | 0 código + 31 imgs; reconstrucción completa; Rankine básico ya cubierto en NB13 | Esfuerzo alto |
| 13 | 03 | Ciclos Biogeoquímicos | 2 | 2 | **1.0** | 13 celdas + grafos ya generados; verificar relevancia en sílabo antes de invertir | Periférico |
| 14 | 10 | Plantas Turbinas Gas | 4 | 5 | **0.8** | 0 código + 22 imgs; Brayton básico cubierto mejor en NB11; reconstrucción completa | Esfuerzo alto |
| 15 | 06 | Tecnología Combustión | 2 | 4 | **0.5** | 35 imgs estáticas; 53 celdas markdown; contenido descriptivo/industrial, bajo calculo interactivo | Descriptivo |

### Recomendación de secuencia

```
Fase 1 (Ranks 1–4): NB02 → NB01 → NB13 → NB09
  Retorno inmediato: todos tienen código base, transformaciones en <1 sesión.

Fase 2 (Ranks 5–6): NB05 → NB14
  Modelos de combustión e intercambiadores: mayor riqueza matemática.

Fase 3 (Ranks 7–10): NB15 → NB08 → NB11 → NB07
  Alta importancia curricular; requieren creación de modelos o reemplazo masivo de imágenes.

Fase 4 (Ranks 11–15): NB04 → NB12 → NB03 → NB10 → NB06
  Material de soporte, reconstrucciones completas o contenido descriptivo.
```

---

## 4. Notas para la transformación

1. **Entorno primero:** Crear `env/environment.yml` con al menos `numpy matplotlib scipy CoolProp ipywidgets pandas graphviz networkx scikit-learn` antes de iniciar Fase 1.
2. **NB02 como plantilla:** Es el único notebook con widgets funcionales. Su patrón `@interact` / `ipywidgets` puede servir de plantilla para todos los demás.
3. **CoolProp disponible en:** NB02, NB08, NB13, NB14 — base para extender a NB01, NB07, NB11, NB15.
4. **Imgs estáticas como base64:** Casi todas las imágenes están embebidas directamente en el JSON del notebook, no como archivos externos. Su reemplazo por código generado es independiente de un servidor de archivos.
5. **NB03 requiere decisión curricular:** El único notebook sin ecuaciones y con herramientas de grafos de red (graphviz, networkx). Parece tratar ciclos de carbono/nitrógeno como contexto ambiental del curso; verificar si debe mantenerse en el pipeline de transformación interactiva.
6. **NB06, NB07, NB08, NB09:** Contienen imágenes generadas con IA (filenames tipo `ChatGPT Image Aug 14, 2025...`). Verificar derechos y reemplazarlas con figuras propias generadas por código o TikZ.
