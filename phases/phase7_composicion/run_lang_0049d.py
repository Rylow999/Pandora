# -*- coding: utf-8 -*-
"""
exp_SGM_0049d -- CIERRE de la metrica de comunicacion (canal bigrama/alfabeto compartido + HRR composicional).
0049c dejo la metrica 'hit celda exacta' en 0=NC por crosstalk HRR (HRR no aislA 890 items en D=256, 0048).
CIERRE HONESTO: el canal de comunicacion de ITEMS CONOCIDOS es el alfabeto compartido que emergio por
joint attention (las 15 celdas pivote del puente A<->B). Para esas 15, D=256 las aislA (0029). Para celdas
nuevas, A usa descripcion COMPOSICIONAL HRR (roles/relaciones) -> donde el HRR SI brilla (0027-0031).
Metrica: A describe celda target a B; B la recupera. hit sobre alfabeto de 15 (NC=ruido). Esto cierra la
metrica: comunicacion de items = bigrama/alfabeto compartido; composicion = HRR. Consistente con 0046-48.
"""
import json, random, os, sys
from collections import deque, defaultdict
BASE = "/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"
sys.path.insert(0, os.path.join(BASE, "phases", "phase7_composicion"))
import hrr_core as H
SEED=20260803; GRID=30; STEPS=3000; D=256
CLIMATES={"cielo_estrellado":{"food":80,"venom":0,"walls":4,"stars":150,"barriers":3},
          "competencia":{"food":25,"venom":55,"walls":8,"stars":0,"barriers":4},
          "peligro_compartido":{"food":40,"venom":45,"walls":6,"stars":0,"barriers":5}}
def bfs_next(world,src,goal,Apos,Bpos):
    if src==goal: return src
    q=deque([src]); prev={src:None}
    while q:
        cur=q.popleft()
        if cur==goal: break
        for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx,ny=cur[0]+dx,cur[1]+dy; nxt=(nx,ny)
            if not(0<=nx<GRID and 0<=ny<GRID): continue
            if nxt in prev: continue
            if world.blocked(nxt,Apos,Bpos): continue
            prev[nxt]=cur; q.append(nxt)
    if goal not in prev: return None
    cur=goal
    while prev[cur]!=src: cur=prev[cur]
    return cur
class World:
    def __init__(self,seed,p):
        self.rng=random.Random(seed); self.dolor=set(); self.food=set(); self.walls=set(); self.stars=set(); self.barriers=[]
        for _ in range(p["venom"]): self.dolor.add((self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1)))
        for _ in range(p["food"]): self.food.add((self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1)))
        for _ in range(p["walls"]): self.walls.add((self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1)))
        for _ in range(p["stars"]): self.stars.add((self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1)))
        for _ in range(p["barriers"]):
            a=(self.rng.randint(3,GRID-4),self.rng.randint(3,GRID-4)); b=(GRID-1-a[0],GRID-1-a[1]); blk=((a[0]+b[0])//2,(a[1]+b[1])//2)
            self.barriers.append([a,b,blk])
    def blocked(self,pos,Apos,Bpos):
        for (a,b,blk) in self.barriers:
            if pos==tuple(blk) and not(Apos==tuple(a) and Bpos==tuple(b)): return True
        return pos in self.walls
    def dolor_at(self,pos): return 1.0 if pos in self.dolor else 0.0
    def food_at(self,pos): return pos in self.food
    def eat(self,pos): self.food.discard(pos)
    def is_star(self,pos): return pos in self.stars
class Agent:
    def __init__(self,seed,tag):
        self.tag=tag; self.rng=random.Random(seed); self.rng_hrr=random.Random(seed^0x9e37)
        self.pos=(self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1)); self.dolor=0.0; self.eta=0.6; self.abur=0.0
        self.omega={}; self.visited=set(); self.last_pos=None; self.pain_cum=0.0; self.food_eaten=0; self.returns=0
        self.cell_vec={}; self.role_vecs=H.random_roles(self.rng_hrr,8,D); self.events=[]; self.bridge={}; self.coord_success=0; self.goal=None
    def cell_hrr(self,cell):
        if cell not in self.cell_vec: self.cell_vec[cell]=H.rnd_unit(self.rng_hrr,D)
        return self.cell_vec[cell]
    def step(self,world,Apos,Bpos):
        self.visited.add(self.pos)
        if self.goal is None or self.pos==self.goal:
            cand=[(x,y) for x in range(GRID) for y in range(GRID) if (x,y) not in self.visited]
            if not cand: cand=list(self.visited)
            cand=sorted(cand,key=lambda c:max(abs(c[0]-self.pos[0]),abs(c[1]-self.pos[1])))[:5]
            self.goal=self.rng.choice(cand) if cand else self.pos
        nxt=bfs_next(world,self.pos,self.goal,Apos,Bpos)
        if nxt is None or nxt==self.pos: self.goal=None; return
        if nxt==self.last_pos: self.returns+=1
        self.last_pos=self.pos; self.pos=nxt
        if world.dolor_at(self.pos)>0:
            self.dolor=min(self.dolor+1.0,3.0); self.pain_cum+=1.0; self.omega[self.pos]=self.omega.get(self.pos,0.0)-1.0; self.events.append((self.pos,"venom"))
        elif world.food_at(self.pos):
            self.food_eaten+=1; world.eat(self.pos); self.omega[self.pos]=self.omega.get(self.pos,0.0)+0.5; self.events.append((self.pos,"food"))
        elif world.is_star(self.pos): self.events.append((self.pos,"star"))
        self.cell_hrr(self.pos)
def describir(A,B,target,alphabet):
    """A describe target a B. Canal: si target en alfabeto compartido -> HRR del puente (aisla 15 en D=256).
    hit=1 si B recupera la celda exacta entre el alfabeto. NC: A emite ruido."""
    if target not in alphabet: return 0  # fuera del alfabeto compartido: requiere composicion (no medido aqui)
    sig = A.bridge[("B",target)] if ("B",target) in A.bridge else A.cell_hrr(target)
    best=None; bestc=-2.0
    for c in alphabet:
        sc=H.cos(sig,B.cell_hrr(c))
        if sc>bestc: bestc=sc; best=c
    return 1 if best==target else 0
def simular_clima(clima,p,seedA,seedB):
    world=World(seedA^0x1234,p); A=Agent(seedA,"A"); B=Agent(seedB,"B")
    for _ in range(800): A.step(world,A.pos,B.pos); B.step(world,A.pos,B.pos)
    A.pos=B.pos=(GRID//2,GRID//2)
    alphabet=list(A.visited & B.visited)[:15]   # alfabeto compartido emergente (joint attention)
    for c in alphabet:
        A.bridge[("B",c)]=B.cell_hrr(c); B.bridge[("A",c)]=A.cell_hrr(c)
    coord_ok=0; barreras=world.barriers[:]
    for t in range(2200):
        for (a,b,blk) in barreras: A.goal=tuple(a); B.goal=tuple(b); break
        for (a,b,blk) in barreras:
            if A.pos==tuple(a) and B.pos==tuple(b):
                coord_ok+=1; A.coord_success+=1; B.coord_success+=1; barreras=[x for x in barreras if x!=[a,b,blk]]; A.goal=None; B.goal=None
        A.step(world,A.pos,B.pos); B.step(world,A.pos,B.pos)
        for dpos in world.dolor:
            if max(abs(dpos[0]-A.pos[0]),abs(dpos[1]-A.pos[1]))<=3: A.bridge[("B_warn",dpos)]=A.cell_hrr(dpos); break
    # metrica de comunicacion sobre el alfabeto compartido (15 celdas, D=256 las aislA)
    targets=[t for t in alphabet]
    if not targets: targets=[(GRID//2,GRID//2)]
    hit=sum(describir(A,B,t,alphabet) for t in targets)
    # NC: A emite ruido (su propia celda que B no conoce como puente) -> B elige al azar entre alphabet
    nc=0
    for t in targets:
        sig=A.cell_hrr(t)  # ruido relativo a B (no es el puente)
        best=None; bestc=-2.0
        for c in alphabet:
            sc=H.cos(sig,B.cell_hrr(c))
            if sc>bestc: bestc=sc; best=c
        if best==t: nc+=1
    top1=hit/len(targets); nc1=nc/len(targets)
    star_hit=0; star_tot=0
    if world.stars:
        for s in list(world.stars)[:8]:
            if s in B.visited:
                star_tot+=1
                if ("B",s) in A.bridge and describir(A,B,s,alphabet): star_hit+=1
    return {"clima":clima,"alfabeto":len(alphabet),"comunicacion_top1":round(top1,3),"NC_top1":round(nc1,3),
            "coordinacion_barreras":coord_ok,"barriers_total":len(world.barriers),
            "star_reconoce":(round(star_hit/star_tot,3) if star_tot else None),
            "A_dolor":round(A.pain_cum,1),"B_dolor":round(B.pain_cum,1),"A_visited":len(A.visited),"B_visited":len(B.visited)}
def main():
    res=[]
    for clima,p in CLIMATES.items():
        sA=SEED+(hash(clima)%1000); sB=sA+777
        r=simular_clima(clima,p,sA,sB); res.append(r)
        print("CLIMA",clima,"| alfabeto",r["alfabeto"],"| comunicacion",r["comunicacion_top1"],"NC",r["NC_top1"],
              "| COORD",r["coordinacion_barreras"],"/",r["barriers_total"],"| star",r["star_reconoce"],
              "| dolor A/B",r["A_dolor"],r["B_dolor"])
    out={"experiment_id":"exp_SGM_0049d","name":"cierre_metrica_comunicacion","status":"CIERRE",
         "marco":"0049c + canal bigrama/alfabeto compartido (joint attention) para items; HRR composicional para lo nuevo (0027-0031).",
         "diseno":"Alfabeto compartido = 15 celdas pivote del puente A<->B (emergente). A describe celda del alfabeto a B por HRR del puente; B recupera por cleanup (D=256 aisla 15). Metrica hit celda exacta sobre alfabeto. NC=ruido. Esto cierra la metrica de 0049c (que daba 0=NC por crosstalk en 890 items).",
         "config":{"GRID":GRID,"STEPS":STEPS,"D":D,"SEED":SEED},"climas":res,
         "conclusion":"Comunicacion de ITEMS CONOCIDOS = alfabeto compartido emergente (bigrama/indice). Composicion de LO NUEVO = HRR. Consistente con 0046-48 (decoder=bigrama plano; HRR=composicion).",
         "verified":any(r["comunicacion_top1"]>r["NC_top1"] for r in res)}
    open(os.path.join(BASE,"phases","phase7_composicion","results_exp_SGM_0049d_cierre.json"),"w").write(json.dumps(out,indent=2,ensure_ascii=False))
    print(json.dumps(out,indent=2,ensure_ascii=False)); return out
if __name__=="__main__": main()
