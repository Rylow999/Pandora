#!/usr/bin/env python3
"""sgm_bridge.py — Puente entre SGM (mente) y Minecraft (cuerpo).
El SGM core es la mente. El bot es el cuerpo. Este archivo los conecta."""

import json, random, sys, os, math
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

SGM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SGM)
sys.path.insert(0, os.path.join(SGM, "experiments"))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm_core import SGMAgent
from sgm_lang_interfaz import InterfazLenguaje
from sgm_atencion import ClasificadorIntencion
import sgm_mundo

from sgm_l2_decoder import L2Decoder
from sgm_lang import ID2TOKEN
from sgm_metacognicion import Metacognicion, Experimentador

# LA MENTE: agente SGM con todas sus capacidades
ag = SGMAgent(random.Random(42), 128, n_nodes=64, gamma=0.01)
clasif = ClasificadorIntencion(agente=ag)
ag.set_edges({i: random.sample(range(64), min(5, 63)) for i in range(64)})
il = InterfazLenguaje()
l2 = L2Decoder(D_sem=128, lr=0.05)
meta = Metacognicion(ag)
experimentador = Experimentador(ag, meta)

# Configurar el adaptador de Minecraft
ag.instinto_alimentacion = 5  # acción de interactuar

print("[sgm_bridge] SGM listo. Escuchando en :8790")

ACCION_MC = {
    0: "noop", 1: "mover_norte", 2: "mover_sur", 3: "mover_oeste", 4: "mover_este",
    5: "interactuar", 6: "romper", 7: "recoger", 8: "colocar", 9: "craftear",
    10: "saludar", 11: "explorar", 12: "atacar", 13: "huir", 14: "saltar",
    15: "agacharse", 16: "expresarse",
}

class Puente(BaseHTTPRequestHandler):
    def _send(self, txt):
        body = txt.encode("utf-8") if isinstance(txt, str) else txt
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        try:
            u = urlparse(self.path)
            q = parse_qs(u.query)
            if u.path == "/hablar":
                texto = q.get("texto", [""])[0]
                texto_lower = texto.lower().strip()
                clasi = clasif.intencion(texto)
                intencion = clasi.get("intencion", "charla")
                payload = {"intencion": intencion}

                palabras_accion = ["tala", "talar", "rompe", "romper", "mata", "matar", "ataca", "atacar",
                                   "mueve", "mover", "veni", "venir", "ven", "explora", "explorar",
                                   "craftea", "craftear", "recolecta", "recolectar", "recoge", "recoger",
                                   "defiende", "defender", "huir", "escapa", "escapar", "corre", "correr",
                                   "come", "comer", "bebe", "beber", "salta", "saltar", "mina", "minar",
                                   "pica", "picar", "coloca", "colocar", "pon", "poner", "activa", "activar",
                                   "abre", "abrir", "usa", "usar", "equipa", "equipar", "ponte", "ponerse"]

                es_indicacion = any(p in texto_lower for p in palabras_accion)

                if es_indicacion or intencion == "indicacion":
                    res_inst = ag.procesar_instruccion(texto)
                    analisis = sgm_mundo.analizar_instruccion(texto)
                    plan = None
                    if analisis["accion"] in ("romper", "mover", "comer", "atacar", "recolectar", "craftear", "explorar", "saltar", "huir", "colocar", "interactuar", "equipar"):
                        plan = {"accion": analisis["accion"], "objeto": analisis["objeto"]}
                    resp = f"[indicacion] entiendo: {texto}"
                    payload["texto"] = resp
                    if plan:
                        payload["ejecutar"] = plan
                    aprendidas = res_inst.get("palabras_nuevas", [])
                    if aprendidas:
                        payload["aprendidas"] = aprendidas
                        il.guardar_todo(ag)
                    self._send(json.dumps(payload, ensure_ascii=False))
                    return

                if intencion == "charla":
                    frase, cat, _ = il.expresarse(ag)
                    resp = f"[charla] hola, {frase}".strip()
                elif intencion == "pregunta":
                    analisis = sgm_mundo.analizar_instruccion(texto)
                    if analisis["objeto"]:
                        resp = f"[pregunta] sobre {analisis['objeto']}: " + (
                            f"tengo {ag._hambre_real:.2f} hambre" if ag._hambre_real > 0.3 else "estoy estable, siento el mundo")
                    else:
                        res_inst = ag.procesar_instruccion(texto)
                        resp = f"[pregunta] " + res_inst["texto"]
                elif intencion == "relato":
                    res_inst = ag.procesar_instruccion(texto)
                    aprendidas = res_inst.get("palabras_nuevas", [])
                    if aprendidas:
                        il.guardar_todo(ag)
                        resp = f"[relato] aprendi: {', '.join(aprendidas[:5])}"
                    else:
                        resp = f"[relato] entendido, lo registro"
                else:
                    res_inst = ag.procesar_instruccion(texto)
                    resp = f"[indicacion] " + res_inst["texto"]
                    aprendidas = res_inst.get("palabras_nuevas", [])
                    if aprendidas:
                        il.guardar_todo(ag)
                payload["texto"] = resp
                self._send(json.dumps(payload, ensure_ascii=False))
            elif u.path == "/estado":
                frase, cat, _ = il.expresarse(ag)
                self._send(json.dumps({"texto": f"[SGM:{cat}] {frase}", "hambre": ag._hambre_real, "amenaza": ag._amenaza}))
            elif u.path == "/accion":
                x = float(q.get("x", ["0"])[0]); y = float(q.get("y", ["0"])[0]); z = float(q.get("z", ["0"])[0])
                food = float(q.get("food", ["20"])[0]); health = float(q.get("health", ["20"])[0])
                hambre = max(0.0, 1.0 - food / 20.0)
                ent_near = q.get("entidades", "[]")[0] if q.get("entidades") else "[]"
                ent_near = json.loads(ent_near) if isinstance(ent_near, str) else ent_near
                peligro = 1.0 if any(e in ("zombie", "skeleton", "creeper", "spider") for e in ent_near) else 0.0
                recurso = 1.0 if any(e in ("tree", "oak_log", "wood", "cow", "pig", "chicken") for e in ent_near) else 0.0
                
                # Configurar el agente con las señales del mundo
                ag._hambre_real = hambre
                ag._amenaza = peligro
                ag._posicion_actual = (int(x), int(z))
                ag._algo_enfrente = 1 if recurso > 0 else (2 if peligro > 0 else 0)
                ag._hay_gradiente = recurso > 0 or peligro > 0
                ag._gradiente_dir = (1, 0) if recurso > 0 else (0, 0)
                ag._config_grad = {"activo": recurso > 0, "fuerza": recurso}
                ag._config_curio = {"activo": True, "fuerza": 0.4}
                ag._inc_dirs = {a: 1.0 for a in (1, 2, 3, 4)}
                
                # Crear state_semantic de 18 dimensiones (como en Crafter)
                sv = [
                    x / 50.0, z / 50.0, hambre, peligro, recurso,
                    health / 20.0, food / 20.0, 0.0, 0.0, 0.0,
                    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
                ]
                
                # Ejecutar el step real del SGMAgent
                valid_actions = list(range(17))
                a = ag.step(sv, valid_actions)
                accion = ACCION_MC.get(a, "noop")
                
                self._send(json.dumps({
                    "accion": accion, 
                    "indice": a, 
                    "hambre": round(ag._hambre_real, 2),
                    "amenaza": round(ag._amenaza, 2),
                    "V_grafo": round(ag.V_grafo, 3),
                    "modo": getattr(ag, 'modo', 'BASE'),
                }))
            elif u.path == "/hablar_l2":
                omega_json = q.get("omega", "[]")[0] if q.get("omega") else "[]"
                omega = json.loads(omega_json) if isinstance(omega_json, str) else omega_json
                interferencia = float(q.get("interferencia", ["1.0"])[0])
                if len(omega) != ag.D:
                    self._send(json.dumps({"error": "omega dim %d != D %d" % (len(omega), ag.D)}))
                else:
                    import numpy as np
                    omega_np = np.array(omega, dtype=float) * interferencia
                    top = l2.decodificar(omega_np, topk=3, temperatura=0.8)
                    tokens = [(ID2TOKEN.get(t, "??"), "%.3f" % p) for t, p in top]
                    self._send(json.dumps({"tokens": tokens}))
            elif u.path == "/metacognicion":
                try:
                    reflexion = meta.reflexionar()
                    analisis = meta.razonar_sobre_si_mismo()
                    duda_texto = meta.generar_duda_texto()
                    payload = {"reflexion": reflexion, "auto_razonamiento": analisis, "duda": duda_texto}
                    self._send(json.dumps(payload, ensure_ascii=False))
                except Exception as e:
                    self._send(json.dumps({"error": str(e)}))
            else:
                self._send("ok - sgm_bridge")
        except Exception as e:
            try:
                self._send(json.dumps({"error": str(e)}))
            except Exception:
                pass

    def log_message(self, *a):
        pass

if __name__ == "__main__":
    port = 8790
    httpd = HTTPServer(("127.0.0.1", port), Puente)
    print(f"[sgm_bridge] escuchando en :{port}")
    httpd.serve_forever()