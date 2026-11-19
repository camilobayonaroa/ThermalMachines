# -*- coding: utf-8 -*-
"""
00_validar_mecanismo_etanol.py
==============================

Comprueba el mecanismo de etanol antes de ejecutar run.py.
"""

from pathlib import Path
import cantera as ct

from configuracion.combustibles import obtener_combustible


BASE_DIR = Path(__file__).resolve().parent

cfg = obtener_combustible("etanol")

path = (
    BASE_DIR
    / "mecanismos"
    / cfg["mecanismo"]
)


print()
print("=" * 72)
print("VALIDACIÓN DEL MECANISMO DE ETANOL")
print("=" * 72)

print(
    f"Archivo esperado = {path}"
)


if not path.exists():
    raise FileNotFoundError(
        "\nNo existe el mecanismo de etanol.\n\n"
        f"Coloca este archivo:\n"
        f"    {cfg['mecanismo']}\n\n"
        f"dentro de:\n"
        f"    {BASE_DIR / 'mecanismos'}\n"
    )


gas = ct.Solution(
    str(path),
    transport_model=None,
)


print(
    f"[OK] Mecanismo cargado con Cantera {ct.__version__}"
)

print(
    f"Especies = {gas.n_species}"
)

print(
    f"Reacciones = {gas.n_reactions}"
)


for sp in cfg["especies_requeridas"]:

    if sp not in gas.species_names:
        raise ValueError(
            f"Falta la especie requerida: {sp}"
        )

    print(
        f"[OK] {sp}"
    )


gas.TP = (
    330.0,
    0.95 * ct.one_atm,
)

gas.set_equivalence_ratio(
    cfg["phi"],
    fuel=cfg["fuel"],
    oxidizer=cfg["oxidizer"],
)


k_fuel = gas.species_index(
    cfg["especie_combustible"]
)

Yfuel = float(
    gas.Y[k_fuel]
)

AFR = (
    1.0 - Yfuel
) / Yfuel


print()
print(
    f"phi = {cfg['phi']:.4f}"
)

print(
    f"Y combustible = {Yfuel:.8f}"
)

print(
    f"AFR mezcla fresca = {AFR:.4f} kg aire/kg combustible"
)


# Comprobar que también podemos generar productos quemados
gas_eq = ct.Solution(
    str(path),
    transport_model=None,
)

gas_eq.TP = (
    330.0,
    0.95 * ct.one_atm,
)

gas_eq.set_equivalence_ratio(
    cfg["phi"],
    fuel=cfg["fuel"],
    oxidizer=cfg["oxidizer"],
)

gas_eq.equilibrate("HP")


print(
    f"T equilibrio HP = {gas_eq.T:.2f} K"
)

print()
print("=" * 72)
print("[OK] MECANISMO DE ETANOL LISTO PARA run.py")
print("=" * 72)
