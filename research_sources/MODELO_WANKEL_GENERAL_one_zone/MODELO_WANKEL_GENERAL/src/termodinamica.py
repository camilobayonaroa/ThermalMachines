# -*- coding: utf-8 -*-
"""
src/termodinamica.py
=====================

Módulo termodinámico general del modelo Wankel.

Lee el estado generado por src/quimica.py:
    resultados/<combustible>/estado_acoplado.npz

y NO vuelve a resolver la química.

Funciones principales:
- reconstrucción de cp, cv, gamma, h y u con Cantera;
- trabajo P-dV directo y mediante tasa;
- trabajo por etapas y pérdidas de bombeo;
- IMEP neta y bruta;
- LHV consistente con el mecanismo;
- eficiencia indicada neta y bruta;
- balance del primer principio para todo el ciclo;
- balance cerrado IVC -> EO, libre de términos de flujo másico;
- almacenamiento de un estado termodinámico común para mecánica.

IMPORTANTE
----------
La tasa química -V*sum(h_k*wdot_k) se conserva únicamente como
DIAGNÓSTICO CINÉTICO. No se suma como calor externo al primer principio,
ya que la energía química ya está incluida en el estado multiespecie de
Cantera.
"""

from pathlib import Path
import json
import numpy as np
import matplotlib.pyplot as plt
import cantera as ct

from configuracion.motor import MOTOR_KEY, MOTOR, CICLO
from configuracion.combustibles import obtener_combustible
from src.mecanismos import cargar_solucion


# ============================================================
# 1. RUTAS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

EPS = 1.0e-30


# ============================================================
# 2. UTILIDADES
# ============================================================

def trapz(y, x):
    """Integral trapezoidal compatible con varias versiones de NumPy."""
    if hasattr(np, "trapezoid"):
        return float(np.trapezoid(y, x))
    return float(np.trapz(y, x))


def cumulative_trapezoid_manual(y, x):
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    out = np.zeros_like(y)
    if len(y) > 1:
        out[1:] = np.cumsum(0.5 * (y[1:] + y[:-1]) * np.diff(x))
    return out


def cumulative_pdv(P, V):
    """Integral acumulada de P dV."""
    P = np.asarray(P, dtype=float)
    V = np.asarray(V, dtype=float)
    out = np.zeros_like(P)
    if len(P) > 1:
        out[1:] = np.cumsum(0.5 * (P[1:] + P[:-1]) * np.diff(V))
    return out


def nearest_index(arr, value):
    return int(np.argmin(np.abs(np.asarray(arr, dtype=float) - float(value))))


def integrar_segmento_tiempo(y, t, i0, i1):
    if i1 <= i0:
        return 0.0
    return trapz(y[i0:i1 + 1], t[i0:i1 + 1])


def integrar_segmento_pdv(P, V, i0, i1):
    if i1 <= i0:
        return 0.0
    return trapz(P[i0:i1 + 1], V[i0:i1 + 1])


def marcar_etapas(ax, ivc, spark, tdc, eo, end):
    for ang in [ivc, spark, tdc, eo]:
        ax.axvline(ang, ls="--", lw=0.8, alpha=0.55)

    ymin, ymax = ax.get_ylim()
    if np.isclose(ymin, ymax):
        ymax = ymin + 1.0
    ytxt = ymin + 0.95 * (ymax - ymin)

    etapas = [
        (0.5 * ivc, "ADMISIÓN"),
        (0.5 * (ivc + spark), "COMPRESIÓN"),
        (0.5 * (spark + eo), "COMB./EXP."),
        (0.5 * (eo + end), "ESCAPE"),
    ]

    for x, txt in etapas:
        ax.text(x, ytxt, txt, ha="center", va="top", fontsize=8)


def calcular_lhv_desde_config(fuel_cfg):
    """
    LHV general a 298.15 K para una corriente de combustible arbitraria.

    Funciona para:
    - combustible puro: H2, CH4, C2H5OH, IC8H18;
    - mezcla multicomponente: GNV surrogate;
    - diluyentes presentes en la corriente de combustible: CO2, N2.

    Base: 1 kmol de la corriente 'fuel' normalizada. Se conserva C/H/O/N y
    se construyen productos de combustión completa CO2/H2O/N2. El LHV se
    expresa por kg de la corriente completa de combustible.
    """
    gas = cargar_solucion(fuel_cfg)

    T0 = 298.15
    P0 = ct.one_atm

    gas.TPX = T0, P0, fuel_cfg["fuel"]

    Xf = gas.X.copy()
    MW_stream = float(gas.mean_molecular_weight)  # kg/kmol corriente

    h0 = (
        gas.standard_enthalpies_RT
        * ct.gas_constant
        * T0
    )

    h_fuel_stream = float(np.dot(Xf, h0))

    def atomos(elemento):
        if elemento not in gas.element_names:
            return 0.0
        total = 0.0
        for k, sp in enumerate(gas.species_names):
            if Xf[k] == 0.0:
                continue
            total += Xf[k] * gas.n_atoms(sp, elemento)
        return float(total)

    nC = atomos("C")
    nH = atomos("H")
    nO = atomos("O")
    nN = atomos("N")

    nu_o2 = nC + nH / 4.0 - nO / 2.0

    if nu_o2 < -1.0e-12:
        raise ValueError(
            "La corriente combustible contiene más oxígeno del compatible "
            "con el cálculo estándar de LHV implementado."
        )

    nu_o2 = max(nu_o2, 0.0)
    nu_co2 = nC
    nu_h2o = nH / 2.0
    nu_n2 = nN / 2.0

    requeridas = ["O2"]
    if nu_co2 > 0.0:
        requeridas.append("CO2")
    if nu_h2o > 0.0:
        requeridas.append("H2O")
    if nu_n2 > 0.0:
        requeridas.append("N2")

    faltan = [sp for sp in requeridas if sp not in gas.species_names]
    if faltan:
        raise ValueError(
            "No se puede calcular LHV. Faltan especies estables en el "
            f"mecanismo: {faltan}"
        )

    h_reactants = h_fuel_stream
    h_reactants += nu_o2 * h0[gas.species_index("O2")]

    h_products = 0.0
    if nu_co2 > 0.0:
        h_products += nu_co2 * h0[gas.species_index("CO2")]
    if nu_h2o > 0.0:
        h_products += nu_h2o * h0[gas.species_index("H2O")]
    if nu_n2 > 0.0:
        h_products += nu_n2 * h0[gas.species_index("N2")]

    delta_h = h_products - h_reactants  # J/kmol corriente combustible
    LHV = -delta_h / MW_stream           # J/kg corriente combustible

    return {
        "LHV_J_kg": float(LHV),
        "nu_O2_kmol_per_kmol_stream": float(nu_o2),
        "nu_CO2_kmol_per_kmol_stream": float(nu_co2),
        "nu_H2O_kmol_per_kmol_stream": float(nu_h2o),
        "MW_stream_kg_kmol": float(MW_stream),
        "X_stream": Xf,
        "species_names": list(gas.species_names),
    }


def masa_equivalente_corriente_combustible(
    mass_kg,
    Y_row,
    species_names,
    fuel_cfg,
    lhv_info,
):
    """
    Reconstruye la masa equivalente de la corriente de combustible a partir
    de las especies padre reactivas.

    Para un combustible puro coincide con m*Y_fuel.
    Para GNV usa CH4+C2H6+C3H8 y la composición molar original de la
    corriente para recuperar la masa total equivalente, incluyendo los
    diluyentes CO2/N2 de esa corriente.
    """
    reactive = list(fuel_cfg["especies_combustible"])
    x_stream = np.asarray(lhv_info["X_stream"], dtype=float)
    stream_names = list(lhv_info["species_names"])

    x_reactive = 0.0
    n_parent_kmol = 0.0

    # Usamos los pesos moleculares del mecanismo reconstruido desde el estado.
    gas = cargar_solucion(fuel_cfg)

    for sp in reactive:
        if sp not in species_names:
            continue

        k_state = list(species_names).index(sp)
        k_stream = stream_names.index(sp)
        x_reactive += float(x_stream[k_stream])

        MW_sp = float(gas.molecular_weights[gas.species_index(sp)])
        m_sp = float(mass_kg * Y_row[k_state])
        n_parent_kmol += m_sp / MW_sp

    if x_reactive <= EPS:
        return 0.0

    n_stream_equiv_kmol = n_parent_kmol / x_reactive

    return float(
        n_stream_equiv_kmol
        * lhv_info["MW_stream_kg_kmol"]
    )


# ============================================================
# 3. API PRINCIPAL
# ============================================================

def ejecutar_termodinamica(
    nombre_combustible="isooctano",
    generar_graficas=True,
    mostrar_graficas=False,
):
    """Ejecuta el postproceso termodinámico del combustible seleccionado."""

    fuel_key = str(nombre_combustible).strip().lower()
    fuel_cfg = obtener_combustible(fuel_key)

    fuel_species_list = list(
        fuel_cfg["especies_combustible"]
    )

    fuel_label = (
        fuel_species_list[0]
        if len(fuel_species_list) == 1
        else " + ".join(fuel_species_list)
    )

    out_root = BASE_DIR / "resultados" / MOTOR_KEY / fuel_key
    out_thermo = out_root / "termodinamica"
    out_graphs = out_thermo / "graficas"
    out_thermo.mkdir(parents=True, exist_ok=True)
    out_graphs.mkdir(parents=True, exist_ok=True)

    state_file = out_root / "estado_acoplado.npz"

    if not state_file.exists():
        raise FileNotFoundError(
            f"No existe {state_file}\n"
            "Ejecuta primero 03_validar_quimica.py."
        )


    data = np.load(state_file, allow_pickle=False)

    # ========================================================
    # 4. ESTADO ACOPLADO
    # ========================================================

    theta = np.asarray(data["theta_deg"], dtype=float)

    # Preferimos el tiempo realmente alcanzado por Cantera.
    if "time_actual_local_s" in data.files:
        time_s = np.asarray(data["time_actual_local_s"], dtype=float)
    else:
        time_s = np.asarray(data["time_s"], dtype=float)

    V = np.asarray(data["V_m3"], dtype=float)
    P = np.asarray(data["P_Pa"], dtype=float)
    T = np.asarray(data["T_K"], dtype=float)
    mass = np.asarray(data["mass_kg"], dtype=float)
    rho = np.asarray(data["rho_kg_m3"], dtype=float)
    u_mass_saved = np.asarray(data["u_mass_J_kg"], dtype=float)
    h_mass_saved = np.asarray(data["h_mass_J_kg"], dtype=float)
    Y = np.asarray(data["Y_matrix"], dtype=float)
    X = np.asarray(data["X_matrix"], dtype=float)
    species_names = data["species_names"].astype(str)

    qdot_chem_W = np.asarray(data["qdot_chem_W"], dtype=float)
    work_rate_W = np.asarray(data["work_rate_W"], dtype=float)
    qwall_out_W = np.asarray(data["qwall_out_W"], dtype=float)
    spark_power_in_W = np.asarray(data["spark_power_in_W"], dtype=float)
    Hin_rate_W = np.asarray(data["Hin_rate_W"], dtype=float)
    Hout_rate_W = np.asarray(data["Hout_rate_W"], dtype=float)
    h_coeff = np.asarray(data["h_coeff_W_m2K"], dtype=float)
    A_wall = np.asarray(data["A_wall_m2"], dtype=float)
    fuel_conversion = np.asarray(data["fuel_conversion_absolute"], dtype=float)

    rpm_eje = float(data["RPM_EJE"][0])
    omega_eje_deg_s = float(data["OMEGA_EJE_DEG_S"][0])
    phi = float(data["PHI"][0])
    T_wall = float(data["T_WALL_K"][0])
    V_displaced = float(data["V_DISPLACED_m3"][0])

    ivc = float(data["THETA_IVC_DEG"][0])
    spark = float(data["THETA_SPARK_DEG"][0])
    tdc = float(data["THETA_TDC_DEG"][0])
    eo = float(data["THETA_EO_DEG"][0])
    end = float(theta[-1])

    CA10 = float(data["CA10_deg"][0])
    CA50 = float(data["CA50_deg"][0])
    CA90 = float(data["CA90_deg"][0])

    multicycle_converged = bool(int(data["MULTICYCLE_CONVERGED"][0]))
    if not multicycle_converged:
        print(
            "[ADVERTENCIA] El estado químico no alcanzó régimen periódico. "
            "Los resultados termodinámicos deben considerarse preliminares."
        )

    # ========================================================
    # 5. RECONSTRUCCIÓN DE PROPIEDADES DE CANTERA
    # ========================================================

    gas = cargar_solucion(fuel_cfg)

    N = len(theta)
    cp_mass = np.zeros(N)
    cv_mass = np.zeros(N)
    gamma = np.zeros(N)
    h_mass = np.zeros(N)
    u_mass_check = np.zeros(N)

    for i in range(N):
        gas.TPY = float(T[i]), float(P[i]), Y[i, :]
        cp_mass[i] = gas.cp_mass
        cv_mass[i] = gas.cv_mass
        gamma[i] = cp_mass[i] / max(cv_mass[i], EPS)
        h_mass[i] = gas.enthalpy_mass
        u_mass_check[i] = gas.int_energy_mass

    max_u_reconstruction_error = float(
        np.max(np.abs(u_mass_check - u_mass_saved))
    )

    max_h_reconstruction_error = float(
        np.max(np.abs(h_mass - h_mass_saved))
    )

    # ========================================================
    # 6. ENERGÍAS ACUMULADAS
    # ========================================================

    U = mass * u_mass_saved
    delta_U = U - U[0]

    W_rate_cum = cumulative_trapezoid_manual(work_rate_W, time_s)
    W_PdV_cum = cumulative_pdv(P, V)
    Qwall_cum = cumulative_trapezoid_manual(qwall_out_W, time_s)
    Qspark_cum = cumulative_trapezoid_manual(spark_power_in_W, time_s)
    Hin_cum = cumulative_trapezoid_manual(Hin_rate_W, time_s)
    Hout_cum = cumulative_trapezoid_manual(Hout_rate_W, time_s)

    # Diagnóstico cinético solamente.
    Qchem_diag_cum = cumulative_trapezoid_manual(qdot_chem_W, time_s)

    energy_rhs_cum = (
        Hin_cum
        - Hout_cum
        + Qspark_cum
        - Qwall_cum
        - W_rate_cum
    )

    energy_residual_full = energy_rhs_cum - delta_U

    # ========================================================
    # 7. ÍNDICES ANGULARES
    # ========================================================

    idx_ivc = nearest_index(theta, ivc)
    idx_spark = nearest_index(theta, spark)
    idx_tdc = nearest_index(theta, tdc)
    idx_eo = nearest_index(theta, eo)

    # ========================================================
    # 8. TRABAJO POR ETAPAS
    # ========================================================

    W_ADMISSION_J = integrar_segmento_pdv(P, V, 0, idx_ivc)
    W_GROSS_CLOSED_J = integrar_segmento_pdv(P, V, idx_ivc, idx_eo)
    W_EXHAUST_J = integrar_segmento_pdv(P, V, idx_eo, N - 1)
    W_PUMPING_J = W_ADMISSION_J + W_EXHAUST_J

    W_NET_PDV_J = float(W_PdV_cum[-1])
    W_NET_RATE_J = float(W_rate_cum[-1])

    W_METHOD_ERROR_J = W_NET_RATE_J - W_NET_PDV_J
    W_METHOD_ERROR_PCT = (
        100.0 * W_METHOD_ERROR_J / W_NET_PDV_J
        if abs(W_NET_PDV_J) > EPS
        else np.nan
    )

    IMEP_NET_PA = W_NET_PDV_J / max(V_displaced, EPS)
    IMEP_GROSS_PA = W_GROSS_CLOSED_J / max(V_displaced, EPS)

    # ========================================================
    # 9. PRIMER PRINCIPIO — TRAMO CERRADO IVC -> EO
    # ========================================================

    delta_U_closed_J = float(U[idx_eo] - U[idx_ivc])

    Qspark_closed_J = integrar_segmento_tiempo(
        spark_power_in_W, time_s, idx_ivc, idx_eo
    )

    Qwall_closed_J = integrar_segmento_tiempo(
        qwall_out_W, time_s, idx_ivc, idx_eo
    )

    W_closed_rate_J = integrar_segmento_tiempo(
        work_rate_W, time_s, idx_ivc, idx_eo
    )

    # Usamos el P-dV directo como referencia termodinámica principal.
    W_closed_pdv_J = W_GROSS_CLOSED_J

    closed_rhs_J = Qspark_closed_J - Qwall_closed_J - W_closed_pdv_J
    closed_energy_residual_J = closed_rhs_J - delta_U_closed_J

    # Curvas acumuladas referidas a IVC para graficar el balance cerrado.
    th_closed = theta[idx_ivc:idx_eo + 1]
    t_closed = time_s[idx_ivc:idx_eo + 1]
    P_closed = P[idx_ivc:idx_eo + 1]
    V_closed = V[idx_ivc:idx_eo + 1]

    U_closed_rel = U[idx_ivc:idx_eo + 1] - U[idx_ivc]
    Qspark_closed_cum = cumulative_trapezoid_manual(
        spark_power_in_W[idx_ivc:idx_eo + 1], t_closed
    )
    Qwall_closed_cum = cumulative_trapezoid_manual(
        qwall_out_W[idx_ivc:idx_eo + 1], t_closed
    )
    W_closed_pdv_cum = cumulative_pdv(P_closed, V_closed)

    rhs_closed_cum = (
        Qspark_closed_cum
        - Qwall_closed_cum
        - W_closed_pdv_cum
    )
    residual_closed_cum = rhs_closed_cum - U_closed_rel

    # ========================================================
    # 10. LHV Y EFICIENCIA INDICADA
    # ========================================================

    lhv_info = calcular_lhv_desde_config(fuel_cfg)
    LHV_J_KG = float(lhv_info["LHV_J_kg"])

    # Masa equivalente de la corriente completa de combustible.
    m_fuel_start_kg = masa_equivalente_corriente_combustible(
        mass[0], Y[0], species_names, fuel_cfg, lhv_info
    )
    m_fuel_ivc_kg = masa_equivalente_corriente_combustible(
        mass[idx_ivc], Y[idx_ivc], species_names, fuel_cfg, lhv_info
    )

    # Para la conversión usamos directamente la desaparición de las especies
    # padre reactivas, válida para combustible puro y para mezclas.
    reactive_indices = [
        list(species_names).index(sp)
        for sp in fuel_cfg["especies_combustible"]
        if sp in species_names
    ]

    m_parent_ivc_kg = float(
        mass[idx_ivc]
        * np.sum(Y[idx_ivc, reactive_indices])
    )
    m_parent_eo_kg = float(
        mass[idx_eo]
        * np.sum(Y[idx_eo, reactive_indices])
    )

    ETA_COMBUSTION = (
        (m_parent_ivc_kg - m_parent_eo_kg) / m_parent_ivc_kg
        if m_parent_ivc_kg > EPS
        else np.nan
    )
    ETA_COMBUSTION = float(np.clip(ETA_COMBUSTION, 0.0, 1.0))

    m_fuel_admitted_kg = max(
        m_fuel_ivc_kg - m_fuel_start_kg,
        0.0,
    )

    # Masa de corriente equivalente cuya fracción reactiva fue consumida.
    m_fuel_consumed_kg = (
        m_fuel_ivc_kg * ETA_COMBUSTION
    )

    m_fuel_eo_kg = max(
        m_fuel_ivc_kg - m_fuel_consumed_kg,
        0.0,
    )

    Q_FUEL_INPUT_J = m_fuel_admitted_kg * LHV_J_KG
    Q_FUEL_TRAPPED_IVC_J = m_fuel_ivc_kg * LHV_J_KG
    Q_FUEL_CONSUMED_J = m_fuel_consumed_kg * LHV_J_KG

    ETA_IND_NET = (
        W_NET_PDV_J / Q_FUEL_INPUT_J
        if Q_FUEL_INPUT_J > EPS
        else np.nan
    )

    ETA_IND_GROSS = (
        W_GROSS_CLOSED_J / Q_FUEL_TRAPPED_IVC_J
        if Q_FUEL_TRAPPED_IVC_J > EPS
        else np.nan
    )


    closed_residual_pct_fuel = (
        100.0 * closed_energy_residual_J / Q_FUEL_TRAPPED_IVC_J
        if Q_FUEL_TRAPPED_IVC_J > EPS
        else np.nan
    )

    full_residual_pct_fuel = (
        100.0 * energy_residual_full[-1] / Q_FUEL_INPUT_J
        if Q_FUEL_INPUT_J > EPS
        else np.nan
    )

    # ========================================================
    # 11. TASAS POR GRADO
    # ========================================================

    dU_dtheta = np.gradient(U, theta)
    dW_dtheta = work_rate_W / omega_eje_deg_s
    dQwall_dtheta = qwall_out_W / omega_eje_deg_s
    dQspark_dtheta = spark_power_in_W / omega_eje_deg_s
    dHin_dtheta = Hin_rate_W / omega_eje_deg_s
    dHout_dtheta = Hout_rate_W / omega_eje_deg_s
    dQchem_dtheta = qdot_chem_W / omega_eje_deg_s

    # ========================================================
    # 12. REPORTE
    # ========================================================

    print()
    print("=" * 76)
    print(f"TERMODINÁMICA GENERAL — {fuel_cfg['nombre'].upper()} / {MOTOR['nombre']}")
    print("=" * 76)
    print(f"Cantera = {ct.__version__}")
    print(f"Mecanismo = {fuel_cfg['mecanismo']}")
    print(f"RPM eje = {rpm_eje:.2f}")
    print(f"phi = {phi:.4f}")
    print(f"IVC = {ivc:.3f}° | Chispa = {spark:.3f}° | TDC = {tdc:.3f}° | EO = {eo:.3f}°")
    print(f"T máxima = {np.max(T):.2f} K")
    print(f"P máxima = {np.max(P)/1000.0:.2f} kPa")
    print(f"gamma min/max = {np.min(gamma):.4f} / {np.max(gamma):.4f}")
    print(f"h pared máximo = {np.max(h_coeff):.2f} W/(m² K)")
    print(f"Área mojada equivalente máxima = {np.max(A_wall):.6f} m²")

    print("\n--- TRABAJO E IMEP ---")
    print(f"Trabajo admisión = {W_ADMISSION_J:+.6f} J")
    print(f"Trabajo bruto IVC->EO = {W_GROSS_CLOSED_J:+.6f} J")
    print(f"Trabajo escape = {W_EXHAUST_J:+.6f} J")
    print(f"Trabajo bombeo = {W_PUMPING_J:+.6f} J")
    print(f"Trabajo neto P-dV = {W_NET_PDV_J:+.6f} J")
    print(f"Trabajo neto por tasa = {W_NET_RATE_J:+.6f} J")
    print(f"Diferencia métodos = {W_METHOD_ERROR_J:+.6e} J ({W_METHOD_ERROR_PCT:+.6e} %)")
    print(f"IMEP neta = {IMEP_NET_PA/1000.0:.3f} kPa")
    print(f"IMEP bruta = {IMEP_GROSS_PA/1000.0:.3f} kPa")

    print("\n--- ENERGÍA DEL COMBUSTIBLE / EFICIENCIA ---")
    print(f"LHV = {LHV_J_KG/1.0e6:.6f} MJ/kg")
    print(f"Combustible al inicio = {m_fuel_start_kg*1.0e6:.6f} mg")
    print(f"Combustible en IVC = {m_fuel_ivc_kg*1.0e6:.6f} mg")
    print(f"Combustible admitido neto = {m_fuel_admitted_kg*1.0e6:.6f} mg")
    print(f"Combustible consumido IVC->EO = {m_fuel_consumed_kg*1.0e6:.6f} mg")
    print(f"Q combustible admitido (LHV) = {Q_FUEL_INPUT_J:.6f} J")
    print(f"Q combustible atrapado en IVC = {Q_FUEL_TRAPPED_IVC_J:.6f} J")
    print(f"Eficiencia combustión = {100.0*ETA_COMBUSTION:.3f} %")
    print(f"Eficiencia indicada NETA = {100.0*ETA_IND_NET:.3f} %")
    print(f"Eficiencia indicada BRUTA = {100.0*ETA_IND_GROSS:.3f} %")

    print("\n--- BALANCE CERRADO IVC -> EO ---")
    print(f"ΔU cerrado = {delta_U_closed_J:+.6f} J")
    print(f"Q chispa cerrado = {Qspark_closed_J:+.6f} J")
    print(f"Q pared cerrado = {Qwall_closed_J:+.6f} J")
    print(f"W P-dV cerrado = {W_closed_pdv_J:+.6f} J")
    print(f"W por tasa cerrado = {W_closed_rate_J:+.6f} J")
    print(f"Residual cerrado = {closed_energy_residual_J:+.6e} J")
    print(f"Residual cerrado / Qfuel = {closed_residual_pct_fuel:+.6e} %")

    print("\n--- BALANCE ABIERTO CICLO COMPLETO ---")
    print(f"ΔU final = {delta_U[-1]:+.6f} J")
    print(f"H entrada integrada = {Hin_cum[-1]:+.6f} J")
    print(f"H salida integrada = {Hout_cum[-1]:+.6f} J")
    print(f"Q chispa total = {Qspark_cum[-1]:+.6f} J")
    print(f"Q pared total = {Qwall_cum[-1]:+.6f} J")
    print(f"Residual energético final = {energy_residual_full[-1]:+.6e} J")
    print(f"Residual ciclo / Qfuel = {full_residual_pct_fuel:+.6e} %")
    print(
        "NOTA: el balance abierto usa tasas de flujo muestreadas. "
        "El balance cerrado IVC->EO es la validación energética principal."
    )

    print("\n--- COMBUSTIÓN ---")
    print(f"CA10 = {CA10:.3f}°" if np.isfinite(CA10) else "CA10 = NO ALCANZADO")
    print(f"CA50 = {CA50:.3f}°" if np.isfinite(CA50) else "CA50 = NO ALCANZADO")
    print(f"CA90 = {CA90:.3f}°" if np.isfinite(CA90) else "CA90 = NO ALCANZADO")
    print(f"Q química integrada (diagnóstico) = {Qchem_diag_cum[-1]:.6f} J")
    print("Q química diagnóstica NO se usa para calcular eficiencia ni el primer principio.")

    print("\n--- RECONSTRUCCIÓN CANTERA ---")
    print(f"Error máx reconstrucción u = {max_u_reconstruction_error:.3e} J/kg")
    print(f"Error máx reconstrucción h = {max_h_reconstruction_error:.3e} J/kg")

    # ========================================================
    # 13. GUARDAR ESTADO TERMODINÁMICO PARA MECÁNICA
    # ========================================================

    thermo_state_file = out_root / "estado_termodinamico.npz"

    np.savez(
        thermo_state_file,
        fuel_key=np.asarray([fuel_key]),
        fuel_name=np.asarray([fuel_cfg["nombre"]]),
        theta_deg=theta,
        time_s=time_s,
        V_m3=V,
        P_Pa=P,
        T_K=T,
        mass_kg=mass,
        U_J=U,
        delta_U_J=delta_U,
        cp_mass_J_kgK=cp_mass,
        cv_mass_J_kgK=cv_mass,
        gamma=gamma,
        h_mass_J_kg=h_mass,
        fuel_conversion_absolute=fuel_conversion,
        W_PdV_cum_J=W_PdV_cum,
        W_rate_cum_J=W_rate_cum,
        Qwall_cum_J=Qwall_cum,
        Qspark_cum_J=Qspark_cum,
        Hin_cum_J=Hin_cum,
        Hout_cum_J=Hout_cum,
        energy_residual_full_J=energy_residual_full,
        closed_theta_deg=th_closed,
        closed_delta_U_J=U_closed_rel,
        closed_Qspark_cum_J=Qspark_closed_cum,
        closed_Qwall_cum_J=Qwall_closed_cum,
        closed_W_PdV_cum_J=W_closed_pdv_cum,
        closed_energy_residual_J=residual_closed_cum,
        W_ADMISSION_J=np.asarray([W_ADMISSION_J]),
        W_GROSS_CLOSED_J=np.asarray([W_GROSS_CLOSED_J]),
        W_EXHAUST_J=np.asarray([W_EXHAUST_J]),
        W_PUMPING_J=np.asarray([W_PUMPING_J]),
        W_NET_PDV_J=np.asarray([W_NET_PDV_J]),
        W_NET_RATE_J=np.asarray([W_NET_RATE_J]),
        W_METHOD_ERROR_PCT=np.asarray([W_METHOD_ERROR_PCT]),
        IMEP_NET_PA=np.asarray([IMEP_NET_PA]),
        IMEP_GROSS_PA=np.asarray([IMEP_GROSS_PA]),
        LHV_J_KG=np.asarray([LHV_J_KG]),
        MASS_FUEL_START_KG=np.asarray([m_fuel_start_kg]),
        MASS_FUEL_IVC_KG=np.asarray([m_fuel_ivc_kg]),
        MASS_FUEL_ADMITTED_KG=np.asarray([m_fuel_admitted_kg]),
        MASS_FUEL_CONSUMED_KG=np.asarray([m_fuel_consumed_kg]),
        Q_FUEL_INPUT_J=np.asarray([Q_FUEL_INPUT_J]),
        Q_FUEL_TRAPPED_IVC_J=np.asarray([Q_FUEL_TRAPPED_IVC_J]),
        Q_FUEL_CONSUMED_J=np.asarray([Q_FUEL_CONSUMED_J]),
        ETA_COMBUSTION=np.asarray([ETA_COMBUSTION]),
        ETA_IND_NET=np.asarray([ETA_IND_NET]),
        ETA_IND_GROSS=np.asarray([ETA_IND_GROSS]),
        CLOSED_ENERGY_RESIDUAL_J=np.asarray([closed_energy_residual_J]),
        CLOSED_RESIDUAL_PCT_FUEL=np.asarray([closed_residual_pct_fuel]),
        FULL_ENERGY_RESIDUAL_J=np.asarray([energy_residual_full[-1]]),
        FULL_RESIDUAL_PCT_FUEL=np.asarray([full_residual_pct_fuel]),
        THETA_IVC_DEG=np.asarray([ivc]),
        THETA_SPARK_DEG=np.asarray([spark]),
        THETA_TDC_DEG=np.asarray([tdc]),
        THETA_EO_DEG=np.asarray([eo]),
        RPM_EJE=np.asarray([rpm_eje]),
        PHI=np.asarray([phi]),
    )

    resumen = {
        "fuel": fuel_key,
        "fuel_name": fuel_cfg["nombre"],
        "rpm_eje": rpm_eje,
        "phi": phi,
        "T_max_K": float(np.max(T)),
        "P_max_kPa": float(np.max(P) / 1000.0),
        "W_net_PdV_J": W_NET_PDV_J,
        "W_gross_closed_J": W_GROSS_CLOSED_J,
        "W_pumping_J": W_PUMPING_J,
        "IMEP_net_kPa": IMEP_NET_PA / 1000.0,
        "IMEP_gross_kPa": IMEP_GROSS_PA / 1000.0,
        "LHV_MJ_kg": LHV_J_KG / 1.0e6,
        "fuel_admitted_mg": m_fuel_admitted_kg * 1.0e6,
        "fuel_consumed_mg": m_fuel_consumed_kg * 1.0e6,
        "eta_combustion_pct": 100.0 * ETA_COMBUSTION,
        "eta_ind_net_pct": 100.0 * ETA_IND_NET,
        "eta_ind_gross_pct": 100.0 * ETA_IND_GROSS,
        "closed_energy_residual_J": closed_energy_residual_J,
        "closed_residual_pct_fuel": closed_residual_pct_fuel,
        "full_energy_residual_J": float(energy_residual_full[-1]),
        "full_residual_pct_fuel": full_residual_pct_fuel,
        "CA10_deg": CA10,
        "CA50_deg": CA50,
        "CA90_deg": CA90,
    }

    with open(out_thermo / "resumen_termodinamica.json", "w", encoding="utf-8") as f:
        json.dump(resumen, f, indent=2, ensure_ascii=False)

    # ========================================================
    # 14. GRÁFICAS
    # ========================================================

    if generar_graficas:
        # 01 Temperatura
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(theta, T, lw=2.1)
        ax.axhline(T_wall, ls=":", lw=1.2, label=f"T pared={T_wall:.0f} K")
        marcar_etapas(ax, ivc, spark, tdc, eo, end)
        ax.set_xlabel("Ángulo del eje excéntrico [°]")
        ax.set_ylabel("Temperatura [K]")
        ax.set_title(f"Temperatura del ciclo — {fuel_cfg['nombre']}")
        ax.grid(True, alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(out_graphs / "01_temperatura_vs_theta.png", dpi=220)
        plt.show() if mostrar_graficas else plt.close(fig)

        # 02 Presión
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(theta, P / 1000.0, lw=2.1)
        marcar_etapas(ax, ivc, spark, tdc, eo, end)
        ax.set_xlabel("Ángulo del eje excéntrico [°]")
        ax.set_ylabel("Presión [kPa]")
        ax.set_title(f"Presión del ciclo — {fuel_cfg['nombre']}")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_graphs / "02_presion_vs_theta.png", dpi=220)
        plt.show() if mostrar_graficas else plt.close(fig)

        # 03 P-V
        fig, ax = plt.subplots(figsize=(7.5, 6))
        ax.plot(V * 1.0e6, P / 1000.0, lw=2.0)
        for idx, label in [
            (idx_ivc, "IVC"),
            (idx_spark, "Chispa"),
            (idx_tdc, "Vmin/TDC eq."),
            (idx_eo, "EO"),
        ]:
            ax.scatter([V[idx] * 1.0e6], [P[idx] / 1000.0], s=35, label=label)
        ax.set_xlabel("Volumen [cm³]")
        ax.set_ylabel("Presión [kPa]")
        ax.set_title("Diagrama P-V del reactor 0-D")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(out_graphs / "03_diagrama_PV.png", dpi=220)
        plt.show() if mostrar_graficas else plt.close(fig)

        # 04 Avance combustión
        fig, ax = plt.subplots(figsize=(10, 5))
        if np.any(np.isfinite(fuel_conversion)):
            ax.plot(theta, 100.0 * fuel_conversion, lw=2.2, label=f"{fuel_label} consumido")
        for ang, lab in [(spark, "Chispa"), (CA10, "CA10"), (CA50, "CA50"), (CA90, "CA90")]:
            if np.isfinite(ang):
                ax.axvline(ang, ls="--", lw=1.0, label=f"{lab}={ang:.2f}°")
        ax.set_xlim(spark - 20.0, eo)
        ax.set_ylim(-5.0, 105.0)
        ax.set_xlabel("Ángulo del eje excéntrico [°]")
        ax.set_ylabel(f"{fuel_label} consumido [%]")
        ax.set_title("Avance angular de combustión — modelo 0-D homogéneo")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(out_graphs / "04_avance_combustion.png", dpi=220)
        plt.show() if mostrar_graficas else plt.close(fig)

        # 05 gamma
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(theta, gamma, lw=2.0, label="γ=cp/cv")
        marcar_etapas(ax, ivc, spark, tdc, eo, end)
        ax.set_xlabel("Ángulo del eje excéntrico [°]")
        ax.set_ylabel("γ [-]")
        ax.set_title("Relación de calores específicos variable")
        ax.grid(True, alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(out_graphs / "05_gamma_variable.png", dpi=220)
        plt.show() if mostrar_graficas else plt.close(fig)

        # 06 entalpía
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(theta, h_mass / 1000.0, lw=2.0)
        marcar_etapas(ax, ivc, spark, tdc, eo, end)
        ax.set_xlabel("Ángulo del eje excéntrico [°]")
        ax.set_ylabel("Entalpía específica [kJ/kg]")
        ax.set_title("Entalpía específica de la mezcla")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_graphs / "06_entalpia_vs_theta.png", dpi=220)
        plt.show() if mostrar_graficas else plt.close(fig)

        # 07 h transferencia
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(theta, h_coeff, lw=2.0)
        marcar_etapas(ax, ivc, spark, tdc, eo, end)
        ax.set_xlabel("Ángulo del eje excéntrico [°]")
        ax.set_ylabel("h [W/(m² K)]")
        ax.set_title("Coeficiente de transferencia de calor acoplado")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_graphs / "07_h_vs_theta.png", dpi=220)
        plt.show() if mostrar_graficas else plt.close(fig)

        # 08 tasas térmicas
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(theta, qwall_out_W / 1000.0, lw=2.0, label="Calor hacia pared")
        ax.plot(theta, spark_power_in_W / 1000.0, lw=1.7, label="Encendido hacia gas")
        ax.axhline(0.0, lw=0.8)
        marcar_etapas(ax, ivc, spark, tdc, eo, end)
        ax.set_xlabel("Ángulo del eje excéntrico [°]")
        ax.set_ylabel("Potencia térmica [kW]")
        ax.set_title("Tasas térmicas realmente aplicadas en Cantera")
        ax.grid(True, alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(out_graphs / "08_tasas_transferencia_calor.png", dpi=220)
        plt.show() if mostrar_graficas else plt.close(fig)

        # 09 liberación química diagnóstica
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(theta, dQchem_dtheta, lw=2.0)
        ax.axhline(0.0, lw=0.8)
        marcar_etapas(ax, ivc, spark, tdc, eo, end)
        ax.set_xlabel("Ángulo del eje excéntrico [°]")
        ax.set_ylabel("Diagnóstico químico [J/°]")
        ax.set_title("Tasa química diagnóstica — NO equivale al LHV")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_graphs / "09_liberacion_quimica_diagnostica.png", dpi=220)
        plt.show() if mostrar_graficas else plt.close(fig)

        # 10 qchem acumulada diagnóstico
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(theta, Qchem_diag_cum, lw=2.0)
        marcar_etapas(ax, ivc, spark, tdc, eo, end)
        ax.set_xlabel("Ángulo del eje excéntrico [°]")
        ax.set_ylabel("Integral diagnóstica [J]")
        ax.set_title("Integral de tasa química — diagnóstico cinético")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_graphs / "10_quimica_diagnostica_acumulada.png", dpi=220)
        plt.show() if mostrar_graficas else plt.close(fig)

        # 11 tasas primer principio
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(theta, dU_dtheta, lw=1.8, label="dU/dθ")
        ax.plot(theta, dHin_dtheta, lw=1.5, label="H entrada")
        ax.plot(theta, -dHout_dtheta, lw=1.5, label="-H salida")
        ax.plot(theta, dQspark_dtheta, lw=1.5, label="Q encendido")
        ax.plot(theta, -dQwall_dtheta, lw=1.5, label="-Q pared")
        ax.plot(theta, -dW_dtheta, lw=1.5, label="-P dV")
        marcar_etapas(ax, ivc, spark, tdc, eo, end)
        ax.set_xlabel("Ángulo del eje excéntrico [°]")
        ax.set_ylabel("Energía por grado [J/°]")
        ax.set_title("Primer principio — términos del volumen de control")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(out_graphs / "11_tasas_primer_principio.png", dpi=220)
        plt.show() if mostrar_graficas else plt.close(fig)

        # 12 balance acumulado abierto
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(theta, delta_U, lw=2.0, label="ΔU")
        ax.plot(theta, Hin_cum, lw=1.5, label="H entrada")
        ax.plot(theta, -Hout_cum, lw=1.5, label="-H salida")
        ax.plot(theta, Qspark_cum, lw=1.5, label="Q encendido")
        ax.plot(theta, -Qwall_cum, lw=1.5, label="-Q pared")
        ax.plot(theta, -W_rate_cum, lw=1.5, label="-Trabajo P dV")
        marcar_etapas(ax, ivc, spark, tdc, eo, end)
        ax.set_xlabel("Ángulo del eje excéntrico [°]")
        ax.set_ylabel("Energía acumulada [J]")
        ax.set_title("Balance acumulado — ciclo abierto completo")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(out_graphs / "12_balance_acumulado_abierto.png", dpi=220)
        plt.show() if mostrar_graficas else plt.close(fig)

        # 13 residual abierto
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(theta, energy_residual_full, lw=2.0)
        ax.axhline(0.0, ls="--", lw=1.0)
        marcar_etapas(ax, ivc, spark, tdc, eo, end)
        ax.set_xlabel("Ángulo del eje excéntrico [°]")
        ax.set_ylabel("Residual [J]")
        ax.set_title("Residual energético — ciclo abierto (diagnóstico)")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_graphs / "13_residual_energetico_abierto.png", dpi=220)
        plt.show() if mostrar_graficas else plt.close(fig)

        # 14 trabajo acumulado directo
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(theta, W_PdV_cum, lw=2.0, label="∫P dV directo")
        ax.plot(theta, W_rate_cum, ls="--", lw=1.5, label="∫P(dV/dt)dt")
        marcar_etapas(ax, ivc, spark, tdc, eo, end)
        ax.set_xlabel("Ángulo del eje excéntrico [°]")
        ax.set_ylabel("Trabajo acumulado [J]")
        ax.set_title("Trabajo indicado acumulado de una cámara")
        ax.grid(True, alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(out_graphs / "14_trabajo_indicado_acumulado.png", dpi=220)
        plt.show() if mostrar_graficas else plt.close(fig)

        # 15 balance cerrado principal
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(th_closed, U_closed_rel, lw=2.1, label="ΔU desde IVC")
        ax.plot(th_closed, Qspark_closed_cum, lw=1.6, label="Q chispa")
        ax.plot(th_closed, -Qwall_closed_cum, lw=1.6, label="-Q pared")
        ax.plot(th_closed, -W_closed_pdv_cum, lw=1.6, label="-∫P dV")
        ax.plot(th_closed, rhs_closed_cum, ls="--", lw=2.0, label="RHS primer principio")
        ax.set_xlabel("Ángulo del eje excéntrico [°]")
        ax.set_ylabel("Energía acumulada desde IVC [J]")
        ax.set_title("Validación principal — primer principio IVC → EO")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(out_graphs / "15_balance_cerrado_IVC_EO.png", dpi=220)
        plt.show() if mostrar_graficas else plt.close(fig)

        # 16 residual cerrado
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(th_closed, residual_closed_cum, lw=2.0)
        ax.axhline(0.0, ls="--", lw=1.0)
        ax.set_xlabel("Ángulo del eje excéntrico [°]")
        ax.set_ylabel("Residual [J]")
        ax.set_title("Residual energético principal — tramo cerrado IVC → EO")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_graphs / "16_residual_cerrado_IVC_EO.png", dpi=220)
        plt.show() if mostrar_graficas else plt.close(fig)

    print(f"\n[OK] Estado termodinámico: {thermo_state_file.resolve()}")
    print(f"[OK] Resultados termodinámicos: {out_thermo.resolve()}")

    return {
        "fuel_key": fuel_key,
        "state_file": thermo_state_file,
        "out_dir": out_thermo,
        "W_net_J": W_NET_PDV_J,
        "W_gross_closed_J": W_GROSS_CLOSED_J,
        "W_pumping_J": W_PUMPING_J,
        "IMEP_net_Pa": IMEP_NET_PA,
        "IMEP_gross_Pa": IMEP_GROSS_PA,
        "LHV_J_kg": LHV_J_KG,
        "Q_fuel_input_J": Q_FUEL_INPUT_J,
        "eta_ind_net": ETA_IND_NET,
        "eta_ind_gross": ETA_IND_GROSS,
        "eta_combustion": ETA_COMBUSTION,
        "closed_energy_residual_J": closed_energy_residual_J,
        "closed_residual_pct_fuel": closed_residual_pct_fuel,
        "full_energy_residual_J": float(energy_residual_full[-1]),
        "full_residual_pct_fuel": full_residual_pct_fuel,
        "work_method_error_pct": W_METHOD_ERROR_PCT,
        "CA10_deg": CA10,
        "CA50_deg": CA50,
        "CA90_deg": CA90,
    }
