# -*- coding: utf-8 -*-
"""
exp_SGM_0059b -- DECODE ANIDADO via TPR-WALK (Plate 2003). Opcion 2.
Diferencia con HRR-plano (0059): NO se suman todas las ataduras en una bolsa.
Cada hecho se codifica como bind(rol, filler) AISLADO; el filler puede ser otro hecho
(enlazado por un "puntero" que baja de nivel). El decoder hace unbind(rol) -> filler,
y si el filler tiene estructura de hecho, RECURRE sobre el sobre el mismo filler.
Como cada nivel esta aislado en su bind, NO hay contaminacion cruzada de la bolsa plana.
Test: profundidad 3,4,5. Si escala (>0.9 en todas), TPR-walk es el camino real.
"""
import math, random
N=128
ROLES=["SUJ","ROL","OBJ"]
VOCAB=["lobo","manzana","pasto","zorro","arbol","piedra","rio","ave","come","corre","esta_en"]
def norm(x):
    m=math.sqrt(sum(v*v for v in x)); return [v/m for v in x] if m>0 else x
def gen_vec(rng):
    return norm([rng.gauss(0,1) for _ in range(N)])
def conv_circ(a,b):
    n=len(a); c=[0.0]*n
    for i in range(n):
        s=0.0
        for k in range(n): s+=a[k]*b[(i-k)%n]
        c[i]=s
    return norm(c)
def bind(a,b): return conv_circ(a,b)
def invert(a):
    n=len(a); return norm([a[(-i)%n] for i in range(n)])
def unbind(c,r): return bind(c, invert(r))
def dot(a,b): return sum(x*y for x,y in zip(a,b))
class TPR:
    def __init__(self,seed):
        self.rng=random.Random(seed)
        self.role={r:gen_vec(self.rng) for r in ROLES}
        self.sym={s:gen_vec(self.rng) for s in VOCAB}
        # "puntero de nivel": vector que marca "esto es un hecho anidado"
        self.lvl=gen_vec(self.rng)
    def encode_fact(self, fact):
        # fact = ("SUJ",a,"ROL",r,"OBJ",b); a,r,b son str O fact anidado
        # NO sumamos: cada rol se ata con su filler y SE SUMA, pero el filler anidado
        # viaja DENTRO de su propio bind ya aislado -> al desatar el rol padre, el filler
        # hijo queda limpio (no mezclado con los otros roles del padre).
        c=[0.0]*N
        for i in range(0,len(fact),2):
            r=fact[i]; fval=fact[i+1]
            fv=self.encode_fact(fval) if isinstance(fval,tuple) else self.sym[fval]
            # marcamos que el filler es un hecho anidado sumando el puntero de nivel
            if isinstance(fval,tuple): fv=norm([fv[k]+0.5*self.lvl[k] for k in range(N)])
            b=bind(self.role[r], fv)
            c=[c[k]+b[k] for k in range(N)]
        return norm(c)
    def decode_walk(self, c, depth=0):
        if depth>8: return {}
        out={}
        for r in ROLES:
            f=unbind(c, self.role[r])
            # es simbolo o hecho anidado? medimos si tiene la marca de nivel
            lvl_dot=dot(f, self.lvl)
            best=None; bd=-1e9
            for s in VOCAB:
                d=dot(f, self.sym[s])
                if d>bd: bd=d; best=s
            if lvl_dot<0.10 and bd>0.10:
                out[r]=("SYM",best)
            else:
                # quitar la marca de nivel para decodificar el hijo limpio
                fclean=norm([f[k]-0.5*self.lvl[k] for k in range(N)])
                sub=self.decode_walk(fclean, depth+1)
                out[r]=("FACT",sub)
        return out
    def fact_accuracy(self, decoded, gt):
        ok=0; tot=0
        gt_map={gt[i]:gt[i+1] for i in range(0,len(gt),2)}
        for r in ROLES:
            tot+=1
            if r not in decoded: continue
            tipo,val=decoded[r]
            gv=gt_map[r]
            if isinstance(gv,str):
                if tipo=="SYM" and val==gv: ok+=1
            else:
                if tipo=="FACT":
                    ro,rt=self.fact_accuracy(val, gv)
                    if ro==rt and rt>0: ok+=1
        return ok,tot
def make_fact(rng, depth):
    a=rng.choice(VOCAB); r=rng.choice(VOCAB); b=rng.choice(VOCAB)
    if depth<=1: return ("SUJ",a,"ROL",r,"OBJ",b)
    return ("SUJ",a,"ROL",r,"OBJ",make_fact(rng, depth-1))
def main():
    rng=random.Random(99)
    t=TPR(7)
    print("=== TPR-walk: decode anidado por profundidad ===")
    for depth in [3,4,5]:
        ok=0; tot=0; n=12
        for _ in range(n):
            f=make_fact(rng, depth)
            c=t.encode_fact(f)
            dec=t.decode_walk(c)
            ro,rt=t.fact_accuracy(dec, f); ok+=ro; tot+=rt
        print("prof %d: tpr_walk=%.2f"%(depth, ok/tot))
if __name__=="__main__":
    main()
