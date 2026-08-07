# -*- coding: utf-8 -*-
"""
exp_SGM_0049b (LARGO + COORDINACION OBLIGATORIA) -- nacimiento lenguaje bajo presion sostenida.
CORRECCION de 0049: simulacion MUCHO MAS LARGA (2000 ticks), A y B JUNTOS todo el tiempo tras encuentro.
Dificultades que NO se sortean de a uno: BARRERAS que solo se abren si AMBOS estan en celdas-clave a la vez
(puente que necesita que A empuje desde un lado y B desde otro). Veneno EN EL CAMINO (dolor ocurre).
Belleza: cielo estrellado denso, A/B se senalan estrellas (coordinacion estetica).
Metrica: comunicacion (hit celda exacta vs NC), dolor (ocurrio?), coordinacion (superaron barreras juntos?),
belleza (star_reconoce).
"""
import json, random, os, sys
from collections import defaultdict
BASE = "/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"
sys.path.insert(0, os.path.join(BASE, "phases", "phase7_composicion"))
import hrr_core as H
SEED = 20260803
GRID = 30
STEPS = 2000          # simulacion larga
D = 256
CLIMATES = {
    "cielo_estrellado":  {"food": 80, "venom": 0,  "walls": 4, "stars": 120, "barriers": 2},
    "competencia":       {"food": 20, "venom": 50, "walls": 8, "stars": 0,   "barriers": 3},
    "peligro_compartido":{"food": 40, "venom": 40, "walls": 6, "stars": 0,   "barriers": 4},
}
class World:
    def __init__(self, seed, p):
        self.rng = random.Random(seed)
        self.dolor=set(); self.food=set(); self.walls=set(); self.stars=set()
        self.barriers=[]   # (celda_clave_A, celda_clave_B, celda_bloqueada) -> se abre si ambos en claves
        for _ in range(p["venom"]): self.dolor.add((self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1)))
        for _ in range(p["food"]):  self.food.add((self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1)))
        for _ in range(p["walls"]): self.walls.add((self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1)))
        for _ in range(p["stars"]): self.stars.add((self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1)))
        # barreras de coordinacion: celda bloqueada entre dos claves; solo se abre si A y B en claves simultaneo
        for _ in range(p["barriers"]):
            a=(self.rng.randint(2,GRID-3), self.rng.randint(2,GRID-3))
            b=(GRID-1-a[0], GRID-1-a[1])   # clave B opuesta (lejos -> requiere coordinarse)
            blk=( (a[0]+b[0])//2, (a[1]+b[1])//2 )
            self.barriers.append((a,b,blk))
    def blocked(self, pos, Apos, Bpos):
        for (a,b,blk) in self.barriers:
            if pos==blk and not (Apos==a and Bpos==b):
                return True
        return pos in self.walls
    def dolor_at(self,pos): return 1.0 if pos in self.dolor else 0.0
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
        self.coord_success=0   # cuantas barreras ayudo a abrir
    def cell_hrr(self,cell):
        if cell not in self.cell_vec: self.cell_vec[cell]=H.rnd_unit(self.rng_hrr,D)
        return self.cell_vec[cell]
    def affinity_to(self,pos,world,Apos,Bpos):
        w=self.omega.get(pos,0.0); d=world.dolor_at(pos); food=world.food_at(pos)
        bl=world.blocked(pos,Apos,Bpos)
        nb=0; nbnov=0
        for dx,dy in [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]:
            nx,ny=pos[0]+dx,pos[1]+dy
            if 0<=nx<GRID and 0<=ny<GRID:
                nb+=1
                if (nx,ny) not in self.visited: nbnov+=1
        frontier=(nbnov/nb) if nb else 0.0
        aff=w+(0.8 if food else 0.0)+self.eta*frontier*0.6-(2.0*d)-(3.0 if bl else 0.0)
        if self.abur>0.5 and pos==self.last_pos: aff-=self.abur
        return aff
    def step(self,world,Apos,Bpos):
        self.visited.add(self.pos)
        best=None; best_a=-1e9
        for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx,ny=self.pos[0]+dx,self.pos[1]+dy
            if 0<=nx<GRID and 0<=ny<GRID and not world.blocked((nx,ny),Apos,Bpos):
                a=self.affinity_to((nx,ny),world,Apos,Bpos)
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
    sig = A.bridge[("B",target)] if (use_bridge and ("B",target) in A.bridge) else A.cell_hrr(target)
    best=None; bestc=-2.0
    for c in list(B.visited)+[target]:
        sc=H.cos(sig,B.cell_hrr(c))
        if sc>bestc: bestc=sc; best=c
    return 1 if best==target else 0
def simular_clima(clima, p, seedA, seedB):
    world=World(seedA^0x1234, p)
    A=Agent(seedA,"A"); B=Agent(seedB,"B")
    # fase 1: cada uno transita su mundo (omega propio distinto) - 500 ticks
    for _ in range(500):
        A.step(world,A.pos,B.pos); B.step(world,A.pos,B.pos)
    # fase 2: ENCUENTRO y se quedan JUNTOS el resto (2000 ticks total, coordinando barreras)
    A.pos=B.pos=(GRID//2,GRID//2)
    comunes=list(A.visited & B.visited)
    pivotes=comunes[:min(15,len(comunes))]
    for c in pivotes:
        A.bridge[("B",c)]=B.cell_hrr(c); B.bridge[("A",c)]=A.cell_hrr(c)
    coord_ok=0
    for t in range(1500):
        # barreras: si ambos en claves -> se abre (coordinacion lograda)
        for (a,b,blk) in world.barriers:
            if A.pos==a and B.pos==b:
                coord_ok+=1
                A.coord_success+=1; B.coord_success+=1
        A.step(world,A.pos,B.pos); B.step(world,A.pos,B.pos)
        # senalizacion: si A ve veneno cerca, lo senala a B (lenguaje utilitario)
        for dpos in world.dolor:
            if max(abs(dpos[0]-A.pos[0]),abs(dpos[1]-A.pos[1]))<=3:
                A.bridge[("B_warn",dpos)]=A.cell_hrr(dpos); break
    # test comunicacion: A senala celdas de B que B conoce
    targets=list(B.visited)[-8:]
    if not targets: targets=[(GRID//2,GRID//2)]
    hit=sum(describir(A,B,t,True) for t in targets)
    nc =sum(describir(A,B,t,False) for t in targets)
    top1=hit/len(targets); nc1=nc/len(targets)
    # belleza: cielo estrellado, A senala estrella a B sin recompensa
    esteticas=len([e for e in A.events if e[1]=="star"])+len([e for e in B.events if e[1]=="star"])
    star_hit=0; star_tot=0
    if world.stars:
        for s in list(world.stars)[:8]:
            if s in B.visited:
                star_tot+=1
                if ("B",s) in A.bridge and describir(A,B,s,True): star_hit+=1
    return {"clima":clima,"puente":len(pivotes),"comunicacion_top1":round(top1,3),"NC_top1":round(nc1,3),
            "targets":len(targets),"coordinacion_barreras":coord_ok,"barriers":len(world.barriers),
            "esteticas_estrellas":esteticas,"star_reconoce":(round(star_hit/star_tot,3) if star_tot else None),
            "A_food":A.food_eaten,"B_food":B.food_eaten,"A_dolor":round(A.pain_cum,1),"B_dolor":round(B.pain_cum,1),
            "A_visited":len(A.visited),"B_visited":len(B.visited)}
def main():
    res=[]
    for clima,p in CLIMATES.items():
        sA=SEED+(hash(clima)%1000); sB=sA+777
        r=simular_clima(clima,p,sA,sB)
        res.append(r)
        print("CLIMA",clima,"| puente",r["puente"],"| comunicacion",r["comunicacion_top1"],"NC",r["NC_top1"],
              "| COORD barreras",r["coordinacion_barreras"],"/",r["barriers"],
              "| esteticas",r["esteticas_estrellas"],"star",r["star_reconoce"],
              "| dolor A/B",r["A_dolor"],r["B_dolor"],"| food A/B",r["A_food"],r["B_food"])
    out={"experiment_id":"exp_SGM_0049b","name":"nacimiento_lenguaje_largo_coord","status":"LARGO_COORD",
         "marco":"Tomasello joint attention sostenida, Schultz RPE, 0018 dolor Eq.6, 0044 motor, barreras de coordinacion.",
         "diseno":"Mapa 30x30, 2000 ticks. Fase1: omega propio 500 ticks. Fase2: encuentro + JUNTOS 1500 ticks. Barreras que solo se abren si AMBOS en claves (no sorteables de a uno). Veneno en camino. Belleza=cielo estrellado denso, senal estetica. Metrica=hit celda exacta (NC~1/N).",
         "config":{"GRID":GRID,"STEPS":STEPS,"D":D,"SEED":SEED},"climas":res,
         "belleza_inferencia":"star_reconoce>0 en cielo_estrellado => belleza = coordinacion estetica emergente bajo presion baja sostenida.",
         "verified":any(r["comunicacion_top1"]>r["NC_top1"] for r in res)}
    open(os.path.join(BASE,"phases","phase7_composicion","results_exp_SGM_0049b_lenguaje_largo.json"),"w").write(json.dumps(out,indent=2,ensure_ascii=False))
    print(json.dumps(out,indent=2,ensure_ascii=False))
    return out
if __name__=="__main__": main()
class Agent:
    def __init__(self, seed, tag):
        self.tag=tag; self.rng=random.Random(seed); self.rng_hrr=random.Random(seed^0x9e37)
        self.pos=(self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1))
        self.dolor=0.0; self.eta=0.6; self.abur=0.0
        self.omega={}; self.visited=set(); self.last_pos=None
        self.pain_cum=0.0; self.food_eaten=0; self.returns=0
        self.cell_vec={}; self.role_vecs=H.random_roles(self.rng_hrr,8,D)
        self.events=[]; self.bridge={}; self.signal_log=[]; self.coord_success=0
        self.goal=None   # celda meta (fase 2: clave de barrera)
    def cell_hrr(self,cell):
        if cell not in self.cell_vec: self.cell_vec[cell]=H.rnd_unit(self.rng_hrr,D)
        return self.cell_vec[cell]
    def affinity_to(self,pos,world,Apos,Bpos):
        w=self.omega.get(pos,0.0); d=world.dolor_at(pos); food=world.food_at(pos)
        bl=world.blocked(pos,Apos,Bpos)
        nb=0; nbnov=0
        for dx,dy in [(0,1),(0,-1),(1,0),(-1,0),(1,1),(1,-1),(-1,1),(-1,-1)]:
            nx,ny=pos[0]+dx,pos[1]+dy
            if 0<=nx<GRID and 0<=ny<GRID:
                nb+=1
                if (nx,ny) not in self.visited: nbnov+=1
        frontier=(nbnov/nb) if nb else 0.0
        aff=w+(0.8 if food else 0.0)+self.eta*frontier*0.6-(2.0*d)-(3.0 if bl else 0.0)
        # en fase 2, atraccion a la meta (goal) para recorrer el mapa y encontrarse
        if self.goal is not None:
            gd=max(abs(pos[0]-self.goal[0]),abs(pos[1]-self.goal[1]))
            aff += (5.0/(1.0+gd))   # premia estar cerca de la meta
        return aff
    def step(self,world,Apos,Bpos):
        self.visited.add(self.pos)
        best=None; best_a=-1e9
        for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx,ny=self.pos[0]+dx,self.pos[1]+dy
            if 0<=nx<GRID and 0<=ny<GRID and not world.blocked((nx,ny),Apos,Bpos):
                a=self.affinity_to((nx,ny),world,Apos,Bpos)
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
    sig = A.bridge[("B",target)] if (use_bridge and ("B",target) in A.bridge) else A.cell_hrr(target)
    best=None; bestc=-2.0
    for c in list(B.visited)+[target]:
        sc=H.cos(sig,B.cell_hrr(c))
        if sc>bestc: bestc=sc; best=c
    return 1 if best==target else 0
def simular_clima(clima, p, seedA, seedB):
    world=World(seedA^0x1234, p)
    A=Agent(seedA,"A"); B=Agent(seedB,"B")
    for _ in range(500):
        A.step(world,A.pos,B.pos); B.step(world,A.pos,B.pos)
    A.pos=B.pos=(GRID//2,GRID//2)
    comunes=list(A.visited & B.visited)
    pivotes=comunes[:min(15,len(comunes))]
    for c in pivotes:
        A.bridge[("B",c)]=B.cell_hrr(c); B.bridge[("A",c)]=A.cell_hrr(c)
    coord_ok=0
    # fase 2: JUNTOS 1500 ticks; persiguen claves de barrera (coordinacion real: cada uno su clave)
    barreras=world.barriers
    for t in range(1500):
        # asignar metas: A va a clave a, B va a clave b de la primer barrera no resuelta
        for (a,b,blk) in barreras:
            if (a,b,blk) not in [("done")]:
                A.goal=a; B.goal=b
                break
        # si ambos en claves -> barrera abierta (coordinacion lograda)
        for (a,b,blk) in barreras:
            if A.pos==a and B.pos==b:
                coord_ok+=1
                A.coord_success+=1; B.coord_success+=1
        A.step(world,A.pos,B.pos); B.step(world,A.pos,B.pos)
        for (a,b,blk) in barreras:
            if A.pos==a and B.pos==b:
                barreras=[(x,y,z) for (x,y,z) in barreras if (x,y,z)!=(a,b,blk)]
                A.goal=None; B.goal=None
        # senalizacion utilitaria: A avisa veneno cercano
        for dpos in world.dolor:
            if max(abs(dpos[0]-A.pos[0]),abs(dpos[1]-A.pos[1]))<=3:
                A.bridge[("B_warn",dpos)]=A.cell_hrr(dpos); break
    targets=list(B.visited)[-8:]
    if not targets: targets=[(GRID//2,GRID//2)]
    hit=sum(describir(A,B,t,True) for t in targets)
    nc =sum(describir(A,B,t,False) for t in targets)
    top1=hit/len(targets); nc1=nc/len(targets)
    esteticas=len([e for e in A.events if e[1]=="star"])+len([e for e in B.events if e[1]=="star"])
    star_hit=0; star_tot=0
    if world.stars:
        for s in list(world.stars)[:8]:
            if s in B.visited:
                star_tot+=1
                if ("B",s) in A.bridge and describir(A,B,s,True): star_hit+=1
    return {"clima":clima,"puente":len(pivotes),"comunicacion_top1":round(top1,3),"NC_top1":round(nc1,3),
            "targets":len(targets),"coordinacion_barreras":coord_ok,"barriers_total":len(world.barriers),
            "esteticas_estrellas":esteticas,"star_reconoce":(round(star_hit/star_tot,3) if star_tot else None),
            "A_food":A.food_eaten,"B_food":B.food_eaten,"A_dolor":round(A.pain_cum,1),"B_dolor":round(B.pain_cum,1),
            "A_visited":len(A.visited),"B_visited":len(B.visited)}
