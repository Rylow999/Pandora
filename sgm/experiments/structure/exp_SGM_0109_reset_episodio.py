#!/usr/bin/env python3
"""
exp_SGM_0109 — Reset episodio: persistencia de omega entre vidas.
El agente vive 3 episodios. Entre episodios se llama reset_episodio()
que mantiene omega pero resetea estado afectivo (E_acum, duda, status).
Hipótesis: el agente mejora su exploración en cada vida porque aprende
de vidas anteriores (omega persistente). NC: comparar contra un agente
que se reinicia completamente entre vidas (omega nuevo cada vez).
"""
import sys, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from sgm.core.sgm_core import SGMAgent
import crafter
from collections import Counter

random.seed(42); rng = random.Random(42)
D=128; N_NODES=64; REWARD_NOV=0.1; N_VIDAS=3
ACC = {0:"noop",1:"move_left",2:"move_right",3:"move_up",4:"move_down",
       5:"do",6:"sleep",7:"place_stone",8:"place_table",9:"place_furnace",
       10:"make_wood_pickaxe",11:"make_stone_pickaxe",12:"make_iron_pickaxe",
       13:"make_wood_sword",14:"make_stone_sword",15:"make_iron_sword",16:"eat"}

def correr_episodio(agent, n_steps=300):
    env = crafter.Env(); env.reset()
    obs,r,t,info = env.step(0)
    tiles=set(); log=[]
    for step in range(n_steps):
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
        log.append({"step":step,"a":ACC.get(a,"?"),"hp":inv["health"],
                    "food":inv["food"],"nov":ri,"Ea":round(agent.E_acumulado,3),
                    "st":agent.status,"d":agent.doubt_count,"pos":list(pos)})
        if t: break
    return log, tiles, inv, step+1

# === AGENTE A: persistencia entre vidas (reset_episodio) ===
rng_a = random.Random(42)
agent_a = SGMAgent(rng_a, D, n_nodes=N_NODES, gamma=0.01)
agent_a.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES-1)) for i in range(N_NODES)})

print("="*70)
print("  exp_SGM_0109 — Reset episodio (persistencia omega entre vidas)")
print("="*70)

resultados_a = []
for vida in range(N_VIDAS):
    log_a, tiles_a, inv_a, pasos_a = correr_episodio(agent_a)
    cnt_a = Counter(l['a'] for l in log_a)
    noop_a = cnt_a.get('noop',0)/max(1,len(log_a))*100
    resultados_a.append({
        "vida": vida, "pasos": pasos_a, "tiles": len(tiles_a),
        "noop_pct": round(noop_a,1), "status": agent_a.status,
        "duda": agent_a.doubt_count, "E_acum": round(agent_a.E_acumulado,3),
        "conexiones": len(agent_a.conn_type),
        "top3": cnt_a.most_common(3),
    })
    print(f"\n  Vida {vida} (PERSISTENTE): {pasos_a} pasos, {len(tiles_a)} tiles, {noop_a:.1f}% noop, "
          f"status={agent_a.status}, d={agent_a.doubt_count}, conn={len(agent_a.conn_type)}")
    for act,n in cnt_a.most_common(3):
        print(f"    {act:20s} {n:3d} ({100*n/len(log_a):.1f}%)")
    agent_a.reset_episodio()

# === AGENTE B (NC): reinicio completo entre vidas ===
rng_b = random.Random(42)
resultados_b = []
for vida in range(N_VIDAS):
    agent_b = SGMAgent(rng_b, D, n_nodes=N_NODES, gamma=0.01)
    agent_b.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES-1)) for i in range(N_NODES)})
    log_b, tiles_b, inv_b, pasos_b = correr_episodio(agent_b)
    cnt_b = Counter(l['a'] for l in log_b)
    noop_b = cnt_b.get('noop',0)/max(1,len(log_b))*100
    resultados_b.append({
        "vida": vida, "pasos": pasos_b, "tiles": len(tiles_b),
        "noop_pct": round(noop_b,1), "status": agent_b.status,
        "duda": agent_b.doubt_count, "E_acum": round(agent_b.E_acumulado,3),
        "conexiones": len(agent_b.conn_type),
        "top3": cnt_b.most_common(3),
    })
    print(f"\n  Vida {vida} (REINICIADO): {pasos_b} pasos, {len(tiles_b)} tiles, {noop_b:.1f}% noop, "
          f"status={agent_b.status}, d={agent_b.doubt_count}, conn={len(agent_b.conn_type)}")
    for act,n in cnt_b.most_common(3):
        print(f"    {act:20s} {n:3d} ({100*n/len(log_b):.1f}%)")

# === COMPARACION ===
print(f"\n{'='*70}")
print("  COMPARACION")
print(f"{'='*70}")
print(f"  {'Vida':<6} {'Persistente':>30} {'Reiniciado':>30}")
for v in range(N_VIDAS):
    a = resultados_a[v]; b = resultados_b[v]
    print(f"  {v:<6} tiles={a['tiles']:3d} noop={a['noop_pct']:5.1f}% conn={a['conexiones']:3d}    "
          f"tiles={b['tiles']:3d} noop={b['noop_pct']:5.1f}% conn={b['conexiones']:3d}")

# Mejora entre vidas 0 y 2
mejora_a_tiles = resultados_a[-1]['tiles'] - resultados_a[0]['tiles']
mejora_b_tiles = resultados_b[-1]['tiles'] - resultados_b[0]['tiles']
print(f"\n  Mejora tiles vida 0->2: Persistente={mejora_a_tiles:+d}, Reiniciado={mejora_b_tiles:+d}")
print(f"  Conexiones acumuladas vidaja 2: P={resultados_a[-1]['conexiones']}, R={resultados_b[-1]['conexiones']}")
print(f"{'='*70}")

# Guardar
import json
out=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "results/results_exp_SGM_0109_reset_episodio.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id":"exp_SGM_0109",
    "experiment_name":"reset_episodio_persistencia",
    "phase":"Auditoria — reset_episodio entre vidas",
    "date":"2026-08-06",
    "hypothesis":"El agente con reset_episodio (omega persistente) acumula conexiones aprendidas entre vidas y explora mas que el agente reiniciado.",
    "config":{"D":D,"N_NODES":N_NODES,"reward_novedad":REWARD_NOV,"n_vidas":N_VIDAS},
    "result":{"persistente":resultados_a,"reiniciado":resultados_b,
              "mejora_tiles_persistente":mejora_a_tiles,
              "mejora_tiles_reiniciado":mejora_b_tiles},
    "script":"experiments/exp_SGM_0109_reset_episodio.py",
    "results_file":"results/results_exp_SGM_0109_reset_episodio.json",
    "variant_of":"exp_SGM_0108",
    "lit_refs":["Implicit memory — procedural memory persists across episodes (Wikipedia)"],
    "notes":"Comparacion A/B: agente con omega persistente vs agente reiniciado. 3 vidas cada uno.",
    "notes_criollo":"Le dimos 3 vidas al agente. En unas mantiene la memoria entre vidas (como recordar lo que aprendiste ayer) y en otras arranca de cero cada vez. Si la memoria ayuda, deberia explorar mas y aprender mas conexiones con cada vida."
}, open(out,"w"), indent=2)
print(f"\n  Guardado en: {out}")
