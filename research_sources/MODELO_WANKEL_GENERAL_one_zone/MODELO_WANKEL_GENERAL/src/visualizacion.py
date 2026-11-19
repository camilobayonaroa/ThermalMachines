# -*- coding: utf-8 -*-
"""
src/visualizacion.py
====================

Utilidades gráficas compartidas del modelo Wankel.

Este módulo NO participa en los cálculos de química, termodinámica
ni mecánica. Solo añade referencias visuales de las fases del ciclo
a gráficas cuyo eje horizontal es el ángulo del eje excéntrico.

Se mantiene compatibilidad con llamadas:
    agregar_fases_ciclo(ax)
y:
    agregar_fases_ciclo(ax, mostrar_eventos=False)
"""

from configuracion.motor import CICLO, ENCENDIDO


def agregar_fases_ciclo(
    ax,
    mostrar_eventos=True,
):
    """
    Añade divisiones y etiquetas de las cuatro fases del ciclo 4T.

    Fases:
        0 -> IVC       : admisión
        IVC -> TDC     : compresión
        TDC -> EO      : expansión
        EO -> fin      : escape

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Eje sobre el cual se añaden las referencias.
    mostrar_eventos : bool, optional
        Si True, también marca IVC, chispa, TDC y EO.
        Se conserva para compatibilidad con versiones anteriores.
    """

    theta_start = float(
        CICLO.get(
            "INTAKE_OPEN_DEG",
            0.0,
        )
    )

    theta_ivc = float(
        CICLO["INTAKE_CLOSE_DEG"]
    )

    theta_tdc = float(
        CICLO["TDC_COMBUSTION_DEG"]
    )

    theta_eo = float(
        CICLO.get(
            "EXHAUST_OPEN_DEG",
            CICLO["EXPANSION_END_DEG"],
        )
    )

    theta_end = float(
        CICLO["CYCLE_END_DEG"]
    )

    # Límites principales de las fases.
    for ang in (
        theta_ivc,
        theta_tdc,
        theta_eo,
    ):
        ax.axvline(
            ang,
            ls=":",
            lw=0.8,
            alpha=0.35,
        )

    # Etiquetas en coordenada relativa vertical para no depender
    # de la escala concreta de torque, trabajo, fuerza o potencia.
    fases = (
        (
            0.5 * (theta_start + theta_ivc),
            "ADMISIÓN",
        ),
        (
            0.5 * (theta_ivc + theta_tdc),
            "COMPRESIÓN",
        ),
        (
            0.5 * (theta_tdc + theta_eo),
            "EXPANSIÓN",
        ),
        (
            0.5 * (theta_eo + theta_end),
            "ESCAPE",
        ),
    )

    for x, texto in fases:
        ax.text(
            x,
            0.98,
            texto,
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="top",
            fontsize=7,
            alpha=0.65,
        )

    if mostrar_eventos:
        spark = float(
            ENCENDIDO["SPARK_ANGLE_DEG"]
        )

        eventos = (
            (theta_ivc, "IVC"),
            (spark, "Chispa"),
            (theta_tdc, "TDC"),
            (theta_eo, "EO"),
        )

        for x, etiqueta in eventos:
            ax.axvline(
                x,
                ls="--",
                lw=0.7,
                alpha=0.45,
            )

            ax.text(
                x,
                0.03,
                etiqueta,
                transform=ax.get_xaxis_transform(),
                ha="center",
                va="bottom",
                rotation=90,
                fontsize=6.5,
                alpha=0.65,
            )

    return ax
