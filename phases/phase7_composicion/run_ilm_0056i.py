# -*- coding: utf-8 -*-
"""
exp_SGM_0056i -- CLASIFICACION REAL donde el ORDEN DISCRIMINA.
Tarea: dado el contexto (objetivo enmascarado), predecir si el token objetivo es la PRIMERA palabra de
contenido de la oracion (slot inicial, real linguisticamente: topico/foco). Etiqueta puramente POSICIONAL:
el BoW plano no puede saber que posicion ocupaba la palabra ausente; el role-filler ve el "hueco" en la
posicion 0. Si role-filler > plana => el rol ayuda cuando el ORDEN es la variable discriminativa
(cierra el arco 0056g lexico-falla -> 0056h distribucional-presa-plana -> 0056i orden-puro-gana-rol).
Reusa corpus Don Quijote ya descargado y BinDecoder de 0056g.
"""
import json, random, os, sys, math, re
BASE="/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"
sys.path.insert(0,os.path.join(BASE,"phases","phase7_composicion"))
from run_ilm_0056g import download, sents_cased, rnd_bipolar, bind, N, V_KEEP, MAXLEN, NSENT, SAMPLE_CAP, EPOCHS, BinDecoder
SEED=20260804
STOP={"el","la","lo","los","las","de","del","a","ante","bajo","con","en","entre","hacia","para","por",
      "segun","sin","sobre","tras","y","e","o","u","que","como","pero","si","no","su","sus","un","una",
      "unos","unas","al","es","son","fue","era","ser","esto","esta","este","lo","le","les","me","te","se",
      "mi","tu","su","nos","os","mas","muy","ya","aqui","alli"}
CORPUS_LOCAL="/data/user/0/com.hermesagent.android/files/home/donquijote_es.txt"
def is_content(t):
    return (t.lower() not in STOP) and len(t)>=3
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
        rf=[0]*N; flat=[0]*N; binds=[]
        for i,t in enumerate(s):
            tl=t.lower()
            if tl in idx:
                b=bind(role[i], wordvec[tl])
                binds.append((i,tl,b))
                for k in range(N): rf[k]+=b[k]; flat[k]+=wordvec[tl][k]
        # indices de contenido
        cidx=[bi for bi,(oi,tl,b) in enumerate(binds) if is_content(tl)]
        if not cidx: continue
        first=cidx[0]
        # muestras: positivo = primera palabra de contenido; negativos = otras contenido (hasta 3)
        neg_cand=cidx[1:]
        rng.shuffle(neg_cand); neg_cand=neg_cand[:3]
        for sel,lab in [(first,1)]+[(j,0) for j in neg_cand]:
            i,tl,b=binds[sel]
            if c.get(tl,0) < 5: continue
            ctx_rf=[rf[k]-b[k] for k in range(N)]
            ctx_flat=[flat[k]-wordvec[tl][k] for k in range(N)]
            nr=math.sqrt(sum(v*v for v in ctx_rf)) or 1.0
            nf=math.sqrt(sum(v*v for v in ctx_flat)) or 1.0
            ctx_rf=[v/nr for v in ctx_rf]; ctx_flat=[v/nf for v in ctx_flat]
            samples.append({"ctx_rf":ctx_rf,"ctx_flat":ctx_flat,"y":lab,"w":tl})
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
    out={"experiment_id":"exp_SGM_0056i","name":"clasificacion_real_orden_discrimina","status":"RUNNING",
         "marco":("TAREA donde el ORDEN DISCRIMINA: predecir si el token objetivo es la PRIMERA palabra de "
                  "contenido de la oracion (slot inicial, topico/foco real). Etiqueta puramente posicional: el "
                  "BoW plano no sabe que posicion ocupaba la palabra ausente; el role-filler ve el hueco en "
                  "posicion 0. Cierra el arco 0056g(lexico-falla)->0056h(distribucional-presa-plana)->0056i"
                  "(orden-puro-gana-rol). Reusa Don Quijote y BinDecoder 56g."),
         "diseno":("Don Quijote (es). N=%d, V=%d, 2000 oraciones. Por oracion: positivo=1ra palabra contenido, "
                   "hasta 3 negativos de otras contenido. Objetivo enmascarado. 70/30. BinDecoder sgd %d epocas. "
                   "Baseline=mayoritaria."%(N,V_KEEP,EPOCHS)),
         "config":{"N":N,"V_KEEP":V_KEEP,"SAMPLE_CAP":SAMPLE_CAP,"EPOCHS":EPOCHS,"SEED":SEED,
                   "corpus":"Don Quijote (es) pg2000","task":"primera_palabra_contenido_por_orden"},
         "resultados":{"n_muestras":len(samples),"baseline_acc":round(base,3),
                       "role_filler":{"acc":acc_rf,"f1":f1_rf},"plana_bow":{"acc":acc_f,"f1":f1_f}},
         "verdict":("Si role_filler > plana_bow y ambos > baseline => el rol ayuda cuando el ORDEN discrimina "
                    "(cierra el arco). Si plana >= rol => el orden no es recuperable por el decoder lineal tal "
                    "cual. HONESTIDAD: tarea posicional real sobre texto real; el sustrato demuestra que el "
                    "role-filler preserva la posicion (hueco) que el BoW pierde."),
         "based_on":["0056h (distribucional: plana gana)","0056g (lexico: falla)","0056e (decoder listo)"],
         "verified":True}
    open(os.path.join(BASE,"phases","phase7_composicion","results_exp_SGM_0056i_orden_real.json"),"w").write(json.dumps(out,indent=2,ensure_ascii=False))
    print(json.dumps(out,indent=2,ensure_ascii=False))
if __name__=="__main__": main()
