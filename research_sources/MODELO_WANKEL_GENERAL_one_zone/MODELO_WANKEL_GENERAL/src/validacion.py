# -*- coding: utf-8 -*-
"""
src/validacion.py
=================

Prevalidación automática y genérica del caso motor + combustible.

No se ejecuta manualmente. run.py la llama antes de simular.
"""

import cantera as ct

from configuracion.motores import (
    obtener_motor,
    validar_motor_config,
)
from configuracion.combustibles import obtener_combustible
from src.mecanismos import cargar_solucion


def validar_caso(motor_key, fuel_key):
    motor_cfg = obtener_motor(motor_key)
    fuel_cfg = obtener_combustible(fuel_key)

    validar_motor_config(motor_cfg)

    gas = cargar_solucion(fuel_cfg)

    faltantes = [
        sp
        for sp in fuel_cfg["especies_requeridas"]
        if sp not in gas.species_names
    ]

    if faltantes:
        raise ValueError(
            "\nEl mecanismo configurado NO corresponde al combustible.\n"
            f"Combustible : {fuel_cfg['nombre']}\n"
            f"Mecanismo   : {fuel_cfg['mecanismo']}\n"
            f"Faltan      : {', '.join(faltantes)}\n\n"
            "Corrige únicamente configuracion/combustibles.py o el YAML. "
            "No modifiques los solvers."
        )

    oper = motor_cfg["OPERACION"]

    gas.TP = (
        float(oper["T_INTAKE_K"]),
        float(oper["P_INTAKE_PA"]),
    )

    phi = float(fuel_cfg["phi"])
    fuel = fuel_cfg["fuel"]
    oxidizer = fuel_cfg["oxidizer"]

    gas.set_equivalence_ratio(
        phi,
        fuel=fuel,
        oxidizer=oxidizer,
    )

    afr_st = float(
        gas.stoich_air_fuel_ratio(
            fuel=fuel,
            oxidizer=oxidizer,
            basis="mole",
        )
    )

    afr = afr_st / phi

    gas_eq = cargar_solucion(fuel_cfg)
    gas_eq.TP = (
        float(oper["T_INTAKE_K"]),
        float(oper["P_INTAKE_PA"]),
    )
    gas_eq.set_equivalence_ratio(
        phi,
        fuel=fuel,
        oxidizer=oxidizer,
    )
    gas_eq.equilibrate("HP")

    return {
        "motor": motor_cfg["MOTOR"],
        "fuel": fuel_cfg,
        "mechanism_name": fuel_cfg["mecanismo"],
        "mechanism_origin": fuel_cfg.get("origen_mecanismo", "local"),
        "n_species": int(gas.n_species),
        "n_reactions": int(gas.n_reactions),
        "AFR": afr,
        "AFR_st": afr_st,
        "T_equilibrium_HP_K": float(gas_eq.T),
    }
