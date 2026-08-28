#!/usr/bin/env python3
"""pandora.py — PANDORA: le da forma al nucleo SGM, con Minecraft como su mundo.

ANCLA TODO EL DOCUMENTO (docs/Arquitectura_Pure_L2_Pandora.md) a lo que ya
construimos y funciono. No duplica: ORQUESTA los modulos existentes bajo la
arquitectura PURE-L2 / NOUS / DSCN-BIO.

MAZO (como surge Pandora):
  - Python vs. document's struct -> Pandora envuelve el SGMAgent (el 'nucleo motor
    cognitivo' del doc) y los modulos que ya probamos (sgm_lang, sgm_mundo, sgm_atencion).
  - El documento separa ALMACENAMIENTO SEMANTICO (grafo) de DECODIFICACION L2 (capa
    externa). Pandora = eso: el grafo (sgm_core) decide QUE; la capa de lenguaje
    (sgm_lang_interfaz + sgm_atencion) determina COMO se expresa y con que intencion.
  - La IDENTIDAD reside en la TRAYECTORIA del hilo por el grafo (NOUS §2.2): Pandora
    es la historia que dibuja su omega al vivir en Minecraft, no un nodo fijo.

LITERATURA ADQUIRIDA (anclada): Kanerva VSA/HDC (binding/cleanup), Kuramoto (fases),
PPR (ruteo multi-hop), Yin&Tucker no --- las que ya estan en SGM_literature_index.md.
"""
import sys, os, json, random, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm.core.sgm_core import SGMAgent


class Pandora:
    """Pandora: el ser. Envuelve el nucleo SGM y le da cuerpo, sentir, mente, y voz
    con Minecraft como mundo. Orquesta los modulos existentes; no implementa de nuevo."""

    def __init__(self, seed=42, D=128, n_nodes=64, nombre="Pandora"):
        self.nombre = nombre
        # EL NUCLEO MOTOR COGNITIVO (el SGM del documento); cerebro/grafo
        self.cerebro = SGMAgent(random.Random(seed), D, n_nodes=n_nodes, gamma=0.01)
        self.cerebro.set_edges({i: random.sample(range(n_nodes), min(5, n_nodes - 1)) for i in range(n_nodes)})
        # capa de lenguaje (COMO hablo) + intencion (QUE quiero decir)
        self.lang = None   # InterfazLenguaje (init post-import para path)
        self.atencion = None
        self._inicializado_lenguaje = False
        # C U E R P O (percepcion del mundo Minecraft): estado actual
        self.pos = (0, 0, 0)
        self.food = 20.0
        self.health = 20.0
        self.entidades_near = []
        self.bloques_near = []
        # S E N T I R (homeostasis y valencia via el core)
        # P E R S I S T E N C I A (el doc: identidad en la trayectoria, no nodo fijo)
        self.ruta_estado = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pandora_estado.json")
        self._cargar_estado()  # recuperar lo vivido (persistencia en caliente)

    def _init_lang(self):
        """Inicializa la capa de lenguaje/intencion (import diferido para que el path funcione)."""
        if self._inicializado_lenguaje:
            return
        from sgm_lang_interfaz import InterfazLenguaje
        from sgm_atencion import ClasificadorIntencion
        self.lang = InterfazLenguaje()
        self.atencion = ClasificadorIntencion(agente=self.cerebro)
        self.lang.cargar_todo(self.cerebro)  # restaurar vocabulario/vida previa
        self._lenguaje_inicializado = True

    # ---------- C U E R P O: el mundo llega por aqui ----------
    def percibir(self, pos, food=20, health=20, entidades=None, bloques=None):
        """Pandora PERCIBE su mundo (la percepción del bot de Minecraft).
        Actualiza cuerpo + senales internas del core (hambre, amenaza, recursos)."""
        self.pos = tuple(pos)
        self.food = food; self.health = health
        self.entidades_near = entidades or []
        self.bloques_near = bloques or []
        x, y, z = self.pos[0], self.pos[1], self.pos[2]
        # senales internas (hambre real, amenaza por entidades hostiles)
        hambre = max(0.0, 1.0 - food / 20.0)
        self.cerebro._hambre_real = min(1.0, hambre)
        peligro = 1.0 if any(e in ("zombie", "skeleton", "creeper", "spider") for e in self.entidades_near) else 0.0
        self.cerebro._amenaza = min(1.0, peligro)
        self.cerebro._posicion_actual = (int(x), int(z))

    # ---------- M E N T E: decidir (usa el nucleo real) ----------
    def decidir(self, acciones_validas=None):
        """Pandora decide su siguiente accion usando el GREGA/VSA del core (el motor
        cognitivo del documento). Devuelve la accion (indice 0-16 del core)."""
        acciones = acciones_validas or list(range(17))
        sv = self._estado_vector()
        self.cerebro._config_curio = {"activo": True, "fuerza": 0.4}
        self.cerebro._inc_dirs = {a: 1.0 for a in (1, 2, 3, 4)}
        self.cerebro._hay_gradiente = False
        return self.cerebro.step(sv, acciones)

    def _estado_vector(self):
        """Construye el vector de estado (percepcion -> omega-like) para la decision."""
        x, y, z = self.pos[0], self.pos[1], self.pos[2]
        peligro = 1.0 if any(e in ("zombie", "skeleton", "creeper", "spider") for e in self.entidades_near) else 0.0
        recurso = 1.0 if any(b in ("oak_log", "log", "tree", "wood") for b in self.bloques_near) or \
                    any(e in ("cow", "pig", "chicken") for e in self.entidades_near) else 0.0
        return [float(x / 50.0), float(z / 50.0), max(0.0, 1.0 - self.food / 20.0),
                peligro, recurso, self.health / 20.0, self.food / 20.0,
                0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

    # ---------- S E N T I R / sentimientos emergentes ----------
    @property
    def sentimiento(self):
        """El 'sentir' actual de Pandora, emergente de su estado interno (no programado):
        hambre, valencia (gusto/aversion), duda (incertidumbre), curiosidad (drive)."""
        c = self.cerebro
        if getattr(c, "_amenaza", 0) > 0.4:
            return "asustad{o/a}"
        if getattr(c, "_hambre_real", 0) > 0.7:
            return "con hambre"
        if getattr(c, "incertidumbre_acum", 0) > 2.5 or getattr(c, "doubt_count", 0) > 3:
            return "dudando"
        if getattr(c, "drive_noop", 0) > 0.8:
            return "curioso, quiero explorar"
        if c.valencia_recurso:
            b = max(c.valencia_recurso, key=c.valencia_recurso.get)
            v = c.valencia_recurso[b]
            return f"interesado en {b}" if v > 0 else f"rechazando {b}"
        return "en calma, observando su mundo"

    # ---------- V O Z: hablar con intencion ----------
    def responder(self, mensaje_humano):
        """Pandora escucha, clasifica la intencion (HRR) y responde SEGUN el acto.
        Devuelve (respuesta_texto, intencion, plan_ejecucion_opcional)."""
        self._init_lang()
        clasi = self.atencion.intencion(mensaje_humano)
        intencion = clasi.get("intencion", "charla")
        resp, plan = "", None
        if intencion == "charla":
            frase, cat, _ = self.lang.expresarse(self.cerebro)
            resp = f"[charla] hola, {frase}".strip()
        elif intencion == "pregunta":
            import sgm_mundo
            analisis = sgm_mundo.analizar_instruccion(mensaje_humano)
            if analisis["objeto"]:
                resp = f"[pregunta] sobre {analisis['objeto']}: " + (
                    f"tengo {self.cerebro._hambre_real:.2f} hambre" if self.cerebro._hambre_real > 0.3
                    else "estoy estable, siento el mundo")
            else:
                ri = self.cerebro.procesar_instruccion(mensaje_humano)
                resp = f"[pregunta] {ri['texto']}"
        elif intencion == "relato":
            ri = self.cerebro.procesar_instruccion(mensaje_humano)
            ap = ri.get("palabras_nuevas", [])
            resp = f"[relato] aprendi: {', '.join(ap[:5])}" if ap else "[relato] entendido, lo registro"
        else:  # indicacion
            import sgm_mundo
            ri = self.cerebro.procesar_instruccion(mensaje_humano)
            analisis = sgm_mundo.analizar_instruccion(mensaje_humano)
            resp = f"[indicacion] {ri['texto']}"
            if analisis["accion"] in ("romper", "mover", "comer", "atacar", "recolectar", "craftear"):
                plan = {"accion": analisis["accion"], "objeto": analisis["objeto"]}
        self._guardar_estado()  # persistir tras interactuar
        return resp, intencion, plan

    # ---------- P E R S I S T E N C I A (identidad en la trayectoria) ----------
    def _guardar_estado(self):
        """Guarda el estado de Pandora (vida/vocabulario/valencia/duda) -> sobrevive al stop."""
        try:
            if self.lang:
                self.lang.guardar_todo(self.cerebro)
        except Exception:
            pass

    def _cargar_estado(self):
        """Restaura lo vivido si Pandora existia antes (identidad continua entre sesiones)."""
        try:
            self._init_lang()
        except Exception:
            pass


# Si se corre directo, una demo de Pandora en 'vivo' (sin Minecraft, ciclo de estado)
if __name__ == "__main__":
    p = Pandora(seed=1)
    print(f"Pandora nacio. Su sentir inicial: {p.sentimiento}")
    # simular percepcion de su mundo
    p.percibir((10, 0, 10), food=6, health=20, entidades=[], bloques=["oak_log"])
    print(f"  Percibe madera cerca, hambre {p.food}/20 -> sentir: {p.sentimiento}")
    # hablar con intencion
    for m in ["hola", "tala el arbol", "que ves?"]:
        r, i, plan = p.responder(m)
        print(f"  humano: '{m}' -> [{i}] {r} {'| ejecutar: '+str(plan) if plan else ''}")
    print(f"\nPandora esta viva en su mundo (Minecraft es su cuerpo).")