# -*- coding: utf-8 -*-
"""
src/mecanismos.py
=================

Resolución única de mecanismos cinéticos.

Dos orígenes:
- local: archivo YAML guardado en MODELO_WANKEL_GENERAL/mecanismos/
- cantera: archivo distribuido con la instalación de Cantera

Los solvers no necesitan saber dónde vive el mecanismo.
"""

from pathlib import Path
import cantera as ct


BASE_DIR = Path(__file__).resolve().parents[1]
DIR_MECANISMOS = BASE_DIR / "mecanismos"


def resolver_mecanismo(fuel_cfg):
    nombre = str(fuel_cfg["mecanismo"])
    origen = str(
        fuel_cfg.get("origen_mecanismo", "local")
    ).strip().lower()

    if origen == "local":
        path = DIR_MECANISMOS / nombre

        if not path.exists():
            raise FileNotFoundError(
                "\nFalta el mecanismo local del combustible.\n"
                f"Mecanismo: {nombre}\n"
                f"Ruta esperada: {path}\n"
            )

        return str(path)

    if origen == "cantera":
        # Cantera busca automáticamente en sus data directories.
        return nombre

    raise ValueError(
        f"origen_mecanismo='{origen}' no reconocido. "
        "Usa 'local' o 'cantera'."
    )


def cargar_solucion(fuel_cfg):
    referencia = resolver_mecanismo(fuel_cfg)

    try:
        return ct.Solution(
            referencia,
            transport_model=None,
        )
    except Exception as exc:
        raise RuntimeError(
            "\nCantera no pudo cargar el mecanismo configurado.\n"
            f"Combustible: {fuel_cfg['nombre']}\n"
            f"Mecanismo: {fuel_cfg['mecanismo']}\n"
            f"Origen: {fuel_cfg.get('origen_mecanismo', 'local')}\n"
            f"Referencia usada: {referencia}\n"
            f"Error original: {exc}"
        ) from exc
