# -*- coding: utf-8 -*-
"""
exp_SGM_0059d -- DECODE ANIDADO via RESONATOR NETWORK (Frady et al. 2020) sobre la estructura
de roles independientes por nivel de 0027c.
Diagnostico de 0059/59c: el unbind directo contamina al hijo porque la bolsa tiene 3 bindings
superpuestos (SUJ,ROL,OBJ) y al desatar uno quedan los otros pegados.
Resonator: en vez de unbind una vez, ITERA restando de la bolsa las estimaciones actuales de los
OTROS roles y desatando el rol objetivo, luego clean-up. Busca en superposicion.
Estructura (de 0027c): cada NIVEL de anidamiento usa roles INDEPENDIENTES para que el crosstalk
entre niveles sea bajo. El resonator opera DENTRO de cada nivel para resolver la superposicion.
Honesto (survey 2020/2025): capacidad decrece con nº de factores para D fija. No es magia infinita,
pero corre mejor que unbind directo. Medimos prof 3,4,5,6.
"""
import math, random
N=64
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
    return c  # sin norm: bind conserva magnitud para que la suma de bindings no se aplaste
def bind(a,b): return conv_circ(a,b)  # sin norm (como 0027c: conserva magnitud en la suma)
def invert(a):
    n=len(a); return norm([a[(-i)%n] for i in range(n)])
def unbind(c,r): return bind(c, invert(r))
def vsum(a,b): return norm([a[i]+b[i] for i in range(len(a))])
def dot(a,b): return sum(x*y for x,y in zip(a,b))
class Resonator:
    def __init__(self,seed):
        self.rng=random.Random(seed)
        self.role_levels=[gen_vec(self.rng) for _ in range(30)]  # rol independiente por nivel (0027c), pool grande
        self.sym={s:gen_vec(self.rng) for s in VOCAB}
        self.lvl=gen_vec(self.rng)
    def encode_fact(self, fact, level=0):
        role3=[self.role_levels[level], self.role_levels[level+10], self.role_levels[level+20]]  # roles deterministas por nivel (0027c)
        c=[0.0]*N
        for i in range(0,len(fact),2):
            fval=fact[i+1]
            if isinstance(fval,tuple):
                fv=vsum(self.encode_fact(fval, level+1)[0], [0.5*self.lvl[k] for k in range(N)])
            else:
                fv=self.sym[fval]
            b=bind(role3[i//2], norm(fv))
            c=[c[k]+b[k] for k in range(N)]
        return norm(c), role3
    def child_role3(self, level):
        return [self.role_levels[level], self.role_levels[level+10], self.role_levels[level+20]]
    def decode_level(self, c, role3, T=20, level=0):
        if level>6: return {}
        est=[gen_vec(self.rng) for _ in range(3)]
        for _ in range(T):
            bnd=[bind(role3[k], est[k]) for k in range(3)]
            new=[None,None,None]
            for j in range(3):
                rest=[c[i]-sum(bnd[k][i] for k in range(3) if k!=j) for i in range(N)]
                fj=unbind(rest, role3[j])
                new[j]=norm(fj)   # resonator itera VECTORES (no fuerza a simbolo)
            est=new
        bnd=[bind(role3[k], est[k]) for k in range(3)]
        out={}
        for j,r in enumerate(ROLES):
            rest=[c[i]-sum(bnd[k][i] for k in range(3)) for i in range(N)]
            fj=unbind(rest, role3[j])
            lvl_dot=dot(fj, self.lvl)
            best=None; bd=-1e9
            for s in VOCAB:
                d=dot(fj, self.sym[s])
                if d>bd: bd=d; best=s
            if lvl_dot<0.10 and bd>0.10:
                out[r]=("SYM",best)
            else:
                fclean=norm([fj[k]-0.5*self.lvl[k] for k in range(N)])
                out[r]=("FACT", self.decode_level(fclean, self.child_role3(level+1), level=level+1))
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
    t=Resonator(7)
    print("=== 0059d RESONATOR NETWORK (roles indep por nivel 0027c + resonator) ===")
    for depth in [3]:
        ok=0; tot=0; n=4
        for _ in range(n):
            f=make_fact(rng, depth)
            c,role3=t.encode_fact(f)
            dec=t.decode_level(c, role3, level=0)
            ro,rt=t.fact_accuracy(dec, f); ok+=ro; tot+=rt
        print("prof %d: resonator=%.2f"%(depth, ok/tot))
if __name__=="__main__":
    main()
