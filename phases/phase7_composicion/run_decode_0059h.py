# -*- coding: utf-8 -*-
"""
exp_SGM_0059h -- BARRIDO de BINDINGS POR BLOQUE: mapea la curva profundidad-vs-tamano entre
superposicion pura (K=1: los 3 roles en UN bloque, resonator desata) y slots separados (K=3: cada
rol su bloque, 0059g). K=2 = punto intermedio (SUJ+ROL en un bloque, OBJ aparte). El hijo se apunta
por proyeccion en el bloque que le toca (como 0059g). El resonator canonico (Frady 2020, M_i^-1) se
usa SOLO en los bloques con >1 rol. Esto mapea CUANTA superposicion se puede tolerar antes de que el
decode anidado colapse -> la curva capacidad-vs-superposicion (el aporte de Luciano, 2026-08-04).
"""
import cmath, math, random
def rnd_phase(rng, dim): return [cmath.exp(1j*rng.random()*2*math.pi) for _ in range(dim)]
def bind(a,b): return [a[i]*b[i] for i in range(len(a))]
def unbind(c,r): return [c[i]*r[i].conjugate() for i in range(len(c))]
def vsub(a,b): return [a[i]-b[i] for i in range(len(a))]
def bundle(vecs): return [sum(v[i] for v in vecs) for i in range(len(vecs[0]))]
def sim(a,b):
    na=math.sqrt(sum(abs(x)**2 for x in a)); nb=math.sqrt(sum(abs(x)**2 for x in b))
    if na*nb==0: return 0.0
    return sum((a[i]*b[i].conjugate()).real for i in range(len(a)))/(na*nb)
def mat_inv(M):
    n=len(M)
    A=[list(M[i])+[1.0 if i==j else 0.0 for j in range(n)] for i in range(n)]
    for col in range(n):
        piv=max(range(col,n), key=lambda r: abs(A[r][col]))
        A[col],A[piv]=A[piv],A[col]
        pv=A[col][col]; A[col]=[x/pv for x in A[col]]
        for r in range(n):
            if r!=col:
                f=A[r][col]; A[r]=[A[r][k]-f*A[col][k] for k in range(2*n)]
    return [[A[i][n+j] for j in range(n)] for i in range(n)]
def mat_vec(M,v): return [sum(M[i][k]*v[k] for k in range(len(v))) for i in range(len(M))]
def proj_fhr(vec, dim):
    # proyeccion circular-mean de un VECTOR COMPLEJO (lista de cmath.exp(1j*phase)) a dim fases
    n=len(vec); out=[0j]*dim; seg=n/dim
    for k in range(dim):
        a=int(k*seg); b=int((k+1)*seg); b=max(b,a+1)
        re=sum(v.real for v in vec[a:b])/(b-a)
        im=sum(v.imag for v in vec[a:b])/(b-a)
        ang=cmath.phase(re+1j*im)
        out[k]=cmath.exp(1j*ang)
    return out
VS=["lobo","zorro","ave","venado"]; VR=["come","corre","esta_en","persigue"]; VO=["manzana","pasto","rio","arbol"]
ROLE_NAMES=["SUJ","ROL","OBJ"]
class BlockBundle:
    def __init__(self, seed, K, N):
        self.rng=random.Random(seed); self.K=K; self.N=N; self.BLK=N//K
        # simbolos por rol (vectores de BLK fases)
        self.sym={}
        for s in VS+VR+VO:
            if s not in self.sym: self.sym[s]=rnd_phase(self.rng, self.BLK)
        self.codebooks={
            "SUJ":{s:self.sym[s] for s in VS},
            "ROL":{s:self.sym[s] for s in VR},
            "OBJ":{s:self.sym[s] for s in VO},
        }
        # roles por bloque (calculado inline para dimensionar self.roles correctamente)
        br={}
        for j,rname in enumerate(ROLE_NAMES):
            b=j%self.K; br.setdefault(b,[]).append((j,rname))
        # un vector-rol distinto por rol DENTRO de su bloque (longitud = nroles del bloque)
        self.roles=[[rnd_phase(self.rng, self.BLK) for _ in range(len(br[b]))] for b in range(self.K)]
        self.br=br
        # matrices de capacidad M_i^-1 por BLOQUE (para bloques multi-rol);
        # todos los roles de un bloque comparten el bloque de BLK dims -> una Minv por bloque
        self.Minv=[None]*self.K
        for b in range(self.K):
            nroles=sum(1 for j in range(3) if j%self.K==b)
            if nroles>1:
                cb=[]
                for j in range(3):
                    if j%self.K==b: cb+=list(self.codebooks[ROLE_NAMES[j]].values())
                Mm=[[sum(cb[kk][i]*cb[kk][jj].conjugate() for kk in range(len(cb))) for jj in range(self.BLK)] for i in range(self.BLK)]
                self.Minv[b]=mat_inv(Mm)
    def block_role_assign(self):
        return self.br
    def encode_fact(self, fact, level=0, mem=None):
        if mem is None: mem={}
        BLK=self.BLK; br=self.block_role_assign(); segs=[None]*self.K
        for b, roles in br.items():
            if len(roles)==1:
                j,rname=roles[0]; fval=fact[2*j+1]
                if isinstance(fval,tuple):
                    hijo_vec,_=self.encode_fact(fval, level+1, mem)
                    vec=proj_fhr(hijo_vec, BLK)
                else:
                    vec=self.sym[fval]
                segs[b]=vec
            else:
                parts=[]
                for idx,(j,rname) in enumerate(roles):
                    fval=fact[2*j+1]
                    if isinstance(fval,tuple):
                        hijo_vec,_=self.encode_fact(fval, level+1, mem)
                        fv=proj_fhr(hijo_vec, BLK)
                    else:
                        fv=self.sym[fval]
                    parts.append(bind(self.roles[b][idx], fv))
                segs[b]=bundle(parts)
        c=[]
        for b in range(self.K): c+=segs[b]
        mem[fact]=c
        return c, mem
    def find_child(self, vec, mem):
        best=None; bd=-2
        for key,val in mem.items():
            if not isinstance(key,tuple): continue
            d=sim(vec, proj_fhr(val, len(vec)))
            if d>bd: bd=d; best=(key,val)
        return (best[0], best[1], bd) if best else None
    def cleanup_sym(self, vec, rname):
        best=None; bd=-2
        for name,cw in self.codebooks[rname].items():
            d=sim(vec, cw)
            if d>bd: bd=d; best=name
        return best, bd
    def decode_block_multi(self, seg, b, roles, mem):
        # resonator canonico sobre el bloque para desatar los roles de ese bloque
        T=25; est=[rnd_phase(self.rng, len(seg)) for _ in roles]
        for _ in range(T):
            new=[None]*len(roles)
            for idx,(j,rname) in enumerate(roles):
                others=vsub(seg, bundle([bind(self.roles[b][o], est[o]) for o in range(len(roles)) if o!=idx]))
                fj=unbind(others, self.roles[b][idx])
                Minv=self.Minv[b]
                if Minv is not None: fj=mat_vec(Minv, fj)
                cw,bd=self.cleanup_sym(fj, rname)
                new[idx]=self.sym[cw]
            est=new
        out={}
        for idx,(j,rname) in enumerate(roles):
            fj=est[idx]
            sym_name,sd=self.cleanup_sym(fj, rname)
            found=self.find_child(fj, mem)
            if found and found[2]>sd:
                out[rname]=("FACT", self.decode_fact(found[1], mem, 0))
            else:
                out[rname]=("SYM", sym_name)
        return out
    def decode_block_single(self, seg, j, rname, mem):
        sym_name,sd=self.cleanup_sym(seg, rname)
        found=self.find_child(seg, mem)
        if found and found[2]>sd:
            return ("FACT", self.decode_fact(found[1], mem, 0))
        return ("SYM", sym_name)
    def decode_fact(self, c, mem, level=0):
        BLK=self.BLK; br=self.block_role_assign(); out={}
        for b, roles in br.items():
            seg=c[b*BLK:(b+1)*BLK]
            if len(roles)==1:
                j,rname=roles[0]
                out[rname]=self.decode_block_single(seg, j, rname, mem)
            else:
                out.update(self.decode_block_multi(seg, b, roles, mem))
        return out
    def fact_accuracy(self, dec, gt):
        ok=0; tot=0
        gm={gt[i]:gt[i+1] for i in range(0,len(gt),2)}
        for r in ROLE_NAMES:
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
    print("=== 0059h BARRIDO BINDINGS-POR-BLOQUE (K bloques, N dims) ===")
    print("K\\N |  prof-max alcanzable (acierto>=0.85)")
    for K in [1,2,3]:
        fila="K=%d |"%K
        for N in [64,128,192]:
            t=BlockBundle(7, K, N)
            prof_max=0
            for depth in [2,3,4,5,6,7,8]:
                ok=0; tot=0; n=4
                for _ in range(n):
                    f=make_fact(rng, depth)
                    c,mem=t.encode_fact(f)
                    dec=t.decode_fact(c, mem)
                    ro,rt=t.fact_accuracy(dec, f); ok+=ro; tot+=rt
                acc=ok/tot
                if acc>=0.85: prof_max=depth
                else: break
            fila+=" N=%d:prof%d |"%(N, prof_max)
        print(fila)
if __name__=="__main__":
    main()
