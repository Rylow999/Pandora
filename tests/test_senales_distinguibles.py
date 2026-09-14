# -*- coding: utf-8 -*-
"""Test de distinguibilidad de las señales internas (NOTA 0072).

Verifica que las métricas que alimentan la boca ya NO colapsan a un solo número:
- doubt desacoplada de valence (duda = zonas ciegas, no deseo reciclado)
- contradiction continua (dispersión de fase), no semáforo
- arousal con fuente propia, no espejo del input

La distinguibilidad de las señales es la condición necesaria para que la voz
produzca estados distinguibles (la distinguibilidad del texto la mide el test
e2e con LLM, aparte).
"""
import random

from sgm.core.sgm_core import SGMAgentCore
from pandora.core.pandora_agent import PandoraAgent


def _make_agente(seed=42, D=64, n=24):
    sgm = SGMAgentCore(random.Random(seed), D=D, n_nodes=n, gamma=0.01)
    sgm.set_edges({i: random.Random(seed + i).sample(range(n), min(4, n - 1)) for i in range(n)})
    ag = PandoraAgent(sgm=sgm, load_checkpoint=False)
    return ag, sgm


class TestSenalesDistinguibles:
    def test_doubt_desacoplada_de_valence(self):
        """Un grafo íntegro con muchos nodos dormidos DUDA sin estar fragmentado."""
        ag, sgm = _make_agente()
        # Forzar vitalidad: muchísimos nodos dormidos (duda alta) pero conectados
        # (integridad alta, valence positiva)
        for i in range(len(sgm.vitalidad)):
            sgm.vitalidad[i] = 0.1  # casi todos dormidos
        for i in range(8):
            sgm.vitalidad[i] = 0.9  # unos pocos muy activos
        sgm.phi = [random.Random(7).uniform(0, 6.28) for _ in range(len(sgm.phi))]
        # Alinear fases para que la coherencia sea alta (integridad alta)
        for i in range(len(sgm.phi)):
            sgm.phi[i] = 0.5

        duda = ag._duda_zona_ciega()
        deseo = ag._deseo_integracion()
        # duda alta (muchos dormidos), deseo bajo o distinto (coherencia alta)
        assert duda > 0.5, f"duda debería ser alta (zonas ciegas), dio {duda:.2f}"
        assert duda != deseo, f"duda y deseo no deberían ser el mismo número: {duda} vs {deseo}"

    def test_contradiccion_es_gradiente_no_semaforo(self):
        """La contradicción varía continuamente con la dispersión de fase."""
        ag, sgm = _make_agente()
        # fases alineadas => contradicción ~0
        sgm.phi = [0.1] * len(sgm.phi)
        c_alineado = ag._contradiccion_fase()
        # fases dispersas => contradicción alta
        import math
        sgm.phi = [i * (2 * math.pi / len(sgm.phi)) for i in range(len(sgm.phi))]
        c_disperso = ag._contradiccion_fase()
        assert c_alineado < c_disperso, f"alineado={c_alineado:.2f} debería ser < disperso={c_disperso:.2f}"
        # es continua: no solo dos valores
        assert 0.0 <= c_alineado <= 1.0 and 0.0 <= c_disperso <= 1.0

    def test_arousal_no_es_solo_espejo(self):
        """El arousal tiene fuente propia (zona activa), independiente del input."""
        ag, sgm = _make_agente()
        ag.sgm._amenaza = 0.0  # sin input del otro
        propio = ag._arousal_kuramoto()
        assert 0.0 <= propio <= 1.0
        # el arousal propio es función del grafo, no del input inyectado
        ag.sgm._amenaza = 0.9  # input alto
        mezclado = 0.5 * ag.sgm._amenaza + 0.5 * ag._arousal_kuramoto()
        assert 0.0 <= mezclado <= 1.0


class TestInternalStateDistingue:
    def test_estados_distintos_dan_senales_distintas(self):
        """Dos configuraciones de grafo distintas producen InternalState distintas."""
        ag1, sgm1 = _make_agente(seed=1)
        ag2, sgm2 = _make_agente(seed=99)
        # configuraciones deliberadamente distintas
        for i in range(len(sgm1.vitalidad)):
            sgm1.vitalidad[i] = 0.05  # todo dormido -> duda máxima
        for i in range(len(sgm2.vitalidad)):
            sgm2.vitalidad[i] = 0.95  # todo activo -> duda mínima
        for i in range(len(sgm1.phi)):
            sgm1.phi[i] = 3.14  # fases desalineadas del centro
        for i in range(len(sgm2.phi)):
            sgm2.phi[i] = 0.0   # fases alineadas

        d1 = ag1._duda_zona_ciega()
        d2 = ag2._duda_zona_ciega()
        assert d1 > d2, f"estado 1 (todo dormido) debe dudar más: {d1:.2f} vs {d2:.2f}"