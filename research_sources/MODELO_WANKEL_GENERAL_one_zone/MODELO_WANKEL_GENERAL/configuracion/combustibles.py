# -*- coding: utf-8 -*-
"""
configuracion/combustibles.py
=============================

Registro general de combustibles.

REGLA DE ARQUITECTURA
---------------------
El combustible define:
- su corriente de combustible (fuel);
- su mecanismo cinético;
- si el mecanismo es local o viene incluido con Cantera;
- las especies padre que representan combustible no quemado;
- las especies que interesa graficar.

Para añadir un combustible nuevo:
1) Si el mecanismo es externo, copiar el YAML a /mecanismos.
   Si Cantera ya lo incluye, no copiar nada.
2) Añadir UNA entrada aquí.
3) Ejecutar:
       python run.py --motor 13b --fuel <clave>

No se crean validadores ni ejecutores por combustible.
"""

from copy import deepcopy


COMBUSTIBLES = {

    "isooctano": {
        "nombre": "Iso-octano",
        "nombre_quimico": "2,2,4-trimetilpentano",

        "mecanismo": "gasoline_surrogate.yaml",
        "origen_mecanismo": "local",

        "fuel": "IC8H18:1",
        "oxidizer": "O2:1, N2:3.76",
        "phi": 1.0,

        # Mantener química finite-rate activa durante compresión.
        # Este es el comportamiento de la versión de iso-octano ya validada.
        "chemistry_before_spark": True,
        "ignition_target_K": 1150.0,

        "especies_combustible": ["IC8H18"],
        "especie_combustible": "IC8H18",  # compatibilidad / etiqueta

        "especies_requeridas": [
            "IC8H18", "O2", "N2", "CO2", "H2O", "CO",
        ],

        "especies_principales": [
            "IC8H18", "O2", "CO2", "H2O", "CO", "H2", "N2",
        ],

        "radicales": [
            "AC8H17", "BC8H17", "CC8H17", "DC8H17", "IC8H16",
            "CH3", "CH2O", "HCO", "H", "O", "OH", "HO2", "H2O2",
        ],

        "contaminantes": ["CO", "NO", "NO2", "N2O"],
    },

    "etanol": {
        "nombre": "Etanol",
        "nombre_quimico": "Etanol / alcohol etílico",

        "mecanismo": "Z74_C2H5OH_20230420.yaml",
        "origen_mecanismo": "local",

        "fuel": "C2H5OH:1",
        "oxidizer": "O2:1, N2:3.76",
        "phi": 1.0,

        "chemistry_before_spark": True,
        "ignition_target_K": 1150.0,

        "especies_combustible": ["C2H5OH"],
        "especie_combustible": "C2H5OH",

        "especies_requeridas": [
            "C2H5OH", "O2", "N2", "CO2", "H2O", "CO",
        ],

        "especies_principales": [
            "C2H5OH", "O2", "CO2", "H2O", "CO",
            "H2", "C2H4", "CH2O", "N2",
        ],

        "radicales": [
            "C2H5", "C2H4", "C2H3", "C2H2", "C2H",
            "CH3", "CH3O", "CH2", "CH2O", "CH2OH",
            "CH", "HCO", "H", "O", "OH", "HO2", "H2O2",
        ],

        "contaminantes": ["CO"],
    },

    "hidrogeno": {
        "nombre": "Hidrógeno",
        "nombre_quimico": "Hidrógeno molecular",

        # Incluido con Cantera: NO se copia a /mecanismos.
        "mecanismo": "h2o2.yaml",
        "origen_mecanismo": "cantera",

        "fuel": "H2:1",
        "oxidizer": "O2:1, N2:3.76",
        "phi": 1.0,

        # H2 es mucho más reactivo en el reactor 0-D con residuales.
        # Se conserva congelado hasta el evento de chispa.
        "chemistry_before_spark": False,
        "ignition_target_K": 1150.0,

        "especies_combustible": ["H2"],
        "especie_combustible": "H2",

        "especies_requeridas": [
            "H2", "O2", "N2", "H2O",
        ],

        "especies_principales": [
            "H2", "O2", "H2O", "N2",
        ],

        "radicales": [
            "H", "O", "OH", "HO2", "H2O2",
        ],

        # h2o2.yaml no contiene química de NOx.
        "contaminantes": [],
    },

    "metano": {
        "nombre": "Metano",
        "nombre_quimico": "Metano",

        # GRI-Mech 3.0 viene incluido con Cantera.
        "mecanismo": "gri30.yaml",
        "origen_mecanismo": "cantera",

        "fuel": "CH4:1",
        "oxidizer": "O2:1, N2:3.76",
        "phi": 1.0,

        # Mantener química activa: evita la discontinuidad numérica de V6.
        "chemistry_before_spark": True,
        "ignition_target_K": 1500.0,

        "especies_combustible": ["CH4"],
        "especie_combustible": "CH4",

        "especies_requeridas": [
            "CH4", "O2", "N2", "CO2", "H2O", "CO",
        ],

        "especies_principales": [
            "CH4", "O2", "CO2", "H2O", "CO", "H2", "N2",
        ],

        "radicales": [
            "CH3", "CH2", "CH2(S)", "CH2O", "CH2OH", "CH3O",
            "HCO", "H", "O", "OH", "HO2", "H2O2",
        ],

        "contaminantes": ["CO", "NO", "NO2", "N2O"],
    },

    "gas_natural": {
        "nombre": "Gas natural (GNV surrogate)",
        "nombre_quimico": "Surrogate multicomponente de gas natural",

        # El mismo mecanismo sirve porque GRI-Mech contiene CH4, C2H6 y C3H8.
        "mecanismo": "gri30.yaml",
        "origen_mecanismo": "cantera",

        # Surrogate que ya se había utilizado en el proyecto.
        # Fracciones molares de la corriente de GNV:
        # CH4 94.0 %, C2H6 3.5 %, C3H8 1.0 %, CO2 1.0 %, N2 0.5 %.
        "fuel": (
            "CH4:0.940, "
            "C2H6:0.035, "
            "C3H8:0.010, "
            "CO2:0.010, "
            "N2:0.005"
        ),
        "oxidizer": "O2:1, N2:3.76",
        "phi": 1.0,

        # Mantener química activa: evita la discontinuidad numérica de V6.
        "chemistry_before_spark": True,
        "ignition_target_K": 1500.0,

        # Solo estas especies representan combustible químicamente reactivo.
        # CO2 y N2 forman parte de la corriente de GNV, pero son diluyentes.
        "especies_combustible": ["CH4", "C2H6", "C3H8"],
        "especie_combustible": "CH4",  # solo etiqueta compatible

        "especies_requeridas": [
            "CH4", "C2H6", "C3H8",
            "O2", "N2", "CO2", "H2O", "CO",
        ],

        "especies_principales": [
            "CH4", "C2H6", "C3H8",
            "O2", "CO2", "H2O", "CO", "H2", "N2",
        ],

        "radicales": [
            "C3H7", "C2H5", "C2H4", "CH3", "CH2", "CH2(S)",
            "CH2O", "HCO", "H", "O", "OH", "HO2", "H2O2",
        ],

        "contaminantes": ["CO", "NO", "NO2", "N2O"],

        "nota": (
            "Surrogate genérico de trabajo. No presentar como composición "
            "oficial del GNV colombiano sin una fuente específica."
        ),
    },
}


def listar_combustibles():
    return sorted(COMBUSTIBLES.keys())


def obtener_combustible(nombre):
    key = str(nombre).strip().lower()

    if key not in COMBUSTIBLES:
        disponibles = ", ".join(listar_combustibles())
        raise KeyError(
            f"Combustible '{nombre}' no definido. Disponibles: {disponibles}"
        )

    cfg = deepcopy(COMBUSTIBLES[key])

    # Compatibilidad con cualquier entrada antigua de combustible puro.
    if "especies_combustible" not in cfg:
        cfg["especies_combustible"] = [cfg["especie_combustible"]]

    if "especie_combustible" not in cfg:
        cfg["especie_combustible"] = cfg["especies_combustible"][0]

    cfg.setdefault("origen_mecanismo", "local")

    return cfg
