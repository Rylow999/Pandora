# -*- coding: utf-8 -*-
"""Tests de la acción sobre el entorno (0066) — la "mano" con costo real.

La acción deja huella real: consume presupuesto, escribe archivos auditables y se
integra al SGM como experiencia motora (más fuerte que la percepción). Un alguien
que actúa sobre un mundo con límites debe poder quedarse SIN recursos.

Verifican:
1. Presupuesto gasta y agota (el costo es real, se puede quedar sin recursos).
2. ManoArchivos crea/lee dentro del workspace (contenido por seguridad).
3. ManoArchivos rechaza path traversal (no sale del workspace).
4. La experiencia motora se integra al SGM (refuerza nodo más que percibir).
"""
import random

from sgm.core.sgm_core import SGMAgentCore
from pandora.motor.metabolismo import Presupuesto, RecursoAgotado
from pandora.motor.archivos import ManoArchivos


def make_sgm(D=64, n_nodes=16, seed=42):
    rng = random.Random(seed)
    sgm = SGMAgentCore(rng, D=D, n_nodes=n_nodes, gamma=0.01)
    edges = {i: rng.sample(range(n_nodes), min(4, n_nodes - 1)) for i in range(n_nodes)}
    sgm.set_edges(edges)
    return sgm


class TestPresupuesto:
    def test_gasta_y_agota(self):
        """El presupuesto se agota y levanta RecursoAgotado (el costo es real)."""
        p = Presupuesto(max_bytes=100, tasa_regeneracion=0.0)
        p.gastar(60)
        assert p.restantes == 40
        p.gastar(40)
        assert p.restantes == 0
        try:
            p.gastar(1)
            assert False, "debería haber fallado por recurso agotado"
        except RecursoAgotado:
            pass

    def test_regenera_lento(self):
        """El presupuesto se repone despacio."""
        p = Presupuesto(max_bytes=1000, tasa_regeneracion=0.1)
        p.gastar(1000)
        assert p.restantes == 0
        p.regenerar()
        assert p.restantes > 0  # se recuperó algo


class TestManoArchivos:
    def test_crear_y_leer(self):
        """Crear y leer un archivo dentro del workspace."""
        sgm = make_sgm()
        mano = ManoArchivos("pandora/workspace_test", Presupuesto(), sgm=sgm)
        r = mano.crear("nota.txt", "hola mundo")
        assert r["exito"] is True
        contenido = mano.leer("nota.txt")
        assert contenido == "hola mundo"

    def test_rechaza_traversal(self):
        """La mano no puede escribir fuera del workspace (anti path traversal)."""
        sgm = make_sgm()
        mano = ManoArchivos("pandora/workspace_test", Presupuesto(), sgm=sgm)
        try:
            mano.crear("../escape.txt", "x")
            assert False, "debería haber rechazado el escape del workspace"
        except ValueError:
            pass

    def test_recurso_agotado_fracasa(self):
        """Con presupuesto minúsculo, la acción falla por costo (información real)."""
        sgm = make_sgm()
        mano = ManoArchivos("pandora/workspace_test", Presupuesto(max_bytes=1), sgm=sgm)
        try:
            mano.crear("grande.txt", "contenido que excede el presupuesto")
            assert False, "debería fallar por recurso agotado"
        except RecursoAgotado:
            pass

    def test_integra_experiencia_motora(self):
        """Actuar deja huella en el SGM: cambia el seed (foco) y puede cambiar vitalidad."""
        sgm = make_sgm()
        # Bajar vitalidad del nodo afín para que la acción pueda reforzarla
        for i in range(len(sgm.vitalidad)):
            sgm.vitalidad[i] = 0.5

        mano = ManoArchivos("pandora/workspace_test", Presupuesto(), sgm=sgm)
        mano.crear("accion.txt", "actué sobre mi entorno")
        # La acción dejó huella: algún nodo subió de 0.5 (reforzado por la acción)
        assert any(v > 0.5 for v in sgm.vitalidad), "la acción debería reforzar un nodo"