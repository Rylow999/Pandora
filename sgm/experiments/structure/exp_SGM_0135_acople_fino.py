#!/usr/bin/env python3
"""exp_SGM_0135 — INSTINTO DE INTERACCION unificado (hambre + defensa via 'do').

CONTEXTO 0131: con el fix del mapeo (comer=do=5), el agente NUNCA ejecuto 'do'. El
instinto de interaccion requiere que (a) haya una necesidad real y (b) haya algo
accionable ENFRENTE. Este experimento implementa el INSTINTO UNIFICADO (Luciano): el
'do' interactua con lo que haya enfrente (come si hay comida, ataca si hay enemigo).

MECANISMO (core 0135): la pulsion a 'do' sube = max(hambre_real, amenaza) * fuerza,
pero SOLO si hay algo accionable enfrente (comida o enemigo). Es el mecanismo
multiaccion independiente del sustrato: UN impulso base, el mundo decide que hace 'do'.

SENALES (harness setea en cada step al agente):
  _hambre_real: food bajo -> 0-1 (0= saciado, 1= hambre critica)
  _amenaza:     hp perdido reciente + enemigo en gradiente -> 0-1
  _algo_enfrente: 1=comida, 2=enemigo, 0=nada (lo que hay en pos+facing)

Para conocer el facing del player (no expuesto en info), el harness lo rastrea: en
Crafter cada move cambia facing a esa direccion y desplaza. El facing es la direccion
del ultimo move. La celda 'enfrente' = pos + facing.

HIPOTESIS falsable: con el instinto unificado, cuando el agente percibe amenaza y hay
un enemigo enfrente, ejecuta 'do' para atacar (reduce hp perdido / no muere tan rapido).
Cuando tiene hambre y hay comida enfrente, ejecuta 'do' para comer (food sube). Pred:
en al menos una seed, el agente ataca (baja enemigos, sobrevive mas) y/o come
(comio_efectivo>0). Es la fusion de los mecanismos de subsistencia + defensa.

LITERATURA: Luciano 2026-08-11 (mecanismo multiaccion independiente del sustrato);
Panksepp 1998 (SEEKING/RAGE); objects.py:113-116 (do=comer/cazar); objetos 13=cow,
14=zombie, 15=skeleton.
"""
import sys, os, random, json
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm.core.sgm_core import SGMAgent
import crafter
import numpy as np

D = 128; N_NODES = 64
ACC = {0:"noop",1:"mv_l",2:"mv_r",3:"mv_u",4:"mv_d",5:"do",6:"sleep",
       7:"p_stone",8:"p_table",9:"p_furnace",10:"p_plant",11:"mk_w_pick",
       12:"mk_s_pick",13:"mk_i_pick",14:"mk_w_sword",15:"mk_s_sword",
       16:"mk_i_sword"}
MOV = {1,2,3,4}
COMIDA = {13, 17}      # cow, plant
ENEMIGO = {14, 15}     # zombie, skeleton
COMER = 5              # 'do'
UMBRAL_EAT = 2.0
# facing por accion de movimiento (Crafter: move l/r/u/d)
MOVE_DIR = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


def gradiente(sem, px, py, clases, r=6):
    """Busca el objeto/s de 'clases' mas cercano en el FOV. Retorna (dx,dy) o (0,0)."""
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
    facing = (0, 1)   # facing inicial de Crafter
    prev_hp = 9.0
    # ofensivas/defensivas contadas
    for step in range(max_p):
        sem = info["semantic"]; inv = info["inventory"]
        px, py = int(info["player_pos"][0]), int(info["player_pos"][1])
        hp = float(inv["health"])
        sf = sem.flatten().tolist()
        sv = [float(v) for v in sf[::64]] + [float(inv["health"])/10.0,
              float(inv["food"])/10.0, float(inv["wood"]), float(inv["stone"]),
              float(inv["iron"])]
        # --- computar senales para el instinto unificado ---
        # hambre real: food bajo (0-1)
        hambre = max(0.0, 1.0 - inv["food"] / 10.0)
        # amenaza: hp perdido reciente + enemigo en el gradiente con DECAIMIENTO POR DISTANCIA
        # (0135: equilibrio temporal). Un enemigo LEJANO es amenaza baja -> el hambre puede
        # competir y el agente come en calma. Un enemigo CERCA es amenaza alta -> pelea.
        # Biologico: el animal no pelea constante; come entre amenazas (Panksepp RAGE/SEEKING).
        danio = max(0.0, (prev_hp - hp) / 10.0)   # dolor reciente (amenaza inmediata)
        g_enemigo, dist_enemigo = gradiente(sem, px, py, ENEMIGO)
        # amenaza por enemigo en vista: decae con la distancia (lejos=calma, cerca=alerta)
        if dist_enemigo < 999:
            amenaza_env = max(0.0, 1.0 - (dist_enemigo - 1) / 3.0)  # cerco (1-2)=1, lejos (4+)=0
        else:
            amenaza_env = 0.0
        amenaza = max(danio * 1.5, amenaza_env * 0.8)
        # lo que hay enfrente: en la celda pos+facing
        ex, ey = px + facing[0], py + facing[1]
        algo_enfrente = 0
        if 0 <= ex < 64 and 0 <= ey < 64:
            v = sem[ey, ex]
            if v in COMIDA:
                algo_enfrente = 1
            elif v in ENEMIGO:
                algo_enfrente = 2
        # setear senales al agente
        ag._hambre_real = min(1.0, hambre)
        ag._amenaza = min(1.0, amenaza)
        ag._algo_enfrente = algo_enfrente
        ag._gradiente_dir = g_enemigo; ag._gradiente_dist = dist_enemigo
        ag._hay_gradiente = g_enemigo != (0, 0)
        ag._inc_dirs = {a: inc_dir(ag.modelo_mundo, a) for a in MOV}
        ag._config_grad = {"activo": True, "fuerza": 0.5}
        ag._config_curio = {"activo": True, "fuerza": 0.3}
        # 0135 RE-ENCARE: objetivo dominante segun necesidad. Si hay amenaza, prioriza
        # enemigo; si no, comida. Es la SENAL de adonde orientarse para poder interactuar.
        g_comida, d_comida = gradiente(sem, px, py, COMIDA)
        if amenaza > hambre and g_enemigo != (0, 0):
            ag._target_dir = g_enemigo
            ag._target_dist = max(abs(g_enemigo[0]), abs(g_enemigo[1]))
        elif hambre > 0.05 and g_comida != (0, 0):
            ag._target_dir = g_comida
            ag._target_dist = max(abs(g_comida[0]), abs(g_comida[1]))
        else:
            ag._target_dir = (0, 0)
            ag._target_dist = 0
        # instinto de comer (hambre) via override; el core suma la parte de amenaza
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
        # --- accion ---
        a = ag.step(sv, list(range(17)))
        food_antes = float(inv["food"]); hp_antes = hp
        obs, r, t, info = env.step(a)
        food_despues = float(inv["food"])
        ag.actualizar_homeostasis(inv["food"], inv["health"])
        # control del do: comida efectiva / ataque
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
            facing = MOVE_DIR[a]  # actualizar facing con el move
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
print(" exp_SGM_0135 — Acople fino: interactuar cuando el objetivo esta adyacente")
print("=" * 70)
for seed in [42, 7, 99]:
    res = correr(seed, max_p=600)
    print(f" seed {seed}: {res['pasos']}p {res['tiles']}tiles "
          f"comio_efectivo={res['comio_efectivo']} comio_vacio={res['comio_vacio']} "
          f"ataco={res['ataco']} mov={res['mov']} ciclos={res['ciclos']} "
          f"consol={res['consol']} muerte={res['muerte']}")

out = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), ""
                         "results/results_exp_SGM_0135_acople_fino.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id": "exp_SGM_0135",
    "experiment_name": "acople_fino_adyacente",
    "phase": "Fase 8 - acople fino: interactuar cuando el objetivo esta adyacente",
    "date": "2026-08-11",
    "hypothesis": "El 'do'(5) es el mecanismo operante general: come si hay comida enfrente, "
                  "ataca si hay enemigo. La pulsion sube = max(hambre, amenaza) cuando hay algo "
                  "accionable enfrente. Pred: el agente ataca enemigos (reduce daño) y/o come "
                  "(food sube). Mecanismo multiaccion independiente del sustrato.",
    "config": {"D": D, "N_NODES": N_NODES, "max_pasos": 600, "seeds": [42, 7, 99],
               "comer": "accion do(5)", "atacar": "accion do(5) sobre enemigo enfrente",
               "homeostasis": "NATIVA Crafter"},
    "result": [{"seed": s, **{k: correr(s, 600)[k] for k in
               ["pasos","tiles","comio_efectivo","comio_vacio","ataco","mov","ciclos","muerte"]}}
               for s in [42,7,99]] if False else "ver reporte stdout (resultados se imprimieron arriba)",
    "script": "experiments/exp_SGM_0135_acople_fino.py",
    "results_file": "results/results_exp_SGM_0135_acople_fino.json",
    "variant_of": "exp_SGM_0134",
    "lit_refs": ["Luciano 2026-08-11 - mecanismo multiaccion independiente del sustrato",
                 "Panksepp 1998 - SEEKING/RAGE",
                 "crafter objects.py:113-116 - do=comer/cazar"],
    "notes": "Extiende el instinto de alimentacion (que apuntaba a 'do') a un instinto de "
             "interaccion UNIFICADO: la misma accion 'do' come o ataca segun que haya enfrente. "
             "El sustrato percibe hambre (food bajo), amenaza (hp perdido + enemigo en grace), "
             "y lo que tiene enfrente (pos+facing). La pulsion a 'do' = max(hambre, amenaza) "
             "si hay algo accionable. Test de si el agente por fin ejecuta 'do' (comer y/o pelear).",
    "notes_criollo": "Ahora el 'do' es como la mano del bebe: toma lo que tenga adelante. Si hay "
                     "comida, come; si hay un bicho, lo golpea. La pulsion de hacerlo crece cuando "
                     "el cuerpo tiene una necesidad real (hambre o le pegaron) y hay algo adelante "
                     "sobre lo que actuar. Es UN solo mecanismo para subsistencia Y defensa, no dos "
                     "sistemas separados — la idea que marcaste.",
}, open(out, "w"), indent=2)
print(f"\n Guardado en: {out}")