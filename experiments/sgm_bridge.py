#!/usr/bin/env python3
"""sgm_bridge.py — Adaptador entre Minecraft y el SGMAgent real.
Convierte percepciones del bot en state_semantic y ejecuta el step() del core."""

import json, random, sys, os, math
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

SGM = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SGM)
sys.path.insert(0, os.path.join(SGM, "experiments"))
import importlib, sgm_core_minecraft; importlib.reload(sgm_core_minecraft)
from sgm_core_minecraft import SGMAgent

# LA MENTE: agente SGM con toda su maquinaria
ag = SGMAgent(random.Random(42), 128, n_nodes=64, gamma=0.01)

# Configurar el adaptador de Minecraft
ag.instinto_alimentacion = 5  # acción de interactuar (do)

print("[sgm_bridge] SGM listo. Escuchando en :8790")

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
                
                # Procesar el texto como percepciones
                palabras = [p for p in texto_lower.split() if len(p) > 2]
                
                # Crear state_semantic simple para el chat
                sv = [0.0] * 18
                sv[2] = min(1.0, len([p for p in palabras if p in ['hambre', 'comida', 'food']]) * 0.3)
                sv[3] = min(1.0, len([p for p in palabras if p in ['peligro', 'zombie', 'enemigo']]) * 0.3)
                sv[4] = min(1.0, len([p for p in palabras if p in ['arbol', 'madera', 'piedra', 'recurso']]) * 0.3)
                
                # Configurar señales
                ag._hambre_real = sv[2]
                ag._amenaza = sv[3]
                ag._algo_enfrente = 1 if sv[4] > 0 else (2 if sv[3] > 0 else 0)
                
                # Ejecutar step
                valid_actions = list(range(17))
                a = ag.step(sv, valid_actions)
                
                # Mapear acción a respuesta
                accion_nombre = ACCION_MC.get(a, "noop")
                
                # Expresión basada en el estado del grafo
                expresion = self._generar_expresion()
                
                payload = {"texto": expresion, "intencion": "expresion"}
                if a != 0:
                    payload["ejecutar"] = {"accion": accion_nombre, "objeto": palabras[0] if palabras else None}
                
                self._send(json.dumps(payload, ensure_ascii=False))
            elif u.path == "/estado":
                expresion = self._generar_expresion()
                payload = {
                    "texto": expresion,
                    "nodos": len(ag.omega),
                    "V_grafo": round(ag.V_grafo, 3),
                    "modo": getattr(ag, 'modo', 'BASE'),
                    "hambre": round(ag._hambre_real, 2),
                    "amenaza": round(ag._amenaza, 2),
                }
                self._send(json.dumps(payload, ensure_ascii=False))
            elif u.path == "/accion":
                x = float(q.get("x", ["0"])[0])
                y = float(q.get("y", ["0"])[0])
                z = float(q.get("z", ["0"])[0])
                food = float(q.get("food", ["20"])[0])
                health = float(q.get("health", ["20"])[0])
                hambre = max(0.0, 1.0 - food / 20.0)
                ent_near = q.get("entidades", "[]")[0] if q.get("entidades") else "[]"
                ent_near = json.loads(ent_near) if isinstance(ent_near, str) else ent_near
                peligro = 1.0 if any(e in ("zombie", "skeleton", "creeper", "spider") for e in ent_near) else 0.0
                recurso = 1.0 if any(e in ("tree", "oak_log", "wood", "cow", "pig", "chicken") for e in ent_near) else 0.0
                
                # Crear state_semantic de 18 dimensiones
                sv = [
                    x / 50.0, z / 50.0, hambre, peligro, recurso,
                    health / 20.0, food / 20.0, 0.0, 0.0, 0.0,
                    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0
                ]
                
                # Configurar señales internas del agente
                ag._hambre_real = hambre
                ag._amenaza = peligro
                ag._posicion_actual = (int(x), int(z))
                ag._algo_enfrente = 1 if recurso > 0 else (2 if peligro > 0 else 0)
                ag._hay_gradiente = recurso > 0 or peligro > 0
                ag._gradiente_dir = (1, 0) if recurso > 0 else (0, 0)
                ag._config_grad = {"activo": recurso > 0, "fuerza": recurso}
                ag._config_curio = {"activo": True, "fuerza": 0.4}
                ag._inc_dirs = {a: 1.0 for a in (1, 2, 3, 4)}
                
                # Ejecutar el step real del SGMAgent
                valid_actions = list(range(17))
                a = ag.step(sv, valid_actions)
                accion = ACCION_MC.get(a, "noop")
                
                # Actualizar homeostasis
                ag.actualizar_homeostasis(food, health)
                
                self._send(json.dumps({
                    "accion": accion,
                    "indice": a,
                    "hambre": round(hambre, 2),
                    "amenaza": round(peligro, 2),
                    "V_grafo": round(ag.V_grafo, 3),
                    "modo": getattr(ag, 'modo', 'BASE'),
                }))
            elif u.path == "/metacognicion":
                reflexion = {}
                reflexion['nodos'] = len(ag.omega)
                reflexion['V_grafo'] = round(ag.V_grafo, 3)
                reflexion['modo'] = getattr(ag, 'modo', 'BASE')
                reflexion['hambre'] = round(ag._hambre_real, 2)
                reflexion['amenaza'] = round(ag._amenaza, 2)
                reflexion['incertidumbre'] = round(ag.incertidumbre_acum, 2)
                reflexion['drive_noop'] = round(ag.drive_noop, 2)
                reflexion['status'] = ag.status
                self._send(json.dumps(reflexion, ensure_ascii=False))
            else:
                self._send("ok - sgm_bridge")
        except Exception as e:
            try:
                self._send(json.dumps({"error": str(e)}))
            except Exception:
                pass

    def _generar_expresion(self):
        """Generar expresión basada en el estado del grafo."""
        from sgm_core_minecraft import ppr_route
        if not ag.omega:
            return "..."
        rank = ppr_route(ag.edges, 0, ag._aff, alpha=ag.alpha, iters=10)
        indices = sorted(range(len(rank)), key=lambda i: -rank[i])[:3]
        palabras = []
        for i in indices:
            if i < len(ag.omega) and ag.vitalidad[i] > 0.3:
                palabras.append(f"nodo{i}")
        return ' '.join(palabras) if palabras else "..."

    def log_message(self, *a):
        pass

ACCION_MC = {
    0: "noop", 1: "mover_norte", 2: "mover_sur", 3: "mover_oeste", 4: "mover_este",
    5: "interactuar", 6: "romper", 7: "recoger", 8: "colocar", 9: "craftear",
    10: "saludar", 11: "explorar", 12: "atacar", 13: "huir", 14: "saltar",
    15: "agacharse", 16: "expresarse",
}

if __name__ == "__main__":
    port = 8790
    httpd = HTTPServer(("127.0.0.1", port), Puente)
    print(f"[sgm_bridge] escuchando en :{port}")
    httpd.serve_forever()