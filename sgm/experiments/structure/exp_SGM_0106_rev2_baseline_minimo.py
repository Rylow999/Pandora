#!/usr/bin/env python3
"""
exp_SGM_0106_rev2 — Baseline minimo (core recien limpiado).
Verifica que con el core minimo (sin omega_root, sin bonus, sin modos, sin conn_type)
el agente recupera el comportamiento de la v2 original (se mueve, come, explora).
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from sgm.core.sgm_core import SGMAgent
import crafter
from collections import Counter

random.seed(42)
rng = random.Random(42)
D = 128; N_NODES = 64
REWARD_NOVEDAD = 0.1
ACC = {0:"noop",1:"move_left",2:"move_right",3:"move_up",4:"move_down",
       5:"do",6:"sleep",7:"place_stone",8:"place_table",9:"place_furnace",
       10:"make_wood_pickaxe",11:"make_stone_pickaxe",12:"make_iron_pickaxe",
       13:"make_wood_sword",14:"make_stone_sword",15:"make_iron_sword",16:"eat"}

agent = SGMAgent(rng, D, n_nodes=N_NODES, gamma=0.01)
agent.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES-1)) for i in range(N_NODES)})

env = crafter.Env(); env.reset()
obs, r, t, info = env.step(0)
tiles_vistos = set(); log = []

for step in range(300):
    sem = info["semantic"].flatten().tolist(); inv = info["inventory"]
    pos = tuple(info["player_pos"])
    sv = [float(v) for v in sem[::64]] + [float(inv["health"])/10.0, float(inv["food"])/10.0,
         float(inv["wood"]), float(inv["stone"]), float(inv["iron"])]
    a = agent.step(sv, list(range(17)))
    obs, r, t, info = env.step(a)
    ri = 0.0
    if pos not in tiles_vistos: tiles_vistos.add(pos); ri = REWARD_NOVEDAD
    pain = 0.0
    if r < 0: pain = abs(r)
    elif inv["health"] < 5: pain = 0.1*(5-inv["health"])
    elif inv["food"] < 3: pain = 0.05
    agent.reward(r + ri, pain)
    log.append({"step":step,"a":ACC.get(a,"?"),"pos":list(pos),"hp":inv["health"],
                "food":inv["food"],"nov":ri,"Ea":round(agent.E_acumulado,3),
                "st":agent.status,"d":agent.doubt_count})
    if t: break

cnt = Counter(l['a'] for l in log)
noop_pct = cnt.get('noop',0)/max(1,len(log))*100
print("="*60)
print("exp_SGM_0106_rev2 — Core minimo")
print("="*60)
print(f"Pasos: {step+1} | Tiles: {len(tiles_vistos)} | HP: {inv['health']}")
print(f"Status: {agent.status} | Duda: {agent.doubt_count}")
print(f"NOOP: {noop_pct:.1f}%")
for act,n in cnt.most_common():
    print(f"  {act:20s} {n:3d} ({100*n/len(log):.1f}%)")
print(f"\nCada 30 pasos:")
for l in log[::30]:
    print(f"  p{l['step']:03d}: {l['a']:18s} pos={str(l['pos']):12s} nov={l['nov']:.1f} Ea={l['Ea']:.2f} d={l['d']} st={l['st'][:8]}")
print(f"\nPASS: {noop_pct < 50}")
print(f"{'='*60}")