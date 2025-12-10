# ArcheryGame – Arcade joy for everyone, everywhere

A complete, free, and open platform that brings real arcade magic back and makes it even better – without the downsides of modern gaming.

You can play these games with:
- a mouse (for testing)
- a laser pointer
- real arrows, darts, nerf balls, bean bags, or anything you can throw at a wall
- your finger on a phone or tablet

The same game runs identically on a 30-foot projected wall, in a browser, or on a laptop in a classroom.  
One file. Zero installs for players. Zero dark patterns. Zero pay-to-win.

## The mission
Modern games train thumbs and dopamine loops.
I wanted my kids to grow up with games that train:

- hand-eye coordination that translates to real life
- spatial reasoning and timing you can feel in your muscles
- proprioception and bilateral coordination
- the pure neuroplastic rocket fuel that only comes from physical cause → visible effect in the same half-second

So I built a system where the duck dies because the arrow you shot actually hit it in the real world, at the exact moment your brain predicted it would.
That’s not nostalgia.
That’s brain-building in its most fun possible form.
Every game on this platform is engineered from the ground up to be creatable by children (drag-and-drop (coming) → YAML → optional tiny safe Lua), instantly playable in a browser, and magically accurate when you play it with real projectiles on a real wall or archery target.
From bedroom screen to 30-foot projected wall with real arrows – no changes.

I also wanted kids to be able to make games themselves.  
So everything is designed from the ground up to be creatable and understandable by those who have never written code.

The result is a platform where:
- Making a complete, polished arcade game is as easy as editing a short text file (YAML)
- Learning a little coding (Lua) is optional, never required, and always safe to share
- Every game you make instantly works in the browser and on real physical installations
- Sharing is just sending a link or a text file
- Schools, makerspaces, museums, and families get it forever for free
- Commercial arcades and venues pay a fair price so the project stays alive and keeps getting better for everyone

## What’s inside right now

- A rock-solid data-driven 2D arcade engine (pure YAML + optional tiny Lua scripts)
- Full browser deployment via pygame-wasm / pygbag (playable right now)
- AMS – the physical-input layer that turns projectors + cameras into interactive walls
- DuckHunt, Brick Breaker, Balloon Pop, and more – all running with real arrows or in your browser
- Temporal hit compensation (computer vision pipeline has latency? the duck still gets hit at the right moment)

## Try it right now

(Links coming the second the first live web demo is up – literally days away)

In the meantime:  
`git clone https://github.com/timonorawski/ArcheryGame`  
`python ams_game.py --game brickbreaker --backend mouse`  
or just wait for the browser version and play with your finger.

Made with love by one dad who got fed up, for his kids and for yours.

Welcome to your arcade renaissance.

## Features for techies

- **3 Detection Backends**: Mouse (testing), laser pointer, object detection
- **Geometric Calibration**: ArUco marker-based camera-projector alignment
- **Temporal Hit Detection**: Handles cv detection latency automatically
- **Duck Hunt Game**: Full implementation with multiple modes
- **Extensible Architecture**: Easy to add new games and detection methods

## Hardware Setup

- Projector (any resolution)
- Webcam or USB camera
- Flat projection surface
- Optional: Laser pointer or colorful projectiles

## Documentation

- See `docs/AMS_ARCHITECTURE.md` for architecture overview
- See `docs/guides/` for setup guides
- See `docs/history/` for design rationale

## Project Structure

```
├── ams/              # Core detection and calibration
├── calibration/      # ArUco-based geometric calibration
├── models/           # Pydantic data models
├── games/            # Game implementations
│   ├── base/         # Simple targets example
│   └── DuckHunt/     # Full Duck Hunt game
├── docs/             # Documentation
└── ams_game.py       # Main entry point
```

## License

CC-BY-NC-SA 4.0 with a heart:

You can use, modify, and share this freely for non-commercial purposes
(personal use, schools, non-profits, publicly subsidized daycares, makerspaces, art projects, ...).

If you're a business making money with it (installations, arcades, events, etc.),
don't be a jerk—just reach out and we'll figure out a fair contribution
or a simple commercial license. No gotchas, no NDAs, no 50-page contracts.

In short: be cool, share alike, and if you're getting paid, help keep it alive and make it better for everyone.

https://creativecommons.org/licenses/by-nc-sa/4.0/
