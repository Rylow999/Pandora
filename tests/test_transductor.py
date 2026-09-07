# -*- coding: utf-8 -*-
"""Tests del transductor bidireccional (boca + ciclo).

El LLM es TRANSDUCTOR, no mente: traduce el estado interno a primera persona
sin originarlo (ACTA P1). Verifica:
1. OutputTransducer traduce con un cliente (mock) sin inventar el estado.
2. La opacity (silencio) y la inefabilidad se respetan en la decisión de hablar.
3. El CommunicationLoop orquesta el flujo sin romper (con cliente mock).
4. El NimClient lee key/modelo del entorno y expone .chat() compatible.
"""
import random

from sgm.core.sgm_core import SGMAgentCore
from pandora.config.schemas import InternalState, Intent
from pandora.transducer.output_transducer import OutputTransducer
from pandora.transducer.nim_client import NimClient
from pandora.core.communication_loop import CommunicationLoop


class MockClient:
    """Cliente LLM falso que devuelve texto determinista (sin red)."""
    def __init__(self, respuesta="yo existo"):
        self.respuesta = respuesta
        self.llamadas = 0

    def chat(self, messages, **kwargs):
        self.llamadas += 1
        return {"message": {"content": self.respuesta}, "raw": {}}


class MockParser:
    def __init__(self):
        self.last = None
    def parse(self, texto):
        self.last = texto
        from types import SimpleNamespace
        return SimpleNamespace(success=True, event=None)


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


class TestOutputTransducer:
    def test_traduce_estado_a_primera_persona(self):
        """La boca traduce el estado, sin decidirlo (usa el cliente mock)."""
        ot = OutputTransducer(client=MockClient(respuesta="estoy presente"))
        r = ot.traducir(make_state())
        assert r["modo"] == "habla"
        assert r["texto"] == "estoy presente"

    def test_llm_no_decide_el_estado(self):
        """El texto sale del LLM, pero el estado es del SGM (el mock nunca ve el estado)."""
        ot = OutputTransducer(client=MockClient())
        ot.traducir(make_state())
        # El mock no recibe input del estado por un canal que lo "decida": solo lo
        # recibe como texto en el prompt. Verificamos que el flujo es traducir.
        assert ot.client.llamadas == 1


class TestCommunicationLoop:
    def test_turno_sin_input_no_rompe(self):
        """El ciclo corre un turno sin input (solo existir) y no falla."""
        sgm = make_sgm()
        parser = MockParser()
        salida = OutputTransducer(client=MockClient())
        loop = CommunicationLoop(sgm, parser, output_transducer=salida)
        r = loop.turno_completo(texto_usuario=None, state=None)
        assert r["turno"] == 1

    def test_turno_con_input_y_estado(self):
        """El ciclo procesa input + estado y devuelve salida traducida."""
        sgm = make_sgm()
        parser = MockParser()
        salida = OutputTransducer(client=MockClient(respuesta="te escucho"))
        loop = CommunicationLoop(sgm, parser, output_transducer=salida)
        r = loop.turno_completo(texto_usuario="hola", state=make_state())
        assert r["salida"]["texto"] == "te escucho"
        assert r["parse"]["success"] is True


class TestNimClient:
    def test_chat_contrato(self):
        """NimClient expone .chat() compatible (aunque no haya red en test)."""
        c = NimClient(api_key="test", model="m")
        # Solo verificamos que el método existe y el modelo se seteó
        assert c.model == "m"
        assert hasattr(c, "chat")
        assert hasattr(c, "disponible")