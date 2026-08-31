#!/usr/bin/env python3
"""Smoke test: hibernacion + trauma"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from sgm.core.sgm_core import SGMAgent
import random

rng = random.Random(42)
ag = SGMAgent(rng, D=64, n_nodes=8, gamma=0.01)
ag.set_edges({i: [j for j in range(8) if j != i] for i in range(8)})

# Test 1: hibernacion por decaimiento
print("=== Test 1: hibernacion por decaimiento ===")
for _ in range(200):
    ag.tick(1)
activos = sum(1 for e in ag.estado_nodo if e == "ACTIVO")
hibernados = sum(1 for e in ag.estado_nodo if e == "HIBERNADO")
print(f"  Activos: {activos}, Hibernados: {hibernados} (esperado: raiz activa, resto hibernado)")
print(f"  Raiz activa?: {ag.estado_nodo[0] == 'ACTIVO'}")

# Test 2: trauma
print("\n=== Test 2: trauma en nodo 1 ===")
ag2 = SGMAgent(rng, D=64, n_nodes=8)
ag2.set_edges({i: [j for j in range(8) if j != i] for i in range(8)})
v_before = ag2.vitalidad[1]
ag2.aplicar_trauma(1)
v_after = ag2.vitalidad[1]
print(f"  V[1] antes: {v_before:.3f}, despues: {v_after:.3f} (esperado: *0.5)")

# Test 3: trauma repetido lleva a hibernacion
print("\n=== Test 3: trauma repetido -> hibernacion ===")
for _ in range(5):
    ag2.aplicar_trauma(1)
print(f"  V[1] tras 5 traumas: {ag2.vitalidad[1]:.3f}")
print(f"  Estado[1]: {ag2.estado_nodo[1]} (esperado: HIBERNADO)")

# Test 4: afinidad de nodo hibernado es 0
print("\n=== Test 4: afinidad hibernado = 0 ===")
aff = ag2._aff(0, 1)
print(f"  Afinidad(0,1) con nodo 1 hibernado: {aff:.3f} (esperado: 0.0)")

# Test 5: reset_episodio reactiva hibernados
print("\n=== Test 5: reset reactiva hibernados ===")
ag2.reset_episodio()
print(f"  Estado[1] tras reset: {ag2.estado_nodo[1]} (esperado: ACTIVO)")
print(f"  V[1] tras reset: {ag2.vitalidad[1]:.3f}")

# Test 6: step con nodos hibernados no rompe
print("\n=== Test 6: step con hibernados ===")
a = ag.step([0.5]*70, [0,1,2,3])
print(f"  Accion: {a}")
ag.reward(0.5, pain=0.0)
print(f"  E: {ag.E:.3f}")

print("\n=== SMOKE TEST HIBERNACION OK ===")