/**
 * WASMOON Bridge for AMS Browser Games
 *
 * This module provides Lua 5.4 execution in the browser via WASMOON.
 * It communicates with Python (pygbag) via postMessage to execute
 * Lua behaviors and return state changes.
 *
 * Architecture:
 *   Python sends 'lua_*' messages -> wasmoonBridge processes them
 *   wasmoonBridge executes Lua with entity snapshot
 *   wasmoonBridge sends results back via 'lua_*_result' messages
 *
 * !! IMPORTANT - WASMOON GOTCHAS !!
 *
 * 1. NEVER call Lua functions directly from JavaScript! This causes:
 *      "TypeError: Cannot read properties of null (reading 'then')"
 *
 *    BAD:  behavior.on_update(entityId, dt)
 *    BAD:  action.execute(a, b, modifier)
 *    BAD:  typeof result.on_update === 'function'
 *
 *    GOOD: luaEngine.doString(`${globalName}.on_update("${entityId}", ${dt})`)
 *    GOOD: luaEngine.doString(`${globalName}.execute("${a}", "${b}", ${modifierLua})`)
 *
 *    Store Lua tables via global.get() for existence checks only, not property access.
 *
 * 2. Not all behaviors have all hooks! Check for nil before calling:
 *
 *    BAD:  luaEngine.doString(`${globalName}.on_update(...)`)
 *    GOOD: luaEngine.doString(`if ${globalName}.on_update then ${globalName}.on_update(...) end`)
 */

(function() {
    'use strict';

    // Global state
    let luaEngine = null;
    let luaReady = false;
    let subroutines = {
        behavior: {},
        collision_action: {},
        generator: {},
        input_action: {}
    };

    // Queue for subroutines sent before WASMOON is ready
    let pendingSubroutines = [];

    // Game state snapshot (updated each frame from Python)
    let gameState = {
        screenWidth: 800,
        screenHeight: 600,
        score: 0,
        elapsedTime: 0,
        entities: {}
    };

    // State changes to send back to Python
    let stateChanges = {
        entities: {},
        spawns: [],
        sounds: [],
        scheduled: [],
        score: 0
    };

    // Response queue for Python to poll
    window.luaResponses = window.luaResponses || [];

    /**
     * Load WASMOON library dynamically
     */
    async function loadWasmoonLibrary() {
        // Check if already loaded
        if (typeof LuaFactory !== 'undefined') {
            return true;
        }

        console.log('[WASMOON] Loading library from jsdelivr...');

        return new Promise((resolve, reject) => {
            // Use dynamic import for ES module
            const script = document.createElement('script');
            script.type = 'module';
            script.textContent = `
                import wasmoon from 'https://cdn.jsdelivr.net/npm/wasmoon@1.16.0/+esm';
                window.LuaFactory = wasmoon.LuaFactory;
                window.wasmoonLoaded = true;
                console.log('[WASMOON] Library loaded via jsdelivr ESM');
            `;
            script.onerror = (e) => reject(e);
            document.head.appendChild(script);

            // Poll for load completion
            let attempts = 0;
            const checkLoaded = setInterval(() => {
                attempts++;
                if (window.wasmoonLoaded || typeof window.LuaFactory !== 'undefined') {
                    clearInterval(checkLoaded);
                    resolve(true);
                } else if (attempts > 50) {  // 5 seconds timeout
                    clearInterval(checkLoaded);
                    reject(new Error('WASMOON load timeout'));
                }
            }, 100);
        });
    }

    /**
     * Initialize WASMOON
     */
    async function initWasmoon() {
        if (luaEngine) return;

        console.log('[WASMOON] Initializing...');

        try {
            // Load wasmoon library if not already loaded
            await loadWasmoonLibrary();

            if (typeof LuaFactory === 'undefined') {
                console.error('[WASMOON] LuaFactory not found after load attempt.');
                return;
            }

            const factory = new LuaFactory();
            luaEngine = await factory.createEngine();

            // Apply sandbox
            applySandbox();

            // Register ams.* API
            registerAmsApi();

            luaReady = true;
            console.log('[WASMOON] Ready');

            // Process any queued subroutines
            if (pendingSubroutines.length > 0) {
                console.log(`[WASMOON] Processing ${pendingSubroutines.length} queued subroutines`);
                for (const pending of pendingSubroutines) {
                    loadSubroutine(pending.subType, pending.name, pending.code);
                }
                pendingSubroutines = [];
            }

        } catch (err) {
            console.error('[WASMOON] Init error:', err);
        }
    }

    /**
     * Apply Lua sandbox (restrict dangerous functions)
     */
    function applySandbox() {
        luaEngine.doString(`
            -- Clear dangerous globals
            io = nil
            os = nil
            debug = nil
            package = nil
            require = nil
            loadfile = nil
            dofile = nil
            rawget = nil
            rawset = nil
            getmetatable = nil
            setmetatable = nil
            collectgarbage = nil
            _G = nil
            coroutine = nil

            -- Limit string functions
            string.dump = nil
        `);
    }

    /**
     * Register ams.* API functions
     */
    function registerAmsApi() {
        const ams = {};

        // Helper to get entity from current snapshot
        function getEntity(id) {
            return gameState.entities[id];
        }

        // Helper to record entity change
        function setEntityProp(id, prop, value) {
            if (!stateChanges.entities[id]) {
                stateChanges.entities[id] = {};
            }
            stateChanges.entities[id][prop] = value;

            // Also update local snapshot for subsequent calls
            const entity = gameState.entities[id];
            if (entity) {
                entity[prop] = value;
            }
        }

        // Transform API
        ams.get_x = (id) => getEntity(id)?.x ?? 0;
        ams.set_x = (id, x) => setEntityProp(id, 'x', x);
        ams.get_y = (id) => getEntity(id)?.y ?? 0;
        ams.set_y = (id, y) => setEntityProp(id, 'y', y);
        ams.get_vx = (id) => getEntity(id)?.vx ?? 0;
        ams.set_vx = (id, vx) => setEntityProp(id, 'vx', vx);
        ams.get_vy = (id) => getEntity(id)?.vy ?? 0;
        ams.set_vy = (id, vy) => setEntityProp(id, 'vy', vy);
        ams.get_width = (id) => getEntity(id)?.width ?? 0;
        ams.get_height = (id) => getEntity(id)?.height ?? 0;

        // Visual API
        ams.get_sprite = (id) => getEntity(id)?.sprite ?? '';
        ams.set_sprite = (id, s) => setEntityProp(id, 'sprite', s);
        ams.get_color = (id) => getEntity(id)?.color ?? 'white';
        ams.set_color = (id, c) => setEntityProp(id, 'color', c);
        ams.set_visible = (id, v) => setEntityProp(id, 'visible', v);

        // State API
        ams.get_health = (id) => getEntity(id)?.health ?? 0;
        ams.set_health = (id, h) => setEntityProp(id, 'health', h);
        ams.is_alive = (id) => getEntity(id)?.alive ?? false;
        ams.destroy = (id) => setEntityProp(id, 'alive', false);

        // Properties API
        ams.get_prop = (id, key) => {
            const entity = getEntity(id);
            return entity?.properties?.[key] ?? null;
        };
        ams.set_prop = (id, key, value) => {
            if (!stateChanges.entities[id]) {
                stateChanges.entities[id] = { properties: {} };
            }
            if (!stateChanges.entities[id].properties) {
                stateChanges.entities[id].properties = {};
            }
            stateChanges.entities[id].properties[key] = value;

            // Update local snapshot
            const entity = gameState.entities[id];
            if (entity && entity.properties) {
                entity.properties[key] = value;
            }
        };

        ams.get_config = (id, behavior, key, defaultValue) => {
            const entity = getEntity(id);
            const config = entity?.behavior_config?.[behavior];
            if (config && key in config) {
                return config[key];
            }
            return defaultValue ?? null;
        };

        // Query API
        ams.get_entities_of_type = (entityType) => {
            const result = [];
            for (const [id, entity] of Object.entries(gameState.entities)) {
                if (entity.alive && entity.entity_type === entityType) {
                    result.push(id);
                }
            }
            return result;
        };

        ams.get_entities_by_tag = (tag) => {
            const result = [];
            for (const [id, entity] of Object.entries(gameState.entities)) {
                if (entity.alive && entity.tags && entity.tags.includes(tag)) {
                    result.push(id);
                }
            }
            return result;
        };

        ams.count_entities_by_tag = (tag) => {
            return ams.get_entities_by_tag(tag).length;
        };

        ams.get_all_entity_ids = () => {
            return Object.keys(gameState.entities).filter(id => gameState.entities[id].alive);
        };

        // Game state API
        ams.get_screen_width = () => gameState.screenWidth;
        ams.get_screen_height = () => gameState.screenHeight;
        ams.get_score = () => stateChanges.score;
        ams.add_score = (points) => {
            stateChanges.score += points;
        };
        ams.get_time = () => gameState.elapsedTime;

        // Events API
        ams.play_sound = (soundName) => {
            stateChanges.sounds.push(soundName);
        };

        ams.schedule = (delay, callbackName, entityId) => {
            stateChanges.scheduled.push({
                delay: delay,
                callback: callbackName,
                entity_id: entityId
            });
        };

        // Spawning API
        ams.spawn = (entityType, x, y, vx, vy, width, height, color, sprite) => {
            const spawnId = `spawn_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            stateChanges.spawns.push({
                id: spawnId,
                entity_type: entityType,
                x: x ?? 0,
                y: y ?? 0,
                vx: vx ?? 0,
                vy: vy ?? 0,
                width: width ?? 0,
                height: height ?? 0,
                color: color ?? '',
                sprite: sprite ?? ''
            });
            return spawnId;
        };

        // Parent-child API
        ams.get_parent_id = (id) => getEntity(id)?.parent_id ?? '';
        ams.has_parent = (id) => !!getEntity(id)?.parent_id;
        ams.get_children = (id) => getEntity(id)?.children ?? [];

        ams.set_parent = (childId, parentId, offsetX, offsetY) => {
            setEntityProp(childId, 'parent_id', parentId);
            setEntityProp(childId, 'parent_offset', [offsetX ?? 0, offsetY ?? 0]);
        };

        ams.detach_from_parent = (id) => {
            setEntityProp(id, 'parent_id', null);
            setEntityProp(id, 'parent_offset', [0, 0]);
        };

        // Math helpers (pure JS, no roundtrip)
        ams.sin = Math.sin;
        ams.cos = Math.cos;
        ams.sqrt = Math.sqrt;
        ams.atan2 = Math.atan2;
        ams.abs = Math.abs;
        ams.min = Math.min;
        ams.max = Math.max;
        ams.floor = Math.floor;
        ams.ceil = Math.ceil;
        ams.random = Math.random;
        ams.random_range = (min, max) => min + Math.random() * (max - min);
        ams.clamp = (value, min, max) => Math.max(min, Math.min(max, value));

        // Debug
        ams.log = (msg) => console.log('[Lua]', msg);

        // Register as global
        luaEngine.global.set('ams', ams);
    }

    /**
     * Load a Lua subroutine
     */
    function loadSubroutine(subType, name, code) {
        if (!luaReady) {
            // Queue for later processing when WASMOON is ready
            console.log(`[WASMOON] Queueing ${subType}/${name} (engine not ready)`);
            pendingSubroutines.push({ subType, name, code });
            return false;
        }

        try {
            // WASMOON: doString doesn't return Lua tables directly.
            // We wrap the code to store result in a global, then retrieve it.
            const globalName = `__subroutine_${subType}_${name}`;
            const wrappedCode = `${globalName} = (function() ${code} end)()`;
            luaEngine.doString(wrappedCode);

            // Get the result from the global
            const result = luaEngine.global.get(globalName);

            if (!result) {
                console.warn(`[WASMOON] ${subType}/${name} returned nil`);
                return false;
            }

            subroutines[subType][name] = result;
            // Don't access Lua table properties directly - just confirm it loaded
            console.log(`[WASMOON] Loaded ${subType}/${name}`);
            return true;
        } catch (err) {
            console.error(`[WASMOON] Error loading ${subType}/${name}:`, err);
            return false;
        }
    }

    /**
     * Execute behavior updates for all entities
     */
    function executeBehaviorUpdates(dt, entities) {
        if (!luaReady) {
            console.log('[WASMOON] executeBehaviorUpdates: not ready yet');
            return { entities: {}, spawns: [], sounds: [], scheduled: [], score: 0 };
        }

        // Validate dt to prevent Infinity/NaN crashes
        if (!Number.isFinite(dt) || dt < 0) {
            console.warn('[WASMOON] Invalid dt:', dt, '- using 0.016');
            dt = 0.016;
        }

        // Update game state snapshot
        gameState.entities = entities;

        // Reset state changes
        stateChanges = {
            entities: {},
            spawns: [],
            sounds: [],
            scheduled: [],
            score: gameState.score
        };

        // Execute on_update for each entity's behaviors
        let behaviorsRun = 0;
        let entitiesChecked = 0;
        let entitiesWithBehaviors = 0;
        for (const [entityId, entity] of Object.entries(entities)) {
            entitiesChecked++;
            if (!entity.alive || !entity.behaviors) continue;
            entitiesWithBehaviors++;

            for (const behaviorName of entity.behaviors) {
                // Check if behavior is loaded (don't access Lua table properties directly)
                if (!subroutines.behavior[behaviorName]) {
                    if (gameState.elapsedTime < 1.0) {
                        console.log(`[WASMOON] Behavior '${behaviorName}' not found in subroutines`);
                    }
                    continue;
                }

                try {
                    // WASMOON: Call Lua functions via doString for reliability
                    // Check if global exists AND has on_update (handles async loading + missing hooks)
                    const globalName = `__subroutine_behavior_${behaviorName}`;
                    const luaCode = `local b = ${globalName}; if b and b.on_update then b.on_update("${entityId}", ${dt}) end`;
                    luaEngine.doString(luaCode);
                    behaviorsRun++;
                } catch (err) {
                    console.error(`[WASMOON] Error in ${behaviorName}.on_update:`, err);
                }
            }
        }

        // Log occasionally to verify behaviors are running
        if (gameState.elapsedTime < 1.0 || Math.floor(gameState.elapsedTime) % 5 === 0) {
            const changedCount = Object.keys(stateChanges.entities).length;
            console.log(`[WASMOON] Frame: ${entitiesChecked} entities, ${entitiesWithBehaviors} with behaviors, ${behaviorsRun} behaviors run, ${changedCount} changed`);
        }

        return stateChanges;
    }

    /**
     * Execute a collision action
     */
    function executeCollisionAction(actionName, entityA, entityB, modifier) {
        if (!luaReady) return false;

        // Check if collision action is loaded (actual function is accessed via global)
        if (!subroutines.collision_action[actionName]) {
            console.warn(`[WASMOON] Collision action not found: ${actionName}`);
            return false;
        }

        // Update entities in snapshot
        gameState.entities[entityA.id] = entityA;
        gameState.entities[entityB.id] = entityB;

        // Reset changes for this action
        stateChanges = {
            entities: {},
            spawns: [],
            sounds: [],
            scheduled: [],
            score: gameState.score
        };

        try {
            // WASMOON: Call Lua functions via doString for reliability
            // Direct JS calls to Lua table functions can have proxy issues
            const globalName = `__subroutine_collision_action_${actionName}`;

            // Convert modifier to Lua table syntax
            let modifierLua = 'nil';
            if (modifier && typeof modifier === 'object') {
                const parts = [];
                for (const [key, value] of Object.entries(modifier)) {
                    if (typeof value === 'string') {
                        parts.push(`${key}="${value}"`);
                    } else if (typeof value === 'number' || typeof value === 'boolean') {
                        parts.push(`${key}=${value}`);
                    }
                }
                modifierLua = parts.length > 0 ? `{${parts.join(', ')}}` : 'nil';
            }

            const luaCode = `local a = ${globalName}; if a and a.execute then a.execute("${entityA.id}", "${entityB.id}", ${modifierLua}) end`;
            luaEngine.doString(luaCode);
            return true;
        } catch (err) {
            console.error(`[WASMOON] Error in collision action ${actionName}:`, err);
            return false;
        }
    }

    /**
     * Handle messages from Python
     */
    function handlePythonMessage(event) {
        let msg;
        try {
            if (typeof event.data === 'string') {
                msg = JSON.parse(event.data);
            } else {
                msg = event.data;
            }
        } catch {
            return; // Not a JSON message
        }

        if (msg.source !== 'lua_engine') return;

        const { type, data } = msg;

        switch (type) {
            case 'lua_init':
                gameState.screenWidth = data.screen_width || 800;
                gameState.screenHeight = data.screen_height || 600;
                initWasmoon();
                break;

            case 'lua_load_subroutine':
                loadSubroutine(data.sub_type, data.name, data.code);
                break;

            case 'lua_update':
                gameState.elapsedTime = data.elapsed_time || 0;
                gameState.score = data.score || 0;
                // Log first few updates to verify message flow
                if (gameState.elapsedTime < 0.5) {
                    console.log('[WASMOON] lua_update received, entities:', Object.keys(data.entities || {}).length);
                }
                console.log('[WASMOON] About to call executeBehaviorUpdates, luaReady=' + luaReady);
                let results;
                try {
                    results = executeBehaviorUpdates(data.dt, data.entities);
                    console.log('[WASMOON] executeBehaviorUpdates returned:', results ? 'object' : 'null');
                } catch (err) {
                    console.error('[WASMOON] executeBehaviorUpdates ERROR:', err);
                    results = { entities: {}, spawns: [], sounds: [], scheduled: [], score: 0 };
                }

                // Send results back to Python
                window.luaResponses.push(JSON.stringify({
                    type: 'lua_update_result',
                    data: results
                }));
                break;

            case 'lua_collision':
                executeCollisionAction(
                    data.action,
                    data.entity_a,
                    data.entity_b,
                    data.modifier
                );

                // Send collision results back
                window.luaResponses.push(JSON.stringify({
                    type: 'lua_collision_result',
                    data: stateChanges
                }));
                break;

            case 'lua_set_global':
                if (luaReady) {
                    luaEngine.global.set(data.name, data.value);
                }
                break;
        }
    }

    // Listen for messages from Python
    window.addEventListener('message', handlePythonMessage);

    // Also set up for direct window access (pygbag uses this)
    window.wasmoonBridge = {
        init: initWasmoon,
        loadSubroutine,
        executeBehaviorUpdates,
        executeCollisionAction,
        isReady: () => luaReady,
        getGameState: () => gameState,
        getStateChanges: () => stateChanges
    };

    // Auto-init if WASMOON is already loaded
    if (typeof LuaFactory !== 'undefined') {
        initWasmoon();
    }

    console.log('[WASMOON Bridge] Loaded v4 - fixed doString return');

    // Signal to Python that bridge is ready
    window.wasmoonBridgeReady = true;
})();
