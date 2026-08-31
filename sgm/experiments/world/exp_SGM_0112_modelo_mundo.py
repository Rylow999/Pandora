#!/usr/bin/env python3
"""
exp_SGM_0112 — Decoder L2 como modelo del mundo (forward model).
El bigrama aprende transiciones (estado_cuantizado, accion) -> siguiente_estado_cuantizado.
Si el agente puede predecir el siguiente estado antes de actuar, tiene un modelo del mundo.
Si la prediccion difiere de lo que pasa, hay error de prediccion = sorpresa = senal de aprendizaje.

Hipotesis: El decoder bigrama puede predecir la proxima posicion del agente
mejor que azar (NC: shuffle de transiciones). Si puede, hay un modelo del mundo
funcional. La sorpresa (error de prediccion) genera una senal que empuja al agente
a explorar donde el modelo falla (hay informacion nueva para aprender).

Metodo:
  1. 1er episodio: recolectar transiciones (pos_cuantizada, accion) -> pos_siguiente.
  2. Entrenar bigrama sobre esas transiciones.
  3. 2do episodio: predecir la siguiente posicion antes de actuar. Medir accuracy.
  4. NC: entrenar con transiciones shuffladas. Si accuracy real >> NC, hay modelo.
"""
import sys, os, random, math
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from sgm.core.sgm_core import SGMAgent
import crafter

random.seed(42); rng = random.Random(42)
D=128; N_NODES=64; REWARD_NOV=0.1
ACC = {0:"noop",1:"move_left",2:"move_right",3:"move_up",4:"move_down",
       5:"do",6:"sleep",7:"place_stone",8:"place_table",9:"place_furnace",
       10:"make_wood_pickaxe",11:"make_stone_pickaxe",12:"make_iron_pickaxe",
       13:"make_wood_sword",14:"make_stone_sword",15:"make_iron_sword",16:"eat"}

def cuantizar_pos(pos, grid=4):
    """Cuantizar posicion a una de grid*grid buckets."""
    x, y = int(pos[0]), int(pos[1])
    return (x // grid, y // grid)

def correr_y_recolectar(agent, n_steps=300):
    """Episodio 1: recolectar transiciones para entrenar el modelo."""
    env = crafter.Env(); env.reset()
    obs,r,t,info = env.step(0)
    tiles=set(); transiciones=[]; log=[]
    for step in range(n_steps):
        sem=info["semantic"].flatten().tolist(); inv=info["inventory"]
        pos=tuple(info["player_pos"])
        sv=[float(v) for v in sem[::64]]+[float(inv["health"])/10.0,float(inv["food"])/10.0,
           float(inv["wood"]),float(inv["stone"]),float(inv["iron"])]
        a=agent.step(sv,list(range(17)))
        obs,r,t,info=env.step(a)
        ri=0.0
        if pos not in tiles: tiles.add(pos); ri=REWARD_NOV
        pain=0.0
        if r<0: pain=abs(r)
        elif inv["health"]<5: pain=0.1*(5-inv["health"])
        elif inv["food"]<3: pain=0.05
        agent.reward(r+ri, pain)
        pos_next=tuple(info["player_pos"])
        q_pos = cuantizar_pos(pos)
        q_next = cuantizar_pos(pos_next)
        transiciones.append((q_pos, a, q_next))
        log.append({"step":step,"a":ACC.get(a,"?"),"hp":inv["health"],
                    "nov":ri,"Ea":round(agent.E_acumulado,3),"st":agent.status})
        if t: break
    return log, tiles, transiciones, step+1

def entrenar_modelo_mundo(transiciones):
    """Bigrama: (pos_cuantizada, accion) -> pos_siguiente_cuantizada."""
    counts = defaultdict(lambda: defaultdict(int))
    for q_pos, accion, q_next in transiciones:
        key = (q_pos, accion)
        counts[key][q_next] += 1
    modelo = {}
    for key, nexts in counts.items():
        total = sum(nexts.values())
        modelo[key] = {k: v/total for k, v in nexts.items()}
    return modelo

def predecir(modelo, q_pos, accion):
    """Predice la siguiente posicion cuantizada."""
    key = (q_pos, accion)
    if key not in modelo:
        return None, 0.0
    predicciones = modelo[key]
    best, bp = None, 0.0
    for k, p in predicciones.items():
        if p > bp: best, bp = k, p
    return best, bp

def evaluar_modelo(modelo, transiciones):
    """Mide accuracy del modelo sobre las transiciones."""
    correctos = 0; total = 0; conocidas = 0
    for q_pos, accion, q_next in transiciones:
        pred, prob = predecir(modelo, q_pos, accion)
        if pred is not None:
            conocidas += 1
            if pred == q_next:
                correctos += 1
        total += 1
    return correctos, conocidas, total

# === EPISODIO 1: recolectar transiciones ===
print("="*70)
print("  exp_SGM_0112 — Decoder L2 como modelo del mundo (forward model)")
print("="*70)

agent1 = SGMAgent(random.Random(42), D, n_nodes=N_NODES, gamma=0.01)
agent1.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES-1)) for i in range(N_NODES)})
log1, tiles1, transiciones, pasos1 = correr_y_recolectar(agent1)
cnt1 = Counter(l['a'] for l in log1)
print(f"\n  Episodio 1 (recoleccion): {pasos1} pasos, {len(tiles1)} tiles, "
      f"{len(transiciones)} transiciones")
print(f"  Acciones: {dict(cnt1.most_common(5))}")

# === ENTRENAR MODELO DEL MUNDO ===
modelo = entrenar_modelo_mundo(transiciones)
print(f"\n  Modelo del mundo: {len(modelo)} entradas (pos,accion)->pos_next")
n_unicos_estados = len(set(q for q, a, n in transiciones))
print(f"  Estados cuantizados unicos: {n_unicos_estados}")

# === EVALUAR: accuracy real vs NC (shuffeado) ===
correctos, conocidas, total = evaluar_modelo(modelo, transiciones)
accuracy = correctos / max(1, conocidas)
print(f"\n  Accuracy (entradas conocidas): {correctos}/{conocidas} = {accuracy:.2f}")
print(f"  Cobertura: {conocidas}/{total} = {conocidas/max(1,total):.2f}")

# NC: shuffle de transiciones
rng_nc = random.Random(99)
transiciones_shuffled = list(transiciones)
rng_nc.shuffle(transiciones_shuffled)
modelo_nc = entrenar_modelo_mundo(transiciones_shuffled)
correctos_nc, conocidas_nc, total_nc = evaluar_modelo(modelo_nc, transiciones)
accuracy_nc = correctos_nc / max(1, conocidas_nc)
print(f"  NC (shuffle): {correctos_nc}/{conocidas_nc} = {accuracy_nc:.2f}")
print(f"  Diferencia real-NC: {accuracy - accuracy_nc:+.2f}")

# === EPISODIO 2: MISMO agente, usar modelo para predecir y sorpresa ===
# Mismo agente para que las acciones coincidan con lo que el modelo aprendio
env2 = crafter.Env(); env2.reset()
obs,r,t,info = env2.step(0)
tiles2=set(); log2=[]; sorpresas=0; predicciones_hechas=0; correctos_ep2=0

for step in range(200):
    sem=info["semantic"].flatten().tolist(); inv=info["inventory"]
    pos=tuple(info["player_pos"])
    sv=[float(v) for v in sem[::64]]+[float(inv["health"])/10.0,float(inv["food"])/10.0,
       float(inv["wood"]),float(inv["stone"]),float(inv["iron"])]
    
    # Prediccion del modelo ANTES de actuar
    q_pos = cuantizar_pos(pos)
    
    a=agent1.step(sv,list(range(17)))
    
    # Evaluar prediccion
    pred, prob = predecir(modelo, q_pos, a)
    obs,r,t,info=env2.step(a)
    pos_next=tuple(info["player_pos"])
    q_next_real = cuantizar_pos(pos_next)
    
    if pred is not None:
        predicciones_hechas += 1
        if pred == q_next_real:
            correctos_ep2 += 1
        else:
            sorpresas += 1
            # Sorpresa: el modelo fallo. Esto es una senal de aprendizaje.
            # Bajar vitalidad del nodo que no predijo bien para forzar exploracion alli.
            if a < len(agent1.vitalidad):
                agent1.vitalidad[a] *= 0.95  # pequeno penal
    
    ri=0.0
    if pos not in tiles2: tiles2.add(pos); ri=REWARD_NOV
    pain=0.0
    if r<0: pain=abs(r)
    elif inv["health"]<5: pain=0.1*(5-inv["health"])
    elif inv["food"]<3: pain=0.05
    agent1.reward(r+ri, pain)
    log2.append({"step":step,"a":ACC.get(a,"?"),"hp":inv["health"],
                 "pred":pred is not None,"correct":pred==q_next_real if pred else False,
                 "nov":ri,"Ea":round(agent1.E_acumulado,3),"st":agent1.status})
    if t: break

cnt2 = Counter(l['a'] for l in log2)
accuracy_ep2 = correctos_ep2 / max(1, predicciones_hechas)
print(f"\n  Episodio 2 (evaluacion): {step+1} pasos, {len(tiles2)} tiles")
print(f"  Predicciones hechas: {predicciones_hechas}, Correctas: {correctos_ep2}, Accuracy: {accuracy_ep2:.2f}")
print(f"  Sorpresas (prediccion fallo): {sorpresas}")
print(f"  Acciones: {dict(cnt2.most_common(5))}")
print(f"\n  Cada 20 pasos:")
for l in log2[::20]:
    pred_str = f"pred={l['correct']}" if l['pred'] else "pred=?"
    print(f"    p{l['step']:03d}: {l['a']:18s} {pred_str} nov={l['nov']:.1f} Ea={l['Ea']:.2f} st={l['st'][:8]}")

pass_test = accuracy > 0.5 and accuracy > accuracy_nc
print(f"\n{'='*70}")
print(f"  PASS (accuracy>0.5 y >NC): {pass_test}")
print(f"  Accuracy entrenamiento: {accuracy:.2f} vs NC {accuracy_nc:.2f}")
print(f"  Accuracy episodio 2: {accuracy_ep2:.2f}")
print(f"{'='*70}")

import json
out=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "results/results_exp_SGM_0112_modelo_mundo.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id":"exp_SGM_0112",
    "experiment_name":"decoder_l2_modelo_mundo",
    "phase":"Decoder L2 — forward model",
    "date":"2026-08-06",
    "hypothesis":"El decoder bigrama puede aprender transiciones (pos,accion)->pos_siguiente y predecir mejor que azar. La sorpresa (error de prediccion) genera una senal de aprendizaje.",
    "config":{"D":D,"N_NODES":N_NODES,"grid_cuant":8,"ep1_pasos":300,"ep2_pasos":200},
    "result":{"ep1":{"pasos":pasos1,"tiles":len(tiles1),"transiciones":len(transiciones),
              "modelo_entradas":len(modelo),"estados_unicos":n_unicos_estados,
              "accuracy":round(accuracy,3),"accuracy_nc":round(accuracy_nc,3)},
             "ep2":{"pasos":step+1,"tiles":len(tiles2),"predicciones":predicciones_hechas,
              "correctas":correctos_ep2,"accuracy":round(accuracy_ep2,3),
              "sorpresas":sorpresas,"pass":pass_test}},
    "script":"experiments/exp_SGM_0112_modelo_mundo.py",
    "results_file":"results/results_exp_SGM_0112_modelo_mundo.json",
    "variant_of":"exp_SGM_0110",
    "lit_refs":["Forward model predicts next state (Robot Learning Part 5)","WorldCycle: world model consistency over action sequences (2026)"],
    "notes":"Bigrama que en vez de predecir siguiente accion, predice siguiente posicion cuantizada dado (pos_actual, accion). NC: shuffle de transiciones. Episodio 2 usa el modelo para predecir y la sorpresa genera senal.",
    "notes_criollo":"Al agente le ensenamos a imaginar. En el primer episodio recolecta lo que pasa cuando hace cada accion en cada lugar. Despues arma un modelo mental: 'si estoy aca y me muevo para abajo, voy a llegar alla'. En el segundo episodio, antes de moverse intenta predecir a donde va a llegar. Si se equivoca, se sorprende, y esa sorpresa es una senal de que ahi hay algo nuevo para aprender."
}, open(out,"w"), indent=2)
print(f"\n  Guardado en: {out}")
