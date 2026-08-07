# -*- coding: utf-8 -*-
"""
exp_SGM_0059 -- DECODE ANIDADO (pulido de 0058). Decoder RECURSIVO sobre HRR con convolucion circular.
En 0058 el decode era dot contra bind(rol,candidato) -> tomaba el termino dominante, fallaba en anidado.
Aca: para cada rol, UNBIND (aislar el filler) y luego O matchear contra simbolo, O RECURRIR
si el filler es a su vez un hecho. Mido precision por profundidad (1,2,3) y comparo con el metodo viejo.
HRR: convolucion circular (Plate 1995), inversa = permutacion circular inversa de indices.
"""
import math, random
N=512
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
class HRR:
    def __init__(self,seed):
        self.rng=random.Random(seed)
        self.role={r:gen_vec(self.rng) for r in ROLES}
        self.sym={s:gen_vec(self.rng) for s in VOCAB}
    def encode_flat(self, roles, fillers):
        c=[0.0]*N
        for r,f in zip(roles,fillers):
            fv=self.sym[f] if isinstance(f,str) else f
            b=bind(self.role[r], fv)
            c=[c[i]+b[i] for i in range(N)]
        return norm(c)
    def encode_nested(self, fact):
        # fact = ("SUJ",a, "ROL",r, "OBJ",b) donde a,r,b son str O fact anidado
        c=[0.0]*N
        for i in range(0,len(fact),2):
            r=fact[i]; fval=fact[i+1]
            fv=self.encode_nested(fval) if isinstance(fval,tuple) else self.sym[fval]
            b=bind(self.role[r], fv)
            c=[c[k]+b[k] for k in range(N)]
        return norm(c)
    def decode_flat_old(self, c, roles, fillers_gt):
        # metodo viejo 0058: dot contra bind(rol,candidato)
        ok=0; tot=0
        for r in roles:
            best=None; bd=-1e9
            for s in VOCAB:
                d=dot(c, bind(self.role[r], self.sym[s]))
                if d>bd: bd=d; best=s
            tot+=1
            if best==fillers_gt[r]: ok+=1
        return ok,tot
    def decode_recursive(self, c, depth=0, budget=30):
        if depth>5 or budget<=0: return {}
        out={}; used=budget
        for r in ROLES:
            f=unbind(c, self.role[r])          # aislar filler del rol r
            # cleanup: dot contra todos los simbolos
            dots=sorted(((dot(f,self.sym[s]),s) for s in VOCAB), reverse=True)
            top1,top2=dots[0][0],dots[1][0]
            if top1>0.15 and (top1-top2)>0.05:
                out[r]=("SYM",dots[0][1])      # separacion clara => simbolo
            else:
                sub=self.decode_recursive(f, depth+1, used-1)
                out[r]=("FACT",sub)
        return out
    def fact_accuracy(self, decoded, gt):
        # compara decoded (dict rol->(tipo,val)) con gt (tuple)
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
    h=HRR(7)
    print("=== HRR sanity: unbind recupera filler (plano)? ===")
    for _ in range(5):
        f=["lobo","come","manzana"]
        c=h.encode_flat(["SUJ","ROL","OBJ"],f)
        rec=0
        for r,exp in zip(["SUJ","ROL","OBJ"],f):
            fi=unbind(c,h.role[r])
            best=max(VOCAB,key=lambda s:dot(fi,h.sym[s]))
            if best==exp: rec+=1
        print("  acierto plano:", rec, "/3")
    print("=== decode anidado por profundidad ===")
    for depth in [1,2,3]:
        old_ok=old_tot=0; rec_ok=rec_tot=0; n=10
        for _ in range(n):
            f=make_fact(rng, depth)
            c=h.encode_nested(f)
            gt_map={f[i]:f[i+1] for i in range(0,len(f),2)}
            o,t=h.decode_flat_old(c, ["SUJ","ROL","OBJ"], gt_map); old_ok+=o; old_tot+=t
            dec=h.decode_recursive(c)
            ro,rt=h.fact_accuracy(dec, f); rec_ok+=ro; rec_tot+=rt
        print("prof %d: viejo=%.2f  recursivo=%.2f"%(depth, old_ok/old_tot, rec_ok/rec_tot))
if __name__=="__main__":
    main()