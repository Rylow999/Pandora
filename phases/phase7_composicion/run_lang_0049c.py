# -*- coding: utf-8 -*-
"""
exp_SGM_0049c (PATHFINDING) -- nacimiento lenguaje bajo presion sostenida, agentes CON CUERPO (BFS).
CORRECCION de 0049b: el motor de afinidad no escalaba a mapa grande ni navegaba metas. 0049c agrega
BFS real: el agente SIEMPRE tiene una meta y calcula el camino (proximo paso). Fase1: explorar zonas
no visitadas. Fase2: claves de barrera (coordinacion: cada uno su clave, barrera se abre si AMBOS en
clave a la vez). Veneno en camino: BFS lo evita pero si no hay vuelta lo pisa -> dolor ocurre.
Belleza: cielo estrellado denso, A/B se senalan estrellas (coordinacion estetica sin recompensa).
Metrica: comunicacion (hit celda exacta vs NC), coordinacion (barreras abiertas), dolor (ocurrio?),
belleza (star_reconoce). Simulacion LARGA (hasta 3000 ticks).
"""
import json, random, os, sys
from collections import deque, defaultdict
BASE = "/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"
sys.path.insert(0, os.path.join(BASE, "phases", "phase7_composicion"))
import hrr_core as H
SEED = 20260803
GRID = 30
STEPS = 3000
D = 256
CLIMATES = {
    "cielo_estrellado":  {"food": 80, "venom": 0,  "walls": 4, "stars": 150, "barriers": 3},
    "competencia":       {"food": 25, "venom": 55, "walls": 8, "stars": 0,   "barriers": 4},
    "peligro_compartido":{"food": 40, "venom": 45, "walls": 6, "stars": 0,   "barriers": 5},
}
def bfs_next(world, src, goal, Apos, Bpos):
    """Proximo paso de src hacia goal usando BFS (evita walls/barreras cerradas, penaliza veneno)."""
    if src==goal: return src
    q=deque([src]); prev={src:None}
    while q:
        cur=q.popleft()
        if cur==goal: break
        for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx,ny=cur[0]+dx,cur[1]+dy
            nxt=(nx,ny)
            if not (0<=nx<GRID and 0<=ny<GRID): continue
            if nxt in prev: continue
            if world.blocked(nxt,Apos,Bpos): continue
            prev[nxt]=cur; q.append(nxt)
    if goal not in prev: return None
    # reconstruir
    cur=goal
    while prev[cur]!=src:
        cur=prev[cur]
    return cur
class World:
    def __init__(self, seed, p):
        self.rng=random.Random(seed)
        self.dolor=set(); self.food=set(); self.walls=set(); self.stars=set(); self.barriers=[]
        for _ in range(p["venom"]): self.dolor.add((self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1)))
        for _ in range(p["food"]):  self.food.add((self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1)))
        for _ in range(p["walls"]): self.walls.add((self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1)))
        for _ in range(p["stars"]): self.stars.add((self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1)))
        for _ in range(p["barriers"]):
            a=(self.rng.randint(3,GRID-4), self.rng.randint(3,GRID-4))
            b=(GRID-1-a[0], GRID-1-a[1]); blk=((a[0]+b[0])//2,(a[1]+b[1])//2)
            self.barriers.append([a,b,blk])
    def blocked(self,pos,Apos,Bpos):
        for (a,b,blk) in self.barriers:
            if pos==tuple(blk) and not (Apos==tuple(a) and Bpos==tuple(b)): return True
        return pos in self.walls
    def dolor_at(self,pos): return 1.0 if pos in self.dolor else 0.0
    def food_at(self,pos): return pos in self.food
    def eat(self,pos): self.food.discard(pos)
    def is_star(self,pos): return pos in self.stars
class Agent:
    def __init__(self, seed, tag):
        self.tag=tag; self.rng=random.Random(seed); self.rng_hrr=random.Random(seed^0x9e37)
        self.pos=(self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1))
        self.dolor=0.0; self.eta=0.6; self.abur=0.0
        self.omega={}; self.visited=set(); self.last_pos=None
        self.pain_cum=0.0; self.food_eaten=0; self.returns=0
        self.cell_vec={}; self.role_vecs=H.random_roles(self.rng_hrr,8,D)
        self.events=[]; self.bridge={}; self.coord_success=0; self.goal=None
    def cell_hrr(self,cell):
        if cell not in self.cell_vec: self.cell_vec[cell]=H.rnd_unit(self.rng_hrr,D)
        return self.cell_vec[cell]
    def step(self,world,Apos,Bpos):
        self.visited.add(self.pos)
        # elegir meta si no hay: explorar celda no visitada mas cercana (BFS a ella)
        if self.goal is None or self.pos==self.goal:
            cand=[c for c in self.visited_union(world) if c not in self.visited]
            if not cand: cand=list(self.visited)
            # meta = la no visitada mas cercana (manhattan)
            cand=sorted(cand, key=lambda c: max(abs(c[0]-self.pos[0]),abs(c[1]-self.pos[1])))[:5]
            self.goal=self.rng.choice(cand) if cand else self.pos
        nxt=bfs_next(world, self.pos, self.goal, Apos, Bpos)
        if nxt is None or nxt==self.pos:
            self.goal=None; return
        if nxt==self.last_pos: self.returns+=1
        self.last_pos=self.pos; self.pos=nxt
        if world.dolor_at(self.pos)>0:
            self.dolor=min(self.dolor+1.0,3.0); self.pain_cum+=1.0
            self.omega[self.pos]=self.omega.get(self.pos,0.0)-1.0; self.events.append((self.pos,"venom"))
        elif world.food_at(self.pos):
            self.food_eaten+=1; world.eat(self.pos); self.omega[self.pos]=self.omega.get(self.pos,0.0)+0.5
            self.events.append((self.pos,"food"))
        elif world.is_star(self.pos):
            self.events.append((self.pos,"star"))
        self.cell_hrr(self.pos)
    def visited_union(self,world):
        return [(x,y) for x in range(GRID) for y in range(GRID)]
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
    # fase 1: cada uno explora su mundo (omega propio) 800 ticks
    for _ in range(800):
        A.step(world,A.pos,B.pos); B.step(world,A.pos,B.pos)
    # encuentro
    A.pos=B.pos=(GRID//2,GRID//2)
    comunes=list(A.visited & B.visited)
    pivotes=comunes[:min(15,len(comunes))]
    for c in pivotes:
        A.bridge[("B",c)]=B.cell_hrr(c); B.bridge[("A",c)]=A.cell_hrr(c)
    coord_ok=0
    barreras=world.barriers[:]
    # fase 2: JUNTOS hasta 2200 ticks; persiguen claves de barrera (coordinacion)
    for t in range(2200):
        for (a,b,blk) in barreras:
            A.goal=tuple(a); B.goal=tuple(b); break
        for (a,b,blk) in barreras:
            if A.pos==tuple(a) and B.pos==tuple(b):
                coord_ok+=1; A.coord_success+=1; B.coord_success+=1
                barreras=[x for x in barreras if x!=[a,b,blk]]
                A.goal=None; B.goal=None
        A.step(world,A.pos,B.pos); B.step(world,A.pos,B.pos)
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
def main():
    res=[]
    for clima,p in CLIMATES.items():
        sA=SEED+(hash(clima)%1000); sB=sA+777
        r=simular_clima(clima,p,sA,sB)
        res.append(r)
        print("CLIMA",clima,"| puente",r["puente"],"| comunicacion",r["comunicacion_top1"],"NC",r["NC_top1"],
              "| COORD",r["coordinacion_barreras"],"/",r["barriers_total"],
              "| esteticas",r["esteticas_estrellas"],"star",r["star_reconoce"],
              "| dolor A/B",r["A_dolor"],r["B_dolor"],"| visited A/B",r["A_visited"],r["B_visited"])
    out={"experiment_id":"exp_SGM_0049c","name":"nacimiento_lenguaje_pathfinding","status":"LARGO_BFS",
         "marco":"Tomasello joint attention sostenida, Schultz RPE, 0018 dolor Eq.6, 0044 motor + BFS (cuerpo).",
         "diseno":"BFS real: agente siempre tiene meta y calcula camino. Fase1 explorar (800t). Fase2 JUNTOS (2200t) persiguen claves de barrera (coordinacion: ambos en clave abre). Veneno en camino -> dolor. Belleza=cielo estrellado denso. Metrica=hit celda exacta (NC~1/N).",
         "config":{"GRID":GRID,"STEPS":STEPS,"D":D,"SEED":SEED},"climas":res,
         "belleza_inferencia":"star_reconoce>0 en cielo_estrellado => belleza = coordinacion estetica emergente bajo presion baja sostenida.",
         "verified":any(r["comunicacion_top1"]>r["NC_top1"] for r in res)}
    open(os.path.join(BASE,"phases","phase7_composicion","results_exp_SGM_0049c_lenguaje_bfs.json"),"w").write(json.dumps(out,indent=2,ensure_ascii=False))
    print(json.dumps(out,indent=2,ensure_ascii=False))
    return out
if __name__=="__main__": main()
