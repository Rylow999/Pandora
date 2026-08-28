"""
Cliente HTTP para Ollama local.
Interfaz simple y robusta para generación y chat.
"""

import json
import time
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Any, Generator
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LLMConfig:
    """Configuración del modelo LLM."""
    base_url: str = "http://localhost:11434"
    model: str = "qwen2.5:0.5b-instruct"
    timeout: int = 60
    temperature: float = 0.1
    top_p: float = 0.9
    num_predict: int = 512
    stop: List[str] = None

    def __post_init__(self):
        if self.stop is None:
            self.stop = ["</s>", "<|endoftext|>", "<|im_end|>"]


class OllamaClient:
    """Cliente síncrono para API de Ollama."""

    def __init__(self, config: LLMConfig = None):
        self.config = config or LLMConfig()
        self.session = None  # urllib no necesita sesión persistente

    def _request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Hace POST request a endpoint de Ollama."""
        url = f"{self.config.base_url}{endpoint}"
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )

        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8') if e.fp else str(e)
            raise RuntimeError(f"Ollama HTTP {e.code}: {body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Ollama conexión fallida: {e.reason}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Ollama respuesta inválida: {e}")

    def generate(self, prompt: str, stream: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Generación simple (completion).
        """
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "top_p": kwargs.get("top_p", self.config.top_p),
                "num_predict": kwargs.get("num_predict", self.config.num_predict),
                "stop": kwargs.get("stop", self.config.stop),
            }
        }
        return self._request("/api/generate", payload)

    def chat(self, messages: List[Dict[str, str]], stream: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Chat con historial de mensajes.
        messages: [{"role": "user|assistant|system", "content": "..."}]
        """
        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "top_p": kwargs.get("top_p", self.config.top_p),
                "num_predict": kwargs.get("num_predict", self.config.num_predict),
                "stop": kwargs.get("stop", self.config.stop),
            }
        }
        return self._request("/api/chat", payload)

    def generate_stream(self, prompt: str, **kwargs) -> Generator[str, None, None]:
        """Generación streaming - yields chunks de texto."""
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": kwargs.get("temperature", self.config.temperature),
                "top_p": kwargs.get("top_p", self.config.top_p),
                "num_predict": kwargs.get("num_predict", self.config.num_predict),
                "stop": kwargs.get("stop", self.config.stop),
            }
        }
        url = f"{self.config.base_url}/api/generate"
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                for line in resp:
                    if line:
                        try:
                            chunk = json.loads(line.decode('utf-8'))
                            if "response" in chunk:
                                yield chunk["response"]
                            if chunk.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
        except urllib.error.URLError as e:
            raise RuntimeError(f"Ollama streaming falló: {e.reason}")

    def health_check(self) -> bool:
        """Verifica que Ollama esté respondiendo y el modelo cargado."""
        try:
            with urllib.request.urlopen(f"{self.config.base_url}/api/tags", timeout=5) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                models = [m["name"] for m in data.get("models", [])]
                return self.config.model in models
        except Exception:
            return False

    def pull_model(self, model_name: str = None) -> bool:
        """Descarga un modelo (bloqueante)."""
        model = model_name or self.config.model
        payload = {"name": model, "stream": False}
        try:
            result = self._request("/api/pull", payload)
            return result.get("status") == "success"
        except Exception as e:
            print(f"Error descargando modelo: {e}")
            return False


def get_default_client() -> OllamaClient:
    """Factory para cliente con configuración por defecto."""
    return OllamaClient(LLMConfig())


if __name__ == "__main__":
    # Test rápido
    client = get_default_client()
    print("Health check:", client.health_check())

    if client.health_check():
        print("Generando test...")
        result = client.generate("Di 'ok' y nada más.")
        print("Respuesta:", result.get("response", "").strip())
    else:
        print("Ollama no disponible en localhost:11434")