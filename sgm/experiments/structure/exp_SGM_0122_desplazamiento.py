#!/usr/bin/env python3
"""
exp_SGM_0122 — Instinto de desplazamiento con razon (reconocimiento del desplazamiento).
CONTEXTO: exp_SGM_0121 FAIL (mov=0%). El instinto de exploracion empujaba a moverse por
curiosidad/incertidumbre, pero el sistema estaba clavado en eat+noop+make_* porque esas
acciones locales eran atractores del PPR. Diagnostico (Luciano): sistema "hipostatico" —
siente hambre pero solo responde con acciones locales, no usa su cuerpo para buscar comida/huir.

DISEÑO (en sgm_core.py, ya aplicado y verificado):
  El movimiento gana fuerza NO por curiosidad sino porque QUEDARSE NO FUNCIONA.
  Cuando hay carencia grave (V_grafo < devaluar_umbral) Y la ultima accion fue comer
  (y no resolvio), se DEVALÚAN las acciones locales que no funcionan (score -= 0.4)
  y el movimiento gana peso (score += 0.6). El cuerpo se mueve porque quedarse es inutil.

HIPOTESIS (falsable):
  Con el instinto de desplazamiento, cuando la carencia grave persiste tras comer,
  el sistema devalua las acciones locales que no resuelven y SE MUEVE (mov_total > 0),
  explorando mas tiles y (criterio fuerte) viviendo mas que el NC. El movimiento esta
  ANCLADO a la carencia (solo se dispara con V_grafo < umbral y tras comer sin exito),
  NO es deambular perpetuo: si se sacia, se apaga y vuelve a actuar localmente.

Protocolo A/B:
  A: instinto de alimentacion + instinto de desplazamiento ACTIVOS.
  NC: solo instinto de alimentacion (desplazamiento APAGADO -> 0121 repechaje, hipostatico).

Metricas:
  - mov_total > 0 en A (el cuerpo por fin se mueve cuando quedarse no funciona).
  - tiles explorados: A > NC (si se mueve, ve mundo nuevo).
  - supervivencia: A > NC (buscar donde hay recurso > quedarse a morir).
  - NO deambulo perpetuo: la fraccion de movimiento NO domina la vida (el sistema
    tambien sigue comiendo y actuando localmente cuando no esta en carencia grave).
  - querer operativo de comer se mantiene (no se pierde lo ganado en 0120).
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

def correr_vida(agent, usar_desplazamiento, usar_alimentacion=True, max_pasos=2000):
    env = crafter.Env(); env.reset()
    obs,r,t,info = env.step(0)
    tiles=set(); log=[]; eat_total=0; hambre=0; eat_con_hambre=0; mov_total=0
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
        if a in MOV: mov_total += 1
        log.append({"step":step,"a":a,"food":float(inv["food"]),"hp":float(inv["health"]),
                    "Vg":round(agent.V_grafo,3),"duda":agent.doubt_count,"status":agent.status,
                    "nec_insat":agent.necesidad_insatisfecha})
        if t:
            muerte={"step":step,"food":float(inv["food"]),"hp":float(inv["health"]),
                    "status":agent.status,"V_grafo_fin":round(agent.V_grafo,3)}
            return log,tiles,muerte,step+1,eat_total,hambre,eat_con_hambre,mov_total
    return log,tiles,None,step+1,eat_total,hambre,eat_con_hambre,mov_total

# A: alimentacion + desplazamiento ACTIVOS
rng_a = random.Random(42)
ag_a = SGMAgent(rng_a, D, n_nodes=N_NODES, gamma=0.01)
ag_a.set_edges({i: random.sample(range(N_NODES), min(5,N_NODES-1)) for i in range(N_NODES)})
log_a,tiles_a,muerte_a,pasos_a,eat_a,hambre_a,echa_a,mov_a = correr_vida(ag_a, usar_desplazamiento=True)
cnt_a = Counter(ACC.get(l['a'],"?") for l in log_a)

# NC: SOLO alimentacion (desplazamiento APAGADO via umbral altisimo => nunca se activa)
rng_c = random.Random(42)
ag_c = SGMAgent(rng_c, D, n_nodes=N_NODES, gamma=0.01)
ag_c.set_edges({i: random.sample(range(N_NODES), min(5,N_NODES-1)) for i in range(N_NODES)})
ag_c.devaluar_umbral = 0.0  # solo se activaria con V_grafo<0 (imposible) => desplazamiento apagado
log_c,tiles_c,muerte_c,pasos_c,eat_c,hambre_c,echa_c,mov_c = correr_vida(ag_c, usar_desplazamiento=False)
cnt_c = Counter(ACC.get(l['a'],"?") for l in log_c)

# Reporte
noop_a = 100*cnt_a.get('noop',0)/max(1,len(log_a))
noop_c = 100*cnt_c.get('noop',0)/max(1,len(log_c))
eat_pct_a = 100*eat_a/max(1,len(log_a))
mov_pct_a = 100*mov_a/max(1,len(log_a))
mov_pct_c = 100*mov_c/max(1,len(log_c))
querer_a = (echa_a/max(1,hambre_a)>0.5) if hambre_a>0 else False
querer_c = (echa_c/max(1,hambre_c)>0.5) if hambre_c>0 else False
# Fraccion de la vida en la que el desplazamiento se disparo (carecencia grave + comer fallo)
nec_insat_a = sum(1 for l in log_a if l["nec_insat"])
nec_insat_pct_a = 100*nec_insat_a/max(1,len(log_a))

print("="*70)
print("  exp_SGM_0122 — Instinto de desplazamiento con razon")
print("="*70)
print(f"\n  A (desplazamiento ACTIVO): {pasos_a}p, {len(tiles_a)} tiles, mov={mov_pct_a:.0f}%, "
      f"eat={eat_a} ({eat_pct_a:.0f}%), querer={querer_a}, noop={noop_a:.0f}%")
print(f"    carencia-insatisfecha disparada: {nec_insat_a} steps ({nec_insat_pct_a:.0f}%)")
print(f"    muerte: {muerte_a}")
for act,n in cnt_a.most_common(6):
    print(f"      {act:18s} {n:3d} ({100*n/len(log_a):.1f}%)")
print(f"\n  NC (desplazamiento APAGADO): {pasos_c}p, {len(tiles_c)} tiles, mov={mov_pct_c:.0f}%, "
      f"eat={eat_c}, querer={querer_c}, noop={noop_c:.0f}%")
print(f"    muerte: {muerte_c}")
for act,n in cnt_c.most_common(6):
    print(f"      {act:18s} {n:3d} ({100*n/len(log_c):.1f}%)")

# METRICAS DE EXITO
print(f"\n{'='*70}")
print("  METRICAS")
print(f"{'='*70}")
pass_se_mueve = mov_a > 0  # el cuerpo por fin se mueve (0121 fallo con mov=0)
pass_explora = len(tiles_a) > len(tiles_c)
pass_vive = pasos_a > pasos_c
# NO deambulo perpetuo: el movimiento no domina la vida (si domina, es solo "huir" sin razon)
no_deambulo = mov_pct_a < 60
# Mantiene el querer operativo de comer (no perdio lo ganado en 0120)
mantiene_querer = querer_a
print(f"  PASS se mueve (mov_total A > 0): {pass_se_mueve} ({mov_a} moves)")
print(f"  PASS explora (A tiles > NC): {pass_explora} ({len(tiles_a)} vs {len(tiles_c)})")
print(f"  PASS supervivencia (A>NC): {pass_vive} ({pasos_a} vs {pasos_c})")
print(f"  PASS no deambulo (mov < 60%): {no_deambulo} ({mov_pct_a:.0f}%)")
print(f"  PASS mantiene querer de comer: {mantiene_querer}")
print(f"{'='*70}")

import json
out=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "results/results_exp_SGM_0122_desplazamiento.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id":"exp_SGM_0122",
    "experiment_name":"instinto_desplazamiento_con_razon",
    "phase":"Fase 8 - instinto de desplazamiento (reconocimiento del desplazamiento)",
    "date":"2026-08-09",
    "hypothesis":"Con el instinto de desplazamiento, cuando la carencia grave persiste tras comer, el sistema devalua las acciones locales que no resuelven (score-=devaluar_fuerza) y se mueve (mov_total>0, score+=instinto_desplazar_fuerza), explorando mas tiles y viviendo mas que el NC(sin desplazamiento, solo alimentacion). El movimiento esta anclado a la carencia, no es deambulo perpetuo: si se sacia se apaga (autolimitativo) y vuelve a actuar localmente, y mantiene el querer de comer ganado en 0120.",
    "config":{"D":D,"N_NODES":N_NODES,"instinto_desplazar_fuerza":0.6,"devaluar_umbral":0.35,"devaluar_fuerza":0.4,"instinto_fuerza_base":0.5,"instinto_umbral_carencia":0.3},
    "result":{
        "A_desplazamiento":{"pasos":pasos_a,"tiles":len(tiles_a),"mov_total":mov_a,"mov_pct":round(mov_pct_a,1),"eat":eat_a,"eat_pct":round(eat_pct_a,1),"eat_con_hambre":echa_a,"hambre":hambre_a,"noop":round(noop_a,1),"querer":querer_a,"nec_insat_steps":nec_insat_a,"nec_insat_pct":round(nec_insat_pct_a,1),"muerte":muerte_a},
        "NC_sin_desplazamiento":{"pasos":pasos_c,"tiles":len(tiles_c),"mov_total":mov_c,"mov_pct":round(mov_pct_c,1),"eat":eat_c,"noop":round(noop_c,1),"querer":querer_c,"muerte":muerte_c},
        "pass_se_mueve":pass_se_mueve,"pass_explora":pass_explora,"pass_supervivencia":pass_vive,"pass_no_deambulo":no_deambulo,"pass_mantiene_querer":mantiene_querer},
    "script":"experiments/exp_SGM_0122_desplazamiento.py",
    "results_file":"results/results_exp_SGM_0122_desplazamiento.json",
    "variant_of":"exp_SGM_0121",
    "lit_refs":["Berridge & Robinson 1998 - wanting como motivacion operante (correlacion hambre->busqueda)","O'Keefe & Nadel 1978 - el cuerpo se desplaza para buscar el recurso donde esta","Berridge & Robinson 2016 - liking vs wanting: el desplazamiento es motivacional, no placentero","Dolan & Dayan 2013 - accion dirigida a meta emerge de recompensa diferencial (no quedarse)","Varela 1991 - enactivismo: el movimiento es constitutivo del conocer (no solo buscar)"],
    "notes":"El 0121 fallo (mov=0%) porque empujar a moverse por curiosidad no vence el atractor local del PPR. Por eso el 0122 NO empuja a moverse proactivamente sino REACTIVO a la carencia: cuando V_grafo < devaluar_umbral(0.35) y la ultima accion fue comer (y no resolvio), devalua acciones locales que no funcionan (score-=0.4) y da peso al movimiento (score+=0.6). El cuerpo se mueve porque quedarse es inutil. Autolimitativo: depende de la carencia real; si se sacia, se apaga. Mide si el movimiento emerge con razon (no deambulo perpetuo) y si mantiene el querer de comer.",
    "notes_criollo":"En el 0121 el sistema no se movia porque nadie le habia dado un motivo real para moverse: empujarlo a explorar no alcanzaba porque quedarse comiendo le 'funcionaba'. La idea del 0122 es distinta: el cuerpo se mueve cuando quedarse quieto NO le sirve mas — cuando tiene hambre critica, intenta comer, y sigue con hambre. Entonces las acciones locales (comer, fabricar) se devaluan porque no resuelven, y el movimiento gana peso: el cuerpo sale a buscar donde SI haya comida. Es como cuando vos tenes hambre de verdad y la heladera esta vacia: no seguis mirando la heladera, salis a buscar un almacen. Y se apaga solo cuando encuentra y come — no deambula por deambular.",
}, open(out,"w"), indent=2)
print(f"\n  Guardado en: {out}")
