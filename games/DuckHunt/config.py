"""
Configuration file for Duck Hunt game.

Contains all game constants, screen settings, colors, and gameplay parameters.
"""

# Screen and Display Settings
SCREEN_WIDTH = 1920  # Default projector resolution
SCREEN_HEIGHT = 1080
FPS = 60  # Target frame rate

# Colors (RGBA tuples)
BLACK = (0, 0, 0, 255)
WHITE = (255, 255, 255, 255)
RED = (255, 0, 0, 255)
GREEN = (0, 255, 0, 255)
BLUE = (0, 0, 255, 255)
YELLOW = (255, 255, 0, 255)
ORANGE = (255, 165, 0, 255)
PURPLE = (128, 0, 128, 255)
CYAN = (0, 255, 255, 255)
GRAY = (128, 128, 128, 255)
LIGHT_GRAY = (200, 200, 200, 255)
DARK_GRAY = (64, 64, 64, 255)

# Background color
BACKGROUND_COLOR = (135, 206, 235, 255)  # Sky blue

# Target Settings
TARGET_DEFAULT_SIZE = 50.0  # Default target diameter in pixels
TARGET_MIN_SIZE = 30.0  # Minimum target size
TARGET_MAX_SIZE = 100.0  # Maximum target size
TARGET_DEFAULT_SPEED = 100.0  # Pixels per second
TARGET_COLOR = ORANGE
TARGET_HIT_COLOR = GREEN
TARGET_MISS_COLOR = RED

# Target Spawn Settings
TARGET_SPAWN_RATE = 2.0  # Seconds between spawns
TARGET_MAX_ACTIVE = 5  # Maximum simultaneous targets
TARGET_SPAWN_MARGIN = 50  # Margin from screen edges for spawn

# Scoring Settings
POINTS_PER_HIT = 100
COMBO_MULTIPLIER = 1.5  # Points multiplier for combos
COMBO_THRESHOLD = 3  # Hits needed to start combo bonus
PENALTY_PER_MISS = 0  # Points lost per miss (0 = no penalty)

# Visual Effects Settings
HIT_EFFECT_DURATION = 0.5  # Seconds
MISS_EFFECT_DURATION = 0.3  # Seconds
SCORE_POPUP_DURATION = 1.0  # Seconds
EFFECT_FADE_SPEED = 2.0  # Alpha fade rate

# Input Settings
INPUT_DEADZONE = 5.0  # Minimum pixel movement to register
CLICK_RADIUS = 10.0  # Radius for hit detection (pixels)

# Game Mode Settings - Classic Mode
CLASSIC_TARGET_LIFETIME = 5.0  # Seconds before target escapes
CLASSIC_INITIAL_SPEED = 80.0  # Initial target speed
CLASSIC_SPEED_INCREASE = 10.0  # Speed increase per level
CLASSIC_MAX_SPEED = 300.0  # Maximum target speed

# Game Mode Settings - Flash Mode
FLASH_DISPLAY_TIME = 1.0  # Seconds targets are visible
FLASH_MEMORY_TIME = 2.0  # Seconds to remember positions
FLASH_TARGET_COUNT = 3  # Number of targets per round

# Game Mode Settings - Sequence Mode
SEQUENCE_TARGET_COUNT = 5  # Number of targets in sequence
SEQUENCE_TIME_LIMIT = 10.0  # Seconds to complete sequence
SEQUENCE_WRONG_ORDER_PENALTY = -50  # Points lost for wrong order

# UI Settings
FONT_SIZE_SMALL = 24
FONT_SIZE_MEDIUM = 36
FONT_SIZE_LARGE = 48
FONT_SIZE_HUGE = 72

# UI Colors
UI_TEXT_COLOR = WHITE
UI_BACKGROUND_COLOR = DARK_GRAY
UI_HIGHLIGHT_COLOR = YELLOW


# Organized Constants for Code Access
class Colors:
    """Color constants for easy access in code."""
    BLACK = BLACK
    WHITE = WHITE
    RED = RED
    GREEN = GREEN
    BLUE = BLUE
    YELLOW = YELLOW
    ORANGE = ORANGE
    PURPLE = PURPLE
    CYAN = CYAN
    GRAY = GRAY
    LIGHT_GRAY = LIGHT_GRAY
    DARK_GRAY = DARK_GRAY
    BACKGROUND = BACKGROUND_COLOR
    TARGET = TARGET_COLOR
    TARGET_HIT = TARGET_HIT_COLOR
    TARGET_MISS = TARGET_MISS_COLOR
    UI_TEXT = UI_TEXT_COLOR
    UI_BACKGROUND = UI_BACKGROUND_COLOR
    UI_HIGHLIGHT = UI_HIGHLIGHT_COLOR
    SCORE_TEXT = WHITE  # Score display text color


class Fonts:
    """Font size constants for easy access in code."""
    SMALL = FONT_SIZE_SMALL
    MEDIUM = FONT_SIZE_MEDIUM
    LARGE = FONT_SIZE_LARGE
    HUGE = FONT_SIZE_HUGE
    SCORE_SIZE = FONT_SIZE_MEDIUM  # Size for score display

# Debug Settings
DEBUG_MODE = False
SHOW_FPS = False
SHOW_BOUNDING_BOXES = False
SHOW_INPUT_POSITIONS = False
LOG_INPUT_EVENTS = False

# Audio Settings (placeholder values)
AUDIO_ENABLED = True
MASTER_VOLUME = 0.7  # 0.0 to 1.0
SFX_VOLUME = 0.8
MUSIC_VOLUME = 0.5

# Performance Settings
MAX_VISUAL_EFFECTS = 20  # Maximum simultaneous visual effects
PARTICLE_COUNT = 10  # Particles per effect

# Game State Settings
GAME_OVER_DELAY = 2.0  # Seconds before showing game over screen
MENU_TRANSITION_TIME = 0.3  # Seconds for menu transitions

# Difficulty Settings
DIFFICULTY_LEVELS = {
    'easy': {
        'target_speed': 80.0,
        'spawn_rate': 3.0,
        'target_size': 60.0,
        'max_active': 3,
    },
    'medium': {
        'target_speed': 120.0,
        'spawn_rate': 2.0,
        'target_size': 50.0,
        'max_active': 5,
    },
    'hard': {
        'target_speed': 180.0,
        'spawn_rate': 1.5,
        'target_size': 40.0,
        'max_active': 7,
    },
    'expert': {
        'target_speed': 250.0,
        'spawn_rate': 1.0,
        'target_size': 30.0,
        'max_active': 10,
    },
}

# Default difficulty
DEFAULT_DIFFICULTY = 'medium'
