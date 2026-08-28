#!/usr/bin/env python3
"""
exp_SGM_0117 — Curiosidad = reducción de prediction error (Oudeyer/Schmidhuber).
NO es "moverse mucho" (eso era aimless wandering, 0113). Es explorar DONDE el
modelo del mundo falla: el decoder predice la proxima accion; prediction error
alto = hay informacion nueva = el agente "quiere" ir ahi (reward intrinseco).

HIPOTESIS (falsable):
  Si el prediction error del decoder genera reward intrinseco por curiosidad,
  el agente explorará mas tiles y producirá mas variedad de acciones que el NC
  (sin curiosidad), porque la curiosidad rompe el atractor de "accion predecible".

El decoder predice la proxima accion de la secuencia. Prediction error =
1 - acierto (0 si acerto, 1 si fallo). Reward curiosidad = epsilon * prediction_error.
NC: decoder apagado (prediction error = 0, sin reward curiosidad).

Protocolo A/B con reward externo de novedad APAGADO para aislar SOLO la curiosidad.
"""
import sys, os, random, math
from collections import Counter
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm.core.sgm_core import SGMAgent
import crafter

D=128; N_NODES=64; VIEW=20  # ventana del decoder
ACC = {0:"noop",1:"move_left",2:"move_right",3:"move_up",4:"move_down",
       5:"do",6:"sleep",7:"place_stone",8:"place_table",9:"place_furnace",
       10:"make_wood_pickaxe",11:"make_stone_pickaxe",12:"make_iron_pickaxe",
       13:"make_wood_sword",14:"make_stone_sword",15:"make_iron_sword",16:"eat"}

def train_bigram(seq, V=17):
    if len(seq) < 3: return None
    counts = {a: {b: 0.0 for b in range(V)} for a in range(V)}
    for i in range(len(seq)-1):
        a,b = seq[i],seq[i+1]
        if a in counts and b in counts[a]: counts[a][b] += 1.0
    model = {}
    for a in range(V):
        tot = sum(counts[a].values())
        model[a] = {b: counts[a][b]/tot for b in range(V)} if tot>0 else {b:1.0/V for b in range(V)}
    return model

def top1(model, accion, V=17):
    if model is None or accion not in model: return None
    return max(range(V), key=lambda b: model[accion].get(b,0.0))

def correr_vida(agent, usar_curiosidad, eps_curiosidad=0.2, max_pasos=2000):
    env = crafter.Env(); env.reset()
    obs,r,t,info = env.step(0)
    tiles=set(); historial=[]; log=[]; pred_errors=[]; n_pred=0; n_aciertos=0
    for step in range(max_pasos):
        sem=info["semantic"].flatten().tolist(); inv=info["inventory"]
        pos=tuple(info["player_pos"])
        sv=[float(v) for v in sem[::64]]+[float(inv["health"])/10.0,float(inv["food"])/10.0,
           float(inv["wood"]),float(inv["stone"]),float(inv["iron"])]
        # Prediccion ANTES de actuar (modelo del mundo)
        pred = top1(train_bigram(historial[-VIEW:]), historial[-1]) if (usar_curiosidad and len(historial)>=VIEW and historial) else None
        a = agent.step(sv, list(range(17)))
        # Calcular prediction error REAL
        error = 0.0
        if pred is not None:
            n_pred += 1
            error = 0.0 if pred == a else 1.0
            if pred == a: n_aciertos += 1
            pred_errors.append(error)
        obs,r,t,info=env.step(a)
        # Reward: NO reward externo por novedad (aislar solo curiosidad)
        reward = 0.0
        pain = 0.0
        if r < 0: pain = abs(r)
        elif inv["health"] < 5: pain = 0.1*(5-inv["health"])
        elif inv["food"] < 3: pain = 0.05
        # Curiosidad: reward intrinseco proporcional al prediction error
        if usar_curiosidad:
            reward = eps_curiosidad * error
        agent.reward(reward, pain)
        if pos not in tiles: tiles.add(pos)
        historial.append(a)
        log.append({"step":step,"a":a,"food":inv["food"],"hp":inv["health"],
                    "pe":error,"duda":agent.doubt_count,"status":agent.status})
        if t:
            muerte={"step":step,"food":inv["food"],"hp":inv["health"],"status":agent.status}
            return log,tiles,historial,muerte,step+1,pred_errors,n_pred,n_aciertos
    return log,tiles,historial,None,step+1,pred_errors,n_pred,n_aciertos

def reportar(nombre, log, tiles, cnt, muerte, pasos, errors, n_pred, n_aciertos):
    noop = 100*cnt.get('noop',0)/max(1,len(log))
    acc_med = (n_aciertos/n_pred)*100 if n_pred>0 else 0
    pe_prom = sum(errors)/len(errors) if errors else 0
    print(f"\n  {nombre}: {pasos}p, {len(tiles)} tiles, {noop:.1f}% noop, pred_acc={acc_med:.0f}%, PE_prom={pe_prom:.2f}")
    if muerte: print(f"    muerte: {muerte}")
    for act,n in cnt.most_common(4):
        print(f"    {act:18s} {n:3d} ({100*n/len(log):.1f}%)")
    return len(tiles), noop, len(cnt), acc_med

print("="*70)
print("  exp_SGM_0117 — Curiosidad por prediction error (Schmidhuber/Oudeyer)")
print("="*70)

# A: CON curiosidad (prediction error -> reward intrinseco)
rng_a = random.Random(42)
ag_a = SGMAgent(rng_a, D, n_nodes=N_NODES, gamma=0.01)
ag_a.set_edges({i: random.sample(range(N_NODES), min(5,N_NODES-1)) for i in range(N_NODES)})
log_a,tiles_a,hist_a,muerte_a,pasos_a,err_a,np_a,na_a = correr_vida(ag_a, usar_curiosidad=True)
cnt_a = Counter(ACC.get(l['a'],"?") for l in log_a)
tA,nA,vA,accA = reportar("A (con curiosidad)", log_a, tiles_a, cnt_a, muerte_a, pasos_a, err_a, np_a, na_a)

# B: NC SIN curiosidad (decoder apagado, sin reward intrinseco)
rng_b = random.Random(42)
ag_b = SGMAgent(rng_b, D, n_nodes=N_NODES, gamma=0.01)
ag_b.set_edges({i: random.sample(range(N_NODES), min(5,N_NODES-1)) for i in range(N_NODES)})
log_b,tiles_b,hist_b,muerte_b,pasos_b,err_b,np_b,na_b = correr_vida(ag_b, usar_curiosidad=False)
cnt_b = Counter(ACC.get(l['a'],"?") for l in log_b)
tB,nB,vB,accB = reportar("B (NC sin curiosidad)", log_b, tiles_b, cnt_b, muerte_b, pasos_b, err_b, np_b, na_b)

# Comparacion
print(f"\n{'='*70}")
print("  COMPARACION")
print(f"{'='*70}")
print(f"  A (curiosidad):  tiles={tA}, noop={nA:.1f}%, variedad={vA}")
print(f"  B (NC sin cur):  tiles={tB}, noop={nB:.1f}%, variedad={vB}")
pass_test = (tA > tB) or (vA > vB)
print(f"\n  PASS (curiosidad aumenta exploracion/variedad): {pass_test}")
print(f"{'='*70}")

import json
out=os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/results/results_exp_SGM_0117_curiosidad.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id":"exp_SGM_0117",
    "experiment_name":"curiosidad_prediction_error",
    "phase":"Fase 8 — curiosidad (Schmidhuber/Oudeyer)",
    "date":"2026-08-06",
    "hypothesis":"Si el prediction error del decoder genera reward intrinseco, el agente explora mas tiles y produce mas variedad de acciones que el NC sin curiosidad (la curiosidad rompe el atractor de accion predecible).",
    "config":{"D":D,"N_NODES":N_NODES,"VIEW":VIEW,"eps_curiosidad":0.2},
    "result":{
        "A_curiosidad":{"pasos":pasos_a,"tiles":tA,"noop":round(nA,1),"variedad":vA,"pred_acc":round(accA,1),"pe_prom":round(sum(err_a)/len(err_a),2) if err_a else 0,"muerte":muerte_a},
        "B_nc_sin_curiosidad":{"pasos":pasos_b,"tiles":tB,"noop":round(nB,1),"variedad":vB,"pred_acc":round(accB,1),"pe_prom":round(sum(err_b)/len(err_b),2) if err_b else 0,"muerte":muerte_b},
        "pass":pass_test},
    "script":"experiments/exp_SGM_0117_curiosidad.py",
    "results_file":"results/results_exp_SGM_0117_curiosidad.json",
    "variant_of":"exp_SGM_0113",
    "lit_refs":["Schmidhuber 1991 — learning progress curiosity","Oudeyer & Kaplan 2007 — curiosity-driven exploration via prediction error","Berridge — wanting vs liking"],
    "notes":"Curiosidad = prediction error del decoder -> reward intrinseco. NO es moverse mucho (0113 aimless wandering). El agente explora donde el modelo falla. NC: decoder apagado.",
    "notes_criollo":"La curiosidad no es 'caminar mucho' — es querer ir donde no entendés el mundo. El decoder predice lo que va a pasar; cuando se equivoca, hay algo nuevo que aprender, y eso da una recompensa interna. Es como cuando te intriga un sonido desconocido: no te atrae por moverse, te atrae por no saber qué es."
}, open(out,"w"), indent=2)
print(f"\n  Guardado en: {out}")