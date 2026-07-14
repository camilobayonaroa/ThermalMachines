# Trazabilidad de módulos de frontera (investigación → aula)

Mapea cada fuente de investigación estudiantil al módulo AVA derivado, su anclaje en el curso y su validación numérica.

| Módulo AVA | Fuente (research_sources) | Autores estudiantiles | Ancla en el curso | Resultados reproducidos y validación |
|---|---|---|---|---|
| `notebooks/05b_Bonus_Reacciones_Nucleares.ipynb` | `EntregasCurso/Entrega_Final_Proyecto_Planta_del_señor_Vernns_.ipynb` | A. G. Belalcázar, S. F. Triana, S. Lemus, J. C. Pineda (nov 2025) | Bonus tras **Lección 5 (Repaso de Química)**; extiende el widget de energía de enlace por nucleón | Energía específica fisión 82.1 TJ/kg (fuente ~82, **0.1 %**); consumo U-235 3.16 kg/día @3000 MWt (literatura ~1.05 g/MWd, **0.2 %**); β=650 pcm (Keepin, **0.0 %**); fusión D-T 338 TJ/kg, ⟨σv⟩(15 keV)=6.55e-23 m³/s. Ejecuta sin errores. |
| `notebooks/08b_Bonus_Combustión_Biomasa.ipynb` | `Biofuels Combustion/Taylor&Francis_R1.tex` (artículo en revisión) | D. A. Arias-Guerrero, M. Castillo-Hernández, J. D. Mayorga-Guzmán, C. A. Bayona-Roa | Bonus tras **Lección 8 (Cinética de la Combustión)**; generaliza sus EDOs acopladas a 16 especies (EFB/PMF) con estequiometría corregida | AFR estequiométrico 7.92 vs 7.94 (EFB, **0.26 %**) y 8.61 vs 8.63 (PMF, **0.27 %**); energía calibrada 147.11/158.27 MJ = LHV·m (**0.0002 %**); fórmula EFB C496H834O350N6S vs C488H821O344N6S del artículo; penalización por humedad −13.7 %/−1.1 % (artículo ≈−15.3 %/−1.9 %); conservación atómica 1.7e-13 %. Ejecuta sin errores. |

## Convenciones
- **Ancla en el curso**: semana/lección del sílabo donde el estudiante encuentra el módulo.
- **Validación**: % de desviación de los resultados reproducidos frente a la fuente o a literatura independiente (tolerancia objetivo < 5 %).
- Los notebooks fuente en `research_sources/` son de **solo lectura**; nunca se modifican.
- Cita BibTeX de cada fuente en `docs/modules_registry.bib`.
