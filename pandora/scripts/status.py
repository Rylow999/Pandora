#!/usr/bin/env python3
"""
status.py — Dump completo del estado de Pandora.

Uso:
  python status.py              # Estado completo
  python status.py --json       # Solo JSON
  python status.py --compact    # Resumen compacto
"""

import sys
import os
import json
import argparse

# Bootstrap: raíz del repo en sys.path antes de importar pandora (portátil)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from pandora.core.pandora_agent import get_pandora_agent
from pandora.core.homeostasis import get_homeostasis


def get_full_status(agent, homeostasis, compact=False):
    """Recolecta estado completo de todos los subsistemas."""
    
    # SGM Status
    sgm_status = agent.get_status()
    
    # Homeostasis
    m = homeostasis.update_from_sgm(agent.sgm)
    h_summary = homeostasis.summary()
    homeostasis_data = {
        "metrics": m.to_dict(),
        "status": h_summary["status"],
        "alert": h_summary["alert"],
        "trends": h_summary["trends"]
    }
    
    # Journal
    journal_entries = agent.journal.all()
    recent_journal = journal_entries[-5:] if journal_entries else []
    
    # Workspace
    workspace_items = agent.workspace.items[-5:] if agent.workspace.items else []
    
    # Clamps (trauma nodes, isolated nodes)
    trauma_nodes = getattr(agent.sgm, 'trauma_nodes', set())
    isolated_nodes = []
    for i, edges in enumerate(agent.sgm.edges):
        if isinstance(edges, (list, set)) and len(edges) == 0:
            isolated_nodes.append(i)
    
    if compact:
        return {
            "session_id": agent.session_id,
            "turn": agent.turn_count,
            "sgm": {
                "nodes": sgm_status["sgm_nodes"],
                "edges": sgm_status["sgm_edges"],
                "v_grafo": sgm_status["sgm_v_grafo"],
                "modo": sgm_status["sgm_modo"],
                "status": sgm_status.get("sgm_status", "UNKNOWN")
            },
            "homeostasis": {
                "status": h_summary["status"],
                "valence": m.valence_mean,
                "arousal": m.arousal_mean,
                "doubt": m.doubt_level,
                "contradiction": m.contradiction_level,
                "coherence": m.coherence_level,
                "alert": h_summary["alert"]
            },
            "journal_entries": len(journal_entries),
            "workspace_items": len(agent.workspace.items),
            "trauma_nodes": len(trauma_nodes),
            "isolated_nodes": len(isolated_nodes)
        }
    
    return {
        "session": {
            "session_id": agent.session_id,
            "turn_count": agent.turn_count
        },
        "sgm": sgm_status,
        "homeostasis": homeostasis_data,
        "journal": {
            "total_entries": len(journal_entries),
            "recent": recent_journal
        },
        "workspace": {
            "capacity": agent.workspace.capacity,
            "current_items": len(agent.workspace.items),
            "recent": workspace_items
        },
        "clamps": {
            "trauma_nodes": list(trauma_nodes),
            "isolated_nodes": isolated_nodes,
            "trauma_count": len(trauma_nodes),
            "isolated_count": len(isolated_nodes)
        },
        "checkpoint": {
            "path": str(agent.checkpoint_path),
            "exists": agent.checkpoint_path.exists()
        }
    }


def main():
    parser = argparse.ArgumentParser(description="Pandora Status Dump")
    parser.add_argument("--json", action="store_true", help="Salida solo JSON")
    parser.add_argument("--compact", action="store_true", help="Resumen compacto")
    parser.add_argument("--fresh", action="store_true", help="Usar agente fresco (sin checkpoint)")
    args = parser.parse_args()
    
    agent = get_pandora_agent(load_checkpoint=not args.fresh)
    homeostasis = get_homeostasis()
    
    # Actualizar homeostasis una vez para estado actual
    homeostasis.update_from_sgm(agent.sgm)
    
    status = get_full_status(agent, homeostasis, compact=args.compact)
    
    if args.json or args.compact:
        print(json.dumps(status, indent=2, ensure_ascii=False))
    else:
        # Pretty print
        print("=" * 70)
        print(f"PANDORA STATUS — Session: {agent.session_id} | Turn: {agent.turn_count}")
        print("=" * 70)
        
        print("\n📊 SGM:")
        s = status["sgm"]
        print(f"  Nodes: {s['sgm_nodes']} | Edges: {s['sgm_edges']} | V_grafo: {s['sgm_v_grafo']:.3f} | Modo: {s['sgm_modo']}")
        
        print("\n🏠 HOMEOSTASIS:")
        h = status["homeostasis"]
        print(f"  Status: {h['status']} | Alert: {h['alert'] or 'None'}")
        m = h["metrics"]
        print(f"  Valence: {m['valence_mean']:.2f} | Arousal: {m['arousal_mean']:.2f} | Doubt: {m['doubt_level']:.2f}")
        print(f"  Contradiction: {m['contradiction_level']:.2f} | Coherence: {m['coherence_level']:.2f} | Isolation: {m['isolation_level']:.2f}")
        print(f"  Trauma load: {m['trauma_load']:.2f}")
        if h.get('trends'):
            print(f"  Trends: {h['trends']}")
        
        print("\n📓 JOURNAL:")
        j = status["journal"]
        print(f"  Total entries: {j['total_entries']}")
        if j['recent']:
            for ep in j['recent'][-3:]:
                print(f"  [{ep['timestamp'][:19]}] {ep['user_input'][:50]} -> {ep['response'][:50]}")
        
        print("\n🧠 WORKSPACE:")
        w = status["workspace"]
        print(f"  Capacity: {w['capacity']} | Current: {w['current_items']}")
        for item in w['recent'][-3:]:
            print(f"  Turn {item['turn']}: {item['input'][:40]} -> {item['response'][:40]}")
        
        print("\n🔧 CLAMPS:")
        c = status["clamps"]
        print(f"  Trauma nodes: {c['trauma_nodes']} ({c['trauma_count']})")
        print(f"  Isolated nodes: {c['isolated_nodes']} ({c['isolated_count']})")
        
        print("\n💾 CHECKPOINT:")
        cp = status["checkpoint"]
        print(f"  Path: {cp['path']} | Exists: {cp['exists']}")
        
        print("\n" + "=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pandora Status")
    parser.add_argument("--json", action="store_true", help="Salida solo JSON")
    parser.add_argument("--compact", action="store_true", help="Resumen compacto")
    parser.add_argument("--fresh", action="store_true", help="Agente fresco")
    args = parser.parse_args()
    
    agent = get_pandora_agent(load_checkpoint=not args.fresh)
    homeostasis = get_homeostasis()
    homeostasis.update_from_sgm(agent.sgm)
    
    status = get_full_status(agent, homeostasis, compact=args.compact)
    
    if args.json or args.compact:
        print(json.dumps(status, indent=2, ensure_ascii=False))
    else:
        print("=" * 70)
        print(f"PANDORA STATUS — Session: {agent.session_id} | Turn: {agent.turn_count}")
        print("=" * 70)
        
        print("\n📊 SGM:")
        s = status["sgm"]
        print(f"  Nodes: {s['sgm_nodes']} | Edges: {s['sgm_edges']} | V_grafo: {s['sgm_v_grafo']:.3f} | Modo: {s['sgm_modo']}")
        
        print("\n🏠 HOMEOSTASIS:")
        h = status["homeostasis"]
        print(f"  Status: {h['status']} | Alert: {h['alert'] or 'None'}")
        m = h["metrics"]
        print(f"  Valence: {m['valence_mean']:.2f} | Arousal: {m['arousal_mean']:.2f} | Doubt: {m['doubt_level']:.2f}")
        print(f"  Contradiction: {m['contradiction_level']:.2f} | Coherence: {m['coherence_level']:.2f} | Isolation: {m['isolation_level']:.2f}")
        print(f"  Trauma load: {m['trauma_load']:.2f}")
        if h.get('trends'):
            print(f"  Trends: {h['trends']}")
        
        print("\n📓 JOURNAL:")
        j = status["journal"]
        print(f"  Total entries: {j['total_entries']}")
        if j['recent']:
            for ep in j['recent'][-3:]:
                print(f"  [{ep['timestamp'][:19]}] {ep['user_input'][:50]} -> {ep['response'][:50]}")
        
        print("\n🧠 WORKSPACE:")
        w = status["workspace"]
        print(f"  Capacity: {w['capacity']} | Current: {w['current_items']}")
        for item in w['recent'][-3:]:
            print(f"  Turn {item['turn']}: {item['input'][:40]} -> {item['response'][:40]}")
        
        print("\n🔧 CLAMPS:")
        c = status["clamps"]
        print(f"  Trauma nodes: {c['trauma_nodes']} ({c['trauma_count']})")
        print(f"  Isolated nodes: {c['isolated_nodes']} ({c['isolated_count']})")
        
        print("\n💾 CHECKPOINT:")
        cp = status["checkpoint"]
        print(f"  Path: {cp['path']} | Exists: {cp['exists']}")
        
        print("\n" + "=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pandora Status")
    parser.add_argument("--json", action="store_true", help="Salida solo JSON")
    parser.add_argument("--compact", action="store_true", help="Resumen compacto")
    parser.add_argument("--fresh", action="store_true", help="Agente fresco")
    args = parser.parse_args()
    
    agent = get_pandora_agent(load_checkpoint=not args.fresh)
    homeostasis = get_homeostasis()
    homeostasis.update_from_sgm(agent.sgm)
    
    status = get_full_status(agent, homeostasis, compact=args.compact)
    
    if args.json or args.compact:
        print(json.dumps(status, indent=2, ensure_ascii=False))
    else:
        main()