#!/usr/bin/env python3
"""
exp_SGM_0108 — Aristas emergentes del uso (conn_type aprendido por co-ocurrencia).
Las conexiones entre acciones se refuerzan cuando ocurren juntas.
Las aristas se etiquetan como Causal (alta frecuencia) o Functional (baja).
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from sgm.core.sgm_core import SGMAgent
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
print("exp_SGM_0108 — Aristas emergentes del uso")
print("="*60)
print(f"Pasos: {step+1} | Tiles: {len(tiles)} | HP: {inv['health']}")
print(f"Status: {agent.status} | Duda: {agent.doubt_count}")
print(f"NOOP: {noop_pct:.1f}%")
for act,n in cnt.most_common():
    print(f"  {act:20s} {n:3d} ({100*n/len(log):.1f}%)")
print(f"\nConexiones aprendidas: {len(agent.conn_type)}")
causales = sum(1 for v in agent.conn_type.values() if isinstance(v, dict) and v.get("tipo")==1)
print(f"  Causales: {causales}, Funcionales: {len(agent.conn_type)-causales}")
print(f"\nCada 30 pasos:")
for l in log[::30]:
    print(f"  p{l['step']:03d}: {l['a']:18s} pos={str(l['pos']):12s} nov={l['nov']:.1f} Ea={l['Ea']:.2f} d={l['d']} st={l['st'][:8]}")
print(f"\nPASS (noop<50%): {noop_pct < 50}")
print("="*60)

import json, os
out=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "results/results_exp_SGM_0108_aristas_emergentes.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id":"exp_SGM_0108",
    "experiment_name":"aristas_emergentes_uso",
    "phase":"Auditoria — aristas tipadas por co-ocurrencia",
    "date":"2026-08-06",
    "hypothesis":"Las aristas tipadas que emergen del uso (co-ocurrencia de acciones) no interfieren con la exploracion y permiten que el PPR favorezca transiciones frecuentes.",
    "config":{"D":D,"N_NODES":N_NODES,"reward_novedad":REWARD_NOV,"aristas_emergentes":True},
    "result":{"pasos":step+1,"tiles":len(tiles),"noop_pct":round(noop_pct,1),
              "conexiones_aprendidas":len(agent.conn_type),"causales":causales,
              "accion_dominante":cnt.most_common(1)[0] if cnt else ("none",0),
              "status":agent.status,"duda":agent.doubt_count,"pass":noop_pct<50},
    "script":"experiments/exp_SGM_0108_aristas_emergentes.py",
    "results_file":"results/results_exp_SGM_0108_aristas_emergentes.json",
    "variant_of":"exp_SGM_0107",
    "lit_refs":[],
    "notes":"Aristas tipadas aprendidas por co-ocurrencia. Cada vez que el agente hace una transicion A->B, se refuerza la conexion. Si ocurre >5 veces, se vuelve Causal (boost 1.5).",
    "notes_criollo":"Las conexiones entre acciones ahora se aprenden del uso, no se asignan al azar. Si el agente siempre hace A y despues B, esa conexion se refuerza y el PPR la favorece. Es como aprender que 'si mueves la mano izquierda, luego la derecha' — no es una regla, es un patron que el sistema descubre solo."
}, open(out,"w"), indent=2)
print(f"\nGuardado en: {out}")
