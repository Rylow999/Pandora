# -*- coding: utf-8 -*-
"""pandora/core/communication_loop.py — El ciclo de comunicación bidireccional.

Orquesta el flujo completo entre Luciano y Pandora:
  1. Percepción del entorno (sentidos, 0066)
  2. Input humano → SemanticEvent (oídos) → SGM
  3. Tick del SGM (existir, esculpir, percibir)
  4. Estado interno → texto (boca, con opacity + inefabilidad)
  5. Acción sobre el entorno (la mano, si Pandora quiere actuar)

Es el cierre de la arquitectura transductor: el LLM traduce en ambas direcciones
sin originar estado mental (ACTA P1). El SGM es la mente; el LLM, el traductor.
"""
from ..transducer.output_transducer import OutputTransducer
from ..transducer.nim_client import NimClient


class CommunicationLoop:
    """Ciclo de comunicación: percibir → escuchar → existir → hablar → actuar."""

    def __init__(self, sgm, parser, output_transducer=None, percepcion=None, mano=None):
        self.sgm = sgm
        self.parser = parser
        self.salida = output_transducer or OutputTransducer(client=NimClient())
        self.percepcion = percepcion
        self.mano = mano
        self.turno = 0

    def percibir(self):
        """Percibe el entorno y lo integra al SGM (si hay sentidos)."""
        if self.percepcion is None:
            return None
        vector, carga, muestra = self.percepcion.percibir()
        self.sgm.integrar_experiencia_entorno(vector, carga)
        return {"carga": carga, "muestra": muestra}

    def escuchar(self, texto_usuario):
        """Traduce el texto humano a SemanticEvent e integra al SGM (los oídos)."""
        parse = self.parser.parse(texto_usuario)
        if parse.success:
            self.sgm._inject_event_to_sgm(parse.event) if hasattr(self.sgm, "_inject_event_to_sgm") else None
        return parse

    def existir(self, ticks=1):
        """El SGM procesa (existe) por N ticks, sin input externo."""
        for _ in range(ticks):
            self.sgm.step([0.1] * self.sgm.D, list(range(17)))

    def hablar(self, state):
        """Traduce el estado interno a texto (la boca), o calla/declara inefable."""
        return self.salida.traducir(state)

    def turno_completo(self, texto_usuario=None, state=None):
        """Un turno completo del ciclo de comunicación bidireccional.

        Devuelve un dict con todo lo que pasó (para auditar y para el caller).
        """
        self.turno += 1
        resultado = {"turno": self.turno}

        # 1. Percepción del entorno
        if self.percepcion is not None:
            resultado["percepcion"] = self.percibir()

        # 2. Escuchar input humano (si hay)
        if texto_usuario:
            parse = self.escuchar(texto_usuario)
            resultado["parse"] = {"success": parse.success,
                                  "n_triplets": len(parse.event.triplets) if parse.success and parse.event else 0}

        # 3. Existir (procesar)
        self.existir(ticks=1)

        # 4. Hablar
        if state is None:
            # leer estado dominante del agente si está disponible
            pass
        resultado["salida"] = self.hablar(state) if state is not None else {"texto": None, "modo": "sin_estado"}

        return resultado