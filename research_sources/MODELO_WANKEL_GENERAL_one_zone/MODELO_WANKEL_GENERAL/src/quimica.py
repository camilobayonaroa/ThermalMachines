# -*- coding: utf-8 -*-
"""
src/quimica.py
==============

Solver termoquímico GENERAL para el motor Wankel seleccionado.

El combustible NO está escrito dentro del solver. Se recibe desde:
    configuracion/combustibles.py

El motor y la condición de operación se reciben desde:
    configuracion/motor.py

La geometría se recibe desde:
    src/geometria.py

Incluye:
- Cantera + cinética química de velocidad finita;
- volumen Wankel V(theta);
- admisión y escape;
- transferencia de calor acoplada;
- pulso de encendido efectivo para reactor 0-D;
- integración multiciclo hasta régimen periódico;
- historias de especies y tasas químicas;
- conversión absoluta del combustible;
- CA10 / CA50 / CA90;
- validación estequiométrica de productos configurados;
- reacciones dominantes por contribución energética;
- guardado de estado para termodinámica y mecánica posteriores;
- sincronización estricta de advance_limits con la malla angular.
"""

from pathlib import Path
import csv
import json

import cantera as ct
import numpy as np
import matplotlib.pyplot as plt

from configuracion.motor import (
    MOTOR_KEY,
    MOTOR,
    OPERACION,
    CICLO,
    ENCENDIDO,
    TRANSFERENCIA_CALOR,
    PUERTOS,
    INTEGRACION,
    MULTICICLO,
)
from configuracion.combustibles import obtener_combustible
from src.geometria import generar_geometria
from src.mecanismos import cargar_solucion


# ============================================================
# 1. RUTAS GENERALES
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]
DIR_RESULTADOS = BASE_DIR / "resultados"

X_FLOOR = 1.0e-30


# ============================================================
# 2. UTILIDADES NUMÉRICAS
# ============================================================

def cumulative_trapezoid_manual(y, x):
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    out = np.zeros_like(y)
    if len(y) > 1:
        out[1:] = np.cumsum(0.5 * (y[1:] + y[:-1]) * np.diff(x))
    return out


def nearest_index(arr, value):
    return int(np.argmin(np.abs(np.asarray(arr) - value)))


def closure_percent(initial, final):
    """Diferencia relativa simétrica en porcentaje."""
    scale = max(0.5 * (abs(initial) + abs(final)), 1.0e-30)
    return 100.0 * abs(final - initial) / scale


def composition_closure_percent(Y0, Y1):
    """Distancia de variación total de composición másica [%]."""
    return 50.0 * np.sum(np.abs(np.asarray(Y1) - np.asarray(Y0)))


def valve_window(theta_deg, theta_open, theta_close):
    return float(theta_open <= theta_deg < theta_close)


def _species_presentes(lista, species_names):
    return [sp for sp in lista if sp in species_names]


# ============================================================
# 3. ETAPAS DEL CICLO
# ============================================================

def stage_name(theta_deg):
    ivc = CICLO["INTAKE_CLOSE_DEG"]
    spark = ENCENDIDO["SPARK_ANGLE_DEG"]
    tdc = CICLO["TDC_COMBUSTION_DEG"]
    eo = CICLO["EXPANSION_END_DEG"]
    end = CICLO["CYCLE_END_DEG"]

    if CICLO["INTAKE_OPEN_DEG"] <= theta_deg < ivc:
        return "ADMISION"
    if ivc <= theta_deg < spark:
        return "COMPRESION"
    if spark <= theta_deg < tdc:
        return "ENCENDIDO_COMBUSTION_EN_COMPRESION"
    if tdc <= theta_deg < eo:
        return "COMBUSTION_EXPANSION"
    if CICLO["EXHAUST_OPEN_DEG"] <= theta_deg <= CICLO["EXHAUST_CLOSE_DEG"]:
        return "ESCAPE"
    if theta_deg <= end:
        return "TRANSICION"
    return "FUERA_DE_CICLO"


def marcar_etapas(ax):
    ivc = CICLO["INTAKE_CLOSE_DEG"]
    spark = ENCENDIDO["SPARK_ANGLE_DEG"]
    tdc = CICLO["TDC_COMBUSTION_DEG"]
    eo = CICLO["EXPANSION_END_DEG"]
    end = CICLO["CYCLE_END_DEG"]

    for ang in [ivc, spark, tdc, eo]:
        ax.axvline(ang, ls="--", lw=0.8, alpha=0.55)

    ymin, ymax = ax.get_ylim()
    if np.isclose(ymin, ymax):
        ymax = ymin + 1.0
    ytxt = ymin + 0.95 * (ymax - ymin)

    etiquetas = [
        (0.5 * ivc, "ADMISIÓN"),
        (0.5 * (ivc + spark), "COMPRESIÓN"),
        (0.5 * (tdc + eo), "COMB./EXP."),
        (0.5 * (eo + end), "ESCAPE"),
    ]

    for x, txt in etiquetas:
        ax.text(x, ytxt, txt, ha="center", va="top", fontsize=8)

    ax.text(
        0.5 * (spark + tdc),
        ytxt,
        "ENC.",
        ha="center",
        va="bottom",
        fontsize=7,
        rotation=90,
    )


# ============================================================
# 4. TRANSFERENCIA DE CALOR
# ============================================================

def h_wankel_tipo_woschni(P, T, rpm):
    """
    Correlación empírica tipo-Woschni conservada como aproximación
    inicial. No debe presentarse como Woschni exacta para Wankel.
    """
    P_use = max(float(P), 2.0e4)
    T_use = max(float(T), 250.0)

    return (
        0.685
        * (rpm / 1000.0) ** 0.786
        * (P_use / 1.0e5) ** 0.786
        * T_use ** (-0.525)
        * 1.0e3
    )


def area_mojada_equivalente(Vloc, b_width):
    """Área mojada equivalente; futura sustitución por área geométrica real."""
    A_plan = max(float(Vloc) / b_width, 1.0e-12)
    diam_eq = np.sqrt(4.0 * A_plan / np.pi)
    return 2.0 * A_plan + np.pi * diam_eq * b_width


# ============================================================
# 5. SOLVER PRINCIPAL
# ============================================================

def ejecutar_quimica(
    nombre_combustible,
    generar_graficas=True,
    mostrar_graficas=False,
):
    """
    Ejecuta la simulación termoquímica multiciclo para un combustible.

    Parameters
    ----------
    nombre_combustible : str
        Clave definida en configuracion/combustibles.py.

    generar_graficas : bool
        Guarda las gráficas químicas.

    mostrar_graficas : bool
        Si True, muestra las figuras además de guardarlas.

    Returns
    -------
    resultado : dict
        Resumen y rutas principales de la simulación.
    """

    fuel_key = str(nombre_combustible).strip().lower()
    fuel_cfg = obtener_combustible(fuel_key)

    out_root = DIR_RESULTADOS / MOTOR_KEY / fuel_key
    out_chem = out_root / "quimica"
    out_graph = out_chem / "graficas"

    out_root.mkdir(parents=True, exist_ok=True)
    out_chem.mkdir(parents=True, exist_ok=True)
    out_graph.mkdir(parents=True, exist_ok=True)

    state_file = out_root / "estado_acoplado.npz"
    summary_file = out_chem / "resumen_quimica.json"

    # --------------------------------------------------------
    # Condición de operación
    # --------------------------------------------------------
    rpm_eje = float(OPERACION["RPM_EJE"])
    omega_eje_rad_s = 2.0 * np.pi * rpm_eje / 60.0
    omega_eje_deg_s = 6.0 * rpm_eje

    T_intake = float(OPERACION["T_INTAKE_K"])
    P_intake = float(OPERACION["P_INTAKE_PA"])
    T_residual = float(OPERACION["T_RESIDUAL_K"])
    P_residual = float(OPERACION["P_RESIDUAL_PA"])
    T_exhaust = float(OPERACION["T_EXHAUST_K"])
    P_exhaust = float(OPERACION["P_EXHAUST_PA"])

    T_wall = float(TRANSFERENCIA_CALOR["T_WALL_K"])

    spark_angle = float(ENCENDIDO["SPARK_ANGLE_DEG"])
    spark_duration_deg = float(ENCENDIDO["SPARK_DURATION_DEG"])
    T_ign_target = float(
        fuel_cfg.get(
            "ignition_target_K",
            ENCENDIDO["T_IGNITION_TARGET_K"],
        )
    )

    theta_end = float(CICLO["CYCLE_END_DEG"])
    geometry_offset = float(CICLO["GEOMETRY_PHASE_OFFSET_DEG"])

    dtheta_output = float(INTEGRACION["DTHETA_OUTPUT_DEG"])

    # Resolución reforzada alrededor de la combustión. La malla general se
    # mantiene relativamente gruesa para no inflar memoria/CSV, pero se añade
    # una malla fina alrededor de chispa/TDC para resolver adecuadamente los
    # picos químicos, CA10/50/90 y las gráficas de combustión.
    dtheta_combustion = float(
        INTEGRACION.get("DTHETA_COMBUSTION_DEG", 0.05)
    )
    fine_before_spark = float(
        INTEGRACION.get("FINE_BEFORE_SPARK_DEG", 10.0)
    )
    fine_after_tdc = float(
        INTEGRACION.get("FINE_AFTER_TDC_DEG", 60.0)
    )

    if dtheta_output <= 0.0 or dtheta_combustion <= 0.0:
        raise ValueError("Las resoluciones angulares deben ser positivas.")

    delta_T_limit = float(INTEGRACION["DELTA_T_ADVANCE_LIMIT_K"])
    rtol = float(INTEGRACION["RTOL"])
    atol = float(INTEGRACION["ATOL"])

    # Integración temporal: ya NO usamos advance_limit como controlador de
    # puntos de salida. CVODES integra adaptativamente y cada estado se pide
    # exactamente en el tiempo asociado a la malla angular. Para reforzar la
    # resolución fuera de la ventana fina, limitamos solamente el paso interno
    # máximo del integrador.
    max_internal_dtheta_deg = float(
        INTEGRACION.get("MAX_INTERNAL_DTHETA_DEG", 0.25)
    )
    if max_internal_dtheta_deg <= 0.0:
        raise ValueError("MAX_INTERNAL_DTHETA_DEG debe ser positivo.")

    MAX_INTERNAL_DT_S = max_internal_dtheta_deg / omega_eje_deg_s

    # Al usar advance(..., apply_limit=False), el punto solicitado debe quedar
    # prácticamente exacto. Esta tolerancia es únicamente para redondeo de
    # punto flotante, no una tolerancia física del modelo.
    SYNC_TOL_DEG = 1.0e-6
    SYNC_TOL_S = SYNC_TOL_DEG / omega_eje_deg_s

    min_cycles = int(MULTICICLO["MIN_CYCLES"])
    max_cycles = int(MULTICICLO["MAX_CYCLES"])
    closure_tol = float(MULTICICLO["CLOSURE_TOL_PCT"])
    comp_tol = float(MULTICICLO["COMPOSITION_TOL_PCT"])

    # --------------------------------------------------------
    # Configuración del combustible
    # --------------------------------------------------------
    fuel_species_list = list(fuel_cfg["especies_combustible"])
    fuel_species = fuel_cfg.get(
        "especie_combustible",
        fuel_species_list[0],
    )
    conversion_label = fuel_cfg["nombre"]
    fuel_string = fuel_cfg["fuel"]
    oxidizer = fuel_cfg["oxidizer"]
    phi = float(fuel_cfg["phi"])

    # ========================================================
    # 6. GEOMETRÍA COMÚN
    # ========================================================
    geom, _ = generar_geometria(
        forzar=False,
        generar_graficas=False,
        mostrar_graficas=False,
    )

    theta_geom_deg = geom["angulos_eje_deg"]
    V_geom_m3 = geom["volumen_m3"]
    b_width = float(geom["B_m"])

    # La geometría base comienza en Vmax. El ciclo termoquímico usa
    # un desfase configurable para comenzar en la fase física deseada.
    n_lookup = max(int(round(theta_end / 0.05)) + 1, 21601)
    theta_lookup_deg = np.linspace(0.0, theta_end, n_lookup)
    theta_shift = theta_lookup_deg + geometry_offset

    q = np.mod(theta_shift, theta_end)
    q = np.where(
        np.isclose(q, 0.0, atol=1.0e-12) & (theta_shift > 0.0),
        theta_end,
        q,
    )

    V_lookup = np.interp(q, theta_geom_deg, V_geom_m3)
    theta_lookup_rad = np.deg2rad(theta_lookup_deg)
    dVdtheta_rad_lookup = np.gradient(V_lookup, theta_lookup_rad)
    V_displaced = float(np.max(V_lookup) - np.min(V_lookup))

    def volume_from_angle(theta_deg):
        return float(np.interp(theta_deg, theta_lookup_deg, V_lookup))

    def dVdtheta_rad_from_angle(theta_deg):
        return float(np.interp(theta_deg, theta_lookup_deg, dVdtheta_rad_lookup))

    def cycle_angle_from_time(t):
        total_deg = omega_eje_deg_s * float(t)
        local = np.mod(total_deg, theta_end)

        if total_deg > 0.0 and np.isclose(local, 0.0, atol=1.0e-8):
            return theta_end

        return float(local)

    def chamber_volume_rate(t):
        theta_local = cycle_angle_from_time(t)
        return dVdtheta_rad_from_angle(theta_local) * omega_eje_rad_s

    # ========================================================
    # 7. MECANISMO Y MEZCLA FRESCA
    # ========================================================
    gas_fresh = cargar_solucion(fuel_cfg)

    for sp in fuel_cfg["especies_requeridas"]:
        if sp not in gas_fresh.species_names:
            raise ValueError(
                f"El mecanismo '{fuel_cfg['mecanismo']}' no contiene "
                f"la especie requerida '{sp}'."
            )

    for sp in fuel_species_list:
        if sp not in gas_fresh.species_names:
            raise ValueError(
                f"La especie combustible '{sp}' no existe en "
                f"{fuel_cfg['mecanismo']}."
            )

    gas_fresh.TP = T_intake, P_intake
    gas_fresh.set_equivalence_ratio(phi, fuel=fuel_string, oxidizer=oxidizer)

    fresh_X = gas_fresh.X.copy()
    fresh_Y = gas_fresh.Y.copy()

    species_names = list(gas_fresh.species_names)
    n_species = gas_fresh.n_species
    n_reactions = gas_fresh.n_reactions
    MW = gas_fresh.molecular_weights.copy()
    reaction_equations = gas_fresh.reaction_equations()

    AFR_st = float(
        gas_fresh.stoich_air_fuel_ratio(
            fuel=fuel_string,
            oxidizer=oxidizer,
            basis="mole",
        )
    )
    AFR_fresh = AFR_st / phi

    # Productos quemados de referencia para residuales.
    gas_residual = cargar_solucion(fuel_cfg)
    gas_residual.TP = T_intake, P_intake
    gas_residual.set_equivalence_ratio(phi, fuel_string, oxidizer)
    gas_residual.equilibrate("HP")
    X_burned_eq = gas_residual.X.copy()
    gas_residual.TPX = T_residual, P_residual, X_burned_eq

    print("\n" + "=" * 70)
    print(f"SOLVER QUÍMICO GENERAL — {MOTOR['nombre']}")
    print("=" * 70)
    print(f"Combustible = {fuel_cfg['nombre']} ({', '.join(fuel_species_list)})")
    print(f"Mecanismo = {fuel_cfg['mecanismo']}")
    print(f"Cantera = {ct.__version__}")
    print(f"Especies = {n_species}")
    print(f"Reacciones = {n_reactions}")
    print(f"phi = {phi:.4f}")
    print(f"AFR mezcla fresca = {AFR_fresh:.4f} kg aire/kg combustible")
    print(f"RPM eje = {rpm_eje:.1f}")
    print(f"Chispa = {spark_angle:.2f}°")
    print(f"T objetivo de encendido = {T_ign_target:.2f} K")
    print(
        f"Resolución angular solicitada = {dtheta_output:.3f}° general / "
        f"{dtheta_combustion:.3f}° en combustión"
    )

    # ========================================================
    # 8. REACTOR Y RESERVORIOS
    # ========================================================
    cyl = ct.IdealGasReactor(
        gas_residual,
        energy="on",
        clone=True,
        name=f"camara_{MOTOR_KEY}",
    )
    cyl.volume = volume_from_angle(0.0)

    # Modelo actual: encendido provocado (SI).
    # La química permanece congelada durante admisión y compresión
    # y se habilita exactamente en el ángulo de chispa.
    chemistry_before_spark = bool(
        fuel_cfg.get(
            "chemistry_before_spark",
            ENCENDIDO.get(
                "CHEMISTRY_BEFORE_SPARK",
                True,
            ),
        )
    )

    cyl.chemistry_enabled = chemistry_before_spark

    print(
        "Química antes de chispa = "
        + ("ACTIVA" if chemistry_before_spark else "CONGELADA")
    )

    gas_in = cargar_solucion(fuel_cfg)
    gas_in.TPX = T_intake, P_intake, fresh_X
    inlet = ct.Reservoir(gas_in, clone=True, name="admision")

    gas_out = cargar_solucion(fuel_cfg)
    gas_out.TPX = T_exhaust, P_exhaust, "N2:1"
    outlet = ct.Reservoir(gas_out, clone=True, name="escape")

    gas_wall = cargar_solucion(fuel_cfg)
    gas_wall.TPX = T_wall, P_exhaust, "N2:1"
    wall_reservoir = ct.Reservoir(gas_wall, clone=True, name="pared")

    # ========================================================
    # 9. PUERTOS
    # ========================================================
    inlet_valve = ct.Valve(inlet, cyl)
    inlet_valve.valve_coeff = float(PUERTOS["INLET_VALVE_COEFF"])
    inlet_valve.time_function = lambda t: valve_window(
        cycle_angle_from_time(t),
        CICLO["INTAKE_OPEN_DEG"],
        CICLO["INTAKE_CLOSE_DEG"],
    )

    exhaust_valve = ct.Valve(cyl, outlet)
    exhaust_valve.valve_coeff = float(PUERTOS["EXHAUST_VALVE_COEFF"])
    exhaust_valve.time_function = lambda t: valve_window(
        cycle_angle_from_time(t),
        CICLO["EXHAUST_OPEN_DEG"],
        CICLO["EXHAUST_CLOSE_DEG"],
    )

    # ========================================================
    # 10. PARED MÓVIL + TRANSFERENCIA TÉRMICA
    # ========================================================
    moving_wall = ct.Wall(
        cyl,
        wall_reservoir,
        A=1.0,
        U=0.0,
        velocity=chamber_volume_rate,
        name="pared_movil_geometria",
    )

    h0 = h_wankel_tipo_woschni(cyl.phase.P, cyl.phase.T, rpm_eje)
    A0 = area_mojada_equivalente(cyl.volume, b_width)

    heat_wall = ct.Wall(
        cyl,
        wall_reservoir,
        A=A0,
        U=h0,
        name="pared_transferencia_calor",
    )

    # ========================================================
    # 11. ENCENDIDO EFECTIVO
    # ========================================================
    spark_dt = spark_duration_deg / omega_eje_deg_s

    spark_state = {
        "energy_J": 0.0,
        "t0_s": -1.0,
        "t1_s": -1.0,
        "armed": False,
        "cycle_number": 0,
    }

    def spark_power_in_W(t):
        if not spark_state["armed"]:
            return 0.0

        t0 = spark_state["t0_s"]
        t1 = spark_state["t1_s"]

        if not (t0 <= t <= t1):
            return 0.0

        dt = t1 - t0
        if dt <= 0.0:
            return 0.0

        xi = (t - t0) / dt

        return (
            spark_state["energy_J"]
            * np.pi
            / (2.0 * dt)
            * np.sin(np.pi * xi)
        )

    def spark_heat_flux_wall(t):
        # En ct.Wall el signo positivo va del reactor izquierdo al derecho.
        # Por tanto, para introducir calor al cilindro usamos signo negativo.
        return -spark_power_in_W(t)

    spark_wall = ct.Wall(
        cyl,
        wall_reservoir,
        A=1.0,
        U=0.0,
        Q=spark_heat_flux_wall,
        name="chispa_efectiva",
    )

    # Mantener referencias vivas y explícitas durante toda la función.
    _ = (moving_wall, spark_wall)

    # ========================================================
    # 12. RED DE REACTORES
    # ========================================================
    sim = ct.ReactorNet([cyl])
    sim.rtol = rtol
    sim.atol = atol

    # CVODES controla internamente el error mediante RTOL/ATOL. En lugar de
    # imponer un advance_limit de temperatura (que modifica los tiempos de
    # salida), fijamos un paso interno máximo. Esto mantiene t <-> theta <-> V
    # exactamente sincronizados y sigue obligando a resolver cambios rápidos.
    sim.max_time_step = MAX_INTERNAL_DT_S

    # Inicialización explícita de la red antes de consultar propiedades de
    # dispositivos de flujo (Valve.mass_flow_rate). Cantera 3.2 requiere que
    # la red haya sido inicializada al menos una vez antes de leer estas tasas.
    sim.initialize()

    def actualizar_pared_termica():
        heat_wall.heat_transfer_coeff = h_wankel_tipo_woschni(
            cyl.phase.P,
            cyl.phase.T,
            rpm_eje,
        )
        heat_wall.area = area_mojada_equivalente(cyl.volume, b_width)

    # ========================================================
    # 13. MALLA DE SALIDA
    # ========================================================
    # Malla base del ciclo completo.
    theta_base = np.arange(
        0.0,
        theta_end + 0.5 * dtheta_output,
        dtheta_output,
    )

    # Malla fina alrededor del evento de combustión. No reemplaza la malla
    # base: se fusionan ambas para conservar exactamente el resto del ciclo.
    theta_fine_start = max(0.0, spark_angle - fine_before_spark)
    theta_fine_end = min(
        theta_end,
        float(CICLO["TDC_COMBUSTION_DEG"]) + fine_after_tdc,
    )

    theta_fine = np.arange(
        theta_fine_start,
        theta_fine_end + 0.5 * dtheta_combustion,
        dtheta_combustion,
    )

    # Redondeo únicamente para eliminar duplicados numéricos al fusionar.
    theta = np.unique(
        np.round(
            np.concatenate([theta_base, theta_fine]),
            decimals=10,
        )
    )

    # Garantizar límites exactos.
    if theta[0] != 0.0:
        theta = np.r_[0.0, theta]
    if theta[-1] != theta_end:
        theta = np.r_[theta, theta_end]

    times = theta / omega_eje_deg_s
    n_out = len(theta)

    # ========================================================
    # 14. ARRAYS
    # ========================================================
    T_hist = np.zeros(n_out)
    P_hist = np.zeros(n_out)
    V_hist = np.zeros(n_out)
    mass_hist = np.zeros(n_out)
    rho_hist = np.zeros(n_out)
    u_mass_hist = np.zeros(n_out)
    h_mass_hist = np.zeros(n_out)

    mdot_in_hist = np.zeros(n_out)
    mdot_out_hist = np.zeros(n_out)

    h_coeff_hist = np.zeros(n_out)
    A_wall_hist = np.zeros(n_out)
    qwall_out_hist = np.zeros(n_out)
    spark_power_in_hist = np.zeros(n_out)

    qdot_chem_hist = np.zeros(n_out)
    work_rate_hist = np.zeros(n_out)
    Hin_rate_hist = np.zeros(n_out)
    Hout_rate_hist = np.zeros(n_out)

    X_hist = np.zeros((n_out, n_species))
    Y_hist = np.zeros((n_out, n_species))
    dm_species_chem_dt_hist = np.zeros((n_out, n_species))

    # Mantener la matriz completa reproduce el diagnóstico del modelo previo.
    # Si un mecanismo futuro es demasiado grande, podrá sustituirse por un
    # registrador selectivo sin tocar la física del solver.
    qdot_rxn_hist = np.zeros((n_out, n_reactions))

    # Tiempos/ángulos realmente alcanzados por ReactorNet. Estos arrays
    # son una salvaguarda contra el comportamiento de advance_limits:
    # sim.advance(t_objetivo) puede retornar antes de t_objetivo.
    actual_time_global_hist = np.zeros(n_out)
    actual_theta_deg_hist = np.zeros(n_out)

    stages = []

    # ========================================================
    # 15. REGISTRO DE ESTADO
    # ========================================================
    def record_state(i):
        phase = cyl.phase

        actualizar_pared_termica()

        actual_time_global_hist[i] = float(sim.time)
        # El ángulo local real se reconstruye al finalizar el ciclo a partir
        # de actual_time_global_hist - tiempo_inicial_del_ciclo.
        actual_theta_deg_hist[i] = np.nan

        T_hist[i] = phase.T
        P_hist[i] = phase.P
        V_hist[i] = cyl.volume
        mass_hist[i] = cyl.mass
        rho_hist[i] = phase.density
        u_mass_hist[i] = phase.int_energy_mass
        h_mass_hist[i] = phase.enthalpy_mass
        X_hist[i, :] = phase.X
        Y_hist[i, :] = phase.Y

        mdot_in_hist[i] = max(float(inlet_valve.mass_flow_rate), 0.0)
        mdot_out_hist[i] = max(float(exhaust_valve.mass_flow_rate), 0.0)

        h_coeff_hist[i] = heat_wall.heat_transfer_coeff
        A_wall_hist[i] = heat_wall.area

        # Positivo = calor que sale del gas hacia la pared.
        qwall_out_hist[i] = float(heat_wall.heat_rate)

        # Positivo = aporte efectivo de encendido hacia el gas.
        spark_power_in_hist[i] = spark_power_in_W(sim.time)

        dVdt = chamber_volume_rate(sim.time)
        work_rate_hist[i] = phase.P * dVdt

        Hin_rate_hist[i] = mdot_in_hist[i] * gas_in.enthalpy_mass
        Hout_rate_hist[i] = mdot_out_hist[i] * phase.enthalpy_mass

        if bool(cyl.chemistry_enabled):
            wdot = phase.net_production_rates
            hbar = phase.partial_molar_enthalpies

            qdot_chem_hist[i] = (
                -cyl.volume
                * np.dot(
                    wdot,
                    hbar,
                )
            )

            dm_species_chem_dt_hist[i, :] = (
                cyl.volume
                * wdot
                * MW
            )

            qdot_rxn_hist[i, :] = (
                -cyl.volume
                * phase.net_rates_of_progress
                * phase.delta_enthalpy
            )
        else:
            qdot_chem_hist[i] = 0.0
            dm_species_chem_dt_hist[i, :].fill(0.0)
            qdot_rxn_hist[i, :].fill(0.0)

        stages.append(stage_name(theta[i]))

    # ========================================================
    # 16. MULTICICLO
    # ========================================================
    def limpiar_arrays_ciclo():
        for arr in [
            T_hist,
            P_hist,
            V_hist,
            mass_hist,
            rho_hist,
            u_mass_hist,
            h_mass_hist,
            mdot_in_hist,
            mdot_out_hist,
            h_coeff_hist,
            A_wall_hist,
            qwall_out_hist,
            spark_power_in_hist,
            qdot_chem_hist,
            work_rate_hist,
            Hin_rate_hist,
            Hout_rate_hist,
            X_hist,
            Y_hist,
            dm_species_chem_dt_hist,
            qdot_rxn_hist,
            actual_time_global_hist,
            actual_theta_deg_hist,
        ]:
            arr.fill(0.0)

        stages.clear()

    def avanzar_hasta_tiempo_exacto(t_target, contexto="avance"):
        """
        Avanza ReactorNet exactamente hasta ``t_target``.

        La red usa integración adaptativa de CVODES, RTOL/ATOL y un
        ``max_time_step`` físico. No se aplica ``advance_limit`` a los puntos
        de salida, porque ese mecanismo puede modificar el tiempo alcanzado.
        """
        t_target = float(t_target)

        # Nunca intentamos retroceder el integrador.
        if sim.time > t_target + SYNC_TOL_S:
            error_deg = (float(sim.time) - t_target) * omega_eje_deg_s
            raise RuntimeError(
                f"El integrador ya está después del objetivo durante {contexto}: "
                f"actual={sim.time:.12e} s, objetivo={t_target:.12e} s, "
                f"error={error_deg:+.6e} deg"
            )

        if sim.time < t_target - SYNC_TOL_S:
            t_reached = float(sim.advance(t_target, apply_limit=False))
        else:
            t_reached = float(sim.time)

        error_t = t_reached - t_target
        error_deg = error_t * omega_eje_deg_s

        if abs(error_deg) > SYNC_TOL_DEG:
            raise RuntimeError(
                f"No se alcanzó exactamente el tiempo objetivo durante {contexto}: "
                f"actual={t_reached:.12e} s, objetivo={t_target:.12e} s, "
                f"error={error_deg:+.6e} deg, tolerancia={SYNC_TOL_DEG:.6e} deg"
            )

        return 1

    def preparar_chispa_ciclo(cycle_number, t_spark_global):
        phase = cyl.phase

        gas_target = cargar_solucion(fuel_cfg)
        gas_target.TDY = (
            max(T_ign_target, phase.T),
            phase.density,
            phase.Y,
        )

        du_target = max(
            gas_target.int_energy_mass - phase.int_energy_mass,
            0.0,
        )

        Q_eff = cyl.mass * du_target

        spark_state["energy_J"] = float(Q_eff)
        spark_state["t0_s"] = float(t_spark_global)
        spark_state["t1_s"] = float(t_spark_global + spark_dt)
        spark_state["armed"] = True
        spark_state["cycle_number"] = int(cycle_number)

        # La función térmica de la chispa cambia de forma discontinua en este
        # instante. Reinicializamos CVODES para descartar el historial previo y
        # volvemos a inicializar la red para que FlowDevice/Wall queden listos
        # incluso si el siguiente punto de salida coincide exactamente con la chispa.
        sim.reinitialize()
        sim.initialize()

        return float(Q_eff)

    def ejecutar_un_ciclo(cycle_number):
        limpiar_arrays_ciclo()

        # Cada ciclo vuelve a comenzar con química congelada hasta la chispa.
        cyl.chemistry_enabled = chemistry_before_spark
        sim.reinitialize()
        sim.initialize()

        t_cycle_start = float(sim.time)

        P_start = float(cyl.phase.P)
        T_start = float(cyl.phase.T)
        m_start = float(cyl.mass)
        Y_start = cyl.phase.Y.copy()

        record_state(0)

        t_spark_global = t_cycle_start + spark_angle / omega_eje_deg_s
        spark_prepared = False
        Q_ignition_cycle_J = 0.0

        for i in range(1, n_out):
            theta_prev = theta[i - 1]
            theta_target = theta[i]
            t_target = t_cycle_start + times[i]

            actualizar_pared_termica()

            if (
                not spark_prepared
                and theta_prev < spark_angle <= theta_target
            ):
                if sim.time < t_spark_global:
                    avanzar_hasta_tiempo_exacto(
                        t_spark_global,
                        contexto=f"chispa ciclo {cycle_number}",
                    )

                actualizar_pared_termica()

                Q_ignition_cycle_J = preparar_chispa_ciclo(
                    cycle_number,
                    t_spark_global,
                )

                # Si la química estaba congelada, se habilita aquí.
                # Si ya estaba activa (iso-octano, etanol, CH4, GNV),
                # no se toca el estado del integrador una segunda vez.
                if not bool(cyl.chemistry_enabled):
                    cyl.chemistry_enabled = True
                    sim.reinitialize()
                    sim.initialize()

                spark_prepared = True

            if sim.time < t_target:
                avanzar_hasta_tiempo_exacto(
                    t_target,
                    contexto=f"ciclo {cycle_number}, theta={theta_target:.3f} deg",
                )

            # Garantía adicional: el estado registrado corresponde realmente
            # al tiempo/ángulo nominal solicitado.
            record_state(i)

        P_end = float(cyl.phase.P)
        T_end = float(cyl.phase.T)
        m_end = float(cyl.mass)
        Y_end = cyl.phase.Y.copy()

        closures = {
            "P_pct": closure_percent(P_start, P_end),
            "T_pct": closure_percent(T_start, T_end),
            "mass_pct": closure_percent(m_start, m_end),
            "Y_pct": composition_closure_percent(Y_start, Y_end),
        }

        return Q_ignition_cycle_J, closures

    print("\n" + "=" * 70)
    print("INTEGRACIÓN MULTICICLO — BÚSQUEDA DE RÉGIMEN PERIÓDICO")
    print("=" * 70)

    closure_history = []
    multicyle_converged = False
    Q_ignition_effective_J = 0.0
    final_cycle_number = max_cycles

    for cycle_number in range(1, max_cycles + 1):
        Q_ignition_effective_J, closures = ejecutar_un_ciclo(cycle_number)

        closure_history.append([
            cycle_number,
            closures["P_pct"],
            closures["T_pct"],
            closures["mass_pct"],
            closures["Y_pct"],
            Q_ignition_effective_J,
        ])

        print(
            f"Ciclo {cycle_number:02d}: "
            f"P={closures['P_pct']:8.4f}% | "
            f"T={closures['T_pct']:8.4f}% | "
            f"m={closures['mass_pct']:8.4f}% | "
            f"Y={closures['Y_pct']:8.4f}% | "
            f"Qign={Q_ignition_effective_J:10.5f} J"
        )

        cycle_converged = (
            cycle_number >= min_cycles
            and closures["P_pct"] <= closure_tol
            and closures["T_pct"] <= closure_tol
            and closures["mass_pct"] <= closure_tol
            and closures["Y_pct"] <= comp_tol
        )

        if cycle_converged:
            multicyle_converged = True
            final_cycle_number = cycle_number
            print(
                f"\n[OK] Régimen periódico aproximado alcanzado "
                f"en el ciclo {cycle_number}."
            )
            break

    closure_history = np.asarray(closure_history, dtype=float)

    final_P_closure = float(closure_history[-1, 1])
    final_T_closure = float(closure_history[-1, 2])
    final_mass_closure = float(closure_history[-1, 3])
    final_Y_closure = float(closure_history[-1, 4])

    if not multicyle_converged:
        print(
            f"\n[ADVERTENCIA] No se alcanzó régimen periódico en "
            f"{max_cycles} ciclos. Se guardará el último ciclo."
        )

    # ========================================================
    # 17. VARIABLES DERIVADAS Y CONSISTENCIA TEMPORAL/GEOMÉTRICA
    # ========================================================
    actual_time_local_s = actual_time_global_hist - actual_time_global_hist[0]
    actual_theta_deg_hist[:] = actual_time_local_s * omega_eje_deg_s

    # El último ciclo debe quedar exactamente sobre la malla angular nominal.
    time_sync_error_s = float(np.max(np.abs(actual_time_local_s - times)))
    theta_sync_error_deg = float(np.max(np.abs(actual_theta_deg_hist - theta)))

    V_target_hist = np.asarray([volume_from_angle(th) for th in theta], dtype=float)
    V_error_hist = V_hist - V_target_hist
    V_max_error_m3 = float(np.max(np.abs(V_error_hist)))
    V_rms_error_m3 = float(np.sqrt(np.mean(V_error_hist**2)))

    print("\n" + "=" * 70)
    print("VALIDACIÓN TIEMPO / ÁNGULO / VOLUMEN")
    print("=" * 70)
    print(f"Error máx tiempo = {time_sync_error_s:.6e} s")
    print(f"Error máx ángulo = {theta_sync_error_deg:.6e}°")
    print(f"Error máx volumen = {V_max_error_m3*1.0e6:.6e} cm³")
    print(f"Error RMS volumen = {V_rms_error_m3*1.0e6:.6e} cm³")

    if theta_sync_error_deg > SYNC_TOL_DEG or V_max_error_m3 > 0.05e-6:
        raise RuntimeError(
            "La simulación quedó desincronizada de la geometría. "
            f"Límites: |Δθ|max <= {SYNC_TOL_DEG:.6e} deg y "
            "|ΔV|max <= 0.05 cm³. "
            "No se permite continuar hacia termodinámica/mecánica."
        )

    print("[OK] Estado Cantera sincronizado con la malla angular y V(theta).")

    mass_species_kg = mass_hist[:, None] * Y_hist
    mass_species_mg = mass_species_kg * 1.0e6

    dm_species_chem_dtheta_mg_deg = (
        dm_species_chem_dt_hist * 1.0e6 / omega_eje_deg_s
    )

    dQchem_dtheta_J_deg = qdot_chem_hist / omega_eje_deg_s
    dQwall_dtheta_J_deg = qwall_out_hist / omega_eje_deg_s
    dQspark_dtheta_J_deg = spark_power_in_hist / omega_eje_deg_s

    Qchem_cum_J = cumulative_trapezoid_manual(qdot_chem_hist, actual_time_local_s)
    W_cum_J = cumulative_trapezoid_manual(work_rate_hist, actual_time_local_s)
    Qwall_cum_J = cumulative_trapezoid_manual(qwall_out_hist, actual_time_local_s)
    Qspark_cum_J = cumulative_trapezoid_manual(spark_power_in_hist, actual_time_local_s)
    Hin_cum_J = cumulative_trapezoid_manual(Hin_rate_hist, actual_time_local_s)
    Hout_cum_J = cumulative_trapezoid_manual(Hout_rate_hist, actual_time_local_s)

    # Integrales muestreadas de los FlowDevice (diagnóstico).
    mass_in_cum_kg = cumulative_trapezoid_manual(mdot_in_hist, actual_time_local_s)
    mass_out_cum_kg = cumulative_trapezoid_manual(mdot_out_hist, actual_time_local_s)

    # Trabajo termodinámico robusto a partir del camino P-V realmente guardado.
    W_PdV_state_J = float(np.trapezoid(P_hist, V_hist))

    # Masa admitida/expulsada robusta desde el cambio de masa del reactor.
    dm_state = np.diff(mass_hist)
    theta_mid = 0.5 * (theta[:-1] + theta[1:])
    mask_in_state = (
        (theta_mid >= CICLO["INTAKE_OPEN_DEG"])
        & (theta_mid < CICLO["INTAKE_CLOSE_DEG"])
    )
    mask_out_state = (
        (theta_mid >= CICLO["EXHAUST_OPEN_DEG"])
        & (theta_mid < CICLO["EXHAUST_CLOSE_DEG"])
    )
    MASS_IN_STATE_KG = float(np.sum(np.maximum(dm_state[mask_in_state], 0.0)))
    MASS_OUT_STATE_KG = float(np.sum(np.maximum(-dm_state[mask_out_state], 0.0)))

    # ========================================================
    # 18. CONVERSIÓN ABSOLUTA DEL COMBUSTIBLE
    # ========================================================
    idx_ivc = nearest_index(theta, CICLO["INTAKE_CLOSE_DEG"])
    idx_eo = nearest_index(theta, CICLO["EXPANSION_END_DEG"])

    fuel_indices = [
        species_names.index(sp)
        for sp in fuel_species_list
    ]

    # Conversión global del combustible = desaparición de las especies
    # padre declaradas como combustible reactivo. Para un combustible puro
    # la definición coincide exactamente con la versión anterior. Para GNV
    # suma CH4 + C2H6 + C3H8.
    fuel_parent_mass_kg = np.sum(
        mass_species_kg[:, fuel_indices],
        axis=1,
    )

    m_fuel_ivc = float(fuel_parent_mass_kg[idx_ivc])
    m_fuel_eo = float(fuel_parent_mass_kg[idx_eo])

    fuel_conversion_eo_pct = (
        100.0
        * (m_fuel_ivc - m_fuel_eo)
        / max(m_fuel_ivc, 1.0e-30)
    )

    fuel_conversion_absolute = np.full(n_out, np.nan)

    mask_closed = (
        (theta >= CICLO["INTAKE_CLOSE_DEG"])
        & (theta <= CICLO["EXPANSION_END_DEG"])
    )

    if m_fuel_ivc > 1.0e-30:
        fuel_conversion_absolute[mask_closed] = (
            m_fuel_ivc - fuel_parent_mass_kg[mask_closed]
        ) / m_fuel_ivc

    fuel_conversion_absolute[mask_closed] = np.clip(
        fuel_conversion_absolute[mask_closed],
        0.0,
        1.0,
    )

    # O2, si existe, se guarda como diagnóstico general.
    O2_conversion_absolute = np.full(n_out, np.nan)
    O2_conversion_eo_pct = np.nan

    if "O2" in species_names:
        k_o2 = species_names.index("O2")
        m_o2_ivc = mass_species_kg[idx_ivc, k_o2]
        m_o2_eo = mass_species_kg[idx_eo, k_o2]

        O2_conversion_eo_pct = (
            100.0
            * (m_o2_ivc - m_o2_eo)
            / max(m_o2_ivc, 1.0e-30)
        )

        if m_o2_ivc > 1.0e-30:
            O2_conversion_absolute[mask_closed] = (
                m_o2_ivc - mass_species_kg[mask_closed, k_o2]
            ) / m_o2_ivc
            O2_conversion_absolute[mask_closed] = np.clip(
                O2_conversion_absolute[mask_closed],
                0.0,
                1.0,
            )

    # ========================================================
    # 19. CA10 / CA50 / CA90
    # ========================================================
    mask_after_spark = (
        (theta >= spark_angle)
        & (theta <= CICLO["EXPANSION_END_DEG"])
    )

    theta_burn = theta[mask_after_spark]
    xb_abs = fuel_conversion_absolute[mask_after_spark]

    def angle_at_absolute_conversion(frac):
        valid = np.isfinite(xb_abs)
        if not np.any(valid):
            return np.nan

        th = theta_burn[valid]
        xb = xb_abs[valid]
        reached = np.where(xb >= frac)[0]

        if len(reached) == 0:
            return np.nan

        j = int(reached[0])
        if j == 0:
            return float(th[0])

        x0, x1 = xb[j - 1], xb[j]
        th0, th1 = th[j - 1], th[j]

        if abs(x1 - x0) < 1.0e-14:
            return float(th1)

        return float(th0 + (frac - x0) * (th1 - th0) / (x1 - x0))

    CA10_deg = angle_at_absolute_conversion(0.10)
    CA50_deg = angle_at_absolute_conversion(0.50)
    CA90_deg = angle_at_absolute_conversion(0.90)

    # ========================================================
    # 20. VALIDACIÓN DE PRODUCTOS POR BALANCE ELEMENTAL
    # ========================================================
    #
    # General para combustibles puros y mezclas. Se cuentan los átomos C/H
    # contenidos en las especies padre del combustible al IVC. Así no se
    # necesita escribir una estequiometría distinta para cada combustible.
    #
    product_validation = {}

    n_C_fuel_ivc_kmol = 0.0
    n_H_fuel_ivc_kmol = 0.0

    # No todos los mecanismos contienen los mismos elementos.
    # Ejemplo: h2o2.yaml usa H/O/N y no contiene carbono.
    # Por tanto, nunca se debe pedir n_atoms(..., "C") sin comprobar
    # primero que "C" exista en gas.element_names.
    elementos_disponibles = set(gas_fresh.element_names)

    def n_atoms_seguro(especie, elemento):
        if elemento not in elementos_disponibles:
            return 0.0
        return float(
            gas_fresh.n_atoms(
                especie,
                elemento,
            )
        )

    for sp in fuel_species_list:
        k = species_names.index(sp)
        n_sp_kmol = mass_species_kg[idx_ivc, k] / MW[k]

        n_C_fuel_ivc_kmol += (
            n_sp_kmol
            * n_atoms_seguro(sp, "C")
        )

        n_H_fuel_ivc_kmol += (
            n_sp_kmol
            * n_atoms_seguro(sp, "H")
        )

    theoretical_by_product = {}

    if "CO2" in species_names and n_C_fuel_ivc_kmol > 0.0:
        k_co2 = species_names.index("CO2")
        theoretical_by_product["CO2"] = (
            n_C_fuel_ivc_kmol
            * MW[k_co2]
        )

    if "H2O" in species_names and n_H_fuel_ivc_kmol > 0.0:
        k_h2o = species_names.index("H2O")
        theoretical_by_product["H2O"] = (
            0.5
            * n_H_fuel_ivc_kmol
            * MW[k_h2o]
        )

    for product, theoretical_kg in theoretical_by_product.items():
        k_prod = species_names.index(product)
        m_prod_ivc = mass_species_kg[idx_ivc, k_prod]
        m_prod_eo = mass_species_kg[idx_eo, k_prod]

        formed_kg = max(
            m_prod_eo - m_prod_ivc,
            0.0,
        )

        yield_pct = (
            100.0
            * formed_kg
            / max(theoretical_kg, 1.0e-30)
        )

        product_validation[product] = {
            "formed_kg": float(formed_kg),
            "theoretical_kg": float(theoretical_kg),
            "yield_pct": float(yield_pct),
        }

    # ========================================================
    # 21. REACCIONES DOMINANTES
    # ========================================================
    reaction_abs_energy_J = np.zeros(n_reactions)

    for j in range(n_reactions):
        reaction_abs_energy_J[j] = cumulative_trapezoid_manual(
            np.abs(qdot_rxn_hist[:, j]),
            times,
        )[-1]

    top_n_reactions = min(10, n_reactions)
    top_rxn_idx = np.argsort(reaction_abs_energy_J)[-top_n_reactions:][::-1]

    with open(
        out_chem / "reacciones_dominantes.csv",
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.writer(f)
        writer.writerow([
            "rank",
            "reaction_index_0based",
            "reaction",
            "integrated_abs_energy_J",
        ])
        for rank, j in enumerate(top_rxn_idx, start=1):
            writer.writerow([
                rank,
                int(j),
                reaction_equations[j],
                reaction_abs_energy_J[j],
            ])

    np.savetxt(
        out_chem / "convergencia_multiciclo.csv",
        closure_history,
        delimiter=",",
        header=(
            "cycle,P_closure_pct,T_closure_pct,mass_closure_pct,"
            "composition_closure_pct,Q_ignition_effective_J"
        ),
        comments="",
    )

    # ========================================================
    # 22. ESTADO COMPARTIDO GENERAL
    # ========================================================
    shared_state = {
        "fuel_key": np.asarray([fuel_key]),
        "fuel_name": np.asarray([fuel_cfg["nombre"]]),
        "fuel_species": np.asarray([fuel_species]),
        "conversion_species": np.asarray([conversion_label]),
        "mechanism_name": np.asarray([fuel_cfg["mecanismo"]]),
        "theta_deg": theta,
        "time_s": times,
        "time_actual_local_s": actual_time_local_s,
        "theta_actual_deg": actual_theta_deg_hist,
        "V_m3": V_hist,
        "V_target_m3": V_target_hist,
        "V_error_m3": V_error_hist,
        "P_Pa": P_hist,
        "T_K": T_hist,
        "mass_kg": mass_hist,
        "rho_kg_m3": rho_hist,
        "u_mass_J_kg": u_mass_hist,
        "h_mass_J_kg": h_mass_hist,
        "species_names": np.asarray(species_names, dtype=str),
        "X_matrix": X_hist,
        "Y_matrix": Y_hist,
        "mass_species_mg": mass_species_mg,
        "chem_rate_mg_deg": dm_species_chem_dtheta_mg_deg,
        "qdot_chem_W": qdot_chem_hist,
        "work_rate_W": work_rate_hist,
        "qwall_out_W": qwall_out_hist,
        "spark_power_in_W": spark_power_in_hist,
        "Hin_rate_W": Hin_rate_hist,
        "Hout_rate_W": Hout_rate_hist,
        "h_coeff_W_m2K": h_coeff_hist,
        "A_wall_m2": A_wall_hist,
        "mdot_in_kg_s": mdot_in_hist,
        "mdot_out_kg_s": mdot_out_hist,
        "mass_in_cum_kg": mass_in_cum_kg,
        "mass_out_cum_kg": mass_out_cum_kg,
        "fuel_conversion_absolute": fuel_conversion_absolute,
        "O2_conversion_absolute": O2_conversion_absolute,
        "fuel_conversion_EO_pct": np.asarray([fuel_conversion_eo_pct]),
        "O2_conversion_EO_pct": np.asarray([O2_conversion_eo_pct]),
        "CA10_deg": np.asarray([CA10_deg]),
        "CA50_deg": np.asarray([CA50_deg]),
        "CA90_deg": np.asarray([CA90_deg]),
        "THETA_IVC_DEG": np.asarray([CICLO["INTAKE_CLOSE_DEG"]]),
        "THETA_SPARK_DEG": np.asarray([spark_angle]),
        "THETA_TDC_DEG": np.asarray([CICLO["TDC_COMBUSTION_DEG"]]),
        "THETA_EO_DEG": np.asarray([CICLO["EXPANSION_END_DEG"]]),
        "RPM_EJE": np.asarray([rpm_eje]),
        "OMEGA_EJE_RAD_S": np.asarray([omega_eje_rad_s]),
        "OMEGA_EJE_DEG_S": np.asarray([omega_eje_deg_s]),
        "PHI": np.asarray([phi]),
        "T_WALL_K": np.asarray([T_wall]),
        "Q_IGNITION_EFFECTIVE_J": np.asarray([Q_ignition_effective_J]),
        "V_DISPLACED_m3": np.asarray([V_displaced]),
        "TIME_SYNC_ERROR_S": np.asarray([time_sync_error_s]),
        "THETA_SYNC_ERROR_DEG": np.asarray([theta_sync_error_deg]),
        "V_MAX_ERROR_m3": np.asarray([V_max_error_m3]),
        "V_RMS_ERROR_m3": np.asarray([V_rms_error_m3]),
        "SYNC_TOL_DEG": np.asarray([SYNC_TOL_DEG]),
        "MAX_INTERNAL_DTHETA_DEG": np.asarray([max_internal_dtheta_deg]),
        "W_PdV_STATE_J": np.asarray([W_PdV_state_J]),
        "MASS_IN_STATE_KG": np.asarray([MASS_IN_STATE_KG]),
        "MASS_OUT_STATE_KG": np.asarray([MASS_OUT_STATE_KG]),
        "reaction_top_indices": top_rxn_idx.astype(int),
        "reaction_abs_energy_J": reaction_abs_energy_J,
        "reaction_equations": np.asarray(reaction_equations, dtype=str),
        "MULTICYCLE_CONVERGED": np.asarray([int(multicyle_converged)]),
        "MULTICYCLE_FINAL_CYCLE": np.asarray([final_cycle_number]),
        "MULTICYCLE_P_CLOSURE_PCT": np.asarray([final_P_closure]),
        "MULTICYCLE_T_CLOSURE_PCT": np.asarray([final_T_closure]),
        "MULTICYCLE_MASS_CLOSURE_PCT": np.asarray([final_mass_closure]),
        "MULTICYCLE_Y_CLOSURE_PCT": np.asarray([final_Y_closure]),
        "MULTICYCLE_HISTORY": closure_history,
    }

    # Productos configurados se guardan con nombres genéricos.
    for product, vals in product_validation.items():
        shared_state[f"product_{product}_formed_kg"] = np.asarray([
            vals["formed_kg"]
        ])
        shared_state[f"product_{product}_theoretical_kg"] = np.asarray([
            vals["theoretical_kg"]
        ])
        shared_state[f"product_{product}_yield_pct"] = np.asarray([
            vals["yield_pct"]
        ])

    np.savez(state_file, **shared_state)

    # ========================================================
    # 23. CSV PRINCIPAL
    # ========================================================
    csv_path = out_chem / "quimica_todas_especies.csv"

    headers = [
        "theta_deg",
        "time_s",
        "stage",
        "T_K",
        "P_Pa",
        "V_m3",
        "mass_kg",
        "qdot_chem_W",
        "qwall_out_W",
        "spark_power_in_W",
        "mdot_in_kg_s",
        "mdot_out_kg_s",
    ]
    headers += [f"X_{sp}" for sp in species_names]
    headers += [f"Y_{sp}" for sp in species_names]
    headers += [f"mass_{sp}_mg" for sp in species_names]
    headers += [f"chem_rate_{sp}_mg_deg" for sp in species_names]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for i in range(n_out):
            row = [
                theta[i],
                times[i],
                stages[i],
                T_hist[i],
                P_hist[i],
                V_hist[i],
                mass_hist[i],
                qdot_chem_hist[i],
                qwall_out_hist[i],
                spark_power_in_hist[i],
                mdot_in_hist[i],
                mdot_out_hist[i],
            ]
            row.extend(X_hist[i, :])
            row.extend(Y_hist[i, :])
            row.extend(mass_species_mg[i, :])
            row.extend(dm_species_chem_dtheta_mg_deg[i, :])
            writer.writerow(row)

    # ========================================================
    # 24. RESUMEN JSON
    # ========================================================
    summary = {
        "fuel_key": fuel_key,
        "fuel_name": fuel_cfg["nombre"],
        "fuel_species": fuel_species,
        "mechanism": fuel_cfg["mecanismo"],
        "cantera_version": ct.__version__,
        "n_species": int(n_species),
        "n_reactions": int(n_reactions),
        "phi": phi,
        "AFR_fresh": float(AFR_fresh),
        "RPM_eje": rpm_eje,
        "multicycle_converged": bool(multicyle_converged),
        "final_cycle": int(final_cycle_number),
        "closure_P_pct": final_P_closure,
        "closure_T_pct": final_T_closure,
        "closure_mass_pct": final_mass_closure,
        "closure_Y_pct": final_Y_closure,
        "T_max_K": float(np.max(T_hist)),
        "P_max_kPa": float(np.max(P_hist) / 1000.0),
        "fuel_conversion_EO_pct": float(fuel_conversion_eo_pct),
        "O2_conversion_EO_pct": (
            float(O2_conversion_eo_pct)
            if np.isfinite(O2_conversion_eo_pct)
            else None
        ),
        "CA10_deg": float(CA10_deg) if np.isfinite(CA10_deg) else None,
        "CA50_deg": float(CA50_deg) if np.isfinite(CA50_deg) else None,
        "CA90_deg": float(CA90_deg) if np.isfinite(CA90_deg) else None,
        "Q_ignition_effective_J": float(Q_ignition_effective_J),
        "Qchem_diagnostic_J": float(Qchem_cum_J[-1]),
        "Qwall_J": float(Qwall_cum_J[-1]),
        "W_PdV_J": float(W_cum_J[-1]),
        "mass_in_kg": float(mass_in_cum_kg[-1]),
        "mass_out_kg": float(mass_out_cum_kg[-1]),
        "products": product_validation,
    }

    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # ========================================================
    # 25. GRÁFICAS
    # ========================================================
    if generar_graficas:
        main_species = _species_presentes(
            fuel_cfg.get("especies_principales", []), species_names
        )
        radicals = _species_presentes(
            fuel_cfg.get("radicales", []), species_names
        )
        pollutants = _species_presentes(
            fuel_cfg.get("contaminantes", []), species_names
        )

        # 00 — convergencia multiciclo
        fig, ax = plt.subplots(figsize=(10, 5))
        labels = ["Presión", "Temperatura", "Masa", "Composición"]
        for j, label in enumerate(labels, start=1):
            ax.semilogy(
                closure_history[:, 0],
                np.maximum(closure_history[:, j], 1.0e-12),
                marker="o",
                label=label,
            )
        ax.axhline(
            closure_tol,
            ls="--",
            lw=1.0,
            label=f"Tolerancia P/T/m = {closure_tol:.2f} %",
        )
        ax.set_xlabel("Número de ciclo")
        ax.set_ylabel("Error de cierre [%] — escala log")
        ax.set_title(f"Convergencia multiciclo — {fuel_cfg['nombre']}")
        ax.grid(True, which="both", alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(out_graph / "00_convergencia_multiciclo.png", dpi=220)
        if mostrar_graficas:
            plt.show()
        else:
            plt.close(fig)

        # 01 — volumen / etapas
        fig, ax = plt.subplots(figsize=(11, 5))
        ax.plot(theta, V_hist * 1.0e6, lw=2.2)
        marcar_etapas(ax)
        ax.set_xlabel("Ángulo del eje excéntrico [°]")
        ax.set_ylabel("Volumen [cm³]")
        ax.set_title(f"{MOTOR['nombre']} — Etapas del ciclo")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_graph / "01_etapas_ciclo.png", dpi=220)
        if mostrar_graficas:
            plt.show()
        else:
            plt.close(fig)

        # 02 — especies principales
        if main_species:
            fig, ax = plt.subplots(figsize=(11, 5))
            for sp in main_species:
                k = species_names.index(sp)
                ax.plot(theta, X_hist[:, k], lw=1.9, label=sp)
            marcar_etapas(ax)
            ax.set_xlabel("Ángulo del eje excéntrico [°]")
            ax.set_ylabel("Fracción molar X [-]")
            ax.set_title(f"{fuel_cfg['nombre']}/aire — especies principales")
            ax.grid(True, alpha=0.3)
            ax.legend()
            fig.tight_layout()
            fig.savefig(out_graph / "02_especies_principales.png", dpi=220)
            if mostrar_graficas:
                plt.show()
            else:
                plt.close(fig)

        # 03 — radicales
        if radicals:
            fig, ax = plt.subplots(figsize=(11, 5))
            for sp in radicals:
                k = species_names.index(sp)
                ax.semilogy(
                    theta,
                    np.maximum(X_hist[:, k], X_FLOOR),
                    lw=1.6,
                    label=sp,
                )
            marcar_etapas(ax)
            ax.set_xlabel("Ángulo del eje excéntrico [°]")
            ax.set_ylabel("Fracción molar X [-] — log")
            ax.set_title(f"{fuel_cfg['nombre']}/aire — radicales e intermedios")
            ax.grid(True, which="both", alpha=0.3)
            ax.legend(ncol=2, fontsize=8)
            fig.tight_layout()
            fig.savefig(out_graph / "03_radicales_intermedios.png", dpi=220)
            if mostrar_graficas:
                plt.show()
            else:
                plt.close(fig)

        # 04 — contaminantes
        if pollutants:
            fig, ax = plt.subplots(figsize=(11, 5))
            for sp in pollutants:
                k = species_names.index(sp)
                ax.semilogy(
                    theta,
                    np.maximum(X_hist[:, k], X_FLOOR),
                    lw=1.8,
                    label=sp,
                )
            marcar_etapas(ax)
            ax.set_xlabel("Ángulo del eje excéntrico [°]")
            ax.set_ylabel("Fracción molar X [-] — log")
            ax.set_title(f"{fuel_cfg['nombre']}/aire — contaminantes")
            ax.grid(True, which="both", alpha=0.3)
            ax.legend()
            fig.tight_layout()
            fig.savefig(out_graph / "04_contaminantes.png", dpi=220)
            if mostrar_graficas:
                plt.show()
            else:
                plt.close(fig)

        # 05 — balance de masas de especies principales seleccionadas
        mass_plot_species = _species_presentes(
            [*fuel_species_list, "O2", "CO2", "H2O", "CO"],
            species_names,
        )
        if mass_plot_species:
            fig, ax = plt.subplots(figsize=(11, 5))
            for sp in mass_plot_species:
                k = species_names.index(sp)
                ax.plot(theta, mass_species_mg[:, k], lw=1.9, label=sp)
            marcar_etapas(ax)
            ax.set_xlabel("Ángulo del eje excéntrico [°]")
            ax.set_ylabel("Masa en cámara [mg]")
            ax.set_title("Consumo de reactivos y formación de productos")
            ax.grid(True, alpha=0.3)
            ax.legend()
            fig.tight_layout()
            fig.savefig(out_graph / "05_balance_especies.png", dpi=220)
            if mostrar_graficas:
                plt.show()
            else:
                plt.close(fig)

        # 06 — tasas químicas de especies representativas
        rate_species = _species_presentes(
            [*fuel_species_list, "O2", "CO2", "H2O", "CO", "OH", "CH3"],
            species_names,
        )
        if rate_species:
            fig, ax = plt.subplots(figsize=(11, 5))
            for sp in rate_species:
                k = species_names.index(sp)
                ax.plot(
                    theta,
                    dm_species_chem_dtheta_mg_deg[:, k],
                    lw=1.6,
                    label=sp,
                )
            ax.axhline(0.0, lw=0.8)
            marcar_etapas(ax)
            ax.set_xlabel("Ángulo del eje excéntrico [°]")
            ax.set_ylabel("dm químico/dθ [mg/°]")
            ax.set_title("Velocidad química por especie")
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=8)
            fig.tight_layout()
            fig.savefig(out_graph / "06_tasas_quimicas_especies.png", dpi=220)
            if mostrar_graficas:
                plt.show()
            else:
                plt.close(fig)

        # 07 — conversión absoluta / CA
        fig, ax = plt.subplots(figsize=(11, 5))
        ax.plot(
            theta,
            100.0 * fuel_conversion_absolute,
            lw=2.2,
            label=f"Conversión absoluta {conversion_label}",
        )
        for frac in [10.0, 50.0, 90.0]:
            ax.axhline(frac, ls=":", lw=0.8, alpha=0.55)
        for ang, lab in [
            (spark_angle, "chispa"),
            (CA10_deg, "CA10"),
            (CA50_deg, "CA50"),
            (CA90_deg, "CA90"),
        ]:
            if np.isfinite(ang):
                ax.axvline(ang, ls="--", lw=1.0, label=f"{lab}={ang:.2f}°")
        ax.set_xlim(spark_angle - 20.0, CICLO["EXPANSION_END_DEG"])
        ax.set_ylim(-2.0, 102.0)
        ax.set_xlabel("Ángulo del eje excéntrico [°]")
        ax.set_ylabel("Conversión absoluta [%]")
        ax.set_title(f"Conversión real del combustible — {fuel_cfg['nombre']}")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(out_graph / "07_conversion_absoluta_CA.png", dpi=220)
        if mostrar_graficas:
            plt.show()
        else:
            plt.close(fig)

        # 08 — validación de productos estequiométricos
        if product_validation:
            fig, ax = plt.subplots(figsize=(11, 5))
            for product, vals in product_validation.items():
                k_prod = species_names.index(product)
                m_prod_ivc = mass_species_kg[idx_ivc, k_prod]
                formed_curve = np.full(n_out, np.nan)
                yield_curve = np.full(n_out, np.nan)
                formed_curve[mask_closed] = np.maximum(
                    mass_species_kg[mask_closed, k_prod] - m_prod_ivc,
                    0.0,
                )
                if vals["theoretical_kg"] > 1.0e-30:
                    yield_curve[mask_closed] = (
                        formed_curve[mask_closed] / vals["theoretical_kg"]
                    )
                ax.plot(
                    theta,
                    100.0 * yield_curve,
                    lw=2.0,
                    label=f"{product} formado / teórico",
                )
            ax.axhline(100.0, ls="--", lw=1.0, label="Estequiometría completa")
            ax.set_xlim(CICLO["INTAKE_CLOSE_DEG"], CICLO["EXPANSION_END_DEG"])
            ax.set_ylim(-2.0, 105.0)
            ax.set_xlabel("Ángulo del eje excéntrico [°]")
            ax.set_ylabel("Producto formado / máximo teórico [%]")
            ax.set_title("Validación estequiométrica de productos")
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=8)
            fig.tight_layout()
            fig.savefig(out_graph / "08_validacion_productos.png", dpi=220)
            if mostrar_graficas:
                plt.show()
            else:
                plt.close(fig)

        # 09 — liberación química
        fig, ax = plt.subplots(figsize=(11, 5))
        ax.plot(theta, dQchem_dtheta_J_deg, lw=2.0, label="dQquím/dθ")
        ax.axhline(0.0, lw=0.8)
        marcar_etapas(ax)
        ax.set_xlabel("Ángulo del eje excéntrico [°]")
        ax.set_ylabel("Liberación química [J/°]")
        ax.set_title("Liberación química obtenida de la cinética")
        ax.grid(True, alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(out_graph / "09_liberacion_quimica.png", dpi=220)
        if mostrar_graficas:
            plt.show()
        else:
            plt.close(fig)

        # 10 — transferencias térmicas
        fig, ax = plt.subplots(figsize=(11, 5))
        ax.plot(theta, dQwall_dtheta_J_deg, lw=1.8, label="Q pared saliente")
        ax.plot(theta, dQspark_dtheta_J_deg, lw=1.8, label="Q encendido entrante")
        ax.axhline(0.0, lw=0.8)
        marcar_etapas(ax)
        ax.set_xlabel("Ángulo del eje excéntrico [°]")
        ax.set_ylabel("Energía por grado [J/°]")
        ax.set_title("Transferencias térmicas acopladas")
        ax.grid(True, alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(out_graph / "10_transferencias_termicas.png", dpi=220)
        if mostrar_graficas:
            plt.show()
        else:
            plt.close(fig)

        # 11 — reacciones dominantes
        if n_reactions > 0:
            fig, ax = plt.subplots(figsize=(12, 6))
            for j in top_rxn_idx[:8]:
                ax.plot(
                    theta,
                    qdot_rxn_hist[:, j] / 1000.0,
                    lw=1.4,
                    label=f"R{j+1}: {reaction_equations[j]}",
                )
            ax.axhline(0.0, lw=0.8)
            ax.set_xlim(spark_angle - 20.0, CICLO["EXPANSION_END_DEG"])
            ax.set_xlabel("Ángulo del eje excéntrico [°]")
            ax.set_ylabel("Contribución energética [kW]")
            ax.set_title(f"Reacciones dominantes — {fuel_cfg['nombre']}")
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=7)
            fig.tight_layout()
            fig.savefig(out_graph / "11_reacciones_dominantes.png", dpi=220)
            if mostrar_graficas:
                plt.show()
            else:
                plt.close(fig)

        # 12 — zoom de conversión durante combustión
        zoom_start = max(0.0, spark_angle - 5.0)
        zoom_end = min(
            theta_end,
            max(
                float(CICLO["TDC_COMBUSTION_DEG"]) + 15.0,
                (CA90_deg + 5.0) if np.isfinite(CA90_deg) else spark_angle + 40.0,
            ),
        )

        fig, ax = plt.subplots(figsize=(11, 5))
        ax.plot(
            theta,
            100.0 * fuel_conversion_absolute,
            lw=2.2,
            label=f"Conversión {conversion_label}",
        )
        for frac in [10.0, 50.0, 90.0]:
            ax.axhline(frac, ls=":", lw=0.8, alpha=0.55)
        for ang, lab in [
            (spark_angle, "chispa"),
            (CA10_deg, "CA10"),
            (CA50_deg, "CA50"),
            (CA90_deg, "CA90"),
            (float(CICLO["TDC_COMBUSTION_DEG"]), "Vmin/TDC"),
        ]:
            if np.isfinite(ang):
                ax.axvline(ang, ls="--", lw=1.0, label=f"{lab}={ang:.2f}°")
        ax.set_xlim(zoom_start, zoom_end)
        ax.set_ylim(-2.0, 102.0)
        ax.set_xlabel("Ángulo del eje excéntrico [°]")
        ax.set_ylabel("Conversión absoluta [%]")
        ax.set_title(f"ZOOM de combustión — {fuel_cfg['nombre']}")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(out_graph / "12_zoom_conversion_combustion.png", dpi=220)
        if mostrar_graficas:
            plt.show()
        else:
            plt.close(fig)

        # 13 — zoom de tasas químicas de especies
        if rate_species:
            fig, ax = plt.subplots(figsize=(11, 5))
            for sp in rate_species:
                k = species_names.index(sp)
                ax.plot(
                    theta,
                    dm_species_chem_dtheta_mg_deg[:, k],
                    lw=1.6,
                    label=sp,
                )
            ax.axhline(0.0, lw=0.8)
            ax.axvline(spark_angle, ls="--", lw=1.0, label="chispa")
            ax.axvline(
                float(CICLO["TDC_COMBUSTION_DEG"]),
                ls="--",
                lw=1.0,
                label="Vmin/TDC",
            )
            ax.set_xlim(zoom_start, zoom_end)
            ax.set_xlabel("Ángulo del eje excéntrico [°]")
            ax.set_ylabel("dm químico/dθ [mg/°]")
            ax.set_title(f"ZOOM de tasas químicas — {fuel_cfg['nombre']}")
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=8)
            fig.tight_layout()
            fig.savefig(out_graph / "13_zoom_tasas_quimicas.png", dpi=220)
            if mostrar_graficas:
                plt.show()
            else:
                plt.close(fig)

        # 14 — zoom de liberación química
        fig, ax = plt.subplots(figsize=(11, 5))
        ax.plot(theta, dQchem_dtheta_J_deg, lw=2.0, label="dQquím/dθ")
        ax.axhline(0.0, lw=0.8)
        ax.axvline(spark_angle, ls="--", lw=1.0, label="chispa")
        ax.axvline(
            float(CICLO["TDC_COMBUSTION_DEG"]),
            ls="--",
            lw=1.0,
            label="Vmin/TDC",
        )
        ax.set_xlim(zoom_start, zoom_end)
        ax.set_xlabel("Ángulo del eje excéntrico [°]")
        ax.set_ylabel("Liberación química [J/°]")
        ax.set_title(f"ZOOM de liberación química — {fuel_cfg['nombre']}")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(out_graph / "14_zoom_liberacion_quimica.png", dpi=220)
        if mostrar_graficas:
            plt.show()
        else:
            plt.close(fig)

    # ========================================================
    # 26. REPORTE FINAL
    # ========================================================
    def _ca_text(value):
        return f"{value:.3f}°" if np.isfinite(value) else "NO ALCANZADO"

    print("\n" + "=" * 70)
    print(f"RESULTADOS QUÍMICOS — {fuel_cfg['nombre'].upper()}")
    print("=" * 70)
    print(f"Régimen periódico = {'SI' if multicyle_converged else 'NO'}")
    print(f"Ciclo utilizado = {final_cycle_number}")
    print(f"Cierre P = {final_P_closure:.5f} %")
    print(f"Cierre T = {final_T_closure:.5f} %")
    print(f"Cierre masa = {final_mass_closure:.5f} %")
    print(f"Cierre composición = {final_Y_closure:.5f} %")
    print(f"T máxima = {np.max(T_hist):.2f} K")
    print(f"P máxima = {np.max(P_hist)/1000.0:.2f} kPa")
    print(f"Conversión absoluta {conversion_label} a EO = {fuel_conversion_eo_pct:.3f} %")
    if np.isfinite(O2_conversion_eo_pct):
        print(f"Conversión absoluta O2 a EO = {O2_conversion_eo_pct:.3f} %")
    for product, vals in product_validation.items():
        print(
            f"{product}: formado={vals['formed_kg']*1e6:.6f} mg | "
            f"teórico={vals['theoretical_kg']*1e6:.6f} mg | "
            f"yield={vals['yield_pct']:.3f} %"
        )
    print(f"CA10 = {_ca_text(CA10_deg)}")
    print(f"CA50 = {_ca_text(CA50_deg)}")
    print(f"CA90 = {_ca_text(CA90_deg)}")
    print(f"Energía efectiva de encendido = {Q_ignition_effective_J:.6f} J")
    print(f"Energía química diagnóstica = {Qchem_cum_J[-1]:.6f} J")
    print(f"Calor a pared = {Qwall_cum_J[-1]:.6f} J")
    print(f"Trabajo P dV (integral tasa muestreada) = {W_cum_J[-1]:.6f} J")
    print(f"Trabajo P dV (integral directa P-V) = {W_PdV_state_J:.6f} J")
    print(f"Masa admitida (estado reactor) = {MASS_IN_STATE_KG*1000.0:.6f} g")
    print(f"Masa expulsada (estado reactor) = {MASS_OUT_STATE_KG*1000.0:.6f} g")
    print(f"Masa admitida (mdot muestreado) = {mass_in_cum_kg[-1]*1000.0:.6f} g")
    print(f"Masa expulsada (mdot muestreado) = {mass_out_cum_kg[-1]*1000.0:.6f} g")
    print(f"[OK] Estado compartido: {state_file}")
    print(f"[OK] Resultados químicos: {out_chem}")

    return {
        "fuel_key": fuel_key,
        "fuel_config": fuel_cfg,
        "state_file": state_file,
        "output_dir": out_chem,
        "summary_file": summary_file,
        "multicycle_converged": multicyle_converged,
        "final_cycle": final_cycle_number,
        "fuel_conversion_EO_pct": fuel_conversion_eo_pct,
        "CA10_deg": CA10_deg,
        "CA50_deg": CA50_deg,
        "CA90_deg": CA90_deg,
        "T_max_K": float(np.max(T_hist)),
        "P_max_Pa": float(np.max(P_hist)),
        "W_PdV_J": float(W_cum_J[-1]),
    }
