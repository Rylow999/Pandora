#!/usr/bin/env python3
"""sgm_bridge.py — Puente HTTP CHAT↔SGM + ACCIONES↔SGM (lado Python).

Sirve el sustrato SGM via HTTP local para que el bot de mineflayer
(puente_minecraft_sgm.js) le pase:
  - los mensajes de chat (tu -> SGM) y devuelva las respuestas.
  - la percepcion del mundo (posicion, bloques, entidades) y devuelva la ACCION que
    SGM decide (moverse/romper/interactuar) usando sgmo.SGMAgent.step() real.
Usa la interfaz de lenguaje (InterfazLenguaje) y el core (SGMAgent). Sin dependencias.
"""
import sys, os, json, random
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

SGM = os.path.expanduser("~/vaults/vega-vault/NOUS/DSCN-G/EXPERIMENTS/SGM")
sys.path.insert(0, SGM)
sys.path.insert(0, os.path.join(SGM, "experiments"))
import importlib, sgm_core; importlib.reload(sgm_core)
from sgm_core import SGMAgent
from sgm_lang_interfaz import InterfazLenguaje
# clasificador de INTENCION (charla/indicacion/pregunta/relato) con HRR/VSA + sgm_mundo
from sgm_atencion import ClasificadorIntencion
import sgm_mundo

# DECODIFICADOR L2 (PURE-L2): W·ω + b → softmax → token
from sgm_l2_decoder import L2Decoder
from sgm_lang import ID2TOKEN
l2 = L2Decoder(D_sem=128, lr=0.05)
print("[sgm_bridge] Decodificador L2 listo. Pesos en:", l2.ruta_pesos)

# un agente SGM persistente para la sesion
ag = SGMAgent(random.Random(42), 128, n_nodes=64, gamma=0.01)

# clasificador de intencion compartido (usa el HRR del sustrato)
clasif = ClasificadorIntencion(agente=ag)
ag.set_edges({i: random.sample(range(64), min(5, 63)) for i in range(64)})
il = InterfazLenguaje()
print("[sgm_bridge] SGM listo. Escuchando en :8790")

# mapeo de accion de SGM (indice 0-16) a lo que el bot debe hacer
# (coherente con las acciones del core de Crafter; el bot traduce a mineflayer)
# 0=noop/espera, 1-4=mover(caminar), 5=do(interactuar), otros=acciones especiales
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
                clasi = clasif.intencion(texto)
                intencion = clasi.get("intencion", "charla")
                resp = ""
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
                    aprendidas = res_inst.get("palabras_nuevas", [])
                    analisis = sgm_mundo.analizar_instruccion(texto)
                    plan = None
                    if analisis["accion"] in ("romper", "mover", "comer", "atacar", "recolectar", "craftear", "explorar", "saltar", "huir"):
                        plan = {"accion": analisis["accion"], "objeto": analisis["objeto"]}
                    resp = f"[indicacion] {res_inst['texto']}"
                    payload = {"texto": resp, "intencion": intencion}
                    if plan:
                        payload["ejecutar"] = plan
                    if aprendidas:
                        payload["aprendidas"] = aprendidas
                        il.guardar_todo(ag)
                    self._send(json.dumps(payload, ensure_ascii=False))
                    return
                self._send(resp)
            elif u.path == "/estado":
                frase, cat, _ = il.expresarse(ag)
                self._send(f"[SGM:{cat}] {frase}")
            elif u.path == "/accion":
                x = float(q.get("x", ["0"])[0]); y = float(q.get("y", ["0"])[0]); z = float(q.get("z", ["0"])[0])
                food = float(q.get("food", ["20"])[0]); health = float(q.get("health", ["20"])[0])
                hambre = max(0.0, 1.0 - food / 20.0)
                ent_near = q.get("entidades", "[]")[0] if q.get("entidades") else "[]"
                ent_near = json.loads(ent_near) if isinstance(ent_near, str) else ent_near
                peligro = 1.0 if any(e in ("zombie", "skeleton", "creeper", "spider") for e in ent_near) else 0.0
                recurso = 1.0 if any(e in ("tree", "oak_log", "wood", "cow", "pig", "chicken") for e in ent_near) else 0.0
                ag._hambre_real = min(1.0, hambre)
                ag._amenaza = min(1.0, peligro)
                ag._posicion_actual = (int(x), int(z))
                ag._config_grad = {"activo": False, "fuerza": 0.0}
                ag._config_curio = {"activo": True, "fuerza": 0.4}
                ag._inc_dirs = {a: 1.0 for a in (1, 2, 3, 4)}
                ag._hay_gradiente = False
                sv = [float(v) for v in (
                    x / 50.0, z / 50.0, hambre, peligro, recurso,
                    health / 20.0, food / 20.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)]
                eq = ag.cuantizar_estado(sv)
                a = ag.step(sv, list(range(17)))
                accion = ACCION_MC.get(a, "noop")
                self._send(json.dumps({"accion": accion, "indice": a, "hambre": round(ag._hambre_real, 2),
                                       "amenaza": round(ag._amenaza, 2)}))
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
    HTTPServer(("127.0.0.1", port), Puente).serve_forever()