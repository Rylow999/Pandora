#!/usr/bin/env python3
"""sgm_bridge.py — Puente HTTP CHAT↔SGM (lado Python).

Sirve el sustrato SGM via HTTP local para que el bot de mineflayer
(puente_minecraft_sgm.js) le pase los mensajes de chat y devuelva las respuestas.
  - GET /hablar?texto=...  -> ag.procesar_instruccion(texto)  (tu -> SGM) y luego SGM se expresa
  - GET /estado            -> SGM genera un mensaje espontaneo (SGM -> tu)
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

# un agente SGM persistente para la sesion
ag = SGMAgent(random.Random(42), 128, n_nodes=64, gamma=0.01)
ag.set_edges({i: random.sample(range(64), min(5, 63)) for i in range(64)})
il = InterfazLenguaje()
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
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/hablar":
            texto = q.get("texto", [""])[0]
            # tu -> SGM: procesar la instruccion (afecta su estado)
            r_inst = ag.procesar_instruccion(texto)
            # SGM responde expresando su estado (lo que quiere decir tras tu instruccion)
            frase, cat, _ = il.expresarse(ag)
            resp = f"[SGM:{cat}] {frase}"
            self._send(resp)
        elif u.path == "/estado":
            frase, cat, _ = il.expresarse(ag)
            self._send(f"[SGM:{cat}] {frase}")
        else:
            self._send("ok - sgm_bridge")

    def log_message(self, *a):
        pass

if __name__ == "__main__":
    port = 8790
    HTTPServer(("127.0.0.1", port), Puente).serve_forever()