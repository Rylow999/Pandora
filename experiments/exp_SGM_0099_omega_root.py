#!/usr/bin/env python3
"""Smoke test: ω_root persistente + interocepcion + reset episodio"""
import sys, os
sys.path.insert(0, os.path.expanduser("~/sgm-test"))
from sgm_core import SGMAgent
import random

rng = random.Random(42)
ag = SGMAgent(rng, D=64, n_nodes=8, gamma=0.01)
ag.set_edges({i: [j for j in range(8) if j != i] for i in range(8)})

# Test 1: interocepcion actualiza la raiz
print("=== Test 1: interocepcion ===")
print("omega_root antes:", round(ag.omega[0][0], 3))
ag.actualizar_interocepcion(health=0.9, food=0.8, energia=0.7)
print("omega_root despues:", round(ag.omega[0][0], 3))
print("omega_root_intero[0]:", round(ag.omega_root_intero[0], 3))

# Test 2: la raiz no decae por debajo de 0.5
print("\n=== Test 2: vitalidad protegida ===")
for _ in range(500):
    ag.tick(1)
print("vitalidad[0] tras 500 ticks:", round(ag.vitalidad[0], 3))
print("vitalidad[1] tras 500 ticks:", round(ag.vitalidad[1], 3))
# La raiz debe estar en 0.5+, los demas en 0.05

# Test 3: reset episodio mantiene omega pero resetea estado afectivo
print("\n=== Test 3: reset episodio ===")
ag.E_acumulado = 3.5
ag.status = "CONTRADICTORIA"
ag.doubt_count = 3
omega_guardado = ag.omega[0][0]
ag.reset_episodio()
print("E_acumulado tras reset:", ag.E_acumulado)
print("status tras reset:", ag.status)
print("doubt_count tras reset:", ag.doubt_count)
print("omega_root se mantuvo?", "SI" if abs(ag.omega[0][0] - omega_guardado) < 0.01 else "NO")
print("vitalidad raiz tras reset:", round(ag.vitalidad[0], 3))

# Test 4: step con raiz funciona
print("\n=== Test 4: step con raiz ===")
a = ag.step([0.5]*70, [0,1,2,3])
print("accion:", a)
ag.reward(0.5, pain=0.0)
print("E acum tras reward:", round(ag.E_acumulado, 3))

print("\n=== SMOKE TEST ω_ROOT OK ===")