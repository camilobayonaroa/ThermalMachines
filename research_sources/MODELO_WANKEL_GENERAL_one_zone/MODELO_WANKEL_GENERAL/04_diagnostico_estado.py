# -*- coding: utf-8 -*-
"""
04_diagnostico_estado.py
========================

Diagnóstico independiente del estado generado por src/quimica.py.

NO vuelve a ejecutar Cantera multiciclo. Lee estado_acoplado.npz y comprueba:
- consistencia V_reactor(theta) vs geometría común;
- trabajo por etapas mediante integral P dV;
- consistencia trabajo_rate vs integral P dV;
- presiones/temperaturas en ángulos clave;
- balance de masa a partir del ESTADO del reactor;
- combustible atrapado/consumido;
- LHV termoquímico consistente con el mecanismo;
- escala física de energía frente a la integral diagnóstica qdot_chem.

Uso:
    .\\.venv\\Scripts\\python.exe 04_diagnostico_estado.py --fuel isooctano
"""

from pathlib import Path
import argparse
import numpy as np
import cantera as ct

from configuracion.motor import CICLO
from configuracion.combustibles import obtener_combustible


BASE_DIR = Path(__file__).resolve().parent
DIR_GEOM = BASE_DIR / "datos_comunes" / "geometria_13B"


def cumulative_trapezoid_manual(y, x):
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    out = np.zeros_like(y)
    if len(y) > 1:
        out[1:] = np.cumsum(0.5 * (y[1:] + y[:-1]) * np.diff(x))
    return out


def nearest_index(arr, value):
    return int(np.argmin(np.abs(np.asarray(arr, dtype=float) - float(value))))


def integrar_segmento_PdV(theta, P, V, a, b):
    mask = (theta >= a) & (theta <= b)
    if np.count_nonzero(mask) < 2:
        return np.nan
    return float(np.trapezoid(P[mask], V[mask]))


def calcular_lhv_desde_config(mechanism_path, fuel_cfg):
    """
    LHV con H2O(g), a 298.15 K, usando la fórmula elemental de la
    configuración y entalpías estándar del mecanismo.

    Para C_a H_b O_c:
        C_a H_b O_c + (a + b/4 - c/2) O2
          -> a CO2 + b/2 H2O(g)
    """
    formula = fuel_cfg.get("formula", {})
    a = float(formula.get("C", 0.0))
    b = float(formula.get("H", 0.0))
    c = float(formula.get("O", 0.0))

    fuel_sp = fuel_cfg["especie_combustible"]
    nu_o2 = a + b / 4.0 - c / 2.0
    nu_co2 = a
    nu_h2o = b / 2.0

    gas = ct.Solution(str(mechanism_path), transport_model=None)
    requeridas = [fuel_sp, "O2"]
    if nu_co2 > 0:
        requeridas.append("CO2")
    if nu_h2o > 0:
        requeridas.append("H2O")

    faltan = [sp for sp in requeridas if sp not in gas.species_names]
    if faltan:
        raise ValueError(f"No se puede calcular LHV. Faltan especies: {faltan}")

    T0 = 298.15
    gas.TP = T0, ct.one_atm
    h0 = gas.standard_enthalpies_RT * ct.gas_constant * T0  # J/kmol

    k_f = gas.species_index(fuel_sp)
    k_o2 = gas.species_index("O2")

    h_products = 0.0
    if nu_co2 > 0:
        h_products += nu_co2 * h0[gas.species_index("CO2")]
    if nu_h2o > 0:
        h_products += nu_h2o * h0[gas.species_index("H2O")]

    h_reactants = h0[k_f] + nu_o2 * h0[k_o2]
    delta_h = h_products - h_reactants  # J/kmol combustible

    MW_fuel = gas.molecular_weights[k_f]  # kg/kmol
    LHV = -delta_h / MW_fuel

    return float(LHV), float(nu_o2), float(nu_co2), float(nu_h2o)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fuel", default="isooctano")
    args = parser.parse_args()

    fuel_key = args.fuel.strip().lower()
    fuel_cfg = obtener_combustible(fuel_key)

    state_file = BASE_DIR / "resultados" / fuel_key / "estado_acoplado.npz"
    mechanism_path = BASE_DIR / "mecanismos" / fuel_cfg["mecanismo"]

    if not state_file.exists():
        raise FileNotFoundError(
            f"No existe {state_file}\nEjecuta primero 03_validar_quimica.py."
        )

    data = np.load(state_file, allow_pickle=False)

    theta = data["theta_deg"]
    # Preferir el tiempo REAL alcanzado por Cantera cuando esté disponible.
    if "time_actual_local_s" in data.files:
        time_s = data["time_actual_local_s"]
    else:
        time_s = data["time_s"]
    V = data["V_m3"]
    P = data["P_Pa"]
    T = data["T_K"]
    mass = data["mass_kg"]
    Y = data["Y_matrix"]
    species = data["species_names"].astype(str)
    qdot_chem = data["qdot_chem_W"]
    work_rate = data["work_rate_W"]
    mdot_in = data["mdot_in_kg_s"]
    mdot_out = data["mdot_out_kg_s"]

    ivc = float(data["THETA_IVC_DEG"][0])
    spark = float(data["THETA_SPARK_DEG"][0])
    tdc = float(data["THETA_TDC_DEG"][0])
    eo = float(data["THETA_EO_DEG"][0])
    end = float(theta[-1])

    print("\n" + "=" * 76)
    print("DIAGNÓSTICO DEL ESTADO ACOPLADO — MODELO WANKEL GENERAL")
    print("=" * 76)
    print(f"Combustible = {fuel_cfg['nombre']}")
    print(f"Estado      = {state_file}")

    # ------------------------------------------------------------------
    # 1) VALIDACIÓN DEL VOLUMEN DEL REACTOR CONTRA LA GEOMETRÍA
    # ------------------------------------------------------------------
    th_geom = np.rad2deg(np.load(DIR_GEOM / "theta_eje_rad.npy"))
    V_geom = np.load(DIR_GEOM / "volumen_m3.npy")
    offset = float(CICLO["GEOMETRY_PHASE_OFFSET_DEG"])
    cycle_end = float(CICLO["CYCLE_END_DEG"])

    shift = theta + offset
    q = np.mod(shift, cycle_end)
    q = np.where(
        np.isclose(q, 0.0, atol=1e-12) & (shift > 0.0),
        cycle_end,
        q,
    )
    V_target = np.interp(q, th_geom, V_geom)

    V_abs_err = np.abs(V - V_target)
    V_max_err = float(np.max(V_abs_err))
    V_rms_err = float(np.sqrt(np.mean(V_abs_err**2)))

    print("\n" + "-" * 76)
    print("1. VOLUMEN DEL REACTOR VS GEOMETRÍA")
    print("-" * 76)
    print(f"Error máximo V = {V_max_err*1e6:.6f} cm³")
    print(f"Error RMS V    = {V_rms_err*1e6:.6f} cm³")
    print(
        "[OK] Volumen dinámico consistente con V(theta)."
        if V_max_err <= 0.05e-6
        else "[ADVERTENCIA] El volumen del reactor se aparta de la geometría."
    )

    # ------------------------------------------------------------------
    # 2) ESTADOS EN ÁNGULOS CLAVE
    # ------------------------------------------------------------------
    print("\n" + "-" * 76)
    print("2. ESTADOS EN ÁNGULOS CLAVE")
    print("-" * 76)

    for ang, label in [
        (0.0, "Inicio"),
        (ivc, "IVC"),
        (spark, "Chispa"),
        (tdc, "Vmin/TDC eq."),
        (eo, "EO"),
        (end, "Fin ciclo"),
    ]:
        i = nearest_index(theta, ang)
        print(
            f"{label:<13} θ={theta[i]:8.3f}° | "
            f"V={V[i]*1e6:9.3f} cm³ | "
            f"P={P[i]/1000.0:10.3f} kPa | "
            f"T={T[i]:8.2f} K | "
            f"m={mass[i]*1e3:9.6f} g"
        )

    # ------------------------------------------------------------------
    # 3) TRABAJO POR ETAPAS
    # ------------------------------------------------------------------
    W_adm = integrar_segmento_PdV(theta, P, V, 0.0, ivc)
    W_closed = integrar_segmento_PdV(theta, P, V, ivc, eo)
    W_exh = integrar_segmento_PdV(theta, P, V, eo, end)
    W_net_pv = float(np.trapezoid(P, V))
    W_pumping = W_adm + W_exh

    W_rate = float(np.trapezoid(work_rate, time_s))

    print("\n" + "-" * 76)
    print("3. TRABAJO P-dV POR ETAPAS")
    print("-" * 76)
    print(f"Admisión  0 -> IVC       = {W_adm:+12.6f} J")
    print(f"Tramo cerrado IVC -> EO  = {W_closed:+12.6f} J")
    print(f"Escape EO -> 1080        = {W_exh:+12.6f} J")
    print(f"Bombeo admisión+escape   = {W_pumping:+12.6f} J")
    print(f"NETO integral P dV       = {W_net_pv:+12.6f} J")
    print(f"NETO integral P*dV/dt dt = {W_rate:+12.6f} J")
    print(f"Diferencia métodos        = {W_rate-W_net_pv:+12.6e} J")

    if W_closed > 0.0 and W_net_pv < 0.0:
        print(
            "[DIAGNÓSTICO] La combustión produce trabajo positivo en el tramo "
            "cerrado, pero las pérdidas de bombeo lo superan. Revisar puertos."
        )
    elif W_closed <= 0.0:
        print(
            "[ADVERTENCIA] El tramo cerrado tampoco produce trabajo positivo. "
            "Debemos revisar fase presión-volumen/encendido antes de mecánica."
        )
    else:
        print("[OK] El trabajo neto y el tramo cerrado son positivos.")

    # ------------------------------------------------------------------
    # 4) BALANCE DE MASA DESDE EL ESTADO DEL REACTOR
    # ------------------------------------------------------------------
    dm = np.diff(mass)
    th_mid = 0.5 * (theta[:-1] + theta[1:])

    mask_in = (th_mid >= CICLO["INTAKE_OPEN_DEG"]) & (th_mid < ivc)
    mask_out = (th_mid >= eo) & (th_mid < CICLO["EXHAUST_CLOSE_DEG"])

    m_in_state = float(np.sum(np.maximum(dm[mask_in], 0.0)))
    m_out_state = float(np.sum(np.maximum(-dm[mask_out], 0.0)))
    delta_m_cycle = float(mass[-1] - mass[0])

    # Lo que reportaba la integral muestreada de mdot
    m_in_sampled = float(np.trapezoid(mdot_in, time_s))
    m_out_sampled = float(np.trapezoid(mdot_out, time_s))

    print("\n" + "-" * 76)
    print("4. BALANCE DE MASA")
    print("-" * 76)
    print(f"Δm reactor ciclo                = {delta_m_cycle*1e6:+.6f} mg")
    print(f"Masa admitida desde estado      = {m_in_state*1e3:.6f} g")
    print(f"Masa expulsada desde estado     = {m_out_state*1e3:.6f} g")
    print(f"Masa admitida integral mdot     = {m_in_sampled*1e3:.6f} g")
    print(f"Masa expulsada integral mdot    = {m_out_sampled*1e3:.6f} g")
    print(
        f"Cierre por estados in-out-Δm    = "
        f"{(m_in_state-m_out_state-delta_m_cycle)*1e6:+.6f} mg"
    )

    # ------------------------------------------------------------------
    # 5) COMBUSTIBLE Y ESCALA ENERGÉTICA
    # ------------------------------------------------------------------
    fuel_sp = fuel_cfg["especie_combustible"]
    k_f = list(species).index(fuel_sp)
    i_ivc = nearest_index(theta, ivc)
    i_eo = nearest_index(theta, eo)

    m_f_ivc = float(mass[i_ivc] * Y[i_ivc, k_f])
    m_f_eo = float(mass[i_eo] * Y[i_eo, k_f])
    m_f_consumed = max(m_f_ivc - m_f_eo, 0.0)

    LHV, nu_o2, nu_co2, nu_h2o = calcular_lhv_desde_config(
        mechanism_path, fuel_cfg
    )

    Q_LHV_trapped = m_f_ivc * LHV
    Q_LHV_consumed = m_f_consumed * LHV
    Qchem_sampled = float(np.trapezoid(qdot_chem, time_s))

    mask_q_closed = (theta >= ivc) & (theta <= eo)
    Qchem_closed = float(
        np.trapezoid(
            qdot_chem[mask_q_closed],
            time_s[mask_q_closed],
        )
    )

    print("\n" + "-" * 76)
    print("5. ESCALA ENERGÉTICA DEL COMBUSTIBLE")
    print("-" * 76)
    print(
        f"Estequiometría O2 = {nu_o2:.6f} mol O2/mol fuel | "
        f"CO2={nu_co2:.6f} | H2O={nu_h2o:.6f}"
    )
    print(f"LHV desde mecanismo             = {LHV/1e6:.6f} MJ/kg")
    print(f"Combustible presente en IVC     = {m_f_ivc*1e6:.6f} mg")
    print(f"Combustible presente en EO      = {m_f_eo*1e6:.6f} mg")
    print(f"Combustible consumido IVC->EO   = {m_f_consumed*1e6:.6f} mg")
    print(f"Energía LHV atrapada en IVC     = {Q_LHV_trapped:.6f} J")
    print(f"Energía LHV del fuel consumido  = {Q_LHV_consumed:.6f} J")
    print(f"Integral qdot_chem ciclo completo = {Qchem_sampled:.6f} J")
    print(f"Integral qdot_chem IVC->EO         = {Qchem_closed:.6f} J")

    ratio_q = (
        abs(Qchem_closed) / Q_LHV_consumed
        if Q_LHV_consumed > 1e-12
        else np.nan
    )
    print(f"|Qchem_IVC->EO| / Q_LHV            = {ratio_q:.6e}")

    print(
        "NOTA: -V*sum(h_k*wdot_k) es una tasa química diagnóstica a la "
        "temperatura instantánea; no es, por definición, el LHV del combustible."
    )

    if not np.isfinite(ratio_q):
        print("[ADVERTENCIA] No se pudo evaluar la escala de qdot_chem.")
    elif ratio_q > 1.5:
        print(
            "[ADVERTENCIA] qdot_chem no debe usarse cuantitativamente como "
            "'energía liberada'. La malla/resolución y la definición diagnóstica "
            "todavía producen una integral muy distinta del LHV."
        )
    elif ratio_q < 0.5:
        print(
            "[ADVERTENCIA] qdot_chem queda muy por debajo de la escala LHV; "
            "revisar resolución antes de interpretarlo cuantitativamente."
        )
    else:
        print(
            "[OK] qdot_chem está en el mismo orden de magnitud que el LHV; "
            "se mantiene únicamente como diagnóstico cinético."
        )

    print("\n" + "=" * 76)
    print("FIN DEL DIAGNÓSTICO")
    print("=" * 76)
    print(
        "Este archivo no modifica resultados. Solo decide qué corregir antes "
        "de construir termodinámica, torque y potencia."
    )


if __name__ == "__main__":
    main()
