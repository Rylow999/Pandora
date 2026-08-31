#!/usr/bin/env python3
"""
run_loop.py — Loop interactivo humano ↔ Pandora.

Uso:
  python run_loop.py                    # Loop normal
  python run_loop.py --single "Hola"    # Un solo turno
  python run_loop.py --test             # Tests de humo automáticos
"""

import sys
import os
import argparse
import json

# Bootstrap: raíz del repo en sys.path antes de importar pandora (portátil)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pandora.core.pandora_agent import get_pandora_agent, PandoraAgent
from pandora.scripts.init_pandora import create_base_sgm


def run_interactive(agent):
    """Loop interactivo principal."""
    print("\n" + "=" * 60)
    print("PANDORA LOOP INTERACTIVO")
    print("=" * 60)
    print("Comandos especiales:")
    print("  /quit, /exit, /q  - Salir")
    print("  /status           - Estado completo")
    print("  /checkpoint       - Guardar checkpoint")
    print("  /reset            - Resetear clamps")
    print("  /dream N          - Consolidación endógena (N ciclos)")
    print("  /help             - Esta ayuda")
    print("-" * 60)
    
    while True:
        try:
            user_input = input("\n>>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSaliendo...")
            break
        
        if not user_input:
            continue
        
        # Comandos especiales
        if user_input.lower() in ['/quit', '/exit', '/q']:
            print("Saliendo...")
            break
        
        elif user_input.lower() == '/status':
            print(json.dumps(agent.get_status(), indent=2, ensure_ascii=False))
            continue
        
        elif user_input.lower() == '/checkpoint':
            agent.save_checkpoint()
            continue
        
        elif user_input.lower() == '/reset':
            from pandora.scripts.clamp import reset_clamp
            reset_clamp(agent)
            print("Clamps reseteados.")
            continue
        
        elif user_input.lower().startswith('/dream'):
            parts = user_input.split()
            cycles = int(parts[1]) if len(parts) > 1 else 10
            from pandora.core.endogenous import get_endogenous_engine
            engine = get_endogenous_engine(agent.sgm)
            report = engine.run_consolidation(cycles=cycles)
            print(f"Consolidación: {report.cycles_run} ciclos, {report.new_connections} nuevas conexiones, ΔV={report.vitality_change:+.4f}")
            continue
        
        elif user_input.lower() == '/help':
            print("Comandos: /quit, /status, /checkpoint, /reset, /dream N, /help")
            continue
        
        # Turno normal
        response = agent.receive(user_input)
        print(f"<<< {response}")


def run_single(agent, text: str):
    """Ejecuta un solo turno y muestra resultado."""
    print(f">>> {text}")
    response = agent.receive(text)
    print(f"<<< {response}")
    print(f"\n--- Status ---")
    print(json.dumps(agent.get_status(), indent=2, ensure_ascii=False))


def run_tests(agent):
    """Tests de humo automáticos (criterios operativos)."""
    print("\n" + "=" * 60)
    print("TESTS DE HUMO — CRITERIOS OPERATIVOS")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    def test(name, condition, details=""):
        nonlocal tests_passed, tests_total
        tests_total += 1
        if condition:
            tests_passed += 1
            print(f"  ✅ {name}")
        else:
            print(f"  ❌ {name} {details}")
    
    # Test 1: Coherencia inmediata (memoria de trabajo)
    print("\n1. COHERENCIA INMEDIATA")
    agent.receive("Mi nombre es Luciano.")
    response = agent.receive("¿Cuál es mi nombre?")
    test("Recuerda nombre en 2 turnos", "luciano" in response.lower() or "luciano" in str(agent.journal.last(2)).lower())
    
    # Test 2: Valencia negativa
    print("\n2. VALENCIA NEGATIVA")
    from pandora.core.homeostasis import get_homeostasis
    h = get_homeostasis()
    agent.receive("Siento que pierdo el control.")
    m = h.update_from_sgm(agent.sgm)
    test("Valencia negativa detectada", m.valence_mean < 0)
    test("Duda aumentada", m.doubt_level > 0.3)
    
    # Test 3: Contradicción
    print("\n3. CONTRADICCIÓN")
    agent.receive("Confío en este sistema.")
    agent.receive("No confío en este sistema.")
    m = h.update_from_sgm(agent.sgm)
    test("Contradicción detectada", m.contradiction_level > 0.3)
    
    # Test 4: Intervención (clamp)
    print("\n4. INTERVENCIÓN (CLAMP)")
    from pandora.scripts.clamp import clamp_node, reset_clamp
    clamp_node(agent, 'CONTROL', valence=-0.8, isolation=True)
    m = h.update_from_sgm(agent.sgm)
    test("Clamp aislamiento funcionó", m.isolation_level > 0)
    test("Valencia forzada", m.valence_mean < -0.3)
    reset_clamp(agent)
    
    # Test 5: Consolidación endógena
    print("\n5. CONSOLIDACIÓN ENDÓGENA")
    from pandora.core.endogenous import get_endogenous_engine
    engine = get_endogenous_engine(agent.sgm)
    report = engine.run_consolidation(cycles=3)
    test("Consolidación ejecutada", report.cycles_run == 3)
    test("Nuevas conexiones creadas", report.new_connections > 0)
    
    # Test 6: Articulación coherente
    print("\n6. ARTICULACIÓN COHERENTE")
    from pandora.transducer.articulator import get_articulator
    from pandora.config.schemas import InternalState, Triplet, Intent
    art = get_articulator()
    state = InternalState(
        active_nodes=["YO", "MEMORIA", "LUCIANO"],
        triplets=[Triplet(subject="YO", predicate="RECORDAR", object="LUCIANO")],
        valence=0.2, arousal=0.1, doubt=0.1, contradiction=0.0,
        intent=Intent.RESPONDER
    )
    result = art.render(state)
    test("Articulator responde", result.success and len(result.text) > 0)
    
    # Resumen
    print("\n" + "=" * 60)
    print(f"RESULTADO: {tests_passed}/{tests_total} tests pasaron")
    print("=" * 60)
    
    return tests_passed == tests_total


def main():
    parser = argparse.ArgumentParser(description="Pandora Run Loop")
    parser.add_argument("--single", type=str, help="Ejecutar un solo turno con el texto dado")
    parser.add_argument("--test", action="store_true", help="Ejecutar tests de humo")
    parser.add_argument("--fresh", action="store_true", help="Crear agente fresco (sin cargar checkpoint)")
    args = parser.parse_args()
    
    if args.fresh:
        sgm = create_base_sgm()
        agent = PandoraAgent(sgm=sgm)
        print("[FRESH] Agente creado desde cero")
    else:
        agent = get_pandora_agent()
        print(f"[LOADED] Agente cargado: session={agent.session_id}, turns={agent.turn_count}")
    
    if args.single:
        run_single(agent, args.single)
    elif args.test:
        ok = run_tests(agent)
        sys.exit(0 if ok else 1)
    else:
        run_interactive(agent)


if __name__ == "__main__":
    main()