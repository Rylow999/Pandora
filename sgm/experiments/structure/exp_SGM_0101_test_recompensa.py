#!/usr/bin/env python3
"""Test: repeticion con y sin reward"""
import sys, os
sys.path.insert(0, os.path.expanduser("~/sgm-test"))
from sgm.core.sgm_core import SGMAgent
import random

rng = random.Random(7)
ag = SGMAgent(rng, D=64, n_nodes=8, gamma=0.01)
ag.set_edges({i: [j for j in range(8) if j != i] for i in range(8)})
print("--- SIN REWARD ---")
for i in range(15):
    a = ag.step([0.5]*70, [0,1,2,3])
    ag.reward(0, pain=0.0)
    print("t=%d: act=%d vital[%d]=%.3f" % (i, a, a, ag.vitalidad[a]))

print("\n--- CON REWARD ---")
ag2 = SGMAgent(rng, D=64, n_nodes=8, gamma=0.01)
ag2.set_edges({i: [j for j in range(8) if j != i] for i in range(8)})
for i in range(10):
    a = ag2.step([0.5]*70, [0,1,2,3])
    r = 0.5 if i >= 5 else 0
    ag2.reward(r, pain=0.0)
    print("t=%d: act=%d vital[%d]=%.3f (r=%.1f)" % (i, a, a, ag2.vitalidad[a], r))
print("\nOK")