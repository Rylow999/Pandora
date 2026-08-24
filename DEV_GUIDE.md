# SGM — Guía de Desarrollo

## Estructura del Proyecto

```
SGM/
├── README.md                    # Documentación general (público)
├── DEV_GUIDE.md                 # Esta guía (desarrollo)
├── sgm_core.py                  # Motor cognitivo principal (~2250 líneas)
├── sgm-core-ref.py              # Referencia congelada v0.8-sgm-stable
├── experiments/
│   ├── sgm_pulsiones.py         # Plugins de pulsiones + Arbitro
│   ├── sgm_l2_system.py         # Decodificador L2 (Rosetta + Proyección)
│   ├── sgm_l2_decoder.py        # Decoder L2 original (bigrama)
│   ├── sgm_lang.py              # Diccionario base (487 tokens)
│   ├── sgm_lang_interfaz.py     # Interfaz de lenguaje
│   ├── sgm_lang_modelo.py       # Mini-transformer
│   ├── sgm_bridge.py            # Adaptador HTTP
│   ├── sgm_atencion.py          # Clasificador de intenciones
│   ├── sgm_mundo.py             # Diccionario del mundo MC
│   ├── sgm_metacognicion.py     # Metacognición
│   ├── sgm_crecimiento.py       # Crecimiento libre
│   ├── pandora.py               # Orquestador
│   ├── exp_SGM_*.py             # Experimentos (170+)
│   └── run_*.py                 # Scripts de ejecución
├── docs/
│   ├── Arquitectura_Pure_L2_Pandora.md  # Documento técnico principal
│   ├── SGM_ROADMAP.md           # Roadmap
│   └── ...
└── results/
    └── experiment_registry.json # Registro de experimentos
```

## Reglas de Oro

1. **Omega inmutable para conceptos**: Nunca modificar `self.omega[i]` directamente. Usar `_mutar_omega()` que respeta `es_place_cell`.
2. **Place cells mutables**: Solo los nodos-lugar (`es_place_cell=True`) pueden mutar su omega.
3. **Pulsiones independientes**: Cada pulsión es un plugin que no sabe de las demás. El Arbitro las combina.
4. **Fases del step()**: Proyección → Percepción → Arbitro → Elección → Post-acción.
5. **Tests obligatorios**: Todo cambio debe pasar `/tmp/hermes-verify-omega-l2.py`.

## Cómo agregar una nueva pulsión

1. Crear clase que herede de `Pulsion`:
```python
class PulsionMiPulsion(Pulsion):
    def __init__(self):
        super().__init__('MiPulsion', {'fuerza': 0.5})
    
    def computar(self, agente, valid_actions):
        result = {}
        # Lógica de la pulsión
        # Devolver {accion: peso_crudo}
        return result
```

2. Registrarla en `crear_arbitro_default()`:
```python
arbitro.registrar(PulsionMiPulsion())
```

3. Agregar factores en el Arbitro (modos BASE y SUPERVIVENCIA):
```python
self.modos['BASE']['MiPulsion'] = 1.0
self.modos['SUPERVIVENCIA']['MiPulsion'] = 0.5
```

## Cómo entrenar L2

```bash
python3 /tmp/entrenar_l2.py
```

El script:
- Genera corpus desde la Piedra Rosetta
- Entrena W con SGD + cross-entropy
- Guarda en `experiments/l2_projection.npz`

## Cómo verificar

```bash
python3 /tmp/hermes-verify-omega-l2.py
```

Tests:
- Omega mutabilidad (place cells sí, conceptos no)
- Piedra Rosetta (L1)
- L2 Decoder (proyección)
- Campo de interferencia
- DecodeL2 completo

## Cómo integrar un nuevo entorno

1. Crear adaptador que:
   - Reciba percepciones del entorno
   - Las convierta a `state_semantic` (18 dims)
   - Configure señales internas (`_hambre_real`, `_amenaza`, etc.)
   - Llame a `ag.step(sv, valid_actions)`
   - Mapee la acción resultante a comandos del entorno

2. Ejemplo de state_semantic (18 dimensiones):
```python
sv = [
    x / 50.0,       # posición X normalizada
    z / 50.0,       # posición Z normalizada
    hambre,          # 0-1
    peligro,         # 0-1
    recurso,         # 0-1
    health / 20.0,   # salud normalizada
    food / 20.0,     # comida normalizada
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0  # padding
]
```

## Puntos de Extensión

| Componente | Archivo | Cómo extender |
|-----------|---------|---------------|
| Pulsiones | `sgm_pulsiones.py` | Nueva clase + registrar en Arbitro |
| Decodificador | `sgm_l2_system.py` | Entrenar con nuevo corpus |
| Diccionario | `sgm_lang.py` | Agregar tokens al DICCIONARIO_BASE |
| Instintos | `sgm_core.py` | Modificar parámetros en `__init__` |
| Experimentos | `experiments/exp_SGM_*.py` | Nuevo script con registry |

## Debugging

### Ver estado del agente
```python
print(f'Nodos: {len(ag.omega)}')
print(f'Modo: {ag.modo}')
print(f'V_grafo: {ag.V_grafo:.3f}')
print(f'Place cells: {sum(1 for x in ag.es_place_cell if x)}')
print(f'Interferencia: {ag.incertidumbre_acum:.2f}')
```

### Ver pulsiones activas
```python
from sgm_pulsiones import crear_arbitro_default
arbitro = crear_arbitro_default()
for p in arbitro.pulsiones:
    vector = p.computar(ag, list(range(17)))
    if vector:
        print(f'{p.nombre}: {vector}')
```

### Ver campo de interferencia
```python
from sgm_l2_system import CampoInterferencia
campo = CampoInterferencia(ag)
zona = campo.computar()
for nodo_id, omega, I in zona[:5]:
    print(f'  Nodo {nodo_id}: I={I:.3f}')
```

## Tags de Versión

- `v0.8-sgm-stable`: Core limpio y verificado (2250 líneas)
- `v0.9-pulsiones`: Arbitro de Pulsiones integrado
- `v1.0-l2`: Sistema L2 completo (Rosetta + Proyección)

## Commits Importantes

| Commit | Descripción |
|--------|-------------|
| `edd26b1` | Core limpio, sin referencias a Crafter |
| `1eddd3d` | Omega mutable solo para place cells |
| `de4d414` | Arbitro de Pulsiones (10 plugins) |
| `02e31f7` | Sistema L2 completo |
| `8a35836` | Estado completo antes de adaptación MC |

---

*Última actualización: 2026-08-24*