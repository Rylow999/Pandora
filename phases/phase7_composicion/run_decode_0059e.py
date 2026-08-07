# -*- coding: utf-8 -*-
"""
exp_SGM_0059e -- DECODE ANIDADO via RESONATOR NETWORK sobre FHRR (Fourier HRR, Frady 2020).
Por que no cerro 0059d (HRR convolucion circular): la convolucion introduce ruido y el resonator
no converge con N chico. Frady 2020 usa FHRR donde bind = producto complejo (suma de fases EXACTA,
sin ruido). Ahi el resonator converge de verdad.
Implementacion canonica del Resonator (Frady 2020):
  - Vectores = e^{i*phi} (FHRR). bind = producto complejo. unbind = producto por conjugado.
  - Bolsa c = SUMAd e bindings (vectores complejos, NO normalizo: el resonator resta vectores).
  - Iteracion: x_j = cleanup( unbind( c - suma_{k!=j} bind(r_k, x_k), r_j ) ), T iteraciones.
  - Clean-up contra MEMORIA COMPLETA (símbolos + vectores de hechos) -> resuelve el anidado.
Roles independientes por nivel (de 0027c) para que el crosstalk entre niveles sea bajo.
Decodificacion: para cada rol, el filler estimado se limpia contra memoria; si coincide con un
HECHO (marca de nivel) -> se recurre sobre ese hecho; si con un SIMBOLO -> SYM.
Honesto: la memoria de clean-up incluye los vectores de los hechos generados (en uso real seria la
memoria del agente). Medimos si el resonator RESUELVE la factorizacion vectorial a prof 3,4,5,6.
"""
import cmath, math, random
N=100
ROLES=["SUJ","ROL","OBJ"]
VOCAB=["lobo","manzana","pasto","zorro","arbol","piedra","rio","ave","come","corre","esta_en"]
def rnd_vec(rng):
    return [cmath.exp(1j*rng.random()*2*math.pi) for _ in range(N)]
def bind(a,b): return [a[i]*b[i] for i in range(N)]
def unbind(c,r): return [c[i]*r[i].conjugate() for i in range(N)]
def vsum(a,b): return [a[i]+b[i] for i in range(N)]
def vsub(a,b): return [a[i]-b[i] for i in range(N)]
def bundle(vecs): return [sum(v[i] for v in vecs) for i in range(N)]
def sim(a,b):
    # similitud coseno de vectores complejos (angulo)
    na=math.sqrt(sum(abs(x)**2 for x in a)); nb=math.sqrt(sum(abs(x)**2 for x in b))
    if na*nb==0: return 0.0
    re=sum((a[i]*b[i].conjugate()).real for i in range(N))
    return re/(na*nb)
def add_mark(fv, lvl): return [fv[i]*lvl[i] for i in range(N)]  # marca de nivel (producto = suma fase)
class FHRR:
    def __init__(self, seed):
        self.rng=random.Random(seed)
        self.role_levels=[rnd_vec(self.rng) for _ in range(30)]
        self.sym={s:rnd_vec(self.rng) for s in VOCAB}
        self.lvl=rnd_vec(self.rng)
    def child_role3(self, level):
        return [self.role_levels[level], self.role_levels[level+10], self.role_levels[level+20]]
    def encode_fact(self, fact, level=0, mem=None):
        if mem is None: mem={}
        role3=self.child_role3(level)
        parts=[]
        for i in range(0,len(fact),2):
            fval=fact[i+1]
            if isinstance(fval,tuple):
                fv,_,mem=self.encode_fact(fval, level+1, mem)
                fv=add_mark(fv, self.lvl)
            else:
                fv=self.sym[fval]
            parts.append(bind(role3[i//2], fv))
        c=bundle(parts)
        mem[fact]=c   # guardo vector del hecho para clean-up
        return c, role3, mem
    def decode_level(self, c, role3, mem, T=20, level=0):
        if level>6: return {}
        est=[rnd_vec(self.rng) for _ in range(3)]
        for _ in range(T):
            bnd=[bind(role3[k], est[k]) for k in range(3)]
            new=[None,None,None]
            for j in range(3):
                rest=vsub(c, bundle([bnd[k] for k in range(3) if k!=j]))
                fj=unbind(rest, role3[j])
                # clean-up canónico del resonator: proyecta a memoria COMPLETA en cada iteracion
                best=None; bd=-2
                for s in VOCAB:
                    d=sim(fj, self.sym[s])
                    if d>bd: bd=d; best=self.sym[s]
                for key,vec in mem.items():
                    if not isinstance(key,tuple): continue
                    d=sim(fj, vec)
                    if d>bd: bd=d; best=vec
                new[j]=best
            est=new
        out={}
        for j,r in enumerate(ROLES):
            rest=vsub(c, bundle([bind(role3[k], est[k]) for k in range(3)]))
            fj=unbind(rest, role3[j])
            best_sym=None; bd_sym=-2
            for s in VOCAB:
                d=sim(fj, self.sym[s])
                if d>bd_sym: bd_sym=d; best_sym=s
            best_fact=None; bd_fact=-2
            for key,vec in mem.items():
                if not isinstance(key,tuple): continue
                d=sim(fj, vec)
                if d>bd_fact: bd_fact=d; best_fact=key
            if bd_fact>bd_sym and bd_fact>0.3:
                out[r]=("FACT", best_fact)
            else:
                out[r]=("SYM", best_sym)
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
                if tipo=="FACT" and isinstance(val,tuple) and val==gv: ok+=1
        return ok,tot
def make_fact(rng, depth):
    a=rng.choice(VOCAB); r=rng.choice(VOCAB); b=rng.choice(VOCAB)
    if depth<=1: return ("SUJ",a,"ROL",r,"OBJ",b)
    return ("SUJ",a,"ROL",r,"OBJ",make_fact(rng, depth-1))
def main():
    rng=random.Random(99)
    t=FHRR(7)
    print("=== 0059e RESONATOR sobre FHRR (roles indep por nivel 0027c + clean-up memoria completa) ===")
    for depth in [3,4,5,6]:
        ok=0; tot=0; n=8
        for _ in range(n):
            f=make_fact(rng, depth)
            c,role3,mem=t.encode_fact(f)
            dec=t.decode_level(c, role3, mem, T=15)
            ro,rt=t.fact_accuracy(dec, f); ok+=ro; tot+=rt
        print("prof %d: resonator_fhr=%.2f"%(depth, ok/tot))
if __name__=="__main__":
    main()
