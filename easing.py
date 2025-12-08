# easing.py

def linear(t):
    return t

def ease_in_quad(t):
    return t * t

def ease_out_quad(t):
    return 1 - (1 - t) * (1 - t)

def ease_in_out_quad(t):
    return 2 * t * t if t < 0.5 else 1 - (-2 * t + 2) * (-2 * t + 2) / 2

def ease_in_cubic(t):
    return t * t * t

def ease_out_cubic(t):
    return 1 - pow(1 - t, 3)

def ease_in_out_cubic(t):
    return 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2

def ease_in_quart(t):
    return t * t * t * t

def ease_out_quart(t):
    return 1 - pow(1 - t, 4)

def ease_in_out_quart(t):
    return 8 * t * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 4) / 2

def ease_in_quint(t):
    return t * t * t * t * t

def ease_out_quint(t):
    return 1 - pow(1 - t, 5)

def ease_in_out_quint(t):
    return 16 * t * t * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 5) / 2

# Add more easing functions as needed
EASING_FUNCTIONS = {
    "linear": linear,
    "in_quad": ease_in_quad,
    "out_quad": ease_out_quad,
    "in_out_quad": ease_in_out_quad,
    "in_cubic": ease_in_cubic,
    "out_cubic": ease_out_cubic,
    "in_out_cubic": ease_in_out_cubic,
    "in_quart": ease_in_quart,
    "out_quart": ease_out_quart,
    "in_out_quart": ease_in_out_quart,
    "in_quint": ease_in_quint,
    "out_quint": ease_out_quint,
    "in_out_quint": ease_in_out_quint,
}

# List of easing function names for cycling through in UI
EASING_NAMES = list(EASING_FUNCTIONS.keys())
EASING_DEFAULT = "linear"
