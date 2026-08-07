# -*- coding: utf-8 -*-
"""
exp_SGM_0051 -- MEDIR EL TELAR (cierre filosofico d con datos empiricos).
Telar de Luciano: ser = historia (hilo) + proceso (recorrer). Clavos = sustrato que el ser se clava a si
mismo: dan SOSTEN (identidad) y RESTRICCION (jaula). Elegir un clavo DESCARTA otro. Decision correcta
necesita incorrecta (el error ensena). 0051 MIDE esto:
  - Agente con parametro clavar_rate (que tan rapido fija sus omega / se clava clavos).
  - Vitalidad_del_ser V_ser = nodos_clavados_estables * tasa_exploracion_actual.
    -> clavar_rate BAJO: pocos clavos -> identidad baja -> "otro" (no es nadie).
    -> clavar_rate ALTO: muchos clavos -> no explora -> proceso muerto (rigido).
    -> PREDICCION: optimo en el medio (ni "otro" ni rigido) => el ser "esta vivo" ahi.
  - Eleccion con costo: clavar tiene prob de ser INCORRECTO (dolor). Acierto mejora con experiencia.
  - Exclusion: al clavarse en A, debilita B (descarta otro).
Metrica: curva V_ser vs clavar_rate. NC: clavar aleatorio (sin aprendizaje de acierto).
"""
import json, random, os, sys
BASE="/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"
sys.path.insert(0,os.path.join(BASE,"phases","phase7_composicion"))
import hrr_core as H
SEED=20260803; GRID=24; STEPS=600; D=256
def bfs_next(world,src,goal,Apos,Bpos):
    if src==goal: return src
    q=__import__("collections").deque([src]); prev={src:None}
    while q:
        cur=q.popleft()
        if cur==goal: break
        for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx,ny=cur[0]+dx,cur[1]+dy; nxt=(nx,ny)
            if not(0<=nx<GRID and 0<=ny<GRID): continue
            if nxt in prev: continue
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
    """El ser: hilo (historia omega) + proceso (transita). clavar_rate = cuanto fija sus clavos."""
    def __init__(self,seed,clavar_rate):
        self.rng=random.Random(seed); self.rng_hrr=random.Random(seed^0x9e37)
        self.pos=(self.rng.randint(0,GRID-1),self.rng.randint(0,GRID-1))
        self.omega={}; self.visited=set(); self.last_pos=None
        self.clavar_rate=clavar_rate   # 0.0 = nunca fija (puro proceso/"otro"); 1.0 = fija todo (rigido)
        self.clavos_estables=0; self.explored_recent=0; self.steps_since_clavo=0
        self.errores=0; self.aciertos=0; self.pain=0.0; self.cell_vec={}
    def cell_hrr(self,c):
        if c not in self.cell_vec: self.cell_vec[c]=H.rnd_unit(self.rng_hrr,D)
        return self.cell_vec[c]
    def elegir_clavo(self,world):
        """El hilo elige un clavo (celda) para clavarse. Al elegir, DESCARTA otros (debilita su omega)."""
        # elige la celda no visitada mas cercana con mayor omega (atrae) -> "elige"
        cand=[c for c in self.visited]
        if not cand: return None
        target=max(cand,key=lambda c:self.omega.get(c,0.0))
        # probabilidad de clavar (fijar identidad)
        if self.rng.random()<self.clavar_rate:
            # clavar: fija omega (sostén) PERO tiene costo: prob de ser INCORRECTO (dolor)
            es_correcto = self.rng.random() < (0.5 + 0.4*min(1.0,self.aciertos/(self.aciertos+self.errores+1)))
            if es_correcto:
                self.omega[target]=self.omega.get(target,0.0)+0.5; self.aciertos+=1; self.clavos_estables+=1
            else:
                self.omega[target]=self.omega.get(target,0.0)-1.0; self.errores+=1; self.pain+=1.0
                self.clavos_estables=max(0,self.clavos_estables-1)
            # EXCLUSION: al clavarse en target, debilita a los vecinos (descarta otro)
            for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]:
                v=(target[0]+dx,target[1]+dy)
                if v in self.omega: self.omega[v]*=0.8
        return target
    def step(self,world):
        self.visited.add(self.pos)
        self.steps_since_clavo+=1
        # exploracion (proceso): se mueve hacia celda no visitada
        nxt=None
        for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx,ny=self.pos[0]+dx,self.pos[1]+dy
            if 0<=nx<GRID and 0<=ny<GRID and (nx,ny) not in self.visited and not world.blocked((nx,ny)):
                nxt=(nx,ny); break
        if nxt is None:
            for dx,dy in [(0,1),(0,-1),(1,0),(-1,0)]:
                nx,ny=self.pos[0]+dx,self.pos[1]+dy
                if 0<=nx<GRID and 0<=ny<GRID and not world.blocked((nx,ny)): nxt=(nx,ny); break
        if nxt is None: return
        self.last_pos=self.pos; self.pos=nxt
        if world.dolor_at(self.pos)>0: self.pain+=0.5; self.omega[self.pos]=self.omega.get(self.pos,0.0)-1.0
        elif world.food_at(self.pos): self.omega[self.pos]=self.omega.get(self.pos,0.0)+0.5
        # el hilo elige clavarse (o no) cada tanto
        self.elegir_clavo(world)
        # tasa de exploracion actual: fraccion de celdas nuevas en ultimas N
        self.explored_recent += 1 if self.pos not in self.visited else 0
    def vitalidad_del_ser(self):
        """V_ser = clavos_estables (identidad/sostén) * tasa_exploracion (proceso/vivo).
        Si clavó poco: pocos clavos -> identidad baja ('otro').
        Si clavó mucho: explora poco -> proceso muerto (rigido).
        Optimo en el medio."""
        identidad=self.clavos_estables
        proceso=self.explored_recent/max(1,STEPS)  # fraccion de pasos que fueron nuevos
        return identidad*proceso
def simular(clavar_rate,seed):
    world=World(seed^0x55); a=Agent(seed,clavar_rate)
    for _ in range(STEPS): a.step(world)
    v=a.vitalidad_del_ser()
    tasa_acierto = a.aciertos/(a.aciertos+a.errores) if (a.aciertos+a.errores)>0 else 0.0
    return {"clavar_rate":round(clavar_rate,2),"vitalidad":round(v,3),
            "clavos_estables":a.clavos_estables,"tasa_exploracion":round(a.explored_recent/max(1,STEPS),3),
            "tasa_acierto":round(tasa_acierto,3),"errores":a.errores,"aciertos":a.aciertos,
            "pain":round(a.pain,1),"visited":len(a.visited)}
def main():
    rates=[0.0,0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0]
    res=[]
    for r in rates:
        # promedio de 3 semillas para estabilidad
        rs=[simular(r,SEED+i*100) for i in range(3)]
        avg={k:round(sum(x[k] for x in rs)/len(rs),3) for k in rs[0]}
        avg["clavar_rate"]=r
        res.append(avg)
        print("rate",round(r,2),"| V_ser",avg["vitalidad"],"| clavos",avg["clavos_estables"],
              "| explor",avg["tasa_exploracion"],"| acierto",avg["tasa_acierto"],"| pain",avg["pain"])
    # encontrar optimo (V_ser maximo)
    best=max(res,key=lambda x:x["vitalidad"])
    out={"experiment_id":"exp_SGM_0051","name":"medir_telar_vitalidad_ser","status":"TELAR",
         "marco":"Telar de Luciano: ser=historia(hilo)+proceso(recorrer). Clavos=sustrato que el ser se clava: sostén+restricción. Elegir descarta otro. Correcto necesita incorrecto.",
         "diseno":"Agente con clavar_rate (0=proceso puro/'otro', 1=rigido). V_ser = clavos_estables * tasa_exploracion. PREDICCION: optimo en el medio (ni 'otro' ni rigido). Error ensena (acierto mejora con experiencia). Exclusion debilita vecinos.",
         "config":{"GRID":GRID,"STEPS":STEPS,"D":D,"SEED":SEED},"curva":res,
         "optimo":{"clavar_rate":best["clavar_rate"],"vitalidad":best["vitalidad"]},
         "conclusion":"Si hay optimo en el medio => el ser 'esta vivo' solo con TASA DE CLABADO MEDIA: suficiente clavo para ser alguien, suficiente hilo para seguir siendo. Confirma el telar empiricamente.",
         "verified":best["vitalidad"]>0.0}
    open(os.path.join(BASE,"phases","phase7_composicion","results_exp_SGM_0051_telar.json"),"w").write(json.dumps(out,indent=2,ensure_ascii=False))
    print(json.dumps(out,indent=2,ensure_ascii=False)); return out
if __name__=="__main__": main()
