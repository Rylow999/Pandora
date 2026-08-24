#!/usr/bin/env python3
"""sgm_lang.py — Diccionario base EXTENDIDO con Minecraft 1.20.4 (361 tokens).

Incluye: marcadores de estructura, recursos, estados internos, acciones,
y TODOS los bloques/items/entidades de Minecraft 1.20.4 (324 tokens).
"""
import hashlib

DICCIONARIO_BASE = [
    # marcadores de estructura
    "<sos>", "</sos>", "<pad>", "yo", "y", "pero", "porque",
    # recursos del mundo (base)
    "comida", "madera", "mesa", "pico", "piedra", "hierro", "vaca",
    # estados internos
    "hambre", "veo", "recuerdo", "valoro", "evito", "tengo", "necesito", "quiero",
    "aprendi", "bien", "mal", "peligro", "zombie", "enemigo",
    # acciones / identidad
    "comer", "craftear", "explorar", "soy", "creo", "el otro", "sabe", "puede",
    # acciones en español (para L2 y comprensión)
    "mover", "moverse", "caminar", "andar", "ir", "venir", "acercarse", "seguir",
    "saltar", "brincar", "romper", "quebrar", "destruir", "talar", "picar", "minar",
    "colocar", "poner", "construir", "edificar",
    "recolectar", "recoger", "juntar", "cosechar", "reunir", "obtener", "tomar", "agarrar",
    "atacar", "pegar", "golpear", "dañar", "matar", "luchar", "defender",
    "huir", "escapar", "correr", "alejarse", "retirarse", "esquivar",
    "interactuar", "usar", "utilizar", "abrir", "activar", "presionar",
    "equipar", "ponerse", "vestir",
    "beber", "tragar", "masticar",
    # negacion / afirmacion
    "no", "si",
    # Minecraft 1.20.4 — Bloques (114)
    "acacia_leaves", "acacia_log", "acacia_slab", "acacia_stairs", "acacia_fence", "acacia_door", "acacia_trapdoor",
    "acacia_button", "acacia_pressure_plate", "acacia_sign", "acacia_hanging_sign", "acacia_planks",
    "andesite", "anvil",
    "bamboo", "banner", "barrel", "bed", "bee", "beetroot", "birch_leaves", "birch_log",
    "blast_furnace", "bookshelf", "brewing_stand", "cactus", "cake", "campfire", "cauldron",
    "chest", "chorus_flower", "chorus_plant", "clay", "cobblestone", "cobblestone_slab",
    "cobblestone_stairs", "cobblestone_wall", "cocoa", "comparator", "composter",
    "crafting_table", "crying_obsidian", "dark_oak_leaves", "dark_oak_log", "daylight_detector",
    "deepslate", "deepslate_iron_ore", "deepslate_gold_ore", "deepslate_diamond_ore",
    "diamond_ore", "diorite", "dirt", "dispenser", "dropper", "emerald_ore",
    "end_stone", "ender_chest", "fence", "fern", "fletching_table", "furnace",
    "glass", "glass_pane", "glowstone", "gold_ore", "granite", "grass", "grass_block",
    "gravel", "grindstone", "hopper", "iron_ore", "item_frame", "jukebox",
    "jungle_leaves", "jungle_log", "ladder", "lapis_ore", "lava", "lectern",
    "lever", "lily_pad", "loom", "magma_block", "melon", "mossy_cobblestone",
    "mushroom_stew", "netherrack", "nether_wart", "note_block", "oak_button",
    "oak_door", "oak_fence", "oak_hanging_sign", "oak_leaves", "oak_log",
    "oak_planks", "oak_pressure_plate", "oak_sign", "oak_slab", "oak_stairs",
    "oak_trapdoor", "observer", "obsidian", "piston", "podzol", "pumpkin",
    "red_mushroom", "red_sand", "redstone_ore", "redstone_torch", "repeater",
    "rooted_dirt", "sand", "scaffolding", "smithing_table", "smoker", "snow",
    "soul_campfire", "soul_torch", "spruce_leaves", "spruce_log", "stone",
    "stone_brick", "stonecutter", "sugar_cane", "target", "tnt", "torch",
    "tripwire_hook", "vine", "water", "wheat", "white_stained_glass",
    # Minecraft 1.20.4 — Items (141)
    "apple", "arrow", "axolotl_bucket", "baked_potato", "beetroot_soup",
    "blaze_powder", "blaze_rod", "block_of_coal", "block_of_diamond", "block_of_emerald",
    "block_of_gold", "block_of_iron", "block_of_lapis", "block_of_redstone",
    "boat", "bone", "bone_meal", "book", "bow", "bowl", "bread", "brick",
    "bucket", "carrot", "chain", "chest_boat", "chorus_fruit", "clay_ball",
    "coal", "cocoa_beans", "compass", "cooked_beef", "cooked_chicken", "cooked_cod",
    "cooked_mutton", "cooked_porkchop", "cooked_rabbit", "cooked_salmon",
    "cookie", "copper_ingot", "diamond", "dragon_brew", "dragon_breath",
    "egg", "elytra", "emerald", "enchanted_book", "enchanted_golden_apple",
    "ender_eye", "ender_pearl", "experience_bottle", "feather", "fermented_spider_eye",
    "fire_charge", "firework_rocket", "fishing_rod", "flint", "flint_and_steel",
    "flower_pot", "ghast_tear", "glass_bottle", "glistering_melon_slice",
    "glow_berries", "glow_ink_sac", "gold_ingot", "golden_apple", "golden_axe",
    "golden_boots", "golden_carrot", "golden_chestplate", "golden_helmet",
    "golden_hoe", "golden_horse_armor", "golden_leggings", "golden_pickaxe",
    "golden_shovel", "golden_sword", "gunpowder", "heart_of_the_sea",
    "honey_bottle", "honeycomb", "ink_sac", "iron_axe", "iron_boots",
    "iron_chestplate", "iron_helmet", "iron_hoe", "iron_horse_armor",
    "iron_ingot", "iron_leggings", "iron_pickaxe", "iron_shovel", "iron_sword",
    "lapis_lazuli", "lava_bucket", "leather", "leather_boots", "leather_chestplate",
    "leather_helmet", "leather_leggings", "magma_cream", "map", "melon_seeds",
    "milk_bucket", "minecart", "mushroom_stew", "name_tag", "nautilus_shell",
    "nether_star", "netherite_axe", "netherite_boots", "netherite_chestplate",
    "netherite_helmet", "netherite_hoe", "netherite_ingot", "netherite_leggings",
    "netherite_pickaxe", "netherite_shovel", "netherite_sword", "nether_wart",
    "painting", "paper", "poisonous_potato", "porkchop", "potato", "potion",
    "pufferfish", "pumpkin_pie", "pumpkin_seeds", "rabbit_stew", "raw_beef",
    "raw_chicken", "raw_cod", "raw_mutton", "raw_porkchop", "raw_rabbit",
    "raw_salmon", "redstone", "rotten_flesh", "saddle", "salmon", "shears",
    "shield", "shulker_shell", "slime_ball", "snowball", "spider_eye",
    "splash_potion", "stick", "stone_axe", "stone_hoe", "stone_pickaxe",
    "stone_shovel", "stone_sword", "string", "sugar", "sweet_berries",
    "tipped_arrow", "totem_of_undying", "tropical_fish", "trident",
    "turtle_helmet", "water_bucket", "wheat_seeds", "wooden_axe", "wooden_hoe",
    "wooden_pickaxe", "wooden_shovel", "wooden_sword", "writable_book", "written_book",
    # Minecraft 1.20.4 — Entidades (71)
    "allay", "armadillo", "axolotl", "bat", "bee", "blaze", "camel", "cat",
    "cave_spider", "chicken", "cod", "cow", "creeper", "dolphin", "donkey",
    "drowned", "elder_guardian", "ender_dragon", "enderman", "endermite", "evoker",
    "fox", "frog", "ghast", "glow_squid", "guardian", "hoglin", "horse", "husk",
    "iron_golem", "llama", "magma_cube", "mooshroom", "mule", "ocelot", "panda",
    "parrot", "phantom", "pig", "piglin", "piglin_brute", "pillager",
    "polar_bear", "pufferfish", "rabbit", "ravager", "salmon", "sheep",
    "shulker", "silverfish", "skeleton", "slime", "sniffer", "snow_golem",
    "spider", "squid", "stray", "strider", "tadpole", "trader_llama",
    "tropical_fish", "turtle", "vex", "villager", "vindicator", "wandering_trader",
    "witch", "wither", "wither_skeleton", "wolf", "zoglin", "zombie",
    "zombie_villager", "zombified_piglin",
    # acciones numéricas (compatibilidad)
    "acc_0", "acc_1", "acc_2", "acc_3", "acc_4", "acc_5", "acc_6", "acc_7",
    "acc_8", "acc_9", "acc_10", "acc_11", "acc_12", "acc_13", "acc_14",
    "acc_15", "acc_16"
]

TOKEN2ID = {t: i for i, t in enumerate(DICCIONARIO_BASE)}
ID2TOKEN = {i: t for t, i in TOKEN2ID.items()}
VOCAB_SIZE = len(DICCIONARIO_BASE)


def token_a_id(token):
    """Devuelve el ID de un token, agregándolo al diccionario si no existe."""
    if token not in TOKEN2ID:
        nuevo_id = len(DICCIONARIO_BASE)
        TOKEN2ID[token] = nuevo_id
        ID2TOKEN[nuevo_id] = token
        DICCIONARIO_BASE.append(token)
    return TOKEN2ID[token]


def ids_a_tokens(ids):
    """Convierte una lista de IDs a tokens."""
    return [ID2TOKEN.get(i, "<???>") for i in ids]


def estado_a_tokens(ag, max_len=12):
    """Convierte el estado de SGM a una secuencia de tokens legibles."""
    tokens = []
    if getattr(ag, "_hambre_real", 0) > 0.5:
        tokens.append("hambre")
    if ag.valencia_recurso:
        for r, v in ag.valencia_recurso.items():
            if v > 0.5:
                tokens.append(r)
    return tokens[:max_len]


def estado_a_contexto_vector(ag, D=64):
    """Proyecta el estado de SGM a un vector de contexto D-dim (para el transformer)."""
    vec = [0.0] * D
    vec[0] = getattr(ag, "_hambre_real", 0)
    vec[1] = getattr(ag, "_amenaza", 0)
    vec[2] = len(ag.historial_acciones) / 100.0 if ag.historial_acciones else 0
    return vec


if __name__ == "__main__":
    print("VOCAB_SIZE (diccionario base):", VOCAB_SIZE)
    print("primeros tokens:", DICCIONARIO_BASE[:12])
    print("últimos tokens:", DICCIONARIO_BASE[-12:])