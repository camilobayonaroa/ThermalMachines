# -*- coding: utf-8 -*-
"""
src/mecanica.py
===============

Módulo mecánico vectorial general del motor Wankel seleccionado.

FORMULACIÓN PRINCIPAL — O, C, P
-------------------------------
La implementación sigue explícitamente la construcción vectorial discutida
con el director de tesis:

    r_OP(theta) = r_OC(theta) + r_CP(theta)

Para una cara curva no se aplica una única normal a toda la longitud.
La cara se discretiza en segmentos j y, para cada segmento,

    dA_j = b * dl_j
    dF_j(theta) = -(P(theta) - P_ref) * n_j(theta) * dA_j
    dTau_j(theta) = r_OP,j(theta) x dF_j(theta)

por lo que el torque de una cara es

    Tau_cara(theta) = sum_j dTau_j(theta)

y el torque del motor se obtiene sumando las tres caras de cada rotor y
posteriormente los rotores con su desfase angular.

Esta forma es la versión discretizada y físicamente consistente de la
expresión dibujada:

    F = -n * p * A
    Tau = r_OP x F

para una superficie curva, donde la normal cambia a lo largo de la cara.

DESCOMPOSICIÓN ÚTIL
-------------------
Como r_OP = r_OC + r_CP,

    Tau_cara = r_OC x F_resultante
             + sum_j (r_CP,j x dF_j)

El segundo término es el momento de presión respecto al centro/centroide
del rotor C. Para una cara Wankel simétrica sometida a presión uniforme,
este término debe ser prácticamente nulo; el código lo calcula y lo reporta
como validación, no lo impone.

VALIDACIONES INDEPENDIENTES
---------------------------
1) Trabajo virtual:
       Tau_virtual(theta) = integral_A dF · (dr/dtheta_e)

2) Geometría analítica:
       Tau_PdV(theta) = (P - P_ref) * dV_geom/dtheta_e

3) Trabajo termodinámico:
       integral Tau_vectorial dtheta_e ~= integral (P - P_ref) dV

No se utiliza np.gradient(V_reactor) como referencia principal porque la
diferenciación numérica amplifica pequeños errores del volumen, en especial
si la malla angular fue refinada durante la combustión.

COMPATIBILIDAD
--------------
Se conservan las salidas históricas de trabajo virtual, r x F distribuido y
la aproximación radial antigua. Sin embargo, torque y potencia finales usan
la formulación vectorial O-C-P distribuida descrita arriba.
"""
from src.visualizacion import agregar_fases_ciclo
from pathlib import Path
import json

import numpy as np
import matplotlib.pyplot as plt

from configuracion.motor import MOTOR_KEY, MOTOR, GEOMETRIA, OPERACION, CICLO
from configuracion.combustibles import obtener_combustible
from src.geometria import cargar_geometria


EPS = 1.0e-30


# ============================================================
# 1. UTILIDADES
# ============================================================

def cumulative_trapezoid_manual(y, x):
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    out = np.zeros_like(y)

    if len(y) > 1:
        out[1:] = np.cumsum(
            0.5 * (y[1:] + y[:-1]) * np.diff(x)
        )

    return out


def periodic_shift_signal(theta_deg, signal, shift_deg):
    """Desplaza periódicamente una señal definida en 0..1080°."""
    theta_deg = np.asarray(theta_deg, dtype=float)
    signal = np.asarray(signal, dtype=float)

    period_deg = float(CICLO["CYCLE_END_DEG"])

    th_base = theta_deg[:-1]
    sig_base = signal[:-1]

    q = np.mod(theta_deg + shift_deg, period_deg)

    return np.interp(
        q,
        th_base,
        sig_base,
        period=period_deg,
    )


def rotation_matrix(angle_rad):
    c = np.cos(angle_rad)
    s = np.sin(angle_rad)

    return np.array([
        [c, -s],
        [s,  c],
    ])


def cross2d(r, f):
    r = np.asarray(r)
    f = np.asarray(f)

    return (
        r[..., 0] * f[..., 1]
        - r[..., 1] * f[..., 0]
    )


def volumen_geometrico_analitico(
    theta_cycle_deg,
    e_m,
    R_m,
    b_m,
    CR,
    phase_offset_deg,
):
    """
    V(theta) exacto del modelo geométrico utilizado en src/geometria.py.

    La química utiliza la referencia desplazada +810° respecto a la
    geometría almacenada.
    """
    theta_pose_rad = np.deg2rad(
        np.asarray(theta_cycle_deg, dtype=float)
        + phase_offset_deg
    )

    Vd = (
        3.0
        * np.sqrt(3.0)
        * e_m
        * R_m
        * b_m
    )

    Vmin = Vd / (CR - 1.0)

    arg = (
        (2.0 / 3.0)
        * (theta_pose_rad + 2.0 * np.pi)
        + np.pi / 6.0
    )

    V = (
        Vmin
        + 0.5
        * Vd
        * (1.0 - np.sin(arg))
    )

    return V


def dV_dtheta_geometrico_analitico(
    theta_cycle_deg,
    e_m,
    R_m,
    b_m,
    phase_offset_deg,
):
    """
    Derivada analítica dV/dtheta_e [m³/rad].

    V = Vmin + (Vd/2) [1 - sin(arg)]
    arg = (2/3)(theta_e + 2pi) + pi/6

    => dV/dtheta_e = -sqrt(3)*e*R*b*cos(arg)
    """
    theta_pose_rad = np.deg2rad(
        np.asarray(theta_cycle_deg, dtype=float)
        + phase_offset_deg
    )

    arg = (
        (2.0 / 3.0)
        * (theta_pose_rad + 2.0 * np.pi)
        + np.pi / 6.0
    )

    return (
        -np.sqrt(3.0)
        * e_m
        * R_m
        * b_m
        * np.cos(arg)
    )


# ============================================================
# 2. PREPROCESADO DE UNA CARA
# ============================================================

def _face_local_polyline(
    face_id,
    x_rotor_local,
    y_rotor_local,
):
    n_points = len(x_rotor_local)

    if n_points % 3 != 0:
        raise ValueError(
            "El perfil del rotor debe tener un número de puntos "
            "divisible por 3."
        )

    n_face = n_points // 3

    if face_id == 0:
        idx = np.arange(0, n_face + 1)

    elif face_id == 1:
        idx = np.arange(n_face, 2 * n_face + 1)

    elif face_id == 2:
        idx = np.r_[
            np.arange(2 * n_face, n_points),
            0,
        ]

    else:
        raise ValueError(
            "face_id debe ser 0, 1 o 2."
        )

    return (
        x_rotor_local[idx],
        y_rotor_local[idx],
    )


def _preprocess_face(
    face_id,
    x_rotor_local,
    y_rotor_local,
    b_m,
):
    """
    Precalcula:
    - puntos medios de segmentos;
    - normal exterior;
    - área diferencial;
    - longitud de arco;
    - área superficial real aproximada;
    - cuerda entre ápices;
    - área tipo cuerda;
    - centroide por longitud de arco.
    """

    x, y = _face_local_polyline(
        face_id,
        x_rotor_local,
        y_rotor_local,
    )

    apex_start = np.array([x[0], y[0]], dtype=float)
    apex_end = np.array([x[-1], y[-1]], dtype=float)

    p0 = np.column_stack([
        x[:-1],
        y[:-1],
    ])

    p1 = np.column_stack([
        x[1:],
        y[1:],
    ])

    d = p1 - p0
    ds = np.linalg.norm(d, axis=1)

    valid = ds > 1.0e-14

    p0 = p0[valid]
    p1 = p1[valid]
    d = d[valid]
    ds = ds[valid]

    midpoint_local = 0.5 * (p0 + p1)

    # Perfil CCW -> normal exterior hacia la derecha.
    n_out_local = np.column_stack([
        d[:, 1] / ds,
        -d[:, 0] / ds,
    ])

    dA = b_m * ds

    arc_length = float(np.sum(ds))
    area_surface = float(np.sum(dA))

    centroid_local = (
        np.sum(
            midpoint_local * ds[:, None],
            axis=0,
        )
        / max(np.sum(ds), EPS)
    )

    chord_length = float(
        np.linalg.norm(apex_end - apex_start)
    )

    area_chord = (
        b_m * chord_length
    )

    return {
        "midpoint_local": midpoint_local,
        "normal_out_local": n_out_local,
        "dA_m2": dA,
        "arc_length_m": arc_length,
        "area_surface_m2": area_surface,
        "chord_length_m": chord_length,
        "area_chord_m2": area_chord,
        "centroid_local_m": centroid_local,
    }


# ============================================================
# 3. CINEMÁTICA + FUERZAS PARA 1 Pa
# ============================================================

def _unit_face_mechanics(
    theta_cycle_deg,
    face,
    e_m,
    ratio_eje_rotor,
    phase_offset_deg,
):
    """
    Mecánica vectorial de una cara para 1 Pa de presión manométrica.

    Convención geométrica de la figura O-C-P:
        O : centro del eje excéntrico / origen fijo.
        C : centro-centroide del rotor.
        Pj: punto de aplicación del elemento de presión j
            (punto medio del segmento discretizado de la cara).

    Para cada elemento j:
        r_OP,j = r_OC + r_CP,j
        dF_j   = -n_j * dA_j              [N/Pa = m²]
        dTau_j = r_OP,j x dF_j            [N m/Pa = m³]

    Se retorna además la descomposición:
        Tau = r_OC x F_resultante
            + sum(r_CP,j x dF_j)

    El trabajo virtual se mantiene como validación independiente.
    """

    theta_pose = np.deg2rad(
        theta_cycle_deg + phase_offset_deg
    )

    theta_rotor = (
        theta_pose / ratio_eje_rotor
    )

    Q = rotation_matrix(theta_rotor)

    # --------------------------------------------------------
    # O -> C : posición del centro del rotor respecto al eje.
    # --------------------------------------------------------
    r_OC = np.array([
        e_m * np.cos(theta_pose),
        e_m * np.sin(theta_pose),
    ])

    dr_OC_dtheta = np.array([
        -e_m * np.sin(theta_pose),
        e_m * np.cos(theta_pose),
    ])

    # --------------------------------------------------------
    # C -> Pj : puntos de la cara en el sistema global.
    # --------------------------------------------------------
    r_CP_segments = (
        face["midpoint_local"] @ Q.T
    )

    # O -> Pj = O -> C + C -> Pj
    r_OP_segments = (
        r_OC + r_CP_segments
    )

    normal_out_world = (
        face["normal_out_local"] @ Q.T
    )

    # --------------------------------------------------------
    # FUERZA DE PRESIÓN PARA 1 Pa
    #
    # dA_j = b * dl_j ya está en face["dA_m2"].
    # La fuerza del gas sobre el rotor apunta en sentido opuesto
    # a la normal exterior del sólido.
    # --------------------------------------------------------
    dF_unit = (
        -normal_out_world
        * face["dA_m2"][:, None]
    )

    F_unit = np.sum(
        dF_unit,
        axis=0,
    )

    F_unit_mag = float(
        np.linalg.norm(F_unit)
    )

    if F_unit_mag > EPS:
        normal_resultant_out = (
            -F_unit / F_unit_mag
        )
    else:
        normal_resultant_out = np.zeros(2)

    # Para una presión unitaria, |F| tiene unidades m² y representa
    # el área efectiva proyectada del resultante.
    area_resultant_effective = F_unit_mag

    # --------------------------------------------------------
    # TORQUE VECTORIAL O-C-P — MÉTODO PRINCIPAL
    # --------------------------------------------------------
    dTau_vectorial_unit = cross2d(
        r_OP_segments,
        dF_unit,
    )

    tau_vectorial_unit = float(
        np.sum(dTau_vectorial_unit)
    )

    # Descomposición exacta de r_OP = r_OC + r_CP.
    tau_OC_unit = float(
        cross2d(
            r_OC,
            F_unit,
        )
    )

    tau_CP_unit = float(
        np.sum(
            cross2d(
                r_CP_segments,
                dF_unit,
            )
        )
    )

    tau_decomposition_unit = (
        tau_OC_unit
        + tau_CP_unit
    )

    decomposition_closure_unit = (
        tau_vectorial_unit
        - tau_decomposition_unit
    )

    # Alias físico: integral(r x dF) respecto al eje O.
    tau_rxf_distributed_unit = tau_vectorial_unit

    # Momento de la presión respecto a C.
    moment_about_rotor_center_unit = tau_CP_unit

    # --------------------------------------------------------
    # TRABAJO VIRTUAL — VALIDACIÓN INDEPENDIENTE
    # --------------------------------------------------------
    J = np.array([
        [0.0, -1.0],
        [1.0,  0.0],
    ])

    rotational_jacobian = (
        r_CP_segments @ J.T
    )

    dr_OP_dtheta = (
        dr_OC_dtheta
        + rotational_jacobian / ratio_eje_rotor
    )

    tau_virtual_unit = float(
        np.sum(
            np.sum(
                dF_unit * dr_OP_dtheta,
                axis=1,
            )
        )
    )

    # --------------------------------------------------------
    # PUNTO REPRESENTATIVO DE LA CARA
    #
    # Solo se guarda para visualizar la construcción O-C-P.
    # El torque principal NO usa un único punto: integra todos
    # los segmentos de la cara curva.
    # --------------------------------------------------------
    cumulative_area = np.cumsum(
        face["dA_m2"]
    )

    if len(cumulative_area):
        j_rep = int(
            np.searchsorted(
                cumulative_area,
                0.5 * cumulative_area[-1],
                side="left",
            )
        )
        j_rep = min(
            max(j_rep, 0),
            len(cumulative_area) - 1,
        )
    else:
        j_rep = 0

    r_CP_rep = r_CP_segments[j_rep].copy()
    r_OP_rep = r_OP_segments[j_rep].copy()
    normal_rep_out = normal_out_world[j_rep].copy()

    vector_closure_rep = float(
        np.linalg.norm(
            r_OC
            + r_CP_rep
            - r_OP_rep
        )
    )

    # Centroide geométrico de la longitud de arco de la cara.
    # Se conserva porque ya era salida del código anterior.
    face_centroid_world = (
        face["centroid_local_m"] @ Q.T
        + r_OC
    )

    # --------------------------------------------------------
    # APROXIMACIÓN ANTIGUA RADIAL — SOLO COMPATIBILIDAD
    #
    # OJO: esto NO es la ecuación dibujada por el director.
    # Se mantiene únicamente para comparar con versiones previas.
    # --------------------------------------------------------
    r1 = (
        face_centroid_world - r_OC
    )

    r1_norm = float(
        np.linalg.norm(r1)
    )

    if r1_norm > EPS:
        fhat_legacy = (
            -r1 / r1_norm
        )
    else:
        fhat_legacy = np.zeros(2)

    F_legacy_unit = (
        face["area_chord_m2"]
        * fhat_legacy
    )

    tau_document_old_unit = float(
        cross2d(
            face_centroid_world,
            F_legacy_unit,
        )
    )

    return {
        # Fuerza resultante para 1 Pa.
        "F_unit_N_Pa": F_unit,
        "F_unit_mag_m2": F_unit_mag,
        "normal_resultant_out": normal_resultant_out,
        "area_resultant_effective_m2":
            area_resultant_effective,

        # Torque principal y descomposición O-C-P.
        "tau_vectorial_unit_m3": tau_vectorial_unit,
        "tau_OC_unit_m3": tau_OC_unit,
        "tau_CP_unit_m3": tau_CP_unit,
        "tau_decomposition_unit_m3":
            tau_decomposition_unit,
        "decomposition_closure_unit_m3":
            decomposition_closure_unit,

        # Validaciones / compatibilidad.
        "tau_virtual_unit_m3": tau_virtual_unit,
        "tau_rxf_distributed_unit_m3":
            tau_rxf_distributed_unit,
        "tau_document_old_unit_m3":
            tau_document_old_unit,
        "moment_about_rotor_center_unit_m3":
            moment_about_rotor_center_unit,

        # Vectores de la construcción O-C-P.
        "r_OC_m": r_OC,
        "r_CP_rep_m": r_CP_rep,
        "r_OP_rep_m": r_OP_rep,
        "normal_rep_out": normal_rep_out,
        "vector_closure_rep_m": vector_closure_rep,

        # Salidas antiguas / auxiliares.
        "centroid_world_m": face_centroid_world,
        "center_rotor_m": r_OC,
    }


# ============================================================
# 4. FUNCIÓN PRINCIPAL
# ============================================================

def ejecutar_mecanica(
    nombre_combustible="isooctano",
    generar_graficas=True,
    mostrar_graficas=True,
):

    fuel_key = str(
        nombre_combustible
    ).strip().lower()

    fuel_cfg = obtener_combustible(
        fuel_key
    )

    base_dir = Path(
        __file__
    ).resolve().parents[1]

    out_root = (
        base_dir
        / "resultados"
        / MOTOR_KEY
        / fuel_key
    )

    out_mech = (
        out_root
        / "mecanica"
    )

    out_graphs = (
        out_mech
        / "graficas"
    )

    out_mech.mkdir(
        parents=True,
        exist_ok=True,
    )

    out_graphs.mkdir(
        parents=True,
        exist_ok=True,
    )

    state_file = (
        out_root
        / "estado_termodinamico.npz"
    )

    if not state_file.exists():
        raise FileNotFoundError(
            "\nNo existe el estado termodinámico:\n"
            f"{state_file}\n\n"
            "Ejecuta el caso completo desde run.py para generar "
            "primero el estado termodinámico."
        )

    data = np.load(
        state_file,
        allow_pickle=False,
    )

    geom = cargar_geometria()

    # ========================================================
    # ESTADO TERMODINÁMICO
    # ========================================================

    theta_deg = np.asarray(
        data["theta_deg"],
        dtype=float,
    )

    theta_rad = np.deg2rad(
        theta_deg
    )

    P = np.asarray(
        data["P_Pa"],
        dtype=float,
    )

    V = np.asarray(
        data["V_m3"],
        dtype=float,
    )

    rpm_eje = float(
        data["RPM_EJE"][0]
    )

    W_thermo_net_J = float(
        data["W_NET_PDV_J"][0]
    )

    # ========================================================
    # PARÁMETROS
    # ========================================================

    e_m = float(
        GEOMETRIA["e_m"]
    )

    R_m = float(
        GEOMETRIA["R_m"]
    )

    b_m = float(
        GEOMETRIA["b_m"]
    )

    CR = float(
        GEOMETRIA["CR"]
    )

    ratio = float(
        GEOMETRIA[
            "relacion_eje_rotor"
        ]
    )

    phase_offset_deg = float(
        CICLO[
            "GEOMETRY_PHASE_OFFSET_DEG"
        ]
    )

    p_ref = float(
        OPERACION["P_REF_PA"]
    )

    n_rotors = int(
        MOTOR["numero_rotores"]
    )

    faces_per_rotor = int(
        MOTOR["caras_por_rotor"]
    )

    # Con el offset termoquímico +810°,
    # la cámara corresponde geométricamente a la cara 2.
    active_face_id = 1

    x_rotor_local = np.asarray(
        geom["rotor_local_x_m"],
        dtype=float,
    )

    y_rotor_local = np.asarray(
        geom["rotor_local_y_m"],
        dtype=float,
    )

    face = _preprocess_face(
        active_face_id,
        x_rotor_local,
        y_rotor_local,
        b_m,
    )

    # ========================================================
    # GEOMETRÍA ANALÍTICA
    # ========================================================

    V_geom = volumen_geometrico_analitico(
        theta_deg,
        e_m,
        R_m,
        b_m,
        CR,
        phase_offset_deg,
    )

    dV_dtheta_geom = (
        dV_dtheta_geometrico_analitico(
            theta_deg,
            e_m,
            R_m,
            b_m,
            phase_offset_deg,
        )
    )

    # Solo diagnóstico: derivar V_reactor amplifica pequeños errores
    # de integración/interpolación y no debe ser la referencia mecánica.
    dV_dtheta_numeric = np.gradient(
        V,
        theta_rad,
    )

    V_error = (
        V - V_geom
    )

    V_error_max_cm3 = float(
        np.max(np.abs(V_error))
        * 1.0e6
    )

    V_error_rms_cm3 = float(
        np.sqrt(np.mean(V_error**2))
        * 1.0e6
    )

    P_gauge = (
        P - p_ref
    )

    # ========================================================
    # MECÁNICA DE LA CARA
    # ========================================================

    n = len(theta_deg)

    # Coeficientes de torque [m³ = N·m/Pa].
    k_tau_vectorial = np.zeros(n)
    k_tau_OC = np.zeros(n)
    k_tau_CP = np.zeros(n)
    k_tau_decomposition = np.zeros(n)

    k_tau_virtual = np.zeros(n)
    k_tau_rxf_distributed = np.zeros(n)
    k_tau_document_old = np.zeros(n)

    moment_center_unit = np.zeros(n)
    decomposition_closure_unit = np.zeros(n)

    # Fuerza y vectores O-C-P.
    F_unit_xy = np.zeros((n, 2))
    F_unit_mag_m2 = np.zeros(n)
    normal_resultant_out_xy = np.zeros((n, 2))

    r_OC_xy = np.zeros((n, 2))
    r_CP_rep_xy = np.zeros((n, 2))
    r_OP_rep_xy = np.zeros((n, 2))
    normal_rep_out_xy = np.zeros((n, 2))
    vector_closure_rep_m = np.zeros(n)

    # Compatibilidad con salidas anteriores.
    centroid_xy = np.zeros((n, 2))
    center_rotor_xy = np.zeros((n, 2))

    for i, th in enumerate(theta_deg):

        info = _unit_face_mechanics(
            th,
            face,
            e_m,
            ratio,
            phase_offset_deg,
        )

        k_tau_vectorial[i] = (
            info["tau_vectorial_unit_m3"]
        )

        k_tau_OC[i] = (
            info["tau_OC_unit_m3"]
        )

        k_tau_CP[i] = (
            info["tau_CP_unit_m3"]
        )

        k_tau_decomposition[i] = (
            info["tau_decomposition_unit_m3"]
        )

        k_tau_virtual[i] = (
            info["tau_virtual_unit_m3"]
        )

        k_tau_rxf_distributed[i] = (
            info["tau_rxf_distributed_unit_m3"]
        )

        k_tau_document_old[i] = (
            info["tau_document_old_unit_m3"]
        )

        moment_center_unit[i] = (
            info["moment_about_rotor_center_unit_m3"]
        )

        decomposition_closure_unit[i] = (
            info["decomposition_closure_unit_m3"]
        )

        F_unit_xy[i, :] = (
            info["F_unit_N_Pa"]
        )

        F_unit_mag_m2[i] = (
            info["F_unit_mag_m2"]
        )

        normal_resultant_out_xy[i, :] = (
            info["normal_resultant_out"]
        )

        r_OC_xy[i, :] = (
            info["r_OC_m"]
        )

        r_CP_rep_xy[i, :] = (
            info["r_CP_rep_m"]
        )

        r_OP_rep_xy[i, :] = (
            info["r_OP_rep_m"]
        )

        normal_rep_out_xy[i, :] = (
            info["normal_rep_out"]
        )

        vector_closure_rep_m[i] = (
            info["vector_closure_rep_m"]
        )

        centroid_xy[i, :] = (
            info["centroid_world_m"]
        )

        center_rotor_xy[i, :] = (
            info["center_rotor_m"]
        )

    # ========================================================
    # VALIDACIONES GEOMÉTRICAS
    # ========================================================

    geom_rms = max(
        float(
            np.sqrt(
                np.mean(
                    dV_dtheta_geom**2
                )
            )
        ),
        EPS,
    )

    # Validación principal: torque vectorial O-C-P vs dV/dtheta.
    vectorial_geom_rmse_rel = float(
        np.sqrt(
            np.mean(
                (
                    k_tau_vectorial
                    - dV_dtheta_geom
                )**2
            )
        )
        / geom_rms
    )

    vectorial_virtual_rmse_rel = float(
        np.sqrt(
            np.mean(
                (
                    k_tau_vectorial
                    - k_tau_virtual
                )**2
            )
        )
        / geom_rms
    )

    vectorial_decomposition_rmse_rel = float(
        np.sqrt(
            np.mean(
                (
                    k_tau_vectorial
                    - k_tau_decomposition
                )**2
            )
        )
        / geom_rms
    )

    cp_moment_ratio = float(
        np.max(np.abs(k_tau_CP))
        / max(
            np.max(np.abs(k_tau_vectorial)),
            EPS,
        )
    )

    area_resultant_mean_m2 = float(
        np.mean(F_unit_mag_m2)
    )

    area_resultant_span_m2 = float(
        np.ptp(F_unit_mag_m2)
    )

    area_chord_error_rel = float(
        (
            area_resultant_mean_m2
            - face["area_chord_m2"]
        )
        / max(
            abs(face["area_chord_m2"]),
            EPS,
        )
    )

    length_resultant_effective_m = (
        area_resultant_mean_m2
        / max(b_m, EPS)
    )

    vector_identity_max_m = float(
        np.max(np.abs(vector_closure_rep_m))
    )

    torque_decomposition_max_m3 = float(
        np.max(
            np.abs(
                decomposition_closure_unit
            )
        )
    )

    virtual_geom_rmse_rel = float(
        np.sqrt(
            np.mean(
                (
                    k_tau_virtual
                    - dV_dtheta_geom
                )**2
            )
        )
        / geom_rms
    )

    numeric_gradient_rmse_rel = float(
        np.sqrt(
            np.mean(
                (
                    dV_dtheta_numeric
                    - dV_dtheta_geom
                )**2
            )
        )
        / geom_rms
    )

    distributed_rxf_geom_rmse_rel = float(
        np.sqrt(
            np.mean(
                (
                    k_tau_rxf_distributed
                    - dV_dtheta_geom
                )**2
            )
        )
        / geom_rms
    )

    document_geom_rmse_rel = float(
        np.sqrt(
            np.mean(
                (
                    k_tau_document_old
                    - dV_dtheta_geom
                )**2
            )
        )
        / geom_rms
    )

    virtual_vs_rxf_rmse_rel = float(
        np.sqrt(
            np.mean(
                (
                    k_tau_virtual
                    - k_tau_rxf_distributed
                )**2
            )
        )
        / geom_rms
    )

    # ========================================================
    # TORQUES
    # ========================================================

    # Resultado principal: formulación vectorial O-C-P.
    tau_face_vectorial = (
        P_gauge
        * k_tau_vectorial
    )

    # Descomposición del torque:
    # tau = (OC x F) + sum(CP_j x dF_j)
    tau_face_OC = (
        P_gauge
        * k_tau_OC
    )

    tau_face_CP = (
        P_gauge
        * k_tau_CP
    )

    tau_face_decomposition = (
        tau_face_OC
        + tau_face_CP
    )

    # Trabajo virtual: validación independiente.
    tau_face_virtual = (
        P_gauge
        * k_tau_virtual
    )

    # Validación geométrica independiente.
    tau_face_pdv_geom = (
        P_gauge
        * dV_dtheta_geom
    )

    # Diagnóstico solamente.
    tau_face_pdv_numeric = (
        P_gauge
        * dV_dtheta_numeric
    )

    # Alias del cálculo distribuido exacto r x dF.
    tau_face_rxf_distributed = (
        P_gauge
        * k_tau_rxf_distributed
    )

    # Aproximación histórica radial; NO corresponde al esquema O-C-P.
    tau_face_document_old = (
        P_gauge
        * k_tau_document_old
    )

    F_resultant_xy = (
        P_gauge[:, None]
        * F_unit_xy
    )

    F_resultant_mag = np.linalg.norm(
        F_resultant_xy,
        axis=1,
    )

    # ========================================================
    # TRABAJO UNA CARA
    # ========================================================

    W_vectorial_cum = cumulative_trapezoid_manual(
        tau_face_vectorial,
        theta_rad,
    )

    W_virtual_cum = cumulative_trapezoid_manual(
        tau_face_virtual,
        theta_rad,
    )

    W_pdv_geom_cum = cumulative_trapezoid_manual(
        tau_face_pdv_geom,
        theta_rad,
    )

    W_pdv_numeric_cum = cumulative_trapezoid_manual(
        tau_face_pdv_numeric,
        theta_rad,
    )

    W_rxf_distributed_cum = cumulative_trapezoid_manual(
        tau_face_rxf_distributed,
        theta_rad,
    )

    W_document_old_cum = cumulative_trapezoid_manual(
        tau_face_document_old,
        theta_rad,
    )

    W_vectorial_face_J = float(
        W_vectorial_cum[-1]
    )

    W_virtual_face_J = float(
        W_virtual_cum[-1]
    )

    W_pdv_geom_face_J = float(
        W_pdv_geom_cum[-1]
    )

    W_pdv_numeric_face_J = float(
        W_pdv_numeric_cum[-1]
    )

    W_rxf_distributed_face_J = float(
        W_rxf_distributed_cum[-1]
    )

    W_document_old_face_J = float(
        W_document_old_cum[-1]
    )

    vectorial_pdv_geom_error_pct = (
        100.0
        * (
            W_vectorial_face_J
            - W_pdv_geom_face_J
        )
        / max(
            abs(W_pdv_geom_face_J),
            EPS,
        )
    )

    vectorial_thermo_error_pct = (
        100.0
        * (
            W_vectorial_face_J
            - W_thermo_net_J
        )
        / max(
            abs(W_thermo_net_J),
            EPS,
        )
    )

    vectorial_virtual_work_error_pct = (
        100.0
        * (
            W_vectorial_face_J
            - W_virtual_face_J
        )
        / max(
            abs(W_virtual_face_J),
            EPS,
        )
    )

    virtual_pdv_geom_error_pct = (
        100.0
        * (
            W_virtual_face_J
            - W_pdv_geom_face_J
        )
        / max(
            abs(W_pdv_geom_face_J),
            EPS,
        )
    )

    virtual_thermo_error_pct = (
        100.0
        * (
            W_virtual_face_J
            - W_thermo_net_J
        )
        / max(
            abs(W_thermo_net_J),
            EPS,
        )
    )

    pdv_geom_thermo_error_pct = (
        100.0
        * (
            W_pdv_geom_face_J
            - W_thermo_net_J
        )
        / max(
            abs(W_thermo_net_J),
            EPS,
        )
    )

    numeric_gradient_thermo_error_pct = (
        100.0
        * (
            W_pdv_numeric_face_J
            - W_thermo_net_J
        )
        / max(
            abs(W_thermo_net_J),
            EPS,
        )
    )

    distributed_rxf_thermo_error_pct = (
        100.0
        * (
            W_rxf_distributed_face_J
            - W_thermo_net_J
        )
        / max(
            abs(W_thermo_net_J),
            EPS,
        )
    )

    document_old_thermo_error_pct = (
        100.0
        * (
            W_document_old_face_J
            - W_thermo_net_J
        )
        / max(
            abs(W_thermo_net_J),
            EPS,
        )
    )

    # ========================================================
    # 3 CARAS / ROTOR
    # ========================================================

    face_shift_deg = (
        float(
            CICLO["CYCLE_END_DEG"]
        )
        / faces_per_rotor
    )

    tau_faces = np.asarray([
        periodic_shift_signal(
            theta_deg,
            tau_face_vectorial,
            j * face_shift_deg,
        )
        for j in range(
            faces_per_rotor
        )
    ])

    tau_single_rotor = np.sum(
        tau_faces,
        axis=0,
    )

    # ========================================================
    # 2 ROTORES
    # ========================================================

    rotor_phase_deg = (
        face_shift_deg / 2.0
    )

    rotor_signals = np.asarray([
        periodic_shift_signal(
            theta_deg,
            tau_single_rotor,
            j * rotor_phase_deg,
        )
        for j in range(
            n_rotors
        )
    ])

    tau_total_engine = np.sum(
        rotor_signals,
        axis=0,
    )

    # ========================================================
    # TORQUE MEDIO
    # ========================================================

    theta_span_rad = float(
        theta_rad[-1]
        - theta_rad[0]
    )

    tau_mean_signal_Nm = float(
        np.trapezoid(
            tau_total_engine,
            theta_rad,
        )
        / theta_span_rad
    )

    # En 1080° de eje cada una de las 6 caras completa un ciclo.
    tau_mean_work_Nm = float(
        (
            n_rotors
            * faces_per_rotor
            * W_vectorial_face_J
        )
        / theta_span_rad
    )

    tau_mean_consistency_pct = (
        100.0
        * (
            tau_mean_signal_Nm
            - tau_mean_work_Nm
        )
        / max(
            abs(tau_mean_work_Nm),
            EPS,
        )
    )

    # ========================================================
    # POTENCIA
    # ========================================================

    omega_eje_rad_s = (
        2.0
        * np.pi
        * rpm_eje
        / 60.0
    )

    power_single_rotor_W = (
        tau_single_rotor
        * omega_eje_rad_s
    )

    power_total_engine_W = (
        tau_total_engine
        * omega_eje_rad_s
    )

    power_mean_ind_W = (
        tau_mean_work_Nm
        * omega_eje_rad_s
    )

    cycle_time_s = (
        theta_span_rad
        / omega_eje_rad_s
    )

    power_from_work_W = (
        n_rotors
        * faces_per_rotor
        * W_vectorial_face_J
        / cycle_time_s
    )

    power_consistency_pct = (
        100.0
        * (
            power_mean_ind_W
            - power_from_work_W
        )
        / max(
            abs(power_from_work_W),
            EPS,
        )
    )

    # ========================================================
    # REPORTE
    # ========================================================

    print()
    print("=" * 78)
    print(
        f"MECÁNICA VECTORIAL O-C-P — "
        f"{fuel_cfg['nombre'].upper()} / {MOTOR['nombre']}"
    )
    print("=" * 78)

    print(
        f"RPM eje = {rpm_eje:.2f}"
    )

    print(
        f"omega eje = "
        f"{omega_eje_rad_s:.6f} rad/s"
    )

    print(
        f"Presión de referencia = "
        f"{p_ref/1000.0:.3f} kPa"
    )

    print(
        f"Cara geométrica activa = "
        f"{active_face_id + 1} "
        "(fijada por referencia angular)"
    )

    print()
    print(
        "--- GEOMETRÍA DE LA CARA ---"
    )

    print(
        f"Longitud de arco l = "
        f"{face['arc_length_m']*1000.0:.3f} mm"
    )

    print(
        f"Área superficial curva b·l = "
        f"{face['area_surface_m2']*1e4:.3f} cm²"
    )

    print(
        f"Longitud de cuerda = "
        f"{face['chord_length_m']*1000.0:.3f} mm"
    )

    print(
        f"Área proyectada por cuerda = "
        f"{face['area_chord_m2']*1e4:.3f} cm²"
    )

    print(
        f"Área efectiva del resultante = "
        f"{area_resultant_mean_m2*1e4:.3f} cm²"
    )

    print(
        f"Longitud efectiva del resultante = "
        f"{length_resultant_effective_m*1000.0:.3f} mm"
    )

    print(
        "Error área efectiva resultante vs área de cuerda = "
        f"{100.0*area_chord_error_rel:+.6e} %"
    )

    print()
    print(
        "--- FORMULACIÓN O-C-P DEL DIRECTOR ---"
    )

    print(
        "Implementación exacta sobre la cara curva:"
    )

    print(
        "r_OP,j = r_OC + r_CP,j"
    )

    print(
        "dF_j = -(P-P_ref) n_j (b dl_j)"
    )

    print(
        "dTau_j = r_OP,j x dF_j"
    )

    print(
        "Tau_cara = sum_j dTau_j"
    )

    print(
        "Cierre máximo r_OC + r_CP - r_OP = "
        f"{vector_identity_max_m:.6e} m"
    )

    print(
        "Cierre máximo de la descomposición de torque = "
        f"{torque_decomposition_max_m3:.6e} m³"
    )

    print(
        "Contribución máxima relativa del término "
        "sum(r_CP x dF) = "
        f"{100.0*cp_moment_ratio:.6f} %"
    )

    print(
        "Momento unitario máximo respecto a C = "
        f"{np.max(np.abs(moment_center_unit)):.6e} m³"
    )

    print()
    print(
        "--- VALIDACIÓN GEOMÉTRICA ---"
    )

    print(
        f"Error máx V_reactor vs V_geom = "
        f"{V_error_max_cm3:.6f} cm³"
    )

    print(
        f"Error RMS V_reactor vs V_geom = "
        f"{V_error_rms_cm3:.6f} cm³"
    )

    print(
        "RMSE relativo torque vectorial O-C-P "
        "vs dV/dθ analítico = "
        f"{100.0*vectorial_geom_rmse_rel:.6f} %"
    )

    print(
        "RMSE relativo trabajo virtual "
        "vs dV/dθ analítico = "
        f"{100.0*virtual_geom_rmse_rel:.6f} %"
    )

    print(
        "RMSE relativo vectorial vs trabajo virtual = "
        f"{100.0*vectorial_virtual_rmse_rel:.6e} %"
    )

    print(
        "RMSE relativo vectorial vs "
        "[OC×F + sum(CP×dF)] = "
        f"{100.0*vectorial_decomposition_rmse_rel:.6e} %"
    )

    print(
        "RMSE relativo np.gradient(V_reactor) "
        "vs dV/dθ analítico = "
        f"{100.0*numeric_gradient_rmse_rel:.6f} %"
    )

    print(
        "NOTA: np.gradient(V_reactor) se conserva solo "
        "como diagnóstico."
    )

    print()
    print(
        "--- UNA CARA ---"
    )

    print(
        f"Fuerza resultante máxima = "
        f"{np.max(F_resultant_mag):.3f} N"
    )

    print(
        f"Torque VECTORIAL O-C-P min/max = "
        f"{np.min(tau_face_vectorial):+.3f} / "
        f"{np.max(tau_face_vectorial):+.3f} N·m"
    )

    print(
        f"Trabajo vectorial O-C-P = "
        f"{W_vectorial_face_J:+.6f} J"
    )

    print(
        f"Trabajo virtual = "
        f"{W_virtual_face_J:+.6f} J"
    )

    print(
        f"Trabajo (P-Pref)dV/dθ analítico = "
        f"{W_pdv_geom_face_J:+.6f} J"
    )

    print(
        f"Trabajo termodinámico directo P-dV = "
        f"{W_thermo_net_J:+.6f} J"
    )

    print(
        f"Error vectorial vs dV/dθ analítico = "
        f"{vectorial_pdv_geom_error_pct:+.6f} %"
    )

    print(
        f"Error vectorial vs termodinámica = "
        f"{vectorial_thermo_error_pct:+.6f} %"
    )

    print(
        f"Error vectorial vs trabajo virtual = "
        f"{vectorial_virtual_work_error_pct:+.6f} %"
    )

    print(
        f"Error trabajo virtual vs termodinámica = "
        f"{virtual_thermo_error_pct:+.6f} %"
    )

    print(
        f"Error dV/dθ analítico vs termodinámica = "
        f"{pdv_geom_thermo_error_pct:+.6f} %"
    )

    print()
    print(
        "--- DIAGNÓSTICOS / COMPATIBILIDAD ---"
    )

    print(
        f"Trabajo r×F distribuido exacto = "
        f"{W_rxf_distributed_face_J:+.6f} J"
    )

    print(
        f"Error r×F distribuido vs termodinámica = "
        f"{distributed_rxf_thermo_error_pct:+.6f} %"
    )

    print(
        f"Trabajo usando np.gradient(V_reactor) = "
        f"{W_pdv_numeric_face_J:+.6f} J"
    )

    print(
        f"Error np.gradient vs termodinámica = "
        f"{numeric_gradient_thermo_error_pct:+.3f} %"
    )

    print(
        f"Trabajo aproximación radial antigua = "
        f"{W_document_old_face_J:+.6f} J"
    )

    print(
        f"Error aproximación radial antigua vs termodinámica = "
        f"{document_old_thermo_error_pct:+.3f} %"
    )

    print(
        "NOTA: la aproximación radial antigua NO corresponde al "
        "esquema O-C-P dibujado por el director y no se usa en "
        "torque ni potencia finales."
    )

    print()
    print(
        "--- MOTOR COMPLETO ---"
    )

    print(
        f"Torque medio indicado desde señal = "
        f"{tau_mean_signal_Nm:.3f} N·m"
    )

    print(
        f"Torque medio indicado desde trabajo = "
        f"{tau_mean_work_Nm:.3f} N·m"
    )

    print(
        f"Cierre torque medio = "
        f"{tau_mean_consistency_pct:+.6e} %"
    )

    print(
        f"Torque total instantáneo min/max = "
        f"{np.min(tau_total_engine):+.3f} / "
        f"{np.max(tau_total_engine):+.3f} N·m"
    )

    print(
        f"Potencia indicada media = "
        f"{power_mean_ind_W/1000.0:.3f} kW"
    )

    print(
        f"Potencia indicada media = "
        f"{power_mean_ind_W/745.699872:.3f} hp"
    )

    print(
        f"Potencia desde trabajo/ciclo = "
        f"{power_from_work_W/1000.0:.3f} kW"
    )

    print(
        f"Cierre potencia = "
        f"{power_consistency_pct:+.6e} %"
    )

    # ========================================================
    # GUARDADO NPZ
    # ========================================================

    state_mech_file = (
        out_root
        / "estado_mecanico.npz"
    )

    np.savez(
        state_mech_file,

        fuel_key=np.asarray([fuel_key]),
        fuel_name=np.asarray([fuel_cfg["nombre"]]),

        theta_deg=theta_deg,
        theta_rad=theta_rad,

        P_Pa=P,
        P_gauge_Pa=P_gauge,

        V_reactor_m3=V,
        V_geom_m3=V_geom,

        dV_dtheta_geom_m3_rad=dV_dtheta_geom,
        dV_dtheta_numeric_m3_rad=dV_dtheta_numeric,

        # Formulación vectorial principal O-C-P.
        k_tau_vectorial_m3=k_tau_vectorial,
        k_tau_OC_m3=k_tau_OC,
        k_tau_CP_m3=k_tau_CP,
        k_tau_decomposition_m3=k_tau_decomposition,

        k_tau_virtual_m3=k_tau_virtual,
        k_tau_rxf_distributed_m3=k_tau_rxf_distributed,
        k_tau_document_old_m3=k_tau_document_old,

        F_resultant_xy_N=F_resultant_xy,
        F_resultant_mag_N=F_resultant_mag,
        F_unit_mag_m2=F_unit_mag_m2,
        normal_resultant_out_xy=normal_resultant_out_xy,

        # Vectores O-C-P; P_rep solo visualiza el punto medio
        # representativo. El torque principal integra toda la cara.
        r_OC_xy_m=r_OC_xy,
        r_CP_rep_xy_m=r_CP_rep_xy,
        r_OP_rep_xy_m=r_OP_rep_xy,
        normal_rep_out_xy=normal_rep_out_xy,
        vector_closure_rep_m=vector_closure_rep_m,

        centroid_xy_m=centroid_xy,
        center_rotor_xy_m=center_rotor_xy,

        tau_face_vectorial_Nm=tau_face_vectorial,
        tau_face_OC_Nm=tau_face_OC,
        tau_face_CP_Nm=tau_face_CP,
        tau_face_decomposition_Nm=tau_face_decomposition,

        tau_face_virtual_Nm=tau_face_virtual,
        tau_face_PdV_geom_Nm=tau_face_pdv_geom,
        tau_face_PdV_numeric_Nm=tau_face_pdv_numeric,
        tau_face_rxf_distributed_Nm=tau_face_rxf_distributed,
        tau_face_document_old_Nm=tau_face_document_old,

        tau_faces_rotor_Nm=tau_faces,
        tau_single_rotor_Nm=tau_single_rotor,
        rotor_signals_Nm=rotor_signals,
        tau_total_engine_Nm=tau_total_engine,

        power_single_rotor_W=power_single_rotor_W,
        power_total_engine_W=power_total_engine_W,

        W_vectorial_cum_J=W_vectorial_cum,
        W_virtual_cum_J=W_virtual_cum,
        W_PdV_geom_cum_J=W_pdv_geom_cum,
        W_PdV_numeric_cum_J=W_pdv_numeric_cum,
        W_rxf_distributed_cum_J=W_rxf_distributed_cum,
        W_document_old_cum_J=W_document_old_cum,

        W_VECTORIAL_FACE_J=np.asarray([W_vectorial_face_J]),
        W_VIRTUAL_FACE_J=np.asarray([W_virtual_face_J]),
        W_PDV_GEOM_FACE_J=np.asarray([W_pdv_geom_face_J]),
        W_PDV_NUMERIC_FACE_J=np.asarray([W_pdv_numeric_face_J]),
        W_THERMO_NET_J=np.asarray([W_thermo_net_J]),
        W_RXF_DISTRIBUTED_FACE_J=np.asarray([W_rxf_distributed_face_J]),
        W_DOCUMENT_OLD_FACE_J=np.asarray([W_document_old_face_J]),

        VECTORIAL_GEOM_RMSE_REL=np.asarray(
            [vectorial_geom_rmse_rel]
        ),
        VECTORIAL_VIRTUAL_RMSE_REL=np.asarray(
            [vectorial_virtual_rmse_rel]
        ),
        VECTORIAL_DECOMPOSITION_RMSE_REL=np.asarray(
            [vectorial_decomposition_rmse_rel]
        ),
        CP_MOMENT_RATIO=np.asarray([cp_moment_ratio]),
        AREA_RESULTANT_MEAN_M2=np.asarray(
            [area_resultant_mean_m2]
        ),
        AREA_RESULTANT_SPAN_M2=np.asarray(
            [area_resultant_span_m2]
        ),
        AREA_CHORD_ERROR_REL=np.asarray(
            [area_chord_error_rel]
        ),

        VIRTUAL_GEOM_RMSE_REL=np.asarray([virtual_geom_rmse_rel]),
        NUMERIC_GRADIENT_RMSE_REL=np.asarray([numeric_gradient_rmse_rel]),
        DISTRIBUTED_RXF_GEOM_RMSE_REL=np.asarray(
            [distributed_rxf_geom_rmse_rel]
        ),
        DOCUMENT_GEOM_RMSE_REL=np.asarray([document_geom_rmse_rel]),

        VECTORIAL_PDV_GEOM_ERROR_PCT=np.asarray(
            [vectorial_pdv_geom_error_pct]
        ),
        VECTORIAL_THERMO_ERROR_PCT=np.asarray(
            [vectorial_thermo_error_pct]
        ),
        VECTORIAL_VIRTUAL_WORK_ERROR_PCT=np.asarray(
            [vectorial_virtual_work_error_pct]
        ),

        VIRTUAL_PDV_GEOM_ERROR_PCT=np.asarray(
            [virtual_pdv_geom_error_pct]
        ),
        VIRTUAL_THERMO_ERROR_PCT=np.asarray(
            [virtual_thermo_error_pct]
        ),
        PDV_GEOM_THERMO_ERROR_PCT=np.asarray(
            [pdv_geom_thermo_error_pct]
        ),
        NUMERIC_GRADIENT_THERMO_ERROR_PCT=np.asarray(
            [numeric_gradient_thermo_error_pct]
        ),
        DOCUMENT_OLD_THERMO_ERROR_PCT=np.asarray(
            [document_old_thermo_error_pct]
        ),

        TAU_MEAN_SIGNAL_NM=np.asarray([tau_mean_signal_Nm]),
        TAU_MEAN_WORK_NM=np.asarray([tau_mean_work_Nm]),
        TAU_MEAN_CONSISTENCY_PCT=np.asarray(
            [tau_mean_consistency_pct]
        ),

        POWER_IND_MEAN_W=np.asarray([power_mean_ind_W]),
        POWER_FROM_WORK_W=np.asarray([power_from_work_W]),
        POWER_CONSISTENCY_PCT=np.asarray(
            [power_consistency_pct]
        ),

        RPM_EJE=np.asarray([rpm_eje]),
        OMEGA_EJE_RAD_S=np.asarray([omega_eje_rad_s]),
        ACTIVE_FACE_ID=np.asarray([active_face_id]),
        P_REF_PA=np.asarray([p_ref]),
    )

    # ========================================================
    # JSON
    # ========================================================

    resumen = {
        "fuel": fuel_key,
        "fuel_name": fuel_cfg["nombre"],
        "rpm_eje": rpm_eje,
        "active_face_display": active_face_id + 1,

        "formulacion_principal":
            "Vectorial O-C-P distribuida sobre la cara curva",

        "V_error_max_cm3": V_error_max_cm3,
        "V_error_rms_cm3": V_error_rms_cm3,

        "vectorial_geom_rmse_pct":
            100.0 * vectorial_geom_rmse_rel,

        "vectorial_virtual_rmse_pct":
            100.0 * vectorial_virtual_rmse_rel,

        "vectorial_decomposition_rmse_pct":
            100.0 * vectorial_decomposition_rmse_rel,

        "cp_moment_ratio_pct":
            100.0 * cp_moment_ratio,

        "area_surface_curve_cm2":
            face["area_surface_m2"] * 1.0e4,

        "area_chord_cm2":
            face["area_chord_m2"] * 1.0e4,

        "area_resultant_effective_cm2":
            area_resultant_mean_m2 * 1.0e4,

        "area_chord_error_pct":
            100.0 * area_chord_error_rel,

        "vector_identity_max_m":
            vector_identity_max_m,

        "torque_decomposition_closure_max_m3":
            torque_decomposition_max_m3,

        "virtual_geom_rmse_pct":
            100.0 * virtual_geom_rmse_rel,

        "numeric_gradient_rmse_pct":
            100.0 * numeric_gradient_rmse_rel,

        "W_vectorial_face_J":
            W_vectorial_face_J,

        "W_virtual_face_J":
            W_virtual_face_J,

        "W_PdV_geom_face_J":
            W_pdv_geom_face_J,

        "W_thermo_net_J":
            W_thermo_net_J,

        "W_numeric_gradient_face_J":
            W_pdv_numeric_face_J,

        "vectorial_PdV_geom_error_pct":
            vectorial_pdv_geom_error_pct,

        "vectorial_thermo_error_pct":
            vectorial_thermo_error_pct,

        "vectorial_virtual_work_error_pct":
            vectorial_virtual_work_error_pct,

        "virtual_PdV_geom_error_pct":
            virtual_pdv_geom_error_pct,

        "virtual_thermo_error_pct":
            virtual_thermo_error_pct,

        "numeric_gradient_thermo_error_pct":
            numeric_gradient_thermo_error_pct,

        "W_rxf_distributed_face_J":
            W_rxf_distributed_face_J,

        "W_document_old_face_J":
            W_document_old_face_J,

        "document_old_thermo_error_pct":
            document_old_thermo_error_pct,

        "force_resultant_max_N":
            float(np.max(F_resultant_mag)),

        "tau_face_min_Nm":
            float(np.min(tau_face_vectorial)),

        "tau_face_max_Nm":
            float(np.max(tau_face_vectorial)),

        "tau_engine_min_Nm":
            float(np.min(tau_total_engine)),

        "tau_engine_max_Nm":
            float(np.max(tau_total_engine)),

        "tau_mean_indicated_Nm":
            tau_mean_work_Nm,

        "power_indicated_mean_kW":
            power_mean_ind_W / 1000.0,

        "power_indicated_mean_hp":
            power_mean_ind_W / 745.699872,

        "power_consistency_pct":
            power_consistency_pct,
    }

    with open(
        out_mech
        / "resumen_mecanica.json",
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            resumen,
            f,
            indent=2,
            ensure_ascii=False,
        )

    # ========================================================
    # GRÁFICAS
    # ========================================================

    if generar_graficas:

        # 1. Geometría/Jacobiano
        fig, ax = plt.subplots(figsize=(11, 5))

        ax.plot(
            theta_deg,
            dV_dtheta_geom * 1e6,
            lw=2.2,
            label="dV/dθ analítico — referencia",
        )

        ax.plot(
            theta_deg,
            k_tau_vectorial * 1e6,
            lw=2.2,
            label="Vectorial O-C-P — PRINCIPAL",
        )

        ax.plot(
            theta_deg,
            k_tau_virtual * 1e6,
            "--",
            lw=1.8,
            label="Trabajo virtual",
        )

        ax.plot(
            theta_deg,
            dV_dtheta_numeric * 1e6,
            lw=0.9,
            alpha=0.6,
            label="np.gradient(V reactor) — diagnóstico",
        )

        ax.axhline(0.0, lw=0.8)

        ax.set_xlabel(
            "Ángulo del eje excéntrico [°]"
        )

        ax.set_ylabel(
            "Coeficiente [cm³/rad]"
        )

        ax.set_title(
            "Validación geométrica del Jacobiano mecánico"
        )

        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)

        agregar_fases_ciclo(ax)

        fig.tight_layout()
        fig.savefig(
            out_graphs
            / "01_validacion_jacobiano_analitico.png",
            dpi=220,
        )

        if mostrar_graficas:
            plt.show()
        else:
            plt.close(fig)

        # 2. Torque una cara
        fig, ax = plt.subplots(figsize=(11, 5))

        ax.plot(
            theta_deg,
            tau_face_vectorial,
            lw=2.3,
            label="Vectorial O-C-P — PRINCIPAL",
        )

        ax.plot(
            theta_deg,
            tau_face_virtual,
            "--",
            lw=1.7,
            label="Trabajo virtual — validación",
        )

        ax.plot(
            theta_deg,
            tau_face_pdv_geom,
            lw=1.2,
            alpha=0.8,
            label="(P-Pref)dV/dθ analítico",
        )

        ax.axhline(0.0, lw=0.8)

        ax.set_xlabel(
            "Ángulo del eje excéntrico [°]"
        )

        ax.set_ylabel(
            "Torque [N·m]"
        )

        ax.set_title(
            f"Torque de una cara — {fuel_cfg['nombre']}"
        )

        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)

        agregar_fases_ciclo(ax)
        fig.tight_layout()
        fig.savefig(
            out_graphs
            / "02_torque_vectorial_OCP_vs_validaciones.png",
            dpi=220,
        )

        if mostrar_graficas:
            plt.show()
        else:
            plt.close(fig)

        # 3. Cierre de trabajo
        fig, ax = plt.subplots(figsize=(11, 5))

        ax.plot(
            theta_deg,
            W_vectorial_cum,
            lw=2.2,
            label="Integral torque vectorial O-C-P",
        )

        ax.plot(
            theta_deg,
            W_virtual_cum,
            "--",
            lw=1.7,
            label="Integral trabajo virtual",
        )

        ax.plot(
            theta_deg,
            W_pdv_geom_cum,
            lw=1.2,
            alpha=0.8,
            label="Integral (P-Pref)dV/dθ analítico",
        )

        ax.set_xlabel(
            "Ángulo del eje excéntrico [°]"
        )

        ax.set_ylabel(
            "Trabajo acumulado [J]"
        )

        ax.set_title(
            "Cierre trabajo vectorial O-C-P — termodinámica"
        )

        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)

        agregar_fases_ciclo(ax)
        fig.tight_layout()
        fig.savefig(
            out_graphs
            / "03_cierre_trabajo_vectorial_OCP.png",
            dpi=220,
        )

        if mostrar_graficas:
            plt.show()
        else:
            plt.close(fig)

        # 4. Fuerza resultante
        fig, ax = plt.subplots(figsize=(11, 5))

        ax.plot(
            theta_deg,
            F_resultant_mag,
            lw=2.0,
        )

        ax.set_xlabel(
            "Ángulo del eje excéntrico [°]"
        )

        ax.set_ylabel(
            "|F resultante| [N]"
        )

        ax.set_title(
            "Fuerza resultante de presión sobre la cara"
        )

        ax.grid(True, alpha=0.3)

        agregar_fases_ciclo(ax)
        fig.tight_layout()
        fig.savefig(
            out_graphs
            / "04_fuerza_resultante.png",
            dpi=220,
        )

        if mostrar_graficas:
            plt.show()
        else:
            plt.close(fig)

        # 5. Tres caras
        fig, ax = plt.subplots(figsize=(11, 5))

        for j in range(faces_per_rotor):
            ax.plot(
                theta_deg,
                tau_faces[j],
                lw=1.1,
                label=f"Cara {j+1}",
            )

        ax.plot(
            theta_deg,
            tau_single_rotor,
            lw=2.3,
            label="Total rotor",
        )

        ax.axhline(0.0, lw=0.8)

        ax.set_xlabel(
            "Ángulo del eje excéntrico [°]"
        )

        ax.set_ylabel(
            "Torque [N·m]"
        )

        ax.set_title(
            "Torque indicado — tres caras de un rotor"
        )

        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)

        agregar_fases_ciclo(ax)
        fig.tight_layout()
        fig.savefig(
            out_graphs
            / "05_torque_tres_caras_un_rotor.png",
            dpi=220,
        )

        if mostrar_graficas:
            plt.show()
        else:
            plt.close(fig)

        # 6. Motor completo
        fig, ax = plt.subplots(figsize=(11, 5))

        for j in range(n_rotors):
            ax.plot(
                theta_deg,
                rotor_signals[j],
                lw=1.2,
                label=f"Rotor {j+1}",
            )

        ax.plot(
            theta_deg,
            tau_total_engine,
            lw=2.4,
            label="Torque total motor",
        )

        ax.axhline(
            tau_mean_work_Nm,
            ls="--",
            lw=1.2,
            label=(
                "Torque medio = "
                f"{tau_mean_work_Nm:.2f} N·m"
            ),
        )

        ax.set_xlabel(
            "Ángulo del eje excéntrico [°]"
        )

        ax.set_ylabel(
            "Torque [N·m]"
        )

        ax.set_title(
            f"Torque indicado instantáneo — {MOTOR['nombre']}"
        )

        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)

        agregar_fases_ciclo(ax)
        fig.tight_layout()
        fig.savefig(
            out_graphs
            / "06_torque_total_motor.png",
            dpi=220,
        )

        if mostrar_graficas:
            plt.show()
        else:
            plt.close(fig)

        # 7. Potencia
        fig, ax = plt.subplots(figsize=(11, 5))

        ax.plot(
            theta_deg,
            power_total_engine_W / 1000.0,
            lw=2.3,
            label="Potencia indicada instantánea",
        )

        ax.axhline(
            power_mean_ind_W / 1000.0,
            ls="--",
            lw=1.2,
            label=(
                "Potencia media = "
                f"{power_mean_ind_W/1000.0:.2f} kW"
            ),
        )

        ax.set_xlabel(
            "Ángulo del eje excéntrico [°]"
        )

        ax.set_ylabel(
            "Potencia [kW]"
        )

        ax.set_title(
            f"Potencia indicada — {MOTOR['nombre']}"
        )

        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)

        agregar_fases_ciclo(ax)
        fig.tight_layout()
        fig.savefig(
            out_graphs
            / "07_potencia_indicada_motor.png",
            dpi=220,
        )

        if mostrar_graficas:
            plt.show()
        else:
            plt.close(fig)

        # 8. Brazos vectoriales O-C-P (punto representativo de la cara)
        r_OC_mag = np.linalg.norm(
            r_OC_xy,
            axis=1,
        )

        r_CP_rep_mag = np.linalg.norm(
            r_CP_rep_xy,
            axis=1,
        )

        r_OP_rep_mag = np.linalg.norm(
            r_OP_rep_xy,
            axis=1,
        )

        fig, ax = plt.subplots(figsize=(11, 5))

        ax.plot(
            theta_deg,
            r_OC_mag * 1000.0,
            lw=1.8,
            label="|r_OC|",
        )

        ax.plot(
            theta_deg,
            r_CP_rep_mag * 1000.0,
            lw=1.8,
            label="|r_CP| — P representativo",
        )

        ax.plot(
            theta_deg,
            r_OP_rep_mag * 1000.0,
            lw=2.2,
            label="|r_OP| — P representativo",
        )

        ax.set_xlabel(
            "Ángulo del eje excéntrico [°]"
        )

        ax.set_ylabel(
            "Longitud [mm]"
        )

        ax.set_title(
            "Brazos vectoriales O-C-P"
        )

        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)

        agregar_fases_ciclo(ax)

        fig.tight_layout()
        fig.savefig(
            out_graphs
            / "08_brazos_vectoriales_O_C_P.png",
            dpi=220,
        )

        if mostrar_graficas:
            plt.show()
        else:
            plt.close(fig)

        # 9. Descomposición del torque O-C-P
        fig, ax = plt.subplots(figsize=(11, 5))

        ax.plot(
            theta_deg,
            tau_face_vectorial,
            lw=2.3,
            label="Tau total vectorial O-C-P",
        )

        ax.plot(
            theta_deg,
            tau_face_OC,
            "--",
            lw=1.8,
            label="r_OC × F_resultante",
        )

        ax.plot(
            theta_deg,
            tau_face_CP,
            lw=1.2,
            label="sum(r_CP × dF)",
        )

        ax.axhline(0.0, lw=0.8)

        ax.set_xlabel(
            "Ángulo del eje excéntrico [°]"
        )

        ax.set_ylabel(
            "Torque [N·m]"
        )

        ax.set_title(
            "Descomposición vectorial del torque de una cara"
        )

        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)

        agregar_fases_ciclo(ax)
        fig.tight_layout()
        fig.savefig(
            out_graphs
            / "09_descomposicion_torque_O_C_P.png",
            dpi=220,
        )

        if mostrar_graficas:
            plt.show()
        else:
            plt.close(fig)

    print()
    print(
        f"[OK] Estado mecánico: "
        f"{state_mech_file}"
    )

    print(
        f"[OK] Resultados mecánicos: "
        f"{out_mech}"
    )

    return {
        "state_file": state_mech_file,
        "output_dir": out_mech,

        "formulacion_principal":
            "Vectorial O-C-P distribuida",

        "W_vectorial_face_J":
            W_vectorial_face_J,

        "W_virtual_face_J":
            W_virtual_face_J,

        "W_PdV_geom_face_J":
            W_pdv_geom_face_J,

        "W_thermo_net_J":
            W_thermo_net_J,

        "vectorial_geom_rmse_rel":
            vectorial_geom_rmse_rel,

        "vectorial_virtual_rmse_rel":
            vectorial_virtual_rmse_rel,

        "vectorial_pdv_geom_error_pct":
            vectorial_pdv_geom_error_pct,

        "vectorial_thermo_error_pct":
            vectorial_thermo_error_pct,

        "virtual_geom_rmse_rel":
            virtual_geom_rmse_rel,

        "numeric_gradient_rmse_rel":
            numeric_gradient_rmse_rel,

        "virtual_pdv_geom_error_pct":
            virtual_pdv_geom_error_pct,

        "virtual_thermo_error_pct":
            virtual_thermo_error_pct,

        "document_old_thermo_error_pct":
            document_old_thermo_error_pct,

        "tau_mean_indicated_Nm":
            tau_mean_work_Nm,

        "power_indicated_mean_W":
            power_mean_ind_W,

        "power_indicated_mean_hp":
            power_mean_ind_W / 745.699872,

        "tau_engine_min_Nm":
            float(np.min(tau_total_engine)),

        "tau_engine_max_Nm":
            float(np.max(tau_total_engine)),
    }