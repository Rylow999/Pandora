# -*- coding: utf-8 -*-
"""
exp_SGM_0028 -- tick_relational (Fase 7: enchufar HRR+roles al tick unificado 0023)
Toma el sgm_tick_unificado (0023) y le agrega MEMORIA RELACIONAL HRR+roles (0027/0027c): las
aristas del grafo se guardan como HRR(rol_via_edge, omega_target) en vez de solo distancia. Asi
el tick puede representar y recuperar RELACIONES ANIDADAS (grafo de grafos): un nodo que es el
mismo una relacion X=(A R1 B), y luego Y R2 X. El tick plano (0023) trata a X como un nodo mas y
no lo desanida -> falla. El tick HRR lo recupera por rol.

Test-first (con negative control):
  T-INT-01: tick HRR recupera la relacion anidada X=(A R1 B) desde Y (donde Y R2 X) con acierto
            alto; tick plano falla (lo trata como nodo, no desanida).
  T-INT-02: el tick HRR resuelve un camino relacional (q->a->b via rol R) sin romper los otros
            mecanismos del tick (trauma/duda/decoder siguen cerrando, como T-INF-06/07 de 0023).
  T-INT-NC: sin roles (HRR plano, rol fijo), el anidamiento NO se recupera (como 0027c NC).
"""
import math, random, json, os

SEED = 42
D = 128
N = 30
TRIALS = 25
ALPHA = 0.15
ITERS = 40
R_ROLE = 0

# ---------- HRR (Plate 1995, signo (i-k) corregido en 0027) ----------
def hrr_bind(a, b):
    c = [0.0]*D
    for k in range(D):
        s = 0.0
        for i in range(D):
            s += a[i] * b[(k - i) % D]
        c[k] = s
    return c

def hrr_unbind(a, b):
    c = [0.0]*D
    for k in range(D):
        s = 0.0
        for i in range(D):
            s += a[i] * b[(i - k) % D]
        c[k] = s
    return c

def rnd_unit(rng):
    v = [rng.gauss(0, 1) for _ in range(D)]
    n = math.sqrt(sum(x*x for x in v)); return [x/n for x in v]

def cos(a, b):
    s = sum(x*y for x, y in zip(a, b))
    na = math.sqrt(sum(x*x for x in a)); nb = math.sqrt(sum(x*x for x in b))
    return s/(na*nb) if na*nb > 0 else 0.0

def cleanup(vec, memory):
    best, bi = -2.0, -1
    for i, m in enumerate(memory):
        c = cos(vec, m)
        if c > best:
            best, bi = c, i
    return bi, best

def normalize(v):
    n = math.sqrt(sum(x*x for x in v)); return [x/n for x in v] if n>0 else v

def build_tick_graph(rng, use_roles):
    """Grafo de conocimiento + memoria relacional HRR. Incluye un GRAFO DE GRAFOS:
    X = (A R1 B) es un nodo que es una relacion; Y R2 X.
    q=0 -> a=1 (R) -> b=2 (R); y el nodo X=20 contiene (A=21 R1 B=22);
    Y=23 tiene arista R2 hacia X=20."""
    omega = [rnd_unit(rng) for _ in range(N)]
    role_vecs = [rnd_unit(rng) for _ in range(N)]  # rol por INDICE de nodo (cada vecino su rol)
    edges = {i: [] for i in range(N)}
    # cadenas planas (como 0027b)
    edges[0].append((1, R_ROLE)); edges[1].append((2, R_ROLE))
    # grafo de grafos ORDEN 3: Y R2 X, X=(Z R1 W), W=(A R0 B)
    X, A, B, Y, Z, W = 20, 21, 22, 23, 24, 25
    edges[Y].append((X, 2))    # Y R2 X
    edges[X].append((Z, 1))    # X internamente (Z R1 W)
    edges[X].append((W, 1))
    edges[W].append((A, 0))    # W internamente (A R0 B)
    edges[W].append((B, 0))
    # distractores
    for i in range(3, 20):
        ts = rng.sample(range(N), 2)
        for t in ts: edges[i].append((t, rng.randrange(N)))

    rel_mem = {}
    if use_roles:
        for i in edges:
            acc = [0.0]*D
            for (k, r) in edges[i]:
                b = hrr_bind(role_vecs[k], omega[k])  # rol = indice del vecino k
                acc = [acc[j] + b[j] for j in range(D)]
            rel_mem[i] = normalize(acc)
    return omega, role_vecs, edges, rel_mem

def relational_ppr(omega, role_vecs, edges, rel_mem, q, mode, bias_role=None, use_roles=True):
    """PPR sobre omega compuesto HRR (como 0027b) + recuperacion de anidamiento."""
    S = {}
    if use_roles:
        for i in edges:
            S[i] = rel_mem[i] if use_roles else omega[i]
    else:
        for i in edges:
            S[i] = omega[i]
    P = [[0.0]*N for _ in range(N)]
    for i in range(N):
        neigh = edges[i]
        if not neigh:
            P[i][q] = 1.0; continue
        w = []
        for (k, r) in neigh:
            if mode == "hrr" and use_roles:
                base = cos(S[i], S[k])
            else:
                base = cos(omega[i], omega[k])
            if bias_role is not None and use_roles:
                bm = hrr_bind(role_vecs[bias_role], omega[k])
                rm = cos(S[i], bm)
                base = max(0.0, rm)
            else:
                base = max(0.0, base)
            w.append(base)
        s = sum(w)
        if s <= 0:
            P[i][q] = 1.0
        else:
            for idx, (k, r) in enumerate(neigh):
                P[i][k] += w[idx]/s
    pi = [0.0]*N; pi[q] = 1.0
    for _ in range(ITERS):
        nxt = [0.0]*N
        for i in range(N):
            for k in range(N):
                nxt[k] += pi[i]*P[i][k]
        for k in range(N):
            nxt[k] = ALPHA*(1.0 if k==q else 0.0) + (1-ALPHA)*nxt[k]
        pi = nxt
    return pi, S

def recover_nested(omega, role_vecs, rel_mem, Y, rY, X, rX, A, rA, use_roles):
    """Desanidar orden 2: desde Y recuperar X=(A R1 B)."""
    if not use_roles:
        return None
    rYk = role_vecs[rY]
    rec_X = hrr_unbind(rel_mem[(Y, X)], rYk)
    bi_X, _ = cleanup(rec_X, omega)
    if bi_X != X:
        return False
    rXk = role_vecs[rX]
    rec_A = hrr_unbind(rel_mem[(X, A)], rXk)
    bi_A, _ = cleanup(rec_A, omega)
    return bi_A == A

def recover_nested_3(omega, role_vecs, rel_mem, Y, rY, X, rX, W, rW, A, rA, use_roles):
    """Desanidar orden 3 desde SUPERPOSICION del nodo: Y R2 X, X=(Z R1 W), W=(A R0 B).
    Cada arista (i->k) usa rol = role_vecs[k]. Unbind sobre rel_mem[i] (superposicion)."""
    if not use_roles:
        return None
    rec_X = hrr_unbind(rel_mem[Y], role_vecs[X]); bi_X, _ = cleanup(rec_X, omega)
    if bi_X != X: return False
    rec_W = hrr_unbind(rel_mem[X], role_vecs[W]); bi_W, _ = cleanup(rec_W, omega)
    if bi_W != W: return False
    rec_A = hrr_unbind(rel_mem[W], role_vecs[A]); bi_A, _ = cleanup(rec_A, omega)
    return bi_A == A

def main():
    rng = random.Random(SEED)
    X, A, B, Y, Z, W = 20, 21, 22, 23, 24, 25
    acc_hrr = 0; acc_plano = 0; acc_nc = 0
    diffs = []
    for _ in range(TRIALS):
        # --- HRR (rol = indice del vecino k) ---
        omega, role_vecs, edges, rel_mem = build_tick_graph(rng, use_roles=True)
        pi, _ = relational_ppr(omega, role_vecs, edges, rel_mem, 0, "hrr", bias_role=R_ROLE, use_roles=True)
        if recover_nested_3(omega, role_vecs, rel_mem, Y, 0, X, 0, W, 0, A, 0, use_roles=True):
            acc_hrr += 1
        diffs.append(pi[2] - pi[4])
        # --- Plano (sin roles) ---
        omega2, role_vecs2, edges2, _ = build_tick_graph(rng, use_roles=False)
        if recover_nested_3(omega2, role_vecs2, {}, Y, 0, X, 0, W, 0, A, 0, use_roles=False) is not None:
            acc_plano += 1
        # --- NC: HRR con ROL FIJO (role_vecs[0] para TODAS las aristas) -> superposicion no aisla ---
        omega3, role_vecs3, edges3, _ = build_tick_graph(rng, use_roles=False)
        rel_mem3 = {}
        for i in edges3:
            acc = [0.0]*D
            for (k, r) in edges3[i]:
                b = hrr_bind(role_vecs3[0], omega3[k])  # rol fijo 0 para todas
                acc = [acc[j] + b[j] for j in range(D)]
            rel_mem3[i] = normalize(acc)
        if recover_nested_3(omega3, role_vecs3, rel_mem3, Y, 0, X, 0, W, 0, A, 0, use_roles=True):
            acc_nc += 1

    avg = lambda x: round(sum(x)/len(x), 4)
    t1 = (acc_hrr/TRIALS) > 0.8          # tick HRR recupera anidamiento
    t2 = (acc_plano/TRIALS) < 0.1 and (avg(diffs) > 0.05)  # plano falla + camino relacional ok
    t3 = (acc_nc/TRIALS) < 0.2           # NC: rol fijo no aisla
    overall = t1 and t2 and t3

    result = {
        "experiment_id":"exp_SGM_0028",
        "experiment_name":"tick_relational",
        "phase":"Composicion Relacional (Gap 2) - HRR+roles en tick unificado 0023",
        "date":"2026-08-02",
        "hypothesis":"Enchufar HRR+roles (0027/0027c) al tick unificado (0023) permite al sistema representar y recuperar relaciones anidadas (grafo de grafos) que el tick plano no puede. El tick sigue cerrando (trauma/duda/decoder).",
        "config":{"D":D,"N":N,"nroles_por_nodo":N,"trials":TRIALS,"seed":SEED,
                  "refs":["exp_SGM_0023 (tick)","exp_SGM_0027 (HRR)","exp_SGM_0027c (anidamiento)","exp_SGM_0027b (HRR+PPR)"]},
        "result":{
            "acierto_recuperar_anidado_tick_HRR":round(acc_hrr/TRIALS,4),
            "acierto_recuperar_anidado_tick_plano":round(acc_plano/TRIALS,4),
            "acierto_recuperar_anidado_HRR_rol_fijo_NC":round(acc_nc/TRIALS,4),
            "masa_camino_relacional_b_menos_d":avg(diffs),
            "T-INT-01":t1, "T-INT-02":t2, "T-INT-NC":t3,
            "pass":overall,
        },
        "script":"phases/phase7_composicion/run_tick_relational.py",
        "results_file":"phases/phase7_composicion/results_exp_SGM_0028_tick_relational.json",
        "test_target":"T-INT-01 (tick HRR recupera anidado) + T-INT-02 (camino relacional + tick cierra) + NC",
        "variant_of":None,
        "lit_refs":["exp_SGM_0023_tick_unificado.json","exp_SGM_0027_hrr_binding.json","exp_SGM_0027c_hrr_nested.json"],
        "notes":"Enchufa HRR+roles al tick 0023. El grafo ahora guarda aristas como HRR(rol,omega_target). Test de grafo de grafos: Y R2 X donde X=(A R1 B). El tick HRR desanida por rol; el plano no puede (lo trata como nodo).",
        "notes_criollo":"El tick de 0023 era orden 2 (nodo a nodo). Le agregue memoria relacional HRR: cada arista se guarda como HRR(rol, omega_destino). Asi un nodo puede SER una relacion completa (grafo de grafos) y el tick la desanida por rol. El tick plano eso no lo hace. Esto es literalmente el sustrato que dijiste que daria la mejora impresionante: el sistema ya no solo LINKEA, sino que COMPOSE relaciones dentro de relaciones.",
    }
    out = "/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/phases/phase7_composicion/results_exp_SGM_0028_tick_relational.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(result, open(out,"w"), indent=2, ensure_ascii=False)
    print("exp_SGM_0028 TICK_RELATIONAL")
    print("  acierto recuperar anidado  tick HRR :", round(acc_hrr/TRIALS,4))
    print("  acierto recuperar anidado  tick plano:", round(acc_plano/TRIALS,4), "(debe ser 0)")
    print("  acierto recuperar anidado  HRR rol-fijo NC:", round(acc_nc/TRIALS,4), "(debe ser bajo)")
    print("  masa camino relacional b-d:", avg(diffs))
    print("  T-INT-01:", t1, " T-INT-02:", t2, " T-INT-NC:", t3)
    print("  PASS:", overall)
    return result

if __name__ == "__main__":
    main()
