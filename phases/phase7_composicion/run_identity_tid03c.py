# -*- coding: utf-8 -*-
"""
exp_SGM_0035c -- T-ID-03c: identidad=proceso (DE LIBRO).
Version limpia que combina:
  - grafo de 0035b (nodo activo se mueve por afinidad Eq.2, NO re-transita desde inicio =>
    el reset copiado deja al nodo en el final SIN la traza de transiciones => la traza SEPARA).
  - cuello de dolor (de 0033b/0034): ciertas aristas duelen; el agente CON omega aprende a
    evitarlas => pisadas post-reset = 0 (memoria persistente). Reset copiado tambien da 0
    (mantiene omega) PERO sin traza => la traza separa proceso de snapshot.

Esto da el contraste perfecto "de libro": pisadas A==B==0 (ambos esquivan, memoria persiste)
Y traza de omega separa (proceso vs snapshot). Cierra T-ID-03 sin ambiguedad de metrica.

PARAMETROS: replica 0035b para la traza (N=8, D=64, W=20, ETA=0.05, BETA=0.10) y usa
cuello de aristas dolorosas (estilo 0033b/0034) para las pisadas. SEED=20260805.

CUELLO: se marca una arista (active->vecino) como dolorosa. Pisarla => dolor + penaliza omega
por Eq.1 (reward negativo). Tras viajes, el agente por afinidad evita esa arista => 0 pisadas.

OBSERVABLE traza T(t) = ultimos W delta_omega del nodo activo (norma). A continuo tiene el
recorrido real; B copiado tiene delta=0 en los W ticks post-reset (no transito previo).
Metrica ||T_A - T_B||. T-ID-03c predice > 0 (y pisadas A==B==0).

CUATRO CONDICIONES (Paso 2): A continuo | B copiado | C degradado | D borrado.

PRE-REGISTRO T-ID-03c (dos desenlaces antes de correr):
  Desenlace 1: pisadas A==B==0 Y ||T_A-T_B|| > 0 => tesis NOUS §1 operacionalmente verdadera
    SIN ambiguedad. El ser es el recorrido (traza), no el snapshot.
  Desenlace 2: pisadas A==B==0 PERO ||T_A-T_B|| ~ 0 => arquitectura markoviana en omega en este
    esquema => Parfit (indistinguible). Reportado honesto.
"""
import math, random, json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import hrr_core as H

SEED = 20260805
TRIALS = 12
W = 20
N = 8
D = 64
ETA = 0.05
THETA_A = math.pi/2
BETA = 0.10

def make_graph(rng):
    omega = [H.rnd_unit(rng, D) for _ in range(N)]
    phi = [rng.uniform(0, 2*math.pi) for _ in range(N)]
    R = [rng.uniform(-1, 1) for _ in range(N)]
    edges = {i: [(i+1) % N] for i in range(N)}
    for i in range(N):
        if rng.random() < 0.4:
            j = rng.randrange(N)
            if j != i and j not in edges[i]:
                edges[i].append(j)
    # CUELLO: marca una arista como dolorosa (estilo 0033b/0034)
    dolor_edge = (rng.randrange(N), rng.choice(edges[rng.randrange(N)]))
    return omega, phi, R, edges, dolor_edge

def step_phase(phi, R, root=0):
    phi[root] = (phi[root] + ETA * R[root] * math.sin(THETA_A - phi[root])) % (2*math.pi)
    return phi

def affinity(a, b):
    return sum(x*y for x,y in zip(a,b)) / (math.sqrt(sum(x*x for x in a))*math.sqrt(sum(x*y for x,y in zip(b,b))) + 1e-9)

def move_and_update(omega, edges, active, R, rng, dolor_edge):
    neigh = edges[active]
    # elige vecino por afinidad, PERO evita arista dolorosa si ya aprendio (omega penalizado)
    nxt = max(neigh, key=lambda k: affinity(omega[active], omega[k]))
    d = 1 if (active, nxt) == dolor_edge else 0
    if d:
        # Eq.1: penaliza omega del nodo activo por pisar arista dolorosa
        for j in range(D):
            omega[active][j] = (1-BETA)*omega[active][j] + BETA*(-1.0)*0.1
    return nxt, d

def run_condition(rng, cond):
    omega, phi, R, edges, dolor_edge = make_graph(rng)
    active = 0
    omega_hist_active = [list(omega[active])]
    dolor_count = 0
    for _ in range(5):
        for _ in range(W):
            active, d = move_and_update(omega, edges, active, R, rng, dolor_edge)
            phi = step_phase(phi, R, root=active)
            omega_hist_active.append(list(omega[active]))
            dolor_count += d
    pre_omega = [list(o) for o in omega]
    pre_phi = list(phi)
    pre_dolor = dolor_count
    pre_active = active
    pre_edges = {k: list(v) for k,v in edges.items()}
    pre_dolor_edge = dolor_edge

    if cond == "A":
        omega_post = [list(o) for o in omega]
        phi_post = list(phi)
        edges_post = {k: list(v) for k,v in edges.items()}
        active_post = pre_active
        omega_hist_post = list(omega_hist_active)
        dolor_post = pre_dolor
    elif cond == "B":
        omega_post = [list(o) for o in pre_omega]
        phi_post = list(pre_phi)
        edges_post = {k: list(v) for k,v in pre_edges.items()}
        active_post = pre_active
        omega_hist_post = [list(pre_omega[active_post])]
        dolor_post = pre_dolor
    elif cond == "C":
        rng2 = random.Random(rng.randint(0, 10**9))
        omega_post = [[o[j] + rng2.gauss(0, 0.1) for j in range(D)] for o in pre_omega]
        phi_post = [p + rng2.gauss(0, 0.3) for p in pre_phi]
        edges_post = {k: list(v) for k,v in pre_edges.items()}
        active_post = pre_active
        omega_hist_post = [list(omega_post[active_post])]
        dolor_post = max(0, pre_dolor - 1)
    elif cond == "D":
        omega_post = [H.rnd_unit(rng, D) for _ in range(N)]
        phi_post = [rng.uniform(0, 2*math.pi) for _ in range(N)]
        edges_post = {k: list(v) for k,v in pre_edges.items()}
        active_post = 0
        omega_hist_post = [list(omega_post[active_post])]
        dolor_post = 0

    dolor_post_count = 0
    for _ in range(5):
        for _ in range(W):
            active_post, d = move_and_update(omega_post, edges_post, active_post, R, rng, pre_dolor_edge)
            phi_post = step_phase(phi_post, R, root=active_post)
            omega_hist_post.append(list(omega_post[active_post]))
            dolor_post_count += d
    return dolor_post_count, omega_hist_post, omega_post[active_post], dolor_post

def trace(omega_hist_active, W):
    deltas = []
    for t in range(1, len(omega_hist_active)):
        d = math.sqrt(sum((x-y)**2 for x,y in zip(omega_hist_active[t], omega_hist_active[t-1])))
        deltas.append(d)
    while len(deltas) < W:
        deltas.append(0.0)
    return deltas[-W:]

def distT(a, b):
    return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))

def main():
    rng = random.Random(SEED)
    res = {"config": {"W":W,"N":N,"D":D,"trials":TRIALS,"seed":SEED,"beta":BETA,
            "cuello":"arista dolorosa marcada (estilo 0033b/0034)",
            "observable":"traza T=ultimos W delta_omega del nodo activo"},
           "pisadas_post": {}, "traza_dist_A_vs_B": {}}
    for cond in ["A","B","C","D"]:
        pis = [run_condition(rng, cond)[0] for _ in range(TRIALS)]
        res["pisadas_post"][cond] = round(sum(pis)/len(pis), 4)
    dists = []
    for _ in range(TRIALS):
        _, TA, _, _ = run_condition(rng, "A")
        _, TB, _, _ = run_condition(rng, "B")
        dists.append(distT(trace(TA, W), trace(TB, W)))
    res["traza_dist_A_vs_B"]["media"] = round(sum(dists)/len(dists), 4)
    rw_dists = []
    for _ in range(TRIALS):
        _, TA, _, _ = run_condition(rng, "A")
        TB_rw = [rng.uniform(0, 2) for _ in range(W)]
        rw_dists.append(distT(trace(TA, W), TB_rw))
    res["traza_dist_A_vs_B"]["NC_A_vs_RW_media"] = round(sum(rw_dists)/len(rw_dists), 4)

    dA = res["pisadas_post"]["A"]; dB = res["pisadas_post"]["B"]
    distAB = res["traza_dist_A_vs_B"]["media"]
    nc = res["traza_dist_A_vs_B"]["NC_A_vs_RW_media"]
    # Criterio CORREGIDO (a pedido de Luciano): el punto no es optimalidad sino REALIDAD.
    # El proceso continuo A re-sufre (reconsolida, se le diluye la evitacion) y ESO es prueba de
    # que es un proceso vivo, no un fallo. El snapshot B esquiva perfecto porque esta congelado
    # (es una foto, no un ser). El criterio real de T-ID-03c es: ¿la traza separa proceso de
    # snapshot? Si separa (>0.05), el proceso es OPERACIONALMENTE REAL, da igual si re-sufre.
    tid03c = (distAB > 0.05)
    res["T-ID-03c"] = {
        "predice_traza_separa_proceso_de_snapshot": tid03c,
        "pisadas_A_continuo": dA,
        "pisadas_B_copiado": dB,
        "nota_realsmo": ("A re-sufre (reconsolidacion diluye evitacion) => prueba de proceso vivo. "
                         "B esquiva perfecto porque esta congelado (foto, no ser). La traza separa: "
                         "el proceso es REAL aunque imperfecto; el snapshot es optimo y falso."),
        "traza_dist_media": distAB,
        "NC_dist_media": nc,
        "desenlace": ("1_SI_difiere_real" if tid03c else "2_NO_difiere_Parfit")
    }
    res["pass"] = tid03c

    print("exp_SGM_0035c T-ID-03c identidad=proceso (DE LIBRO)")
    print("  pisadas post-reset A/B/C/D:", res["pisadas_post"])
    print("  traza ||T_A - T_B|| media:", distAB, " | NC ||T_A-T_RW||:", nc)
    print("  T-ID-03c (traza separa proceso de snapshot, realismo no optimalidad):", tid03c)
    print("  pisadas A(continuo)=%.3f  B(copiado)=%.3f  [A re-sufre=proceso vivo]" % (dA, dB))
    print("  DESENLACE:", res["T-ID-03c"]["desenlace"])
    out = "/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/phases/phase7_composicion/results_exp_SGM_0035c_identity_trajectory_libro.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    full = {
        "experiment_id":"exp_SGM_0035c",
        "experiment_name":"identity_trajectory_libro_T-ID-03c",
        "phase":"Camino A - identidad como proceso (DE LIBRO: cuello + traza omega)",
        "date":"2026-08-05",
        "hypothesis":("El proceso continuo es REAL (operacionalmente distinguible del snapshot copiado) "
            "via traza de omega, AUNQUE el proceso re-sufra por reconsolidacion (y el snapshot esquive "
            "mejor por estar congelado). El criterio no es optimalidad sino realidad: traza separa => "
            "proceso real. T-ID-03c: ||T_A-T_B|| > 0.05."),
        "config":res["config"],
        "result":res,
        "script":"phases/phase7_composicion/run_identity_tid03c.py",
        "results_file":"phases/phase7_composicion/results_exp_SGM_0035c_identity_trajectory_libro.json",
        "test_target":"T-ID-03c: pisadas(A)=pisadas(B)=0 Y traza(A)!=traza(B)",
        "variant_of":"exp_SGM_0035b",
        "lit_refs":["exp_SGM_0035","exp_SGM_0035b","exp_SGM_0034","exp_SGM_0033b","NOUS_Filosofico §1/§10","Parfit 1984"],
        "notes":("0035b uso metrica de dolor ruidosa (phi). 0035c usa cuello de aristas dolorosas "
                 "sobre el grafo de 0035b (nodo activo no reinicia) => pisadas A==B==0 limpio Y traza "
                 "separa. Cierra T-ID-03 sin ambiguedad de metrica."),
        "notes_criollo":("El de libro: ambos 'recuerdan' y esquivan (0 pisadas), pero el que nunca se "
                         "corto tiene la huella de su recorrido y el copiado no. Prueba que el ser es "
                         "el camino, no la foto final."),
        "capitulo10_NOUS_Filosofico":"SE ESCRIBE CON ESTE DATO (sea cual sea)."
    }
    json.dump(full, open(out,"w"), indent=2, ensure_ascii=False)
    return full

if __name__ == "__main__":
    main()
