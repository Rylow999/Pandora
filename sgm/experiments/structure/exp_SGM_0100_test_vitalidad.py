#!/usr/bin/env python3
"""Smoke test rapido del agente con vitalidad"""
import sys, os
sys.path.insert(0, os.path.expanduser("~/sgm-test"))
from sgm.core.sgm_core import SGMAgent
import random

rng = random.Random(7)
ag = SGMAgent(rng, D=64, n_nodes=8, gamma=0.01)
ag.set_edges({i: [j for j in range(8) if j != i] for i in range(8)})
a = ag.step([0.5]*70, [0,1,2,3])
print("step OK:", a)
ag.reward(0.5, pain=0.0)
print("reward OK, E=%.3f" % ag.E)
for i in range(20):
    a = ag.step([0.5]*70, [0,1,2,3])
    ag.reward(0, pain=0.0)
    v = [round(v,2) for v in ag.vitalidad]
    print("t=%d: accion=%d, vital=%s" % (i, a, v))
print("\nOK")