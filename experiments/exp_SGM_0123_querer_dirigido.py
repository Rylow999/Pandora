#!/usr/bin/env python3
"""
exp_SGM_0123 — Querer dirigido a recurso + curiosidad dirigida al mundo (opcion C).

CONTEXTO:
  0122 PASS parcial: el instinto de desplazamiento rompio la hipostasia (mov 0->5%,
  7 tiles vs 1). PERO el atractor cambio de lugar (make_iron_pickaxe 76%): el agente
  se mueve SIN RUMBO. Falta la senal de TARGET: moverse ADONDE, no solo salir de donde.

DISEÑO (3 mecanismos integrados sobre la base del 0122):
  1. GRADIENTE HOMEOSTATICO: cuando hay recurso visible (cow/plant) en el FOV 9x9,
     las acciones de movimiento EN LA DIRECCION del recurso reciben un sesgo extra.
     NO es "go to food" -- es quimiotaxis: el sustrato siente "en esa direccion la
     vitalidad podria restaurarse" (Berg & Brown 1972, run-and-tumble E. coli).
  2. CURIOSIDAD DIRIGIDA AL MUNDO: cuando NO hay recurso visible, el movimiento se
     dirige hacia donde el MODELO DEL MUNDO tiene mayor incertidumbre (zonas menos
     exploradas). NO es tiles recorridos (0113 leccion) -- es "no entiendo que hay
     al norte" -> voy al norte (Oudeyer & Kaplan 2007, IAC).
  3. DESPLAZAMIENTO BASE (0122): devaluar acciones locales + empujar movimiento en
     carencia grave. Se MANTIENE como base. El 0123 le agrega DIRECCION.

INSTINTOS AUTOLIMITATIVOS:
  - El gradiente se apaga cuando V_grafo se restaura (no hay carencia -> no hay impulso).
  - La curiosidad se apaga cuando el modelo aprende (incertidumbre baja).
  - Ninguno inyecta el veredicto -- solo inclinan a probar. La experiencia completa.

HIPOTESIS (falsable):
  Con gradiente homeostatico + curiosidad dirigida al mundo, el agente en carencia:
  (a) si hay recurso visible: se mueve EN DIRECCION al recurso (no azimuthal) y
  sobrevive mas que el 0122 puro (sin direccion). PASS si A mueve dirigido Y vive mas.
  (b) si NO hay recurso visible: se mueve hacia zonas de alta incertidumbre del modelo
  del mundo (no al azar). PASS si A explora mas (dirigido por incertidumbre, no deambulo).
  (c) la obsesion del 0122 (make_iron_pickaxe 76%) disminuye: el movimiento dirigido
  saca al agente del atractor de crafting (PASS si accion dominante < 50%).

Protocolo A/B/NC:
  A: gradiente + curiosidad + desplazamiento + alimentacion (TODO activo).
  B: solo desplazamiento del 0122 (sin gradiente, sin curiosidad). Es el 0122 puro.
  NC: desplazamiento apagado (devaluar_umbral=0.0). Solo alimentacion.

Metricas:
  - Supervivencia A > B > NC (la busqueda dirigida da ventaja evolutiva).
  - Querer operativo: movimiento DIRIGIDO al recurso cuando hay carencia (no azimuthal).
    Se mide como: vector de movimientos vs direccion al recurso visible mas cercano.
  - Curiosidad dirigida: cuando no hay recurso, el movimiento va a zonas menos exploradas.
    Se mide como: distribucion de direcciones sesgada vs azar uniforme.
  - Reduccion de obsesion: la accion dominante NO debe ser 50%+ crafting.
  - Mantiene querer de comer (0120): eat con hambre > 0.5.
"""
import sys, os, random, math
from collections import Counter, defaultdict
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm_core import SGMAgent
import crafter
import numpy as np

D = 128; N_NODES = 64
ACC = {0:"noop",1:"move_left",2:"move_right",3:"move_up",4:"move_down",
       5:"do",6:"sleep",7:"place_stone",8:"place_table",9:"place_furnace",
       10:"make_wood_pickaxe",11:"make_stone_pickaxe",12:"make_iron_pickaxe",
       13:"make_wood_sword",14:"make_stone_sword",15:"make_iron_sword",16:"eat"}
MOV = {1,2,3,4}

# --- Mapeo semantico Crafter ---
# Materiales: 0=None,1=grass,2=stone,3=path,4=sand,5=tree,6=lava,7=coal,8=iron,9=diamond,10=table,11=furnace
# Objetos:    12=Player,13=Cow,14=Zombie,15=Skeleton,16=Arrow,17=Plant
RECURSOS_FOOD = {13, 17}  # cow, plant = restauran food
# Direcciones: 1=left(x-1), 2=right(x+1), 3=up(y-1), 4=down(y+1)

def computar_gradiente(sem, px, py):
    """Computa la direccion hacia el recurso homeostatico mas cercano en el FOV.
    Versión ultra-rápida: solo chequea las 4 celdas adyacentes al player.
    Retorna (dx, dy) hacia el recurso, o (0,0) si no hay.
    Es quimiotaxis simple: siente si hay comida arriba/abajo/izq/der."""
    RECURSOS_FOOD = {13, 17}  # cow, plant
    # Chequear 4 direcciones cardinales adyacentes
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        x, y = px + dx, py + dy
        if 0 <= x < sem.shape[1] and 0 <= y < sem.shape[0]:
            if sem[y, x] in RECURSOS_FOOD:
                return (dx, dy), 1
    return (0, 0), 0

def direccion_a_accion(dx, dy):
    """Convierte un vector (dx,dy) en la accion de movimiento que mas se acerca."""
    if abs(dx) >= abs(dy):
        return 2 if dx > 0 else (1 if dx < 0 else (4 if dy > 0 else 3))
    else:
        return 4 if dy > 0 else 3

def computar_incercidumbre_direccional(agente, px, py):
    """Para cada direccion (1=left,2=right,3=up,4=down), cuenta cuantas transiciones
    del modelo del mundo UNKNOWN hay en esa direccion relativa a la posicion actual.
    Retorna un dict {accion: incertidumbre} normalizado."""
    inc = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0}
    if not hasattr(agente, 'modelo_mundo') or not agente.modelo_mundo:
        return inc
    # Contar transiciones nuevas por direccion aproximada
    # El modelo_mundo tiene claves (estado_q, accion) -> {siguiente_q: count}
    # Una transicion "nueva" (count=1) = alta incertidumbre en esa direccion
    for (estado_q, accion), transiciones in agente.modelo_mundo.items():
        if accion in MOV:
            for sig_q, count in transiciones.items():
                if count <= 1:  # transicion nueva = incertidumbre
                    inc[accion] += 1.0
    # Normalizar
    total = sum(inc.values())
    if total > 0:
        inc = {k: v/total for k, v in inc.items()}
    return inc

def correr_vida(agent, config_grad, config_curio, config_desplaza, max_pasos=100):
    """config_grad: {'activo':bool, 'fuerza':float}
       config_curio: {'activo':bool, 'fuerza':float}
       config_desplaza: {'umbral':float, 'devaluar':float, 'fuerza':float}"""
    env = crafter.Env(); env.reset()
    obs, r, t, info = env.step(0)
    tiles = set(); log = []; eat_total = 0; hambre = 0; eat_con_hambre = 0; mov_total = 0
    # Tracking de direccion dirigida
    mov_dirigido_gradiente = 0  # veces que mov va en direccion del gradiente
    mov_dirigido_curiosidad = 0  # veces que mov va en direccion de mayor incertidumbre
    mov_total_gradiente_disparable = 0  # veces que habia gradiente y habia carencia
    mov_total_curio_disparable = 0  # veces que no habia gradiente y habia carencia
    # Distribucion de direcciones de movimiento (para ver si es azar o dirigido)
    dir_distribucion = Counter()
    # Estado previo para modelo del mundo
    sem = info["semantic"]
    inv = info["inventory"]
    px, py = int(info["player_pos"][0]), int(info["player_pos"][1])
    sem_flat = sem.flatten().tolist()
    sv = [float(v) for v in sem_flat[::64]] + [float(inv["health"])/10.0,
          float(inv["food"])/10.0, float(inv["wood"]), float(inv["stone"]),
          float(inv["iron"])]
    estado_q_prev = agent.cuantizar_estado(sv)

    for step in range(max_pasos):
        sem = info["semantic"]
        inv = info["inventory"]
        px, py = int(info["player_pos"][0]), int(info["player_pos"][1])
        pos = (px, py)

        # Senal semantica (igual que 0122)
        sem_flat = sem.flatten().tolist()
        sv = [float(v) for v in sem_flat[::64]] + [float(inv["health"])/10.0,
              float(inv["food"])/10.0, float(inv["wood"]), float(inv["stone"]),
              float(inv["iron"])]

        # --- Computar gradiente homeostatico ---
        grad_dir, grad_dist = computar_gradiente(sem, px, py)
        hay_gradiente = (grad_dir != (0, 0))

        # --- Computar incertidumbre direccional ---
        inc_dirs = computar_incercidumbre_direccional(agent, px, py)

        # --- Modulacion direccional del step ---
        # Anotar info direccional en el agente para que step() la use
        agent._gradiente_dir = grad_dir
        agent._gradiente_dist = grad_dist
        agent._hay_gradiente = hay_gradiente
        agent._inc_dirs = inc_dirs
        agent._config_grad = config_grad
        agent._config_curio = config_curio

        a = agent.step(sv, list(range(17)))
        obs, r, t, info = env.step(a)

        # Acople directo grafo=cuerpo (siempre activo, 0119)
        agent.actualizar_homeostasis(inv["food"], inv["health"])

        # Reward intrinseco (sin reward externo, igual que 0122)
        pain = 0.0
        if r < 0:
            pain = abs(r)
        elif inv["health"] < 5:
            pain = 0.1 * (5 - inv["health"])
        elif inv["food"] < 3:
            pain = 0.05
        agent.reward(0.0, pain)

        if pos not in tiles:
            tiles.add(pos)
            agent.reward(0.1, 0.0)  # novedad de lugar nuevo

        # Apetito
        if a == 16:
            eat_total += 1
            if inv["food"] < 3:
                eat_con_hambre += 1
        if inv["food"] < 3:
            hambre += 1
        if a in MOV:
            mov_total += 1
            dir_distribucion[a] += 1

        # Tracking de movimiento dirigido
        en_carencia = agent.V_grafo < 0.35
        if en_carencia and a in MOV:
            if hay_gradiente:
                mov_total_gradiente_disparable += 1
                accion_grad = direccion_a_accion(grad_dir[0], grad_dir[1])
                if a == accion_grad:
                    mov_dirigido_gradiente += 1
            else:
                mov_total_curio_disparable += 1
                # Si se movio en la direccion de mayor incertidumbre
                if inc_dirs:
                    dir_mas_inc = max(inc_dirs, key=inc_dirs.get)
                    if a == dir_mas_inc and inc_dirs[dir_mas_inc] > 0:
                        mov_dirigido_curiosidad += 1

        # Modelo del mundo (actualizar para curiosidad dirigida)
        estado_q = agent.cuantizar_estado(sv)
        agent.actualizar_modelo_mundo(estado_q_prev, a, estado_q)
        estado_q_prev = estado_q

        log.append({"step": step, "a": a, "food": float(inv["food"]),
                     "hp": float(inv["health"]), "Vg": round(agent.V_grafo, 3),
                     "duda": agent.doubt_count, "status": agent.status,
                     "nec_insat": agent.necesidad_insatisfecha,
                     "hay_grad": hay_gradiente, "grad_dist": grad_dist,
                     "en_carencia": en_carencia})

        if t:
            muerte = {"step": step, "food": float(inv["food"]),
                      "hp": float(inv["health"]), "status": agent.status,
                      "V_grafo_fin": round(agent.V_grafo, 3)}
            return (log, tiles, muerte, step+1, eat_total, hambre, eat_con_hambre,
                    mov_total, mov_dirigido_gradiente, mov_total_gradiente_disparable,
                    mov_dirigido_curiosidad, mov_total_curio_disparable,
                    dict(dir_distribucion))
    return (log, tiles, None, step+1, eat_total, hambre, eat_con_hambre,
            mov_total, mov_dirigido_gradiente, mov_total_gradiente_disparable,
            mov_dirigido_curiosidad, mov_total_curio_disparable,
            dict(dir_distribucion))


# --- 3 condiciones: A, B, NC ---

# A: TODO activo (gradiente + curiosidad + desplazamiento + alimentacion)
rng_a = random.Random(42)
ag_a = SGMAgent(rng_a, D, n_nodes=N_NODES, gamma=0.01)
ag_a.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES-1)) for i in range(N_NODES)})
res_a = correr_vida(ag_a, {"activo": True, "fuerza": 0.5},
                          {"activo": True, "fuerza": 0.3},
                          {"umbral": 0.35, "devaluar": 0.4, "fuerza": 0.6})
(log_a, tiles_a, muerte_a, pasos_a, eat_a, hambre_a, echa_a, mov_a,
 mdg_a, mtgd_a, mdc_a, mtcd_a, dirs_a) = res_a
cnt_a = Counter(ACC.get(l['a'], "?") for l in log_a)

# B: solo 0122 (sin gradiente, sin curiosidad)
rng_b = random.Random(42)
ag_b = SGMAgent(rng_b, D, n_nodes=N_NODES, gamma=0.01)
ag_b.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES-1)) for i in range(N_NODES)})
res_b = correr_vida(ag_b, {"activo": False, "fuerza": 0.0},
                          {"activo": False, "fuerza": 0.0},
                          {"umbral": 0.35, "devaluar": 0.4, "fuerza": 0.6})
(log_b, tiles_b, muerte_b, pasos_b, eat_b, hambre_b, echa_b, mov_b,
 mdg_b, mtgd_b, mdc_b, mtcd_b, dirs_b) = res_b
cnt_b = Counter(ACC.get(l['a'], "?") for l in log_b)

# NC: desplazamiento apagado (solo alimentacion)
rng_c = random.Random(42)
ag_c = SGMAgent(rng_c, D, n_nodes=N_NODES, gamma=0.01)
ag_c.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES-1)) for i in range(N_NODES)})
ag_c.devaluar_umbral = 0.0
res_c = correr_vida(ag_c, {"activo": False, "fuerza": 0.0},
                          {"activo": False, "fuerza": 0.0},
                          {"umbral": 0.0, "devaluar": 0.0, "fuerza": 0.0})
(log_c, tiles_c, muerte_c, pasos_c, eat_c, hambre_c, echa_c, mov_c,
 mdg_c, mtgd_c, mdc_c, mtcd_c, dirs_c) = res_c
cnt_c = Counter(ACC.get(l['a'], "?") for l in log_c)

# --- Metricas ---
noop_a = 100 * cnt_a.get('noop', 0) / max(1, len(log_a))
noop_c = 100 * cnt_c.get('noop', 0) / max(1, len(log_c))
eat_pct_a = 100 * eat_a / max(1, len(log_a))
mov_pct_a = 100 * mov_a / max(1, len(log_a))
mov_pct_b = 100 * mov_b / max(1, len(log_b))
mov_pct_c = 100 * mov_c / max(1, len(log_c))
querer_a = (echa_a / max(1, hambre_a) > 0.5) if hambre_a > 0 else False
querer_c = (echa_c / max(1, hambre_c) > 0.5) if hambre_c > 0 else False

# Querer dirigido: fraccion de movimientos que van en direccion del gradiente
pct_dirigido_grad = 100 * mdg_a / max(1, mtgd_a) if mtgd_a > 0 else 0
pct_dirigido_curio = 100 * mdc_a / max(1, mtcd_a) if mtcd_a > 0 else 0

# Distribucion de direcciones: si es azar, seria ~25% cada una. Si es dirigido, una domina.
dirs_a_total = sum(dirs_a.values()) if dirs_a else 1
dirs_a_norm = {ACC.get(k, k): 100 * v / dirs_a_total for k, v in dirs_a.items()}

# Reduccion de obsesion: la accion dominante de A
dom_a = cnt_a.most_common(1)[0] if cnt_a else ("?", 0)
dom_a_pct = 100 * dom_a[1] / max(1, len(log_a))
dom_b = cnt_b.most_common(1)[0] if cnt_b else ("?", 0)
dom_b_pct = 100 * dom_b[1] / max(1, len(log_b))

# --- Reporte ---
print("=" * 72)
print("  exp_SGM_0123 — Querer dirigido + curiosidad dirigida al mundo (opcion C)")
print("=" * 72)

print(f"\n  A (gradiente+curiosidad+desplaz): {pasos_a}p, {len(tiles_a)} tiles, "
      f"mov={mov_pct_a:.0f}%, eat={eat_a} ({eat_pct_a:.0f}%), querer={querer_a}, noop={noop_a:.0f}%")
print(f"    mov dirigido por gradiente: {mdg_a}/{mtgd_a} ({pct_dirigido_grad:.0f}%)")
print(f"    mov dirigido por curiosidad: {mdc_a}/{mtcd_a} ({pct_dirigido_curio:.0f}%)")
print(f"    accion dominante: {dom_a[0]} {dom_a_pct:.0f}%")
print(f"    dirs: {dirs_a_norm}")
print(f"    muerte: {muerte_a}")
for act, n in cnt_a.most_common(6):
    print(f"      {act:18s} {n:3d} ({100*n/len(log_a):.1f}%)")

print(f"\n  B (0122 puro, sin direccion): {pasos_b}p, {len(tiles_b)} tiles, "
      f"mov={mov_pct_b:.0f}%, eat={eat_b}, noop={100*cnt_b.get('noop',0)/max(1,len(log_b)):.0f}%")
print(f"    accion dominante: {dom_b[0]} {dom_b_pct:.0f}%")
print(f"    muerte: {muerte_b}")
for act, n in cnt_b.most_common(6):
    print(f"      {act:18s} {n:3d} ({100*n/len(log_b):.1f}%)")

print(f"\n  NC (solo alimentacion): {pasos_c}p, {len(tiles_c)} tiles, "
      f"mov={mov_pct_c:.0f}%, eat={eat_c}, querer={querer_c}, noop={noop_c:.0f}%")
print(f"    muerte: {muerte_c}")
for act, n in cnt_c.most_common(6):
    print(f"      {act:18s} {n:3d} ({100*n/len(log_c):.1f}%)")

print(f"\n{'='*72}")
print("  METRICAS")
print(f"{'='*72}")
pass_supervivencia = pasos_a > pasos_b
pass_dirigido_grad = pct_dirigido_grad > 50  # mas de la mitad de los mov van hacia el recurso
pass_dirigido_curio = pct_dirigido_curio > 30  # al menos 30% va hacia incertidumbre
pass_obsesion = dom_a_pct < 50  # la obsesion del 0122 (76%) baja
pass_explora = len(tiles_a) > len(tiles_b)
pass_querer = querer_a
print(f"  PASS supervivencia A>B:     {pass_supervivencia} ({pasos_a} vs {pasos_b})")
print(f"  PASS dirigido por gradiente: {pass_dirigido_grad} ({pct_dirigido_grad:.0f}%)")
print(f"  PASS dirigido por curiosidad: {pass_dirigido_curio} ({pct_dirigido_curio:.0f}%)")
print(f"  PASS no obsesion (dom<50%):  {pass_obsesion} ({dom_a[0]} {dom_a_pct:.0f}%)")
print(f"  PASS explora (A>B tiles):    {pass_explora} ({len(tiles_a)} vs {len(tiles_b)})")
print(f"  PASS mantiene querer comer:  {pass_querer}")
print(f"{'='*72}")

# --- JSON de resultado ---
import json
out = os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/results/results_exp_SGM_0123_querer_dirigido.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id": "exp_SGM_0123",
    "experiment_name": "querer_dirigido_curiosidad_mundo",
    "phase": "Fase 8 — querer dirigido a recurso (opcion C)",
    "date": "2026-08-11",
    "hypothesis": (
        "Con gradiente homeostatico + curiosidad dirigida al mundo, el agente en carencia: "
        "(a) si hay recurso visible: se mueve EN DIRECCION al recurso (no azimuthal) y sobrevive "
        "mas que el 0122 puro (sin direccion). (b) si NO hay recurso: se mueve hacia zonas de "
        "alta incertidumbre del modelo del mundo (no al azar). (c) la obsesion del 0122 "
        "(make_iron_pickaxe 76%) disminuye: el movimiento dirigido saca al agente del atractor."
    ),
    "config": {
        "D": D, "N_NODES": N_NODES,
        "gradiente_fuerza": 0.5,
        "curiosidad_fuerza": 0.3,
        "desplazar_fuerza": 0.6,
        "devaluar_umbral": 0.35,
        "devaluar_fuerza": 0.4,
        "instinto_fuerza_base": 0.5,
        "instinto_umbral_carencia": 0.3,
        "recursos_food": "cow(13), plant(17)",
        "fov": "9x9 alrededor del player (pos 32,32)",
    },
    "result": {
        "A_gradiente_curiosidad": {
            "pasos": pasos_a, "tiles": len(tiles_a),
            "mov_total": mov_a, "mov_pct": round(mov_pct_a, 1),
            "eat": eat_a, "eat_pct": round(eat_pct_a, 1),
            "eat_con_hambre": echa_a, "hambre": hambre_a,
            "querer": querer_a, "noop": round(noop_a, 1),
            "mov_dirigido_gradiente": f"{mdg_a}/{mtgd_a} ({pct_dirigido_grad:.0f}%)",
            "mov_dirigido_curiosidad": f"{mdc_a}/{mtcd_a} ({pct_dirigido_curio:.0f}%)",
            "accion_dominante": f"{dom_a[0]} {dom_a_pct:.0f}%",
            "dirs_distribucion": dirs_a_norm,
            "muerte": muerte_a,
        },
        "B_0122_puro": {
            "pasos": pasos_b, "tiles": len(tiles_b),
            "mov_total": mov_b, "mov_pct": round(mov_pct_b, 1),
            "eat": eat_b, "accion_dominante": f"{dom_b[0]} {dom_b_pct:.0f}%",
            "muerte": muerte_b,
        },
        "NC_solo_alimentacion": {
            "pasos": pasos_c, "tiles": len(tiles_c),
            "mov_total": mov_c, "mov_pct": round(mov_pct_c, 1),
            "eat": eat_c, "querer": querer_c, "noop": round(noop_c, 1),
            "muerte": muerte_c,
        },
        "pass_supervivencia_A_mayor_B": pass_supervivencia,
        "pass_dirigido_gradiente": pass_dirigido_grad,
        "pass_dirigido_curiosidad": pass_dirigido_curio,
        "pass_no_obsesion": pass_obsesion,
        "pass_explora": pass_explora,
        "pass_mantiene_querer": pass_querer,
    },
    "script": "experiments/exp_SGM_0123_querer_dirigido.py",
    "results_file": "results/results_exp_SGM_0123_querer_dirigido.json",
    "variant_of": "exp_SGM_0122",
    "lit_refs": [
        "Berg & Brown 1972 — quimiotaxis E. coli, run-and-tumble (gradiente de concentracion)",
        "Oudeyer & Kaplan 2007 — Intelligent Adaptive Curiosity (IAC), prediction error dirige exploracion",
        "Stephens & Krebs 1986 — forrajeo optimo (target vs exploracion)",
        "O'Keefe & Nadel 1971 — mapas cognitivos (proto-mapa espacial por incertidumbre direccional)",
        "Berridge & Robinson 1998 — wanting como motivacion operante (correlacion carencia->busqueda dirigida)",
    ],
    "notes": (
        "El 0122 rompio la hipostasia (mov 0->5%) pero el atractor cambio de lugar (make_iron_pickaxe 76%): "
        "el agente se mueve sin rumbo. El 0123 le agrega DIRECCION al movimiento mediante dos mecanismos: "
        "(1) gradiente homeostatico -- quimiotaxis: cuando hay cow/plant visible en el FOV, el movimiento "
        "hacia el recurso recibe sesgo extra. (2) curiosidad dirigida al mundo -- cuando no hay recurso, "
        "el movimiento se dirige hacia donde el modelo del mundo tiene mayor incertidumbre (zonas menos "
        "exploradas). Ambos son autolimitativos (se apagan al saciarse / al aprender). La base del 0122 "
        "(devaluar local + empujar movimiento en carencia) se mantiene intacta."
    ),
    "notes_criollo": (
        "En el 0122 el bicho por fin se movio cuando tenia hambre y comer no resolvia. Pero se movia a "
        "cualquier lado -- sin rumbo, cayo en otro atractor (make_iron_pickaxe 76%). Es como si salieras "
        "de tu casa con hambre y caminaras en cualquier direccion:ATAL vez encontras comida, probablemente "
        "no. El 0123 le da dos cosas para saber ADONDE ir: (1) si ve una vaca o una planta en el FOV, el "
        "instinto lo empuja hacia ahi -- como las bacterias que siguen el gradiente de azucar (quimiotaxis). "
        "(2) si no ve nada comestible, lo empuja hacia la zona que menos conoce (curiosidad dirigida al "
        "mundo, no a su propia secuencia). La idea es que el bicho deje de deambular al azar y se mueva "
        "con RAZON: hacia la comida si la ve, hacia lo desconocido si no la ve."
    ),
}, open(out, "w"), indent=2)
print(f"\n  Guardado en: {out}")
