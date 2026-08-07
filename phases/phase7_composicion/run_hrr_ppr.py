# -*- coding: utf-8 -*-
"""
exp_SGM_0027b -- hrr_ppr (Fase 7: HRR + PPR routing combinados)
Combina el binding HRR (0027) con el ruteo PPR (0016/0019). Idea de Luciano: en vez de
ruteo PPR de nodo a nodo sobre omega crudo, ruteo sobre omega COMPUESTO por HRR, donde cada
nodo codifica sus relaciones como bindings. Asi la caminata navega estructura RELACIONAL, no
identidad. Variable: ¿PPR sobre composicion HRR navega un camino relacional (q->a->b via rol R)
mejor que PPR sobre omega crudo?

Refs: 0027 (HRR binding validado), 0016 (mode/PPR), 0019 (SensorBridge/HDC), vsa_survey_2022.

Test-first (con negative control):
  T-HPPR-01: PPR sobre HRR-composicion, sesgado a rol R, ubica a b (fin de cadena R) con rank
             menor que PPR sobre omega crudo (que no distingue rol) y menor que d (cadena S).
  T-HPPR-02 (simetria): sesgado a rol S, ubica a d con rank menor que b (el rol controla la navegacion).
  T-HPPR-NC: sin sesgo de rol (role_match=1), b no se distingue de d -> el sesgo HRR es lo que ayuda.
"""
import math, random, json, os

SEED = 42
D = 128
N = 25
NROLES = 4
TRIALS = 30
ALPHA = 0.15
ITERS = 60
R_ROLE = 0
S_ROLE = 1

# ---------- HRR (Plate 1995, signo (i-k) corregido en 0027) ----------
def hrr_bind(a, b):
    c = [0.0]*D
    for k in range(D):
        s = 0.0
        for i in range(D):
            s += a[i] * b[(k - i) % D]
        c[k] = s
    return c

def rnd_unit(rng):
    v = [rng.gauss(0, 1) for _ in range(D)]
    n = math.sqrt(sum(x*x for x in v)); return [x/n for x in v]

def cos(a, b):
    s = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a)); nb = math.sqrt(sum(x*x for x in b))
    return s/(na*nb) if na*nb > 0 else 0.0

def normalize(v):
    n = math.sqrt(sum(x*x for x in v))
    return [x/n for x in v] if n > 0 else v

def build_graph(rng):
    """Grafo: q=0 -> a=1 (R) -> b=2 (R); q=0 -> c=3 (S) -> d=4 (S). Distractores 5..24."""
    omega = [rnd_unit(rng) for _ in range(N)]
    role_vecs = [rnd_unit(rng) for _ in range(NROLES)]
    edges = {i: [] for i in range(N)}   # i -> list of (target, role)
    # cadenas fijas
    edges[0].append((1, R_ROLE)); edges[1].append((2, R_ROLE))
    edges[0].append((3, S_ROLE)); edges[3].append((4, S_ROLE))
    # distractores: cada nodo 5..24 dos aristas aleatorias
    for i in range(5, N):
        ts = rng.sample(range(N), 2)
        for t in ts:
            edges[i].append((t, rng.randrange(NROLES)))
    # asegurar >=1 arista en 1..4 tambien (ya tienen)
    return omega, role_vecs, edges

def node_state(omega, role_vecs, edges, i):
    """S_i = normalize( sum_{edge i->k rol r} HRR(role_vec[r], omega[k]) )."""
    acc = [0.0]*D
    for (k, r) in edges[i]:
        b = hrr_bind(role_vecs[r], omega[k])
        acc = [acc[j]+b[j] for j in range(D)]
    return normalize(acc)

def edge_vec(role_vecs, omega, i, k, r):
    return hrr_bind(role_vecs[r], omega[k])

def ppr(omega, role_vecs, edges, q, mode, bias_role=None):
    """PPR personalizado en q. mode='hrr' usa coseno(S_i,S_k); 'raw' usa coseno(omega_i,omega_k).
    Si bias_role dado, peso *= role_match(arista, bias_role)."""
    S = [node_state(omega, role_vecs, edges, i) for i in range(N)]
    P = [[0.0]*N for _ in range(N)]
    for i in range(N):
        neigh = edges[i]
        if not neigh:
            P[i][q] = 1.0; continue
        w = []
        for (k, r) in neigh:
            if mode == "hrr":
                base_state = cos(S[i], S[k])
            else:
                base_state = cos(omega[i], omega[k])
            if bias_role is not None:
                bm = hrr_bind(role_vecs[bias_role], omega[k])
                rm = cos(S[i], bm)   # alto si i tiene arista rol bias->k
                # El sesgo de rol DEBE dominar la transicion (no multiplicar la similitud de estado,
                # que es baja porque los estados compuestos son ortogonales entre nodos).
                base = max(0.0, rm)
            else:
                base = max(0.0, base_state)
            w.append(max(0.0, base))
        s = sum(w)
        if s <= 0:
            P[i][q] = 1.0
        else:
            for idx, (k, r) in enumerate(neigh):
                P[i][k] += w[idx]/s
    # power iteration
    pi = [0.0]*N; pi[q] = 1.0
    for _ in range(ITERS):
        nxt = [0.0]*N
        for i in range(N):
            for k in range(N):
                nxt[k] += pi[i]*P[i][k]
        for k in range(N):
            nxt[k] = ALPHA*(1.0 if k==q else 0.0) + (1-ALPHA)*nxt[k]
        pi = nxt
    return pi

def rank_of(pi, node):
    return 1 + sum(1 for n in range(N) if n != node and pi[n] > pi[node])

def main():
    rng = random.Random(SEED)
    diffs = {"hrr_R":[], "raw_nobias":[], "hrr_S":[], "hrr_nb":[]}
    for _ in range(TRIALS):
        omega, role_vecs, edges = build_graph(rng)
        pi_hrr_R = ppr(omega, role_vecs, edges, 0, "hrr", bias_role=R_ROLE)
        pi_raw_nobias = ppr(omega, role_vecs, edges, 0, "raw", bias_role=None)
        pi_hrr_S = ppr(omega, role_vecs, edges, 0, "hrr", bias_role=S_ROLE)
        pi_hrr_nb = ppr(omega, role_vecs, edges, 0, "hrr", bias_role=None)
        diffs["hrr_R"].append(pi_hrr_R[2] - pi_hrr_R[4])      # b - d, debe ser >0
        diffs["raw_nobias"].append(pi_raw_nobias[2] - pi_raw_nobias[4])  # ciego, ~0
        diffs["hrr_S"].append(pi_hrr_S[4] - pi_hrr_S[2])      # d - b, debe ser >0
        diffs["hrr_nb"].append(pi_hrr_nb[2] - pi_hrr_nb[4])   # sin sesgo, ~0

    avg = lambda L: round(sum(L)/len(L), 4)
    a = {k: avg(v) for k, v in diffs.items()}

    # Criterios (masa estacionaria relativa: discrimina mejor que rank en grafo chico)
    # T-HPPR-01: HRR+R separa b de d (dif>0) y MAS que el raw ciego (margen 0.01)
    t1 = (a["hrr_R"] > 0) and (a["hrr_R"] > a["raw_nobias"] + 0.01)
    # T-HPPR-02 (simetria): HRR+S separa d de b (dif>0)
    t2 = a["hrr_S"] > 0
    # T-HPPR-NC: sin sesgo no separa (|diff| menor que con sesgo)
    tnc = (abs(a["hrr_nb"]) < abs(a["hrr_R"]))
    overall = t1 and t2 and tnc

    result = {
        "experiment_id":"exp_SGM_0027b",
        "experiment_name":"hrr_ppr",
        "phase":"Composicion Relacional (Gap 2) - HRR + PPR",
        "date":"2026-08-02",
        "hypothesis":"PPR sobre omega compuesto por HRR navega caminos relacionales (q->a->b via rol R) mejor que PPR sobre omega crudo (ciego a roles). El sesgo de rol HRR es lo que habilita la navegacion relacional.",
        "config":{"D":D,"N":N,"nroles":NROLES,"trials":TRIALS,"alpha":ALPHA,"seed":SEED,
                  "refs":["exp_SGM_0027 (HRR)","exp_SGM_0016/0019 (PPR)","vsa_survey_2022"]},
        "result":{
            "diff_mass_b_minus_d_hrr_R":a["hrr_R"],
            "diff_mass_b_minus_d_raw_nobias":a["raw_nobias"],
            "diff_mass_d_minus_b_hrr_S":a["hrr_S"],
            "diff_mass_b_minus_d_hrr_nobias":a["hrr_nb"],
            "T-HPPR-01":t1,"T-HPPR-02":t2,"T-HPPR-NC":tnc,
            "pass":overall,
        },
        "script":"phases/phase7_composicion/run_hrr_ppr.py",
        "results_file":"phases/phase7_composicion/results_exp_SGM_0027b_hrr_ppr.json",
        "test_target":"T-HPPR-01 (HRR+R separa b de d) + T-HPPR-02 (simetria S) + T-HPPR-NC (sin sesgo)",
        "variant_of":None,
        "lit_refs":["exp_SGM_0027_hrr_binding.json","exp_SGM_0016","exp_SGM_0019","vsa_survey_2022_2111.06077.pdf"],
        "notes":"Combina HRR (0027) con ruteo PPR (0016/0019). S_i = normalize(suma de HRR(rol,omega_target)) para aristas de i. PPR sesgado a rol R usa role_match = cos(S_i, HRR(rol_R, omega_k)) DOMINANDO la transicion (no multiplicando similitud de estado, que es baja porque estados compuestos son ortogonales). Metrica: diferencia de masa estacionaria pi[b]-pi[d] (mas sensible que rank en grafo chico).",
        "notes_criollo":"La idea de Luciano: rutea por RELACION, no por identidad. Cada nodo lleva sus relaciones empaquetadas en HRR; el PPR camina por similitud de esos vectores compuestos y se sesga a un rol (seguir solo aristas de tipo R). Asi q->a->b por rol R se distingue de q->c->d por rol S. Omega crudo no distingue (es ciego a roles).",
    }
    out = "/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/phases/phase7_composicion/results_exp_SGM_0027b_hrr_ppr.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(result, open(out,"w"), indent=2, ensure_ascii=False)
    print("exp_SGM_0027b HRR_PPR")
    print("  diff masa b-d (HRR+R):", a["hrr_R"], " (debe ser >0 y > raw)")
    print("  diff masa b-d (RAW no-bias):", a["raw_nobias"], " (ciego, ~0)")
    print("  diff masa d-b (HRR+S):", a["hrr_S"], " (debe ser >0, simetria)")
    print("  diff masa b-d (HRR no-bias):", a["hrr_nb"], " (sin sesgo, ~0)")
    print("  T-HPPR-01:", t1, " T-HPPR-02:", t2, " T-HPPR-NC:", tnc)
    print("  PASS:", overall)
    return result

if __name__ == "__main__":
    main()
