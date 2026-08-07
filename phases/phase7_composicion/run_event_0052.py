# -*- coding: utf-8 -*-
"""
exp_SGM_0052 -- CLAVOS DE EVENTO (idea de Luciano: clavos NO fijos en el espacio = estado/evento, no celda).
0051/0051b clavaban CELDAS (posicion territorial) y la restriccion (clavo=jaula) no emergio. 0052 clava
TIPOS DE EVENTO (comida/veneno/estrella): el omega se fija por EVENTO, no por lugar.
Restriccion ATENCIONAL EMERGE: la afinidad se inclina a celdas donde ocurre el evento clavado -> el
agente repite esos eventos y explora MENOS eventos nuevos. Sin hardcodear "explora menos": emerge de Eq.2.
V_ser = eventos_clavados_estables * tasa_eventos_nuevos. PREDICCION: optimo en el medio (ni 'otro' ni jaula).
Anti-circulo: frontier por eventos no visitados + penalty retorno.
"""
import json, random, os, sys
from collections import deque, defaultdict
BASE="/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"
sys.path.insert(0,os.path.join(BASE,"phases","phase7_composicion"))
import hrr_core as H
SEED=20260803; GRID=24; STEPS=600; D=256; EVENT_TYPES=["food","venom","star"]
def bfs_next(world,src,goal):
    if src==goal: return src
    q=deque([src]); prev={src:None}
    while q:
        cur=q.popleft()
        if cur==goal: break
        for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]:
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
        self.rng=random.Random(seed); self.dolor=set(); self.food=set(); self.stars=set(); self.walls=set()
        for _ in range(20): self.dolor.add((self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1)))
        for _ in range(25): self.food.add((self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1)))
        for _ in range(20): self.stars.add((self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1)))
    def blocked(self,pos): return pos in self.walls
    def event_at(self,pos):
        if pos in self.dolor: return "venom"
        if pos in self.food: return "food"
        if pos in self.stars: return "star"
        return None
    def eat(self,pos): self.food.discard(pos)
class Agent:
    """El ser clava EVENTOS (no celdas). omega por tipo de evento. Restriccion atencional EMERGE de Eq.2."""
    def __init__(self,seed,clavar_rate):
        self.rng=random.Random(seed); self.rng_hrr=random.Random(seed^0x9e37)
        self.pos=(self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1))
        self.omega_event={t:0.0 for t in EVENT_TYPES}  # omega por EVENTO, no por celda
        self.visited=set(); self.last_pos=None; self.clavar_rate=clavar_rate
        self.eventos_clavados=0; self.errores=0; self.aciertos=0; self.pain=0.0
        self.eta=0.6; self.eventos_vistos=set(); self.cell_vec={}
    def cell_hrr(self,c):
        if c not in self.cell_vec: self.cell_vec[c]=H.rnd_unit(self.rng_hrr,D)
        return self.cell_vec[c]
    def elegir_clavo_evento(self,ev):
        """El hilo elige clavarse un EVENTO (fijar su omega). Al elegir, debilita otros eventos (descarta otro)."""
        if ev is None: return
        if self.rng.random()<self.clavar_rate:
            p_correcto=0.5+0.4*min(1.0,self.aciertos/max(1,(self.aciertos+self.errores)))
            if self.rng.random()<p_correcto:
                self.omega_event[ev]=self.omega_event.get(ev,0.0)+0.5; self.aciertos+=1
                if self.omega_event[ev]>1.0 and ev not in [e for e in self.eventos_clavados_list()]: self.eventos_clavados+=1
            else:
                self.omega_event[ev]=self.omega_event.get(ev,0.0)-1.0; self.errores+=1; self.pain+=1.0
                self.eventos_clavados=max(0,self.eventos_clavados-1)
            for t in EVENT_TYPES:   # EXCLUSION: fija un evento, debilita otros
                if t!=ev: self.omega_event[t]*=0.8
    def eventos_clavados_list(self): return [t for t in EVENT_TYPES if self.omega_event[t]>1.0]
    def affinity(self,pos,world):
        """Eq.2 EMERGE: atraccion por evento clavado en esta celda + frontier de eventos no vistos - retorno."""
        ev=world.event_at(pos)
        w=0.0
        if ev is not None: w=self.omega_event.get(ev,0.0)  # el evento clavado atrae (restriccion atencional)
        nb=sum(1 for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]
               if 0<=pos[0]+dx<GRID and 0<=pos[1]+dy<GRID
               and world.event_at((pos[0]+dx,pos[1]+dy)) not in self.eventos_vistos)
        frontier=self.eta*(nb/4.0)  # empuja a ver eventos nuevos
        ret=-1.0 if pos==self.last_pos else 0.0
        return w+frontier+ret
    def step(self,world):
        self.visited.add(self.pos)
        best=None; best_a=-1e9
        for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx,ny=self.pos[0]+dx,self.pos[1]+dy
            if 0<=nx<GRID and 0<=ny<GRID and not world.blocked((nx,ny)):
                a=self.affinity((nx,ny),world)
                if a>best_a: best_a=a; best=(nx,ny)
        if best is None: return
        self.last_pos=self.pos; self.pos=best
        ev=world.event_at(self.pos)
        if ev is not None:
            self.eventos_vistos.add(ev)
            if ev=="venom": self.pain+=0.5; self.omega_event[ev]=self.omega_event.get(ev,0.0)-0.5
            elif ev=="food": self.omega_event[ev]=self.omega_event.get(ev,0.0)+0.3
            elif ev=="star": self.omega_event[ev]=self.omega_event.get(ev,0.0)+0.2
        self.elegir_clavo_evento(ev)
    def tasa_eventos_nuevos(self):
        # proceso vivo = fraccion de pasos donde vio un evento NO visto antes
        return len(self.eventos_vistos)/max(1,len(EVENT_TYPES))  # 0..1, saturado cuando vio los 3
    def vitalidad_del_ser(self):
        # V_ser = eventos clavados (identidad) * tasa de eventos nuevos (proceso vivo)
        # si clava mucho un evento, la afinidad lo repite -> ve menos eventos nuevos -> proceso baja
        eventos_nuevos_real = len([e for e in self.eventos_vistos])  # cuantos tipos vio
        return self.eventos_clavados * eventos_nuevos_real
def simular(clavar_rate,seed):
    world=World(seed^0x55); a=Agent(seed,clavar_rate)
    for _ in range(STEPS): a.step(world)
    v=a.vitalidad_del_ser()
    tasa_acierto=a.aciertos/(a.aciertos+a.errores) if (a.aciertos+a.errores)>0 else 0.0
    eventos_vistos=len(a.eventos_vistos)
    return {"clavar_rate":round(clavar_rate,2),"vitalidad":round(v,3),"eventos_clavados":a.eventos_clavados,
            "eventos_vistos":eventos_vistos,"tasa_eventos_nuevos":round(a.tasa_eventos_nuevos(),3),
            "tasa_acierto":round(tasa_acierto,3),"errores":a.errores,"aciertos":a.aciertos,
            "pain":round(a.pain,1),"omega_eventos":{k:round(v2,2) for k,v2 in a.omega_event.items()}}
def main():
    rates=[0.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0]
    res=[]
    for r in rates:
        rs=[simular(r,SEED+i*100) for i in range(3)]
        avg={k:round(sum(x[k] for x in rs)/len(rs),3) for k in rs[0] if k!="omega_eventos"}
        avg["clavar_rate"]=r; res.append(avg)
        print("rate",round(r,2),"| V_ser",avg["vitalidad"],"| clavados",avg["eventos_clavados"],
              "| vistos",avg["eventos_vistos"],"| acierto",avg["tasa_acierto"],"| pain",avg["pain"])
    best=max(res,key=lambda x:x["vitalidad"])
    out={"experiment_id":"exp_SGM_0052","name":"clavos_de_evento_telar","status":"TELAR_EVENTO",
         "marco":"Idea Luciano: clavos NO fijos en espacio = EVENTO, no celda. Restriccion ATENCIONAL emerge de Eq.2 (omega de evento atrae). Sin hardcodear.",
         "diseno":"Agente clava omega por TIPO de evento (food/venom/star). Afinidad inclina a celdas con evento clavado -> repite esos eventos -> ve menos nuevos (EMERGE). V_ser=eventos_clavados*eventos_vistos. PREDICCION: optimo en el medio (ni 'otro' ni jaula atencional). Anti-circulo por frontier de eventos + retorno.",
         "config":{"GRID":GRID,"STEPS":STEPS,"D":D,"SEED":SEED},"curva":res,
         "optimo":{"clavar_rate":best["clavar_rate"],"vitalidad":best["vitalidad"]},
         "conclusion":"Si optimo en el medio => el ser 'esta vivo' con TASA MEDIA de clavado de eventos: suficiente identidad (eventos fijos) sin perder proceso (ve eventos nuevos). Confirma el telar SIN hardcodear, con clavos de evento (no territoriales).",
         "verified":best["clavar_rate"]>0.0 and best["clavar_rate"]<1.0}
    open(os.path.join(BASE,"phases","phase7_composicion","results_exp_SGM_0052_eventos_telar.json"),"w").write(json.dumps(out,indent=2,ensure_ascii=False))
    print(json.dumps(out,indent=2,ensure_ascii=False)); return out
if __name__=="__main__": main()
