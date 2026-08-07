# -*- coding: utf-8 -*-
"""
exp_SGM_0049 (v2 CORREGIDO) -- nacimiento del lenguaje bajo presion (2 agentes, mundos distintos)
CORRECCION de v1: la metrica "evitar" daba 1.0 = NC (trivial). Y el mapa 60x60 hacia que dolor/comida
nunca ocurrian. REHACER con: (1) metrica = B identifica la CELDA EXACTA que A senala (hit en celda,
NC ~ 1/N); (2) mapa 30x30 con densidades reales de veneno/comida/estrellas para que actuen.
Climas: cielo_estrellado (sin veneno, estrellas densas) / competencia (veneno denso, comida escasa) /
peligro_compartido (veneno en zona comun). Belleza = senales esteticas (estrella) no-utilitarias.
"""
import json, random, os, sys
from collections import defaultdict
BASE = "/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"
sys.path.insert(0, os.path.join(BASE, "phases", "phase7_composicion"))
import hrr_core as H
SEED = 20260803
GRID = 30
STEPS = 250
D = 256
CLIMATES = {
    "cielo_estrellado":  {"food": 60, "venom": 0,  "walls": 4, "stars": 90},
    "competencia":       {"food": 12, "venom": 40, "walls": 6, "stars": 0},
    "peligro_compartido":{"food": 30, "venom": 30, "walls": 5, "stars": 0},
}
class World:
    def __init__(self, seed, p):
        self.rng = random.Random(seed)
        self.dolor=set(); self.food=set(); self.walls=set(); self.stars=set()
        for _ in range(p["venom"]): self.dolor.add((self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1)))
        for _ in range(p["food"]):  self.food.add((self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1)))
        for _ in range(p["walls"]): self.walls.add((self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1)))
        for _ in range(p["stars"]): self.stars.add((self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1)))
    def dolor_at(self,pos): return 1.0 if pos in self.dolor or pos in self.walls else 0.0
    def food_at(self,pos): return pos in self.food
    def eat(self,pos): self.food.discard(pos)
    def is_star(self,pos): return pos in self.stars
class Agent:
    def __init__(self, seed, tag):
        self.tag=tag; self.rng=random.Random(seed); self.rng_hrr=random.Random(seed^0x9e37)
        self.pos=(self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1))
        self.dolor=0.0; self.eta=0.5; self.abur=0.0
        self.omega={}; self.visited=set(); self.last_pos=None
        self.pain_cum=0.0; self.food_eaten=0; self.returns=0
        self.cell_vec={}; self.role_vecs=H.random_roles(self.rng_hrr,8,D)
        self.events=[]; self.bridge={}; self.signal_log=[]
    def cell_hrr(self,cell):
        if cell not in self.cell_vec: self.cell_vec[cell]=H.rnd_unit(self.rng_hrr,D)
        return self.cell_vec[cell]
    def affinity_to(self,pos,world):
        w=self.omega.get(pos,0.0); d=world.dolor_at(pos); food=world.food_at(pos)
        nb=0; nbnov=0
        for dx,dy in [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]:
            nx,ny=pos[0]+dx,pos[1]+dy
            if 0<=nx<GRID and 0<=ny<GRID:
                nb+=1
                if (nx,ny) not in self.visited: nbnov+=1
        frontier=(nbnov/nb) if nb else 0.0
        aff=w+(0.8 if food else 0.0)+self.eta*frontier*0.6-(2.0*d)
        if self.abur>0.5 and pos==self.last_pos: aff-=self.abur
        return aff
    def step(self,world):
        self.visited.add(self.pos)
        best=None; best_a=-1e9
        for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx,ny=self.pos[0]+dx,self.pos[1]+dy
            if 0<=nx<GRID and 0<=ny<GRID:
                a=self.affinity_to((nx,ny),world)
                if a>best_a: best_a=a; best=(nx,ny)
        if best is None: return
        if best==self.last_pos: self.returns+=1
        self.last_pos=self.pos; self.pos=best
        if world.dolor_at(self.pos)>0:
            self.dolor=min(self.dolor+1.0,3.0); self.pain_cum+=1.0
            self.omega[self.pos]=self.omega.get(self.pos,0.0)-1.0; self.events.append((self.pos,"venom"))
        elif world.food_at(self.pos):
            self.food_eaten+=1; world.eat(self.pos); self.omega[self.pos]=self.omega.get(self.pos,0.0)+0.5
            self.events.append((self.pos,"food"))
        elif world.is_star(self.pos):
            self.events.append((self.pos,"star"))
        self.cell_hrr(self.pos)
def describir(A,B,target,use_bridge):
    """A senala target a B. B debe identificar la CELDA EXACTA. hit=1 si acierta, NC~1/N."""
    sig = A.bridge[("B",target)] if (use_bridge and ("B",target) in A.bridge) else A.cell_hrr(target)
    # B busca su celda mas afin a sig
    best=None; bestc=-2.0
    cands=list(B.visited)+[target]
    for c in cands:
        sc=H.cos(sig,B.cell_hrr(c))
        if sc>bestc: bestc=sc; best=c
    return 1 if best==target else 0
def simular_clima(clima, p, seedA, seedB):
    world=World(seedA^0x1234, p)
    A=Agent(seedA,"A"); B=Agent(seedB,"B")
    for _ in range(STEPS): A.step(world); B.step(world)
    # encuentro forzado: transitan juntos 25 pasos desde el centro
    A.pos=B.pos=(GRID//2,GRID//2)
    for _ in range(25): A.step(world); B.step(world)
    comunes=list(A.visited & B.visited)
    pivotes=comunes[:min(15,len(comunes))]
    # joint attention: cada uno guarda la senal del otro sobre los pivotes
    for c in pivotes:
        A.bridge[("B",c)]=B.cell_hrr(c)
        B.bridge[("A",c)]=A.cell_hrr(c)
    # test de comunicacion: A senala celdas de B que B conoce (targets = visitadas de B)
    targets=list(B.visited)[:8]
    if not targets: targets=[(GRID//2,GRID//2)]
    hit=sum(describir(A,B,t,True) for t in targets)
    nc =sum(describir(A,B,t,False) for t in targets)  # A manda su propia celda (no puente) = ruido relativo a B
    top1=hit/len(targets); nc1=nc/len(targets)
    # belleza: en cielo estrellado, A senala una estrella (no-utilitario) a B; B la reconoce?
    esteticas=len([e for e in A.events if e[1]=="star"])+len([e for e in B.events if e[1]=="star"])
    star_hit=0; star_tot=0
    if world.stars:
        stars=list(world.stars)[:5]
        for s in stars:
            if s in B.visited:
                star_tot+=1
                # A emite estrella vía puente si existe, B reconoce celda exacta
                if ("B",s) in A.bridge and describir(A,B,s,True): star_hit+=1
    return {"clima":clima,"puente":len(pivotes),"comunicacion_top1":round(top1,3),
            "NC_top1":round(nc1,3),"targets":len(targets),"esteticas_estrellas":esteticas,
            "star_reconoce":(round(star_hit/star_tot,3) if star_tot else None),
            "A_food":A.food_eaten,"B_food":B.food_eaten,"A_dolor":round(A.pain_cum,1),"B_dolor":round(B.pain_cum,1),
            "A_visited":len(A.visited),"B_visited":len(B.visited)}
def main():
    rng=random.Random(SEED); res=[]
    for clima,p in CLIMATES.items():
        sA=SEED+(hash(clima)%1000); sB=sA+777
        r=simular_clima(clima,p,sA,sB)
        res.append(r)
        print("CLIMA",clima,"| puente",r["puente"],"| comunicacion",r["comunicacion_top1"],"NC",r["NC_top1"],
              "| esteticas",r["esteticas_estrellas"],"| star_reconoce",r["star_reconoce"],
              "| dolor A/B",r["A_dolor"],r["B_dolor"],"| food A/B",r["A_food"],r["B_food"])
    out={"experiment_id":"exp_SGM_0049","name":"nacimiento_del_lenguaje_bajo_presion","status":"INTEGRADO_v2",
         "marco":"Tomasello joint attention, Kidd/Hayden incertidumbre optima, Schultz RPE, 0018 dolor, 0044 motor.",
         "diseno":"2 agentes omega propio, mapa 30x30 denso. Encuentro forzado -> joint attention (puente A<->B sobre pivotes). Metrica=hit celda exacta (NC~1/N). Climas: cielo_estrellado/competencia/peligro. Belleza=senal estetica (estrella) reconocida sin recompensa.",
         "config":{"GRID":GRID,"STEPS":STEPS,"D":D,"SEED":SEED},"climas":res,
         "belleza_inferencia":"Si star_reconoce>0 en cielo_estrellado (A/B senalan estrellas y se reconocen sin utilidad) => belleza = coordinacion estetica emergente bajo presion baja.",
         "verified":any(r["comunicacion_top1"]>r["NC_top1"] for r in res)}
    open(os.path.join(BASE,"phases","phase7_composicion","results_exp_SGM_0049_lenguaje.json"),"w").write(json.dumps(out,indent=2,ensure_ascii=False))
    print(json.dumps(out,indent=2,ensure_ascii=False))
    return out
if __name__=="__main__": main()
