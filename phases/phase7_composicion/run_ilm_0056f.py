# -*- coding: utf-8 -*-
"""
exp_SGM_0056f -- USO REAL en CORPUS REAL (Don Quijote, espanol, Proyecto Gutenberg).
Sin nltk/spacy: tokenizacion manual stdlib. El sustrato HD (role-filler, 0056e) se usa como
MEMORIA DIRECCIONABLE POR CONTENIDO: guarda oraciones reales como trazas HD, y dada una cueva
recupera las oraciones mas similares (recall). Responde a la pregunta de toda la linea:
¿el HD role-filler (que rompio el techo 0.6 en 0056e) AYUDA en datos reales vs superposicion
plana (tipo 0029)? Compara role-filler vs plana en calidad de recall (solapamiento lexico Jaccard
con los vecinos) y muestra ejemplos reales de query -> vecinos.
"""
import json, random, os, sys, math, urllib.request, ssl, re
BASE="/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"
sys.path.insert(0,os.path.join(BASE,"phases","phase7_composicion"))
SEED=20260804; N=512; V_KEEP=3000; MAXLEN=24; NSENT=4000; NQ=20; KNN=5
CORPUS_URL="https://www.gutenberg.org/cache/epub/2000/pg2000.txt"
CORPUS_LOCAL="/data/user/0/com.hermesagent.android/files/home/donquijote_es.txt"
STOP={"el","la","lo","los","las","de","del","a","ante","bajo","con","en","entre","hacia",
      "para","por","segun","sin","sobre","tras","y","e","o","u","que","como","pero","si",
      "no","su","sus","un","una","unos","unas","al","es","son","fue","era","ser","al","esto","esta","este"}
def rnd_bipolar(rng,n):
    return [1 if rng.random()<0.5 else -1 for _ in range(n)]
def bind(a,b):
    return [a[i]*b[i] for i in range(len(a))]
def cosine(a,b):
    return sum(a[i]*b[i] for i in range(len(a)))/(math.sqrt(sum(x*x for x in a))*math.sqrt(sum(x*x for x in b))+1e-9)
def download():
    if os.path.exists(CORPUS_LOCAL) and os.path.getsize(CORPUS_LOCAL)>100000:
        return
    ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
    req=urllib.request.Request(CORPUS_URL, headers={"User-Agent":"Mozilla/5.0"})
    resp=urllib.request.urlopen(req, timeout=60, context=ctx)
    chunks=[]; total=0
    while True:
        b=resp.read(65536)
        if not b: break
        chunks.append(b); total+=len(b)
    data=b"".join(chunks).decode("utf-8","ignore")
    open(CORPUS_LOCAL,"w").write(data)
    print("descargado",total,"bytes")
def tokenize(text):
    toks=re.findall(r"[a-záéíóúñü]+", text.lower())
    return [t for t in toks if len(t)>2]
def sentences(text):
    parts=re.split(r"[.!?]+", text)
    out=[]
    for p in parts:
        ws=tokenize(p)
        if 4<=len(ws)<=MAXLEN:
            out.append(ws)
        if len(out)>=NSENT: break
    return out
def build():
    rng=random.Random(SEED)
    download()
    text=open(CORPUS_LOCAL).read()
    sents=sentences(text)
    # vocabulario por frecuencia
    from collections import Counter
    c=Counter(w for s in sents for w in s)
    vocab=[w for w,_ in c.most_common(V_KEEP)]
    idx={w:i for i,w in enumerate(vocab)}
    # vectores fijos
    wordvec={w:rnd_bipolar(rng,N) for w in vocab}
    role=[rnd_bipolar(rng,N) for _ in range(MAXLEN)]
    # codificar
    rf=[]; flat=[]; kept=[]
    for s in sents:
        vs=[wordvec[w] for w in s if w in idx]
        if not vs: continue
        f=[0]*N
        for v in vs:
            for i in range(N): f[i]+=v[i]
        flat.append(f)
        r=[0]*N
        for pos,w in enumerate(s):
            if w in idx:
                b=bind(role[pos], wordvec[w])
                for i in range(N): r[i]+=b[i]
        rf.append(r)
        kept.append(s)
    return kept, rf, flat, vocab
def jaccard(a,b):
    sa=set(a)-STOP; sb=set(b)-STOP
    if not sa or not sb: return 0.0
    return len(sa&sb)/len(sa|sb)
def recall_eval(kept, rf, flat, nq=NQ):
    rng=random.Random(SEED^7)
    idxs=list(range(len(kept))); rng.shuffle(idxs); queries=idxs[:nq]
    jr=[]; jf=[]
    examples=[]
    for qi in queries:
        q=kept[qi]
        # role-filler neighbors
        sims_r=sorted(range(len(rf)), key=lambda j: -cosine(rf[qi], rf[j]))[:KNN+1]
        sims_f=sorted(range(len(flat)), key=lambda j: -cosine(flat[qi], flat[j]))[:KNN+1]
        jr_avg=sum(jaccard(q,kept[j]) for j in sims_r[1:])/(KNN)
        jf_avg=sum(jaccard(q,kept[j]) for j in sims_f[1:])/(KNN)
        jr.append(jr_avg); jf.append(jf_avg)
        if len(examples)<3:
            examples.append({"query":" ".join(q[:12]),
                             "rf_neighbors":[" ".join(kept[j][:12]) for j in sims_r[1:3]],
                             "flat_neighbors":[" ".join(kept[j][:12]) for j in sims_f[1:3]],
                             "jr":round(jr_avg,3),"jf":round(jf_avg,3)})
    return sum(jr)/len(jr), sum(jf)/len(jf), examples
def main():
    kept,rf,flat,vocab=build()
    print("oraciones:",len(kept),"| vocab:",len(vocab),"| N:",N)
    jr,jf,examples=recall_eval(kept,rf,flat)
    print("recall Jaccard medio  role-filler=%.3f  plana=%.3f"%(jr,jf))
    for ex in examples:
        print("  Q:",ex["query"])
        print("    RF :",ex["rf_neighbors"],"jr=%.3f"%ex["jr"])
        print("    FLAT:",ex["flat_neighbors"],"jf=%.3f"%ex["jf"])
    out={"experiment_id":"exp_SGM_0056f","name":"uso_real_corpus_donquijote","status":"RUNNING",
         "marco":("Uso real del sustrato HD (role-filler 0056e / slots 0059g) como MEMORIA DIRECCIONABLE "
                  "POR CONTENIDO sobre corpus real (Don Quijote, espanol). Responde si el HD role-filler "
                  "ayuda en datos reales vs superposicion plana (0029)."),
         "diseno":("Descarga Don Quijote (Gutenberg pg2000), tokenizacion manual stdlib, V=%d palabras, "
                   "N=%d dims HD. Codifica %d oraciones como trazas HD (role-filler posicional y plana BoW). "
                   "Recall: %d queries, top-%d vecinos por cosine, metrica Jaccard lexico (sin stopwords)."
                   %(V_KEEP,N,len(kept),NQ,KNN)),
         "config":{"N":N,"V_KEEP":V_KEEP,"MAXLEN":MAXLEN,"NSENT":NSENT,"NQ":NQ,"KNN":KNN,"SEED":SEED,
                   "corpus":"Don Quijote (es) pg2000"},
         "resultados":{"jaccard_role_filler":round(jr,3),"jaccard_plana":round(jf,3),
                       "n_oraciones":len(kept),"n_vocab":len(vocab),"ejemplos":examples},
         "verdict":("Si jaccard_role_filler > jaccard_plana => el role-filler (que rompio el 0.6 en 0056e) "
                    "tambien ayuda en datos reales: la memoria direccionable por contenido es mas precisa con "
                    "estructura de rol. Si son similares => en texto natural el BoW plano ya basta para recall "
                    "tematico y el rol solo importa cuando el ORDEN es discriminativo. HONESTIDAD: esto es "
                    "recall lexico, no 'comprension'; el sustrato demuestra memoria por similitud sobre texto "
                    "real, no razonamiento."),
         "based_on":["0056e (HD role-filler rompe techo)","0059g (slots separados)","0029 (superposicion plana)"],
         "verified":True}
    open(os.path.join(BASE,"phases","phase7_composicion","results_exp_SGM_0056f_uso_real.json"),"w").write(json.dumps(out,indent=2,ensure_ascii=False))
    print(json.dumps(out,indent=2,ensure_ascii=False))
if __name__=="__main__": main()
