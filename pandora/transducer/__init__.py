# -*- coding: utf-8 -*-
"""pandora/transducer — El transductor bidireccional (oídos + boca).

El LLM traduce en ambas direcciones SIN originar estado mental (ACTA P1):
- oídos: SemanticParser (español → constelaciones).
- boca: OutputTransducer (constelaciones → español), con opacity + inefabilidad.
- cliente NIM para la voz rica (en vez del qwen2.5:0.5b limitado por RAM).
"""
from pandora.transducer.nim_client import NimClient, get_nim_client
from pandora.transducer.output_transducer import OutputTransducer, get_output_transducer

__all__ = ["NimClient", "get_nim_client", "OutputTransducer", "get_output_transducer"]