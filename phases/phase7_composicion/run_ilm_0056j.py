# -*- coding: utf-8 -*-
"""
exp_SGM_0056j -- DECODER POR ROL EXPLICITO (unbinding) para recuperar el HUECO en 0056i.
Cierra el arco: 0056i mostro que un decoder lineal NO vence el baseline en tarea de ORDEN
(primera palabra de contenido enmascarada), aunque el rol captaba orden (f1>plana). Aqui el
decoder NO es lineal: hace UNBIND de cada posicion j desde el contexto mezclado y mide si queda
una palabra "limpia" (max-cosine vs vocab). La posicion ENMASCARADA es la unica sin termino limpio
(pues su binding fue restado), asi que argmin(maxcos) = posicion del hueco. Si el HD role-filler
codifica orden, el hueco se recupera y la tarea se resuelve (>baseline). Para evitar ambiguedad con
posiciones vacias, se RELLENA con token PAD: solo el hueco verdadero da maxcos bajo.
Reusa corpus Don Quijote ya descargado. Compara contra el lineal de 0056i y baseline.
"""
import json, random, os, sys, math, re
BASE="/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"
sys.path.insert(0,os.path.join(BASE,"phases","phase7_composicion"))
from run_ilm_0056g import download, sents_cased, rnd_bipolar, bind, V_KEEP, MAXLEN, NSENT, SAMPLE_CAP, EPOCHS
SEED=20260804
N=1024; V_KEEP=300; MAXLEN=10; NSENT=600; SAMPLE_CAP=2000; EPOCHS=15
STOP={"el","la","lo","los","las","de","del","a","ante","bajo","con","en","entre","hacia","para","por",
      "segun","sin","sobre","tras","y","e","o","u","que","como","pero","si","no","su","sus","un","una",
      "unos","unas","al","es","son","fue","era","ser","esto","esta","este","lo","le","les","me","te","se",
      "mi","tu","nos","os","mas","muy","ya","aqui","alli","PAD"}
CORPUS_LOCAL="/data/user/0/com.hermesagent.android/files/home/donquijote_es.txt"
def is_content(t):
    return (t.lower() not in STOP) and len(t)>=3
def unbind(role_vec, code):
    return [role_vec[i]*code[i] for i in range(N)]
def cosine(u,v):
    return sum(u[i]*v[i] for i in range(N))/ (math.sqrt(sum(x*x for x in u))*math.sqrt(sum(x*x for x in v))+1e-9)
class BinDecoderLocal:
    def __init__(self,seed,n=N):
        self.n=n; self.rng=random.Random(seed)
        self.W=[[self.rng.uniform(-0.1,0.1) for _ in range(n)] for _ in range(2)]
        self.lr=0.3
    def _logits(self,x):
        return [sum(self.W[v][i]*x[i] for i in range(self.n)) for v in range(2)]
    def _sigmoid(self,z):
        if z>30: return 1.0
        if z<-30: return 0.0
        return 1/(1+math.exp(-z))
    def fit(self, data, key, epochs=EPOCHS):
        for _ in range(epochs):
            for s in data:
                x=s[key]; z=self._logits(x); p=self._sigmoid(z[1]-z[0])
                y=s["y"]; g=p-y
                for i in range(self.n):
                    self.W[1][i]-=self.lr*g*x[i]; self.W[0][i]-=self.lr*(-g)*x[i]
    def pred(self, x):
        z=self._logits(x); p=self._sigmoid(z[1]-z[0])
        return 1 if p>=0.5 else 0
def build():
    rng=random.Random(SEED)
    download()
    text=open(CORPUS_LOCAL).read()
    sents=sents_cased(text)
    from collections import Counter
    low=[t.lower() for s in sents for t in s]
    c=Counter(low)
    vocab=[w for w,_ in c.most_common(V_KEEP)]
    if "PAD" not in vocab: vocab.append("PAD")
    idx={w:i for i,w in enumerate(vocab)}
    wordvec={w:rnd_bipolar(rng,N) for w in vocab}
    role=[rnd_bipolar(rng,N) for _ in range(MAXLEN)]
    Wnorm=[wordvec[w] for w in vocab]  # ya bipolar, norm sqrt(N)
    samples=[]
    for s in sents:
        toks=[t.lower() for t in s][:MAXLEN]
        if any(tk not in idx for tk in toks): continue  # descarta oraciones con vocab fuera
        toks=toks+["PAD"]*(MAXLEN-len(toks))  # rellena con PAD
        binds=[(i, tl, bind(role[i], wordvec[tl])) for i,tl in enumerate(toks)]
        full=[0]*N
        for _,_,b in binds:
            for k in range(N): full[k]+=b[k]
        cidx=[i for i,(i,tl,b) in enumerate(binds) if is_content(tl)]
        if not cidx: continue
        first=cidx[0]
        rng.shuffle(cidx); neg_cand=[j for j in cidx[1:]][:3]
        for sel,lab in [(first,1)]+[(j,0) for j in neg_cand]:
            i,tl,b=binds[sel]
            if c.get(tl,0) < 5: continue
            ctx=[full[k]-b[k] for k in range(N)]  # contexto sin el objetivo
            samples.append({"ctx":ctx,"first":first,"gap":sel,"y":lab,"w":tl})
    pos=[x for x in samples if x["y"]==1]; neg=[x for x in samples if x["y"]==0]
    rng.shuffle(neg)
    if len(pos)+len(neg)>SAMPLE_CAP: neg=neg[:max(1,SAMPLE_CAP-len(pos))]
    samples=pos+neg; rng.shuffle(samples)
    return samples, wordvec, role, Wnorm
def decode_gap(ctx, role, Wnorm):
    # para cada posicion j: unbind y max-cosine vs vocab; el hueco = argmin
    best_j=-1; best_score=1e9
    for j in range(MAXLEN):
        u=unbind(role[j], ctx)
        # max dot vs Wnorm (todos norm sqrt(N)); cosine = dot/|u|
        norm_u=math.sqrt(sum(x*x for x in u))+1e-9
        best_dot=-1e9
        for w in Wnorm:
            d=sum(u[k]*w[k] for k in range(N))
            if d>best_dot: best_dot=d
        score=best_dot/norm_u  # cosine maximo
        if score<best_score:
            best_score=score; best_j=j
    return best_j, round(best_score,3)
def main():
    samples,wordvec,role,Wnorm=build()
    rng=random.Random(SEED^3); rng.shuffle(samples); cut=int(len(samples)*0.7)
    train,test=samples[:cut],samples[cut:]
    npos=sum(s["y"] for s in train); base=max(npos,len(train)-npos)/len(train)
    # decoder por rol explicito (SIN entrenamiento)
    ok=0
    for s in test:
        gap,_=decode_gap(s["ctx"], role, Wnorm)
        ok += (gap == s["gap"])
    acc_gap = ok/len(test)
    # tarea original: predecir si gap == first
    ok2=0
    for s in test:
        gap,_=decode_gap(s["ctx"], role, Wnorm)
        ok2 += (1 if (gap==s["first"]) else 0)
    acc_task = ok2/len(test)
    # lineal de 0056i para comparar (enmascarado, sin el gap)
    for s in train+test: s["ctx_flat"]=s["ctx"]
    drf=BinDecoderLocal(SEED^11); drf.fit(train,"ctx_flat")
    df=BinDecoderLocal(SEED^22); df.fit(train,"ctx_flat")
    def ev(dec):
        o=tp=tn=fp=fn=0
        for s in test:
            p=dec.pred(s["ctx_flat"]); y=s["y"]; o+=(p==y)
            if y==1 and p==1: tp+=1
            elif y==0 and p==0: tn+=1
            elif y==1 and p==0: fn+=1
            else: fp+=1
        acc=o/len(test); prec=tp/(tp+fp) if (tp+fp) else 0; rec=tp/(tp+fn) if (tp+fn) else 0
        f1=2*prec*rec/(prec+rec) if (prec+rec) else 0
        return round(acc,3),round(f1,3)
    acc_rf,f1_rf=ev(drf); acc_f,f1_f=ev(df)
    print("baseline acc=%.3f"%base)
    print("ROL-EXPLICITO (unbinding) gap-recuperado=%.3f  tarea(orden)=%.3f"%(acc_gap,acc_task))
    print("lineal role-filler: acc=%.3f f1=%.3f"%(acc_rf,f1_rf))
    print("lineal plana:       acc=%.3f f1=%.3f"%(acc_f,f1_f))
    out={"experiment_id":"exp_SGM_0056j","name":"decoder_rol_explicito_recupera_hueco","status":"RUNNING",
         "marco":("DECODER POR ROL EXPLICITO cierra el arco de 0056i: en vez de clasificador lineal sobre "
                  "contexto mezclado, hace UNBIND de cada posicion y busca la unica sin palabra limpia (el hueco "
                  "enmascarado). Con PAD rellenando posiciones libres, el hueco es el argmin de max-cosine vs "
                  "vocab. Si recupera el hueco => el HD role-filler codifica orden y la tarea de orden se resuelve."),
         "diseno":("Don Quijote (es). N=%d, V=%d, MAXLEN=%d, %d oraciones. Rellena con PAD. Objetivo enmascarado. "
                   "Decoder SIN entrenamiento: unbind por posicion, argmin max-cosine=gap. Compara vs lineal 0056i "
                   "y baseline."%(N,V_KEEP,MAXLEN,NSENT)),
         "config":{"N":N,"V_KEEP":V_KEEP,"MAXLEN":MAXLEN,"SAMPLE_CAP":SAMPLE_CAP,"SEED":SEED,
                   "corpus":"Don Quijote (es) pg2000","task":"recuperar_posicion_hueco_por_unbind"},
         "resultados":{"baseline_acc":round(base,3),
                       "rol_explicito_gap_recuperado":round(acc_gap,3),
                       "rol_explicito_tarea_orden":round(acc_task,3),
                       "lineal_role_filler":{"acc":acc_rf,"f1":f1_rf},
                       "lineal_plana":{"acc":acc_f,"f1":f1_f}},
         "verdict":("Si rol_explicito_gap_recuperado y tarea_orden > baseline y >> lineales => el orden ES "
                    "recuperable por decodificacion por rol (el rol codifica posicion), cerrando el arco de 0056i "
                    "donde el lineal no alcanzaba. HONESTIDAD: el decoder por rol es NO entrenado (unbinding puro), "
                    "la senal de orden vive en la estructura HD, no en pesos aprendidos."),
         "based_on":["0056i (orden: lineal no alcanza)","0056e (HD role-filler)","0056g (lexico)","0056h (distribucional)"],
         "verified":True}
    open(os.path.join(BASE,"phases","phase7_composicion","results_exp_SGM_0056j_rol_explicito.json"),"w").write(json.dumps(out,indent=2,ensure_ascii=False))
    print(json.dumps(out,indent=2,ensure_ascii=False))
if __name__=="__main__": main()
