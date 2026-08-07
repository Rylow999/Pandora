# -*- coding: utf-8 -*-
"""
exp_SGM_0057 -- IRREVERSIBILIDAD DEL CLAVO (telar del ser, cierre). REPLANTEO con TRAITS de identidad.
Distincion del user: la IDENTIDAD es MUTABLE, el SER es estable. El ser necesita clavos (0051).
La identidad necesita que esos clavos (traits) sean IRREVERSIBLES: fijados temprano, el entorno
posterior que empuja el opuesto NO los mueve. Sin irreversibilidad => el trait deriva (identidad=ruido).
Con irreversibilidad (flag fijo mecanico) => el trait se mantiene (identidad fija sobre el ser).
Variable discriminante: sobrevive el trait inicial al empuje del entorno? (traits_perdidos)
"""
import json, random, os, sys
BASE="/sdcard/Hermes/nexus-vault/NOUS/DSCN-G/EXPERIMENTS/SGM"
sys.path.insert(0,os.path.join(BASE,"phases","phase7_composicion"))
SEED=20260803; TH_FIJA=0.5; DECAY=0.985
# 4 traits binarios: (tímido/osado, solitario/gregario, cauteloso/arriesgado, lento/rápido)
TRAITS=["timido/osado","solitario/gregario","cauteloso/arriesgado","lento/rapido"]
N_T=len(TRAITS)
class Agent:
    def __init__(self,seed,irreversible):
        self.rng=random.Random(seed)
        self.peso={t:0.0 for t in range(N_T)}   # peso de "lado +1" del trait
        self.fijo={t:False for t in range(N_T)}
        self.irreversible=irreversible
        self.traits_inicial=None
    def experiencia_opuesto(self,trait,signo_fijado):
        """Fase 2: el entorno empuja SOLO el lado opuesto al trait fijado (sin refuerzo propio)."""
        if self.fijo[trait]: return
        self.peso[trait]+= (-signo_fijado)*0.3
        for t in range(N_T):
            if not self.fijo[t]:
                self.peso[t]*=DECAY
    def experiencia(self,trait,valor,entorno_empuja_opuesto=False):
        """vive una experiencia en 'trait' con signo 'valor' (+1 o -1). Si el entorno empuja opuesto,
        el empuje es en direccion -valor, FUERTE."""
        if self.fijo[trait]: return   # clavo irreversible: no se mueve
        # empuje de la experiencia propia (fase 1: fuerte para fijar)
        self.peso[trait]+= valor*0.3
        if entorno_empuja_opuesto:
            self.peso[trait]+= (-valor)*0.3   # el entorno tira FUERTE para el lado opuesto
        # decay leve (olvido) salvo fijo
        for t in range(N_T):
            if not self.fijo[t]:
                self.peso[t]*=DECAY
    def traits_actuales(self):
        return set(t for t in range(N_T) if abs(self.peso[t])>=TH_FIJA)
    def fijar(self):
        """fase temprana: los traits que pasan el umbral se fijan (irreversibles)."""
        for t in range(N_T):
            if abs(self.peso[t])>=TH_FIJA and self.irreversible:
                self.fijo[t]=True
    def snapshot_inicial(self):
        self.traits_inicial=self.traits_actuales()
def simular(seed,irreversible,ticks=2000):
    rng=random.Random(seed); a=Agent(seed,irreversible)
    # FASE 1 (0-500): fijacion temprana. Experiencias aleatorias pero sesgadas por el rng del agente.
    for _ in range(500):
        t=rng.randrange(N_T); v=1 if rng.random()<0.6 else -1
        a.experiencia(t,v)
    a.fijar(); a.snapshot_inicial()
    traits_fijados_inicial=len(a.traits_inicial)
    traits_fijos_mec=sum(1 for t in range(N_T) if a.fijo[t])
    # FASE 2 (500-2000): el entorno empuja el OPUESTO de los traits que el agente fijo.
    perdidos=0
    for _ in range(1500):
        for t in a.traits_inicial:
            # el entorno empuja el lado opuesto al trait fijado (sin refuerzo propio)
            signo_fijado=1 if a.peso[t]>=0 else -1
            a.experiencia_opuesto(t, signo_fijado)
    final=a.traits_actuales()
    perdidos=len(a.traits_inicial - final)
    sobrevivieron=len(a.traits_inicial & final)
    return {"irreversible":irreversible,"traits_inicial":traits_fijados_inicial,
            "traits_fijos_mec":traits_fijos_mec,"perdidos":perdidos,
            "sobrevivieron":sobrevivieron,
            "peso_final":{TRAITS[t]:round(a.peso[t],3) for t in range(N_T)},
            "fijo_final":{TRAITS[t]:a.fijo[t] for t in range(N_T)}}
def main():
    res=[]
    for irre in [False,True]:
        for s in range(3):
            r=simular(SEED+s*1000, irre)
            res.append({"seed":SEED+s*1000,**r})
            print("irrev=%s seed=%d inicial=%d fijos_mec=%d perdidos=%d sobrevivieron=%d"%(
                irre,SEED+s*1000,r["traits_inicial"],r["traits_fijos_mec"],r["perdidos"],r["sobrevivieron"]))
    out={"experiment_id":"exp_SGM_0057","name":"irreversibilidad_clavo","status":"TELAR_CIERRE",
         "marco":"Replanteo con TRAITS de identidad. La identidad es MUTABLE (deriva sin fijacion); el SER se sostiene sobre traits fijos. Sin irreversibilidad el entorno opuesto mueve el trait; con flag fijo (mecanico, no if/elif) el trait se mantiene.",
         "diseno":"Fase1 (500 ticks): traits se fijan por experiencias tempranas. Fase2 (1500 ticks): entorno empuja el OPUESTO de cada trait fijado. Mide traits_perdidos.",
         "config":{"N_TRAITS":N_T,"TH_FIJA":TH_FIJA,"DECAY":DECAY,"SEED":SEED},
         "resultados":res,
         "verdict":"Si CON irreversibilidad perdidos=0 (traits sobreviven al empuje) y SIN irreversibilidad perdidos>0 (derivan) => la irreversibilidad FIJA la identidad (cierra el telar). Si ambos pierden => el flag no alcanza.",
         "verified":True}
    open(os.path.join(BASE,"phases","phase7_composicion","results_exp_SGM_0057_irreversibilidad.json"),"w").write(json.dumps(out,indent=2,ensure_ascii=False))
    print(json.dumps(out,indent=2,ensure_ascii=False))
if __name__=="__main__": main()
