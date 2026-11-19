# -*- coding: utf-8 -*-
"""
configuracion/motores.py
========================

Registro de motores Wankel 4T.

Para añadir OTRO motor Wankel 4T clásico:
1. Copia una entrada.
2. Cambia geometría / número de rotores / operación / timing.
3. Ejecuta:
       python run.py --motor <clave> --fuel <combustible>

No hay que modificar quimica.py, termodinamica.py, mecanica.py ni run.py.

ALCANCE ACTUAL
--------------
La familia geométrica implementada es el Wankel clásico de rotor triangular
(3 ápices) con relación eje:rotor = 3:1.
"""

from copy import deepcopy

ATM_PA = 101325.0


MOTORES = {

    "13b": {

        "MOTOR": {
            "id": "13b",
            "nombre": "Mazda 13B NA",
            "arquitectura": "Wankel 4T",
            "familia_geometrica": "wankel_clasico_3_apex",
            "numero_rotores": 2,
            "caras_por_rotor": 3,
        },

        "GEOMETRIA": {
            "e_m": 15.0e-3,
            "R_m": 105.0e-3,
            "b_m": 80.0e-3,
            "CR": 9.4,

            "N_THETA": 3601,
            "N_HOUSING": 5400,
            "N_POS_ENV": 3240,
            "N_PHI_ROTOR": 3240,

            "ciclo_eje_deg": 1080.0,
            "relacion_eje_rotor": 3.0,
        },

        "OPERACION": {
            "RPM_EJE": 2750.0,

            "T_INTAKE_K": 330.0,
            "P_INTAKE_PA": 0.95 * ATM_PA,

            "T_RESIDUAL_K": 650.0,
            "P_RESIDUAL_PA": 0.20 * ATM_PA,

            "T_EXHAUST_K": 700.0,
            "P_EXHAUST_PA": ATM_PA,

            "P_REF_PA": ATM_PA,
        },

        "CICLO": {
            "INTAKE_OPEN_DEG": 0.0,
            "INTAKE_CLOSE_DEG": 270.0,

            "TDC_COMBUSTION_DEG": 540.0,

            "EXPANSION_END_DEG": 810.0,

            "EXHAUST_OPEN_DEG": 810.0,
            "EXHAUST_CLOSE_DEG": 1080.0,

            "CYCLE_END_DEG": 1080.0,

            # La geometría base comienza en Vmax.
            # El ciclo termoquímico comienza en Vmin.
            "GEOMETRY_PHASE_OFFSET_DEG": 810.0,
        },

        "ENCENDIDO": {
            "SPARK_ANGLE_DEG": 525.0,
            "SPARK_DURATION_DEG": 6.0,
            "T_IGNITION_TARGET_K": 1150.0,
        },

        "TRANSFERENCIA_CALOR": {
            "habilitada": True,
            "T_WALL_K": 450.0,
            "modelo_h": "wankel_tipo_woschni",
            "modelo_area": "area_mojada_equivalente",
        },

        "PUERTOS": {
            "INLET_VALVE_COEFF": 1.0e-6,
            "EXHAUST_VALVE_COEFF": 2.0e-6,
        },

        "INTEGRACION": {
            "DTHETA_OUTPUT_DEG": 0.50,

            # Refinamiento alrededor de la combustión.
            "DTHETA_COMBUSTION_DEG": 0.05,
            "FINE_BEFORE_SPARK_DEG": 10.0,
            "FINE_AFTER_TDC_DEG": 60.0,

            # Paso interno máximo de CVODES expresado como ángulo de eje.
            "MAX_INTERNAL_DTHETA_DEG": 0.25,

            # Se conserva por trazabilidad aunque el solver actual
            # utiliza max_time_step en lugar de advance_limit.
            "DELTA_T_ADVANCE_LIMIT_K": 8.0,

            "RTOL": 1.0e-9,
            "ATOL": 1.0e-15,
        },

        "MULTICICLO": {
            "MIN_CYCLES": 3,
            "MAX_CYCLES": 30,
            "CLOSURE_TOL_PCT": 1.0,
            "COMPOSITION_TOL_PCT": 1.0,
        },

        "MODELOS": {
            "quimica_cinetica": True,
            "transferencia_calor": True,
            "multiciclo": True,
            "mecanica_trabajo_virtual": True,
            "perdidas_mecanicas": False,
        },
    },
}


def listar_motores():
    return sorted(MOTORES.keys())


def obtener_motor(nombre):
    key = str(nombre).strip().lower()

    if key not in MOTORES:
        disponibles = ", ".join(listar_motores())
        raise KeyError(
            f"Motor '{nombre}' no definido. Disponibles: {disponibles}"
        )

    return deepcopy(MOTORES[key])


def validar_motor_config(config):
    motor = config["MOTOR"]
    geom = config["GEOMETRIA"]
    ciclo = config["CICLO"]
    oper = config["OPERACION"]

    if motor["familia_geometrica"] != "wankel_clasico_3_apex":
        raise ValueError(
            "La geometría actual solo implementa "
            "'wankel_clasico_3_apex'."
        )

    if int(motor["caras_por_rotor"]) != 3:
        raise ValueError(
            "La geometría Wankel clásica actual requiere 3 caras por rotor."
        )

    if int(motor["numero_rotores"]) < 1:
        raise ValueError("numero_rotores debe ser >= 1.")

    for k in ("e_m", "R_m", "b_m"):
        if float(geom[k]) <= 0.0:
            raise ValueError(f"{k} debe ser positivo.")

    if float(geom["CR"]) <= 1.0:
        raise ValueError("CR debe ser > 1.")

    if int(geom["N_PHI_ROTOR"]) % 3 != 0:
        raise ValueError("N_PHI_ROTOR debe ser divisible por 3.")

    if float(geom["relacion_eje_rotor"]) != 3.0:
        raise ValueError(
            "La familia geométrica actual usa relación eje:rotor 3:1."
        )

    if float(ciclo["CYCLE_END_DEG"]) != 1080.0:
        raise ValueError(
            "El solver actual está configurado para Wankel 4T = 1080° de eje."
        )

    if float(oper["RPM_EJE"]) <= 0.0:
        raise ValueError("RPM_EJE debe ser positivo.")

    return True
