#!/usr/bin/env python3
"""
exp_SGM_0110 — Decoder L2 como interfaz consciente (detector de loops).
El bigrama observa las ultimas N acciones del agente. Si predice la misma
accion K veces seguidas, dispara una seal de "loop" que baja la vitalidad
del nodo repetido. El agente "se da cuenta" de que esta en un loop.

Hipotesis: El decoder bigrama detecta loops en el comportamiento del agente
y genera una seal que rompe el atractor, aumentando la variedad de acciones.

NC: comparar contra un agente sin decoder (solo vitalidad + duda + reward).
Si el decoder ayuda, el agente con decoder tendra mas variedad de acciones.
"""
import sys, os, random, math
from collections import Counter
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"))
from sgm.core.sgm_core import SGMAgent
import crafter

random.seed(42); rng = random.Random(42)
D=128; N_NODES=64; REWARD_NOV=0.1
VENTANA=50; CHECK_CADA=10; TOPE_LOOP=5
ACC = {0:"noop",1:"move_left",2:"move_right",3:"move_up",4:"move_down",
       5:"do",6:"sleep",7:"place_stone",8:"place_table",9:"place_furnace",
       10:"make_wood_pickaxe",11:"make_stone_pickaxe",12:"make_iron_pickaxe",
       13:"make_wood_sword",14:"make_stone_sword",15:"make_iron_sword",16:"eat"}

def entrenar_bigrama(seq, V=17):
    if len(seq) < 3: return None
    counts = {a: {b: 0.0 for b in range(V)} for a in range(V)}
    for i in range(len(seq)-1):
        a, b = seq[i], seq[i+1]
        if a in counts and b in counts[a]:
            counts[a][b] += 1.0
    model = {}
    for a in range(V):
        tot = sum(counts[a].values())
        if tot > 0:
            model[a] = {b: counts[a][b]/tot for b in range(V)}
        else:
            model[a] = {b: 1.0/V for b in range(V)}
    return model

def predecir_top1(model, accion, V=17):
    if model is None or accion not in model: return None, 0.0
    best, bid = -1.0, 0
    for b in range(V):
        p = model[accion].get(b, 0.0)
        if p > best: best, bid = p, b
    return bid, best

def correr_episodio(agent, usar_decoder=False, n_steps=300):
    env = crafter.Env(); env.reset()
    obs,r,t,info = env.step(0)
    tiles=set(); log=[]; historial=[]; loop_counter=0; loops_detectados=0

    for step in range(n_steps):
        sem=info["semantic"].flatten().tolist(); inv=info["inventory"]
        pos=tuple(info["player_pos"])
        sv=[float(v) for v in sem[::64]]+[float(inv["health"])/10.0,float(inv["food"])/10.0,
           float(inv["wood"]),float(inv["stone"]),float(inv["iron"])]
        
        senal_loop = False
        if usar_decoder and step > 0 and step % CHECK_CADA == 0 and len(historial) >= VENTANA:
            ventana = historial[-VENTANA:]
            model = entrenar_bigrama(ventana)
            if model:
                ultima = historial[-1]
                pred, _ = predecir_top1(model, ultima)
                if pred is not None and pred == ultima:
                    loop_counter += 1
                    if loop_counter >= TOPE_LOOP:
                        senal_loop = True
                        loops_detectados += 1
                        # Bajar vitalidad del nodo que se repite
                        if ultima < len(agent.vitalidad):
                            agent.vitalidad[ultima] *= 0.5
                        loop_counter = 0
                else:
                    loop_counter = 0
        
        a=agent.step(sv,list(range(17)))
        obs,r,t,info=env.step(a)
        ri=0.0
        if pos not in tiles: tiles.add(pos); ri=REWARD_NOV
        pain=0.0
        if r<0: pain=abs(r)
        elif inv["health"]<5: pain=0.1*(5-inv["health"])
        elif inv["food"]<3: pain=0.05
        agent.reward(r+ri, pain)
        historial.append(a)
        log.append({"step":step,"a":ACC.get(a,"?"),"hp":inv["health"],
                    "food":inv["food"],"nov":ri,"Ea":round(agent.E_acumulado,3),
                    "st":agent.status,"d":agent.doubt_count,"loop":senal_loop})
        if t: break
    
    return log, tiles, inv, step+1, loops_detectados

# === AGENTE A: con decoder ===
rng_a = random.Random(42)
agent_a = SGMAgent(rng_a, D, n_nodes=N_NODES, gamma=0.01)
agent_a.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES-1)) for i in range(N_NODES)})

print("="*70)
print("  exp_SGM_0110 — Decoder L2 como interfaz consciente")
print("="*70)

log_a, tiles_a, inv_a, pasos_a, loops_a = correr_episodio(agent_a, usar_decoder=True)
cnt_a = Counter(l['a'] for l in log_a)
noop_a = cnt_a.get('noop',0)/max(1,len(log_a))*100
variedad_a = len(cnt_a)

print(f"\n  CON DECODER: {pasos_a} pasos, {len(tiles_a)} tiles, {noop_a:.1f}% noop")
print(f"  Loops detectados: {loops_a}, variedad acciones: {variedad_a}")
print(f"  Status: {agent_a.status}, Duda: {agent_a.doubt_count}")
for act,n in cnt_a.most_common():
    print(f"    {act:20s} {n:3d} ({100*n/len(log_a):.1f}%)")
print(f"\n  Cada 30 pasos:")
for l in log_a[::30]:
    print(f"    p{l['step']:03d}: {l['a']:18s} nov={l['nov']:.1f} loop={l['loop']} Ea={l['Ea']:.2f} d={l['d']} st={l['st'][:8]}")

# === AGENTE B (NC): sin decoder ===
rng_b = random.Random(42)
agent_b = SGMAgent(rng_b, D, n_nodes=N_NODES, gamma=0.01)
agent_b.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES-1)) for i in range(N_NODES)})

log_b, tiles_b, inv_b, pasos_b, loops_b = correr_episodio(agent_b, usar_decoder=False)
cnt_b = Counter(l['a'] for l in log_b)
noop_b = cnt_b.get('noop',0)/max(1,len(log_b))*100
variedad_b = len(cnt_b)

print(f"\n  SIN DECODER (NC): {pasos_b} pasos, {len(tiles_b)} tiles, {noop_b:.1f}% noop")
print(f"  Variedad acciones: {variedad_b}")
print(f"  Status: {agent_b.status}, Duda: {agent_b.doubt_count}")
for act,n in cnt_b.most_common():
    print(f"    {act:20s} {n:3d} ({100*n/len(log_b):.1f}%)")

# === COMPARACION ===
print(f"\n{'='*70}")
print("  COMPARACION")
print(f"{'='*70}")
print(f"  Con decoder:     tiles={len(tiles_a):3d} noop={noop_a:5.1f}% variedad={variedad_a} loops={loops_a}")
print(f"  Sin decoder (NC): tiles={len(tiles_b):3d} noop={noop_b:5.1f}% variedad={variedad_b}")
print(f"  Diferencia tiles: {len(tiles_a)-len(tiles_b):+d}")
print(f"  Diferencia noop:  {noop_a-noop_b:+.1f}%")
print(f"  Diferencia variedad: {variedad_a-variedad_b:+d}")
print(f"{'='*70}")

pass_test = variedad_a > variedad_b and noop_a <= noop_b
print(f"\n  PASS (decoder aumenta variedad sin aumentar noop): {pass_test}")

# Guardar
import json
out=os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/results/results_exp_SGM_0110_decoder_consciente.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id":"exp_SGM_0110",
    "experiment_name":"decoder_l2_interfaz_consciente",
    "phase":"Auditoria — decoder como interfaz consciente",
    "date":"2026-08-06",
    "hypothesis":"El decoder bigrama detecta loops en el comportamiento del agente y genera una seal que rompe el atractor, aumentando la variedad de acciones comparado con un agente sin decoder.",
    "config":{"D":D,"N_NODES":N_NODES,"reward_novedad":REWARD_NOV,"ventana_decoder":VENTANA,"check_cada":CHECK_CADA,"tope_loop":TOPE_LOOP},
    "result":{"con_decoder":{"pasos":pasos_a,"tiles":len(tiles_a),"noop_pct":round(noop_a,1),"variedad":variedad_a,"loops":loops_a,"status":agent_a.status},
              "sin_decoder_nc":{"pasos":pasos_b,"tiles":len(tiles_b),"noop_pct":round(noop_b,1),"variedad":variedad_b,"status":agent_b.status},
              "pass":pass_test},
    "script":"experiments/exp_SGM_0110_decoder_consciente.py",
    "results_file":"results/results_exp_SGM_0110_decoder_consciente.json",
    "variant_of":"exp_SGM_0108",
    "lit_refs":["CLARION dual-level: implicit/explicit cognition","Unconscious cognition - implicit processing Wikipedia"],
    "notes":"Decoder bigrama como capa explicita (consciente) que observa el comportamiento implicito (PPR) y detecta loops. Al detectar loop, baja vitalidad del nodo repetido.",
    "notes_criollo":"El decoder es como el consciente mirando lo que hace el inconsciente. Si el inconsciente se queda pegado haciendo siempre lo mismo (loop), el consciente se da cuenta y lo sacude bajandole las pilas a esa accion. Es como aburrirte de rascarte la cabeza y decidir hacer otra cosa."
}, open(out,"w"), indent=2)
print(f"\n  Guardado en: {out}")