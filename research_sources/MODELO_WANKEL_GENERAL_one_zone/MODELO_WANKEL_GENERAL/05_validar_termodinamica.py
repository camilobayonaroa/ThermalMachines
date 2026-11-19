# -*- coding: utf-8 -*-
"""
05_validar_termodinamica.py
===========================

Valida el módulo termodinámico general leyendo el estado químico ya
convergido. No vuelve a ejecutar la química.

Uso:
    .\\.venv\\Scripts\\python.exe 05_validar_termodinamica.py --fuel isooctano
"""

import argparse
import numpy as np

from src.termodinamica import ejecutar_termodinamica


parser = argparse.ArgumentParser()
parser.add_argument("--fuel", default="isooctano")
parser.add_argument(
    "--no-show",
    action="store_true",
    help="Guarda las gráficas sin abrir ventanas.",
)
args = parser.parse_args()


print()
print("=" * 76)
print("VALIDACIÓN DEL MÓDULO TERMODINÁMICO GENERAL")
print("=" * 76)
print(f"Combustible solicitado = {args.fuel}")

resultado = ejecutar_termodinamica(
    nombre_combustible=args.fuel,
    generar_graficas=True,
    mostrar_graficas=not args.no_show,
)


print()
print("-" * 76)
print("COMPROBACIONES AUTOMÁTICAS")
print("-" * 76)

checks_fatal = {
    "Trabajo neto positivo": resultado["W_net_J"] > 0.0,
    "Trabajo bruto cerrado positivo": resultado["W_gross_closed_J"] > 0.0,
    "IMEP neta positiva": resultado["IMEP_net_Pa"] > 0.0,
    "LHV positivo": resultado["LHV_J_kg"] > 0.0,
    "Eficiencia indicada neta finita": np.isfinite(resultado["eta_ind_net"]),
    "Eficiencia indicada neta entre 0 y 100 %": 0.0 < resultado["eta_ind_net"] < 1.0,
    "Cierre trabajo P-dV/tasa < 0.1 %": (
        np.isfinite(resultado["work_method_error_pct"])
        and abs(resultado["work_method_error_pct"]) < 0.1
    ),
}

for nombre, ok in checks_fatal.items():
    print(f"{'[OK]' if ok else '[ERROR]'} {nombre}")

if not all(checks_fatal.values()):
    raise RuntimeError(
        "Una o más comprobaciones termodinámicas fundamentales fallaron."
    )


closed_pct = abs(float(resultado["closed_residual_pct_fuel"]))
full_pct = abs(float(resultado["full_residual_pct_fuel"]))

print()
print("-" * 76)
print("CALIDAD DEL BALANCE ENERGÉTICO")
print("-" * 76)

print(
    f"Residual cerrado / Qfuel = {resultado['closed_residual_pct_fuel']:+.6e} %"
)

if closed_pct <= 1.0:
    print("[OK] Balance cerrado IVC->EO dentro de 1 % de la energía de combustible.")
elif closed_pct <= 5.0:
    print("[ADVERTENCIA] Balance cerrado entre 1 y 5 %. Revisar resolución antes de mecánica.")
else:
    raise RuntimeError(
        "El balance energético del tramo cerrado supera 5 % de Qfuel. "
        "No se debe continuar hacia torque."
    )

print(
    f"Residual ciclo abierto / Qfuel = {resultado['full_residual_pct_fuel']:+.6e} %"
)

if full_pct <= 5.0:
    print("[OK] Balance abierto razonable para las tasas de flujo muestreadas.")
else:
    print(
        "[ADVERTENCIA] El balance abierto tiene mayor residual. "
        "Esto puede deberse al muestreo de los caudales en admisión/escape; "
        "el balance cerrado sigue siendo la validación principal."
    )


print()
print("=" * 76)
print("[OK] MÓDULO TERMODINÁMICO GENERAL VALIDADO")
print("=" * 76)
print(f"Trabajo neto = {resultado['W_net_J']:.6f} J/cara")
print(f"Trabajo bruto cerrado = {resultado['W_gross_closed_J']:.6f} J/cara")
print(f"Trabajo de bombeo = {resultado['W_pumping_J']:.6f} J/cara")
print(f"IMEP neta = {resultado['IMEP_net_Pa']/1000.0:.3f} kPa")
print(f"Eficiencia indicada neta = {100.0*resultado['eta_ind_net']:.3f} %")
print(f"Eficiencia indicada bruta = {100.0*resultado['eta_ind_gross']:.3f} %")
print()
