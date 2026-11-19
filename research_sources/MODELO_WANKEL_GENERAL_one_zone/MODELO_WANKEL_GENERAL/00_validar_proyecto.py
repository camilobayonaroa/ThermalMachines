# -*- coding: utf-8 -*-
"""
00_validar_proyecto.py
======================

VALIDADOR GENERAL DEL PROYECTO TERMOQUÍMICO WANKEL

Objetivos:
1. Verificar el intérprete de Python utilizado.
2. Verificar las librerías principales.
3. Comprobar la estructura del proyecto.
4. Localizar y cargar gasoline_surrogate.yaml.
5. Verificar que el mecanismo contiene IC8H18.
6. Crear una mezcla estequiométrica IC8H18/aire.
7. Dejar preparado el proyecto para construir el modelo general.

Este archivo NO realiza todavía:
- geometría;
- combustión;
- integración;
- termodinámica;
- torque;
- potencia.

Solamente valida que el entorno base funciona correctamente.
"""

from pathlib import Path
import sys

import cantera as ct
import numpy as np
import matplotlib
import PIL


# ============================================================
# 1. RUTAS GENERALES DEL PROYECTO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DIR_MECANISMOS = BASE_DIR / "mecanismos"
DIR_CONFIGURACION = BASE_DIR / "configuracion"
DIR_SRC = BASE_DIR / "src"
DIR_DATOS = BASE_DIR / "datos_comunes"
DIR_GEOMETRIA = DIR_DATOS / "geometria_13B"
DIR_RESULTADOS = BASE_DIR / "resultados"

MECANISMO_GASOLINA = (
    DIR_MECANISMOS / "gasoline_surrogate.yaml"
)


# ============================================================
# 2. ENCABEZADO
# ============================================================

print()
print("=" * 70)
print("VALIDACIÓN GENERAL — MODELO TERMOQUÍMICO WANKEL")
print("=" * 70)

print()
print("Carpeta raíz:")
print(BASE_DIR)

print()
print("Intérprete Python:")
print(sys.executable)

print()
print("Versión Python:")
print(sys.version.split()[0])


# ============================================================
# 3. VERSIONES DE LIBRERÍAS
# ============================================================

print()
print("-" * 70)
print("LIBRERÍAS")
print("-" * 70)

print(f"Cantera    : {ct.__version__}")
print(f"NumPy      : {np.__version__}")
print(f"Matplotlib : {matplotlib.__version__}")
print(f"Pillow     : {PIL.__version__}")


# ============================================================
# 4. COMPROBAR ENTORNO VIRTUAL
# ============================================================

python_path_lower = str(sys.executable).lower()

if ".venv" in python_path_lower:
    print()
    print("[OK] Se está utilizando el entorno virtual del proyecto.")
else:
    print()
    print(
        "[ADVERTENCIA] Python no parece provenir de '.venv'."
    )
    print(
        "Se recomienda ejecutar con:"
    )
    print(
        r".\.venv\Scripts\python.exe 00_validar_proyecto.py"
    )


# ============================================================
# 5. COMPROBAR ESTRUCTURA DEL PROYECTO
# ============================================================

print()
print("-" * 70)
print("ESTRUCTURA DEL PROYECTO")
print("-" * 70)

directorios_requeridos = {
    "mecanismos": DIR_MECANISMOS,
    "configuracion": DIR_CONFIGURACION,
    "src": DIR_SRC,
    "datos_comunes": DIR_DATOS,
    "geometria_13B": DIR_GEOMETRIA,
    "resultados": DIR_RESULTADOS,
}

estructura_ok = True

for nombre, ruta in directorios_requeridos.items():

    if ruta.exists() and ruta.is_dir():
        print(f"[OK] {nombre:<20} -> {ruta}")
    else:
        estructura_ok = False
        print(f"[ERROR] Falta carpeta: {ruta}")


if not estructura_ok:
    raise FileNotFoundError(
        "\nLa estructura del proyecto está incompleta."
    )


# ============================================================
# 6. COMPROBAR MECANISMO
# ============================================================

print()
print("-" * 70)
print("MECANISMO QUÍMICO")
print("-" * 70)

if not MECANISMO_GASOLINA.exists():
    raise FileNotFoundError(
        "\nNo se encontró:\n"
        f"{MECANISMO_GASOLINA}\n\n"
        "Coloca gasoline_surrogate.yaml dentro de "
        "la carpeta 'mecanismos'."
    )

print(
    "[OK] Archivo encontrado:"
)
print(MECANISMO_GASOLINA)


# ============================================================
# 7. CARGAR MECANISMO CON CANTERA
# ============================================================

try:

    gas = ct.Solution(
        str(MECANISMO_GASOLINA),
        transport_model=None,
    )

except Exception as exc:

    raise RuntimeError(
        "\nCantera encontró el YAML, pero no pudo cargarlo.\n"
        "Revisa el formato del mecanismo."
    ) from exc


print()
print("[OK] Cantera cargó el mecanismo correctamente.")

print(
    f"Número de especies  : {gas.n_species}"
)

print(
    f"Número de reacciones: {gas.n_reactions}"
)


# ============================================================
# 8. ESPECIES MÍNIMAS PARA ISO-OCTANO
# ============================================================

especies_requeridas = [
    "IC8H18",
    "O2",
    "N2",
    "CO2",
    "H2O",
    "CO",
]

print()
print("-" * 70)
print("ESPECIES REQUERIDAS PARA ISO-OCTANO")
print("-" * 70)

species_ok = True

for especie in especies_requeridas:

    if especie in gas.species_names:
        print(f"[OK] {especie}")
    else:
        species_ok = False
        print(f"[ERROR] No existe {especie}")


if not species_ok:
    raise ValueError(
        "\nEl mecanismo no contiene todas las especies "
        "necesarias para la corrida de iso-octano."
    )


# ============================================================
# 9. MEZCLA ESTEQUIOMÉTRICA ISO-OCTANO / AIRE
# ============================================================

T_INTAKE = 330.0
P_INTAKE = 0.95 * ct.one_atm
PHI = 1.0

FUEL = "IC8H18:1"
OXIDIZER = "O2:1, N2:3.76"

gas.TP = T_INTAKE, P_INTAKE

gas.set_equivalence_ratio(
    PHI,
    fuel=FUEL,
    oxidizer=OXIDIZER,
)


# Índice seguro de la especie.
k_fuel = gas.species_index("IC8H18")

X_FUEL = float(gas.X[k_fuel])
Y_FUEL = float(gas.Y[k_fuel])

AFR = (
    (1.0 - Y_FUEL) / Y_FUEL
    if Y_FUEL > 0.0
    else np.nan
)


print()
print("-" * 70)
print("PRUEBA DE MEZCLA — ISO-OCTANO / AIRE")
print("-" * 70)

print(
    f"Temperatura admisión = {gas.T:.3f} K"
)

print(
    f"Presión admisión     = {gas.P/1000.0:.3f} kPa"
)

print(
    f"Equivalence ratio φ  = {PHI:.4f}"
)

print(
    f"X(IC8H18)            = {X_FUEL:.8e}"
)

print(
    f"Y(IC8H18)            = {Y_FUEL:.8e}"
)

print(
    f"AFR mezcla fresca    = {AFR:.6f} kg aire/kg combustible"
)


# ============================================================
# 10. PRUEBA TERMOQUÍMICA BÁSICA
# ============================================================

T_INITIAL = float(gas.T)
P_INITIAL = float(gas.P)

gas_eq = ct.Solution(
    str(MECANISMO_GASOLINA),
    transport_model=None,
)

gas_eq.TPX = (
    gas.T,
    gas.P,
    gas.X,
)

try:

    gas_eq.equilibrate("HP")

except Exception as exc:

    raise RuntimeError(
        "\nEl mecanismo carga y crea la mezcla, "
        "pero falló la prueba de equilibrio HP."
    ) from exc


print()
print("-" * 70)
print("PRUEBA TERMOQUÍMICA")
print("-" * 70)

print(
    f"Estado inicial : "
    f"T={T_INITIAL:.2f} K | "
    f"P={P_INITIAL/1000.0:.2f} kPa"
)

print(
    f"Equilibrio HP  : "
    f"T={gas_eq.T:.2f} K | "
    f"P={gas_eq.P/1000.0:.2f} kPa"
)

print(
    "[OK] El mecanismo puede representar productos "
    "termoquímicos de combustión."
)


# ============================================================
# 11. RESULTADO FINAL
# ============================================================

print()
print("=" * 70)
print("RESULTADO DE LA VALIDACIÓN")
print("=" * 70)

print()
print("[OK] Python funciona.")
print("[OK] Cantera funciona.")
print("[OK] NumPy funciona.")
print("[OK] Matplotlib funciona.")
print("[OK] Pillow funciona.")
print("[OK] Estructura del proyecto correcta.")
print("[OK] gasoline_surrogate.yaml encontrado.")
print("[OK] Mecanismo cargado por Cantera.")
print("[OK] IC8H18 presente.")
print("[OK] Mezcla IC8H18/aire creada.")
print("[OK] Prueba termoquímica completada.")

print()
print(
    "EL PROYECTO BASE ESTÁ LISTO PARA CONSTRUIR "
    "EL MODELO WANKEL GENERAL."
)

print("=" * 70)
print()