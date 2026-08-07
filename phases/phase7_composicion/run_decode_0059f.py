# -*- coding: utf-8 -*-
"""
exp_SGM_0059f -- RESONATOR NETWORK CANONICO (Frady 2020, Algorithm 1) sobre FHRR.
Por que 0059e colapsaba: mi resonator casero no usa la matriz de capacidad M_i^{-1} que corrige
la distorsion de la superposicion. El resonator canonico actualiza:
   a_i = M_i^{-1} * unbind( z - suma_{j!=i} bind(V_j, x_j), V_i )
   x_i = clean_i(a_i)   (proyecta al codeword mas cercano del codebook i)
donde M_i = (1/K) sum_c (c * c^*) es la matriz de capacidad del codebook i.
Implementacion: FHRR (vectores complejos e^{i*phi}), binding = producto complejo.
Codebooks por rol (SUJ/ROL/OBJ tienen vocab distinto). Para anidado, el codebook de OBJ incluye
los vectores de los hechos generados (memoria del agente en uso real).
Inversion de M_i (NxN) por Gauss-Jordan en puro Python (N=128 manejable).
"""
import cmath, math, random
N=128
def rnd_vec(rng):
    return [cmath.exp(1j*rng.random()*2*math.pi) for _ in range(N)]
def bind(a,b): return [a[i]*b[i] for i in range(N)]
def unbind(c,r): return [c[i]*r[i].conjugate() for i in range(N)]
def vadd(a,b): return [a[i]+b[i] for i in range(N)]
def vsub(a,b): return [a[i]-b[i] for i in range(N)]
def bundle(vecs): return [sum(v[i] for v in vecs) for i in range(N)]
def sim(a,b):
    na=math.sqrt(sum(abs(x)**2 for x in a)); nb=math.sqrt(sum(abs(x)**2 for x in b))
    if na*nb==0: return 0.0
    re=sum((a[i]*b[i].conjugate()).real for i in range(N))
    return re/(na*nb)
def mat_inv(M):
    # Gauss-Jordan en puro Python, M es lista de N listas (complejas)
    n=len(M)
    A=[list(M[i])+[1.0 if i==j else 0.0 for j in range(n)] for i in range(n)]
    for col in range(n):
        # pivote
        piv=max(range(col,n), key=lambda r: abs(A[r][col]))
        A[col],A[piv]=A[piv],A[col]
        pv=A[col][col]
        A[col]=[x/pv for x in A[col]]
        for r in range(n):
            if r!=col:
                f=A[r][col]
                A[r]=[A[r][k]-f*A[col][k] for k in range(2*n)]
    return [[A[i][n+j] for j in range(n)] for i in range(n)]
def mat_vec(M,v):
    return [sum(M[i][k]*v[k] for k in range(len(v))) for i in range(len(M))]
class ResonatorCanon:
    def __init__(self, seed):
        self.rng=random.Random(seed)
        # vocab por rol
        self.vSUJ=["lobo","zorro","ave","venado"]
        self.vROL=["come","corre","esta_en","persigue"]
        self.vOBJ=["manzana","pasto","rio","arbol"]
        self.sym={}
        for s in self.vSUJ+self.vROL+self.vOBJ:
            if s not in self.sym: self.sym[s]=rnd_vec(self.rng)
        self.role_vecs=[rnd_vec(self.rng) for _ in range(30)]  # V_i por nivel
        self.lvl=rnd_vec(self.rng)
        # codebooks por rol (matrices KxN)
        self.codebooks={
            "SUJ":[self.sym[s] for s in self.vSUJ],
            "ROL":[self.sym[s] for s in self.vROL],
            "OBJ":[self.sym[s] for s in self.vOBJ],
        }
        # matrices de capacidad M_i^{-1}
        self.Minv={}
        for rol,cb in self.codebooks.items():
            K=len(cb)
            M=[[sum(cb[k][i]*cb[k][j].conjugate() for k in range(K)) for j in range(N)] for i in range(N)]
            self.Minv[rol]=mat_inv(M)
    def child_roles(self, level):
        return [self.role_vecs[level], self.role_vecs[level+10], self.role_vecs[level+20]]
    def add_mark(self, fv): return [fv[i]*self.lvl[i] for i in range(N)]
    def encode_fact(self, fact, level=0, mem=None):
        if mem is None: mem={}
        V=self.child_roles(level)
        parts=[]
        for i in range(0,len(fact),2):
            fval=fact[i+1]
            if isinstance(fval,tuple):
                fv,_,mem=self.encode_fact(fval, level+1, mem)
                fv=self.add_mark(fv)
            else:
                fv=self.sym[fval]
            parts.append(bind(V[i//2], fv))
        c=bundle(parts)
        mem[fact]=c
        return c, V, mem
    def cleanup(self, vec, codebook):
        best=None; bd=-2
        for cw in codebook:
            d=sim(vec, cw)
            if d>bd: bd=d; best=cw
        return best, bd
    def decode_level(self, z, V, codebooks, Minv, mem, T=40, level=0):
        if level>6: return {}
        roles=["SUJ","ROL","OBJ"]
        # inicializar x_i con codeword aleatoria del codebook
        x=[list(codebooks[r][self.rng.randrange(len(codebooks[r]))]) for r in roles]
        for _ in range(T):
            for i,r in enumerate(roles):
                # z - suma_{j!=i} bind(V_j, x_j)
                others=vsub(z, bundle([bind(V[j], x[j]) for j in range(3) if j!=i]))
                a=unbind(others, V[i])               # desatar rol i
                a=mat_vec(Minv[r], a)                # corregir por capacidad M_i^{-1}
                cx,bd=self.cleanup(a, codebooks[r])  # proyectar a codebook
                x[i]=list(cx)
        # decode final: para cada rol, ¿símbolo o hecho?
        out={}
        for i,r in enumerate(roles):
            others=vsub(z, bundle([bind(V[j], x[j]) for j in range(3)]))
            a=unbind(others, V[i]); a=mat_vec(Minv[r], a)
            # símbolo del codebook
            cs,bds=self.cleanup(a, codebooks[r])
            sym_name=[k for k,v in self.sym.items() if v==cs]
            sym_name=sym_name[0] if sym_name else "?"
            # hecho de memoria
            best_fact=None; bdf=-2
            for key,vec in mem.items():
                if not isinstance(key,tuple): continue
                d=sim(a, vec)
                if d>bdf: bdf=d; best_fact=key
            if bdf>bds and bdf>0.4:
                out[r]=("FACT", best_fact)
            else:
                out[r]=("SYM", sym_name)
        return out
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
                if tipo=="FACT" and isinstance(val,tuple) and val==gv: ok+=1
        return ok,tot
def make_fact(rng, depth):
    a=rng.choice(["lobo","zorro","ave","venado"]); r=rng.choice(["come","corre","esta_en","persigue"]); b=rng.choice(["manzana","pasto","rio","arbol"])
    if depth<=1: return ("SUJ",a,"ROL",r,"OBJ",b)
    return ("SUJ",a,"ROL",r,"OBJ",make_fact(rng, depth-1))
def main():
    rng=random.Random(99)
    t=ResonatorCanon(7)
    print("=== 0059f RESONATOR CANONICO (Frady 2020, M_i^-1) sobre FHRR ===")
    for depth in [3,4,5,6]:
        ok=0; tot=0; n=4
        for _ in range(n):
            f=make_fact(rng, depth)
            c,V,mem=t.encode_fact(f)
            # codebook de OBJ incluye hechos de memoria para el anidado
            cb=dict(t.codebooks); cb["OBJ"]=t.codebooks["OBJ"]+[mem[k] for k in mem if isinstance(k,tuple)]
            Minv=dict(t.Minv); Minv["OBJ"]=mat_inv([[sum(cb["OBJ"][k][i]*cb["OBJ"][k][j].conjugate() for k in range(len(cb["OBJ"]))) for j in range(N)] for i in range(N)])
            dec=t.decode_level(c, V, cb, Minv, mem, T=30)
            ro,rt=t.fact_accuracy(dec, f); ok+=ro; tot+=rt
        print("prof %d: resonator_canon=%.2f"%(depth, ok/tot))
if __name__=="__main__":
    main()
