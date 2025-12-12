"""
Game Metadata for Static Page Generation

Defines metadata for each browser-playable game including name, description,
controls, and category. Used by generate_pages.py to create per-game landing pages.
"""

from typing import Dict, Any

# Game metadata indexed by slug (lowercase, URL-friendly)
GAME_METADATA: Dict[str, Dict[str, Any]] = {
    # Python/BaseGame games
    "balloonpop": {
        "name": "Balloon Pop",
        "description": "Pop colorful balloons before they float away! A fast-paced arcade game that tests your reflexes.",
        "controls": "Click or tap balloons to pop them",
        "category": "arcade",
        "registry_name": "BalloonPop",
    },
    "containment": {
        "name": "Containment",
        "description": "Place deflectors strategically to contain a bouncing ball. An adversarial geometry puzzle.",
        "controls": "Click to place deflectors and block escape routes",
        "category": "puzzle",
        "registry_name": "Containment",
    },
    "duckhunt": {
        "name": "Duck Hunt",
        "description": "Classic shooting gallery with ducks flying across the screen. Multiple game modes available.",
        "controls": "Click to shoot ducks before they escape",
        "category": "arcade",
        "registry_name": "DuckHunt",
    },
    "fruitslice": {
        "name": "Fruit Slice",
        "description": "Slice fruits as they arc across the screen. Build combos but avoid the bombs!",
        "controls": "Swipe through fruits to slice them",
        "category": "arcade",
        "registry_name": "FruitSlice",
    },
    "gradient": {
        "name": "Gradient",
        "description": "Hit targets that appear on a gradient background. Simple and relaxing target practice.",
        "controls": "Click targets as they appear",
        "category": "practice",
        "registry_name": "Gradient",
    },
    "grouping": {
        "name": "Grouping",
        "description": "Precision training that measures your shot grouping in real-time. Consistency is key!",
        "controls": "Click to shoot - aim for tight groupings",
        "category": "training",
        "registry_name": "Grouping",
    },
    "growingtargets": {
        "name": "Growing Targets",
        "description": "Targets grow over time - hit them small for more points, or wait for an easier shot.",
        "controls": "Click targets - smaller hits score more",
        "category": "arcade",
        "registry_name": "GrowingTargets",
    },
    "loveometer": {
        "name": "Love-O-Meter",
        "description": "A fun party game that measures your aim with a love-themed twist.",
        "controls": "Click the target to test your aim",
        "category": "party",
        "registry_name": "LoveOMeter",
    },
    "manytargets": {
        "name": "Many Targets",
        "description": "Simple target shooting with multiple targets on screen. Great for practice.",
        "controls": "Click targets to hit them",
        "category": "practice",
        "registry_name": "ManyTargets",
    },
    # YAML/GameEngine games (NG = Next Generation)
    "brickbreaker": {
        "name": "Brick Breaker",
        "description": "Classic brick breaker with Lua-driven behaviors. Break all the bricks to win!",
        "controls": "Move paddle with mouse, click to launch ball",
        "category": "arcade",
        "registry_name": "BrickBreakerNG",
        "yaml_game": True,
    },
    "loveometerng": {
        "name": "Love-O-Meter NG",
        "description": "Next-generation Love-O-Meter with YAML-defined gameplay.",
        "controls": "Click the target to test your aim",
        "category": "party",
        "registry_name": "LoveOMeterNG",
        "yaml_game": True,
    },
}

# Categories for grouping games in the selector
CATEGORIES = {
    "arcade": {"name": "Arcade", "description": "Fast-paced action games"},
    "puzzle": {"name": "Puzzle", "description": "Strategic thinking games"},
    "training": {"name": "Training", "description": "Improve your skills"},
    "practice": {"name": "Practice", "description": "Simple target practice"},
    "party": {"name": "Party", "description": "Fun games for groups"},
}


def get_games_by_category() -> Dict[str, list]:
    """Group games by their category."""
    by_category: Dict[str, list] = {}
    for slug, meta in GAME_METADATA.items():
        cat = meta.get("category", "other")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append({"slug": slug, **meta})
    return by_category


def get_all_games() -> list:
    """Get all games as a flat list with slugs included."""
    return [{"slug": slug, **meta} for slug, meta in GAME_METADATA.items()]
