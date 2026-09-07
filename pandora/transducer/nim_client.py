# -*- coding: utf-8 -*-
"""pandora/transducer/nim_client.py — Cliente para Nvidia NIM.

NIM expone una API OpenAI-compatible (chat completions). Este cliente lee
NVIDIA_API_KEY y NVIDIA_BASE_URL del entorno (no hardcodea credenciales), y
expone la MISMA interfaz que OllamaClient (.chat() devuelve dict con
message.content), para que sea drop-in en el transductor.

La razón de NIM: el hardware local está limitado por RAM (qwen2.5:0.5b), y NIM
da un modelo mucho más capaz vía API. El LLM sigue siendo TRANSDUCTOR, no mente:
traduce en ambas direcciones sin originar estado mental (ACTA P1, arquitectura
transducer). Y la convierte en voz rica sin reentrenar.
"""
import json
import os
import urllib.request
import urllib.error


class NimClient:
    """Cliente para Nvidia NIM (chat completions, formato OpenAI)."""

    def __init__(self, api_key=None, base_url=None, model=None, timeout=120):
        self.api_key = api_key or os.environ.get("NVIDIA_API_KEY", "")
        self.base_url = (base_url or os.environ.get("NVIDIA_BASE_URL")
                         or "https://integrate.api.nvidia.com/v1").rstrip("/")
        # Modelo por defecto: el que la cuenta NIM tiene habilitado como función
        # serverless (deepseek-v4-pro). Puede sobrescribirse por env NVIDIA_MODEL.
        self.model = model or os.environ.get("NVIDIA_MODEL",
                                             "deepseek-ai/deepseek-v4-pro-0813")
        self.timeout = timeout

    def _headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def chat(self, messages, temperature=0.3, max_tokens=256, **kwargs):
        """Envía una conversación y devuelve el dict de respuesta.

        Devuelve {"message": {"content": str}} para ser compatible con el
        contrato que el Articulator ya espera de OllamaClient.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        url = f"{self.base_url}/chat/completions"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=self._headers(), method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detalle = e.read().decode("utf-8") if e.fp else str(e)
            raise RuntimeError(f"NIM HTTP {e.code}: {detalle}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"NIM conexión fallida: {e.reason}")

        # Respuesta defensiva: si choices viene vacío (contenido filtrado), evitar
        # el IndexError. No debe tumbar un turno por una respuesta rara de la API.
        choices = body.get("choices", [])
        if not choices:
            return {"message": {"content": ""}, "raw": body}
        contenido = choices[0].get("message", {}).get("content", "")
        return {"message": {"content": contenido}, "raw": body}

    def disponible(self):
        return bool(self.api_key)


def get_nim_client():
    return NimClient()


if __name__ == "__main__":
    c = get_nim_client()
    print("NIM disponible:", c.disponible())
    print("modelo:", c.model)
    if c.disponible():
        r = c.chat([{"role": "user", "content": "Respondé solo la palabra 'ok'."}])
        print("respuesta:", r["message"]["content"].strip())