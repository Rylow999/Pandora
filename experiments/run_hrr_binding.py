# -*- coding: utf-8 -*-
"""
exp_SGM_0027 -- hrr_binding (Fase nueva: Composicion Relacional / Binding alternativo)
Aborda el GAP 2 del SGM (literatura index: "Kanerva 1988 + Plate 2003. Adaptar el binding
antes de re-escribir Hebb 3-body"). Hasta ahora SGM usa XOR element-wise (spatter code,
compute_xor_child, Ec.8 spec §2.2) como binding. El problema del ruido en v0.23 (89 relaciones,
extraccion ruidosa) es literalmente el "problema del binding" (VSA survey 2022, p.13).

Hipotesis: HRR (Plate 1995a, circular convolution/correlation, VSA survey Tabla 2 p.10) supera a
XOR en composicion relacional porque el ruido de unbinding decrece ~1/sqrt(D) en vez de crecer
linealmente por dimension. Variable a medir (la "mejor variable" pedida): CAPACIDAD DE
SUPERPOSICION + DEGRADACION POR ANIDAMIENTO, comparando HRR vs XOR en D=128.

Referencias confirmadas en lit/papers/:
  - plate_tensor_product_2003_cs0308022.pdf  (Plate, Tensor Product / HRR)
  - vsa_survey_2022_2111.06077.pdf          (Tabla 2: HRR binding=circular conv, unbinding=circular corr)

Test-first (con negative control):
  T-REL-01 (anidamiento profundo): R = bind(A1, bind(A2, ... bind(Ad-1,Ad)...)); recuperar Ad por
    unbinding en cadena; medir coseno(recuperado, Ad) vs profundidad d={2,3,4,5}. HRR degrada MENOS.
  T-REL-02 (superposicion): S = sum_i bind(Xi,Yi) (k relaciones en un vector); recuperar cada Yi por
    unbind(Xi) + clean-up (max coseno en item memory); tasa acierto vs k={2,4,8,16}. HRR soporta mas.
  T-REL-03 (negative control): vectores aleatorios no-relacionados -> similaridad baja (senal no es ruido).
"""
import math, random, json, os

SEED = 42
D = 128
M = 200          # item memory (vectores base)
DEPTHS = [2, 3, 4, 5]
KSUPER = [2, 4, 8, 16]

# ---------- HRR (Plate 1995, VSA survey Tabla 2) ----------
def hrr_bind(a, b):
    """Circular convolution (a ⋆ b)[k] = sum_i a[i] * b[(k-i) mod D]."""
    c = [0.0]*D
    for k in range(D):
        s = 0.0
        for i in range(D):
            s += a[i] * b[(k - i) % D]
        c[k] = s
    return c

def hrr_unbind(a, b):
    """Circular correlation (a ⋆ b)[k] = sum_i a[i] * b[(i-k) mod D]. unbind(a⋆b, a) ~ b
    (Plate 1995 / VSA survey Tabla 2). El signo (i-k) es critico: con (i+k) no es inverso."""
    c = [0.0]*D
    for k in range(D):
        s = 0.0
        for i in range(D):
            s += a[i] * b[(i - k) % D]
        c[k] = s
    return c

# ---------- XOR / spatter code (SGM actual, Ec.8) ----------
def to_bin(v):
    return [1.0 if x >= 0 else -1.0 for x in v]

def xor_bind(a, b):
    """Spatter code: elementwise XOR sobre version binaria (signo)."""
    aa, bb = to_bin(a), to_bin(b)
    return [1.0 if aa[i] == bb[i] else -1.0 for i in range(D)]

def xor_unbind(a, b):
    return xor_bind(a, b)   # XOR es self-inverse (VSA survey p.8)

# ---------- util ----------
def rnd_unit(rng):
    v = [rng.gauss(0, 1) for _ in range(D)]
    n = math.sqrt(sum(x*x for x in v))
    return [x/n for x in v]

def cos(a, b):
    s = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a)); nb = math.sqrt(sum(x*x for x in b))
    return s/(na*nb) if na*nb > 0 else 0.0

def cleanup(vec, memory):
    """Devuelve el indice de mayor coseno en item memory (clean-up, VSA survey p.10)."""
    best, bi = -2.0, -1
    for i, m in enumerate(memory):
        c = cos(vec, m)
        if c > best:
            best, bi = c, i
    return bi, best

def main():
    rng = random.Random(SEED)
    # item memory: M vectores unitarios (HVs de Plate)
    mem = [rnd_unit(rng) for _ in range(M)]
    mem_bin = [to_bin(m) for m in mem]   # para XOR

    # ---- T-REL-01: anidamiento ----
    res_depth = {}
    for op in ["hrr", "xor"]:
        rows = []
        for d in DEPTHS:
            sims = []
            for _ in range(20):
                idxs = [rng.randrange(M) for _ in range(d)]
                # construir R anidado
                if op == "hrr":
                    R = list(mem[idxs[0]])
                    for j in range(1, d):
                        R = hrr_bind(R, mem[idxs[j]])
                    # recuperar el ultimo por unbinding en cadena CON clean-up en cada paso
                    rec = list(R)
                    for j in range(d-1, 0, -1):
                        rec = hrr_unbind(rec, mem[idxs[j]])
                        bi, _ = cleanup(rec, mem)
                        rec = list(mem[bi])   # CLEAN-UP: reemplazar por item mas similar
                    sims.append(cos(rec, mem[idxs[-1]]))
                else:
                    R = list(mem_bin[idxs[0]])
                    for j in range(1, d):
                        R = xor_bind(R, mem_bin[idxs[j]])
                    rec = list(R)
                    for j in range(d-1, 0, -1):
                        rec = xor_unbind(rec, mem_bin[idxs[j]])
                        bi, _ = cleanup(rec, mem_bin)
                        rec = list(mem_bin[bi])
                    sims.append(cos(rec, mem_bin[idxs[-1]]))
            rows.append(round(sum(sims)/len(sims), 4))
        res_depth[op] = rows

    # ---- T-REL-02: superposicion ----
    res_super = {}
    for op in ["hrr", "xor"]:
        rows = []
        for k in KSUPER:
            acc = 0; tot = 0
            for _ in range(15):
                idxs = rng.sample(range(M), 2*k)   # k pares distintos
                pairs = [(idxs[2*i], idxs[2*i+1]) for i in range(k)]
                if op == "hrr":
                    S = [0.0]*D
                    for (x, y) in pairs:
                        b = hrr_bind(mem[x], mem[y])
                        S = [S[i]+b[i] for i in range(D)]
                    # recuperar cada Yi
                    for (x, y) in pairs:
                        rec = hrr_unbind(S, mem[x])
                        bi, _ = cleanup(rec, mem)
                        if bi == y: acc += 1
                        tot += 1
                else:
                    S = [0.0]*D
                    for (x, y) in pairs:
                        b = xor_bind(mem_bin[x], mem_bin[y])
                        S = [S[i]+b[i] for i in range(D)]
                    for (x, y) in pairs:
                        # XOR unbind honesto: sign(S) antes de XOR (S es suma de ±1, no ±1 puro)
                        Ss = [1.0 if v >= 0 else -1.0 for v in S]
                        rec = xor_unbind(Ss, mem_bin[x])
                        bi, _ = cleanup(rec, mem_bin)
                        if bi == y: acc += 1
                        tot += 1
            rows.append(round(acc/tot, 4))
        res_super[op] = rows

    # ---- T-REL-03: negative control (vectores aleatorios) ----
    nc_hrr = cos(rnd_unit(rng), rnd_unit(rng))
    nc_xor = cos(to_bin(rnd_unit(rng)), to_bin(rnd_unit(rng)))

    # ---- Criterios ----
    # T-REL-01: HRR degrada menos que XOR a profundidad 5
    hrr_d5 = res_depth["hrr"][-1]; xor_d5 = res_depth["xor"][-1]
    t1 = hrr_d5 > xor_d5
    # T-REL-02: HRR soporta mas superposicion a k=16
    hrr_k16 = res_super["hrr"][-1]; xor_k16 = res_super["xor"][-1]
    t2 = hrr_k16 > xor_k16
    # T-REL-03: negative control bajo (senal no es ruido)
    t3 = (nc_hrr < 0.3) and (nc_xor < 0.3)

    overall = t1 and t2 and t3
    result = {
        "experiment_id":"exp_SGM_0027",
        "experiment_name":"hrr_binding",
        "phase":"Composicion Relacional (Gap 2 binding) - HRR vs XOR",
        "date":"2026-08-02",
        "hypothesis":"HRR (circular conv/corr, Plate 1995) supera XOR en composicion relacional: degrada menos por anidamiento y soporta mas superposicion en D=128.",
        "config":{"D":D,"M":M,"depths":DEPTHS,"ksuper":KSUPER,"seed":SEED,
                  "refs":["Plate 1995a HRR","vsa_survey_2022 Tabla 2","SGM spec Ec.8 XOR"]},
        "result":{
            "T-REL-01_anidamiento":{"hrr":res_depth["hrr"],"xor":res_depth["xor"],
                "profundidades":DEPTHS,"pass":t1},
            "T-REL-02_superposicion":{"hrr":res_super["hrr"],"xor":res_super["xor"],
                "k":KSUPER,"pass":t2},
            "T-REL-03_negative_control":{"hrr_rand":round(nc_hrr,4),"xor_rand":round(nc_xor,4),"pass":t3},
            "pass":overall,
        },
        "script":"phases/phase7_composicion/run_hrr_binding.py",
        "results_file":"phases/phase7_composicion/results_exp_SGM_0027_hrr_binding.json",
        "test_target":"T-REL-01 (anidamiento) + T-REL-02 (superposicion) + T-REL-03 (NC)",
        "variant_of":None,
        "lit_refs":["plate_tensor_product_2003_cs0308022.pdf","vsa_survey_2022_2111.06077.pdf",
                    "SGM_v1_4_Especificacion_Corregida.md (Ec.8 XOR)"],
        "notes":"PRIMER ataque al Gap 2 (binding) con operador alternativo a XOR. HRR usa circular convolution (bind) / circular correlation (unbind) y requiere clean-up memory (VSA survey p.10). Variable medida: capacidad de superposicion + degradacion por anidamiento. Siguiente paso (0027-b) propuesto: combinar HRR con ruteo PPR (0016/0019).",
        "notes_criollo":"El XOR (spatter code actual de SGM) acumula ruido lineal por dimension cuando anidas/superpones relaciones; por eso v0.23 se inundaba de ruido con 89 relaciones. HRR (Plate 1995) usa convolution circular y el ruido de unbinding baja como 1/raiz(D). Lo medimos: a igual D=128, HRR tiene que degradar menos al anidar y aguantar mas relaciones superpuestas. Si pasa, el proximo paso es meter HRR en el ruteo PPR para navegar relaciones compuestas.",
    }
    out = "/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/phases/phase7_composicion/results_exp_SGM_0027_hrr_binding.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(result, open(out,"w"), indent=2, ensure_ascii=False)
    print("exp_SGM_0027 HRR_BINDING")
    print("  T-REL-01 anidamiento  d=%s" % DEPTHS)
    print("     HRR:", res_depth["hrr"])
    print("     XOR:", res_depth["xor"], "pass=", t1)
    print("  T-REL-02 superposicion k=%s" % KSUPER)
    print("     HRR:", res_super["hrr"])
    print("     XOR:", res_super["xor"], "pass=", t2)
    print("  T-REL-03 NC  hrr_rand=%.3f xor_rand=%.3f  pass=%s" % (nc_hrr, nc_xor, t3))
    print("  PASS:", overall)
    return result

if __name__ == "__main__":
    main()
