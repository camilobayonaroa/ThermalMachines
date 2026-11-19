# -*- coding: utf-8 -*-
"""
06_validar_mecanica.py
======================

Valida la mecánica Wankel con:
- trabajo virtual;
- dV/dtheta analítico de la geometría;
- trabajo termodinámico directo P-dV;
- comparación histórica;
- torque/potencia del motor completo.
"""

import argparse

from src.mecanica import ejecutar_mecanica


parser = argparse.ArgumentParser()

parser.add_argument(
    "--fuel",
    default="isooctano",
    help="Combustible definido en configuracion/combustibles.py",
)

parser.add_argument(
    "--no-show",
    action="store_true",
    help="Guarda las gráficas sin abrir ventanas.",
)

args = parser.parse_args()


print()
print("=" * 78)
print("VALIDACIÓN DEL MÓDULO MECÁNICO GENERAL — V2")
print("=" * 78)

print(
    f"Combustible solicitado = {args.fuel}"
)


resultado = ejecutar_mecanica(
    nombre_combustible=args.fuel,
    generar_graficas=True,
    mostrar_graficas=not args.no_show,
)


print()
print("-" * 78)
print("COMPROBACIONES AUTOMÁTICAS")
print("-" * 78)


checks = {
    "Trabajo virtual positivo":
        resultado[
            "W_virtual_face_J"
        ] > 0.0,

    "Trabajo P-dV geométrico positivo":
        resultado[
            "W_PdV_geom_face_J"
        ] > 0.0,

    "Torque medio indicado positivo":
        resultado[
            "tau_mean_indicated_Nm"
        ] > 0.0,

    "Potencia indicada positiva":
        resultado[
            "power_indicated_mean_W"
        ] > 0.0,

    "RMSE trabajo virtual / dV-dtheta analítico < 0.1 %":
        100.0
        * resultado[
            "virtual_geom_rmse_rel"
        ]
        < 0.1,

    "Cierre virtual / P-dV geométrico < 0.1 %":
        abs(
            resultado[
                "virtual_pdv_geom_error_pct"
            ]
        )
        < 0.1,

    "Cierre virtual / termodinámica < 0.1 %":
        abs(
            resultado[
                "virtual_thermo_error_pct"
            ]
        )
        < 0.1,
}


for nombre, ok in checks.items():

    print(
        f"{'[OK]' if ok else '[ERROR]'} "
        f"{nombre}"
    )


if not all(checks.values()):
    raise RuntimeError(
        "Una o más validaciones mecánicas fundamentales fallaron."
    )


print()
print("-" * 78)
print("LECTURA DEL RESULTADO")
print("-" * 78)

print(
    "RMSE np.gradient(Vreactor) vs geometría = "
    f"{100.0*resultado['numeric_gradient_rmse_rel']:.3f} %"
)

print(
    "Este valor NO invalida la mecánica: muestra la amplificación "
    "del pequeño error volumétrico al derivar numéricamente."
)

print()

print(
    "Error del método histórico/documento vs termodinámica = "
    f"{resultado['document_old_thermo_error_pct']:+.3f} %"
)

print(
    "El método histórico se conserva únicamente como comparación."
)


print()
print("=" * 78)
print("[OK] MÓDULO MECÁNICO GENERAL VALIDADO")
print("=" * 78)

print(
    f"Trabajo indicado = "
    f"{resultado['W_virtual_face_J']:.6f} J/cara"
)

print(
    f"Torque medio indicado = "
    f"{resultado['tau_mean_indicated_Nm']:.3f} N·m"
)

print(
    f"Torque total min/max = "
    f"{resultado['tau_engine_min_Nm']:+.3f} / "
    f"{resultado['tau_engine_max_Nm']:+.3f} N·m"
)

print(
    f"Potencia indicada media = "
    f"{resultado['power_indicated_mean_W']/1000.0:.3f} kW"
)

print(
    f"Potencia indicada media = "
    f"{resultado['power_indicated_mean_hp']:.3f} hp"
)
