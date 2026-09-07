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

IMPORTANTE (bug #1 resuelto): la inyección semántica (texto → grafo) es un
método del AGENTE (PandoraAgent._inject_event_to_sgm), no del SGM crudo. Por eso
el loop recibe el agente (que envuelve parser + sgm + inyección + lectura de
estado), no el SGM suelto. Antes recibía el SGM crudo y la inyección era un
no-op silencioso (hasattr siempre False).
"""
from ..transducer.output_transducer import OutputTransducer
from ..transducer.nim_client import NimClient


class CommunicationLoop:
    """Ciclo de comunicación: percibir → escuchar → existir → hablar → actuar.

    Recibe el agente completo (PandoraAgent), que sabe inyectar el evento y leer
    el estado dominante. No recibe el SGM crudo.
    """

    def __init__(self, agente, output_transducer=None, percepcion=None, mano=None,
                 valid_actions=None):
        self.agente = agente
        self.sgm = agente.sgm
        self.salida = output_transducer or OutputTransducer(client=NimClient())
        self.percepcion = percepcion
        self.mano = mano
        # Acciones válidas: por defecto el espacio mínimo del loop (no el de Crafter,
        # 17 acciones — bug #2). Un agente conversacional/de-entorno tiene 1 acción
        # no-op (existir) más lo que el entorno permita.
        self.valid_actions = valid_actions if valid_actions is not None else [0]
        self.turno = 0

    def percibir(self):
        """Percibe el entorno y lo integra al SGM (si hay sentidos)."""
        if self.percepcion is None:
            return None
        vector, carga, muestra = self.percepcion.percibir()
        self.sgm.integrar_experiencia_entorno(vector, carga)
        return {"carga": carga, "muestra": muestra}

    def escuchar(self, texto_usuario):
        """Traduce el texto humano a SemanticEvent y lo inyecta al SGM (los oídos).

        Usa el método real del agente (PandoraAgent.receive-like), no un hasattr
        sobre el SGM crudo. Si el agente no expone la inyección, falla ruidoso,
        no silencioso.
        """
        parse = self.agente.parser.parse(texto_usuario)
        if parse.success and parse.event is not None:
            self.agente._inject_event_to_sgm(parse.event)
        return parse

    def existir(self, ticks=1):
        """El SGM procesa por N ticks SIN input (sin placeholder constante).

        Bug #2 resuelto: antes se pasaba [0.1]*D como percepción constante (ruido).
        Ahora, existir sin input es un paso de consolidación endógena honesto:
        no se fuerza percepción; se deja que el grafo siga su dinámica interna
        (Kuramoto, dispersión, reintegración) con una percepción nula.
        """
        for _ in range(ticks):
            # Percepción nula = vector de ceros (no ruido): el sistema existe
            # sin que nada externo lo estimule.
            self.sgm.step([0.0] * self.sgm.D, self.valid_actions)

    def hablar(self, state=None):
        """Traduce el estado interno a texto (la boca), o calla/declara inefable."""
        if state is None:
            state = self.agente._read_dominant_state() if hasattr(self.agente, "_read_dominant_state") else None
        if state is None:
            return {"texto": None, "razon": "sin_estado", "modo": "sin_estado"}
        return self.salida.traducir(state)

    def turno_completo(self, texto_usuario=None):
        """Un turno completo del ciclo de comunicación bidireccional."""
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

        # 3. Existir (procesar, sin input)
        self.existir(ticks=1)

        # 4. Hablar
        resultado["salida"] = self.hablar()

        return resultado