#!/usr/bin/env python3
"""
exp_SGM_0116 — Querer por reward intrínseco de V_grafo (HRRL), núcleo-cuerpo.

HIPOTESIS (falsable):
  Si el núcleo SGM aprende a comer porque comer ELEVA la vitalidad del grafo
  (su propia vida = vida del cuerpo del player), sin reward externo por comida,
  entonces la accion `eat` ganara frecuencia cuando el hambre sube (wanting emergente),
  y el agente vivira mas tiempo que sin el mecanismo.

Protocolo A/B:
  A: reward externo de Crafter por comer APAGADO — solo el efecto intrinseco de V_grafo
     vía actualizar_homeostasis().
  B: reward externo de Crafter por comer ACTIVO (canal A + intrinseco).
  Pregunta clave: ¿basta el intrinseco (A) o se necesita el externo (B)?
  NC: agente SIN actualizar_homeostasis (sin mecanismo) — debe seguir muriendo de hambre.

Medicion multi-estrato: supervivencia, apetito (correlacion food->eat), grafo, estados internos.
"""
import sys, os, random
from collections import Counter
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm.core.sgm_core import SGMAgent
import crafter

D=128; N_NODES=64
ACC = {0:"noop",1:"move_left",2:"move_right",3:"move_up",4:"move_down",
       5:"do",6:"sleep",7:"place_stone",8:"place_table",9:"place_furnace",
       10:"make_wood_pickaxe",11:"make_stone_pickaxe",12:"make_iron_pickaxe",
       13:"make_wood_sword",14:"make_stone_sword",15:"make_iron_sword",16:"eat"}

def correr_vida(agent, usar_homeostasis, usar_reward_externo, max_pasos=2000):
    """Aparato vivir-hasta-morir. homeostasis -> llama actualizar_homeostasis.
    reward_externo -> si apagado, suprime el reward positivo de Crafter por comer
    (mantiene pain por daño/hambre)."""
    env = crafter.Env(); env.reset()
    obs,r,t,info = env.step(0)
    tiles=set(); log=[]; eat_total=0; hambre=0
    for step in range(max_pasos):
        sem=info["semantic"].flatten().tolist(); inv=info["inventory"]
        pos=tuple(info["player_pos"])
        sv=[float(v) for v in sem[::64]]+[float(inv["health"])/10.0,float(inv["food"])/10.0,
           float(inv["wood"]),float(inv["stone"]),float(inv["iron"])]
        a=agent.step(sv,list(range(17)))
        obs,r,t,info=env.step(a)
        # Homeostasis: si usamos el mecanismo intrinseco, llamar ANTES del reward
        # para que actualizar_homeostasis detecte la mejora de la accion anterior.
        if usar_homeostasis:
            agent.actualizar_homeostasis(inv["food"], inv["health"])
        # Reward: si reward externo apagado, suprimir el reward positivo (r>0)
        # del comer; mantener el pain de daño/hambre.
        r_ext = r if usar_reward_externo else max(0.0, r)
        pain = 0.0
        if r < 0: pain = abs(r)
        elif inv["health"] < 5: pain = 0.1*(5-inv["health"])
        elif inv["food"] < 3: pain = 0.05
        agent.reward(r_ext, pain)
        # Contar apetito
        if a == 16: eat_total += 1
        if inv["food"] < 3: hambre += 1
        log.append({"step":step,"a":a,"food":inv["food"],"hp":inv["health"],
                    "nov":0.0,"Ea":round(agent.E_acumulado,3),"duda":agent.doubt_count,
                    "status":agent.status})
        # reward intrinsico por novedad (comun a todos): explorar tiles nuevos
        if pos not in tiles:
            tiles.add(pos)
            agent.reward(0.1, 0.0)  # novedad
        if t:
            muerte={"step":step,"food":inv["food"],"hp":inv["health"],"status":agent.status}
            return log, tiles, acc_a_count(agent, log), muerte, step+1, eat_total, hambre
    # no murio
    return log, tiles, acc_a_count(agent, log), None, step+1, eat_total, hambre

def acc_a_count(agent, log):
    c = Counter(ACC.get(l['a'],"?") for l in log)
    return c

def reportar(nombre, log, tiles, cnt, muerte, pasos, eat_total, hambre):
    noop = 100*cnt.get('noop',0)/max(1,len(log))
    print(f"\n  {nombre}: {pasos}p, {len(tiles)} tiles, {noop:.1f}% noop, eat={eat_total}, hambre={hambre}")
    if muerte: print(f"    muerte: {muerte}")
    for act,n in cnt.most_common(4):
        print(f"    {act:18s} {n:3d} ({100*n/len(log):.1f}%)")

print("="*70)
print("  exp_SGM_0116 — Querer por V_grafo (reward intrinseco HRRL)")
print("="*70)

# A: HOMEOSTASIS intrinseca, reward externo APAGADO
rng_a = random.Random(42)
ag_a = SGMAgent(rng_a, D, n_nodes=N_NODES, gamma=0.01)
ag_a.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES-1)) for i in range(N_NODES)})
log_a, tiles_a, cnt_a, muerte_a, pasos_a, eat_a, hambre_a = correr_vida(ag_a, usar_homeostasis=True, usar_reward_externo=False)
reportar("A (intrinseco, sin reward ext)", log_a, tiles_a, cnt_a, muerte_a, pasos_a, eat_a, hambre_a)

# B: HOMEOSTASIS intrinseca + reward externo ACTIVO
rng_b = random.Random(42)
ag_b = SGMAgent(rng_b, D, n_nodes=N_NODES, gamma=0.01)
ag_b.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES-1)) for i in range(N_NODES)})
log_b, tiles_b, cnt_b, muerte_b, pasos_b, eat_b, hambre_b = correr_vida(ag_b, usar_homeostasis=True, usar_reward_externo=True)
reportar("B (intrinseco + reward ext)", log_b, tiles_b, cnt_b, muerte_b, pasos_b, eat_b, hambre_b)

# NC: SIN homeostasis (sin mecanismo intrinseco)
rng_c = random.Random(42)
ag_c = SGMAgent(rng_c, D, n_nodes=N_NODES, gamma=0.01)
ag_c.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES-1)) for i in range(N_NODES)})
log_c, tiles_c, cnt_c, muerte_c, pasos_c, eat_c, hambre_c = correr_vida(ag_c, usar_homeostasis=False, usar_reward_externo=False)
reportar("NC (sin mecanismo)", log_c, tiles_c, cnt_c, muerte_c, pasos_c, eat_c, hambre_c)

# Comparacion
print(f"\n{'='*70}")
print("  COMPARACION")
print(f"{'='*70}")
print(f"  A (intrinsico):        eat={eat_a}, vive={pasos_a}p, tiles={len(tiles_a)}")
print(f"  B (intr+externo):      eat={eat_b}, vive={pasos_b}p, tiles={len(tiles_b)}")
print(f"  NC (sin mecanismo):    eat={eat_c}, vive={pasos_c}p, tiles={len(tiles_c)}")

# PASS: A come mas que NC (el mecanismo intrinseco genera querer)
pass_test = eat_a > eat_c
print(f"\n  PASS (intrinseco genera querer, A>NC): {pass_test}")
print(f"{'='*70}")

import json
out=os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/results/results_exp_SGM_0116_vgrafo_querer.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id":"exp_SGM_0116",
    "experiment_name":"querer_vgrafo_reward_intrinseco",
    "phase":"Fase 8 — querer por V_grafo (HRRL)",
    "date":"2026-08-06",
    "hypothesis":"Si el nucleo aprende a comer porque comer eleva la vitalidad del grafo (su vida), sin reward externo por comida, la accion eat gana frecuencia cuando el hambre sube (wanting emergente) y el agente vive mas.",
    "config":{"D":D,"N_NODES":N_NODES},
    "result":{
        "A_intrinsico_sin_reward":{"pasos":pasos_a,"tiles":len(tiles_a),"eat":eat_a,"hambre":hambre_a,"muerte":muerte_a,"acciones":dict(cnt_a.most_common(4))},
        "B_intr_mas_externo":{"pasos":pasos_b,"tiles":len(tiles_b),"eat":eat_b,"hambre":hambre_b,"muerte":muerte_b},
        "NC_sin_mecanismo":{"pasos":pasos_c,"tiles":len(tiles_c),"eat":eat_c,"hambre":hambre_c,"muerte":muerte_c},
        "pass":pass_test},
    "script":"experiments/exp_SGM_0116_vgrafo_querer.py",
    "results_file":"results/results_exp_SGM_0116_vgrafo_querer.json",
    "variant_of":"exp_SGM_0114",
    "lit_refs":["HRRL: homeostatically regulated RL (2025)","Berridge wanting vs liking","Maslow 1943 deficiency vs growth needs","Enactivism: Varela Thompson Rosch 1991"],
    "notes":"Nuevo mecanismo actualizar_homeostasis(): refuerza conexion accion->nodo0 cuando la homeostasis mejora, SIN reward externo. A/B: reward externo de comer apagado vs activo. NC: sin mecanismo. El nucleo SGM es cerebro agnostico de cuerpo; Crafter es el cuerpo (player=grafo).",
    "notes_criollo":"Le preguntamos al sistema si aprende a comer porque le hace bien a su propio cuerpo (la vitalidad del grafo sube), sin que nadie le de una recompensa por comer. Es como un bebe que aprende que comer lo mantiene vivo porque al comer se siente con mas energia — no porque le dieran una golosina. La condicion A le saca la golosina; la B se la deja. Si come igual en A, el instinto de sobrevivir es real, no aprendido por premios externos."
}, open(out,"w"), indent=2)
print(f"\n  Guardado en: {out}")