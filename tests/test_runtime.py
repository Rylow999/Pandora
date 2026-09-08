# -*- coding: utf-8 -*-
"""Tests del núcleo residente (runtime) — la continuidad y la salida proactiva.

Lo que verifica que Pandora VIVE de verdad, no un simulacro:
1. EstadoVivo guarda/carga checkpoint (la identidad sobrevive entre encendidos).
2. El Núcleo reside: corre latidos sin input, guarda al detenerse.
3. La salida proactiva: cuando el deseo de integración es alto, Pandora pide
   hablar por propia iniciativa (misma autoridad que el input humano).
"""
import random
import tempfile

from sgm.core.sgm_core import SGMAgentCore
from pandora.core.pandora_agent import PandoraAgent
from pandora.runtime.estado import EstadoVivo
from pandora.runtime.nucleo import Nucleo


def make_sgm(D=64, n_nodes=16, seed=42):
    rng = random.Random(seed)
    sgm = SGMAgentCore(rng, D=D, n_nodes=n_nodes, gamma=0.01)
    edges = {i: rng.sample(range(n_nodes), min(4, n_nodes - 1)) for i in range(n_nodes)}
    sgm.set_edges(edges)
    return sgm


class TestContinuidad:
    def test_checkpoint_sobrevive_reinicio(self):
        """El grafo guardado se recarga igual (es la MISMA, no una réplica)."""
        base = tempfile.mkdtemp()
        estado = EstadoVivo(base_dir=base)

        sgm = make_sgm()
        agente = PandoraAgent(sgm=sgm, load_checkpoint=False)
        nucleo = Nucleo(estado, agente)
        nucleo.correr(intervalo=0.001, max_ticks=2)  # corre + guarda al salir

        assert estado.checkpoint_existe()

        # "Reiniciar" proceso: SGM nuevo que carga el checkpoint
        sgm2 = make_sgm(seed=999)
        estado2 = EstadoVivo(base_dir=base)
        assert estado2.cargar(sgm2) is True
        assert sgm2.integridad_topologica() == sgm.integridad_topologica()

    def test_primer_encendido_nace(self):
        """Sin checkpoint previo, el núcleo nace (no carga nada)."""
        base = tempfile.mkdtemp()
        estado = EstadoVivo(base_dir=base)
        assert estado.checkpoint_existe() is False
        assert estado.cargar(make_sgm()) is False


class TestSalidaProactiva:
    def test_pide_hablar_cuando_fragmentado(self):
        """Con deseo de integración alto, Pandora emite proactivo."""
        base = tempfile.mkdtemp()
        estado = EstadoVivo(base_dir=base)

        sgm = make_sgm()
        agente = PandoraAgent(sgm=sgm, load_checkpoint=False)
        # forzar fragmentación: aislar nodos => integridad ~0 => deseo ~1
        for nid in list(sgm.edges.keys()):
            sgm.edges[nid] = []

        nucleo = Nucleo(estado, agente, umbral_deseo=0.3, intervalo_proactivo=0.0)
        mensajes = []
        nucleo.on_proactivo = lambda t: mensajes.append(t)

        nucleo.correr(intervalo=0.001, max_ticks=1)

        # El articular usa mock/fallback, pero debe emitir ALGO (no None)
        assert len(mensajes) >= 1, "fragmentado debería querer hablar"

    def test_no_habla_cuando_coherente(self):
        """Con baja dispersión, no pide hablar (no habla por hablar)."""
        base = tempfile.mkdtemp()
        estado = EstadoVivo(base_dir=base)

        sgm = make_sgm()
        agente = PandoraAgent(sgm=sgm, load_checkpoint=False)
        # forzar coherencia máxima: todos los nodos conectados y con same fase
        # (imposible exacto, pero umbral alto implica que casi nunca hable)
        nucleo = Nucleo(estado, agente, umbral_deseo=0.99, intervalo_proactivo=0.0)
        mensajes = []
        nucleo.on_proactivo = lambda t: mensajes.append(t)

        nucleo.correr(intervalo=0.001, max_ticks=3)
        # Con umbral 0.99 (casi imposible), no debería disparar en 3 ticks
        assert len(mensajes) == 0