#!/usr/bin/env python3
"""Test that Pandora package imports correctly."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test all critical imports."""
    
    # Test SGM core
    print("Testing SGM core...")
    from sgm.core.sgm_core import SGMAgentCore
    print("  ✓ SGMAgentCore")
    
    from sgm.core.sgm_hdc import HDC, SensorBridge
    print("  ✓ HDC, SensorBridge")
    
    # Test Pandora config
    print("Testing Pandora config...")
    from pandora.config.schemas import (
        SemanticEvent, InternalState, Triplet, 
        Affect, Intent
    )
    print("  ✓ Core schemas")
    
    # Test Pandora transducers
    print("Testing Pandora transducers...")
    from pandora.transducer.llm_client import OllamaClient, LLMConfig
    print("  ✓ OllamaClient, LLMConfig")
    
    from pandora.transducer.articulator import Articulator, get_articulator
    print("  ✓ Articulator")
    
    from pandora.transducer.semantic_parser import SemanticParser, get_parser
    print("  ✓ SemanticParser")
    
    # Test Pandora core
    print("Testing Pandora core...")
    from pandora.core.pandora_agent import PandoraAgent, get_pandora_agent, Episode, Workspace, Journal
    print("  ✓ PandoraAgent, Episode, Workspace, Journal")
    
    from pandora.core.homeostasis import Homeostasis, get_homeostasis
    print("  ✓ Homeostasis")
    
    from pandora.core.endogenous import EndogenousEngine, get_endogenous_engine
    print("  ✓ EndogenousEngine")
    
    # Test Pandora alterity
    print("Testing Pandora alterity...")
    from pandora.alterity.opacity_gate import OpacityGate, create_opacity_gate
    print("  ✓ OpacityGate")
    
    from pandora.alterity.immune_system import CognitiveImmuneSystem, create_immune_system
    print("  ✓ CognitiveImmuneSystem")
    
    from pandora.alterity.aesthetic_drives import AestheticDrives, create_aesthetic_drives
    print("  ✓ AestheticDrives")
    
    from pandora.alterity.translation_limit import TranslationLimit, create_translation_limit
    print("  ✓ TranslationLimit")
    
    from pandora.alterity.alterity_core import AlterityAgent, create_alterity_agent
    print("  ✓ AlterityAgent")
    
    # Test ontology
    print("Testing ontology...")
    from pandora.ontology.hrr_seed import generate_all_vectors, verify_orthogonality
    print("  ✓ hrr_seed")
    
    print("\n✅ All imports successful!")

if __name__ == "__main__":
    test_imports()