#!/usr/bin/env python3
"""exp_SGM_0130 — HIPOTESIS DE LUCIANO: el nodo-referencia al acto se crea SOLO si
el acto produjo resultado real (acople acto-resultado). El eat en vacio no crea
referencia de restauracion.

CONTEXTO 0129: las 3 seeds comen (42x,16x,1x) y 2 se mueven mucho, PERO ciclos=0 y
mueren con food 0.0-2.0. El agente ejecuta 'eat' muchas veces pero la mayoria son
eat VACIOS (sin comida enfrente): en Crafter 'eat' solo sube food si hay cow/plant
a la vista (objetos.py: cow food+=6, plant madura food+=4). El eat vacio no produce
nada -> no hay mejora homeostatica -> Hebb/Kuramoto no consolidan eat->nodo0 ->
el aprendizaje innato 'comer restaura' queda BLOQUEADO.

HIPOTESIS (Luciano): no es el reward lo que bloquea el aprendizaje innato, es la
CREACION del nodo-referencia al acto. El acto 'eat' debe crear referencia a
restauracion SOLO cuando este acoplado a un resultado real en el mundo. Comer en
vacio (sin comida) no debe consolidar eat->nodo0: el sustrato debe registrar que ese
acto NO tuvo efecto, para que el agente no quede atrapado repitiendo eat vacio y en
su lugar BUSQUE comida.

MECANISMO (sin hardcode):
  - Cuando 'eat' NO produce subida de food (eat vacio): aplicar pain intrinseco al
    acto -> la singularidad del nodo de ese acto baja (el PPR deja de elegirlo),
    empujando al agente a buscar donde SI haya comida (gradiente). Es acople
    acto->resultado: acto sin efecto no es referencia a restauracion.
  - Cuando 'eat' SI produce subida de food: refuerzo normal (Hebb) + Kuramoto
    consolida eat->nodo0 (el acto SI creo referencia de restauracion).

Prediccion falsable: con este gating, el agente deja de repetir eat vacio, comienza
a desplazarse hacia el gradiente de comida (mov alta), come solo cuando hay comida
(eat_con_comida > eat_vacio), y los ciclos de subsistencia (hambre->comer->saciado)
EMPIEZAN. Ademas, eat->nodo0 se consolida (cae el instinto) porque solo los eats
efectivos lo refuerzan.

LITERATURA: esta es la hipotesis del nodo-referencia al acto (Luciano 2026-08-11);
Hebb 1949 (co-ocurrencia acto-resultado); Damasio somatic markers; en Crafter la
senal ya esta en objetos.py (eat efectivo si cow/plant a la vista).
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
       7:"p_stone",8:"p_table",9:"p_furnace",10:"mk_w_pick",11:"mk_s_pick",
       12:"mk_i_pick",13:"mk_w_sword",14:"mk_s_sword",15:"mk_i_sword",16:"eat"}
MOV = {1,2,3,4}
FOOD = {13,17}
UMBRAL_EAT = 2.0


def gradiente(sem,px,py,r=5):
    b,bd=(0,0),r*r+1
    for dy in range(-r,r+1):
        for dx in range(-r,r+1):
            if dx==0 and dy==0: continue
            x,y=px+dx,py+dy
            if 0<=x<sem.shape[1] and 0<=y<sem.shape[0]:
                if sem[y,x] in FOOD:
                    d=abs(dx)+abs(dy)
                    if d<bd: bd,b=d,(dx,dy)
    return b,bd


def inc_dir(m,a):
    if not m: return 1.0
    t,nw=0,0
    for (e,ac),tr in m.items():
        if ac==a:
            t+=sum(tr.values())
            for sq,c in tr.items():
                if c<=1: nw+=1
    return nw/max(1,t)


def instinto_eat(ag,food_nivel):
    if food_nivel is None or food_nivel>=ag.umbral_hambre_food:
        return 0.0
    conn=ag.conn_type.get((16,0)); st=conn.get("strength",0) if conn else 0
    if (16,0) in ag.consolidadas or st>=UMBRAL_EAT:
        return 0.0
    carencia=max(0.0,ag.umbral_hambre_food-food_nivel)
    return ag.instinto_fuerza_base*(carencia/ag.umbral_hambre_food)


def correr(seed, gatear_acto, max_p=600):
    """gatear_acto=True: eat vacio NO consolida (hipotesis Luciano, 0130).
       gatear_acto=False: baseline 0129 (todo eat refuerza igual)."""
    ag=SGMAgent(random.Random(seed),D,n_nodes=N_NODES,gamma=0.01)
    ag.set_edges({i:random.sample(range(N_NODES),min(5,N_NODES-1)) for i in range(N_NODES)})
    env=crafter.Env(); env.reset(); obs,r,t,info=env.step(0)
    tiles=set(); eat_tot=eat_vacio=eat_efectivo=mov=ciclos=0
    food_bajo=False; prev_food=None; prev_hay_grad=False
    for step in range(max_p):
        sem=info["semantic"]; inv=info["inventory"]
        px,py=int(info["player_pos"][0]),int(info["player_pos"][1])
        sf=sem.flatten().tolist()
        sv=[float(v) for v in sf[::64]]+[float(inv["health"])/10.0,float(inv["food"])/10.0,
            float(inv["wood"]),float(inv["stone"]),float(inv["iron"])]
        gd,gd2=gradiente(sem,px,py); hg=gd!=(0,0)
        ag._gradiente_dir=gd; ag._gradiente_dist=gd2; ag._hay_gradiente=hg
        ag._inc_dirs={a:inc_dir(ag.modelo_mundo,a) for a in MOV}
        ag._config_grad={"activo":True,"fuerza":0.5}; ag._config_curio={"activo":True,"fuerza":0.3}
        ag._fuerza_instinto_eat_override=instinto_eat(ag,float(inv["food"]))
        a=ag.step(sv,list(range(17)))
        # guardar food ANTES del eat para detectar efectividad
        food_antes=float(inv["food"]); habia_comida=hg
        obs,r,t,info=env.step(a)
        food_despues=float(inv["food"])
        ag.actualizar_homeostasis(inv["food"],inv["health"])
        # PAIN / GATING por acople acto-resultado (0130)
        pain=0.0
        if r<0: pain=abs(r)
        elif inv["health"]<5: pain=0.1
        if gatear_acto and a==16:
            # hipotesis Luciano: eat vacio (food no subio, sin comida a la vista) NO
            # consolida restauracion: se registra pain intrinseco -> el acto no crea
            # nodo-referencia de restauracion, empuja al agente a buscar comida.
            if food_despues <= food_antes and not habia_comida:
                eat_vacio+=1
                pain=max(pain,0.3)  # acto sin efecto = malestar, no referencia
            else:
                eat_efectivo+=1
        if a==16:
            eat_tot+=1
        ag.reward(max(0.0,r),pain)
        pos=(px,py)
        if pos not in tiles:
            tiles.add(pos); ag.reward(0.05,0.0)
        ag.incertidumbre_acum=max(0,ag.incertidumbre_acum-0.01)
        eq=ag.cuantizar_estado(sv)
        ag.actualizar_modelo_mundo(getattr(ag,'ultimo_estado_q',eq) or eq,a,eq)
        ag.ultimo_estado_q=eq
        if inv["food"]<3:
            food_bajo=True
        elif food_bajo and inv["food"]>=7:
            ciclos+=1; food_bajo=False
        if a in MOV: mov+=1
        prev_food=food_despues; prev_hay_grad=hg
        if t: break
    muerte={"step":step,"food":float(inv["food"]),"hp":float(inv["health"]),
            "Vg":round(ag.V_grafo,3)} if t else None
    return {"seed":seed,"pasos":step+1,"tiles":len(tiles),"eat":eat_tot,
            "eat_vacio":eat_vacio,"eat_efectivo":eat_efectivo,"mov":mov,
            "ciclos":ciclos,"muerte":muerte}


print("="*70)
print(" exp_SGM_0130 — Hipotesis nodo-referencia al acto (gatear eat vacio)")
print("="*70)
for seed in [42,7,99]:
    ra=correr(seed,gatear_acto=True,max_p=600)
    rb=correr(seed,gatear_acto=False,max_p=600)  # baseline 0129
    print(f"\n seed {seed}:")
    print(f"  GATED(hipotesis):  {ra['pasos']}p {ra['tiles']}tiles eat={ra['eat']} "
          f"(efect={ra['eat_efectivo']},vacio={ra['eat_vacio']}) mov={ra['mov']} "
          f"ciclos={ra['ciclos']} muerte={ra['muerte']}")
    print(f"  BASELINE(0129):    {rb['pasos']}p {rb['tiles']}tiles eat={rb['eat']} "
          f"(efect={rb['eat_efectivo']},vacio={rb['eat_vacio']}) mov={rb['mov']} "
          f"ciclos={rb['ciclos']} muerte={rb['muerte']}")
    if ra["eat_efectivo"]>0:
        print(f"    >> ratio eat_efectivo/total gated: {ra['eat_efectivo']}/{ra['eat']}")

out=os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/"
                       "results/results_exp_SGM_0130_nodo_referencia.json")
os.makedirs(os.path.dirname(out),exist_ok=True)
json.dump({
    "experiment_id":"exp_SGM_0130",
    "experiment_name":"nodo_referencia_al_acto",
    "phase":"Fase 8 - hipotesis nodo-referencia al acto (gatear eat vacio)",
    "date":"2026-08-11",
    "hypothesis":"El acto 'eat' debe crear nodo-referencia de restauracion SOLO si produjo "
                 "resultado real (comida). Eat vacio (sin comida) NO consolida: se registra "
                 "malestar que empuja a buscar comida. Pred: reduce eat vacio, aumenta "
                 "eat_efectivo y mov (buscar), aparecen ciclos de subsistencia, y eat->nodo0 "
                 "se consolida porque solo los eats efectivos lo refuerzan.",
    "config":{"D":D,"N_NODES":N_NODES,"max_pasos":600,"seeds":[42,7,99],
              "gating":"eat vacio (food no sube y sin comida a la vista) => pain 0.3 intrinseco",
              "homeostasis":"NATIVA Crafter"},
    "result":{"seeds":[{"seed":s,"gated_pasos":r1["pasos"],"gated_tiles":r1["tiles"],
                         "gated_eat":r1["eat"],"gated_eat_efectivo":r1["eat_efectivo"],
                         "gated_eat_vacio":r1["eat_vacio"],"gated_mov":r1["mov"],
                         "gated_ciclos":r1["ciclos"],"gated_muerte":r1["muerte"]}
                         for s,r1 in [(42,correr(42,True,600)),(7,correr(7,True,600)),(99,correr(99,True,600))]]},
    "script":"experiments/exp_SGM_0130_nodo_referencia.py",
    "results_file":"results/results_exp_SGM_0130_nodo_referencia.json",
    "variant_of":"exp_SGM_0129",
    "lit_refs":["Hipotesis nodo-referencia al acto (Luciano 2026-08-11)",
                "Hebb 1949 - co-ocurrencia acto-resultado consolida",
                "Damasio - somatic markers","Hafner/Crafter 2022 - eat efectivo si cow/plant"],
    "notes":"En Crafter el eat solo sube food si hay cow(+6)/plant(+4) a la vista. El 0129 "
            "mostro que el agente come 52x pero muere con food=0: la mayoria son eats vacios "
            "que no refuerzan eat->nodo0, bloqueando el aprendizaje innato. Este experimento "
            "gatea el acto: cuando eat no produce restauracion (vacio), aplica malestar "
            "intrinseco que impide crear nodo-referencia de restauracion y empuja a buscar. "
            "Es la hipotesis de Luciano aplicada sin hardcode.",
    "notes_criollo":"Luciano pensaba que no es la falta de reward lo que traba, sino que el "
                    "acto de comer genera un nodo de referencia al acto aunque no haya comido "
                    "nada de verdad. En Crafter comer solo sirve si tenes una vaca o planta "
                    "adelante. Este experimento hace que comer 'al pedo' (sin comida) de "
                    "malestar en vez de consolidar, asi el bicho aprende a buscar donde hay "
                    "comida de verdad en vez de quedarse comiendo aire.",
}, open(out,"w"),indent=2)
print(f"\n Guardado en: {out}")