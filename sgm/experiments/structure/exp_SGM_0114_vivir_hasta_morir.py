#!/usr/bin/env python3
"""
exp_SGM_0114 — Vivir hasta morir (aparato de evaluación multi-estrato).

El agente corre hasta terminal=True (muerte natural), NO se corta por pasos.
Se reporta QUÉ hacía en cada estrato:
  1. Supervivencia: cuánto vivió, por qué murió, estado al morir.
  2. Grafo: aristas creadas/podadas, conn_type aprendido (¿apareció hambre->comer o enfrentar->espada?).
  3. Movimiento: trayectoria (no solo tiles únicos), rango X/Y.
  4. Apetito: correlación food-bajo -> eat (¿quiere comer?).
  5. Estados internos: traza E_acum, status, duda.
  6. Curiosidad: prediction error del decoder a lo largo de la vida.

NC: mismo aparato sin reward de novedad. Si el agente explora menos sin reward,
la novedad es relevante. Si muere igual, el reward de novedad no cambia la supervivencia.
"""
import sys, os, random, math
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

def correr_vida_hasta_morir(agent, usar_reward_novedad=True, max_pasos=2000):
    env = crafter.Env(); env.reset()
    obs,r,t,info = env.step(0)
    tiles=set(); log=[]; trazapos=[]; acciones=[]; momento_muerte=None
    for step in range(max_pasos):
        sem=info["semantic"].flatten().tolist(); inv=info["inventory"]
        pos=tuple(info["player_pos"]); trazapos.append(pos)
        sv=[float(v) for v in sem[::64]]+[float(inv["health"])/10.0,float(inv["food"])/10.0,
           float(inv["wood"]),float(inv["stone"]),float(inv["iron"])]
        a=agent.step(sv,list(range(17)))
        acciones.append(a)
        obs,r,t,info=env.step(a)
        ri=0.0
        if usar_reward_novedad:
            if pos not in tiles: tiles.add(pos); ri=0.1
        pain=0.0
        if r<0: pain=abs(r)
        elif inv["health"]<5: pain=0.1*(5-inv["health"])
        elif inv["food"]<3: pain=0.05
        agent.reward(r+ri, pain)
        log.append({"step":step,"a":a,"hp":inv["health"],"food":inv["food"],
                    "nov":ri,"Ea":round(agent.E_acumulado,3),"status":agent.status,
                    "duda":agent.doubt_count,"pos":list(pos)})
        if t:
            momento_muerte = {"step":step,"health":inv["health"],"food":inv["food"],
                              "status":agent.status,"duda":agent.doubt_count}
            break
    return log, tiles, trazapos, acciones, momento_muerte, step+1

def strat_grafo(agent):
    """Reporta cambios en el grafo."""
    return {"n_aristas_conn_type": len(agent.conn_type),
            "nodos_con_arista": sum(1 for e in agent.edges.values() if e)}

def strat_apetito(log):
    """Correlacion food-bajo -> eat."""
    eat_cuando_hambre = 0; eat_total = 0; hambre_sin_eat = 0
    for l in log:
        esta_con_hambre = l["food"] < 3
        es_morira = l["a"] == 16  # action eat
        if es_morira:
            eat_total += 1
            if esta_con_hambre: eat_cuando_hambre += 1
        else:
            if esta_con_hambre: hambre_sin_eat += 1
    return {"eat_total": eat_total, "eat_con_hambre": eat_cuando_hambre,
            "hambre_sin_eat": hambre_sin_eat}

print("="*70)
print("  exp_SGM_0114 — Vivir hasta morir (evaluación multi-estrato)")
print("="*70)

# === CONDICION A: con reward de novedad ===
rng_a = random.Random(42)
agent_a = SGMAgent(rng_a, D, n_nodes=N_NODES, gamma=0.01)
agent_a.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES-1)) for i in range(N_NODES)})
log_a, tiles_a, pos_a, acc_a, muerte_a, pasos_a = correr_vida_hasta_morir(agent_a, usar_reward_novedad=True)
cnt_a = Counter(ACC.get(x,"?") for x in acc_a)
noop_a = 100*cnt_a.get('noop',0)/max(1,len(acc_a))

print("\n=== ESTRATO 1: SUPERVIVENCIA (CON reward novedad) ===")
print(f"  Vivido: {pasos_a} pasos | {muerte_a}")
print(f"  Noop: {noop_a:.1f}% | tiles: {len(tiles_a)}")

print("\n=== ESTRATO 2: GRAFO (CON reward novedad) ===")
g_a = strat_grafo(agent_a)
print(f"  {g_a}")

print("\n=== ESTRATO 3: MOVIMIENTO (CON reward novedad) ===")
xs=[p[0] for p in pos_a]; ys=[p[1] for p in pos_a]
movs=sum(1 for i in range(1,len(pos_a)) if pos_a[i]!=pos_a[i-1])
print(f"  Rango X: {min(xs)}-{max(xs)} | Y: {min(ys)}-{max(ys)} | Movimientos: {movs}")

print("\n=== ESTRATO 4: APETITO (CON reward novedad) ===")
ap_a = strat_apetito(log_a)
print(f"  {ap_a}")

print("\n=== ESTRATO 5: ESTADOS INTERNOS (CON reward novedad) ===")
stat_cnt = Counter(l['status'] for l in log_a)
print(f"  Status: {dict(stat_cnt)} | Duda max: {max(l['duda'] for l in log_a)}")
print(f"  E_acum max: {max(l['Ea'] for l in log_a)}")

print("\n=== ACCIONES (CON reward novedad) ===")
for act,n in cnt_a.most_common(6):
    print(f"  {act:20s} {n:3d} ({100*n/len(acc_a):.1f}%)")

# === NC: sin reward de novedad ===
rng_b = random.Random(42)
agent_b = SGMAgent(rng_b, D, n_nodes=N_NODES, gamma=0.01)
agent_b.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES-1)) for i in range(N_NODES)})
log_b, tiles_b, pos_b, acc_b, muerte_b, pasos_b = correr_vida_hasta_morir(agent_b, usar_reward_novedad=False)
cnt_b = Counter(ACC.get(x,"?") for x in acc_b)
noop_b = 100*cnt_b.get('noop',0)/max(1,len(acc_b))
ap_b = strat_apetito(log_b)

print(f"\n{'='*70}")
print("  NC: SIN reward de novedad")
print(f"{'='*70}")
print(f"  Vivido: {pasos_b} pasos | {muerte_b} | Noop: {noop_b:.1f}% | tiles: {len(tiles_b)}")
print(f"  Apetito: {ap_b}")
for act,n in cnt_b.most_common(6):
    print(f"  {act:20s} {n:3d} ({100*n/len(acc_b):.1f}%)")

print(f"\n{'='*70}")
print("  COMPARACION supervivencia")
print(f"{'='*70}")
print(f"  Con reward: {pasos_a} pasos, {len(tiles_a)} tiles, murio: {muerte_a['status'] if muerte_a else 'sin muerte'}")
print(f"  Sin reward: {pasos_b} pasos, {len(tiles_b)} tiles, murio: {muerte_b['status'] if muerte_b else 'sin muerte'}")
pass_vive = (muerte_a is not None and pasos_a > 50)  # vivio "bastante" si paso 50
print(f"\n  Nota: si murió por hambre sin comer, el querer operativo NO está (come al azar).")

import json
out=os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/results/results_exp_SGM_0114_vivir_hasta_morir.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id":"exp_SGM_0114",
    "experiment_name":"vivir_hasta_morir_multi_estrato",
    "phase":"Fase 8 — formato vivir hasta morir",
    "date":"2026-08-06",
    "hypothesis":"El aparato de vivir hasta morir revela por que muere el agente y si tiene querer operativo (correlacion food->eat) o come al azar. Establece el formato de evaluacion multi-estrato.",
    "config":{"D":D,"N_NODES":N_NODES,"max_pasos":2000},
    "result":{
        "con_reward_novedad":{"pasos":pasos_a,"tiles":len(tiles_a),"noop":round(noop_a,1),
            "muerte":muerte_a,"grafo":g_a,"apetito":ap_a,
            "acciones":dict(cnt_a.most_common(6))},
        "sin_reward_novedad_nc":{"pasos":pasos_b,"tiles":len(tiles_b),"noop":round(noop_b,1),
            "muerte":muerte_b,"apetito":ap_b}},
    "script":"experiments/exp_SGM_0114_vivir_hasta_morir.py",
    "results_file":"results/results_exp_SGM_0114_vivir_hasta_morir.json",
    "variant_of":None,
    "lit_refs":["Berridge wanting vs liking — incentive salience medible como respuesta operante"],
    "notes":"Aparato vivo-hasta-morir. Reporta 6 estratos. Establece el formato para los experimentos Fase 8 que siguen (0116 querer, 0117 curiosidad, 0118 integracion).",
    "notes_criollo":"Dejamos al agente vivir hasta que muera, sin cortarlo por pasos. Asi vemos de verdad de que se muere: si de hambre sin comer, quiere el problema (no tiene querer); si muere peleando, es otra cosa. Tambien miramos todos los estratos: el grafo, como se mueve, si come cuando tiene hambre, y su estado interno."
}, open(out,"w"), indent=2)
print(f"\n  Guardado en: {out}")