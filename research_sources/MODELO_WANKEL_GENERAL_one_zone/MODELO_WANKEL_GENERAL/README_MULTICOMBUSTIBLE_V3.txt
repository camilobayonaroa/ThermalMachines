ACTUALIZACIÓN MULTICOMBUSTIBLE V3
=================================

Objetivo
--------
Añadir soporte nativo para mecanismos locales y mecanismos incluidos con Cantera,
y permitir combustibles multicomponente como GNV sin crear validadores ni run.py
específicos.

Combustibles configurados
-------------------------
isooctano   -> local/gasoline_surrogate.yaml
etanol      -> local/Z74_C2H5OH_20230420.yaml
hidrogeno   -> cantera/h2o2.yaml
metano      -> cantera/gri30.yaml
gas_natural -> cantera/gri30.yaml

GNV surrogate recuperado del trabajo previo
--------------------------------------------
Fracciones molares de la corriente:
CH4   0.940
C2H6  0.035
C3H8  0.010
CO2   0.010
N2    0.005

Uso
---
.\.venv\Scripts\python.exe run.py --motor 13b --fuel hidrogeno --no-show
.\.venv\Scripts\python.exe run.py --motor 13b --fuel metano --no-show
.\.venv\Scripts\python.exe run.py --motor 13b --fuel gas_natural --no-show

No copiar h2o2.yaml ni gri30.yaml a /mecanismos: Cantera los resuelve desde sus
directorios de datos.

Cambios de arquitectura
-----------------------
- src/mecanismos.py resuelve local/cantera.
- AFR usa stoich_air_fuel_ratio de Cantera.
- especies_combustible admite una lista.
- Conversión de GNV suma CH4+C2H6+C3H8.
- CO2/H2O teóricos se obtienen por balance elemental.
- LHV se calcula para corrientes puras o multicomponente.

Los resultados siguen guardándose por motor y combustible:
resultados/13b/hidrogeno/
resultados/13b/metano/
resultados/13b/gas_natural/
