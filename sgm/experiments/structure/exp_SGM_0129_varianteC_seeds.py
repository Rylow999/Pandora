#!/usr/bin/env python3
"""exp_SGM_0129 — Variante C: vida mas larga + multiples seeds (ver si el atractor
de crafting cede ante la necesidad), con drive_noop + instinto hambre real + Hebb.

CONTEXTO 0128: drive_noop saco del noop pero el agente cayo en make_wood_sword 77%
(atractor de crafting) sin moverse ni comer. Opcion C: correr mas pasos (800) y
varias seeds para ver si, al prolongarse la vida, la presion homeostatica + drive
terminan por romper el atractor de crafting y permitir el ciclo de subsistencia.

HIPOTESIS: con mas tiempo (800p), la necesidad homeostatica real mas el drive noop
debieran romper el atractor de crafting en AL MENOS ALGUNA seed: el agente deja de
fabricar, se mueve, gasta, genera hambre, come. Pred: en >=1 de 3 seeds, eat>0,
mov>10, ciclos>=1, y la accion dominante NO es crafting-100%.

No se toca la arquitectura ni el reward: SOLO se da mas vida por seed.
Protocolo: 3 seeds (42, 7, 99), A(con Kuramoto/Hebb). Se reporta por seed y
se mira si alguna sensa del ciclo de subsistencia.

LITERATURA: Panksepp 1998 (SEEKING); Friston active inference; Hafner/Crafter 2022.
"""
import sys, os, random, json
from collections import Counter
sys.path.insert(0, os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm.core.sgm_core import SGMAgent
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
    """Instinto por hambre real de food + compuerta de habituacion."""
    if food_nivel is None or food_nivel >= ag.umbral_hambre_food:
        return 0.0
    conn=ag.conn_type.get((16,0)); st=conn.get("strength",0) if conn else 0
    if (16,0) in ag.consolidadas or st>=UMBRAL_EAT:
        return 0.0
    carencia=max(0.0,ag.umbral_hambre_food-food_nivel)
    return ag.instinto_fuerza_base*(carencia/ag.umbral_hambre_food)


def correr(seed, max_p=800):
    ag=SGMAgent(random.Random(seed),D,n_nodes=N_NODES,gamma=0.01)
    ag.set_edges({i:random.sample(range(N_NODES),min(5,N_NODES-1)) for i in range(N_NODES)})
    env=crafter.Env(); env.reset(); obs,r,t,info=env.step(0)
    tiles=set(); eat_tot=mov=ciclos=0; food_bajo=False
    # seeds: en las corridas, drive noop ya activo en el core
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
        obs,r,t,info=env.step(a)
        ag.actualizar_homeostasis(inv["food"],inv["health"])
        pain=0.0
        if r<0: pain=abs(r)
        elif inv["health"]<5: pain=0.1
        ag.reward(max(0.0,r),pain)
        pos=(px,py)
        if pos not in tiles:
            tiles.add(pos); ag.reward(0.05,0.0)
        ag.incertidumbre_acum=max(0,ag.incertidumbre_acum-0.01)
        eq=ag.cuantizar_estado(sv)
        ag.actualizar_modelo_mundo(getattr(ag,'ultimo_estado_q',eq) or eq,a,eq)
        ag.ultimo_estado_q=eq
        if a==16:
            eat_tot+=1
        if inv["food"]<3:
            food_bajo=True
        elif food_bajo and inv["food"]>=7:
            ciclos+=1; food_bajo=False
        if a in MOV: mov+=1
        if t: break
    muerte={"step":step,"food":float(inv["food"]),"hp":float(inv["health"]),
            "Vg":round(ag.V_grafo,3)} if t else None
    return {"seed":seed,"pasos":step+1,"tiles":len(tiles),"eat":eat_tot,
            "mov":mov,"ciclos":ciclos,"muerte":muerte,"log":[]}


print("="*70)
print(" exp_SGM_0129 — Variante C: mas pasos + seeds (rompe atractor crafting?)")
print("="*70)
SEEDS=[42,7,99]
res=[]
for s in SEEDS:
    res.append(correr(s, max_p=800))

# reporte
for r in res:
    print(f" seed {r['seed']:>3}: {r['pasos']}p {r['tiles']}tiles eat={r['eat']} mov={r['mov']} ciclos={r['ciclos']} muerte={r['muerte']}")

n_cielo=[r for r in res if r['ciclos']>=1]
n_come=[r for r in res if r['eat']>0]
n_muve=[r for r in res if r['mov']>10]
print("\n METRICAS:")
print(f"  seeds con ciclo>=1: {len(n_cielo)}/3")
print(f"  seeds que comen (eat>0): {len(n_come)}/3")
print(f"  seeds que se mueven (mov>10): {len(n_muve)}/3")
print("="*70)

out=os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/"
                       "results/results_exp_SGM_0129_varianteC_seeds.json")
os.makedirs(os.path.dirname(out),exist_ok=True)
json.dump({
    "experiment_id":"exp_SGM_0129",
    "experiment_name":"variante_C_mas_seeds",
    "phase":"Fase 8 - variante C: mas vida + seeds (rompe atractor de crafting?)",
    "date":"2026-08-11",
    "hypothesis":"Con mas pasos (800) y varias seeds, la presion homeostatica real + drive noop "
                 "debiera romper el atractor de crafting en alguna seed: moverse, gastar, "
                 "generar hambre, comer (ciclo de subsistencia). Pred: >=1 de 3 seeds con "
                 "eat>0, mov>10, ciclos>=1, dominante no 100% crafting.",
    "config":{"D":D,"N_NODES":N_NODES,"max_pasos":800,"seeds":SEEDS,
              "drive_noop":"activo en core (umbral 1.5)","homeostasis":"NATIVA Crafter"},
    "result":{"seeds":[{"seed":r["seed"],"pasos":r["pasos"],"tiles":r["tiles"],
                         "eat":r["eat"],"mov":r["mov"],"ciclos":r["ciclos"],
                         "muerte":r["muerte"]} for r in res],
               "n_seeds_ciclo":len(n_cielo),"n_seeds_come":len(n_come),
               "n_seeds_muve":len(n_muve)},
    "script":"experiments/exp_SGM_0129_varianteC_seeds.py",
    "results_file":"results/results_exp_SGM_0129_varianteC_seeds.json",
    "variant_of":"exp_SGM_0128",
    "lit_refs":["Panksepp 1998 - SEEKING","Friston - active inference",
                "Hafner/Crafter 2022 - homeostasis nativa"],
    "notes":"Opcion C: conservador, solo se da mas vida (800p) y mas seeds (42,7,99) con "
            "el core de 0128 (drive_noop + instinto hambre real + Hebb). Sin tocar arquitectura. "
            "Se mide si en alguna seed el atractor de crafting cede ante la subsistencia "
            "(comer, moverse, ciclo). Si ninguna seed sensa del ciclo, se confirma que el "
            "problema es estructural y motiva la opcion A (multiples ejes en paralelo).",
    "notes_criollo":"En el 0128 el agente salio del noop pero se clavo fabricando espadas de "
                    "madera sin moverse ni comer. Antes de redisenar toda la arquitectura, "
                    "miramos si dandole MAS VIDA (800 pasos) a varias semillas, la necesidad "
                    "real (hambre) por fin lo hace salir del atractor de fabricar. Si con mas "
                    "tiempo alguna semilla aprende a comer y moverse, el problema era de "
                    "extension temporal. Si no, es arquitectura.",
}, open(out,"w"),indent=2)
print(f" Guardado en: {out}")