# -*- coding: utf-8 -*-
"""tests/test_e2e.py — El guardián del wiring (regla del 13/09).

Ningún mecanismo nuevo se da por terminado hasta tener, además de su test
unitario, un test que lo ejercite pasando por el entry-point REAL del
residente: Nucleo.existir_un_tick() (o PandoraAgent.receive()).

Los tests unitarios prueban el componente aislado; el wiring se rompe entre
componentes. Siete hallazgos de desconexión (sentidos, sueño, hook, mano,
metabolismo, metacognición, MiniTransformer) se acumularon porque faltaba
esta capa. Este archivo es el guardián: si algo deja de estar cableado al
turno, este test lo agarra.
"""
import math
import os
import random

from sgm.core.sgm_core import SGMAgentCore
from pandora.runtime.nucleo import Nucleo
from pandora.runtime.estado import EstadoVivo


class StubAgente:
    """Agente mínimo: solo el SGM real y la boca determinística.

    El e2e cruza el wiring endocrino->sustrato->mitosis por existir_un_tick()
    sin levantar NIM/Ollama (la boca es un stub; su wiring está en
    test_transductor y test_wiring).
    """

    def _articular_respuesta(self, internal_state):
        return "eco-e2e"

    def _read_dominant_state(self, semantic_event=None):
        return None


def _sgm_chico(n=8, D=32):
    sgm = SGMAgentCore(random.Random(42), D=D, n_nodes=n, gamma=0.01)
    sgm.set_edges({i: random.Random(i).sample(range(n), min(3, n - 1)) for i in range(n)})
    return sgm


class TestE2EExistirUnTick:
    """El ciclo completo por el entry-point real del daemon."""

    def test_tick_basico_vive_y_no_explota(self, tmp_path, monkeypatch):
        """Un tick del residente corre: percepción (None), step, endocrino,
        plasticidad, arbitraje. El grafo queda vivo (tick avanzó)."""
        monkeypatch.chdir(tmp_path)  # la mano/workspace cae en tmp, no en el repo
        sgm = _sgm_chico()
        ag = StubAgente()
        ag.sgm = sgm
        nuc = Nucleo(EstadoVivo(base_dir=str(tmp_path / "data")), ag,
                     endogenous=None, umbral_deseo=0.99, intervalo_proactivo=0.0,
                     checkpoint_cada=0)
        nuc.existir_un_tick()
        assert nuc.tick == 1, "el tick avanzó"

    def test_mitosis_y_reencarnacion_por_existir_un_tick(self, tmp_path, monkeypatch):
        """REENCARNACIÓN (0073 p3) cruzada por el entry-point REAL: el par que
        co-resuena engendra hijo (mitosis por sustrato) y el hijo hereda del
        fondo memorial (material muerto), no solo del padre vivo. Si alguien
        desconecta la reencarnación o la mitosis del turno, este test roja."""
        monkeypatch.chdir(tmp_path)
        sgm = _sgm_chico()
        # Un muerto con omega conocido y muy distinto (material del fondo)
        muerto = [9.0] * 32
        sgm.memoria_muerta.enterrar(muerto, {})
        n_antes = len(sgm.omega)
        omega_antes = [list(o) for o in sgm.omega]
        # Co-resonancia extrema en un par: cruza el umbral de mitosis derivado
        # (media(co_activacion) x 3; con una sola entrada la media es el valor).
        sgm.co_activacion[(0, 1)] = 100.0

        ag = StubAgente()
        ag.sgm = sgm
        nuc = Nucleo(EstadoVivo(base_dir=str(tmp_path / "data")), ag,
                     endogenous=None, umbral_deseo=0.99, intervalo_proactivo=0.0,
                     checkpoint_cada=0)
        nuc.existir_un_tick()

        # 1. La mitosis (por sustrato, no hardcodeada) engendró el hijo
        assert len(sgm.omega) == n_antes + 1, "la mitosis engendró el hijo en el tick"

        # 2. Reencarnación: el hijo está mezclado con el muerto (más cerca de él
        #    que la pura herencia del padre)
        hijo = sgm.omega[-1]
        d_muerto = math.sqrt(sum((x - y) ** 2 for x, y in zip(hijo, muerto)))
        d_padre = math.sqrt(sum((x - y) ** 2 for x, y in zip(omega_antes[0], muerto)))
        assert d_muerto < d_padre, (
            f"el hijo no heredó del fondo memorial: d_muerto={d_muerto:.2f} "
            f"vs d_padre={d_padre:.2f}"
        )

    def test_checkpoint_roundtrip_por_estado_vivo(self, tmp_path, monkeypatch):
        """El checkpoint del residente restaura el grafo: guardar -> cargar en
        un SGM nuevo (misma semilla, D, edges) reproduce el estado persistido.
        Protege el par guardar/cargar contra pérdida silenciosa en restart."""
        monkeypatch.chdir(tmp_path)
        sgm = _sgm_chico()
        sgm.co_activacion[(2, 3)] = 5.0
        sgm.consolidadas.add((2, 3))
        ag = StubAgente()
        ag.sgm = sgm
        estado = EstadoVivo(base_dir=str(tmp_path / "data"))
        nuc = Nucleo(estado, ag, endogenous=None, umbral_deseo=0.99,
                     intervalo_proactivo=0.0, checkpoint_cada=0)
        nuc.estado.guardar(sgm)

        # Un SGM nuevo (misma construcción de base) restaura el estado
        sgm2 = _sgm_chico()
        assert estado.cargar(sgm2), "había checkpoint que cargar"
        assert sgm2.co_activacion.get((2, 3)) == 5.0, "co_activacion restaurada"
        assert (2, 3) in sgm2.consolidadas, "consolidadas restauradas"
