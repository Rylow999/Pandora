#!/usr/bin/env python3
"""exp_SGM_0131 — CORRECCION DEL MAPEO DE ACCIONES: instinto_alimentacion=5 (do).

HALLAZGO CRITICO (verificacion del entorno): TODOS los experimentos 0123-0130 usaban
ACC={16:"eat"} y instinto_alimentacion=16. PERO la accion 16 de Crafter es
make_iron_sword (fabricar espada de hierro), NO comer. Comer en Crafter es la accion
5 'do' (objects.py:113-116), que procesa la cow/plant que esta ENFRENTE (pos+facing).

Por eso ningun agente "comia": el instinto empujaba a fabricar espadas (el 'make_iron_sword
77%' que veiamos era el instinto de comer mal mapeado). eat_efectivo=0 SIEMPRE en 0129/0130
no era por facing: era porque la accion que come nunca se ejecutaba.

FIX (0131): instinto_alimentacion=5 en sgm_core.py. Ahora el instinto empuja a 'do' (comer).

HIPOTESIS B (Luciano): el sustrato debe EMERGER el acople cuerpo-mundo
(acercarse a la comida + orientarse + do) por el nodo-referencia, sin enseñarle la
secuencia. Con el mapeo correcto, cuando el agente llega adyacente a una cow/plant con
facing hacia ella y hace 'do', food sube -> nodo-referencia de restauracion SE CREA ->
Hebb/Kuramoto consolidan eat->nodo0 -> el instinto se apaga -> come por prediccion.

Prediccion falsable: por primera vez habra eat EFECTIVO (food sube tras 'do' con cow/plant
enfrente), el agente empezara a subsistir (no muere con food=0), y eat_efectivo>0 en
al menos una seed. Es el cambio que desbloquea toda la saga.

Protocolo: seed 42, vida completa (hasta muerte o 600 pasos), dinamica nativa.
Metricas: eat_efectivo, eat_vacio, food final, ciclos, mov, dominante.

La hipotesis es pura (opcion B): NO se fuerza la secuencia acercarse->orientarse->comer.
Solo se corrige el mapeo; el gradiente + instinto + drive + reward intrinseco deben
descubrir el acople.

LITERATURA: verificado en crafter.env/objects.py (comer=do=5, reward indirecto food->health);
hipotesis nodo-referencia (Luciano 2026-08-11); Hebb 1949; Kuramoto 1975.
"""
import sys, os, random, json
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm.core.sgm_core import SGMAgent
import crafter
import numpy as np

D = 128; N_NODES = 64
# MAPEO CORRECTO de Crafter (verificado en constants.actions)
ACC = {0:"noop",1:"move_left",2:"move_right",3:"move_up",4:"move_down",
       5:"do",6:"sleep",7:"place_stone",8:"place_table",9:"place_furnace",
       10:"place_plant",11:"make_wood_pickaxe",12:"make_stone_pickaxe",
       13:"make_iron_pickaxe",14:"make_wood_sword",15:"make_stone_sword",
       16:"make_iron_sword"}
MOV = {1,2,3,4}
FOOD = {13, 17}  # cow, plant (comidas)
COMER = 5        # accion 'do' (come cow/plant ENFRENTE)
UMBRAL_EAT = 2.0


def gradiente(sem, px, py, r=5):
    """Busca comida (cow/plant) en el FOV. Retorna (dx,dy) hacia la mas cercana o (0,0)."""
    b, bd = (0, 0), r * r + 1
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx == 0 and dy == 0:
                continue
            x, y = px + dx, py + dy
            if 0 <= x < sem.shape[1] and 0 <= y < sem.shape[0]:
                if sem[y, x] in FOOD:
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


def instinto_comer(ag, food_nivel):
    """Instinto de comer por hambre real de food. Empuja la accion 'do' (COMER).
    Compuerta de habituacion: OFF si conexion (COMER,0) consolidada."""
    if food_nivel is None or food_nivel >= ag.umbral_hambre_food:
        return 0.0
    conn = ag.conn_type.get((COMER, 0))
    st = conn.get("strength", 0) if conn else 0
    if (COMER, 0) in ag.consolidadas or st >= UMBRAL_EAT:
        return 0.0
    carencia = max(0.0, ag.umbral_hambre_food - food_nivel)
    return ag.instinto_fuerza_base * (carencia / ag.umbral_hambre_food)


def correr(seed, max_p=600):
    """Vida completa en dinamica nativa con el mapeo de acciones CORREGIDO."""
    ag = SGMAgent(random.Random(seed), D, n_nodes=N_NODES, gamma=0.01)
    ag.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES - 1))
                  for i in range(N_NODES)})
    env = crafter.Env(); env.reset()
    obs, r, t, info = env.step(0)
    tiles = set(); comio_efectivo = 0; comio_vacio = 0; mov = ciclos = 0
    food_bajo = False
    for step in range(max_p):
        sem = info["semantic"]; inv = info["inventory"]
        px, py = int(info["player_pos"][0]), int(info["player_pos"][1])
        sf = sem.flatten().tolist()
        sv = [float(v) for v in sf[::64]] + [float(inv["health"])/10.0,
              float(inv["food"])/10.0, float(inv["wood"]), float(inv["stone"]),
              float(inv["iron"])]
        gd, gd2 = gradiente(sem, px, py)
        hg = gd != (0, 0)
        ag._gradiente_dir = gd; ag._gradiente_dist = gd2; ag._hay_gradiente = hg
        ag._inc_dirs = {a: inc_dir(ag.modelo_mundo, a) for a in MOV}
        ag._config_grad = {"activo": True, "fuerza": 0.5}
        ag._config_curio = {"activo": True, "fuerza": 0.3}
        ag._fuerza_instinto_eat_override = instinto_comer(ag, float(inv["food"]))
        a = ag.step(sv, list(range(17)))
        # food antes de la accion
        food_antes = float(inv["food"]); habia_comida = hg
        obs, r, t, info = env.step(a)
        food_despues = float(inv["food"])
        ag.actualizar_homeostasis(inv["food"], inv["health"])
        # deteccion de comida efectiva: 'do'(5) con food que sube
        if a == COMER:
            if food_despues > food_antes:
                comio_efectivo += 1
            else:
                comio_vacio += 1
        # reward nativo + pain
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
        if t:
            break
    muerte = {"step": step, "food": float(inv["food"]), "hp": float(inv["health"]),
              "Vg": round(ag.V_grafo, 3)} if t else None
    return {"seed": seed, "pasos": step + 1, "tiles": len(tiles),
            "comio_efectivo": comio_efectivo, "comio_vacio": comio_vacio,
            "mov": mov, "ciclos": ciclos, "muerte": muerte, "consol": len(ag.consolidadas)}


print("=" * 70)
print(" exp_SGM_0131 — Fix mapeo: instinto_alimentacion=5 (do). Comer de verdad.")
print("=" * 70)
for seed in [42, 7, 99]:
    res = correr(seed, max_p=600)
    print(f" seed {seed}: {res['pasos']}p {res['tiles']}tiles "
          f"comio_efectivo={res['comio_efectivo']} comio_vacio={res['comio_vacio']} "
          f"mov={res['mov']} ciclos={res['ciclos']} consol={res['consol']} "
          f"muerte={res['muerte']}")

out = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), ""
                         "results/results_exp_SGM_0131_fix_mapeo_acciones.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id": "exp_SGM_0131",
    "experiment_name": "fix_mapeo_acciones_do",
    "phase": "Fase 8 - fix critico del mapeo de acciones (comer=do=5)",
    "date": "2026-08-11",
    "hypothesis": "Con instinto_alimentacion=5 (do, que es COMER en Crafter), el agente por "
                  "primera vez ejecuta la accion correcta para comer. Al llegar adyacente a una "
                  "cow/plant y hacer 'do', food sube -> nodo-referencia de restauracion se crea "
                  "-> Hebb/Kuramoto consolidan (do,0) -> el instinto se apaga -> come por "
                  "prediccion. Pred: comio_efectivo>0, no muere con food=0, ciclos de subsistencia.",
    "config": {"D": D, "N_NODES": N_NODES, "max_pasos": 600, "seeds": [42, 7, 99],
               "instinto_alimentacion": "5 (do/COMER, fix critico) - antes era 16 make_iron_sword",
               "homeostasis": "NATIVA Crafter"},
    "result": [res],
    "script": "experiments/exp_SGM_0131_fix_mapeo_acciones.py",
    "results_file": "results/results_exp_SGM_0131_fix_mapeo_acciones.json",
    "variant_of": "exp_SGM_0130",
    "lit_refs": ["Verificado en crafter/objects.py:113-116 - COMER = accion 'do'(5)",
                 "Hipotesis nodo-referencia (Luciano 2026-08-11)",
                 "Hebb 1949 - co-ocurrencia acto-resultado",
                 "Kuramoto 1975 - consolidacion por relevancia sincronizada"],
    "notes": "HALLAZGO CRITICO: todos los experimentos 0123-0130 usaban instinto_alimentacion=16 "
             "que en Crafter es make_iron_sword, NO comer. Comer=do=5. Se corrige el mapeo. "
             "Este es el verdadero desbloqueo: el instinto ahora empuja a la accion que come. "
             "El reward de Crafter por comer es indirecto (food->health->reward), y 'do' solo "
             "come si hay cow/plant ENFRENTE (pos+facing). Se evalua si con el mapeo correcto el "
             "agente subsiste por primera vez.",
    "notes_criollo": "¡Encontramos el problema de raiz! Todo este tiempo el 'instinto de comer' "
                     "empujaba a la accion 16, que en Crafter es FABRICAR ESPADA DE HIERRO, no "
                     "comer. Por eso el bicho 'comia' 52 veces y nunca se llenaba: en realidad "
                     "estaba fabricando espadas con la pulsion de hambre. Comer de verdad es la "
                     "accion 5 (do), que come la vaca o planta que tengas adelante. Corregimos el "
                     "mapa de acciones y ahora SI el instinto deberia comer de verdad.",
}, open(out, "w"), indent=2)
print(f" Guardado en: {out}")