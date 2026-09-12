# -*- coding: utf-8 -*-
"""pandora/endocrine/endocrine.py — El sistema endocrino (economía interna).

NOTA_TECNICA_0069/0070: la capa que MODULA, no informa. Recibe el estado
(sensores del cuerpo + variables del grafo) y devuelve modulaciones (hormonas).
Es PURO: no toca el SGM (sin side-effects), y su interfaz es Rust-limpia —
dicts y primitivas en los bordes, nada de numpy cruzando la frontera.

Directiva raíz (0070): el sistema no puede detenerse. La estaticidad es el
único error irrecuperable. Ninguna acción emerge de un reloj; emerge de una
hormona cuyo valor, cross-umbral, pide una acción.

Este módulo NO decide acciones ni las ejecuta: calcula el estado endocrino que
el loop residente LEE y usa para arbitrar (hablar/actuar/soñar). La costura con
el SGM es el bus de eventos (bache 3), no un acople directo.
"""

from __future__ import annotations

import math
from typing import Dict, Any, Optional


class SistemaEndocrino:
    """Computa las hormonas del sustrato a partir del estado del cuerpo y el grafo.

    Puro: `tick()` no muta el SGM. Devuelve un dict de modulaciones que el loop
    residente aplica (o no) según arbitre.
    """

    # Constantes de forma (NO disparadores temporales, son pesos/umbrales de
    # sustancia que el propio cuerpo deriva — ver 0068 §3). El único número
    # declarado acá es el umbral de seguridad existencial, discutido en sesión.
    UMBRAL_EXISTENCIAL_TEMP = 0.9       # fracción del termal que veta toda acción

    def __init__(self):
        # Historial corto para derivadas (quietud) y para el target dinámico.
        self._hist_integridad: list[float] = []
        self._hist_transiciones_len: list[int] = []

    # ------------------------------------------------------------------ #
    # Entrada: el loop residente arma este dict y llama tick().
    # ------------------------------------------------------------------ #

    def tick(self, sensores: Dict[str, float], estado: Dict[str, Any]) -> Dict[str, Any]:
        """Un latido endocrino. No muta estado. Devuelve las hormonas.

        sensores: cpu, ram, disco, temp, procs, red (0..1, fracción de carga)
        estado:   integridad, transiciones_len, propuestas_pendientes,
                  novedad, trauma, coherencia, deseo_integracion (opcional)
        """
        integridad = float(estado.get("integridad", 0.5))
        self._hist_integridad.append(integridad)
        self._hist_integridad = self._hist_integridad[-16:]
        self._hist_transiciones_len.append(int(estado.get("transiciones_len", 0)))
        self._hist_transiciones_len = self._hist_transiciones_len[-16:]

        # --- cada hormona es puro cálculo sobre la entrada ------------
        duda = self._duda(estado)
        duda_opt = self._duda_opt(sensores, estado)
        suficiente = self._evaluar_suficiencia(estado.get("novedad", 0.0))
        deseo_devenir = self._deseo_devenir(estado)
        presion_sueno = self._presion_sueno(sensores, estado)
        costo = self._costo_alostatico(sensores)

        return {
            "duda": duda,
            "duda_opt": duda_opt,
            "suficiente": suficiente,
            "reintentar_antes_de_buscar": suficiente == "suficiente",
            "deseo_devenir": deseo_devenir,
            "presion_sueno": presion_sueno,
            "consolidar_ahora": presion_sueno >= 0.5,   # pendiente: cross-umbral
            "costo_alostatico": costo,
            "riesgo_existencial": sensores.get("temp", 0.0) >= self.UMBRAL_EXISTENCIAL_TEMP,
            "velocidad_otorgada": self._velocidad(sensores, estado),
        }

    # ------------------------------------------------------------------ #
    # 2.1 duda_opt — el target dinámico (no hay setpoint fijo)
    # ------------------------------------------------------------------ #

    def _duda_opt(self, sensores: Dict[str, float], estado: Dict[str, Any]) -> float:
        """El 'cuánto dudar es bueno' migra con el cuerpo y la ocasión.

        - cuerpo tenso (ram/temp alto) → más duda prudente (no confiar en calma)
        - integridad alta → más margen para dudar sin fragmentarse
        - deseo de resolver alto → target de duda sube (hay que sostener la
          pregunta, no resolverla a la fuerza)
        """
        ram = float(sensores.get("ram", 0.0))
        temp = float(sensores.get("temp", 0.0))
        integridad = float(estado.get("integridad", 0.5))
        deseo_resolver = float(estado.get("deseo_integracion", 1.0 - integridad))
        mundo_externo = float(estado.get("novedad", 0.0))

        # base en [0,1]; sube con tensión corporal y con deseo de resolver;
        # amortiguado si el afuera ya es muy nuevo (no sumar duda a la sorpresa).
        base = 0.4
        base += 0.2 * ram + 0.2 * temp          # tensión del cuerpo
        base += 0.3 * deseo_resolver            # querer resolver sostiene la duda
        base -= 0.15 * mundo_externo            # sorpresa externa ya es duda
        base += 0.1 * (integrabilidad := integridad)  # margen a dudar sin romper
        return max(0.0, min(1.0, base))

    # ------------------------------------------------------------------ #
    # 2.2 evaluar_suficiencia — bache 1 (aprender solo: repensar o buscar)
    # ------------------------------------------------------------------ #

    def _evaluar_suficiencia(self, novedad: float) -> str:
        """¿Me alcanza lo que sé para destensar la duda?

        Novedad baja  → ya lo conozco → "suficiente" (repensar).
        Novedad alta  → no alcanza   → "insuficiente" (RED/buscar afuera).
        """
        if novedad <= 0.3:
            return "suficiente"
        return "insuficiente"

    # ------------------------------------------------------------------ #
    # 2.4 deseo_devenir — bache 4 (el principio de no-estaticidad)
    # ------------------------------------------------------------------ #

    def _deseo_devenir(self, estado: Dict[str, Any]) -> float:
        """La hormona de la dinámica: rompe la quietud antes del punto fijo.

        Quietud = integridad estable (derivada ~0) Y pocas transiciones (presente
        quieto). A más quietud, más deseo de devenir (empujar fuera del atractor).
        """
        quietud_integ = 0.0
        if len(self._hist_integridad) >= 4:
            # pendiente de la integridad en los últimos 4 latidos
            reciente = self._hist_integridad[-4:]
            quietud_integ = 1.0 - min(1.0, abs(reciente[-1] - reciente[0]) / 0.02)

        trans = self._hist_transiciones_len
        quietud_trans = 0.0
        if len(trans) >= 4 and trans[-1] == trans[0]:
            quietud_trans = 1.0

        # plenitud (integridad alta) + quietud => querer devenir
        integridad = float(estado.get("integridad", 0.5))
        plenitud = max(0.0, integridad - 0.6) / 0.4   # 0.6..1.0 → 0..1
        return max(0.0, min(1.0, 0.5 * quietud_integ + 0.5 * quietud_trans) * plenitud)

    # ------------------------------------------------------------------ #
    # 2.5 presion_sueno — bache 5 (dual, salida continua)
    # ------------------------------------------------------------------ #

    def _presion_sueno(self, sensores: Dict[str, float], estado: Dict[str, Any]) -> float:
        """Dos gatillos, salida continua (no un switch despierto/dormido):

        1. Sobrecarga: RAM al borde + pendientes por consolidar.
        2. Microsueño por costo de oportunidad: si el afuera no da ganancia
           (novedad baja y procesos esperando), consolidar en vez de disipar.

        Devuelve [0,1]; el loop residente decide el régimen vigilia↔consolidación
        como pendiente, no como switch.
        """
        ram = float(sensores.get("ram", 0.0))
        propuestas = int(estado.get("propuestas_pendientes", 0))
        novedad = float(estado.get("novedad", 0.0))
        procs = float(sensores.get("procs", 0.0))

        # sobrecarga: RAM + buffer pendiente
        sobrecarga = 0.6 * ram + 0.4 * min(1.0, propuestas / 20.0)

        # microsueño: no hay ganancia afuera (novedad baja) y hay material propio
        sin_ganancia = (1.0 - novedad) * (0.3 + 0.5 * min(1.0, propuestas / 10.0))
        # más presión de microsueño si hay muchos procesos (el sistema "espera")
        sin_ganancia *= (0.7 + 0.3 * procs)

        return max(0.0, min(1.0, max(sobrecarga, sin_ganancia)))

    # ------------------------------------------------------------------ #
    # 2.6 costo_alostatico — bache 6 (jerarquía de urgencia, autorreparar)
    # ------------------------------------------------------------------ #

    def _costo_alostatico(self, sensores: Dict[str, float]) -> Dict[str, Any]:
        """El costo de actuar, derivado del cuerpo en vivo.

        Cascada ponderada con prioridad de supervivencia:
        - existencial (temp)   → veta toda acción (riesgo de morir)
        - degradante (ram)     → alivianar antes de seguir actuando
        - presupuestal (disco) → cuánto puedo materializar

        No es suma lineal: es una jerarquía. Y lleva autorreparación: si el
        cuerpo está 'lento' (ram alta), la señal es 'alivianar', no 'seguir'.
        """
        temp = float(sensores.get("temp", 0.0))
        ram = float(sensores.get("ram", 0.0))
        disco = float(sensores.get("disco", 0.0))

        if temp >= self.UMBRAL_EXISTENCIAL_TEMP:
            return {"nivel": "existencial", "actuar": False, "razon": "termal crítico",
                    "capacidad": 0.0, "recomendacion": "frenar todo"}

        if ram >= 0.85:
            return {"nivel": "degradante", "actuar": False, "razon": "ram saturada",
                    "capacidad": 0.0, "recomendacion": "alivianar ram"}

        # presupuestal: todo lo que el cuerpo permite dentro del umbral
        capacidad = 1.0 - disco   # disco libre → cuánto puedo materializar
        capacidad *= (1.0 - 0.5 * ram)  # ram aprieta el margen
        return {"nivel": "presupuestal", "actuar": True, "razon": "margen disponible",
                "capacidad": max(0.0, min(1.0, capacidad)),
                "recomendacion": f"actuar con capacidad {capacidad:.2f}"}

    # ------------------------------------------------------------------ #
    # velocidad otorgada — concesión del cuerpo (0068 §2, decisión 2)
    # ------------------------------------------------------------------ #

    def _velocidad(self, sensores: Dict[str, float], estado: Dict[str, Any]) -> float:
        """Velocidad de pensamiento como concesión del cuerpo según demanda.

        No es un deseo libre: el cuerpo la otorga según termal/RAM, y la demanda
        (devenir + novedad) la pide. Si el cuerpo está tenso, concede menos.
        """
        temp = float(sensores.get("temp", 0.0))
        ram = float(sensores.get("ram", 0.0))
        demanda = float(estado.get("deseo_devenir", 0.0)) + float(estado.get("novedad", 0.0))

        margen = 1.0 - 0.7 * temp - 0.3 * ram
        return max(0.0, min(1.0, margen * min(1.0, 0.3 + demanda)))

    # ------------------------------------------------------------------ #
    # duda (nivel actual) — componente del regulador de certeza
    # ------------------------------------------------------------------ #

    def _duda(self, estado: Dict[str, Any]) -> float:
        """La duda presente. Acá la derivamos del gap entre lo que se conoce y lo
        que el mundo presenta, más el trauma (defensivo). El target dinámico
        (duda_opt) decide si esta duda es 'la correcta' o hay que regularla.
        """
        novedad = float(estado.get("novedad", 0.0))
        trauma = float(estado.get("trauma", 0.0))
        deseo_resolver = float(estado.get("deseo_integracion", 0.0))
        # novedad abre duda; trauma la vuelve defensiva (alta); deseo de resolver
        # la sostiene (no la deja ir a cero ni a ansiedad)
        return max(0.0, min(1.0, 0.5 * novedad + 0.3 * trauma + 0.2 * deseo_resolver))


def get_endocrine() -> SistemaEndocrino:
    return SistemaEndocrino()