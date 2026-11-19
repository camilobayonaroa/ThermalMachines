# -*- coding: utf-8 -*-
"""
src/geometria.py
================

Geometría Wankel 4T genérica para la familia clásica de rotor triangular
(3 ápices, relación eje:rotor = 3:1).

El motor seleccionado NO se define aquí.
Se obtiene automáticamente desde configuracion/motor.py, que a su vez es
seleccionado por run.py mediante --motor.

La geometría es independiente del combustible.

Resultados:
    datos_comunes/geometrias/<motor>/
"""

from pathlib import Path
import hashlib
import json

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath

from configuracion.motor import (
    MOTOR_KEY,
    MOTOR,
    GEOMETRIA,
)


BASE_DIR = Path(__file__).resolve().parents[1]

DIR_GEOMETRIA = (
    BASE_DIR
    / "datos_comunes"
    / "geometrias"
    / MOTOR_KEY
)

DIR_GRAFICAS = (
    DIR_GEOMETRIA
    / "graficas"
)

GEOMETRY_MODEL_VERSION = "2.0.0-general-motor"
TOL_VALIDACION_M = 0.15e-3

STATE_FILE = (
    DIR_GEOMETRIA
    / "geometria.npz"
)

META_FILE = (
    DIR_GEOMETRIA
    / "metadata.json"
)


def _signature():
    payload = {
        "version": GEOMETRY_MODEL_VERSION,
        "motor_key": MOTOR_KEY,
        "motor": MOTOR,
        "geometria": GEOMETRIA,
        "tolerancia_m": TOL_VALIDACION_M,
    }

    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(raw).hexdigest()


def geometria_cache_valida():
    if not STATE_FILE.exists() or not META_FILE.exists():
        return False

    try:
        meta = json.loads(
            META_FILE.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return False

    return (
        meta.get("signature")
        == _signature()
    )


def construir_rotor_envolvente_interior(
    x_housing,
    y_housing,
    e,
    R,
    n_posiciones,
    n_phi,
):
    """
    Construye el rotor como envolvente interior numérica del housing.
    """

    r_min = np.full(
        n_phi,
        np.inf,
        dtype=float,
    )

    theta_env = np.linspace(
        0.0,
        6.0 * np.pi,
        n_posiciones,
        endpoint=False,
    )

    for theta_e in theta_env:
        cx = e * np.cos(theta_e)
        cy = e * np.sin(theta_e)

        theta_r = theta_e / 3.0

        c = np.cos(theta_r)
        s = np.sin(theta_r)

        dx = x_housing - cx
        dy = y_housing - cy

        x_local = (
            c * dx
            + s * dy
        )

        y_local = (
            -s * dx
            + c * dy
        )

        phi = np.mod(
            np.arctan2(
                y_local,
                x_local,
            ),
            2.0 * np.pi,
        )

        radio = np.hypot(
            x_local,
            y_local,
        )

        bins = (
            np.rint(
                phi
                / (2.0 * np.pi)
                * n_phi
            ).astype(np.int32)
            % n_phi
        )

        np.minimum.at(
            r_min,
            bins,
            radio,
        )

    indices = np.arange(n_phi)
    finite = np.isfinite(r_min)

    if not np.all(finite):
        idx_ok = indices[finite]
        r_ok = r_min[finite]

        idx_ext = np.concatenate([
            idx_ok - n_phi,
            idx_ok,
            idx_ok + n_phi,
        ])

        r_ext = np.concatenate([
            r_ok,
            r_ok,
            r_ok,
        ])

        r_min = np.interp(
            indices,
            idx_ext,
            r_ext,
        )

    n_sector = n_phi // 3

    r_sector = np.minimum.reduce([
        r_min[0:n_sector],
        r_min[n_sector:2*n_sector],
        r_min[2*n_sector:3*n_sector],
    ])

    r_rotor = np.tile(
        r_sector,
        3,
    )

    phi_rotor = (
        np.arange(n_phi)
        * 2.0 * np.pi
        / n_phi
    )

    # Ápices exactos.
    for apex in (
        0.0,
        2.0 * np.pi / 3.0,
        4.0 * np.pi / 3.0,
    ):
        idx = int(
            round(
                apex
                / (2.0 * np.pi)
                * n_phi
            )
        ) % n_phi

        r_rotor[idx] = R

    return (
        phi_rotor,
        r_rotor,
        r_rotor * np.cos(phi_rotor),
        r_rotor * np.sin(phi_rotor),
    )


def rotor_en_mundo(
    theta_e,
    x_local,
    y_local,
):
    e = float(
        GEOMETRIA["e_m"]
    )

    ratio = float(
        GEOMETRIA[
            "relacion_eje_rotor"
        ]
    )

    theta_r = (
        theta_e / ratio
    )

    c = np.cos(theta_r)
    s = np.sin(theta_r)

    cx = e * np.cos(theta_e)
    cy = e * np.sin(theta_e)

    x_world = (
        c * x_local
        - s * y_local
        + cx
    )

    y_world = (
        s * x_local
        + c * y_local
        + cy
    )

    return (
        x_world,
        y_world,
        cx,
        cy,
        theta_r,
    )


def _calcular_geometria():
    if (
        MOTOR["familia_geometrica"]
        != "wankel_clasico_3_apex"
    ):
        raise NotImplementedError(
            "La versión actual de geometria.py implementa "
            "wankel_clasico_3_apex."
        )

    e = float(GEOMETRIA["e_m"])
    R = float(GEOMETRIA["R_m"])
    b = float(GEOMETRIA["b_m"])
    CR = float(GEOMETRIA["CR"])

    n_theta = int(
        GEOMETRIA["N_THETA"]
    )

    n_housing = int(
        GEOMETRIA["N_HOUSING"]
    )

    n_pos_env = int(
        GEOMETRIA["N_POS_ENV"]
    )

    n_phi = int(
        GEOMETRIA["N_PHI_ROTOR"]
    )

    cycle_deg = float(
        GEOMETRIA["ciclo_eje_deg"]
    )

    ratio = float(
        GEOMETRIA[
            "relacion_eje_rotor"
        ]
    )

    theta_eje = np.linspace(
        0.0,
        np.deg2rad(cycle_deg),
        n_theta,
    )

    theta_rotor = (
        theta_eje / ratio
    )

    theta_eje_deg = np.rad2deg(
        theta_eje
    )

    theta_rotor_deg = np.rad2deg(
        theta_rotor
    )

    # --------------------------------------------------------
    # Volumen Yamamoto
    # --------------------------------------------------------

    Vd = (
        3.0
        * np.sqrt(3.0)
        * e
        * R
        * b
    )

    Vmin = (
        Vd / (CR - 1.0)
    )

    Vmax = (
        Vmin + Vd
    )

    A = (
        theta_eje
        + 2.0 * np.pi
    )

    V = (
        Vmin
        + (
            3.0
            * np.sqrt(3.0)
            / 2.0
        )
        * e
        * R
        * b
        * (
            1.0
            - np.sin(
                (2.0 / 3.0) * A
                + np.pi / 6.0
            )
        )
    )

    # Ajuste numérico únicamente para imponer exactamente Vmin/Vmax.
    V = (
        Vmin
        + (
            V - np.min(V)
        )
        * Vd
        / (
            np.max(V)
            - np.min(V)
        )
    )

    dV_dtheta = np.gradient(
        V,
        theta_eje,
    )

    def shifted_volume(shift_deg):
        q = np.mod(
            theta_eje_deg + shift_deg,
            cycle_deg,
        )

        q = np.where(
            np.isclose(
                q,
                0.0,
                atol=1.0e-12,
            )
            & (
                theta_eje_deg
                + shift_deg
                > 0.0
            ),
            cycle_deg,
            q,
        )

        return np.interp(
            q,
            theta_eje_deg,
            V,
        )

    face_shift = (
        cycle_deg
        / int(
            MOTOR["caras_por_rotor"]
        )
    )

    V_faces = np.asarray([
        shifted_volume(
            j * face_shift
        )
        for j in range(
            int(
                MOTOR[
                    "caras_por_rotor"
                ]
            )
        )
    ])

    # --------------------------------------------------------
    # Housing epitrocoidal
    # --------------------------------------------------------

    alpha = np.linspace(
        0.0,
        2.0 * np.pi,
        n_housing,
        endpoint=False,
    )

    x_h = (
        R * np.cos(alpha)
        + e * np.cos(
            3.0 * alpha
        )
    )

    y_h = (
        R * np.sin(alpha)
        + e * np.sin(
            3.0 * alpha
        )
    )

    # --------------------------------------------------------
    # Rotor por envolvente interior
    # --------------------------------------------------------

    print(
        f"Calculando geometría del motor '{MOTOR_KEY}'..."
    )

    (
        phi_rotor,
        r_rotor,
        x_rl,
        y_rl,
    ) = construir_rotor_envolvente_interior(
        x_h,
        y_h,
        e,
        R,
        n_pos_env,
        n_phi,
    )

    # --------------------------------------------------------
    # Validación de contención
    # --------------------------------------------------------

    housing_path = MplPath(
        np.column_stack([
            x_h,
            y_h,
        ]),
        closed=True,
    )

    n_fuera_max = 0

    for theta_test in np.linspace(
        0.0,
        6.0 * np.pi,
        73,
        endpoint=False,
    ):
        xt, yt, *_ = rotor_en_mundo(
            theta_test,
            x_rl,
            y_rl,
        )

        inside = (
            housing_path
            .contains_points(
                np.column_stack([
                    xt,
                    yt,
                ]),
                radius=TOL_VALIDACION_M,
            )
        )

        n_fuera_max = max(
            n_fuera_max,
            int(
                np.sum(~inside)
            ),
        )

    if n_fuera_max != 0:
        raise RuntimeError(
            "La geometría seleccionada no supera la validación "
            f"de contención. Puntos fuera máximos = {n_fuera_max}."
        )

    CR_numeric = (
        float(np.max(V))
        / float(np.min(V))
    )

    if not np.isclose(
        CR_numeric,
        CR,
        rtol=0.0,
        atol=1.0e-8,
    ):
        raise RuntimeError(
            f"CR geométrica inconsistente: {CR_numeric} vs {CR}."
        )

    data = {
        "motor_key": MOTOR_KEY,

        "theta_eje_rad": theta_eje,
        "theta_rotor_rad": theta_rotor,

        "angulos_eje_deg": theta_eje_deg,
        "angulos_rotor_deg": theta_rotor_deg,

        "volumen_m3": V,
        "volumen_cm3": V * 1.0e6,
        "dV_dtheta_eje_m3_rad": dV_dtheta,

        "volumen_caras_m3": V_faces,

        "housing_x_m": x_h,
        "housing_y_m": y_h,

        "rotor_phi_rad": phi_rotor,
        "rotor_radius_m": r_rotor,

        "rotor_local_x_m": x_rl,
        "rotor_local_y_m": y_rl,

        "E_m": e,
        "R_m": R,
        "B_m": b,
        "K": R / e,
        "CR": CR,

        "Vd_m3": Vd,
        "Vmin_m3": Vmin,
        "Vmax_m3": Vmax,

        "desplazamiento_nominal_m3":
            Vd
            * int(
                MOTOR[
                    "numero_rotores"
                ]
            ),

        "n_fuera_max": n_fuera_max,

        "rotor_radius_min_m":
            float(np.min(r_rotor)),

        "rotor_radius_max_m":
            float(np.max(r_rotor)),
    }

    return data


def _guardar_geometria(data):
    DIR_GEOMETRIA.mkdir(
        parents=True,
        exist_ok=True,
    )

    DIR_GRAFICAS.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Guardado único y autocontenido.
    np.savez(
        STATE_FILE,
        **{
            key: (
                np.asarray([value])
                if np.isscalar(value)
                and not isinstance(value, str)
                else value
            )
            for key, value in data.items()
            if key != "motor_key"
        },
    )

    META_FILE.write_text(
        json.dumps(
            {
                "motor_key": MOTOR_KEY,
                "motor_name": MOTOR["nombre"],
                "signature": _signature(),
                "version": GEOMETRY_MODEL_VERSION,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def cargar_geometria():
    if not geometria_cache_valida():
        data, _ = generar_geometria(
            forzar=True,
            generar_graficas=False,
            mostrar_graficas=False,
        )
        return data

    npz = np.load(
        STATE_FILE,
        allow_pickle=False,
    )

    data = {}

    for key in npz.files:
        value = npz[key]

        if (
            value.ndim == 1
            and value.size == 1
            and key in {
                "E_m",
                "R_m",
                "B_m",
                "K",
                "CR",
                "Vd_m3",
                "Vmin_m3",
                "Vmax_m3",
                "desplazamiento_nominal_m3",
                "n_fuera_max",
                "rotor_radius_min_m",
                "rotor_radius_max_m",
            }
        ):
            data[key] = float(value[0])
        else:
            data[key] = value

    data["motor_key"] = MOTOR_KEY

    return data


def crear_graficas_geometria(
    data,
    mostrar=False,
):
    DIR_GRAFICAS.mkdir(
        parents=True,
        exist_ok=True,
    )

    theta = data[
        "angulos_eje_deg"
    ]

    V_cm3 = data[
        "volumen_cm3"
    ]

    # 1. Volumen
    fig, ax = plt.subplots(
        figsize=(10, 5)
    )

    ax.plot(
        theta,
        V_cm3,
        lw=2.0,
    )

    ax.set_xlabel(
        "Ángulo del eje excéntrico [°]"
    )

    ax.set_ylabel(
        "Volumen [cm³]"
    )

    ax.set_title(
        f"Volumen de cámara — {MOTOR['nombre']}"
    )

    ax.grid(
        True,
        alpha=0.3,
    )

    fig.tight_layout()

    fig.savefig(
        DIR_GRAFICAS
        / "01_volumen_vs_angulo.png",
        dpi=220,
    )

    if mostrar:
        plt.show()
    else:
        plt.close(fig)

    # 2. Caras
    fig, ax = plt.subplots(
        figsize=(10, 5)
    )

    for i, vf in enumerate(
        data[
            "volumen_caras_m3"
        ]
    ):
        ax.plot(
            theta,
            vf * 1.0e6,
            lw=1.5,
            label=f"Cara {i+1}",
        )

    ax.set_xlabel(
        "Ángulo del eje excéntrico [°]"
    )

    ax.set_ylabel(
        "Volumen [cm³]"
    )

    ax.set_title(
        "Volumen de las cámaras del rotor"
    )

    ax.grid(
        True,
        alpha=0.3,
    )

    ax.legend()

    fig.tight_layout()

    fig.savefig(
        DIR_GRAFICAS
        / "02_volumen_tres_camaras.png",
        dpi=220,
    )

    if mostrar:
        plt.show()
    else:
        plt.close(fig)

    # 3. Geometría
    fig, ax = plt.subplots(
        figsize=(7, 7)
    )

    ax.plot(
        data["housing_x_m"] * 1000.0,
        data["housing_y_m"] * 1000.0,
        lw=1.8,
        label="Housing",
    )

    xt, yt, cx, cy, _ = rotor_en_mundo(
        0.0,
        data["rotor_local_x_m"],
        data["rotor_local_y_m"],
    )

    ax.plot(
        xt * 1000.0,
        yt * 1000.0,
        lw=1.8,
        label="Rotor",
    )

    ax.scatter(
        [0.0],
        [0.0],
        s=25,
        label="Centro eje",
    )

    ax.scatter(
        [cx * 1000.0],
        [cy * 1000.0],
        s=25,
        label="Centro rotor",
    )

    ax.set_aspect(
        "equal",
        adjustable="box",
    )

    ax.set_xlabel(
        "x [mm]"
    )

    ax.set_ylabel(
        "y [mm]"
    )

    ax.set_title(
        f"Geometría Wankel — {MOTOR['nombre']}"
    )

    ax.grid(
        True,
        alpha=0.3,
    )

    ax.legend(
        fontsize=8,
    )

    fig.tight_layout()

    fig.savefig(
        DIR_GRAFICAS
        / "03_geometria_wankel.png",
        dpi=220,
    )

    if mostrar:
        plt.show()
    else:
        plt.close(fig)

    # 4. Múltiples posiciones
    fig, ax = plt.subplots(
        figsize=(7, 7)
    )

    ax.plot(
        data["housing_x_m"] * 1000.0,
        data["housing_y_m"] * 1000.0,
        lw=2.0,
        label="Housing",
    )

    for th in np.linspace(
        0.0,
        2.0 * np.pi,
        7,
        endpoint=False,
    ):
        xt, yt, *_ = rotor_en_mundo(
            th,
            data["rotor_local_x_m"],
            data["rotor_local_y_m"],
        )

        ax.plot(
            xt * 1000.0,
            yt * 1000.0,
            lw=0.9,
            alpha=0.7,
        )

    ax.set_aspect(
        "equal",
        adjustable="box",
    )

    ax.set_xlabel("x [mm]")
    ax.set_ylabel("y [mm]")

    ax.set_title(
        "Comprobación del rotor en múltiples posiciones"
    )

    ax.grid(
        True,
        alpha=0.3,
    )

    fig.tight_layout()

    fig.savefig(
        DIR_GRAFICAS
        / "04_comprobacion_multiples_posiciones.png",
        dpi=220,
    )

    if mostrar:
        plt.show()
    else:
        plt.close(fig)


def imprimir_resumen_geometria(
    data,
    origen,
):
    print()
    print("=" * 70)
    print(
        f"GEOMETRÍA — {MOTOR['nombre'].upper()}"
    )
    print("=" * 70)

    print(
        f"Motor = {MOTOR_KEY}"
    )

    print(
        f"Origen = {origen}"
    )

    print(
        f"e = {data['E_m']*1000.0:.3f} mm"
    )

    print(
        f"R = {data['R_m']*1000.0:.3f} mm"
    )

    print(
        f"b = {data['B_m']*1000.0:.3f} mm"
    )

    print(
        f"K = {data['K']:.4f}"
    )

    print(
        f"CR = {data['CR']:.4f}:1"
    )

    print(
        f"Vd por cara = "
        f"{data['Vd_m3']*1.0e6:.3f} cm³"
    )

    print(
        f"Vmin = "
        f"{data['Vmin_m3']*1.0e6:.3f} cm³"
    )

    print(
        f"Vmax = "
        f"{data['Vmax_m3']*1.0e6:.3f} cm³"
    )

    print(
        f"Desplazamiento nominal = "
        f"{data['desplazamiento_nominal_m3']*1.0e6:.3f} cm³"
    )

    print(
        f"Puntos fuera máximos = "
        f"{int(data['n_fuera_max'])}"
    )

    print(
        f"Resultados = {DIR_GEOMETRIA}"
    )

    print("=" * 70)


def generar_geometria(
    forzar=False,
    generar_graficas=True,
    mostrar_graficas=False,
):
    if (
        not forzar
        and geometria_cache_valida()
    ):
        data = cargar_geometria()
        origen = "cache geométrica válida"

    else:
        data = _calcular_geometria()
        _guardar_geometria(data)
        origen = "geometría recalculada"

    if generar_graficas:
        crear_graficas_geometria(
            data,
            mostrar=mostrar_graficas,
        )

    imprimir_resumen_geometria(
        data,
        origen,
    )

    return data, origen
