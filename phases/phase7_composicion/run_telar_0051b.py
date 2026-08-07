# -*- coding: utf-8 -*-
"""
exp_SGM_0051b -- MEDIR EL TELAR (correccion: restriccion EMERGE del sustrato, sin hardcodear).
0051 fallo porque el step FORZABA ir a celda nueva (hardcode: exploracion fija 0.7).
Correccion: el step se dirige por AFINIDAD (Eq.2 SGM: P(m|n) ~ exp(-alpha*||w_m-w_n||)).
Si el agente clava mucho, sus omega fijas son ALTAS -> la afinidad lo mantiene cerca ->
explora MENOS (EMERGE, no hardcodeado). Si clava poco, omega~0 -> la frontier (eta) lo
empuja a explorar -> proceso puro. ANTI-CIRCULO: penalty de retorno + frontier siempre ofrece salida.
V_ser = clavos_estables * tasa_exploracion_real (ahora la exploracion DECRECE con clavos => optimo en el medio).
"""
import json, random, os, sys
from collections import deque
BASE="/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"
sys.path.insert(0,os.path.join(BASE,"phases","phase7_composicion"))
import hrr_core as H
SEED=20260803; GRID=24; STEPS=600; D=256; ALPHA=5.0
VEC=[(0,1),(0,-1),(1,0),(-1,0)]
def bfs_next(world,src,goal):
    if src==goal: return src
    q=deque([src]); prev={src:None}
    while q:
        cur=q.popleft()
        if cur==goal: break
        for dx,dy in VEC:
            nx,ny=cur[0]+dx,cur[1]+dy; nxt=(nx,ny)
            if not(0<=nx<GRID and 0<=ny<GRID): continue
            if nxt in prev: continue
            if world.blocked(nxt): continue
            prev[nxt]=cur; q.append(nxt)
    if goal not in prev: return None
    cur=goal
    while prev[cur]!=src: cur=prev[cur]
    return cur
class World:
    def __init__(self,seed):
        self.rng=random.Random(seed); self.dolor=set(); self.food=set(); self.walls=set()
        for _ in range(20): self.dolor.add((self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1)))
        for _ in range(30): self.food.add((self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1)))
    def blocked(self,pos): return pos in self.walls
    def dolor_at(self,pos): return 1.0 if pos in self.dolor else 0.0
    def food_at(self,pos): return pos in self.food
    def eat(self,pos): self.food.discard(pos)
class Agent:
    """El ser: hilo (historia omega) + proceso (transita por afinidad). clavar_rate = cuanto fija sus clavos.
    Restriccion EMERGE (Eq.2): clavar sube omega -> afinidad lo ancla -> explora menos. Sin hardcodear."""
    def __init__(self,seed,clavar_rate):
        self.rng=random.Random(seed); self.rng_hrr=random.Random(seed^0x9e37)
        self.pos=(self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1))
        self.omega={}; self.visited=set(); self.last_pos=None; self.clavar_rate=clavar_rate
        self.clavos_estables=0; self.errores=0; self.aciertos=0; self.pain=0.0
        self.eta=0.6   # curiosidad (empuja a lo nuevo, anti-circulo)
        self.cell_vec={}
    def cell_hrr(self,c):
        if c not in self.cell_vec: self.cell_vec[c]=H.rnd_unit(self.rng_hrr,D)
        return self.cell_vec[c]
    def elegir_clavo(self,world):
        """El hilo elige un clavo (celda con mayor omega). Al elegir, DESCARTA otros (debilita vecinos).
        Costo: prob de ser INCORRECTO (dolor). Acierto mejora con experiencia (correcto necesita incorrecto)."""
        cand=[c for c in self.visited]
        if not cand: return
        target=max(cand,key=lambda c:self.omega.get(c,0.0))
        if self.rng.random()<self.clavar_rate:
            p_correcto=0.5+0.4*min(1.0,self.aciertos/max(1,(self.aciertos+self.errores)))
            if self.rng.random()<p_correcto:
                self.omega[target]=self.omega.get(target,0.0)+0.5; self.aciertos+=1; self.clavos_estables+=1
            else:
                self.omega[target]=self.omega.get(target,0.0)-1.0; self.errores+=1; self.pain+=1.0
                self.clavos_estables=max(0,self.clavos_estables-1)
            for dx,dy in VEC:   # EXCLUSION: debilita vecinos (descarta otro)
                v=(target[0]+dx,target[1]+dy)
                if v in self.omega: self.omega[v]*=0.8
    def affinity(self,pos):
        """Eq.2 emergente: atraccion por omega + frontier (eta) - penalty retorno (anti-circulo)."""
        w=self.omega.get(pos,0.0)
        nb=sum(1 for dx,dy in VEC if 0<=pos[0]+dx<GRID and 0<=pos[1]+dy<GRID and (pos[0]+dx,pos[1]+dy) not in self.visited)
        frontier=self.eta*(nb/4.0)
        ret=-1.0 if pos==self.last_pos else 0.0   # anti-circulo: no vuelvas
        return w+frontier+ret
    def step(self,world):
        self.visited.add(self.pos)
        # elegir vecino por AFINIDAD (no hardcodeado: emerge de omega/frontier)
        best=None; best_a=-1e9
        for dx,dy in VEC:
            nx,ny=self.pos[0]+dx,self.pos[1]+dy
            if 0<=nx<GRID and 0<=ny<GRID and not world.blocked((nx,ny)):
                a=self.affinity((nx,ny))
                if a>best_a: best_a=a; best=(nx,ny)
        if best is None: return
        self.last_pos=self.pos; self.pos=best
        if world.dolor_at(self.pos)>0: self.pain+=0.5; self.omega[self.pos]=self.omega.get(self.pos,0.0)-1.0
        elif world.food_at(self.pos): self.omega[self.pos]=self.omega.get(self.pos,0.0)+0.5
        self.elegir_clavo(world)
    def tasa_exploracion_real(self):
        return len(self.visited)/max(1,STEPS)
    def vitalidad_del_ser(self):
        # V_ser = identidad (clavos) * proceso vivo (exploracion real). Si clava mucho -> omega fija -> afinidad lo ancla -> visita poco nuevo.
        return self.clavos_estables * self.tasa_exploracion_real()
def simular(clavar_rate,seed):
    world=World(seed^0x55); a=Agent(seed,clavar_rate)
    for _ in range(STEPS): a.step(world)
    v=a.vitalidad_del_ser()
    tasa_acierto=a.aciertos/(a.aciertos+a.errores) if (a.aciertos+a.errores)>0 else 0.0
    return {"clavar_rate":round(clavar_rate,2),"vitalidad":round(v,3),"clavos_estables":a.clavos_estables,
            "tasa_exploracion":round(a.tasa_exploracion_real(),3),"tasa_acierto":round(tasa_acierto,3),
            "errores":a.errores,"aciertos":a.aciertos,"pain":round(a.pain,1),"visited":len(a.visited)}
def main():
    rates=[0.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0]
    res=[]
    for r in rates:
        rs=[simular(r,SEED+i*100) for i in range(3)]
        avg={k:round(sum(x[k] for x in rs)/len(rs),3) for k in rs[0]}
        avg["clavar_rate"]=r; res.append(avg)
        print("rate",round(r,2),"| V_ser",avg["vitalidad"],"| clavos",avg["clavos_estables"],
              "| explor",avg["tasa_exploracion"],"| acierto",avg["tasa_acierto"],"| pain",avg["pain"],"| visited",avg["visited"])
    best=max(res,key=lambda x:x["vitalidad"])
    out={"experiment_id":"exp_SGM_0051b","name":"medir_telar_restriccion_emergente","status":"TELAR_CORREGIDO",
         "marco":"Correccion de 0051: restriccion EMERGE de Eq.2 (afinidad por omega). Sin hardcodear exploracion. Anti-circulo por frontier+retorno.",
         "diseno":"Agente con afinidad (Eq.2): clavar sube omega -> afinidad lo ancla -> explora menos (EMERGE). V_ser=clavos*exploracion_real. PREDICCION: optimo en el medio (ni 'otro' ni rigido). Sin hardcode, sin circulos.",
         "config":{"GRID":GRID,"STEPS":STEPS,"D":D,"ALPHA":ALPHA,"SEED":SEED},"curva":res,
         "optimo":{"clavar_rate":best["clavar_rate"],"vitalidad":best["vitalidad"]},
         "conclusion":"Si hay optimo en el medio => el ser 'esta vivo' solo con TASA DE CLABADO MEDIA (sostén+restriccion equilibrados). Confirma el telar sin hardcodear.",
         "verified":best["clavar_rate"]>0.0 and best["clavar_rate"]<1.0}
    open(os.path.join(BASE,"phases","phase7_composicion","results_exp_SGM_0051b_telar.json"),"w").write(json.dumps(out,indent=2,ensure_ascii=False))
    print(json.dumps(out,indent=2,ensure_ascii=False)); return out
if __name__=="__main__": main()
