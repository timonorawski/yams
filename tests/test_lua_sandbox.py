"""
Lua Sandbox Security Tests

These tests verify that the Lua sandbox properly restricts access to
dangerous capabilities. If any of these tests fail, it indicates a
potential security regression.

Run with: pytest tests/test_lua_sandbox.py -v
"""

import pytest
from pathlib import Path
from lupa import LuaError

from ams.behaviors.engine import BehaviorEngine
from ams.content_fs import ContentFS


# Project root for ContentFS
_PROJECT_ROOT = Path(__file__).parent.parent


@pytest.fixture
def content_fs():
    """Create ContentFS for tests."""
    return ContentFS(_PROJECT_ROOT, add_user_layer=False)


@pytest.fixture
def engine(content_fs):
    """Create a fresh BehaviorEngine for each test."""
    return BehaviorEngine(content_fs, 800, 600)


@pytest.fixture
def lua(engine):
    """Get the Lua runtime from the engine."""
    return engine._lua


class TestBlockedGlobals:
    """Test that dangerous Lua globals are not accessible."""

    @pytest.mark.parametrize("global_name", [
        "io",
        "os",
        "debug",
        "package",
        "python",       # Lupa's Python bridge - critical to block
        "_python",      # Alternative Lupa bridge name
        "ffi",          # LuaJIT FFI
        "jit",          # LuaJIT control
        "bit",          # LuaJIT bit ops
        "bit32",        # Lua 5.2 bit ops
        "string",       # String library as global
        "table",        # Table library as global
        # Note: _ENV exists in Lua 5.2+ but is function-scoped, not a security risk
    ])
    def test_dangerous_library_is_nil(self, lua, global_name):
        """Dangerous standard libraries should be nil."""
        result = lua.eval(global_name)
        assert result is None, f"{global_name} should be nil"

    @pytest.mark.parametrize("func_name", [
        "loadfile",
        "dofile",
        "require",
        "load",
        "loadstring",
        "getmetatable",
        "setmetatable",
        "rawget",
        "rawset",
        "rawequal",
        "rawlen",
        "collectgarbage",
        "newproxy",
    ])
    def test_dangerous_function_is_nil(self, lua, func_name):
        """Dangerous functions should be nil."""
        result = lua.eval(func_name)
        assert result is None, f"{func_name} should be nil"

    def test_G_is_nil(self, lua):
        """_G (global table reference) should be nil to prevent enumeration."""
        result = lua.eval("_G")
        assert result is None, "_G should be nil"

    def test_VERSION_is_nil(self, lua):
        """_VERSION should be nil (information disclosure)."""
        result = lua.eval("_VERSION")
        assert result is None, "_VERSION should be nil"


class TestBlockedOperations:
    """Test that dangerous operations fail."""

    def test_io_open_fails(self, lua):
        """File operations should fail."""
        with pytest.raises(LuaError, match="nil value"):
            lua.execute('io.open("test.txt", "r")')

    def test_os_execute_fails(self, lua):
        """OS command execution should fail."""
        with pytest.raises(LuaError, match="nil value"):
            lua.execute('os.execute("ls")')

    def test_os_getenv_fails(self, lua):
        """Environment variable access should fail."""
        with pytest.raises(LuaError, match="nil value"):
            lua.execute('os.getenv("PATH")')

    def test_loadfile_fails(self, lua):
        """Loading files should fail."""
        with pytest.raises(LuaError, match="nil value"):
            lua.execute('loadfile("test.lua")')

    def test_dofile_fails(self, lua):
        """Executing files should fail."""
        with pytest.raises(LuaError, match="nil value"):
            lua.execute('dofile("test.lua")')

    def test_require_fails(self, lua):
        """Module loading should fail."""
        with pytest.raises(LuaError, match="nil value"):
            lua.execute('require("os")')

    def test_debug_getinfo_fails(self, lua):
        """Debug introspection should fail."""
        with pytest.raises(LuaError, match="nil value"):
            lua.execute('debug.getinfo(1)')

    def test_python_eval_fails(self, lua):
        """Python bridge should be inaccessible."""
        with pytest.raises(LuaError, match="nil value"):
            lua.execute('python.eval("__import__(\'os\').system(\'ls\')")')

    def test_python_exec_fails(self, lua):
        """Python exec should be inaccessible."""
        with pytest.raises(LuaError, match="nil value"):
            lua.execute('python.exec("import os")')


class TestMetatableAccess:
    """Test that metatable manipulation is blocked."""

    def test_getmetatable_nil(self, lua):
        """getmetatable should be nil."""
        result = lua.eval("getmetatable")
        assert result is None

    def test_setmetatable_nil(self, lua):
        """setmetatable should be nil."""
        result = lua.eval("setmetatable")
        assert result is None

    def test_cannot_get_string_metatable(self, lua):
        """Cannot access string metatable (would expose string library)."""
        with pytest.raises(LuaError, match="nil value"):
            lua.execute('getmetatable("")')

    def test_cannot_set_global_metatable(self, lua):
        """Cannot set metatables for sandbox escape."""
        with pytest.raises(LuaError, match="nil value"):
            lua.execute('setmetatable({}, {__index = function() return "escaped" end})')


class TestAttributeFilter:
    """Test that Python attribute access is filtered."""

    def test_cannot_access_dunder_class(self, lua):
        """Cannot access __class__ on Python objects."""
        # ams.get_x is a bound method - try to access its internals
        with pytest.raises((LuaError, AttributeError)):
            lua.execute('local f = ams.get_x; return f.__class__')

    def test_cannot_access_dunder_dict(self, lua):
        """Cannot access __dict__ on Python objects."""
        with pytest.raises((LuaError, AttributeError)):
            lua.execute('local f = ams.get_x; return f.__dict__')

    def test_cannot_access_dunder_self(self, lua):
        """Cannot access __self__ on bound methods."""
        with pytest.raises((LuaError, AttributeError)):
            lua.execute('local f = ams.get_x; return f.__self__')

    def test_cannot_access_private_attrs(self, lua):
        """Cannot access _private attributes."""
        with pytest.raises((LuaError, AttributeError)):
            lua.execute('local f = ams.get_x; return f._engine')

    def test_cannot_call_methods_on_leaked_objects(self, engine, lua):
        """Cannot call methods on Python objects that leak through."""
        # If a Python object somehow gets exposed to Lua, its methods
        # should be blocked by the attribute filter

        class LeakedObject:
            def __init__(self):
                self.data = "safe_data"

            def dangerous_method(self):
                return "should not be callable"

        # Inject object into Lua (simulating a leak)
        lua.globals()['leaked'] = LeakedObject()

        # Data access should work
        result = lua.eval('leaked.data')
        assert result == "safe_data"

        # Method access should be blocked
        with pytest.raises((LuaError, AttributeError)):
            lua.eval('leaked.dangerous_method')

        # Method call should be blocked
        with pytest.raises((LuaError, AttributeError)):
            lua.eval('leaked.dangerous_method()')


class TestAllowedGlobals:
    """Test that safe globals ARE available."""

    @pytest.mark.parametrize("func_name", [
        "pairs",
        "ipairs",
        "type",
        "tostring",
        "tonumber",
        "select",
        "unpack",
        "pcall",
        "error",
        "next",
        "math",
    ])
    def test_safe_function_exists(self, lua, func_name):
        """Safe Lua primitives should be available."""
        result = lua.eval(func_name)
        assert result is not None, f"{func_name} should be available"

    def test_math_library_functions(self, lua):
        """The math library should have standard functions."""
        # Test a few common math functions
        assert lua.eval("math.sin(0)") == 0
        assert lua.eval("math.cos(0)") == 1
        assert lua.eval("math.floor(3.7)") == 3
        assert lua.eval("math.ceil(3.2)") == 4
        assert lua.eval("math.abs(-5)") == 5
        assert lua.eval("math.pi") is not None

    def test_ams_namespace_exists(self, lua):
        """The ams API namespace should exist."""
        result = lua.eval("ams")
        assert result is not None, "ams namespace should exist"

    def test_local_variables_work(self, lua):
        """Local variables should work normally."""
        result = lua.eval("(function() local x = 42; return x end)()")
        assert result == 42

    def test_tables_work(self, lua):
        """Table creation and access should work."""
        lua.execute("_test_table = {a = 1, b = 2}")
        result = lua.eval("_test_table.a")
        assert result == 1

    def test_pairs_iteration_works(self, lua):
        """pairs() iteration should work."""
        lua.execute("""
            local t = {a = 1, b = 2}
            local sum = 0
            for k, v in pairs(t) do
                sum = sum + v
            end
            _test_result = sum
        """)
        result = lua.eval("_test_result")
        assert result == 3


class TestAmsApiAvailable:
    """Test that the ams.* API functions work."""

    def test_ams_random(self, lua):
        """ams.random() should return a number in [0,1)."""
        result = lua.eval("ams.random()")
        assert isinstance(result, float)
        assert 0 <= result < 1

    def test_ams_random_range(self, lua):
        """ams.random_range() should return a number in range."""
        result = lua.eval("ams.random_range(10, 20)")
        assert isinstance(result, float)
        assert 10 <= result <= 20

    def test_ams_sin_cos(self, lua):
        """ams.sin() and ams.cos() should work."""
        sin_result = lua.eval("ams.sin(0)")
        cos_result = lua.eval("ams.cos(0)")
        assert abs(sin_result - 0.0) < 0.001
        assert abs(cos_result - 1.0) < 0.001

    def test_ams_clamp(self, lua):
        """ams.clamp() should clamp values."""
        assert lua.eval("ams.clamp(5, 0, 10)") == 5
        assert lua.eval("ams.clamp(-5, 0, 10)") == 0
        assert lua.eval("ams.clamp(15, 0, 10)") == 10

    def test_ams_screen_dimensions(self, lua):
        """ams.get_screen_width/height should return dimensions."""
        width = lua.eval("ams.get_screen_width()")
        height = lua.eval("ams.get_screen_height()")
        assert width == 800
        assert height == 600

    def test_ams_entity_operations(self, engine, lua):
        """Entity operations should work through ams API."""
        # Create an entity
        entity = engine.create_entity("test", x=100, y=200, behaviors=[])

        # Access it via Lua
        x = lua.eval(f'ams.get_x("{entity.id}")')
        y = lua.eval(f'ams.get_y("{entity.id}")')
        assert x == 100
        assert y == 200

        # Modify via Lua
        lua.execute(f'ams.set_x("{entity.id}", 150)')
        assert entity.x == 150


class TestBehaviorExecution:
    """Test that behaviors execute in the sandbox correctly."""

    def test_inline_behavior_works(self, engine):
        """Inline behaviors should execute normally."""
        code = """
        local behavior = {}
        function behavior.on_spawn(entity_id)
            ams.set_prop(entity_id, "spawned", true)
        end
        function behavior.on_update(entity_id, dt)
            local x = ams.get_x(entity_id)
            ams.set_x(entity_id, x + 10 * dt)
        end
        return behavior
        """
        engine.load_inline_behavior("test_move", code)
        entity = engine.create_entity("test", x=0, y=0, behaviors=["test_move"])

        assert entity.properties.get("spawned") is True

        engine.update(1.0)  # 1 second
        assert entity.x == 10.0

    def test_behavior_cannot_escape_sandbox(self, engine):
        """Behaviors attempting sandbox escape should fail gracefully."""
        # This behavior tries to access os - should fail but not crash
        code = """
        local behavior = {}
        function behavior.on_update(entity_id, dt)
            -- This should fail silently (os is nil)
            if os then
                os.execute("echo pwned")
            end
            -- Normal operation continues
            ams.set_prop(entity_id, "updated", true)
        end
        return behavior
        """
        engine.load_inline_behavior("escape_attempt", code)
        entity = engine.create_entity("test", x=0, y=0, behaviors=["escape_attempt"])

        # Should not raise, behavior continues after failed escape
        engine.update(0.016)
        assert entity.properties.get("updated") is True


class TestEdgeCases:
    """Test edge cases and potential bypass attempts."""

    def test_cannot_reconstruct_globals_via_function_env(self, lua):
        """Cannot use function environments to access hidden globals."""
        # In older Lua, getfenv could access function environments
        result = lua.eval("getfenv")
        assert result is None

        result = lua.eval("setfenv")
        assert result is None

    def test_string_dump_blocked_via_global(self, lua):
        """string.dump via global should be blocked (string is nil)."""
        with pytest.raises(LuaError, match="nil value"):
            lua.execute('string.dump(function() end)')

    def test_string_dump_blocked_via_metatable(self, lua):
        """string.dump via method syntax should be blocked (removed from metatable)."""
        # We remove dump from the string metatable during sandbox setup
        result = lua.eval('("").dump')
        assert result is None, "string.dump should be nil in string metatable"

    def test_string_dump_cannot_serialize(self, lua):
        """Cannot actually use string.dump to serialize functions."""
        # Even accessing via method syntax, dump should be nil
        with pytest.raises(LuaError):
            lua.execute('local bytecode = ("").dump(function() end)')

    def test_string_rep_blocked(self, lua):
        """string.rep should be blocked (memory DoS risk)."""
        # string.rep("x", 2^30) could allocate gigabytes of memory
        result = lua.eval('("").rep')
        assert result is None, "string.rep should be nil"

    def test_string_rep_cannot_be_called(self, lua):
        """Cannot use string.rep via method syntax."""
        with pytest.raises(LuaError):
            lua.execute('local huge = ("x"):rep(1000)')

    def test_string_methods_safe(self, lua):
        """Basic string methods via : syntax are safe and allowed."""
        # String methods like gsub, upper, len are safe - just string manipulation
        # They're accessible via the string metatable's __index
        result = lua.eval('("hello"):upper()')
        assert result == "HELLO"

    def test_cannot_access_string_metatable_directly(self, lua):
        """Cannot access string metatable directly (getmetatable is nil)."""
        # Even though string methods work, we can't introspect the metatable
        with pytest.raises(LuaError, match="nil value"):
            lua.execute('local x = getmetatable("").__index.dump')

    def test_pcall_cannot_expose_internals(self, lua):
        """pcall errors don't expose sensitive information."""
        # pcall is allowed for error handling, but shouldn't leak info
        lua.execute("""
            local ok, err = pcall(function()
                error("test error")
            end)
            _test_ok = ok
            _test_err = err
        """)
        ok = lua.eval("_test_ok")
        err = lua.eval("_test_err")
        assert ok is False
        assert "test error" in str(err)

    def test_coroutines_blocked(self, lua):
        """Coroutines should be blocked."""
        result = lua.eval("coroutine")
        assert result is None

    def test_cannot_create_c_functions(self, lua):
        """Cannot create or call C functions."""
        # newproxy could create userdata in old Lua
        result = lua.eval("newproxy")
        assert result is None


class TestLegitimateUseCases:
    """Test that legitimate operations still work with the sandbox.

    NOTE: Lupa (Python-Lua bridge) has specific behaviors for Python objects:
    - Python lists use 0-based indexing (not Lua's native 1-based)
    - ipairs/pairs don't work directly on Python objects (need Lua tables)
    - # operator doesn't work on Python objects
    """

    def test_iterate_python_list_with_index(self, lua):
        """Can iterate over Python lists using numeric index loop."""
        my_list = [1, 2, 3, 4, 5]
        lua.globals()['my_list'] = my_list
        lua.globals()['list_len'] = len(my_list)

        # Use numeric for loop since ipairs doesn't work on Python objects
        # Lupa uses 0-based indexing for Python lists
        lua.execute("""
            _sum = 0
            for i = 0, list_len - 1 do
                _sum = _sum + my_list[i]
            end
        """)
        result = lua.eval('_sum')
        assert result == 15

    def test_iterate_python_dict_by_keys(self, lua):
        """Can iterate over Python dicts by passing keys separately."""
        my_dict = {'a': 1, 'b': 2, 'c': 3}
        lua.globals()['my_dict'] = my_dict
        # Pass keys as a separate list since pairs() doesn't work on Python dicts
        lua.globals()['keys'] = list(my_dict.keys())
        lua.globals()['keys_len'] = len(my_dict)

        lua.execute("""
            _sum = 0
            for i = 0, keys_len - 1 do
                local key = keys[i]
                _sum = _sum + my_dict[key]
            end
        """)
        result = lua.eval('_sum')
        assert result == 6

    def test_access_list_by_index(self, lua):
        """Can access Python list elements by index (0-based in Lupa)."""
        lua.globals()['my_list'] = [10, 20, 30]

        # Lupa uses 0-based indexing for Python lists (not Lua's native 1-based)
        result = lua.eval('my_list[0]')
        assert result == 10

        result = lua.eval('my_list[2]')
        assert result == 30

    def test_access_dict_by_key(self, lua):
        """Can access Python dict values by key."""
        lua.globals()['my_dict'] = {'name': 'test', 'value': 42}

        result = lua.eval('my_dict.name')
        assert result == 'test'

        result = lua.eval('my_dict["value"]')
        assert result == 42

    def test_access_object_data_attributes(self, lua):
        """Can access data attributes on Python objects."""
        class DataObject:
            def __init__(self):
                self.x = 100
                self.y = 200
                self.name = "entity"

        lua.globals()['obj'] = DataObject()

        assert lua.eval('obj.x') == 100
        assert lua.eval('obj.y') == 200
        assert lua.eval('obj.name') == "entity"

    def test_nested_data_access(self, lua):
        """Can access nested data structures."""
        data = {
            'player': {
                'position': {'x': 10, 'y': 20},
                'health': 100
            },
            'enemies': [
                {'name': 'goblin', 'hp': 30},
                {'name': 'orc', 'hp': 50}
            ]
        }
        lua.globals()['game_data'] = data

        assert lua.eval('game_data.player.position.x') == 10
        assert lua.eval('game_data.player.health') == 100
        # Lupa uses 0-based indexing for Python lists
        assert lua.eval('game_data.enemies[0].name') == 'goblin'
        assert lua.eval('game_data.enemies[1].hp') == 50

    def test_len_on_list_via_python(self, lua):
        """Can get length of Python list (must pass length separately).

        The # operator doesn't work on Python objects in Lupa.
        Length must be provided from Python side.
        """
        my_list = [1, 2, 3, 4, 5]
        lua.globals()['my_list'] = my_list
        lua.globals()['list_len'] = len(my_list)

        # Can use the passed length
        result = lua.eval('list_len')
        assert result == 5

    def test_modify_list(self, lua):
        """Can modify Python list elements (0-based indexing in Lupa)."""
        my_list = [1, 2, 3]
        lua.globals()['my_list'] = my_list

        # Lupa uses 0-based indexing, so my_list[1] is Python's index 1
        lua.execute('my_list[1] = 99')
        assert my_list[1] == 99  # Modified Python index 1

    def test_modify_dict(self, lua):
        """Can modify Python dict values."""
        my_dict = {'a': 1, 'b': 2}
        lua.globals()['my_dict'] = my_dict

        lua.execute('my_dict.a = 100')
        lua.execute('my_dict["c"] = 3')

        assert my_dict['a'] == 100
        assert my_dict['c'] == 3

    def test_pass_callback_to_lua(self, lua):
        """Can pass Python callbacks that Lua can call."""
        results = []

        def callback(value):
            results.append(value)
            return value * 2

        lua.globals()['py_callback'] = callback

        result = lua.eval('py_callback(21)')
        assert result == 42
        assert results == [21]

    def test_return_values_from_lua(self, lua):
        """Can return complex values from Lua to Python."""
        lua.execute("""
            function make_data()
                return {x = 10, y = 20, items = {1, 2, 3}}
            end
        """)

        result = lua.eval('make_data()')
        assert result['x'] == 10
        assert result['y'] == 20
        assert list(result['items'].values()) == [1, 2, 3]


class TestRuntimeValidation:
    """Test that sandbox validation runs and catches issues."""

    def test_engine_validates_on_init(self, content_fs):
        """BehaviorEngine should validate sandbox on initialization."""
        # If validation fails, this would raise RuntimeError
        engine = BehaviorEngine(content_fs, 800, 600)
        # If we get here, validation passed
        assert engine is not None

    def test_validation_catches_exposed_globals(self, content_fs):
        """Validation should catch if dangerous globals are exposed."""
        # Create engine normally (should pass)
        engine = BehaviorEngine(content_fs, 800, 600)

        # Manually expose a dangerous global and re-validate
        # This simulates what would happen if sandbox setup was broken
        engine._lua.execute('python = {}')  # Simulate broken sandbox

        # Now validation should fail
        with pytest.raises(RuntimeError, match="sandbox validation failed"):
            engine._validate_sandbox()


class TestLuaSafeReturns:
    """Test that AMS API methods return Lua-native types, not Python objects.

    This ensures proper 1-indexed iteration with ipairs/pairs and # operator support.
    """

    def test_get_entities_of_type_returns_lua_table(self, content_fs):
        """get_entities_of_type returns a 1-indexed Lua table."""
        engine = BehaviorEngine(content_fs, 800, 600)

        # Create some entities
        engine.create_entity('brick', x=100, y=100, width=50, height=20)
        engine.create_entity('brick', x=200, y=100, width=50, height=20)
        engine.create_entity('ball', x=300, y=300, width=10, height=10)

        # Get entities from Lua
        engine._lua.execute("""
            _bricks = ams.get_entities_of_type("brick")
            _count = #_bricks
            _sum = 0
            for i, id in ipairs(_bricks) do
                _sum = _sum + 1
            end
        """)

        count = engine._lua.eval('_count')
        sum_val = engine._lua.eval('_sum')

        assert count == 2, "# operator should work on returned table"
        assert sum_val == 2, "ipairs should iterate over returned table"

    def test_get_entities_by_tag_returns_lua_table(self, content_fs):
        """get_entities_by_tag returns a 1-indexed Lua table."""
        engine = BehaviorEngine(content_fs, 800, 600)

        # Create entities with tags
        engine.create_entity('enemy', x=100, y=100, tags=['hostile', 'flying'])
        engine.create_entity('enemy', x=200, y=100, tags=['hostile'])
        engine.create_entity('player', x=300, y=300, tags=['friendly'])

        engine._lua.execute("""
            _hostiles = ams.get_entities_by_tag("hostile")
            _count = #_hostiles
        """)

        count = engine._lua.eval('_count')
        assert count == 2

    def test_get_all_entity_ids_returns_lua_table(self, content_fs):
        """get_all_entity_ids returns a 1-indexed Lua table."""
        engine = BehaviorEngine(content_fs, 800, 600)

        engine.create_entity('a', x=0, y=0)
        engine.create_entity('b', x=0, y=0)
        engine.create_entity('c', x=0, y=0)

        engine._lua.execute("""
            _all = ams.get_all_entity_ids()
            _count = #_all
        """)

        count = engine._lua.eval('_count')
        assert count == 3

    def test_get_config_returns_lua_table_for_nested_data(self, content_fs):
        """get_config converts nested dicts/lists to Lua tables."""
        engine = BehaviorEngine(content_fs, 800, 600)

        entity = engine.create_entity(
            'test',
            x=0, y=0,
            behaviors=[],
            behavior_config={
                'movement': {
                    'waypoints': [
                        {'x': 100, 'y': 100},
                        {'x': 200, 'y': 200}
                    ],
                    'speed': 50
                }
            }
        )

        engine._lua.execute(f"""
            _waypoints = ams.get_config("{entity.id}", "movement", "waypoints")
            _count = #_waypoints
            _first_x = _waypoints[1].x
        """)

        count = engine._lua.eval('_count')
        first_x = engine._lua.eval('_first_x')

        assert count == 2, "Nested list should be 1-indexed Lua table"
        assert first_x == 100, "Nested dict should be accessible"

    def test_get_prop_returns_lua_table_for_list(self, content_fs):
        """get_prop converts list properties to Lua tables."""
        engine = BehaviorEngine(content_fs, 800, 600)

        entity = engine.create_entity('test', x=0, y=0)
        entity.properties['items'] = ['sword', 'shield', 'potion']

        engine._lua.execute(f"""
            _items = ams.get_prop("{entity.id}", "items")
            _count = #_items
            _first = _items[1]
        """)

        count = engine._lua.eval('_count')
        first = engine._lua.eval('_first')

        assert count == 3
        assert first == 'sword'

    def test_lua_table_iteration_with_pairs(self, content_fs):
        """Can iterate returned tables with pairs()."""
        engine = BehaviorEngine(content_fs, 800, 600)

        entity = engine.create_entity('test', x=0, y=0)
        entity.properties['stats'] = {'hp': 100, 'mp': 50, 'str': 10}

        engine._lua.execute(f"""
            _stats = ams.get_prop("{entity.id}", "stats")
            _total = 0
            for k, v in pairs(_stats) do
                _total = _total + v
            end
        """)

        total = engine._lua.eval('_total')
        assert total == 160  # 100 + 50 + 10


class TestLuaSafeReturnBoundary:
    """Test that the Lua-safe return decorator enforces type boundaries."""

    def test_rejects_bytes(self):
        """Cannot return bytes to Lua."""
        from ams.behaviors.api import _to_lua_value
        from lupa import LuaRuntime
        lua = LuaRuntime()

        with pytest.raises(TypeError, match="bytes"):
            _to_lua_value(b"raw bytes", lua)

    def test_rejects_sets(self):
        """Cannot return sets to Lua."""
        from ams.behaviors.api import _to_lua_value
        from lupa import LuaRuntime
        lua = LuaRuntime()

        with pytest.raises(TypeError, match="set"):
            _to_lua_value({1, 2, 3}, lua)

    def test_rejects_arbitrary_objects(self):
        """Cannot return arbitrary Python objects."""
        from ams.behaviors.api import _to_lua_value
        from lupa import LuaRuntime
        lua = LuaRuntime()

        class SomeObject:
            pass

        with pytest.raises(TypeError, match="Cannot convert"):
            _to_lua_value(SomeObject(), lua)

    def test_rejects_invalid_dict_keys(self):
        """Cannot return dicts with non-primitive keys."""
        from ams.behaviors.api import _to_lua_value
        from lupa import LuaRuntime
        lua = LuaRuntime()

        with pytest.raises(TypeError, match="Dict key"):
            _to_lua_value({(1, 2): "tuple key"}, lua)

    def test_handles_deeply_nested_structures(self):
        """Properly converts deeply nested structures."""
        from ams.behaviors.api import _to_lua_value
        from lupa import LuaRuntime
        lua = LuaRuntime()

        deep = {"a": [{"b": [1, 2, {"c": 3}]}]}
        result = _to_lua_value(deep, lua)

        # Should be able to traverse without error (1-indexed for arrays)
        assert result["a"][1]["b"][3]["c"] == 3


class TestAttributeFilterEdgeCases:
    """Test edge cases in the attribute filter."""

    def test_attribute_filter_on_none_attribute(self, lua):
        """Attribute filter handles objects with None-valued attributes."""
        class HasNone:
            def __init__(self):
                self.value = None

        lua.globals()['obj'] = HasNone()
        result = lua.eval('obj.value')
        assert result is None  # Should work, not raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
