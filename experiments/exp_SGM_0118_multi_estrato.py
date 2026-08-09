#!/usr/bin/env python3
"""
exp_SGM_0118 — Evaluación multi-estrato COMPLETA (cierre de Fase 8).
Una vida entera del sistema, sin cortar, reportada como historia vista desde
dentro (estados internos) y desde fuera (comportamiento en el mundo).

Integraciones activas:
  - Querer por homeostasis (0116): actualizar_homeostasis refuerza la conexion
    entre la accion que mejoro food y la supervivencia (nodo 0), sin reward externo.
  - Curiosidad por prediction error (0117): el decoder predice la prox accion;
    high prediction error -> reward intrinseco por curiosidad.

RETRIBE LOS 6 ESTRATOS y genera un diario de vida narrativo en criollo.
"""
import sys, os, random, math
from collections import Counter
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm_core import SGMAgent
import crafter

D=128; N_NODES=64; VIEW=20; EPS_CURIOSIDAD=0.2
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

# ============ CONFIG AGENTE ============
rng = random.Random(42)
ag = SGMAgent(rng, D, n_nodes=N_NODES, gamma=0.01)
ag.set_edges({i: random.sample(range(N_NODES), min(5,N_NODES-1)) for i in range(N_NODES)})

env = crafter.Env(); env.reset()
obs,r,t,info = env.step(0)

# ============ ESTADO DE OBSERVACION ============
tiles=set(); historial=[]; trayectoria=[]; diario=[]
# estados internos por step
estados=[]; apetito_log=[]; pe_log=[]; n_pred=0; n_aciertos=0
aristas_inicio = {k:list(v) for k,v in ag.edges.items()}
conn_inicio = len(ag.conn_type); V_inicio = ag.V_grafo

# ============ VIDA (corre hasta que sea terminal, sin corte) ============
step = 0
while True:
    sem=info["semantic"].flatten().tolist(); inv=info["inventory"]
    pos=tuple(info["player_pos"]); trayectoria.append(pos)
    sv=[float(v) for v in sem[::64]]+[float(inv["health"])/10.0,float(inv["food"])/10.0,
       float(inv["wood"]),float(inv["stone"]),float(inv["iron"])]
    # Prediccion (curiosidad)
    pred = top1(train_bigram(historial[-VIEW:]), historial[-1]) if (len(historial)>=VIEW and historial) else None
    a = ag.step(sv, list(range(17)))
    error = 0.0
    if pred is not None:
        n_pred += 1; error = 0.0 if pred==a else 1.0
        if pred==a: n_aciertos += 1
        pe_log.append(error)
    obs,r,t,info = env.step(a)
    # Homeostasis (querer intrinseco)
    ag.actualizar_homeostasis(inv["food"], inv["health"])
    # Reward: curiosidad (intrinseco) + pain
    reward = EPS_CURIOSIDAD * error
    pain = 0.0
    if r < 0: pain = abs(r)
    elif inv["health"] < 5: pain = 0.1*(5-inv["health"])
    elif inv["food"] < 3: pain = 0.05
    ag.reward(reward, pain)
    if pos not in tiles: tiles.add(pos)
    historial.append(a)
    # Registrar estados
    estados.append({"step":step,"a":ACC.get(a,"?"),"pos":list(pos),"hp":inv["health"],
                    "food":inv["food"],"Ea":round(ag.E_acumulado,3),"status":ag.status,
                    "duda":ag.doubt_count,"V_grafo":round(ag.V_grafo,3),"pe":error})
    apetito_log.append({"food":inv["food"],"a":a})
    # DIARIO: cada 50 pasos, una entrada narrativa
    if step % 50 == 0:
        diario.append(f"[t={step}] {ACC.get(a,'?')} | hp={inv['health']} food={inv['food']} "
                      f"pos={list(pos)} Ea={ag.E_acumulado:.2f} st={ag.status} Vg={ag.V_grafo:.2f}")
    step += 1
    if t:
        muerte={"step":step,"food":inv["food"],"hp":inv["health"],"status":ag.status,"duda":ag.doubt_count,"V_grafo":round(ag.V_grafo,3)}
        break
    if step > 3000:  # techo de seguridad, no deberia cortarse
        muerte={"step":step,"food":inv["food"],"hp":inv["health"],"status":"SOBREVIVE(>3000)","duda":ag.doubt_count,"V_grafo":round(ag.V_grafo,3)}
        break

# ============ POST-MORTEM: ANALISIS DE ESTRATOS ============
cnt = Counter(e["a"] for e in estados)
noop = 100*cnt.get("noop",0)/max(1,len(estados))

print("="*70)
print("  exp_SGM_0118 — Evaluación multi-estrato (historia completa)")
print("="*70)

print("\n### ESTRATO 1: SUPERVIVENCIA (desde fuera)")
print(f"  Vivido: {step} pasos")
print(f"  Muerte: {muerte}")
print(f"  Noop: {noop:.1f}% | Tiles unicos: {len(tiles)} | Movimientos: {sum(1 for i in range(1,len(trayectoria)) if trayectoria[i]!=trayectoria[i-1])}")

print("\n### ESTRATO 2: GRAFO (la red del sistema)")
print(f"  Aristas conn_type: inicio={conn_inicio} -> fin={len(ag.conn_type)}. V_grafo inicio={V_inicio:.2f} -> fin={ag.V_grafo:.2f}")
# Que conexiones se aprendieron
aprendidas = [k for k in ag.conn_type if k[1]==0]  # conexiones hacia nodo 0 (supervivencia)
if aprendidas:
    print(f"  Conexiones hacia supervivencia (nodo 0): {len(aprendidas)} -> {list(aprendidas)[:6]}")
else:
    print("  NO se aprendieron conexiones hacia el nodo 0 (supervivencia).")

print("\n### ESTRATO 3: MOVIMIENTO (trayectoria)")
xs=[p[0] for p in trayectoria]; ys=[p[1] for p in trayectoria]
if trayectoria:
    print(f"  Rango X: {min(xs)}-{max(xs)} | Y: {min(ys)}-{max(ys)}")
    print(f"  Pos inicial: {trayectoria[0]}, Pos final: {trayectoria[-1]}")
print(f"  (Trayectoria completa de {len(trayectoria)} posiciones guardada)")

print("\n### ESTRATO 4: APETITO (querer operativo)")
eat_con_hambre = sum(1 for l in apetito_log if l["a"]==16 and l["food"]<3)
eat_total = sum(1 for l in apetito_log if l["a"]==16)
hambre = sum(1 for l in apetito_log if l["food"]<3)
print(f"  eat_total={eat_total}, eat_con_hambre={eat_con_hambre}, hambre_total={hambre}")
if eat_total > 0 and hambre > 0:
    prop = eat_con_hambre/max(1,hambre)
    print(f"  Proporcion de hambre atendida con eat: {prop:.2f}")
    print(f"  >> SI prop > 0.5: querer operativo presente (come cuando tiene hambre).")
else:
    print(f"  >> Sin comer, querer operativo NO evidenciado en esta vida.")

print("\n### ESTRATO 5: ESTADOS INTERNOS (dinamica afectiva)")
stat_cnt = Counter(e["status"] for e in estados)
print(f"  Status: {dict(stat_cnt)}")
print(f"  Duda max: {max(e['duda'] for e in estados)} | E_acum max: {max(e['Ea'] for e in estados)}")

print("\n### ESTRATO 6: CURIOSIDAD (prediction error)")
if n_pred > 0:
    acc_pred = 100*n_aciertos/n_pred
    pe_prom = sum(pe_log)/len(pe_log)
    print(f"  Predicciones: {n_pred}, accuracy={acc_pred:.0f}%, PE_prom={pe_prom:.2f}")
    print(f"  >> PE alto = el sistema encontro lo desconocido (curiosidad dirigida).")
else:
    print("  Sin predicciones suficientes (vida corta para el decoder).")

print("\n### DIARIO DE VIDA (cada 50 pasos)")
for d in diario:
    print(f"  {d}")

print("\n### DISTRIBUCION DE ACCIONES")
for act,n in cnt.most_common(8):
    print(f"  {act:20s} {n:3d} ({100*n/len(estados):.1f}%)")

print("\n### NARRATIVA (resumen en criollo)")
if eat_total > 0:
    narr = f"El sistema comio {eat_total} veces, {eat_con_hambre} de ellas con hambre. "
    if eat_con_hambre/max(1,hambre) > 0.5:
        narr += "Hay querer operativo: come cuando tiene hambre (homeostasis activa). "
    else:
        narr += "Pero come sin correlacion clara con la hambre (querer parcial). "
else:
    narr = "El sistema NO comio en toda la vida: no hay querer operativo por comida. "
narr += f"Exploro {len(tiles)} tiles, murio en paso {step} con food={muerte['food']}, hp={muerte['hp']}, estado {muerte['status']}. "
if "CONTRADICTORIA" in stat_cnt:
    narr += "Llego a CONTRADICTORIA (dolor acumulado). "
narr += f"V_grafo termino en {ag.V_grafo:.2f}."
print(f"  {narr}")

print(f"\n{'='*70}")

import json
out=os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/results/results_exp_SGM_0118_multi_estrato.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump({
    "experiment_id":"exp_SGM_0118",
    "experiment_name":"evaluacion_multi_estrato_completa",
    "phase":"Fase 8 - cierre, evaluacion multi-estrato",
    "date":"2026-08-06",
    "hypothesis":"Una vida entera con querer(0116)+curiosidad(0117) revela los 6 estratos del sistema. Objetivo: analizar el ciclo de subsistencia completo (hacer->hambre->comer->volver a hacer).",
    "config":{"D":D,"N_NODES":N_NODES,"VIEW":VIEW,"EPS_CURIOSIDAD":EPS_CURIOSIDAD},
    "result":{
        "supervivencia":{"pasos":step,"muerte":muerte,"noop":round(noop,1),"tiles":len(tiles),
            "movimientos":sum(1 for i in range(1,len(trayectoria)) if trayectoria[i]!=trayectoria[i-1])},
        "grafo":{"aristas_inicio":conn_inicio,"aristas_fin":len(ag.conn_type),
            "V_grafo_inicio":V_inicio,"V_grafo_fin":round(ag.V_grafo,3),
            "conexiones_supervivencia":len([k for k in ag.conn_type if k[1]==0])},
        "movimiento":{"rango_x":[int(min(xs)),int(max(xs))] if trayectoria else None,"rango_y":[int(min(ys)),int(max(ys))] if trayectoria else None},
        "apetito":{"eat_total":eat_total,"eat_con_hambre":eat_con_hambre,"hambre_total":hambre,
            "querer_operativo":(eat_con_hambre/max(1,hambre)>0.5) if eat_total>0 else False},
        "estados_internos":{"status":dict(stat_cnt),"duda_max":max(e['duda'] for e in estados),"E_acum_max":max(e['Ea'] for e in estados)},
        "curiosidad":{"n_pred":n_pred,"acc_pred":100*n_aciertos/n_pred if n_pred>0 else 0,"pe_prom":round(sum(pe_log)/len(pe_log),3) if pe_log else 0}},
    "script":"experiments/exp_SGM_0118_multi_estrato.py",
    "results_file":"results/results_exp_SGM_0118_multi_estrato.json",
    "variant_of":"exp_SGM_0114",
    "lit_refs":["Maslow 1943 - subsistencia antes que crecimiento","Varela et al 1991 - enactivismo","Panksepp SEEKING","Schmidhuber/Oudeyer curiosidad"],
    "notes":"Vida completa sin corte, 6 estratos. Integra querer(0116)+curiosidad(0117). Diario de vida cada 50 pasos. Analiza el ciclo de subsistencia completo.",
    "notes_criollo":"Es la foto completa de una vida: cuanto vivio, por que murio, como se movio, si comio cuando tuvo hambre, que paso en su interior (dolor, duda), y si fue curioso. Todo junto, como una historia."
}, open(out,"w"), indent=2)
print(f"\n  Guardado en: {out}")