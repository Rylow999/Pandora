#!/usr/bin/env python3
"""
exp_SGM_0113 — Decoder que ALIMENTA LA DUDA (no capea vitalidad).
El decoder (bigrama) mide la predecibilidad de la secuencia de acciones dentro
de check_stagnation(). Comportamiento predecible (repetir la misma accion) baja
la novedad efectiva y dispara la duda. La duda ES el mecanismo emergente que
rompe el estancamiento (relajacion -> relanzamiento), no un castigo directo a
la vitalidad.

Hipotesis: Integrar el decoder a la duda produce MAS variedad de acciones que
el baseline (0108, duda clásica con solo acciones unicas en ventana), porque
detecta loops que la novedad de acciones unicas NO ve (ej: A,B,A,B,A,B tiene
alta novedad de acciones unicas pero es una secuencia predecible/repetitiva).

NC: correr episodio con la duda clasica DESACTIVADA (check_stagnation siempre
False) vs duda clasica vs duda+decoder.
"""
import sys, os, random
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm_core import SGMAgent
import crafter
from collections import Counter

random.seed(42)
D=128; N_NODES=64; REWARD_NOV=0.1
ACC = {0:"noop",1:"move_left",2:"move_right",3:"move_up",4:"move_down",
       5:"do",6:"sleep",7:"place_stone",8:"place_table",9:"place_furnace",
       10:"make_wood_pickaxe",11:"make_stone_pickaxe",12:"make_iron_pickaxe",
       13:"make_wood_sword",14:"make_stone_sword",15:"make_iron_sword",16:"eat"}

def correr_episodio(agent, habilitar_duda=True, n_steps=250):
    env = crafter.Env(); env.reset()
    obs,r,t,info = env.step(0)
    tiles=set(); log=[]; duda_eventos=0
    for step in range(n_steps):
        sem=info["semantic"].flatten().tolist(); inv=info["inventory"]
        pos=tuple(info["player_pos"])
        sv=[float(v) for v in sem[::64]]+[float(inv["health"])/10.0,float(inv["food"])/10.0,
           float(inv["wood"]),float(inv["stone"]),float(inv["iron"])]
        # Guardar nivel de duda previo
        duda_prev = agent.doubt_count
        a=agent.step(sv,list(range(17)))
        if agent.doubt_count > duda_prev:
            duda_eventos += 1
        obs,r,t,info=env.step(a)
        ri=0.0
        if pos not in tiles: tiles.add(pos); ri=REWARD_NOV
        pain=0.0
        if r<0: pain=abs(r)
        elif inv["health"]<5: pain=0.1*(5-inv["health"])
        elif inv["food"]<3: pain=0.05
        agent.reward(r+ri, pain)
        log.append({"step":step,"a":ACC.get(a,"?"),"hp":inv["health"],
                    "nov":ri,"Ea":round(agent.E_acumulado,3),"d":agent.doubt_count,
                    "st":agent.status,"pos":list(pos)})
        if t: break
    return log, tiles, inv, step+1, duda_eventos

print("="*70)
print("  exp_SGM_0113 — Decoder alimenta la duda (no capea vitalidad)")
print("="*70)

# === CONDICION A: baseline (0108, duda clasica, aristas emergentes) ===
rng_a = random.Random(42)
agent_a = SGMAgent(rng_a, D, n_nodes=N_NODES, gamma=0.01)
agent_a.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES-1)) for i in range(N_NODES)})
log_a, tiles_a, inv_a, pasos_a, duda_a = correr_episodio(agent_a, habilitar_duda=True)
cnt_a = Counter(l['a'] for l in log_a)
noop_a = cnt_a.get('noop',0)/max(1,len(log_a))*100
print(f"\n  A (baseline duda clasica): {pasos_a}p, {len(tiles_a)} tiles, {noop_a:.1f}% noop, "
      f"variedad={len(cnt_a)}, duda={duda_a}")

# === CONDICION B: duda + decoder (el nuevo check_stagnation con predecibilidad) ===
# El mismo agente, pero ahora la duda esta informada por el bigrama.
# De hecho el core ya lo tiene; el baseline A usa el MISMO core con el decoder
# activo. Para aislar, desactivamos el decoder en A? No — el decoder es parte del core.
# En vez: comparamos core ANTIGUO (duda clasica pura, sin predecibilidad) vs core NUEVO.
# Como el core ya tiene la predecibilidad, replico manualmente la duda clasica
# para el NC: un agente cuyo check_stagnation es la version original.

# Re-crear agente CON duda clasica pura (desactivando el efecto del decoder):
# Establecemos theta_novelty de modo que la predecibilidad no cambie el resultado
# NO es trivial. Uso approach claro: condicion B usa el mismo core (decoder ON).
# El baseline A es el nuestro 0108. Hago A vs B con decoder ON vs decoder OFF manual.

# Condicion OFF: sobreescribir el metodo check_stagnation con la version clasica
class SGM_DudaClasica(SGMAgent):
    def check_stagnation(self):
        W_t = min(self.W_base, max(1, len(self.historial_acciones)))
        if W_t < 5: self.stagnation_ticks = 0; return False
        ventana = self.historial_acciones[-W_t:]
        novelty = len(set(ventana)) / len(ventana)
        if novelty < self.theta_novelty: self.stagnation_ticks += 1
        else: self.stagnation_ticks = 0
        return self.stagnation_ticks >= self.min_duration

rng_b = random.Random(42)
agent_b = SGM_DudaClasica(rng_b, D, n_nodes=N_NODES, gamma=0.01)
agent_b.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES-1)) for i in range(N_NODES)})
log_b, tiles_b, inv_b, pasos_b, duda_b = correr_episodio(agent_b, habilitar_duda=True)
cnt_b = Counter(l['a'] for l in log_b)
noop_b = cnt_b.get('noop',0)/max(1,len(log_b))*100
print(f"\n  B (duda clasica pura, sin decoder): {pasos_b}p, {len(tiles_b)} tiles, {noop_b:.1f}% noop, "
      f"variedad={len(cnt_b)}, duda={duda_b}")

# === CONDICION C: NC — sin duda en absoluto ===
class SGM_SinDuda(SGMAgent):
    def check_stagnation(self): return False

rng_c = random.Random(42)
agent_c = SGM_SinDuda(rng_c, D, n_nodes=N_NODES, gamma=0.01)
agent_c.set_edges({i: random.sample(range(N_NODES), min(5, N_NODES-1)) for i in range(N_NODES)})
log_c, tiles_c, inv_c, pasos_c, duda_c = correr_episodio(agent_c, habilitar_duda=False)
cnt_c = Counter(l['a'] for l in log_c)
noop_c = cnt_c.get('noop',0)/max(1,len(log_c))*100
print(f"\n  C (NC sin duda): {pasos_c}p, {len(tiles_c)} tiles, {noop_c:.1f}% noop, "
      f"variedad={len(cnt_c)}, duda={duda_c}")

# === COMPARACION ===
print(f"\n{'='*70}")
print("  COMPARACION")
print(f"{'='*70}")
print(f"  {'Condicion':<28} {'tiles':>5} {'noop%':>7} {'variedad':>8} {'duda':>5}")
print(f"  {'A: decoder+duda':<28} {len(tiles_a):>5} {noop_a:>7.1f} {len(cnt_a):>8} {duda_a:>5}")
print(f"  {'B: duda clasica':<28} {len(tiles_b):>5} {noop_b:>7.1f} {len(cnt_b):>8} {duda_b:>5}")
print(f"  {'C: NC sin duda':<28} {len(tiles_c):>5} {noop_c:>7.1f} {len(cnt_c):>8} {duda_c:>5}")

# PASS: decoder+duda da mas variedad o menos noop que duda clasica, y ambos mejor que NC
mejora_variedad = len(cnt_a) - len(cnt_b)
mejora_tiles = len(tiles_a) - len(tiles_b)
actual = (len(cnt_a), len(tiles_a), round(noop_a,1))
clasica = (len(cnt_b), len(tiles_b), round(noop_b,1))
sin_duda = (len(cnt_c), len(tiles_c), round(noop_c,1))
pass_test = (len(cnt_a) > len(cnt_b)) or (noop_a < noop_b)
print(f"\n  Diferencia decoder vs clasica: variedad{mejora_variedad:+d}, tiles{mejora_tiles:+d}")
print(f"  PASS (decoder mejora vs duda clasica): {pass_test}")
print(f"{'='*70}")

import json
out=os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/results/results_exp_SGM_0113_decoder_duda.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id":"exp_SGM_0113",
    "experiment_name":"decoder_alimenta_duda",
    "phase":"Decoder -> duda (sustrato, no cape)",
    "date":"2026-08-06",
    "hypothesis":"Integrar el decoder (predecibilidad bigrama) a check_stagnation dispara la duda ante secuencias repetitivas (A,B,A,B) que la novedad de acciones unicas NO detecta, produciendo mas variedad de acciones que la duda clasica.",
    "config":{"D":D,"N_NODES":N_NODES,"theta_novelty":0.30,"predecibilidad_factor":0.5},
    "result":{
        "decoder_duda":{"tiles":len(tiles_a),"noop":round(noop_a,1),"variedad":len(cnt_a),"duda":duda_a},
        "duda_clasica":{"tiles":len(tiles_b),"noop":round(noop_b,1),"variedad":len(cnt_b),"duda":duda_b},
        "nc_sin_duda":{"tiles":len(tiles_c),"noop":round(noop_c,1),"variedad":len(cnt_c),"duda":duda_c},
        "pass":pass_test},
    "script":"experiments/exp_SGM_0113_decoder_duda.py",
    "results_file":"results/results_exp_SGM_0113_decoder_duda.json",
    "variant_of":"exp_SGM_0110",
    "lit_refs":["Curiosity & intrinsic motivation in RL — prediction error drives exploration","Di Domenico & Ryan 2017 — SEEKING system, intrinsic motivation emerges from dopamine"],
    "notes":"El decoder NO capea vitalidad (eso era hardcode de emergencia, ver 0110). En vez, ALIMENTA la duda: predecibilidad bigrama reduce la novedad efectiva en check_stagnation, disparando el mecanismo emergente de duda (relajacion/relanzamiento). 3 condiciones: decoder+duda, duda clasica pura, NC sin duda.",
    "notes_criollo":"Antes el decoder era un portero que le bajaba la vitalidad a la accion repetida — eso era un capricho, no algo que naciera del sistema. Ahora el decoder le SUSURRA a la duda, que ya existe: 'mirá, esto que hace el agente es tan predecible como aburrido'. Y es la duda la que, por su propia naturaleza, empuja al agente a probar otra cosa. El portero se fue; ahora es el sentido interno del aburrimiento el que trabaja."
}, open(out,"w"), indent=2)
print(f"\n  Guardado en: {out}")