# -*- coding: utf-8 -*-
"""
exp_SGM_0059i -- REFINAMIENTO de K=2 (barrido 0059h) con PUNTERO-ROL EXPLICITO.
En 0059h K=2 (bloque SUJ+OBJ, bloque ROL) colapsaba porque el OBJ-hijo era un puntero proyectado
mezclado con el símbolo OBJ: el resonator no lo separaba. Aquí damos al PUNTERO su propio vector-rol
(PTR) DENTRO del mismo bloque fisico -> el bloque 0 tiene 3 vectores-rol (SUJ, OBJ, PTR) en K=2.
Hipotesis honesta: si el puntero tiene "su propia voz" en el bloque, el resonator lo separa del
símbolo OBJ y de SUJ, y K=2 deberia abrir (matizando el hallazgo binario de 0059h: no es la
superposicion per se, es que el puntero necesitaba su rol propio). Tambien subimos T del resonator.
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
class BlockBundlePTR:
    def __init__(self, seed, K, N, T=40):
        self.rng=random.Random(seed); self.K=K; self.N=N; self.BLK=N//K; self.T=T
        self.sym={}
        for s in VS+VR+VO:
            if s not in self.sym: self.sym[s]=rnd_phase(self.rng, self.BLK)
        self.codebooks={
            "SUJ":{s:self.sym[s] for s in VS},
            "ROL":{s:self.sym[s] for s in VR},
            "OBJ":{s:self.sym[s] for s in VO},
        }
        # asignacion de roles a bloques (K=2: SUJ,OBJ -> bloque0 ; ROL -> bloque1)
        br={}
        for j,rname in enumerate(ROLE_NAMES):
            b=j%self.K; br.setdefault(b,[]).append((j,rname))
        # en el bloque que contiene a OBJ, agregamos un rol PTR explicito (puntero al hijo)
        self.br=br
        self.roles=[]
        for b in range(self.K):
            roles_b=list(br[b])
            # si este bloque tiene OBJ, agregar PTR como rol extra
            if any(rname=="OBJ" for _,rname in roles_b):
                roles_b.append((-1,"PTR"))
            self.roles.append([rnd_phase(self.rng, self.BLK) for _ in range(len(roles_b))])
        # matrices de capacidad por bloque multi-rol
        self.Minv=[None]*self.K
        for b in range(self.K):
            nroles=len(self.roles[b])
            if nroles>1:
                cb=[]
                for idx,(j,rname) in enumerate(br[b]):
                    cb+=list(self.codebooks[rname].values())
                # el rol PTR no tiene codebook (es puntero); lo dejamos fuera de la matriz
                Mm=[[sum(cb[kk][i]*cb[kk][jj].conjugate() for kk in range(len(cb))) for jj in range(self.BLK)] for i in range(self.BLK)]
                self.Minv[b]=mat_inv(Mm)
    def encode_fact(self, fact, level=0, mem=None):
        if mem is None: mem={}
        BLK=self.BLK; br=self.br; segs=[None]*self.K
        for b, roles_b in br.items():
            if len(roles_b)==1:
                j,rname=roles_b[0]; fval=fact[2*j+1]
                if isinstance(fval,tuple):
                    hijo_vec,_=self.encode_fact(fval, level+1, mem)
                    segs[b]=proj_fhr(hijo_vec, BLK)
                else:
                    segs[b]=self.sym[fval]
            else:
                # bloque multi-rol: SUJ, OBJ, y PTR (si OBJ es hecho)
                parts=[]
                rol_list=list(roles_b)+([(-1,"PTR")] if any(rn=="OBJ" for _,rn in roles_b) else [])
                for idx,(j,rname) in enumerate(rol_list):
                    if rname=="PTR":
                        # solo lo bindeamos si OBJ es hecho
                        fval=fact[2*2+1]  # OBJ value
                        if isinstance(fval,tuple):
                            hijo_vec,_=self.encode_fact(fval, level+1, mem)
                            ptr=proj_fhr(hijo_vec, BLK)
                            parts.append(bind(self.roles[b][idx], ptr))
                        # si OBJ no es hecho, no bindeamos PTR (queda ausente)
                    else:
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
    def decode_block_multi(self, seg, b, roles_b, mem, depth=0):
        rol_list=list(roles_b)+([(-1,"PTR")] if any(rn=="OBJ" for _,rn in roles_b) else [])
        T=self.T; est=[rnd_phase(self.rng, len(seg)) for _ in rol_list]
        MAXD=12
        for _ in range(T):
            new=[None]*len(rol_list)
            for idx,(j,rname) in enumerate(rol_list):
                others=vsub(seg, bundle([bind(self.roles[b][o], est[o]) for o in range(len(rol_list)) if o!=idx and est[o] is not None]))
                fj=unbind(others, self.roles[b][idx])
                if rname!="PTR" and self.Minv[b] is not None:
                    fj=mat_vec(self.Minv[b], fj)
                if rname=="PTR":
                    found=self.find_child(fj, mem)
                    new[idx]=found[1] if found and found[2]>0.5 else None
                else:
                    cw,bd=self.cleanup_sym(fj, rname)
                    new[idx]=self.sym[cw]
            est=new
        out={}
        ptr_vec=None
        for idx,(j,rname) in enumerate(rol_list):
            if rname=="PTR":
                ptr_vec=est[idx]
            elif rname in ROLE_NAMES:
                fj=est[idx]
                sym_name,sd=self.cleanup_sym(fj, rname)
                found=self.find_child(fj, mem)
                if found and found[2]>sd:
                    out[rname]=("FACT", self.decode_fact(found[1], mem, depth+1)) if depth<MAXD else ("SYM", sym_name)
                else:
                    out[rname]=("SYM", sym_name)
        if ptr_vec is not None:
            found=self.find_child(ptr_vec, mem)
            if found and found[2]>0.5:
                out["OBJ"]=("FACT", self.decode_fact(found[1], mem, depth+1)) if depth<MAXD else ("SYM", sym_name)
        return out
    def decode_block_single(self, seg, j, rname, mem, depth=0):
        sym_name,sd=self.cleanup_sym(seg, rname)
        found=self.find_child(seg, mem)
        MAXD=12
        if found and found[2]>sd:
            return ("FACT", self.decode_fact(found[1], mem, depth+1)) if depth<MAXD else ("SYM", sym_name)
        return ("SYM", sym_name)
    def decode_fact(self, c, mem, depth=0):
        BLK=self.BLK; out={}
        for b, roles_b in self.br.items():
            seg=c[b*BLK:(b+1)*BLK]
            if len(roles_b)==1:
                j,rname=roles_b[0]
                out[rname]=self.decode_block_single(seg, j, rname, mem, depth)
            else:
                out.update(self.decode_block_multi(seg, b, roles_b, mem, depth))
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
def padre_acc(dec, gt):
    ok=0; tot=0
    gm={gt[i]:gt[i+1] for i in range(0,len(gt),2)}
    for r in ROLE_NAMES:
        tot+=1; tipo,val=dec[r]; gv=gm[r]
        if isinstance(gv,str):
            if tipo=="SYM" and val==gv: ok+=1
        else:
            if tipo=="FACT": ok+=1
    return ok,tot
def main():
    import sys; sys.setrecursionlimit(4000)
    rng=random.Random(99)
    print("=== 0059i REFINAMIENTO K=2 con PUNTERO-ROL (T=40) ===")
    print("K\\N | prof-max (todo>=0.85) | prof-max (padre>=0.85)")
    for K in [1,2,3]:
        fila="K=%d |"%K
        for N in [64,128,192]:
            t=BlockBundlePTR(7, K, N, T=40)
            pf=0; pp=0
            for depth in [2,3,4,5,6,7,8]:
                ok=0; tot=0; okp=0; totp=0; n=4
                for _ in range(n):
                    f=make_fact(rng, depth)
                    c,mem=t.encode_fact(f)
                    dec=t.decode_fact(c, mem)
                    ro,rt=t.fact_accuracy(dec, f); ok+=ro; tot+=rt
                    rp,tp=padre_acc(dec, f); okp+=rp; totp+=tp
                acc=ok/tot; accp=okp/totp
                if acc>=0.85: pf=depth
                if accp>=0.85: pp=depth
                else: break
            fila+=" N=%d:todo%d/padre%d |"%(N, pf, pp)
        print(fila)
if __name__=="__main__":
    main()
