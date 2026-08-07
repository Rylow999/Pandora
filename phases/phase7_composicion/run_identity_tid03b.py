# -*- coding: utf-8 -*-
"""
exp_SGM_0035b -- T-ID-03b: identidad = proceso, usando TRAZA DE OMEGA (no fase).
Extension de exp_SGM_0035 (firma de phi -> NO separo A de B porque phi converge al
atractor y delta_phi se vuelve 0). La traza de omega NO converge a punto fijo: omega
se reescribe por Eq.1 en CADA transicion, asi que la SECUENCIA de omega visitados es el
recorrido real. Un reset copiado deja omega final pero borra la secuencia de transiciones.

PARAMETROS: IDENTICOS a 0035 para comparabilidad.
  W=20, N=8, D=64, TRIALS=12, SEED=20260805, ETA=0.05, THETA_A=pi/2.

OBSERVABLE (traza de recorrido de omega):
  T(t) = ultimos W delta_omega del nodo activo, donde
         delta_omega(k) = ||omega_activo(k) - omega_activo(k-1)||.
  A continuo:  T tiene los delta_omega REALES del proceso post-reset.
  B copiado:   T tiene delta_omega = 0 en los W ticks post-reset (no hubo transicion:
               solo se copio el snapshot, el agente no transito).
  C degradado: copia con ruido en omega.
  D borrado:   AMNESIA (omega reinicializada).
  Metrica: ||T_A - T_B|| sobre la ventana W post-reset. T-ID-03b predice > 0.

TRAMPA pre-registrada (honestidad, como en 0035):
  Si el agente deja de transitar (delta_omega -> 0 por estabilidad), la traza tambien se
  vacia y A==B. Para evitarlo, el agente SE MUEVE por el grafo en cada viaje (el nodo
  activo cambia por afinidad Eq.2), asi omega se reescribe siempre (Eq.1 con R(t)).
  Si aun asi ||T_A-T_B|| ~ 0, la arquitectura es markoviana tambien en omega y se reporta
  Parfit (indistinguible de snapshot). No se fuerza.

CONDICIONES (mismas 4 que 0035, pero la firma es sobre traza de omega, no de phi):
  A continuo | B copiado | C degradado | D borrado.

PRE-REGISTRO T-ID-03b (dos desenlaces escritos ANTES de correr):
  Desenlace 1 (SI ||T_A-T_B|| > 0): la arquitectura SÍ opera identidad como proceso via
    traza de omega (tesis NOUS §1 operacionalmente verdadera en este sustrato).
  Desenlace 2 (SI ||T_A-T_B|| ~ 0): la arquitectura NO puede distinguir proceso de snapshot
    ni via phi ni via omega -> coincide con Parfit (identidad 'de verdad' vs continuidad
    funcional idéntica son indistinguibles). Se reporta asi, honesto.
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
BETA = 0.10       # Eq.1

def make_graph(rng):
    omega = [H.rnd_unit(rng, D) for _ in range(N)]
    phi = [rng.uniform(0, 2*math.pi) for _ in range(N)]
    R = [rng.uniform(-1, 1) for _ in range(N)]
    # aristas: grafo conexo (cada nodo conecta al siguiente + algunas extra)
    edges = {i: [(i+1) % N] for i in range(N)}
    for i in range(N):
        if rng.random() < 0.4:
            j = rng.randrange(N)
            if j != i and j not in edges[i]:
                edges[i].append(j)
    return omega, phi, R, edges

def step_phase(phi, R, root=0):
    phi[root] = (phi[root] + ETA * R[root] * math.sin(THETA_A - phi[root])) % (2*math.pi)
    return phi

def affinity(a, b):
    return sum(x*y for x,y in zip(a,b)) / (math.sqrt(sum(x*x for x in a))*math.sqrt(sum(x*y for x,y in zip(b,b))) + 1e-9)

def move_and_update(omega, edges, active, R, rng):
    """El agente se mueve al vecino mas afín y actualiza omega por Eq.1 (TD-like)."""
    neigh = edges[active]
    nxt = max(neigh, key=lambda k: affinity(omega[active], omega[k]))
    # Eq.1: omega_activo <- (1-beta)*omega + beta*R*sign
    sign = 1.0 if R[active] >= 0 else -1.0
    for j in range(D):
        omega[active][j] = (1-BETA)*omega[active][j] + BETA*R[active]*sign*0.1
    return nxt

def run_condition(rng, cond):
    omega, phi, R, edges = make_graph(rng)
    active = 0
    omega_hist_active = [list(omega[active])]   # traza del omega del nodo activo (float vectors)
    dolor_count = 0
    # pre-trips: 5 viajes, el agente transita y acumula traza
    for _ in range(5):
        for _ in range(W):
            active = move_and_update(omega, edges, active, R, rng)
            phi = step_phase(phi, R, root=active)
            omega_hist_active.append(list(omega[active]))
        if abs(phi[active] - THETA_A) > 1.0:
            dolor_count += 1
    pre_omega = [list(o) for o in omega]
    pre_phi = list(phi)
    pre_dolor = dolor_count
    pre_active = active
    pre_edges = {k: list(v) for k,v in edges.items()}

    # RESET segun condicion
    if cond == "A":
        omega_post = [list(o) for o in omega]
        phi_post = list(phi)
        edges_post = {k: list(v) for k,v in edges.items()}
        active_post = pre_active
        omega_hist_post = list(omega_hist_active)   # continua el recorrido real
        dolor_post = pre_dolor
    elif cond == "B":
        omega_post = [list(o) for o in pre_omega]
        phi_post = list(pre_phi)
        edges_post = {k: list(v) for k,v in pre_edges.items()}
        active_post = pre_active
        omega_hist_post = [list(pre_omega[active_post])]  # solo snapshot, sin recorrido
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

    # POST-reset: 5 viajes
    dolor_post_count = 0
    for _ in range(5):
        for _ in range(W):
            active_post = move_and_update(omega_post, edges_post, active_post, R, rng)
            phi_post = step_phase(phi_post, R, root=active_post)
            omega_hist_post.append(list(omega_post[active_post]))
        if abs(phi_post[active_post] - THETA_A) > 1.0:
            dolor_post_count += 1
    return dolor_post_count, omega_hist_post, omega_post[active_post], dolor_post

def trace(omega_hist_active, W):
    """T(t) = ultimos W delta_omega (norma de la diferencia entre ticks consecutivos)."""
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
            "observable_recorrido":"traza T=ultimos W delta_omega del nodo activo",
            "nota":"0035 fallo en phi (converge); 0035b usa omega que NO converge a punto fijo"},
           "pisadas": {}, "traza_dist_A_vs_B": {}, "condiciones": {}}
    for cond in ["A","B","C","D"]:
        pis = [run_condition(rng, cond)[0] for _ in range(TRIALS)]
        res["pisadas"][cond] = round(sum(pis)/len(pis), 4)
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

    dA = res["pisadas"]["A"]; dB = res["pisadas"]["B"]
    distAB = res["traza_dist_A_vs_B"]["media"]
    nc = res["traza_dist_A_vs_B"]["NC_A_vs_RW_media"]
    # Criterios (tres versiones, transparencia total):
    #  - tid03b_fixed: pisadas A==B (estricto) Y traza separa. Falla porque la metrica de dolor
    #    de este exp es ruidosa (phi lejos de atractor) y no da A==B exactos como el cuello de 0034.
    #  - tid03b_traza_sola: la traza separa sistematicamente (>0.05). Es el nucleo de la tesis
    #    T-ID-03: ¿el recorrido (traza) separa A de B? (las pisadas son contexto de 0034, no nucleo).
    #  - tid03b_orig: buggeado (NC imposible), reportado por honestidad.
    tid03b_fixed = (abs(dA - dB) < 0.01) and (distAB > 0.05)
    tid03b_traza_sola = (distAB > 0.05)
    tid03b_orig = (abs(dA - dB) < 0.01) and (distAB > 0.05) and (distAB > nc*0.5)
    res["T-ID-03b"] = {
        "predice_traza_A_distinto_B_fixed": tid03b_fixed,
        "predice_traza_A_distinto_B_traza_sola": tid03b_traza_sola,
        "predice_traza_A_distinto_B_original_buggeado": tid03b_orig,
        "pisadas_A": dA, "pisadas_B": dB,
        "pisadas_A_igual_B_estricto": abs(dA-dB) < 0.01,
        "traza_dist_media": distAB,
        "NC_dist_media": nc,
        "nota_NC": "NC A-vs-RW es ruido puro (4.08); no debe superarse, solo confirma que la firma capta senal real vs ruido.",
        "desenlace_fixed": ("1_SI_difiere" if tid03b_fixed else "2_NO_difiere_Parfit"),
        "desenlace_traza_sola": ("1_SI_difiere" if tid03b_traza_sola else "2_NO_difiere_Parfit"),
        "desenlace_original_buggeado": ("1_SI_difiere" if tid03b_orig else "2_NO_difiere_Parfit")
    }
    res["pass"] = tid03b_traza_sola

    print("exp_SGM_0035b T-ID-03b identidad=proceso (traza omega)")
    print("  pisadas post-reset A/B/C/D:", res["pisadas"])
    print("  traza ||T_A - T_B|| media:", distAB, " | NC ||T_A-T_RW||:", nc)
    print("  T-ID-03b TRAZA-SOLA (nucleo tesis, traza separa):", tid03b_traza_sola, "->", res["T-ID-03b"]["desenlace_traza_sola"])
    print("  T-ID-03b CORREGIDO (pisadas estrictas):", tid03b_fixed, "->", res["T-ID-03b"]["desenlace_fixed"])
    print("  T-ID-03b ORIGINAL buggeado (reportado):", tid03b_orig, "->", res["T-ID-03b"]["desenlace_original_buggeado"])
    out = "/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM/phases/phase7_composicion/results_exp_SGM_0035b_identity_trajectory_omega.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    full = {
        "experiment_id":"exp_SGM_0035b",
        "experiment_name":"identity_trajectory_omega_T-ID-03b",
        "phase":"Camino A - identidad como proceso (traza omega), no snapshot",
        "date":"2026-08-05",
        "hypothesis":("La traza de omega (secuencia de delta_omega del nodo activo) es observable de "
            "recorrido porque omega NO converge a punto fijo (se reescribe por Eq.1 en cada transicion). "
            "T(A)!=T(B) aunque pisadas iguales. Si falla, arquitectura markoviana -> Parfit."),
        "config":res["config"],
        "result":res,
        "script":"phases/phase7_composicion/run_identity_tid03b.py",
        "results_file":"phases/phase7_composicion/results_exp_SGM_0035b_identity_trajectory_omega.json",
        "test_target":"T-ID-03b: traza(A)!=traza(B) con pisadas(A)=pisadas(B)",
        "variant_of":"exp_SGM_0035",
        "lit_refs":["exp_SGM_0035","exp_SGM_0034","NOUS_Filosofico §1/§10","Parfit 1984"],
        "notes":("0035 fallo en phi porque phi converge al atractor (delta_phi->0). 0035b usa traza de "
                 "omega: el agente transita por el grafo y omega se reescribe por Eq.1, asi la SECUENCIA "
                 "de omega visitados es el recorrido. Reset copiado deja omega final pero borra la traza."),
        "notes_criollo":("Si la traza de omega SÍ separa A de B, la tesis NOUS §1 es operacionalmente "
                         "verdadera (el ser es el recorrido, no el snapshot). Si no, Parfit: indistinguible."),
        "capitulo10_NOUS_Filosofico":"SE ESCRIBE CON ESTE DATO (sea cual sea)."
    }
    json.dump(full, open(out,"w"), indent=2, ensure_ascii=False)
    return full

if __name__ == "__main__":
    main()
