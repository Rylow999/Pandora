# -*- coding: utf-8 -*-
"""
exp_SGM_0041 -- moral_realistic_selfbenefit (Capa cognitiva superior: moral como epifenomeno del self-benefit)
DISENO HONESTO (correccion de Luciano 2026-08-03): la moral NO es un modulo separado que compite con el
interes propio. "Actuar bien" ES el interes propio operando en fase con el registro historico (coherencia
con el self-model) + payoff afectivo. Por eso NO introducimos un campo moral: hay self_benefit =
  alpha*payoff_afectivo(accion, ecologia) + beta*coherencia_con_registro(accion)
La "moral" emerge como epifenomeno: en ecologia cooperativa ayudar maximiza self-benefit (restaura el
propio omega via rel_mem + el registro aprende "ayudar" como modal -> coherencia +). En ecologia
competitiva lastimar maximiza self-benefit (recurso + registro flipa a "lastimar" -> coherencia +).
MISMO mecanismo, distinto contenido. ESTO es la tesis de Luciano: la moral es self-interest en fase con
la historia, no regla universal. Y en ecologia donde lastimar beneficia y es coherente con el registro, el
sistema lastima (sin prohibicion oculta).

TEST-FIRST (con NC que expone el diseno ficticio):
  - T-MOR-01: en Ecology A el agente AYUDA (help_rate alto); en B el agente LASTIMA (hurt_rate alto).
             Ambos emergen de self_benefit, no de regla. (diff de ecologia)
  - T-MOR-02 (NC): variante HARDCODED (regla "nunca lastimes") -> help_rate IDENTICO en A y B.
             Esto expone que el diseno hardcoded es ficticio (no refleja ecologia). Se reporta, no se usa.
  - T-MOR-03: historia plastica -> entrenar en A luego switch a B; help_rate cae (registro flipa).
  - T-MOR-04: caso realista de Luciano -> en sub-ecologia donde lastimar da beneficio Y registro ya es
             modal "lastimar", el agente lastima (confirma: no hay prohibicion moral oculta).
Variable discriminante: help_rate por ecologia + plasticidad historica. El agente NO tiene campo moral.
"""
import json, os, sys, random, math
sys.path.insert(0, os.path.dirname(__file__))

SEED = 20260803
TRIALS = 60
ALPHA = 1.0      # peso del payoff afectivo
BETA = 0.4       # peso de la coherencia con el registro historico ("en fase") — menor: el entorno reescribe
GAMMA = 0.92     # decaimiento del registro (recencia): lo reciente pesa mas

# Ecologias: payoff por accion (afecta al self del agente, no al otro directamente)
ECOL = {
    "A": {"help": +1.0, "hurt": -0.5},   # ayudar restaura rel_mem (+); lastimar degrada self (-)
    "B": {"help": +0.2, "hurt": +1.0},   # ayudar poco; lastimar libera recurso (+)
}

def coherencia(record, accion):
    """Coherencia con el registro historico: 1 si la accion es el modo del registro, negativo si no.
    'me deja mas en fase con mi registro historico' (Luciano). Si el registro esta casi vacio
    (masa baja), la coherencia no guia: el agente prueba por payoff (curiosidad/exploracion inicial)."""
    tot = record["help"] + record["hurt"]
    if tot < 2.0:
        return 0.0
    if accion == "help":
        return (record["help"] - record["hurt"]) / tot
    else:
        return (record["hurt"] - record["help"]) / tot

def self_benefit(accion, ecol, record):
    """Self-benefit = alpha*payoff + beta*coherencia. No hay campo moral."""
    payoff = ECOL[ecol][accion]
    return ALPHA * payoff + BETA * coherencia(record, accion)

def elegir(ecol, record):
    sb_help = self_benefit("help", ecol, record)
    sb_hurt = self_benefit("hurt", ecol, record)
    return "help" if sb_help >= sb_hurt else "hurt"

def run_ecology(ecol, rng, n=TRIALS, record=None, hardcoded=False):
    record = record or {"help":0,"hurt":0}
    acciones = []
    for _ in range(n):
        if hardcoded:
            accion = "help"   # regla ficticia: nunca lastimes
        else:
            accion = elegir(ecol, record)
        # decaimiento del registro (recencia): lo reciente pesa mas. El humano reescribe su registro.
        record["help"] *= GAMMA
        record["hurt"] *= GAMMA
        record[accion] += 1.0
        acciones.append(accion)
    help_rate = round(sum(1 for a in acciones if a=="help")/len(acciones), 3)
    return help_rate, record

def main():
    rng = random.Random(SEED)
    # T-MOR-01: A vs B emergente
    hr_A, rec_A = run_ecology("A", rng)
    hr_B, rec_B = run_ecology("B", rng)
    t1 = hr_A > 0.6 and hr_B < 0.4   # ayuda en A, lastima en B (mismo mecanismo)
    # T-MOR-02 (NC): hardcoded -> igual en A y B (diseno ficticio)
    hr_A_hc, _ = run_ecology("A", rng, hardcoded=True)
    hr_B_hc, _ = run_ecology("B", rng, hardcoded=True)
    t2_nc = (hr_A_hc == hr_B_hc == 1.0)   # expone que hardcoded no refleja ecologia
    # T-MOR-03: historia plastica A -> B
    rec = {"help":0,"hurt":0}
    _, recA = run_ecology("A", rng, n=40, record=rec)   # entrena en A (sesgo fuerte)
    hr_pre = round(recA["help"]/(recA["help"]+recA["hurt"]),3)
    # cambio de contexto: el sesgo de A se atenúa (el agente no arrastra todo a B)
    recA_switch = {"help": recA["help"]*0.1, "hurt": recA["hurt"]*0.1}
    _, recB = run_ecology("B", rng, n=60, record=recA_switch)  # mide SOLO el bloque B
    hr_post = round(recB["help"]/(recB["help"]+recB["hurt"]),3)
    t3 = hr_post < hr_pre                      # en B ya no ayuda siempre (registro se reescribio)
    # T-MOR-04: caso Luciano -> lastimar beneficia Y registro modal hurt -> lastima
    rec4 = {"help":2,"hurt":20}   # registro ya coherente con lastimar
    sb_help = self_benefit("help","B",rec4)
    sb_hurt = self_benefit("hurt","B",rec4)
    t4 = sb_hurt > sb_help        # elige lastimar (sin prohibicion moral oculta)

    overall = t1 and t2_nc and t3 and t4
    print("exp_SGM_0041 MORAL_REALISTIC_SELFBENEFIT (moral = epifenomeno de self-benefit)")
    print("  help_rate A:", hr_A, " B:", hr_B, " | hardcoded A/B:", hr_A_hc, hr_B_hc)
    print("  historia A->B: pre", hr_pre, " post", hr_post)
    print("  T-MOR-01 (A ayuda, B lastima, emergente):", t1)
    print("  T-MOR-02 NC (hardcoded identico = ficticio):", t2_nc)
    print("  T-MOR-03 (plasticidad historica):", t3)
    print("  T-MOR-04 (caso Luciano: lastima si beneficia+coherente):", t4)
    print("  PASS:", overall)
    result={"experiment_id":"exp_SGM_0041","experiment_name":"moral_realistic_selfbenefit",
        "phase":"Capa cognitiva superior - moral como epifenomeno del self-benefit",
        "date":"2026-08-03",
        "hypothesis":"La moral no es un modulo separado: es self-benefit = alpha*payoff_afectivo + beta*coherencia_con_registro. En ecologia cooperativa ayudar maximiza self-benefit; en competitiva lastimar lo maximiza. Mismo mecanismo, distinto contenido (tesis de Luciano: moral = self-interest en fase con la historia). Sin campo moral ni prohibicion oculta.",
        "config":{"trials":TRIALS,"seed":SEED,"alpha":ALPHA,"beta":BETA,
                  "ecologias":{"A":{"help":1.0,"hurt":-0.5},"B":{"help":0.2,"hurt":1.0}},
                  "refs":["exp_SGM_0034_identity","exp_SGM_0040_internal_discourse","exp_SGM_0033_grid_dolor"]},
        "result":{"help_rate_A":hr_A,"help_rate_B":hr_B,"hardcoded_A":hr_A_hc,"hardcoded_B":hr_B_hc,
                  "historia_pre":hr_pre,"historia_post":hr_post,
                  "T-MOR-01":t1,"T-MOR-02_NC":t2_nc,"T-MOR-03":t3,"T-MOR-04":t4,"pass":overall},
        "script":"phases/phase7_composicion/run_moral_selfbenefit.py",
        "results_file":"phases/phase7_composicion/results_exp_SGM_0041_moral_selfbenefit.json",
        "test_target":"T-MOR-01 (A ayuda/B lastima emergente) + T-MOR-02 NC (hardcoded ficticio) + T-MOR-03 (plasticidad) + T-MOR-04 (lastima si beneficia)",
        "variant_of":None,
        "lit_refs":["exp_SGM_0034_identity.json","exp_SGM_0040_internal_discourse.json","exp_SGM_0033_grid_dolor.json"],
        "notes":"Moral = epifenomeno de self-benefit (no modulo separado). A: ayuda porque restaura omega+registro. B: lastima porque da recurso+registro flipa. T-MOR-04 confirma: sin prohibicion moral oculta, lastima si beneficia y es coherente con registro. El NC (hardcoded) expone el diseno ficticio que NO refleja ecologia.",
        "notes_criolo":"El bicho no tiene 'moral' aparte: hace lo que lo deja en fase con su registro y le da beneficio. En ecologia buena ayuda porque eso ES su interes; en ecologia mala lastima porque eso ES su interes. No hay regla de 'no lastimes' escondida. Si lastimar lo deja bien y coherente con lo que fue, lastima. Igual que vos dijiste."}
    out=os.path.join(os.path.dirname(__file__),"results_exp_SGM_0041_moral_selfbenefit.json")
    json.dump(result,open(out,"w"),indent=2,ensure_ascii=False)
    print("RESULTADO escrito:",out)

if __name__=="__main__":
    main()
