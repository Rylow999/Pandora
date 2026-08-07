#!/usr/bin/env python3
"""
exp_SGM_0107 — omega_root SIN bonus de afinidad.
Solo piso de vitalidad 0.5. Identidad emerge de recurrencia, no de boost.
NC: comparar con exp_SGM_0106_rev2 (sin omega_root). Si el comportamiento es
similar, la raiz sin bonus no interfiere.
"""
import sys, os, random
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"))
from sgm_core import SGMAgent
import crafter
from collections import Counter

random.seed(42); rng = random.Random(42)
D=128; N_NODES=64; REWARD_NOV=0.1
ACC = {0:"noop",1:"move_left",2:"move_right",3:"move_up",4:"move_down",
       5:"do",6:"sleep",7:"place_stone",8:"place_table",9:"place_furnace",
       10:"make_wood_pickaxe",11:"make_stone_pickaxe",12:"make_iron_pickaxe",
       13:"make_wood_sword",14:"make_stone_sword",15:"make_iron_sword",16:"eat"}

agent = SGMAgent(rng, D, n_nodes=N_NODES, gamma=0.01)
agent.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES-1)) for i in range(N_NODES)})

env = crafter.Env(); env.reset()
obs,r,t,info = env.step(0)
tiles=set(); log=[]

for step in range(300):
    sem=info["semantic"].flatten().tolist(); inv=info["inventory"]
    pos=tuple(info["player_pos"])
    sv=[float(v) for v in sem[::64]]+[float(inv["health"])/10.0,float(inv["food"])/10.0,
       float(inv["wood"]),float(inv["stone"]),float(inv["iron"])]
    a=agent.step(sv,list(range(17)))
    obs,r,t,info=env.step(a)
    ri=0.0
    if pos not in tiles: tiles.add(pos); ri=REWARD_NOV
    pain=0.0
    if r<0: pain=abs(r)
    elif inv["health"]<5: pain=0.1*(5-inv["health"])
    elif inv["food"]<3: pain=0.05
    agent.reward(r+ri, pain)
    log.append({"step":step,"a":ACC.get(a,"?"),"pos":list(pos),"hp":inv["health"],
                "food":inv["food"],"nov":ri,"Ea":round(agent.E_acumulado,3),
                "st":agent.status,"d":agent.doubt_count})
    if t: break

cnt=Counter(l['a'] for l in log)
noop_pct=cnt.get('noop',0)/max(1,len(log))*100
print("="*60)
print("exp_SGM_0107 — omega_root (sin bonus)")
print("="*60)
print(f"Pasos: {step+1} | Tiles: {len(tiles)} | HP: {inv['health']}")
print(f"Status: {agent.status} | Duda: {agent.doubt_count}")
print(f"NOOP: {noop_pct:.1f}%")
for act,n in cnt.most_common():
    print(f"  {act:20s} {n:3d} ({100*n/len(log):.1f}%)")
print(f"\nCada 30 pasos:")
for l in log[::30]:
    print(f"  p{l['step']:03d}: {l['a']:18s} pos={str(l['pos']):12s} nov={l['nov']:.1f} Ea={l['Ea']:.2f} d={l['d']} st={l['st'][:8]}")
print(f"\nPASS (noop<50%): {noop_pct < 50}")
print("="*60)

import json, os
out=os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/results/results_exp_SGM_0107_omega_root_nobonus.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
output={
    "experiment_id":"exp_SGM_0107",
    "experiment_name":"omega_root_sin_bonus",
    "phase":"Auditoria — omega_root",
    "date":"2026-08-06",
    "hypothesis":"omega_root con piso de vitalidad 0.5 pero SIN bonus de afinidad no interfiere con el comportamiento exploratorio del agente.",
    "config":{"D":D,"N_NODES":N_NODES,"reward_novedad":REWARD_NOV,"omega_root":True,"bonus_afinidad":0.0,"piso_raiz":0.5},
    "result":{"pasos":step+1,"tiles":len(tiles),"noop_pct":round(noop_pct,1),"accion_dominante":cnt.most_common(1)[0] if cnt else ("none",0),"status":agent.status,"duda":agent.doubt_count,"pass":noop_pct<50},
    "script":"experiments/exp_SGM_0107_omega_root_nobonus.py",
    "results_file":"results/results_exp_SGM_0107_omega_root_nobonus.json",
    "variant_of":"exp_SGM_0106_rev2",
    "lit_refs":[],
    "notes":"omega_root agregado SIN bonus de afinidad. Solo piso de vitalidad 0.5. Si el agente se comporta igual que sin omega_root, la raiz sin bonus no interfiere.",
    "notes_criollo":"Le pusimos un yo al sistema, pero sin darle ventaja. El yo solo existe, no empuja la balanza. Si el agente sigue moviendose como antes, significa que la identidad puede coexistir con la exploracion sin necesidad de un boost artificial."
}
with open(out,"w") as f: json.dump(output,f,indent=2)
print(f"\nGuardado en: {out}")