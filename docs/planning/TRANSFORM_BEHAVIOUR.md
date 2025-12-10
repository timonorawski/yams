# Transform Behaviour
The Transform & Behavior-as-Plugin Revolution  
How One Line of YAML Changes What Things Are

## The Final Insight

Arcade games are not made of sprites.  
They are made of **meaning**.

When you shoot a yellow asteroid and it becomes a dive-bombing alien ship that spawns two angry fragments, you didn’t just change its appearance.

You changed **what it is in the universe**.

That is the **transform** behavior — the single most powerful mechanic in AMS.

And because we refuse to hard-code meaning, we made it **data-driven and pluggable**.

## The Transform Behavior — Core Platform Feature

```yaml
on_hit:
  - transform:
      target: "alien_craft"
      behavior: "dive_attack"
      animation: "morph_explode"
      children:
        - type: "asteroid_fragment"
          velocity: [-2.0, -1.0]
        - type: "asteroid_fragment"
          velocity: [2.0, 1.0]
      points_multiplier: 3.0
      sound: "sfx/alien_scream"
```

This is not a skin swap.  
This is **ontological metamorphosis**.

The brick/asteroid/enemy ceases to be what it was and becomes something fundamentally new — with new physics, new AI, new children, new scoring, new sound.

It is the single mechanic that turns six primal games into **infinite living universes**.

### Built-in Transform Targets (shipped with AMS)

| Target Asset             | What It Becomes                     | Example Use |
|--------------------------|-------------------------------------|-----------|
| `platform_assets.duck`   | Flapping duck that flies away       | Duck Hunt remix |
| `alien_craft`            | Dive-bombing Galaga ship            | Asteroids → Galaga |
| `powerup_shield`         | Temporary player shield             | Rehab encouragement |
| `therapy_balloon`        | Balloon that bursts into confetti   | Stroke patient reward |
| `angry_fragment`         | Faster, deadlier mini-rock          | Chain-reaction hell |

All shipped. All free. All one line of YAML.

## Behavior-as-Plugin — The Last 1 %

When built-in transforms aren’t enough, the community writes a plugin.

```yaml
on_hit:
  - plugin: "behaviors/tractor_beam.py"
    strength: 0.6
    duration: 2.0
  - plugin: "behaviors/sing_happy_birthday.py"
    voice: "child"
```

### Plugin Interface (15 lines, forever stable)

```python
# behaviors/tractor_beam.py
from games.common.plugin_base import BehaviorPlugin

class TractorBeam(BehaviorPlugin):
    def __init__(self, strength=0.5, duration=2.0):
        self.strength = strength
        self.duration = duration

    def on_hit(self, brick, game):
        game.player.apply_force_toward(brick.x, brick.y, self.strength)
        game.schedule(self.duration, lambda: game.player.release_pull())

    def on_update(self, brick, game, dt):
        pass  # optional continuous effect
```

That’s it.

- 10-year-old writes `sing_happy_birthday.py`  
- Therapist writes `adaptive_slowdown.py`  
- Retro gamer writes `perfect_galaga_dive.py`

All work.  
All forever compatible.  
All one line of YAML.

## The YAML Schema — Current & Future-Proof

```yaml
entities:
  - type: brick | asteroid | alien | powerup | duck
    x: 0.5
    y: 0.3
    color: yellow
    hits_needed: 1
    descends: true
    shoots: true
    fire_rate: 3.0
    on_hit:
      - transform:
          target: "alien_craft"
          behavior: "dive_attack"
          children: [...]
      - plugin: "behaviors/custom_effect.py"
          param: value
    on_death:
      - spawn: "powerup_shield"
      - sound: "sfx/explosion"
```

### Philosophy: Meaning Belongs to the Player

| What belongs in code       | What belongs in data/plugins |
|----------------------------|------------------------------|
| The laws of physics        | What a thing becomes when shot |
| The input → event pipeline | Whether it shoots back |
| The transform system       | Whether it sings when hit |
| The plugin loader          | Whether it pulls the player |
| The six primal engines     | Whether it’s a duck or a UFO |

Code defines **how the universe works**.  
Data and plugins define **what exists in it**.

This is the final separation of concerns.

## The Result

- A child turns asteroids into ducks → uploads “Ducksteroids”
- A therapist turns bricks into balloons → “Rehab Breaker”
- A retro purist turns bricks into perfect Galaga aliens → “Galaga 1981 Remake”
- You never touch the core again

You have built the **first living arcade universe** where players don’t just play the game.

They **write its mythology**, one transform at a time.

This is not a game engine.

This is **the canvas where meaning is negotiated by shooting things**.

Ship the transform system.  
Ship the built-in assets.  
Ship the plugin spec.

Then watch the world discover that when you give people the power to change what things *are* when they shoot them…

…they will build gods.

You didn’t just make better arcade games.

You made arcade games **alive**.

**The transformation is complete.**  
Now let them play. 🦆🪐❤️🚀