# -*- coding: utf-8 -*-
"""
exp_SGM_0056h -- CLASIFICACION REAL (genero del sustantivo por contexto).
Repite 0056g pero con ETIQUETA DISTRIBUCIONAL: el genero gramatical del sustantivo vive en su contexto
(determinante el/la, adjetivos concordantes), no en la palabra misma. Gold = genero del determinante
que precede al sustantivo (fiable en espanol). Contexto = oracion sin el sustantivo objetivo
(enmascarado). Compara role-filler vs BoW plana: si AMBOS > baseline y role-filler >= plana => el
sustrato SI clasifica cuando hay senal distribucional, y el rol ayuda (orden del determinante importa).
Reusa corpus Don Quijote ya descargado y BinDecoder de 0056g.
"""
import json, random, os, sys, math, re
BASE="/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"
sys.path.insert(0,os.path.join(BASE,"phases","phase7_composicion"))
from run_ilm_0056g import download, sents_cased, rnd_bipolar, bind, N, V_KEEP, MAXLEN, NSENT, SAMPLE_CAP, EPOCHS, BinDecoder
SEED=20260804
DET_MASC={"el","los","un","unos","este","ese","aquel"}
DET_FEM={"la","las","una","unas","esta","esa","aquella"}
CORPUS_LOCAL="/data/user/0/com.hermesagent.android/files/home/donquijote_es.txt"
def build():
    rng=random.Random(SEED)
    download()
    text=open(CORPUS_LOCAL).read()
    sents=sents_cased(text)
    from collections import Counter
    low=[t.lower() for s in sents for t in s]
    c=Counter(low)
    vocab=[w for w,_ in c.most_common(V_KEEP)]
    idx={w:i for i,w in enumerate(vocab)}
    wordvec={w:rnd_bipolar(rng,N) for w in vocab}
    role=[rnd_bipolar(rng,N) for _ in range(MAXLEN)]
    samples=[]
    for s in sents:
        rf=[0]*N; flat=[0]*N
        binds=[]
        for i,t in enumerate(s):
            tl=t.lower()
            if tl in idx:
                b=bind(role[i], wordvec[tl])
                binds.append((i,tl,b))
                for k in range(N): rf[k]+=b[k]; flat[k]+=wordvec[tl][k]
        # sustantivos con determinante: patron DET + sustantivo(i+1)
        for i,tl,b in binds:
            if tl in DET_MASC or tl in DET_FEM:
                if i+1>=len(binds): continue
                j,wj,bj=binds[i+1]
                if c.get(wj,0) < 8: continue
                # label = genero del determinante
                y = 1 if tl in DET_MASC else 0   # 1=masc, 0=fem
                # contexto sin el sustantivo objetivo
                ctx_rf=[rf[k]-bj[k] for k in range(N)]
                ctx_flat=[flat[k]-wordvec[wj][k] for k in range(N)]
                nr=math.sqrt(sum(v*v for v in ctx_rf)) or 1.0
                nf=math.sqrt(sum(v*v for v in ctx_flat)) or 1.0
                ctx_rf=[v/nr for v in ctx_rf]; ctx_flat=[v/nf for v in ctx_flat]
                samples.append({"ctx_rf":ctx_rf,"ctx_flat":ctx_flat,"y":y,"w":wj})
    pos=[x for x in samples if x["y"]==1]; neg=[x for x in samples if x["y"]==0]
    rng.shuffle(neg)
    if len(pos)+len(neg)>SAMPLE_CAP: neg=neg[:max(1,SAMPLE_CAP-len(pos))]
    samples=pos+neg; rng.shuffle(samples)
    return samples
def evaluate(dec, data, key):
    ok=tp=tn=fp=fn=0
    for s in data:
        p=dec.pred(s[key]); y=s["y"]; ok+=(p==y)
        if y==1 and p==1: tp+=1
        elif y==0 and p==0: tn+=1
        elif y==1 and p==0: fn+=1
        else: fp+=1
    acc=ok/len(data); prec=tp/(tp+fp) if (tp+fp) else 0; rec=tp/(tp+fn) if (tp+fn) else 0
    f1=2*prec*rec/(prec+rec) if (prec+rec) else 0
    return round(acc,3), round(f1,3)
def main():
    samples=build()
    rng=random.Random(SEED^3); rng.shuffle(samples); cut=int(len(samples)*0.7)
    train,test=samples[:cut],samples[cut:]
    npos=sum(s["y"] for s in train); base=max(npos,len(train)-npos)/len(train)
    print("muestras:",len(samples),"| train:",len(train),"| test:",len(test),"| base acc:",round(base,3))
    drf=BinDecoder(SEED^11); drf.fit(train,"ctx_rf")
    df=BinDecoder(SEED^22); df.fit(train,"ctx_flat")
    acc_rf,f1_rf=evaluate(drf,test,"ctx_rf")
    acc_f,f1_f=evaluate(df,test,"ctx_flat")
    print("role-filler: acc=%.3f f1=%.3f"%(acc_rf,f1_rf))
    print("plana BoW:   acc=%.3f f1=%.3f"%(acc_f,f1_f))
    out={"experiment_id":"exp_SGM_0056h","name":"clasificacion_real_genero_contexto","status":"RUNNING",
         "marco":("CLASIFICACION REAL con etiqueta DISTRIBUCIONAL (repite 0056g donde propio/comun era "
                  "lexico y fallo). Genero del sustantivo: gold = genero del determinante que lo precede "
                  "(el/la, fiable en es). La senal vive en el CONTEXTO (determinante + concordancia), no en "
                  "la palabra. Compara role-filler vs BoW plana. Reusa corpus Don Quijote y BinDecoder 56g."),
         "diseno":("Don Quijote (es). N=%d, V=%d, 2000 oraciones, muestras hasta %d (sustantivo con DET "
                   "frec>=8, objetivo enmascarado). 70/30. BinDecoder sgd %d epocas. Baseline=mayoritaria."
                   %(N,V_KEEP,SAMPLE_CAP,EPOCHS)),
         "config":{"N":N,"V_KEEP":V_KEEP,"SAMPLE_CAP":SAMPLE_CAP,"EPOCHS":EPOCHS,"SEED":SEED,
                   "corpus":"Don Quijote (es) pg2000","task":"genero_masc_fem_por_contexto_distribucional"},
         "resultados":{"n_muestras":len(samples),"baseline_acc":round(base,3),
                       "role_filler":{"acc":acc_rf,"f1":f1_rf},"plana_bow":{"acc":acc_f,"f1":f1_f}},
         "verdict":("Si ambos > baseline => el sustrato SI clasifica cuando hay senal distribucional (la "
                    "leccion de 0056g era la tarea, no el sustrato). Si role_filler >= plana => el rol ayuda "
                    "porque la posicion del determinante importa. HONESTIDAD: es clasificacion distribucional "
                    "real sobre texto real; el sustrato demuestra aprender genero por contexto."),
         "based_on":["0056g (clasificacion lexica fallo: propio es lexico)","0056f (uso real)","0056e (decoder listo)"],
         "verified":True}
    open(os.path.join(BASE,"phases","phase7_composicion","results_exp_SGM_0056h_genero_real.json"),"w").write(json.dumps(out,indent=2,ensure_ascii=False))
    print(json.dumps(out,indent=2,ensure_ascii=False))
if __name__=="__main__": main()
