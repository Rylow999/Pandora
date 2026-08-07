# -*- coding: utf-8 -*-
"""
exp_SGM_0059c -- TPR-WALK CORRECTO (Plate 2003). El error de 0059b fue re-sumar los roles
del hijo dentro de la bolsa del padre -> contaminacion. ACA el filler hijo viaja como vector
AUTONOMO (ya codificado, sin re-tocar). El padre ata cada rol con su filler y SUMA los 3 binds,
pero el filler hijo YA es un vector final (no se re-procesa). El decoder hace unbind(rol) -> filler
tal cual; si el filler tiene marca de nivel, recurre SOBRE el filler autónomo (no contaminado).
Test: profundidad 3,4,5,6. Si escala (>0.9), TPR-walk correcto es el camino real del decode anidado.
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
def vsum(a,b): return norm([a[k]+b[k] for k in range(len(a))])
class TPR:
    def __init__(self,seed):
        self.rng=random.Random(seed)
        self.role={r:gen_vec(self.rng) for r in ROLES}
        self.sym={s:gen_vec(self.rng) for s in VOCAB}
        self.lvl=gen_vec(self.rng)   # marca de "este filler es un hecho anidado"
    def encode_fact(self, fact):
        # fact = ("SUJ",a,"ROL",r,"OBJ",b); a,r,b son str O fact anidado
        # Cada filler se codifica UNA vez como vector autonomo:
        #   - si es str: sym[s]
        #   - si es tuple (hecho hijo): encode_fact(hijo) YA codificado, mas marca de nivel
        # El padre ata cada rol con su filler y SUMA los 3 binds. El hijo NO se re-procesa.
        c=[0.0]*N
        for i in range(0,len(fact),2):
            r=fact[i]; fval=fact[i+1]
            if isinstance(fval,tuple):
                fvec=vsum(self.encode_fact(fval), [0.5*self.lvl[k] for k in range(N)])
            else:
                fvec=self.sym[fval]
            b=bind(self.role[r], norm(fvec))
            c=[c[k]+b[k] for k in range(N)]
        return norm(c)
    def decode_walk(self, c, depth=0):
        if depth>10: return {}
        out={}
        for r in ROLES:
            f=unbind(c, self.role[r])
            lvl_dot=dot(f, self.lvl)          # marca de nivel => es hecho anidado
            best=None; bd=-1e9
            for s in VOCAB:
                d=dot(f, self.sym[s])
                if d>bd: bd=d; best=s
            if lvl_dot<0.10 and bd>0.10:
                out[r]=("SYM",best)           # simbolo claro
            else:
                # quitar marca de nivel para decodificar el hijo autonomo
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
    print("=== TPR-walk CORRECTO (filler autonomo): decode anidado por profundidad ===")
    for depth in [3,4,5,6]:
        ok=0; tot=0; n=12
        for _ in range(n):
            f=make_fact(rng, depth)
            c=t.encode_fact(f)
            dec=t.decode_walk(c)
            ro,rt=t.fact_accuracy(dec, f); ok+=ro; tot+=rt
        print("prof %d: tpr_walk=%.2f"%(depth, ok/tot))
if __name__=="__main__":
    main()
