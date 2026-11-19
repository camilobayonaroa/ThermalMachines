# -*- coding: utf-8 -*-
r"""
run.py
======

ÚNICO ejecutor del MODELO_WANKEL_GENERAL.

Ejemplos
--------

Mazda 13B + iso-octano:
    .\.venv\Scripts\python.exe run.py --motor 13b --fuel isooctano --no-show

Mazda 13B + etanol:
    .\.venv\Scripts\python.exe run.py --motor 13b --fuel etanol --no-show

Listar motores:
    .\.venv\Scripts\python.exe run.py --list-motors

Listar combustibles:
    .\.venv\Scripts\python.exe run.py --list-fuels

REGLA
-----
No se crea un run por motor ni por combustible.
"""

import argparse
import os
import sys

from configuracion.motores import (
    listar_motores,
    obtener_motor,
)

from configuracion.combustibles import (
    listar_combustibles,
    obtener_combustible,
)

from src.validacion import validar_caso


def parser_cli():
    parser = argparse.ArgumentParser(
        description=(
            "Modelo termoquímico Wankel 4T general: "
            "selección independiente de motor y combustible."
        )
    )

    parser.add_argument(
        "--motor",
        type=str,
        default="13b",
        help="Clave del motor. Ejemplo: 13b",
    )

    parser.add_argument(
        "--fuel",
        type=str,
        default=None,
        help="Clave del combustible. Ejemplo: etanol",
    )

    parser.add_argument(
        "--no-show",
        action="store_true",
        help="Guarda las gráficas sin abrir ventanas.",
    )

    parser.add_argument(
        "--force-geometry",
        action="store_true",
        help="Fuerza el recálculo de la geometría del motor.",
    )

    parser.add_argument(
        "--list-motors",
        action="store_true",
        help="Lista los motores configurados.",
    )

    parser.add_argument(
        "--list-fuels",
        action="store_true",
        help="Lista los combustibles configurados.",
    )

    return parser


def mostrar_motores():
    print()
    print("=" * 78)
    print("MOTORES CONFIGURADOS")
    print("=" * 78)

    for key in listar_motores():
        cfg = obtener_motor(key)
        m = cfg["MOTOR"]
        g = cfg["GEOMETRIA"]

        print(
            f"- {key:12s} | "
            f"{m['nombre']} | "
            f"{m['numero_rotores']} rotor(es) | "
            f"CR={g['CR']:.3f}"
        )

    print()


def mostrar_combustibles():
    print()
    print("=" * 78)
    print("COMBUSTIBLES CONFIGURADOS")
    print("=" * 78)

    for key in listar_combustibles():
        cfg = obtener_combustible(key)

        print(
            f"- {key:12s} | "
            f"{cfg['nombre']} | "
            f"especie={cfg['especie_combustible']} | "
            f"mecanismo={cfg['mecanismo']} | "
            f"phi={cfg['phi']}"
        )

    print()


def main():
    parser = parser_cli()
    args = parser.parse_args()

    if args.list_motors:
        mostrar_motores()
        return 0

    if args.list_fuels:
        mostrar_combustibles()
        return 0

    if args.fuel is None:
        parser.error(
            "Debes indicar --fuel. "
            "Usa --list-fuels para ver opciones."
        )

    motor_key = args.motor.strip().lower()
    fuel_key = args.fuel.strip().lower()

    # --------------------------------------------------------
    # PREVALIDACIÓN GENÉRICA
    # --------------------------------------------------------
    #
    # Esto sustituye TODOS los validadores específicos de combustible.
    # --------------------------------------------------------

    print()
    print("=" * 78)
    print("PREVALIDACIÓN AUTOMÁTICA DEL CASO")
    print("=" * 78)

    info = validar_caso(
        motor_key,
        fuel_key,
    )

    print(
        f"[OK] Motor       = "
        f"{info['motor']['nombre']} ({motor_key})"
    )

    print(
        f"[OK] Combustible = "
        f"{info['fuel']['nombre']} "
        f"({info['fuel']['especie_combustible']})"
    )

    print(
        f"[OK] Mecanismo   = "
        f"{info['fuel']['mecanismo']}"
    )

    print(
        f"[OK] Especies    = "
        f"{info['n_species']}"
    )

    print(
        f"[OK] Reacciones  = "
        f"{info['n_reactions']}"
    )

    print(
        f"[OK] AFR fresco  = "
        f"{info['AFR']:.4f} kg aire/kg combustible"
    )

    print(
        f"[OK] Equilibrio HP = "
        f"{info['T_equilibrium_HP_K']:.2f} K"
    )

    # --------------------------------------------------------
    # SELECCIONAR MOTOR ANTES DE IMPORTAR LOS SOLVERS
    # --------------------------------------------------------

    os.environ[
        "WANKEL_MOTOR"
    ] = motor_key

    # IMPORTACIONES INTENCIONALMENTE TARDÍAS.
    # configuracion.motor leerá WANKEL_MOTOR en este punto.
    from src.geometria import generar_geometria
    from src.quimica import ejecutar_quimica
    from src.termodinamica import ejecutar_termodinamica
    from src.mecanica import ejecutar_mecanica

    mostrar = not args.no_show

    results_rel = (
        f"resultados/{motor_key}/{fuel_key}/"
    )

    print()
    print("=" * 78)
    print("MODELO TERMOQUÍMICO GENERAL — MOTOR WANKEL 4T")
    print("=" * 78)

    print(
        f"Motor       = {info['motor']['nombre']}"
    )

    print(
        f"Combustible = {info['fuel']['nombre']}"
    )

    print(
        f"Mecanismo   = {info['fuel']['mecanismo']}"
    )

    print(
        f"Resultados  = {results_rel}"
    )

    print("=" * 78)

    # ========================================================
    # 1. GEOMETRÍA
    # ========================================================

    print()
    print("#" * 78)
    print("1/4 — GEOMETRÍA DEL MOTOR")
    print("#" * 78)

    generar_geometria(
        forzar=args.force_geometry,
        generar_graficas=True,
        mostrar_graficas=mostrar,
    )

    # ========================================================
    # 2. QUÍMICA
    # ========================================================

    print()
    print("#" * 78)
    print("2/4 — QUÍMICA 0-D MULTICICLO")
    print("#" * 78)

    ejecutar_quimica(
        nombre_combustible=fuel_key,
        generar_graficas=True,
        mostrar_graficas=mostrar,
    )

    # ========================================================
    # 3. TERMODINÁMICA
    # ========================================================

    print()
    print("#" * 78)
    print("3/4 — TERMODINÁMICA")
    print("#" * 78)

    ejecutar_termodinamica(
        nombre_combustible=fuel_key,
        generar_graficas=True,
        mostrar_graficas=mostrar,
    )

    # ========================================================
    # 4. MECÁNICA
    # ========================================================

    print()
    print("#" * 78)
    print("4/4 — TORQUE Y POTENCIA INDICADA")
    print("#" * 78)

    ejecutar_mecanica(
        nombre_combustible=fuel_key,
        generar_graficas=True,
        mostrar_graficas=mostrar,
    )

    print()
    print("=" * 78)
    print("[OK] SIMULACIÓN COMPLETA FINALIZADA")
    print("=" * 78)

    print(
        f"Motor       = {info['motor']['nombre']}"
    )

    print(
        f"Combustible = {info['fuel']['nombre']}"
    )

    print(
        f"Resultados  = {results_rel}"
    )

    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
