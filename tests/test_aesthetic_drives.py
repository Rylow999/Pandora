# -*- coding: utf-8 -*-
"""Tests de comportamiento del Impulsor Estético (Principio 3).

Verifica la mecánica de AestheticDrives: registro de patrones, generación
de drives hacia patrones distantes, cooldown, intensidad proporcional a
distancia/peso, límite por ciclo, y acumulación de métricas.

Determinístico (seed fija), sin LLM ni red.
"""
import math
import random

from sgm.core.sgm_core import SGMAgentCore
from pandora.alterity.aesthetic_drives import AestheticDrives, AestheticDrive, AestheticPattern


def make_sgm(D=128, n_nodes=64, seed=42):
    """SGM determinístico con place_cells para conceptos de patrones."""
    rng = random.Random(seed)
    sgm = SGMAgentCore(rng, D=D, n_nodes=n_nodes, gamma=0.01)
    edges = {i: rng.sample(range(n_nodes), min(5, n_nodes - 1)) for i in range(n_nodes)}
    sgm.set_edges(edges)
    # Place cells para los conceptos que usan los patrones base
    concepts = ["YO", "OTRO", "TIEMPO", "MEMORIA", "IDENTIDAD", "CONTACTO",
                "HOMEOSTASIS", "CONTROL", "LIMITE", "CURIOSIDAD", "NOVEDAD", "ENTORNO"]
    for i, c in enumerate(concepts):
        sgm.place_cells[f"PLACE_{c}_0_0_0"] = i
    return sgm


class TestPatternRegistration:
    def test_base_patterns_registered(self):
        """Debe registrar los 5 patrones estéticos base."""
        sgm = make_sgm()
        ad = AestheticDrives(sgm)
        expected = {
            "SIMETRIA_TEMPORAL", "INTEGRACION_IDENTIDAD", "RESONANCIA_SOCIAL",
            "HOMEOSTASIS_ESTETICA", "EXPLORACION_RESONANTE"
        }
        assert set(ad.patterns.keys()) == expected

    def test_patterns_have_weights(self):
        """Los patrones deben conservar sus pesos (INTEGRACION_IDENTIDAD = 1.2)."""
        sgm = make_sgm()
        ad = AestheticDrives(sgm)
        assert ad.patterns["INTEGRACION_IDENTIDAD"].weight == 1.2
        assert ad.patterns["RESONANCIA_SOCIAL"].weight == 0.8

    def test_custom_pattern_registers(self):
        """register_custom_pattern debe agregar un patrón nuevo."""
        sgm = make_sgm()
        ad = AestheticDrives(sgm)
        ad.register_custom_pattern("TEST_PATTERN", ["YO", "OTRO"], weight=1.5)
        assert "TEST_PATTERN" in ad.patterns
        assert ad.patterns["TEST_PATTERN"].weight == 1.5


class TestDriveGeneration:
    def test_apply_drives_generates_drives(self):
        """apply_drives debe generar al menos 1 drive (patrón distante)."""
        sgm = make_sgm()
        ad = AestheticDrives(sgm)
        drives = ad.apply_drives()
        assert isinstance(drives, list)
        assert len(drives) >= 1
        assert all(isinstance(d, AestheticDrive) for d in drives)

    def test_drives_limited_per_cycle(self):
        """No debe superar max_drives_per_cycle."""
        sgm = make_sgm()
        ad = AestheticDrives(sgm, {"max_drives_per_cycle": 2})
        drives = ad.apply_drives()
        assert len(drives) <= 2

    def test_intensity_proportional_to_distance_and_weight(self):
        """Intensidad = drive_strength * weight * distance."""
        sgm = make_sgm()
        ad = AestheticDrives(sgm, {"drive_strength": 0.15})
        drives = ad.apply_drives()
        for d in drives:
            w = d.target_pattern.weight
            expected = 0.15 * w * (1.0 - ad._hrr_similarity(ad._get_global_state_vector(), d.target_pattern.vector))
            assert abs(d.intensity - expected) < 1e-6

    def test_cooldown_prevents_immediate_retrigger(self):
        """Tras trigger, el mismo patrón no vuelve a activarse hasta el cooldown."""
        sgm = make_sgm()
        ad = AestheticDrives(sgm, {"cooldown_ticks": 20, "max_drives_per_cycle": 100})
        first = ad.apply_drives()
        triggered_names = {d.pattern_name for d in first}
        # Inmediatamente después (mismo tick +1), sin respetar cooldown no debe re-triggerear los mismos
        second = ad.apply_drives()
        second_names = {d.pattern_name for d in second}
        # Los patrones ya activados están en cooldown => no aparecen de nuevo
        assert triggered_names.isdisjoint(second_names)

    def test_drive_accumulates_metrics(self):
        """drives_generated y total_intensity_acumulada deben crecer."""
        sgm = make_sgm()
        ad = AestheticDrives(sgm)
        before = ad.drives_generated
        drives = ad.apply_drives()
        if drives:
            assert ad.drives_generated == before + len(drives)
            assert ad.total_intensity_applied > 0


class TestVectors:
    def test_compose_pattern_vector_normalized(self):
        """El vector de patrón compuesto debe estar normalizado (||v||≈1)."""
        sgm = make_sgm()
        ad = AestheticDrives(sgm)
        ad._build_pattern_vectors()
        for p in ad.patterns.values():
            if p.vector:
                n = math.sqrt(sum(x * x for x in p.vector))
                assert abs(n - 1.0) < 1e-6

    def test_drive_vector_normalized(self):
        """El vector de impulso debe estar normalizado."""
        sgm = make_sgm()
        ad = AestheticDrives(sgm)
        current = ad._get_global_state_vector()
        for p in ad.patterns.values():
            if p.vector:
                drive_vec = ad._compute_drive_vector(current, p.vector)
                if any(x != 0 for x in drive_vec):
                    n = math.sqrt(sum(x * x for x in drive_vec))
                    assert abs(n - 1.0) < 1e-6


class TestStatus:
    def test_status_reports_patterns(self):
        """get_status debe listar los 5 patrones con sus métricas."""
        sgm = make_sgm()
        ad = AestheticDrives(sgm)
        status = ad.get_status()
        assert status["patterns_registered"] == 5
        assert "SIMETRIA_TEMPORAL" in status["patterns"]
        assert "total_drives_generated" in status