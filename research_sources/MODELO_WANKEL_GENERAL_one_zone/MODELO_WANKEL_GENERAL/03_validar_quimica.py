# -*- coding: utf-8 -*-
"""
03_validar_quimica.py
=====================

Primera validación completa del solver químico GENERAL.
Actualmente se ejecuta con iso-octano para reproducir el caso base.
"""

from pathlib import Path
import numpy as np

from configuracion.combustibles import obtener_combustible
from src.quimica import ejecutar_quimica


FUEL_KEY = "isooctano"

print()
print("=" * 70)
print("VALIDACIÓN DEL SOLVER QUÍMICO GENERAL")
print("=" * 70)

fuel = obtener_combustible(FUEL_KEY)

print(f"Combustible solicitado = {fuel['nombre']}")
print(f"Especie principal = {fuel['especie_combustible']}")
print(f"Mecanismo = {fuel['mecanismo']}")

resultado = ejecutar_quimica(
    FUEL_KEY,
    generar_graficas=True,
    mostrar_graficas=True,
)

state_file = Path(resultado["state_file"])

if not state_file.exists():
    raise FileNotFoundError(
        f"El solver terminó, pero no creó el estado esperado:\n{state_file}"
    )

data = np.load(state_file, allow_pickle=False)

required_keys = [
    "theta_deg",
    "P_Pa",
    "T_K",
    "V_m3",
    "mass_kg",
    "Y_matrix",
    "species_names",
    "qdot_chem_W",
    "qwall_out_W",
    "work_rate_W",
    "fuel_conversion_absolute",
    "CA10_deg",
    "CA50_deg",
    "CA90_deg",
    "MULTICYCLE_CONVERGED",
]

print()
print("-" * 70)
print("COMPROBACIÓN DEL ESTADO COMPARTIDO")
print("-" * 70)

for key in required_keys:
    if key not in data.files:
        raise KeyError(f"Falta la variable '{key}' en estado_acoplado.npz")
    print(f"[OK] {key}")

P = data["P_Pa"]
T = data["T_K"]
V = data["V_m3"]
mass = data["mass_kg"]

if not np.all(np.isfinite(P)):
    raise RuntimeError("La presión contiene NaN/Inf.")
if not np.all(np.isfinite(T)):
    raise RuntimeError("La temperatura contiene NaN/Inf.")
if not np.all(np.isfinite(V)):
    raise RuntimeError("El volumen contiene NaN/Inf.")
if not np.all(np.isfinite(mass)):
    raise RuntimeError("La masa contiene NaN/Inf.")

if np.min(P) <= 0.0:
    raise RuntimeError("Se obtuvo presión no física <= 0 Pa.")
if np.min(T) <= 0.0:
    raise RuntimeError("Se obtuvo temperatura no física <= 0 K.")
if np.min(V) <= 0.0:
    raise RuntimeError("Se obtuvo volumen no físico <= 0 m³.")
if np.min(mass) <= 0.0:
    raise RuntimeError("Se obtuvo masa no física <= 0 kg.")

print()
print("[OK] P, T, V y masa son finitos y positivos.")

converged = bool(int(data["MULTICYCLE_CONVERGED"][0]))

if converged:
    print("[OK] Régimen periódico alcanzado.")
else:
    print(
        "[ADVERTENCIA] El solver terminó, pero no alcanzó régimen periódico. "
        "No invalida el código, pero los resultados aún no deben tomarse como definitivos."
    )

print()
print("=" * 70)
print("[OK] SOLVER QUÍMICO GENERAL EJECUTADO Y VALIDADO ESTRUCTURALMENTE")
print("=" * 70)
print()
