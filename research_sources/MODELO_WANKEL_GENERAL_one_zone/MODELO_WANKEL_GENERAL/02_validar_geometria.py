# -*- coding: utf-8 -*-
"""
02_validar_geometria.py
=======================

Valida el primer módulo físico del
modelo termoquímico Wankel general.
"""

import numpy as np

from configuracion.motor import (
    validar_configuracion_motor,
)

from src.geometria import (
    generar_geometria,
    firma_geometrica,
    DIR_GEOMETRIA,
)


print()

print("=" * 70)

print(
    "VALIDACIÓN DEL MÓDULO GEOMÉTRICO — WANKEL GENERAL"
)

print("=" * 70)


# ============================================================
# 1. CONFIGURACIÓN
# ============================================================

validar_configuracion_motor()

print(
    "[OK] Configuración del motor válida."
)


# ============================================================
# 2. GENERAR O CARGAR GEOMETRÍA
# ============================================================

datos, recalculada = generar_geometria(

    forzar=False,

    generar_graficas=True,

    mostrar_graficas=True,
)


# ============================================================
# 3. RESULTADOS PRINCIPALES
# ============================================================

Vd_cm3 = (
    datos["Vd_m3"]
    * 1.0e6
)

Vmin_cm3 = (
    datos["Vmin_m3"]
    * 1.0e6
)

Vmax_cm3 = (
    datos["Vmax_m3"]
    * 1.0e6
)

desplazamiento_cm3 = (

    datos[
        "desplazamiento_2_rotores_m3"
    ]

    * 1.0e6
)

CR_calc = (

    datos["Vmax_m3"]

    / datos["Vmin_m3"]
)


# ============================================================
# 4. REFERENCIAS DEL 13B YA VALIDADO
# ============================================================

REF_VD_CM3 = 654.715

REF_VMIN_CM3 = 77.942

REF_VMAX_CM3 = 732.657

REF_DISP_CM3 = 1309.430

REF_CR = 9.4


TOL_CM3 = 0.01

TOL_CR = 1.0e-6


# ============================================================
# 5. COMPROBACIONES
# ============================================================

checks = {

    "Vd por cara":

        abs(
            Vd_cm3
            - REF_VD_CM3
        )
        <= TOL_CM3,


    "Vmin":

        abs(
            Vmin_cm3
            - REF_VMIN_CM3
        )
        <= TOL_CM3,


    "Vmax":

        abs(
            Vmax_cm3
            - REF_VMAX_CM3
        )
        <= TOL_CM3,


    "Desplazamiento 2 rotores":

        abs(
            desplazamiento_cm3
            - REF_DISP_CM3
        )
        <= TOL_CM3,


    "Relación de compresión":

        abs(
            CR_calc
            - REF_CR
        )
        <= TOL_CR,


    "Contención del rotor":

        datos[
            "n_fuera_max"
        ] == 0,
}


print()

print("-" * 70)

print(
    "COMPROBACIONES AUTOMÁTICAS"
)

print("-" * 70)


for nombre, ok in checks.items():

    print(

        f"{'[OK]' if ok else '[ERROR]'} "
        f"{nombre}"
    )


# ============================================================
# 6. CIERRE DEL VOLUMEN
# ============================================================

integral_dV = np.trapezoid(

    datos[
        "dV_dtheta_eje_m3_rad"
    ],

    datos[
        "theta_eje_rad"
    ],
)


print()

print(

    "Integral geométrica de dV/dθ "
    "en 1080° = "

    f"{integral_dV:+.6e} m³"
)


if abs(integral_dV) <= 1.0e-10:

    print(
        "[OK] El volumen cierra correctamente "
        "después de 1080°."
    )

else:

    raise RuntimeError(
        "El volumen no cierra numéricamente "
        "después de un ciclo."
    )


# ============================================================
# 7. RESULTADO FINAL
# ============================================================

if not all(
    checks.values()
):

    raise RuntimeError(
        "Una o más validaciones "
        "geométricas fallaron."
    )


print()

print("=" * 70)

print(
    "[OK] MÓDULO GEOMÉTRICO VALIDADO"
)

print("=" * 70)


print(

    "Geometría recalculada = "

    + (

        "SI"

        if recalculada

        else "NO, se reutilizó la existente"
    )
)


print(
    f"Firma geométrica = "
    f"{firma_geometrica()}"
)


print(
    f"Archivos = "
    f"{DIR_GEOMETRIA}"
)


print()