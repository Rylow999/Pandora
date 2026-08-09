#!/usr/bin/env python3
"""
exp_SGM_0120 — Instinto de especie autolimitativo (ADN del sustrato).
Resuelve el 0119: el sistema sentia el hambre pero nunca visitaba `eat`.

HIPOTESIS (falsable):
  Con el instinto de alimentacion (empuje proporcional a la carencia, autolimitativo),
  el sistema visitara `eat` en estados de hambre, probando la accion para que la
  experiencia pueda reforzarla. NO se obsesiona: come, se sacia (V_grafo restaura)
  y vuelve a explorar. Comparado con NC (sin instinto), come mas y el ciclo de
  subsistencia (hacer->hambre->comer->volver a hacer) aparece.

Protocolo A/B:
  A: instinto de alimentacion ACTIVO (autolimitativo).
  NC: instinto APAGADO (fuerza=0) -> baseline roto, no visita eat.

Metrica:
  - eat_total > 0 en A (visita la accion que antes nunca tocaba).
  - querer operativo: come con hambre (food bajo -> eat).
  - NO obsesion: eat NO es 100% de acciones (saca y vuelve a explorar/actuar).
  - supervivencia: A vive mas que NC.
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

def correr_vida(agent, usar_instinto, max_pasos=2000):
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
        # Acople directo grafo=cuerpo (siempre activo)
        agent.actualizar_homeostasis(inv["food"], inv["health"])
        # Reward SOLO intrinseco (sin reward externo por comida) para aislar el instinto
        pain = 0.0
        if r < 0: pain = abs(r)
        elif inv["health"] < 5: pain = 0.1*(5-inv["health"])
        elif inv["food"] < 3: pain = 0.05
        agent.reward(0.0, pain)
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

# A: instinto ACTIVO
rng_a = random.Random(42)
ag_a = SGMAgent(rng_a, D, n_nodes=N_NODES, gamma=0.01)
ag_a.set_edges({i: random.sample(range(N_NODES), min(5,N_NODES-1)) for i in range(N_NODES)})
log_a,tiles_a,muerte_a,pasos_a,eat_a,hambre_a,echa_a = correr_vida(ag_a, usar_instinto=True)
cnt_a = Counter(ACC.get(l['a'],"?") for l in log_a)

# NC: instinto APAGADO (fuerza base 0)
rng_c = random.Random(42)
ag_c = SGMAgent(rng_c, D, n_nodes=N_NODES, gamma=0.01)
ag_c.set_edges({i: random.sample(range(N_NODES), min(5,N_NODES-1)) for i in range(N_NODES)})
ag_c.instinto_fuerza_base = 0.0  # apagar instinto
log_c,tiles_c,muerte_c,pasos_c,eat_c,hambre_c,echa_c = correr_vida(ag_c, usar_instinto=False)
cnt_c = Counter(ACC.get(l['a'],"?") for l in log_c)

# Reporte
noop_a = 100*cnt_a.get('noop',0)/max(1,len(log_a))
noop_c = 100*cnt_c.get('noop',0)/max(1,len(log_c))
eat_pct_a = 100*eat_a/max(1,len(log_a))
eat_pct_c = 100*eat_c/max(1,len(log_c))
querer_a = (echa_a/max(1,hambre_a)>0.5) if hambre_a>0 else False
querer_c = (echa_c/max(1,hambre_c)>0.5) if hambre_c>0 else False

print("="*70)
print("  exp_SGM_0120 — Instinto de especie autolimitativo")
print("="*70)
print(f"\n  A (instinto ACTIVO): {pasos_a}p, {len(tiles_a)} tiles, noop={noop_a:.0f}%, "
      f"eat={eat_a} ({eat_pct_a:.0f}%), eat_con_hambre={echa_a}/{hambre_a}, querer={querer_a}")
print(f"    muerte: {muerte_a}")
for act,n in cnt_a.most_common(5):
    print(f"      {act:18s} {n:3d} ({100*n/len(log_a):.1f}%)")
print(f"\n  NC (instinto APAGADO): {pasos_c}p, {len(tiles_c)} tiles, noop={noop_c:.0f}%, "
      f"eat={eat_c} ({eat_pct_c:.0f}%), eat_con_hambre={echa_c}/{hambre_c}, querer={querer_c}")
print(f"    muerte: {muerte_c}")
for act,n in cnt_c.most_common(5):
    print(f"      {act:18s} {n:3d} ({100*n/len(log_c):.1f}%)")

# METRICAS DE EXITO
print(f"\n{'='*70}")
print("  METRICAS")
print(f"{'='*70}")
pass_come = eat_a > 0
pass_querer = querer_a
no_obsesion = eat_pct_a < 90  # come pero NO es 100% (saca y vuelve a explorar)
pass_vive = pasos_a > pasos_c
print(f"  PASS come (A come > 0): {pass_come} ({eat_a} eats)")
print(f"  PASS querer operativo (come con hambre): {pass_querer}")
print(f"  PASS NO obsesion (eat < 90%): {no_obsesion} ({eat_pct_a:.0f}%)")
print(f"  PASS supervivencia (A>NC): {pass_vive} ({pasos_a} vs {pasos_c})")
print(f"{'='*70}")

import json
out=os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/results/results_exp_SGM_0120_instinto.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id":"exp_SGM_0120",
    "experiment_name":"instinto_especie_autolimitativo",
    "phase":"Fase 8 - instinto de especie (ADN del sustrato)",
    "date":"2026-08-06",
    "hypothesis":"Con el instinto autolimitativo (empuje proporcional a la carencia), el sistema visita eat, come, se sacia y vuelve a explorar (no se obsesiona). Comparado con NC, come mas y el ciclo de subsistencia aparece.",
    "config":{"D":D,"N_NODES":N_NODES,"instinto_fuerza_base":0.5,"instinto_umbral_carencia":0.3},
    "result":{
        "A_instinto":{"pasos":pasos_a,"tiles":len(tiles_a),"noop":round(noop_a,1),"eat":eat_a,"eat_pct":round(eat_pct_a,1),"eat_con_hambre":echa_a,"hambre":hambre_a,"querer":querer_a,"muerte":muerte_a},
        "NC_sin_instinto":{"pasos":pasos_c,"tiles":len(tiles_c),"noop":round(noop_c,1),"eat":eat_c,"eat_pct":round(eat_pct_c,1),"eat_con_hambre":echa_c,"querer":querer_c},
        "pass_come":pass_come,"pass_querer":pass_querer,"pass_no_obsesion":no_obsesion,"pass_supervivencia":pass_vive},
    "script":"experiments/exp_SGM_0120_instinto.py",
    "results_file":"results/results_exp_SGM_0120_instinto.json",
    "variant_of":"exp_SGM_0119",
    "lit_refs":["Reflejo de succion innato (News24/Stanford/Cleveland)","Rooting reflex (StatPearls/NCBI)","Olds & Milner 1954 - reward intrinseco sin ancla colapsa","Holtzman 2019 - neural text degeneration (obsesion/loop)"],
    "notes":"Instinto autolimitativo: fuerza del empuje a comer = base*(umbral-V_grafo), solo en carencia. Al saciarse se apaga (evita obsesion). NO pre-juzga el resultado (lo da la experiencia via refuerzo accion->nodo0). Es ADN del sustrato (reflejo de especie), no hardcode del disenador.",
    "notes_criollo":"Le dimos al sistema el instinto del bebe: cuando el cuerpo se degrada por hambre, se siente empujado a probar comer. Pero el empuje es proporcional a la necesidad — cuando come y se sacia, el impulso se apaga y puede seguir explorando. Asi no se obsesiona con la vitalidad alta: come cuando lo necesita, no hasta reventar. Y que comer sea bueno o malo lo descubre el mismo por la experiencia."
}, open(out,"w"), indent=2)
print(f"\n  Guardado en: {out}")