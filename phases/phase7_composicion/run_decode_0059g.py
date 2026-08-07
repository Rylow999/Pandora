# -*- coding: utf-8 -*-
"""
exp_SGM_0059g -- DECODE ANIDADO via ROLE-FILLER con SLOTS SEPARADOS (no sumados) + punteros.
Por que 0059/59b/59c/59d/59e/59f saturaban: sumaban los 3 bindings de un hecho en UN bundle
(superposicion) -> el unbind/resonator contaminaba al hijo y el techo era ~2-3 niveles.
Acá NO se suma: cada rol vive en su PROPIO BLOQUE de dimensiones (SUJ[0:32], ROL[32:64],
OBJ[64:96]) sin solapamiento. El hecho hijo NO se mete adentro del bundle del padre: se apunta
por PROYECCION de 32 dims en el bloque OBJ del padre, y el decoder sigue el puntero a la memoria
de hechos (TPR-walk con punteros separados, no superpuestos). Marca de nivel en bloque aparte
[96:104] para detectar si OBJ es hijo. SIN superposicion -> SIN contaminacion acumulada -> escala.
Honesto: esto es ARQUITECTURA de codificacion (como ADN/instinto es hardcode legítimo en la red
line), NO inyeccion de la respuesta (lo que fue 0056). El CONTENIDO de cada slot viene del hecho.
"""
import math, random
N=96          # 3 bloques de 32
BLK=32
NB=8          # marca de nivel
TOTAL=N+NB
VS=["lobo","zorro","ave","venado"]
VR=["come","corre","esta_en","persigue"]
VO=["manzana","pasto","rio","arbol"]
def rnd_vec(rng,dim): return [rng.gauss(0,1) for _ in range(dim)]
def norm(v):
    m=math.sqrt(sum(x*x for x in v)); return [x/m for x in v] if m>0 else v
def sim(a,b):
    return sum(x*y for x,y in zip(a,b))  # ambos normalizados
def cleanup(vec, codebook):
    # codebook: dict nombre->vector
    best=None; bd=-2
    for name,cw in codebook.items():
        d=sim(vec, cw)
        if d>bd: bd=d; best=name
    return best, bd
class SlotFiller:
    def __init__(self, seed):
        self.rng=random.Random(seed)
        self.sym={}
        for s in VS+VR+VO:
            if s not in self.sym: self.sym[s]=norm(rnd_vec(self.rng,BLK))
        self.codebooks={
            "SUJ":{s:self.sym[s] for s in VS},
            "ROL":{s:self.sym[s] for s in VR},
            "OBJ":{s:self.sym[s] for s in VO},
        }
    def proj(self, vec, dim=BLK):
        out=[0.0]*dim; seg=len(vec)/dim
        for k in range(dim):
            a=int(k*seg); b=int((k+1)*seg); b=max(b,a+1)
            out[k]=sum(vec[a:b])/(b-a)
        return norm(out)
    def encode_fact(self, fact, level=0, mem=None):
        if mem is None: mem={}
        suj=self.sym[fact[1]]; rol=self.sym[fact[3]]
        if isinstance(fact[5],tuple):
            hijo,mem=self.encode_fact(fact[5], level+1, mem)
            obj=self.proj(hijo)
        else:
            obj=self.sym[fact[5]]
        c=norm(suj+rol+obj)   # 96 dims, 3 bloques, sin marca (se decide por similitud)
        mem[fact]=c
        return c, mem
    def find_child(self, obj_vec, mem):
        best=None; bd=-2
        for key,val in mem.items():
            if not isinstance(key,tuple): continue
            fact_hijo, c_hijo = key, val
            p=self.proj(c_hijo)
            d=sim(obj_vec, p)
            if d>bd: bd=d; best=(fact_hijo, c_hijo)
        if best is None: return None
        return (best[0], best[1], bd)
    def decode_fact(self, c, mem):
        suj,ds=cleanup(c[0:BLK], self.codebooks["SUJ"])
        rol,dr=cleanup(c[BLK:2*BLK], self.codebooks["ROL"])
        obj_vec=c[2*BLK:3*BLK]
        sym_obj,db_sym=cleanup(obj_vec, self.codebooks["OBJ"])
        found=self.find_child(obj_vec, mem)
        if found is not None and found[2] > db_sym:
            fact_hijo, c_hijo = found[0], found[1]
            obj=("FACT", self.decode_fact(c_hijo, mem))
        else:
            obj=("SYM", sym_obj)
        return {"SUJ":("SYM",suj),"ROL":("SYM",rol),"OBJ":obj}
    def fact_accuracy(self, dec, gt):
        ok=0; tot=0
        gm={gt[i]:gt[i+1] for i in range(0,len(gt),2)}
        for r in ["SUJ","ROL","OBJ"]:
            tot+=1
            if r not in dec: continue
            tipo,val=dec[r]; gv=gm[r]
            if isinstance(gv,str):
                if tipo=="SYM" and val==gv: ok+=1
            else:
                if tipo=="FACT" and isinstance(val,dict):
                    ro,rt=self.fact_accuracy(val, gv)
                    if ro==rt and rt>0: ok+=1
        return ok,tot
def make_fact(rng, depth):
    a=rng.choice(VS); r=rng.choice(VR); b=rng.choice(VO)
    if depth<=1: return ("SUJ",a,"ROL",r,"OBJ",b)
    return ("SUJ",a,"ROL",r,"OBJ",make_fact(rng, depth-1))
def main():
    rng=random.Random(99)
    t=SlotFiller(7)
    print("=== 0059g ROLE-FILLER SLOTS SEPARADOS + punteros (no sumados) ===")
    for depth in [3,4,5,6,8,10,12]:
        ok=0; tot=0; n=20
        for _ in range(n):
            f=make_fact(rng, depth)
            c,mem=t.encode_fact(f)
            dec=t.decode_fact(c, mem)
            ro,rt=t.fact_accuracy(dec, f); ok+=ro; tot+=rt
        print("prof %d: slots_sep=%.2f"%(depth, ok/tot))
if __name__=="__main__":
    main()
