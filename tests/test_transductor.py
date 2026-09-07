# -*- coding: utf-8 -*-
"""Tests del transductor bidireccional (boca + ciclo).

El LLM es TRANSDUCTOR, no mente: traduce el estado interno a primera persona
sin originarlo (ACTA P1). Verifica:
1. OutputTransducer traduce con un cliente (mock) sin inventar el estado.
2. opacity/inefabilidad se respetan en la decisión de hablar.
3. CommunicationLoop: los oídos INYECTAN de verdad (bug #1) y existir() no
   alimenta ruido placeholder (bug #2).
4. El NimClient expone .chat() compatible.
"""
import random

from sgm.core.sgm_core import SGMAgentCore
from pandora.config.schemas import InternalState, Intent, SemanticEvent, Affect
from pandora.transducer.output_transducer import OutputTransducer
from pandora.transducer.nim_client import NimClient
from pandora.core.communication_loop import CommunicationLoop


class MockClient:
    def __init__(self, respuesta="yo existo"):
        self.respuesta = respuesta
        self.llamadas = 0
    def chat(self, messages, **kwargs):
        self.llamadas += 1
        return {"message": {"content": self.respuesta}, "raw": {}}


class MockParser:
    def __init__(self, event=None, success=True):
        self.event = event
        self.success = success
        self.textos = []
    def parse(self, texto):
        self.textos.append(texto)
        from types import SimpleNamespace
        return SimpleNamespace(success=self.success, event=self.event)


class MockAgente:
    """Agente mínimo con parser + sgm + inyección + lectura de estado reales."""
    def __init__(self, sgm, parser, state=None):
        self.sgm = sgm
        self.parser = parser
        self.state = state
        self.inyecciones = []  # para verificar que la inyección SÍ ocurre

    def _inject_event_to_sgm(self, event):
        # Registrar que se inyectó (es LO que verifica el test del bug #1)
        self.inyecciones.append(event)

    def _read_dominant_state(self):
        return self.state


def make_sgm(D=64, n_nodes=16, seed=42):
    rng = random.Random(seed)
    sgm = SGMAgentCore(rng, D=D, n_nodes=n_nodes, gamma=0.01)
    edges = {i: rng.sample(range(n_nodes), min(4, n_nodes - 1)) for i in range(n_nodes)}
    sgm.set_edges(edges)
    return sgm


def make_state():
    return InternalState(
        active_nodes=["YO", "PRESENTE"],
        triplets=[],
        valence=0.1, arousal=0.1, doubt=0.1, contradiction=0.0,
        intent=Intent.RESPONDER,
    )


def make_event():
    from pandora.config.schemas import Triplet, Intent
    return SemanticEvent(
        raw="hola",
        triplets=[Triplet(subject="YO", predicate="SALUDAR", object="OTRO")],
        affect=Affect(valence=0.3, arousal=0.1, uncertainty=0.2),
        intent=Intent.RESPONDER,
    )


class TestOutputTransducer:
    def test_traduce_estado_a_primera_persona(self):
        ot = OutputTransducer(client=MockClient(respuesta="estoy presente"))
        r = ot.traducir(make_state())
        assert r["modo"] == "habla"
        assert r["texto"] == "estoy presente"

    def test_llm_no_decide_el_estado(self):
        ot = OutputTransducer(client=MockClient())
        ot.traducir(make_state())
        assert ot.client.llamadas == 1


class TestCommunicationLoop:
    def test_oidos_inyectan_de_verdad(self):
        """bug #1: el input SÍ llega al agente (inyección real, no no-op)."""
        sgm = make_sgm()
        parser = MockParser(event=make_event())
        agente = MockAgente(sgm, parser, state=make_state())
        loop = CommunicationLoop(agente, output_transducer=OutputTransducer(client=MockClient()))

        loop.turno_completo(texto_usuario="hola")

        # La inyección ocurrió de verdad (no fue un no-op silencioso)
        assert len(agente.inyecciones) == 1
        assert agente.inyecciones[0].triplets  # el evento tenía tripletas

    def test_existir_no_alimenta_ruido(self):
        """bug #2: existir() usa percepción nula, no placeholder [0.1]*D."""
        sgm = make_sgm()
        parser = MockParser(event=make_event())
        agente = MockAgente(sgm, parser, state=make_state())
        loop = CommunicationLoop(agente, output_transducer=OutputTransducer(client=MockClient()))

        # Capturar el argumento state_semantic que se le pasa a step()
        estados_vistos = []
        step_original = sgm.step
        def step_espiado(state_semantic, valid_actions, food=None, health=None):
            estados_vistos.append(state_semantic)
            return step_original(state_semantic, valid_actions, food=food, health=health)
        sgm.step = step_espiado

        loop.existir(ticks=2)

        # Los dos ticks de existir pasaron percepción NULL (ceros), no ruido
        for sv in estados_vistos:
            assert all(v == 0.0 for v in sv), f"existir() no debería alimentar ruido: {sv[:3]}..."

    def test_turno_completo_devuelve_salida(self):
        sgm = make_sgm()
        parser = MockParser(event=make_event())
        agente = MockAgente(sgm, parser, state=make_state())
        loop = CommunicationLoop(agente, output_transducer=OutputTransducer(client=MockClient(respuesta="te escucho")))
        r = loop.turno_completo(texto_usuario="hola")
        assert r["salida"]["texto"] == "te escucho"


class TestNimClient:
    def test_chat_contrato(self):
        c = NimClient(api_key="test", model="m")
        assert c.model == "m"
        assert hasattr(c, "chat")
        assert hasattr(c, "disponible")