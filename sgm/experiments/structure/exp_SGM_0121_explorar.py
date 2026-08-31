#!/usr/bin/env python3
"""
exp_SGM_0121 — Instinto de exploracion del desconocido (curiosidad como instinto).
El decoder aprende el modelo del mundo (estado->estado). Alta incertidumbre
(prediction error del mundo) genera inclinacion a MOVERSE hacia lo desconocido —
indiferente a lo que produzca (el bebe al fuego/animales/tierra).

HIPOTESIS (falsable):
  Con el instinto de exploracion, el sistema se movera hacia lo desconocido
  cuando su modelo del mundo falle, explorando mas tiles que el NC (sin el
  instinto de exploracion, solo con el de alimentacion). El sistema aprende a
  moverse bien (no se clava), porque la incertidumbre lo empuja a ir a ver el mundo.

Protocolo:
  A: instinto de alimentacion + instinto de exploracion ACTIVOS.
  NC: solo instinto de alimentacion (exploracion apagada).

Metrica:
  - tiles explorados: A > NC (el instinto de exploracion lo mueve).
  - movimiento: proporcion de acciones move_* > NC.
  - ciclo completo: come, se sacia, y ademas explora (no solo deambula).
"""
import sys, os, random
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm.core.sgm_core import SGMAgent
import crafter

D=128; N_NODES=64
ACC = {0:"noop",1:"move_left",2:"move_right",3:"move_up",4:"move_down",
       5:"do",6:"sleep",7:"place_stone",8:"place_table",9:"place_furnace",
       10:"make_wood_pickaxe",11:"make_stone_pickaxe",12:"make_iron_pickaxe",
       13:"make_wood_sword",14:"make_stone_sword",15:"make_iron_sword",16:"eat"}
MOV = {1,2,3,4}

def correr_vida(agent, usar_exploracion, max_pasos=2000):
    env = crafter.Env(); env.reset()
    obs,r,t,info = env.step(0)
    tiles=set(); log=[]; eat_total=0; hambre=0; mov_total=0; prev_q=None
    for step in range(max_pasos):
        sem=info["semantic"].flatten().tolist(); inv=info["inventory"]
        pos=tuple(info["player_pos"])
        sv=[float(v) for v in sem[::64]]+[float(inv["health"])/10.0,float(inv["food"])/10.0,
           float(inv["wood"]),float(inv["stone"]),float(inv["iron"])]
        # Estado del mundo cuantizado (para el modelo)
        mundo_q = agent.cuantizar_estado(sem)
        a=agent.step(sv,list(range(17)))
        obs,r,t,info=env.step(a)
        # Actualizar modelo del mundo (instinto de exploracion) si esta activo
        if usar_exploracion and prev_q is not None:
            agent.actualizar_modelo_mundo(prev_q, a, mundo_q)
        # Acople grafo=cuerpo + instinto de alimentacion
        agent.actualizar_homeostasis(inv["food"], inv["health"])
        pain = 0.0
        if r < 0: pain = abs(r)
        elif inv["health"] < 5: pain = 0.1*(5-inv["health"])
        elif inv["food"] < 3: pain = 0.05
        agent.reward(0.0, pain)
        if pos not in tiles: tiles.add(pos); agent.reward(0.1, 0.0)
        prev_q = mundo_q
        if a == 16: eat_total += 1
        if inv["food"] < 3: hambre += 1
        if a in MOV: mov_total += 1
        log.append({"step":step,"a":a,"food":float(inv["food"]),"hp":float(inv["health"]),
                    "Vg":round(agent.V_grafo,3),"duda":agent.doubt_count,"status":agent.status,
                    "inc":round(agent.incertidumbre_acum,2)})
        if t:
            muerte={"step":step,"food":float(inv["food"]),"hp":float(inv["health"]),
                    "status":agent.status,"V_grafo_fin":round(agent.V_grafo,3)}
            return log,tiles,muerte,step+1,eat_total,hambre,mov_total
    return log,tiles,None,step+1,eat_total,hambre,mov_total

# A: alimentacion + exploracion ACTIVOS
rng_a = random.Random(42)
ag_a = SGMAgent(rng_a, D, n_nodes=N_NODES, gamma=0.01)
ag_a.set_edges({i: random.sample(range(N_NODES), min(5,N_NODES-1)) for i in range(N_NODES)})
log_a,tiles_a,muerte_a,pasos_a,eat_a,hambre_a,mov_a = correr_vida(ag_a, usar_exploracion=True)
cnt_a = Counter(ACC.get(l['a'],"?") for l in log_a)

# NC: SOLO alimentacion (exploracion APAGADA)
rng_c = random.Random(42)
ag_c = SGMAgent(rng_c, D, n_nodes=N_NODES, gamma=0.01)
ag_c.set_edges({i: random.sample(range(N_NODES), min(5,N_NODES-1)) for i in range(N_NODES)})
# apagar exploracion: umbral altisimo para que nunca se active
ag_c.instinto_explorar_umbral = 9999
log_c,tiles_c,muerte_c,pasos_c,eat_c,hambre_c,mov_c = correr_vida(ag_c, usar_exploracion=False)
cnt_c = Counter(ACC.get(l['a'],"?") for l in log_c)

# Metricas
mov_pct_a = 100*mov_a/max(1,len(log_a))
mov_pct_c = 100*mov_c/max(1,len(log_c))
eat_pct_a = 100*eat_a/max(1,len(log_a))

print("="*70)
print("  exp_SGM_0121 — Instinto de exploracion del desconocido")
print("="*70)
print(f"\n  A (exploracion ACTIVA): {pasos_a}p, {len(tiles_a)} tiles, mov={mov_pct_a:.0f}%, "
      f"eat={eat_a} ({eat_pct_a:.0f}%), hambre={hambre_a}")
print(f"    muerte: {muerte_a}")
for act,n in cnt_a.most_common(5):
    print(f"      {act:18s} {n:3d} ({100*n/len(log_a):.1f}%)")
print(f"\n  NC (exploracion APAGADA): {pasos_c}p, {len(tiles_c)} tiles, mov={mov_pct_c:.0f}%, "
      f"eat={eat_c}, hambre={hambre_c}")
print(f"    muerte: {muerte_c}")
for act,n in cnt_c.most_common(5):
    print(f"      {act:18s} {n:3d} ({100*n/len(log_c):.1f}%)")

# Metricas de exito
print(f"\n{'='*70}")
print("  METRICAS")
print(f"{'='*70}")
pass_explora = len(tiles_a) > len(tiles_c)
pass_se_mueve = mov_pct_a > mov_pct_c
# El ciclo completo: come Y explora (no es puro deambulo ni pura comida)
ciclo_completo = (eat_a > 0) and (len(tiles_a) > len(tiles_c))
print(f"  PASS exploracion (A tiles > NC): {pass_explora} ({len(tiles_a)} vs {len(tiles_c)})")
print(f"  PASS se mueve mas (A mov% > NC): {pass_se_mueve} ({mov_pct_a:.0f}% vs {mov_pct_c:.0f}%)")
print(f"  PASS ciclo completo (come Y explora): {ciclo_completo}")
print(f"{'='*70}")

import json
out=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "results/results_exp_SGM_0121_explorar.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id":"exp_SGM_0121",
    "experiment_name":"instinto_exploracion_desconocido",
    "phase":"Fase 8 - instinto de exploracion (curiosidad como instinto)",
    "date":"2026-08-06",
    "hypothesis":"Con el instinto de exploracion, el sistema se mueve hacia lo desconocido cuando su modelo del mundo falla, explorando mas tiles que el NC (sin el instinto de exploracion).",
    "config":{"D":D,"N_NODES":N_NODES,"instinto_explorar_fuerza":0.4,"instinto_explorar_umbral":3},
    "result":{
        "A_exploracion":{"pasos":pasos_a,"tiles":len(tiles_a),"mov_pct":round(mov_pct_a,1),"eat":eat_a,"hambre":hambre_a,"muerte":muerte_a},
        "NC_sin_exploracion":{"pasos":pasos_c,"tiles":len(tiles_c),"mov_pct":round(mov_pct_c,1),"eat":eat_c,"muerte":muerte_c},
        "pass_explora":pass_explora,"pass_movimiento":pass_se_mueve,"pass_ciclo_completo":ciclo_completo},
    "script":"experiments/exp_SGM_0121_explorar.py",
    "results_file":"results/results_exp_SGM_0121_explorar.json",
    "variant_of":"exp_SGM_0120",
    "lit_refs":["Schmidhuber 1991 - curiosidad como reduccion de incertidumbre","Oudeyer & Kaplan 2007 - exploration","Panksepp SEEKING - explorar lo incierto sin prejuzgar"],
    "notes":"Instinto de exploracion: el decoder aprende el modelo del mundo (estado->estado). Alta incertidumbre genera inclinacion a moverse (autolimitativo: al explorar el modelo aprende y se apaga). Cuestion como instinto, NO reward (diferente a 0117).",
    "notes_criollo":"Le dimos al sistema el mismo impulso del bebe que va a lo desconocido: cuando su modelo del mundo no entiende algo, se siente empujado a ir a verlo — sin importar si va a ser tierra, un animal o el fuego. Al explorar, aprende y el impulso se apaga. Asi aprende a moverse bien: no se queda clavado, va a donde hay misterio."
}, open(out,"w"), indent=2)
print(f"\n  Guardado en: {out}")
