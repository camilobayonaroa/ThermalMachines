# -*- coding: utf-8 -*-

"""
01_validar_configuracion.py
===========================

Prueba que las configuraciones del motor y combustible
pueden cargarse correctamente.
"""

from configuracion.motor import (
    MOTOR,
    GEOMETRIA,
    OPERACION,
    CICLO,
    ENCENDIDO,
    TRANSFERENCIA_CALOR,
    validar_configuracion_motor,
)

from configuracion.combustibles import (
    obtener_combustible,
    listar_combustibles,
)


print()
print("=" * 70)
print("VALIDACIÓN DE CONFIGURACIÓN — MODELO WANKEL GENERAL")
print("=" * 70)


# ============================================================
# MOTOR
# ============================================================

validar_configuracion_motor()

print()
print("[OK] Configuración del motor válida.")

print()
print("Motor:")
print(f"  {MOTOR['nombre']}")

print()
print("Geometría:")

print(
    f"  e  = {GEOMETRIA['e_m']*1000.0:.3f} mm"
)

print(
    f"  R  = {GEOMETRIA['R_m']*1000.0:.3f} mm"
)

print(
    f"  b  = {GEOMETRIA['b_m']*1000.0:.3f} mm"
)

print(
    f"  CR = {GEOMETRIA['CR']:.3f}:1"
)

print()
print(
    f"RPM eje = {OPERACION['RPM_EJE']:.1f}"
)

print(
    f"T pared = "
    f"{TRANSFERENCIA_CALOR['T_WALL_K']:.1f} K"
)

print(
    f"Chispa = "
    f"{ENCENDIDO['SPARK_ANGLE_DEG']:.1f}°"
)

print()
print("Ciclo angular:")

print(
    f"  Admisión: "
    f"{CICLO['INTAKE_OPEN_DEG']:.1f}° "
    f"-> {CICLO['INTAKE_CLOSE_DEG']:.1f}°"
)

print(
    f"  Compresión/combustión hasta "
    f"{CICLO['TDC_COMBUSTION_DEG']:.1f}°"
)

print(
    f"  Expansión hasta "
    f"{CICLO['EXPANSION_END_DEG']:.1f}°"
)

print(
    f"  Escape hasta "
    f"{CICLO['EXHAUST_CLOSE_DEG']:.1f}°"
)


# ============================================================
# COMBUSTIBLE
# ============================================================

print()
print("-" * 70)
print("COMBUSTIBLES DISPONIBLES")
print("-" * 70)

for nombre in listar_combustibles():

    print(
        f"  - {nombre}"
    )


fuel = obtener_combustible(
    "isooctano"
)


print()
print("-" * 70)
print("COMBUSTIBLE SELECCIONADO")
print("-" * 70)

print(
    f"Nombre       = {fuel['nombre']}"
)

print(
    f"Especie      = {fuel['especie_combustible']}"
)

print(
    f"Mecanismo    = {fuel['mecanismo']}"
)

print(
    f"Fuel Cantera = {fuel['fuel']}"
)

print(
    f"Oxidizer     = {fuel['oxidizer']}"
)

print(
    f"phi          = {fuel['phi']:.4f}"
)


print()
print("=" * 70)
print("[OK] CONFIGURACIONES CARGADAS CORRECTAMENTE")
print("=" * 70)
print()