# -*- coding: utf-8 -*-
"""
configuracion/motor.py
======================

Capa de compatibilidad entre el registro general de motores
(configuracion/motores.py) y los módulos físicos del modelo.

Este archivo NO define un motor fijo.
run.py selecciona el motor mediante WANKEL_MOTOR.
"""

import os

from configuracion.motores import (
    obtener_motor,
    validar_motor_config,
)

MOTOR_KEY = os.environ.get(
    "WANKEL_MOTOR",
    "13b",
).strip().lower()

_CONFIG = obtener_motor(MOTOR_KEY)
validar_motor_config(_CONFIG)

MOTOR = _CONFIG["MOTOR"]
GEOMETRIA = _CONFIG["GEOMETRIA"]
OPERACION = _CONFIG["OPERACION"]
CICLO = _CONFIG["CICLO"]
ENCENDIDO = _CONFIG["ENCENDIDO"]
TRANSFERENCIA_CALOR = _CONFIG["TRANSFERENCIA_CALOR"]
PUERTOS = _CONFIG["PUERTOS"]
INTEGRACION = _CONFIG["INTEGRACION"]
MULTICICLO = _CONFIG["MULTICICLO"]
MODELOS = _CONFIG["MODELOS"]


def validar_configuracion_motor():
    return validar_motor_config(_CONFIG)


def obtener_motor_activo():
    return MOTOR_KEY, _CONFIG
