MODELO_WANKEL_GENERAL — ARQUITECTURA UNIFICADA V2
=================================================

OBJETIVO
--------
Separar completamente:

    MOTOR / GEOMETRÍA
    COMBUSTIBLE / MECANISMO
    SOLVERS FÍSICOS

USO
---
13B + iso-octano:
    .\.venv\Scripts\python.exe run.py --motor 13b --fuel isooctano --no-show

13B + etanol:
    .\.venv\Scripts\python.exe run.py --motor 13b --fuel etanol --no-show

NO SE USAN VALIDADORES ESPECÍFICOS POR COMBUSTIBLE.

NUEVO COMBUSTIBLE
-----------------
1. Poner YAML en:
       mecanismos/

2. Añadir UNA entrada en:
       configuracion/combustibles.py

3. Ejecutar:
       run.py --motor 13b --fuel NUEVO

NUEVO MOTOR WANKEL 4T CLÁSICO
------------------------------
1. Añadir UNA entrada en:
       configuracion/motores.py

2. Ejecutar:
       run.py --motor NUEVO --fuel etanol

La geometría actual cubre la familia clásica de 3 ápices y relación 3:1.

RESULTADOS
----------
Ahora quedan separados por motor Y combustible:

    resultados/
        13b/
            isooctano/
            etanol/

La geometría se almacena una sola vez por motor:

    datos_comunes/
        geometrias/
            13b/

ARCHIVOS ANTIGUOS
-----------------
Los validadores 00_..., 01_..., 02_..., etc. pueden conservarse como
histórico, pero run.py ya no depende de ellos.

IMPORTANTE
----------
Conserva en /mecanismos:
    gasoline_surrogate.yaml
    Z74_C2H5OH_20230420.yaml

La selección de mecanismo se hace EXCLUSIVAMENTE desde combustibles.py.
