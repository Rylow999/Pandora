#!/usr/bin/env python3
"""
exp_SGM_0111 — Poda de aristas + reset_episodio entre vidas.
Ahora las aristas no usadas se debilitan (strength decae con gamma*2)
y se eliminan si strength < 0.05. Hipotesis: con poda, la persistencia
entre vidas ya no es toxica — el agente mantiene lo que sirve y olvida
lo que no.
NC: comparar contra agente reiniciado (sin memoria entre vidas).
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

# === AGENTE A: persistente con poda ===
rng_a = random.Random(42)
agent_a = SGMAgent(rng_a, D, n_nodes=N_NODES, gamma=0.01)
agent_a.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES-1)) for i in range(N_NODES)})

print("="*70)
print("  exp_SGM_0111 — Poda de aristas + reset_episodio")
print("="*70)

resultados_a = []
for vida in range(N_VIDAS):
    log_a, tiles_a, inv_a, pasos_a = correr_episodio(agent_a)
    cnt_a = Counter(l['a'] for l in log_a)
    noop_a = cnt_a.get('noop',0)/max(1,len(log_a))*100
    variedad_a = len(cnt_a)
    # Contar aristas vivas vs podadas
    vivas = sum(1 for v in agent_a.conn_type.values() if v.get("strength", 0) > 0.05)
    print(f"\n  Vida {vida} (PERSISTENTE+PODA): {pasos_a}p, {len(tiles_a)}t, {noop_a:.1f}%noop, "
          f"var={variedad_a}, conn={len(agent_a.conn_type)}, vivas={vivas}, st={agent_a.status}")
    for act,n in cnt_a.most_common(3):
        print(f"    {act:20s} {n:3d} ({100*n/len(log_a):.1f}%)")
    resultados_a.append({"vida":vida,"pasos":pasos_a,"tiles":len(tiles_a),
        "noop":round(noop_a,1),"variedad":variedad_a,"conn":len(agent_a.conn_type),"vivas":vivas})
    agent_a.reset_episodio()

# === AGENTE B (NC): reiniciado cada vida ===
rng_b = random.Random(42)
resultados_b = []
for vida in range(N_VIDAS):
    agent_b = SGMAgent(rng_b, D, n_nodes=N_NODES, gamma=0.01)
    agent_b.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES-1)) for i in range(N_NODES)})
    log_b, tiles_b, inv_b, pasos_b = correr_episodio(agent_b)
    cnt_b = Counter(l['a'] for l in log_b)
    noop_b = cnt_b.get('noop',0)/max(1,len(log_b))*100
    variedad_b = len(cnt_b)
    print(f"\n  Vida {vida} (REINICIADO): {pasos_b}p, {len(tiles_b)}t, {noop_b:.1f}%noop, "
          f"var={variedad_b}, conn={len(agent_b.conn_type)}, st={agent_b.status}")
    for act,n in cnt_b.most_common(3):
        print(f"    {act:20s} {n:3d} ({100*n/len(log_b):.1f}%)")
    resultados_b.append({"vida":vida,"pasos":pasos_b,"tiles":len(tiles_b),
        "noop":round(noop_b,1),"variedad":variedad_b,"conn":len(agent_b.conn_type)})

# === COMPARACION ===
print(f"\n{'='*70}")
print("  COMPARACION")
print(f"{'='*70}")
print(f"  {'Vida':<6} {'Persistente+Poda':>35} {'Reiniciado':>25}")
for v in range(N_VIDAS):
    a = resultados_a[v]; b = resultados_b[v]
    print(f"  {v:<6} tiles={a['tiles']:3d} noop={a['noop']:5.1f}% var={a['variedad']} conn={a['conn']:3d}    "
          f"tiles={b['tiles']:3d} noop={b['noop']:5.1f}% var={b['variedad']}")
mejora_tiles_a = resultados_a[-1]['tiles'] - resultados_a[0]['tiles']
mejora_tiles_b = resultados_b[-1]['tiles'] - resultados_b[0]['tiles']
print(f"\n  Mejora tiles vida 0->2: P+Poda={mejora_tiles_a:+d}, Reiniciado={mejora_tiles_b:+d}")
pass_test = mejora_tiles_a >= 0 and resultados_a[-1]['noop'] < 50
print(f"  PASS (poda hace persistencia util): {pass_test}")
print(f"{'='*70}")

import json
out=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "results/results_exp_SGM_0111_poda_aristas.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id":"exp_SGM_0111",
    "experiment_name":"poda_aristas_reset_episodio",
    "phase":"Auditoria — poda de aristas + reset entre vidas",
    "date":"2026-08-06",
    "hypothesis":"Con poda de aristas (strength decae, se eliminan si <0.05), la persistencia de omega entre vidas deja de ser toxica y el agente mejora o mantiene su exploracion entre vidas.",
    "config":{"D":D,"N_NODES":N_NODES,"n_vidas":N_VIDAS,"poda":True,"gamma":0.01},
    "result":{"persistente_poda":resultados_a,"reiniciado":resultados_b,
              "mejora_tiles_poda":mejora_tiles_a,"mejora_tiles_reiniciado":mejora_tiles_b,"pass":pass_test},
    "script":"experiments/exp_SGM_0111_poda_aristas.py",
    "results_file":"results/results_exp_SGM_0111_poda_aristas.json",
    "variant_of":"exp_SGM_0109",
    "lit_refs":["Synaptic pruning — unused connections weaken (Hebbian reversal)"],
    "notes":"Aristas con strength continuo que decae con gamma*2. Si strength<0.05 se eliminan. Refrescar al usar (+0.2). Comparacion A/B: persistente con poda vs reiniciado.",
    "notes_criollo":"Las conexiones que el agente no usa se debilitan solas, como un camino que se tapa si nadie lo transita. Si nadie lo usa por suficiente tiempo, desaparece. Esto deberia hacer que la memoria entre vidas ya no sea toxica — el agente recuerda lo que sirve y olvida lo que no."
}, open(out,"w"), indent=2)
print(f"\n  Guardado en: {out}")
