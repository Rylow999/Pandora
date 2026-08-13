#!/usr/bin/env python3
"""exp_SGM_0136 — FIX DEFINITIVO DEL MAPEO DE OBJETOS CRAFTER.

HALLAZGO CRITICO (verificado en crafter/engine.py:251-263 y env.py:47-49):
El semantic ES la grilla mundial 64x64 (no un FOV), y el mapeo de objetos es:
  mat_ids: None=0..furnace=12 (13 materiales)
  obj_ids (len mat_ids + i para [Player,Cow,Zombie,Skeleton,Arrow,Plant]):
    Player=13, Cow=14, Zombie=15, Skeleton=16, Arrow=17, Plant=18

Todos los experimentos 0120-0135 usaban FOOD={13,17} (cow,plant) y ENEMIGO={14,15}
(zombie,skeleton) -> PERO 13=PLAYER, 17=ARROW, 14=COW, 15=ZOMBIE. El gradiente de
comida apuntaba al PLAYER MISMO (13) y a flechas (17), nunca a comida real (14/18).
Por eso comio_efectivo=0 en TODA la saga: el agente perseguia su propia posicion.

FIX: FOOD={14,18} (cow, plant), ENEMIGO={15,16} (zombie, skeleton).

HIPOTESIS falsable: con el mapeo corregido, el gradiente apunta a comida REAL. El
agente que tiene hambre se acerca a una cow real (gracias al re-encare distinguiendo
adyacente vs lejano, 0135) y hace 'do' efectivo -> food sube -> comio_efectivo>0 y
ciclos de subsistencia. Por fin cierra el eslabon que estaba bloqueado por el mapping.

LITERATURA: crafter/engine.py SemanticView (mapeo real); la leccion de verificar SIEMPRE
el mapeo del entorno antes de confiar en el gradiente (proto: verificar accion/constantes).
"""
import sys, os, random, json
from collections import Counter
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm_core import SGMAgent
import crafter
import numpy as np

D = 128; N_NODES = 64
ACC = {0:"noop",1:"mv_l",2:"mv_r",3:"mv_u",4:"mv_d",5:"do",6:"sleep",
       7:"p_stone",8:"p_table",9:"p_furnace",10:"p_plant",11:"mk_w_pick",
       12:"mk_s_pick",13:"mk_i_pick",14:"mk_w_sword",15:"mk_s_sword",
       16:"mk_i_sword"}
MOV = {1,2,3,4}
# MAPEO CORREGIDO de Crafter (verificado en engine.py: mat_ids=0..12, obj_ids=13+)
COMIDA = {14, 18}   # cow=14, plant=18 (REAL)
ENEMIGO = {15, 16}  # zombie=15, skeleton=16 (REAL)
COMER = 5           # 'do'
UMBRAL_EAT = 2.0
MOVE_DIR = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


def gradiente(sem, px, py, clases, r=8):
    b, bd = (0, 0), r * r + 1
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx == 0 and dy == 0:
                continue
            x, y = px + dx, py + dy
            if 0 <= x < sem.shape[1] and 0 <= y < sem.shape[0]:
                if sem[y, x] in clases:
                    d = abs(dx) + abs(dy)
                    if d < bd:
                        bd, b = d, (dx, dy)
    return b, bd


def inc_dir(m, a):
    if not m:
        return 1.0
    t, nw = 0, 0
    for (e, ac), tr in m.items():
        if ac == a:
            t += sum(tr.values())
            for sq, c in tr.items():
                if c <= 1:
                    nw += 1
    return nw / max(1, t)


def correr(seed, max_p=600):
    ag = SGMAgent(random.Random(seed), D, n_nodes=N_NODES, gamma=0.01)
    ag.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES - 1))
                  for i in range(N_NODES)})
    env = crafter.Env(); env.reset()
    obs, r, t, info = env.step(0)
    tiles = set(); comio_efectivo = comio_vacio = ataco = mov = ciclos = 0
    food_bajo = False
    facing = (0, 1)
    prev_hp = 9.0
    for step in range(max_p):
        sem = info["semantic"]; inv = info["inventory"]
        px, py = int(info["player_pos"][0]), int(info["player_pos"][1])
        hp = float(inv["health"])
        sf = sem.flatten().tolist()
        sv = [float(v) for v in sf[::64]] + [float(inv["health"])/10.0,
              float(inv["food"])/10.0, float(inv["wood"]), float(inv["stone"]),
              float(inv["iron"])]
        # hambre real
        hambre = max(0.0, 1.0 - inv["food"] / 10.0)
        # amenaza con decaimiento por distancia (biologico)
        danio = max(0.0, (prev_hp - hp) / 10.0)
        g_enemigo, dist_enemigo = gradiente(sem, px, py, ENEMIGO)
        amenaza_env = max(0.0, 1.0 - (dist_enemigo - 1) / 3.0) if dist_enemigo < 999 else 0.0
        amenaza = max(danio * 1.5, amenaza_env * 0.8)
        # lo que hay enfrente (semantic es grilla mundial)
        ex, ey = px + facing[0], py + facing[1]
        algo_enfrente = 0
        if 0 <= ex < 64 and 0 <= ey < 64:
            v = sem[ey, ex]
            if v in COMIDA:
                algo_enfrente = 1
            elif v in ENEMIGO:
                algo_enfrente = 2
        # senales
        ag._hambre_real = min(1.0, hambre)
        ag._amenaza = min(1.0, amenaza)
        ag._algo_enfrente = algo_enfrente
        ag._gradiente_dir = g_enemigo; ag._gradiente_dist = dist_enemigo
        ag._hay_gradiente = g_enemigo != (0, 0)
        ag._inc_dirs = {a: inc_dir(ag.modelo_mundo, a) for a in MOV}
        ag._config_grad = {"activo": True, "fuerza": 0.5}
        ag._config_curio = {"activo": True, "fuerza": 0.3}
        # re-encare: objetivo dominante (amenaza prioriza enemigo, si no comida)
        g_comida, d_comida = gradiente(sem, px, py, COMIDA)
        if amenaza > hambre and g_enemigo != (0, 0):
            ag._target_dir = g_enemigo; ag._target_dist = max(abs(g_enemigo[0]), abs(g_enemigo[1]))
        elif hambre > 0.05 and g_comida != (0, 0):
            ag._target_dir = g_comida; ag._target_dist = d_comida
        else:
            ag._target_dir = (0, 0); ag._target_dist = 0
        # instinto de comer (hambre) override
        if inv["food"] < ag.umbral_hambre_food:
            conn = ag.conn_type.get((COMER, 0))
            st = conn.get("strength", 0) if conn else 0
            if not ((COMER, 0) in ag.consolidadas) and st < UMBRAL_EAT:
                care = max(0.0, ag.umbral_hambre_food - inv["food"])
                ag._fuerza_instinto_eat_override = ag.instinto_fuerza_base * (care / ag.umbral_hambre_food)
            else:
                ag._fuerza_instinto_eat_override = 0.0
        else:
            ag._fuerza_instinto_eat_override = 0.0
        # accion
        a = ag.step(sv, list(range(17)))
        food_antes = float(inv["food"])
        obs, r, t, info = env.step(a)
        food_despues = float(inv["food"])
        ag.actualizar_homeostasis(inv["food"], inv["health"])
        # contabilizar do
        if a == COMER:
            if food_despues > food_antes:
                comio_efectivo += 1
            elif algo_enfrente == 2:
                ataco += 1
            else:
                comio_vacio += 1
        pain = 0.0
        if r < 0:
            pain = abs(r)
        elif inv["health"] < 5:
            pain = 0.1
        ag.reward(max(0.0, r), pain)
        pos = (px, py)
        if pos not in tiles:
            tiles.add(pos); ag.reward(0.05, 0.0)
        ag.incertidumbre_acum = max(0, ag.incertidumbre_acum - 0.01)
        eq = ag.cuantizar_estado(sv)
        ag.actualizar_modelo_mundo(getattr(ag, 'ultimo_estado_q', eq) or eq, a, eq)
        ag.ultimo_estado_q = eq
        if inv["food"] < 3:
            food_bajo = True
        elif food_bajo and inv["food"] >= 7:
            ciclos += 1; food_bajo = False
        if a in MOV:
            mov += 1
            facing = MOVE_DIR[a]
        prev_hp = hp
        if t:
            break
    muerte = {"step": step, "food": float(inv["food"]), "hp": float(inv["health"]),
              "Vg": round(ag.V_grafo, 3)} if t else None
    return {"seed": seed, "pasos": step + 1, "tiles": len(tiles),
            "comio_efectivo": comio_efectivo, "comio_vacio": comio_vacio,
            "ataco": ataco, "mov": mov, "ciclos": ciclos, "muerte": muerte,
            "consol": len(ag.consolidadas)}


print("=" * 70)
print(" exp_SGM_0136 — FIX MAPEO OBJETOS: comida=14/18, enemigo=15/16")
print("=" * 70)
for seed in [42, 7, 99]:
    res = correr(seed, max_p=600)
    print(f" seed {seed}: {res['pasos']}p {res['tiles']}tiles "
          f"comio_efectivo={res['comio_efectivo']} comio_vacio={res['comio_vacio']} "
          f"ataco={res['ataco']} mov={res['mov']} ciclos={res['ciclos']} "
          f"consol={res['consol']} muerte={res['muerte']}")

out = os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/"
                         "results/results_exp_SGM_0136_fix_mapeo_objetos.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id": "exp_SGM_0136",
    "experiment_name": "fix_mapeo_objetos_crafter",
    "phase": "Fase 8 - fix definitivo del mapeo de objetos (comida=14/18, enemigo=15/16)",
    "date": "2026-08-11",
    "hypothesis": "Los experimentos 0120-0135 usaban FOOD={13,17} pero 13=PLAYER, 17=ARROW en "
                  "Crafter (mapeo real: 13=Player,14=Cow,15=Zombie,16=Skeleton,17=Arrow,18=Plant). "
                  "El gradiente apuntaba al player, nunca a comida real. Con FOOD={14,18} el "
                  "gradiente apunta a comida real; el agente hambriento se acerca (re-encare) y "
                  "hace 'do' efectivo -> comio_efectivo>0, ciclos de subsistencia.",
    "config": {"D": D, "N_NODES": N_NODES, "max_pasos": 600, "seeds": [42, 7, 99],
               "FOOD_corregido": [14, 18], "ENEMIGO_corregido": [15, 16],
               "comer": "do=5", "homeostasis": "NATIVA Crafter"},
    "result": "ver reporte stdout (resultados impresos arriba)",
    "script": "experiments/exp_SGM_0136_fix_mapeo_objetos.py",
    "results_file": "results/results_exp_SGM_0136_fix_mapeo_objetos.json",
    "variant_of": "exp_SGM_0135",
    "lit_refs": ["crafter/engine.py SemanticView: mat_ids=0..12, obj_ids=13+ (Player=13 sle...)"],
    "notes": "HALLAZGO DEFINITIVO: el mapeo de objetos de Crafter (verificado en engine.py) es "
             "mat_ids(0..12)+idx: Player=13, Cow=14, Zombie=15, Skeleton=16, Arrow=17, Plant=18. "
             "0120-0135 usaron FOOD={13,17}(player,arrow) -> el gradiente apuntaba al player. "
             "Se corrige a comida={14,18}, enemigo={15,16}.",
    "notes_criollo": "El bicho nunca comia porque su 'detector de comida' buscaba lo valores "
                     "equivocados: 13 era el PROPIO player (no una vaca) y 17 una flecha. Le "
                     "daba al gradiente 've a la vaca' pero apuntaba a el mismo. Corregimos "
                     "los numeros y ahora si deberia ver comida de verdad.",
}, open(out, "w"), indent=2)
print(f"\n Guardado en: {out}")