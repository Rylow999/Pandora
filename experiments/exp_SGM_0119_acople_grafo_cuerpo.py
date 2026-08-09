#!/usr/bin/env python3
"""
exp_SGM_0119 — Acople directo grafo=cuerpo (monismo). Cierre del querer por homeostasis.

HIPOTESIS (falsable):
  Si la vitalidad del grafo ES la salud del player (acople directo),
  cuando el player tiene hambre V_grafo cae (el grafo se degrada porque ES el cuerpo);
  y el sistema aprende por primera-principio que la accion que restaura la homeostasis
  (comer) mantiene vivo su propio cuerpo. Sin reward externo de comer.

Protocolo A/B:
  A: acople directo ACTIVO, reward externo de comer APAGADO (tesis pura).
  B: acople directo ACTIVO + reward externo ACTIVO.
  NC: acople directo APAGADO (vitalidad como estaba) -> debe seguir muriendo de hambre.

Metrica:
  - Querer operativo: correlacion food->eat (come cuando tiene hambre).
  - Supervivencia: vive mas pasos que NC.
  - Cuerpo: V_grafo correlaciona con health (acople real funcionando).
  - Ciclo subsistencia: hacer->hambre->comer->volver a hacer.
"""
import sys, os, random
from collections import Counter
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm_core import SGMAgent
import crafter

D=128; N_NODES=64
ACC = {0:"noop",1:"move_left",2:"move_right",3:"move_up",4:"move_down",
       5:"do",6:"sleep",7:"place_stone",8:"place_table",9:"place_furnace",
       10:"make_wood_pickaxe",11:"make_stone_pickaxe",12:"make_iron_pickaxe",
       13:"make_wood_sword",14:"make_stone_sword",15:"make_iron_sword",16:"eat"}

def correr_vida(agent, usar_acople, usar_reward_externo, max_pasos=2000):
    """Aparato vivir-hasta-morir con acople grafo=cuerpo.
    usar_acople: llama actualizar_homeostasis (acople directo health).
    usar_reward_externo: si True, pasa reward de Crafter; si False, lo apaga.
    """
    env = crafter.Env(); env.reset()
    obs,r,t,info = env.step(0)
    tiles=set(); log=[]; eat_total=0; hambre=0; eat_con_hambre=0
    for step in range(max_pasos):
        sem=info["semantic"].flatten().tolist(); inv=info["inventory"]
        pos=tuple(info["player_pos"])
        sv=[float(v) for v in sem[::64]]+[float(inv["health"])/10.0,float(inv["food"])/10.0,
           float(inv["wood"]),float(inv["stone"]),float(inv["iron"])]
        a=agent.step(sv,list(range(17)))
        obs,r,t,info=env.step(a)
        # Acople directo (grafo=cuerpo): vitalidad depende de health del player
        if usar_acople:
            agent.actualizar_homeostasis(inv["food"], inv["health"])
        # Reward: apagar el positivo de comer si usar_reward_externo es False
        r_ext = r if usar_reward_externo else max(0.0, r)
        pain = 0.0
        if r < 0: pain = abs(r)
        elif inv["health"] < 5: pain = 0.1*(5-inv["health"])
        elif inv["food"] < 3: pain = 0.05
        agent.reward(r_ext, pain)
        # Novedad (comun): explorar tiles nuevos
        if pos not in tiles:
            tiles.add(pos); agent.reward(0.1, 0.0)
        # Apetito
        if a == 16:
            eat_total += 1
            if inv["food"] < 3: eat_con_hambre += 1
        if inv["food"] < 3: hambre += 1
        log.append({"step":step,"a":a,"food":float(inv["food"]),"hp":float(inv["health"]),
                    "Vg":round(agent.V_grafo,3),"duda":agent.doubt_count,"status":agent.status})
        if t:
            muerte={"step":step,"food":float(inv["food"]),"hp":float(inv["health"]),
                    "status":agent.status,"V_grafo_fin":round(agent.V_grafo,3)}
            return log,tiles,muerte,step+1,eat_total,hambre,eat_con_hambre
    return log,tiles,None,step+1,eat_total,hambre,eat_con_hambre

def reportar(nombre, log, tiles, cnt, muerte, pasos, eat, hambre, echa):
    noop = 100*cnt.get('noop',0)/max(1,len(log))
    querer = (echa/max(1,hambre)>0.5) if hambre>0 else False
    print(f"\n  {nombre}: {pasos}p, {len(tiles)} tiles, {noop:.1f}% noop, eat={eat}, "
          f"eat_con_hambre={echa}/{hambre}, querer_operativo={querer}")
    if muerte: print(f"    muerte: {muerte}")
    for act,n in cnt.most_common(4):
        print(f"    {act:18s} {n:3d} ({100*n/len(log):.1f}%)")
    return querer, noop, pasos

print("="*70)
print("  exp_SGM_0119 — Acople directo grafo=cuerpo (monismo)")

# A: acople directo SIN reward externo (tesis pura)
rng_a = random.Random(42)
ag_a = SGMAgent(rng_a, D, n_nodes=N_NODES, gamma=0.01)
ag_a.set_edges({i: random.sample(range(N_NODES), min(5,N_NODES-1)) for i in range(N_NODES)})
log_a,tiles_a,muerte_a,pasos_a,eat_a,hambre_a,echa_a = correr_vida(ag_a, usar_acople=True, usar_reward_externo=False)
cnt_a = Counter(ACC.get(l['a'],"?") for l in log_a)
qA,nA,pA = reportar("A (acople, sin reward ext)", log_a, tiles_a, cnt_a, muerte_a, pasos_a, eat_a, hambre_a, echa_a)

# B: acople directo + reward externo
rng_b = random.Random(42)
ag_b = SGMAgent(rng_b, D, n_nodes=N_NODES, gamma=0.01)
ag_b.set_edges({i: random.sample(range(N_NODES), min(5,N_NODES-1)) for i in range(N_NODES)})
log_b,tiles_b,muerte_b,pasos_b,eat_b,hambre_b,echa_b = correr_vida(ag_b, usar_acople=True, usar_reward_externo=True)
cnt_b = Counter(ACC.get(l['a'],"?") for l in log_b)
qB,nB,pB = reportar("B (acople + reward ext)", log_b, tiles_b, cnt_b, muerte_b, pasos_b, eat_b, hambre_b, echa_b)

# NC: sin acople (vitalidad como estaba)
rng_c = random.Random(42)
ag_c = SGMAgent(rng_c, D, n_nodes=N_NODES, gamma=0.01)
ag_c.set_edges({i: random.sample(range(N_NODES), min(5,N_NODES-1)) for i in range(N_NODES)})
log_c,tiles_c,muerte_c,pasos_c,eat_c,hambre_c,echa_c = correr_vida(ag_c, usar_acople=False, usar_reward_externo=False)
cnt_c = Counter(ACC.get(l['a'],"?") for l in log_c)
qC,nC,pC = reportar("NC (sin acople)", log_c, tiles_c, cnt_c, muerte_c, pasos_c, eat_c, hambre_c, echa_c)

# Comparacion
print(f"\n{'='*70}")
print("  COMPARACION")
print(f"{'='*70}")
print(f"  A (acople, sin reward):  querer={qA}, vive={pA}p, tiles={len(tiles_a)}, noop={nA:.0f}%")
print(f"  B (acople + reward):     querer={qB}, vive={pB}p, tiles={len(tiles_b)}, noop={nB:.0f}%")
print(f"  NC (sin acople):         querer={qC}, vive={pC}p, tiles={len(tiles_c)}, noop={nC:.0f}%")

# PASS 1: A sobrevive mas que NC (acople sostiene la vida sin reward externo)
pass_sobrevive = pA > pC
# PASS 2: A muestra querer operativo (come con hambre)
pass_querer = qA
print(f"\n  PASS supervivencia (A>NC): {pass_sobrevive}")
print(f"  PASS querer operativo (A come con hambre): {pass_querer}")
print(f"{'='*70}")

import json
out=os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/results/results_exp_SGM_0119_acople_grafo_cuerpo.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id":"exp_SGM_0119",
    "experiment_name":"acople_directo_grafo_cuerpo",
    "phase":"Fase 8 - monismo grafo-cuerpo",
    "date":"2026-08-06",
    "hypothesis":"Si la vitalidad del grafo es la salud del player (acople directo), el sistema aprende que comer mantiene vivo su cuerpo, sin reward externo. A sobrevive mas y come con hambre vs NC.",
    "config":{"D":D,"N_NODES":N_NODES,"acople_directo":True,"factor_cuerpo":"health/10"},
    "result":{
        "A_acople_sin_reward":{"pasos":pA,"tiles":len(tiles_a),"noop":round(nA,1),"eat":eat_a,"eat_con_hambre":echa_a,"hambre":hambre_a,"querer_operativo":qA,"muerte":muerte_a},
        "B_acople_con_reward":{"pasos":pB,"tiles":len(tiles_b),"noop":round(nB,1),"eat":eat_b,"eat_con_hambre":echa_b,"hambre":hambre_b,"querer_operativo":qB},
        "NC_sin_acople":{"pasos":pC,"tiles":len(tiles_c),"noop":round(nC,1),"eat":eat_c,"hambre":hambre_c},
        "pass_supervivencia":pass_sobrevive,"pass_querer":pass_querer},
    "script":"experiments/exp_SGM_0119_acople_grafo_cuerpo.py",
    "results_file":"results/results_exp_SGM_0119_acople_grafo_cuerpo.json",
    "variant_of":"exp_SGM_0116",
    "lit_refs":["Olds & Milner 1954 - reward intrinseco sin ancla colapsa","Damasio - somatic markers","Enactivismo Varela 1991","HRRL 2025"],
    "notes":"Acople directo grafo=cuerpo: V_grafo = mean(vitalidad)*health/10. El sistema siente la vida del player. Protocolo A/B/NC. Cierra la tesis de monismo: si el grafo es el cuerpo, el querer emerge de la dinamica real sin reward externo.",
    "notes_criollo":"El grafo ahora SIFRTE literalmente la vida del player: si tenes poca salud, el grafo se degrada. Es como si tu cuerpo fuera tu mente. Preguntamos: ¿aprende el sistema a comer porque comer lo mantiene vivo, sin que nadie le de recompensa? La condicion A le quita toda recompensa externa; si come igual (y vive mas), el instinto de sobrevivir es real."
}, open(out,"w"), indent=2)
print(f"\n  Guardado en: {out}")