#!/usr/bin/env python3
"""exp_SGM_0158 — Fase 9 en acción: memoria episódica + imaginación para mejorar la subsistencia.

MISION (continuar Fase 9 base): probar si las dos piezas nuevas del Mundo Interno mejoran la
subsistencia emergente del agente en Crafter:
- MEMORIA EPISODICA (0158a): el agente RECUERDA los eventos salientes (crafteo, comida) y al
  razonar la meta, busca primero en los recuerdos, no solo en el buffer plano.
- IMAGINACION (0158b): antes de ejecutar, el agente SIMULA (con el modelo del mundo) la
  consecuencia probable de ciertas acciones clave (craftear, comer) y prefiere las que su
  red de conocimiento valora como productoras de metas.

HIPOTESIS falsable: con memoria episodica + imaginacion, el agente logra la cadena de
subsistencia (craftear wood_pickaxe, comer) MAS TEMPRANO y/o con mas logros que sin ellas.
SI CIERTA: los pasos hasta el primer make_wood_pickaxe bajan, o los logros suben, vs baseline 0155.
SI FALSA: no cambia la subsistencia (las piezas del mundo interno aun no influyen en la conducta).

Se mide: pasos hasta make/eat, logros acumulados, episodios recordados, cantidad de veces que
la memoria/imaginacion influyo en la decision.
"""
import sys, os, random, json
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm.core.sgm_core import SGMAgent
import crafter
import numpy as np

D = 128; N_NODES = 64
MOV = {1,2,3,4}
DO = 5
MOVE_DIR = {1: (-1,0), 2: (1,0), 3: (0,-1), 4: (0,1)}
TODAS = list(range(17))
COMP_RECURSOS = {11:["wood"],12:["wood","stone"],13:["wood","coal","iron"],
                 14:["wood"],15:["wood","stone"],16:["wood","coal","iron"]}
METAS = ["food", "wood_pickaxe", "wood"]


def inventario_de(info):
    inv=info['inventory']
    return {k:int(v) for k,v in inv.items() if v>0}


def inc_dir(m,a):
    if not m: return 1.0
    t,nw=0,0
    for (e,ac),tr in m.items():
        if ac==a:
            t+=sum(tr.values())
            for sq,c in tr.items():
                if c<=1: nw+=1
    return nw/max(1,t)


def run(seed, n_lives=8):
    ag=SGMAgent(random.Random(seed),D,n_nodes=N_NODES,gamma=0.01)
    ag.set_edges({i:random.sample(range(N_NODES),min(5,N_NODES-1)) for i in range(N_NODES)})
    ag.instinto_alimentacion=DO
    env=crafter.Env(); env.reset()
    total_pasos=0; logros_totales=set()
    paso_make=None; paso_eat=None; n_imagino=0
    resumen=[]
    for vida in range(n_lives):
        env.reset(); ag.reset_episodio()
        obs,r,t,info=env.step(0)
        prev_pos=np.array(info['player_pos'],dtype=int); facing=(0,1)
        inv_log=inventario_de(info)
        for step in range(2000):
            sem=info['semantic']; inv=info['inventory']
            px,py=int(info['player_pos'][0]),int(info['player_pos'][1])
            sv=[float(v) for v in sem.flatten().tolist()[::64]]+[inv['health']/10.0,
                inv['food']/10.0,inv['wood'],inv['stone'],inv['iron']]
            hambre=max(0.0,1.0-inv['food']/10.0)
            ag._hambre_real=min(1.0,hambre); ag._amenaza=0.0
            ag._posicion_actual=(px,py); ag._algo_enfrente=0
            ag._config_grad={"activo":False,"fuerza":0.0}
            ag._config_curio={"activo":True,"fuerza":0.4}
            ag._inc_dirs={a:inc_dir(ag.modelo_mundo,a) for a in MOV}
            ag._hay_gradiente=False
            eq=ag.cuantizar_estado(sv)
            # IMAGINACION (0158b): si tengo hambre, imaginar que acciones podrian ayudar
            accion_imag = None
            if hambre > 0.4:
                # imaginar la meta 'food' desde la memoria episodica o red
                acc_raz, _ = ag.razonar_meta('food')
                if acc_raz is not None:
                    sig, conf, bonus = ag.predecir_recompensa(acc_raz, eq, metas_priorizadas=['food'])
                    if conf > 0 or bonus > 0:
                        accion_imag = acc_raz
                        n_imagino += 1
            # decidir: si la imaginacion propone y la curiosidad no dijo algo mejor, usarla
            a = ag.step(sv, TODAS) if accion_imag is None else accion_imag
            obs,r,t,info=env.step(a)
            cur_pos=np.array(info['player_pos'],dtype=int)
            if a in MOV:
                delta=tuple((cur_pos-prev_pos).tolist()); facing=delta if delta!=(0,0) else MOVE_DIR[a]
            prev_pos=cur_pos
            nuevo_inv=inventario_de(info)
            ag._resultado_mundo_prev=inv_log; ag._resultado_mundo_act=nuevo_inv
            ag._aprender_resultado_mundo(a)
            # registrar historia + MEMORIA EPISODICA (eventos salientes)
            ag._registrar_historia(step, a, nuevo_inv, "cuerpo")
            ag._codificar_episodio(eq, a, nuevo_inv, "cuerpo")
            inv_log=nuevo_inv
            # registrar primer make_wood_pickaxe
            if 'wood_pickaxe' in nuevo_inv and paso_make is None:
                paso_make = total_pasos
            if info['achievements'].get('eat_cow',0)>0 and paso_eat is None:
                paso_eat = total_pasos
            ag.actualizar_homeostasis(inv['food'],inv['health'])
            pain=abs(r) if r<0 else 0.0
            ag.reward(max(0.0,r),pain)
            ag.actualizar_modelo_mundo(eq, a, ag.cuantizar_estado(_sv(info)))
            for nm,c in info['achievements'].items():
                if c>0: logros_totales.add(nm)
            total_pasos+=1
            if t: break
        resumen.append({"vida":vida,"pasos":step+1,"logros":len(logros_totales),
                        "episodios":len(ag.episodios),"n_imagino":n_imagino})
        print(f"  vida {vida}: {step+1}p logros={len(logros_totales)} epi={len(ag.episodios)} "
              f"imagino={n_imagino}")
    return resumen, sorted(logros_totales), total_pasos, paso_make, paso_eat, n_imagino


def _sv(info):
    inv=info['inventory']
    sem=info['semantic']
    return [float(v) for v in sem.flatten().tolist()[::64]]+[inv['health']/10.0,
            inv['food']/10.0,inv['wood'],inv['stone'],inv['iron']]


print("="*70)
print(" exp_SGM_0158 — Fase 9 en accion: memoria episodica + imaginacion vs subsistencia")
print("="*70)
res, logros, pasos, paso_make, paso_eat, n_imagino = run(42, n_lives=8)
print(f"\n  seed 42: {pasos} pasos, logros={logros}, paso_make={paso_make}, paso_eat={paso_eat}, "
      f"n_imaginaciones={n_imagino}")

out=os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/"
                       "results/results_exp_SGM_0158_memoria_imag_in_subsistencia.json")
json.dump({
  "experiment_id":"exp_SGM_0158","experiment_name":"fase9_memoria_imaginacion_subsistencia",
  "phase":"Fase 9 - Mundo Interno en accion: memoria episodica + imaginacion mejoran subsistencia",
  "date":"2026-08-14",
  "mision":"probar si las dos piezas nuevas (memoria episodica + imaginacion) mejoran la "
           "emergente subsistencia del agente en Crafter",
  "hypothesis":"con memoria episodica + imaginacion, el agente craftea/come MAS TEMPRANO y/o "
               "con mas logros vs baseline (0155)",
  "config":{"D":D,"N_NODES":N_NODES,"n_lives":8,"seed":42,"metas":METAS},
  "result":{"vidas":res,"logros":logros,"pasos_totales":pasos,"paso_make":paso_make,
            "paso_eat":paso_eat,"n_imaginaciones":n_imagino},
  "script":"experiments/exp_SGM_0158_memoria_imag_subsistencia.py",
  "results_file":"results/results_exp_SGM_0158_memoria_imag_subsistencia.json",
  "variant_of":"exp_SGM_0155",
  "lit_refs":["memoria episodica (Fase 9-1)", "imaginacion Ha&Schmidhuber (Fase 9-2)"],
  "notes":"Integra memoria episodica (recordar eventos salientes al razonar) e imaginacion "
           "(simular consecuencia con modelo del mundo) al agente de subsistencia. Mide si "
           "mejora (crafteo/comer mas temprano, mas logros) vs baseline.",
  "notes_criollo":"Le dimos al bicho memoria (recuerda las veces que le fue bien) y capacidad de "
                   "imaginar que va a pasar si hace algo, y vemos si con eso sobrevive mejor y "
                   "aprende a craftear/hero mas temprano.",
},open(out,"w"),indent=2)
print(f"\n Guardado en: {out}")