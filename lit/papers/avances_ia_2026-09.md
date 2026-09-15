# Pandora — avances IA septiembre 2026 (verificados)

Ventana: últimas ~6 semanas (agosto-septiembre 2026). 34 consultas web verificadas
por el swarm (2026-09-15). Fuente por ítem. Relevancia para Pandora en cursiva.

## 1. Modelos open-source / gateway / providers gratuitos

1. **GLM-5.3 y GLM-5.3-Flash** (Z.ai, 14 y 26 ago 2026) — Flash: multimodal nativo,
   MoE 320B-A18B, 1M de contexto, pesos MIT, atención híbrida sparse+lineal.
   Fuente: openrouter.ai/z-ai/glm-5.3-flash. *Candidato a modelo residente por
   ventana de 1M + pesos abiertos (es el modelo que corre Nexus).*
2. **DeepSeek-V4.1-Flash** (GA 10 sep 2026) — encoder-decoder causal, 552B MoE,
   1M de contexto, visión nativa; V4 Pro pasa a precio Flash desde el 14 sep.
   Fuente: api-docs.deepseek.com/updates/. *Opción barata de alta capacidad para
   sesiones largas del residente.*
3. **Qwen3.8-27B** (Alibaba, 14 ago 2026) y Qwen3.8-Flash-Next (26 ago) — 27.78B
   denso, Apache-2.0, visión, 262K contexto, corre en una GPU de consumidor (~16GB
   a 4-bit); Flash-Next guarda tabla N-gram de 51B en RAM.
   Fuente: typilot.com/blog/qwen3-8-27b-run-locally. *Modelo local de respaldo sin
   dependencia de cloud.*
4. **Kimi K3 + Cognition SWE-2** (10-12 sep 2026) — K3: 2.8T parámetros, pesos
   abiertos (27 jul), el mayor open-weight; SWE-2 = post-entrenamiento RL sobre K3,
   50.0% en FrontierCode 1.1, gratis en Devin hasta el 10 oct.
   Fuente: cognition.com/blog/swe-2. *Post-entrenar bases abiertas gigantes ya es
   vía de especialización cognitiva.*
5. **Providers gratuitos OpenAI-compatible** (sep 2026) — NVIDIA NIM: GLM-5.2 y
   Kimi K3 gratis con cuenta developer (~40 RPM); OpenRouter: ~19-20 modelos :free;
   Cloudflare Workers AI añadió Qwen3.8-27B (17 ago).
   Fuente: build.nvidia.com, freellm.net. *Abarata el gateway de Pandora con
   fallbacks gratuitos.*

## 2. Agentes autónomos residentes / larga vida

6. **xAI Grok Bot** (11 ago 2026) — agentes "always-on" como compañeros duraderos:
   cada Bot corre en cloud computer persistente con navegador, filesystem y
   terminal, más rutinas, skills y aprobaciones. Fuente: odivend.com/blog/durable-ai-agents-checklist.
   *Validación de mercado del patrón exacto del modo residente de Pandora (daemon
   + cuerpo persistente).*
7. **MutMem-V2** (arXiv 2609.01235, 2 sep 2026) — mutación criptográficamente
   autorizada sobre un motor de memoria persistente de agentes: conserva contenido
   y registra evidencia firmada de resultados, con contrato de verificación portable.
   Fuente: arxiv.org/abs/2609.01235. *Base para una memoria auto-mejorable y
   auditable (SGM): la evidencia firmada es el LIBRO_DE_CAMPO formalizado.*
8. **Graphiti v0.30.0 + MCP server v1.1.0** (8 sep 2026) — grafo de conocimiento
   temporal con ventana de validez por hecho ("válido desde/hasta"), retrieval
   híbrido, backends Neo4j/FalkorDB. Fuente: github.com/getzep/graphiti.
   *Patrón bi-temporal para la memoria de grafo: hechos que CADUCAN en vez de
   sobrescribirse — análogo del envejecer()/olvido final del fondo memorial.*
9. **MemU** (NevaMind, memu-py en PyPI) — memoria agéntica open-source para
   agentes proactivos 24/7: destila skills reutilizables del historial y mantiene
   memoria compartida entre sesiones/agentes/dispositivos. Fuente: memu.help.
   *Patrón de auto-mejora por destilación de skills, igual al lazo self-improving.*

## 3. Arquitecturas no-transformer para memoria

10. **Mamba-3** (state-spaces/mamba, code release reciente) — recurrencia expresiva
    multi-input/multi-output, compite con transformers con O(n) y estado fijo.
    Fuente: github.com/state-spaces/mamba/releases. Contexto: NVIDIA Nemotron 3
    Ultra (550B-A55B) valida la vía híbrida Mamba-Transformer para razonamiento
    agéntico (research.nvidia.com/labs/nemotron). *Candidato a sustrato de memoria
    secuencial comprimida con estado constante para el núcleo cognitivo.*

## Sin novedades verificables en la ventana

- **VSA/hyperdimensional computing**: solo material de fondo (Hillock en
  everydev.ai, Hyperdimensional Probe) sin release fechado en las últimas 6
  semanas. No se afirma avance nuevo ahí. (Los papers VSA de 2026 están en
  `arxiv_pandora_2026-09.md`, ventana de 6 meses.)
