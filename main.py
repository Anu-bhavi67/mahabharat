"""
=====================================================================
  MAHABHARAT: DIVINE WARFARE
  A 2D fighting game built with Python + Pygame
=====================================================================

  Controls  (FULL COMBAT SYSTEM)
  --------
  MENU             : ENTER / SPACE  -> start game
  CHARACTER_SELECT : P1 browse with A/D/W/S or ARROWS, ENTER to lock
                     P2 browse with I/J/K/L, B or N to lock
                     once both are locked press ENTER to fight
  FIGHT — PLAYER 1 : ←/→ move   ↑ jump   ↓ crouch
                     ↓ + ← (back) BLOCK   Z punch (20f)  X kick (25f)
                     CTRL special (needs a full meter)
  FIGHT — PLAYER 2 : J/L move   I jump   K crouch
                     K + J (back) BLOCK   B punch (20f)  N kick (25f)
                     SPACE special (needs a full meter)
  RESULT           : ENTER -> main menu   |   C -> character select
  Anywhere         : ESC    -> quit

  Combat rules implemented in the Fighter class:
    * Punch  : fast, low damage,  20-frame cooldown, reach 70 px
    * Kick   : slower, more dmg,  25-frame cooldown, reach 95 px
    * Active window: hitbox live during frames 12-20 of the move;
      the fist/foot glows YELLOW while active and the limb extends.
    * Blocking (hold down/back): -75% damage, shield arc drawn in front,
      10 frames of block stun in which the blocker cannot act.
    * Hit reaction: 15-frame WHITE FLASH, knockback away from the attacker
      and brief hit stun that locks all actions.
    * Combo system: consecutive hits inside 60 frames count up and show
      "X HIT COMBO!" in gold; the counter resets when the window expires.
    * Damage: health drops on hit (never below 0) and the attacker gains
      special meter equal to 1.5x the damage dealt.

  All visuals are drawn procedurally (pygame.font + shapes).
  No external image/sound assets are required.
=====================================================================
"""

import sys
import math
import random
import pygame

# =====================================================================
# SECTION 1: INITIALISATION, GLOBAL CLOCK & CONSTANTS
# =====================================================================

pygame.init()
pygame.display.set_caption("MAHABHARAT: DIVINE WARFARE")

# --- Display ---------------------------------------------------------
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 600
FPS = 60

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
clock = pygame.time.Clock()          # global clock used by the game loop

# --- Colour constants ------------------------------------------------
SAFFRON   = (255, 153, 0)     # sacred saffron / orange
GOLD      = (255, 215, 0)     # shimmering gold
DEEP_RED  = (139, 0, 0)       # deep battle red
DARK_BLUE = (10, 10, 45)      # dark twilight blue
GREEN     = (34, 139, 34)     # forest green
YELLOW    = (255, 210, 0)     # health-bar mid tier
WHITE     = (255, 255, 255)
BLACK     = (0, 0, 0)
GREY      = (128, 128, 128)

# --- Game states (state machine) -------------------------------------
STATE_MENU = "MENU"
STATE_CHARACTER_SELECT = "CHARACTER_SELECT"
STATE_FIGHT = "FIGHT"
STATE_RESULT = "RESULT"

# --- Fonts (created once, reused everywhere) --------------------------
FONT_SMALL  = pygame.font.SysFont("arial", 22)
FONT_TINY   = pygame.font.SysFont("arial", 15)   # character-card micro text
FONT_COMBO  = pygame.font.SysFont("arial", 34, bold=True)   # "X HIT COMBO!"
FONT_MEDIUM = pygame.font.SysFont("arial", 32, bold=True)
FONT_LARGE  = pygame.font.SysFont("arial", 64, bold=True)
FONT_TITLE  = pygame.font.SysFont("arial", 72, bold=True)


# =====================================================================
# SECTION 2: HELPER FUNCTIONS (drawing utilities)
# =====================================================================

def draw_vertical_gradient(surface, top_color, bottom_color):
    """Fill the surface with a smooth vertical colour gradient."""
    height = surface.get_height()
    r1, g1, b1 = top_color
    r2, g2, b2 = bottom_color
    for y in range(height):
        t = y / max(1, height - 1)
        color = (int(r1 + (r2 - r1) * t),
                 int(g1 + (g2 - g1) * t),
                 int(b1 + (b2 - b1) * t))
        pygame.draw.line(surface, color, (0, y), (surface.get_width(), y))


def draw_centered_text(surface, text, font, color, x, y, shadow=False):
    """Draw text centred horizontally AND vertically on (x, y)."""
    img = font.render(text, True, color)
    rect = img.get_rect(center=(x, y))
    if shadow:  # cheap drop-shadow for readability
        sh = font.render(text, True, BLACK)
        surface.blit(sh, sh.get_rect(center=(x + 3, y + 3)))
        surface.blit(img, rect)
    else:
        surface.blit(img, rect)
    return rect


def blink_visible(elapsed_ms, period_ms=1000, duty=0.55):
    """Return True during the 'on' phase of a blink cycle."""
    return (elapsed_ms % period_ms) < period_ms * duty


# =====================================================================
# SECTION 3: BACKGROUND — sunset battlefield (drawn once, blitted often)
# =====================================================================

class BattlefieldBackground:
    """Dark saffron/orange sunset gradient with sun, silhouettes, dust."""

    def __init__(self):
        self.surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        self._paint()
        self.dust_particles = [
            [random.uniform(0, SCREEN_WIDTH),
             random.uniform(0, SCREEN_HEIGHT),
             random.uniform(0.3, 1.2),                       # drift speed
             random.uniform(1, 3)]                           # radius
            for _ in range(40)
        ]

    def _paint(self):
        s = self.surface
        # Sky: near-black deep blue at top -> saffron -> burnt orange horizon
        draw_vertical_gradient(s, DARK_BLUE, SAFFRON)
        pygame.draw.rect(s, DEEP_RED,
                         (0, int(SCREEN_HEIGHT * 0.62),
                          SCREEN_WIDTH, int(SCREEN_HEIGHT * 0.10)))

        # The setting sun
        sun_pos = (SCREEN_WIDTH // 2, int(SCREEN_HEIGHT * 0.55))
        for radius, alpha in ((120, 40), (90, 70), (60, 120)):
            glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*GOLD, alpha), (radius, radius), radius)
            s.blit(glow, (sun_pos[0] - radius, sun_pos[1] - radius))
        pygame.draw.circle(s, (255, 200, 60), sun_pos, 45)

        # Distant mountain / temple silhouettes
        silhouette = (25, 10, 20)
        mountains = [(0, 420), (150, 350), (300, 415), (480, 330),
                     (650, 410), (820, 345), (1000, 400), (1200, 360)]
        pygame.draw.polygon(s, silhouette,
                            [(0, SCREEN_HEIGHT)] + mountains +
                            [(SCREEN_WIDTH, SCREEN_HEIGHT)])

        # Flag banners on two banner-poles (Kurukshetra camp feel)
        for px in (120, SCREEN_WIDTH - 120):
            pygame.draw.line(s, (40, 25, 15), (px, 430), (px, 300), 5)
            pygame.draw.polygon(s, SAFFRON,
                                [(px, 300), (px + 45, 312), (px, 328)])

        # Battlefield ground
        ground_top = int(SCREEN_HEIGHT * 0.72)
        draw_vertical_gradient_region(
            s, (0, ground_top, SCREEN_WIDTH, SCREEN_HEIGHT - ground_top),
            (120, 60, 10), (40, 18, 8))

        # Scattered weapons / rocks as tiny dark marks
        for _ in range(30):
            rx = random.randint(0, SCREEN_WIDTH - 10)
            ry = random.randint(ground_top + 15, SCREEN_HEIGHT - 15)
            pygame.draw.line(s, (20, 10, 5), (rx, ry),
                             (rx + random.randint(-18, 18), ry - 6), 2)

    def update(self):
        """Slow horizontal drift of floating dust motes."""
        for p in self.dust_particles:
            p[0] += p[2]
            if p[0] > SCREEN_WIDTH:
                p[0] = 0

    def draw(self, target, dim=0):
        """Blit the baked battlefield; `dim` (0-255) darkens it (menus)."""
        if dim > 0:
            veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT),
                                  pygame.SRCALPHA)
            veil.fill((8, 4, 14, dim))
            target.blit(self.surface, (0, 0))
            target.blit(veil, (0, 0))
        else:
            target.blit(self.surface, (0, 0))
        for x, y, _, r in self.dust_particles:
            dust = pygame.Surface((6, 6), pygame.SRCALPHA)
            pygame.draw.circle(dust, (*SAFFRON, 60), (3, 3), int(r) + 1)
            target.blit(dust, (x, y))


def draw_dharma_chakra(target, cx, cy, radius, color=(255, 170, 40),
                       spokes=24, angle_offset=0.0, width=2,
                       hub=True, alpha=200):
    """A small dharma chakra: rim circle + radiating spokes (+hub).

    Used as a decorative motif in the corners of the character-select
    screen and wherever else sacred geometry is wanted.  Pure shapes —
    no image assets.
    """
    surf = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
    c = (cx - surf.get_width() // 2 + radius + 2,
         cy - surf.get_height() // 2 + radius + 2)
    rim = (*color, alpha)
    pygame.draw.circle(surf, rim, (c[0], c[1]), radius, width)
    pygame.draw.circle(surf, (*color, max(20, alpha // 3)),
                       (c[0], c[1]), max(2, radius - 4), 1)
    for i in range(spokes):
        a = angle_offset + i * (math.tau / max(1, spokes))
        x1 = c[0] + math.cos(a) * (radius - 5)
        y1 = c[1] + math.sin(a) * (radius - 5)
        x2 = c[0] - math.cos(a) * (radius - 5)
        y2 = c[1] - math.sin(a) * (radius - 5)
        pygame.draw.line(surf, rim, (x1, y1), (x2, y2), max(1, width - 1))
    if hub:
        pygame.draw.circle(surf, (*color, min(255, alpha + 40)),
                           (c[0], c[1]), max(3, radius // 5))
        pygame.draw.circle(surf, (0, 0, 0, min(200, alpha)),
                           (c[0], c[1]), max(2, radius // 9))
    target.blit(surf, (cx - surf.get_width() // 2,
                       cy - surf.get_height() // 2))


def draw_vertical_gradient_region(surface, region, top_color, bottom_color):
    """Gradient fill restricted to a rectangular region of a surface."""
    x, y, w, h = region
    r1, g1, b1 = top_color
    r2, g2, b2 = bottom_color
    for i in range(h):
        t = i / max(1, h - 1)
        color = (int(r1 + (r2 - r1) * t),
                 int(g1 + (g2 - g1) * t),
                 int(b1 + (b2 - b1) * t))
        pygame.draw.line(surface, color, (x, y + i), (x + w, y + i))


# =====================================================================
# SECTION 4: FIGHTER CLASS — detailed procedural stick-figure warriors
# =====================================================================
# One Fighter instance == one character on screen.  Everything about a
# fighter is driven by its CHARACTERS-database record (stats, colours,
# weapon type, special fx colour); the drawing code builds a warrior out
# of primitive shapes only — head circle, torso rect, limb lines with
# fists/feet, a signature weapon silhouette and a glowing astral aura.
#
# Physics convention:
#   self.x    -> horizontal centre (pixels)
#   self.y    -> HEIGHT ABOVE the ground line (0 == standing on it).
#                Jumping adds vel_y; gravity pulls back down until y<=0.
#   GROUND_Y  -> the fixed foot-baseline at y = 430 on screen.
# ---------------------------------------------------------------------
GROUND_Y = 430                        # feet baseline (screen y) per spec
GRAVITY = 0.9                         # downward accel px/frame^2
JUMP_VELOCITY = 16                    # initial upward launch speed
FIGHTER_WIDTH = 50                    # standing hitbox width
STAND_HEIGHT = 150                    # full body height (feet->crown)
CROUCH_HEIGHT = 95                    # squashed height while crouching
BODY_LEFT_MARGIN = 35                 # boundary clamp padding


# ---------------------------------------------------------------------
# PARTICLE AND VISUAL EFFECTS SYSTEM — tunable constants
# ---------------------------------------------------------------------
HEAVY_HIT_THRESHOLD = 18      # damage that counts as a "heavy" blow
HIT_FREEZE_FRAMES = 4         # pause budget on normal hits (3-5 frames)
FREEZE_PER_PARTICLE = 0.1     # extra freeze frames per spawned particle
MAX_FREEZE_FRAMES = 8         # hard cap so fights never feel sluggish
FLASH_FRAMES = 2              # white full-screen flash duration
FLASH_ALPHA = 150             # peak brightness of the flash overlay
TINT_FRAMES = 12              # colour-tint veil duration after a special
AURA_EMISSION_CHANCE = 0.45   # odds/particle of a ready-meter aura puff
EFFECT_RING_LAYERS = 4        # concentric rings in a divine burst


class Particle:
    """ONE particle of the visual-effects engine.

    Properties (exactly per the design spec):
        x, y            position on the world canvas
        dx, dy          velocity components (px / frame)
        color           RGB tuple
        lifetime        frames remaining before it dies
        max_lifetime    starting lifetime (drives alpha fade & shrink)
        size            current radius in px (shrinks as it ages)
        gravity         downward acceleration added to dy each frame
        type            one of: "spark" | "energy" | "divine" |
                        "fire" | "smoke"

    The `type` only changes how the particle behaves and looks:
        spark   : fast, light gravity, bright core dot
        energy  : slight buoyancy, plain glowing circle
        divine  : rises slowly, twinkles, leaves a halo ring
        fire    : strong buoyancy, shrinks fast, flickers
        smoke   : very slow drift, expands instead of shrinking
    """

    __slots__ = ("x", "y", "dx", "dy", "color", "lifetime",
                 "max_lifetime", "size", "gravity", "type")

    def __init__(self, x, y, dx, dy, color, lifetime, size,
                 gravity=0.0, ptype="spark"):
        self.x = float(x)
        self.y = float(y)
        self.dx = float(dx)
        self.dy = float(dy)
        self.color = color
        self.lifetime = int(max(1, lifetime))
        self.max_lifetime = int(max(1, lifetime))
        self.size = float(max(1.0, size))
        self.gravity = float(gravity)
        self.type = ptype

    # ---------- simulation ----------
    def update(self):
        """Advance one frame: move, apply gravity/type behaviour,
        decay the lifetime and shrink the size with it."""
        self.x += self.dx
        self.y += self.dy
        self.dy += self.gravity
        t = self.type
        if t == "spark":                     # hot embers fall back down
            self.dx *= 0.93
            self.dy *= 0.96
        elif t == "energy":                  # pure force floats upward
            self.dy -= 0.06
            self.dx *= 0.97
        elif t == "divine":                  # blessed motes rise & twinkle
            self.dy -= 0.10
            self.dx *= 0.98
        elif t == "fire":                    # flames race upward, die fast
            self.dy -= 0.22
            self.dx += random.uniform(-0.25, 0.25)
            self.lifetime -= 1               # burns out quicker
        elif t == "smoke":                   # smoke drifts and billows
            self.dx *= 0.96
            self.dy -= 0.02
        self.lifetime -= 1

    @property
    def alive(self):
        return self.lifetime > 0

    @property
    def ratio(self):
        """Fraction of life left — drives both fade-out and shrink."""
        return self.lifetime / max(1, self.max_lifetime)

    # ---------- rendering ----------
    def draw(self, target):
        """Draw as an alpha-faded circle (plus type flourishes)."""
        r = self.size
        if self.type != "smoke":             # everything else shrinks
            r = max(1.0, self.size * self.ratio)
        else:                                # smoke expands as it fades
            r = max(1.0, self.size * (1.4 - self.ratio))
        ri = max(1, int(r))
        alpha = int(255 * self.ratio)
        if self.type == "fire":
            alpha = min(255, int(alpha * 1.25))
        elif self.type == "smoke":
            alpha = int(alpha * 0.45)
        col = self.color
        if self.type == "fire":              # flame cools toward red
            col = (col[0], max(40, int(col[1] * self.ratio)),
                   max(0, int(col[2] * self.ratio)))
        elif self.type == "smoke":           # smoke greys itself out
            g = sum(col) // 3
            col = (g, g, g)
        surf = pygame.Surface((ri * 2, ri * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (*col, alpha), (ri, ri), ri)
        if self.type == "spark":             # tiny white-hot core
            cr = max(1, ri // 2)
            pygame.draw.circle(surf, (255, 255, 220, min(255, alpha + 40)),
                               (ri, ri), cr)
        elif self.type == "divine":          # golden halo ring
            pygame.draw.circle(surf, (*GOLD, min(200, alpha // 2)),
                               (ri, ri), ri, 1)
        elif self.type == "energy":          # brighter rim
            pygame.draw.circle(surf, (*col, min(255, alpha + 60)),
                               (ri, ri), max(1, ri // 2))
        target.blit(surf, (int(self.x) - ri, int(self.y) - ri))


class ParticleSystem:
    """The complete PARTICLE AND VISUAL EFFECTS SYSTEM.

    Owns every live Particle plus three lightweight request queues that
    let code anywhere in the game (Fighter specials, hit resolution, AI)
    ask the fight scene for camera work without holding a reference to
    it.  FightState drains these queues once per frame:

        shake_requests    -> (frames, intensity)   screen shake
        flash_requests    -> frames                white flash overlay
        tint_requests     -> (color, frames)       colour-tint veil
        freeze_requests   -> frames                hit-freeze slow-mo
        spark_requests    -> (x, y, frames, color) legacy impact sparks

    Effect factory functions (all return the particles they created):
        create_hit_sparks / create_divine_burst / create_weapon_trail /
        create_ground_dust / create_blood_splash / create_aura_particles /
        create_lightning / create_divine_pillar
    """

    def __init__(self):
        self.particles = []          # live Particle objects
        # ---- effect REQUESTS queued for the fight scene ----
        self.shake_requests = []     # (frames, intensity)
        self.spark_requests = []     # (x, y, frames_left, color)
        self.flash_requests = []     # [frames, ...]
        self.tint_requests = []      # [(color, frames), ...]
        self.freeze_requests = []    # [frames, ...]

    # ------------------------------------------------------------------
    # queue helpers (decoupled requests -> consumed by FightState)
    # ------------------------------------------------------------------
    def shake(self, frames, intensity):
        """Queue a screen-shake request (duration + pixel amplitude)."""
        self.shake_requests.append((int(frames), int(intensity)))

    def flash(self, frames=FLASH_FRAMES):
        """Queue a full-screen white flash (big specials / KO)."""
        self.flash_requests.append(int(frames))

    def tint(self, color, frames=TINT_FRAMES):
        """Queue a brief full-screen colour veil in `color`."""
        self.tint_requests.append((tuple(color), int(frames)))

    def freeze(self, frames):
        """Queue hit-freeze frames (3-5 typical, capped by the scene)."""
        self.freeze_requests.append(int(frames))

    def add_spark(self, x, y, frames=14, color=None):
        """Queue a classic impact spark at (x, y)."""
        self.spark_requests.append((x, y, int(frames),
                                    color or GOLD))

    def drain_shakes(self):
        reqs, self.shake_requests = self.shake_requests, []
        return reqs

    def drain_sparks(self):
        reqs, self.spark_requests = self.spark_requests, []
        return reqs

    def drain_flashes(self):
        reqs, self.flash_requests = self.flash_requests, []
        return reqs

    def drain_tints(self):
        reqs, self.tint_requests = self.tint_requests, []
        return reqs

    def drain_freezes(self):
        reqs, self.freeze_requests = self.freeze_requests, []
        return reqs

    # ------------------------------------------------------------------
    # low-level emitter (kept for backwards compatibility with the
    # SPECIAL MOVES SYSTEM code that already calls fx.spawn(...))
    # ------------------------------------------------------------------
    def emit(self, x, y, dx, dy, color, life, size, gravity=0.0,
             ptype="spark"):
        """Push one Particle into the pool and return it."""
        p = Particle(x, y, dx, dy, color, life, size, gravity, ptype)
        self.particles.append(p)
        return p

    def spawn(self, x, y, color, count=30, speed=6, life=30, size=5,
              gravity=0.0, ptype="energy"):
        """Radial burst of `count` particles in random directions."""
        count = max(1, int(count))
        made = []
        for _ in range(count):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(0.25, 1.0) * speed
            made.append(self.emit(
                x, y, math.cos(ang) * spd, math.sin(ang) * spd, color,
                int(life * random.uniform(0.6, 1.0)) + 1,
                max(1, int(size * random.uniform(0.5, 1.3))),
                gravity, ptype))
        return made

    # ==================================================================
    # EFFECT FUNCTIONS (spec items 1-8)
    # ==================================================================
    def create_hit_sparks(self, x, y, color=None, count=15):
        """1. Orange/yellow sparks flying out of a normal landed hit."""
        color = color or SAFFRON
        made = []
        for _ in range(count):
            ang = random.uniform(-math.pi * 0.85, -math.pi * 0.15)
            spd = random.uniform(3.0, 7.5)
            c = (random.choice([SAFFRON, GOLD, YELLOW, WHITE])) \
                if color is None else color
            made.append(self.emit(x, y, math.cos(ang) * spd,
                                  math.sin(ang) * spd, c,
                                  random.randint(10, 20),
                                  random.uniform(2, 4), 0.35, "spark"))
        return made

    def create_divine_burst(self, x, y, color, count=40):
        """2. Expanding ring of coloured energy for special moves.

        Half the particles fly outward along evenly spaced angles (the
        ring), the rest scatter as an inner blast; the astral's own
        colour tints the whole thing."""
        made = []
        ring_n = max(8, int(count * 0.6))
        base_ang = random.uniform(0, math.tau)
        for i in range(ring_n):
            ang = base_ang + i * (math.tau / ring_n) \
                + random.uniform(-0.12, 0.12)
            spd = random.uniform(5.0, 8.5)
            made.append(self.emit(x, y, math.cos(ang) * spd,
                                  math.sin(ang) * spd, color,
                                  random.randint(22, 34),
                                  random.uniform(4, 7), 0.0, "divine"))
        for _ in range(count - ring_n):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(1.0, 4.5)
            made.append(self.emit(x, y, math.cos(ang) * spd,
                                  math.sin(ang) * spd,
                                  GOLD if random.random() < 0.35 else color,
                                  random.randint(16, 30),
                                  random.uniform(3, 6), -0.02, "energy"))
        return made

    def create_weapon_trail(self, x, y, color):
        """3. A couple of tiny motes dropped behind a swinging weapon."""
        made = []
        for _ in range(random.randint(2, 4)):
            made.append(self.emit(x + random.uniform(-4, 4),
                                  y + random.uniform(-4, 4),
                                  random.uniform(-1.2, 1.2),
                                  random.uniform(-1.6, 0.4),
                                  color, random.randint(8, 14),
                                  random.uniform(2, 3.5), 0.05,
                                  "energy"))
        return made

    def create_ground_dust(self, x, y):
        """5b. Brown dust puff kicked up when a fighter lands."""
        made = []
        for _ in range(random.randint(8, 12)):
            ang = random.uniform(math.pi * 1.05, math.pi * 1.95)
            spd = random.uniform(1.5, 4.0)
            shade = random.randint(90, 150)
            made.append(self.emit(x + random.uniform(-14, 14), y,
                                  math.cos(ang) * spd,
                                  math.sin(ang) * spd * 0.6,
                                  (shade, int(shade * 0.72),
                                   int(shade * 0.45)),
                                  random.randint(14, 24),
                                  random.uniform(3, 6), 0.12, "smoke"))
        return made

    def create_blood_splash(self, x, y):
        """6. Mild dark-red droplets on heavy hits (kept subtle)."""
        made = []
        for _ in range(random.randint(6, 10)):
            ang = random.uniform(-math.pi * 0.9, -math.pi * 0.1)
            spd = random.uniform(2.0, 5.5)
            made.append(self.emit(x, y, math.cos(ang) * spd,
                                  math.sin(ang) * spd, DEEP_RED,
                                  random.randint(10, 18),
                                  random.uniform(2, 3.5), 0.45, "spark"))
        return made

    def create_aura_particles(self, fighter):
        """7. Continuous subtle motes orbiting a fighter whose meter is
        FULL — the visual cue that their DIVINE POWER is ready."""
        made = []
        if fighter is None or fighter.special_meter < 100:
            return made
        if random.random() > AURA_EMISSION_CHANCE:
            return made
        cx = fighter.x
        cy = GROUND_Y - fighter.y - 82
        ang = random.uniform(0, math.tau)
        rad = random.uniform(30, 48)
        made.append(self.emit(cx + math.cos(ang) * rad,
                              cy + math.sin(ang) * rad * 0.8,
                              math.cos(ang) * 0.4,
                              -random.uniform(0.3, 1.0),
                              fighter.special_color,
                              random.randint(18, 30),
                              random.uniform(2, 4), -0.01, "divine"))
        return made

    def create_lightning(self, x1, y1, x2, y2, color=None):
        """8. Jagged lightning polyline between two points (Karna's
        SHAKTI ASTRA / Ashwatthama's BRAHMASHIRA crackle).  Returns the
        segment list so the scene can also stroke it as a shape."""
        color = color or GOLD
        steps = max(4, int(((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5 / 18))
        pts = []
        for i in range(steps + 1):
            t = i / steps
            jx = random.uniform(-10, 10) if 0 < i < steps else 0
            jy = random.uniform(-8, 8) if 0 < i < steps else 0
            pts.append((x1 + (x2 - x1) * t + jx,
                        y1 + (y2 - y1) * t + jy))
        for i, (px, py) in enumerate(pts):
            self.emit(px, py, random.uniform(-0.6, 0.6),
                      random.uniform(-1.2, 0.2), color,
                      random.randint(6, 14), random.uniform(2, 4),
                      0.0, "energy")
        return pts

    def create_divine_pillar(self, x, y, color, height=GROUND_Y):
        """9. Vertical beam of falling light (Yudhishthira's Dharma
        Astra) — motes rain from the sky down to the ground line."""
        made = []
        for _ in range(random.randint(24, 36)):
            yy = random.uniform(y - height, y)
            made.append(self.emit(x + random.uniform(-26, 26), yy,
                                  random.uniform(-0.5, 0.5),
                                  random.uniform(4.0, 9.0),
                                  color if random.random() < 0.6 else GOLD,
                                  random.randint(12, 26),
                                  random.uniform(3, 6), 0.05, "divine"))
        # scorch bloom where the pillar meets the earth
        made.extend(self.create_divine_burst(x, y, color, count=14))
        return made

    # ------------------------------------------------------------------
    # per-frame upkeep
    # ------------------------------------------------------------------
    def update(self):
        alive = []
        for p in self.particles:
            p.update()
            if p.alive:
                alive.append(p)
        self.particles = alive

    def draw(self, target):
        for p in self.particles:
            p.draw(target)

    def clear(self):
        self.particles.clear()


class Fighter:
    """A fully-featured 2D fighting-game character entity."""

    def __init__(self, char_data, x, y, facing, is_player2=False,
                 controls=None):
        """
        char_data   : dict — one entry of the CHARACTERS database
        x, y        : spawn position (y is height above ground, usually 0)
        facing      : +1 faces right, -1 faces left
        is_player2  : True for the right-side fighter (mirrors HUD/tags)
        controls    : keymap dict, or None => fighter runs the built-in AI
        """
        self.data = char_data or {}
        d = self.data
        self.name = d.get("name", "WARRIOR")
        self.color = d.get("color", SAFFRON)               # primary
        self.secondary_color = d.get("secondary_color",     # accents/skin
                                     tuple(min(255, c + 60)
                                           for c in self.color))
        self.weapon = d.get("weapon", "")
        self.is_player2 = bool(is_player2)
        self.controls = controls        # None => AI controlled

        # ---- stats straight from the character database ----
        self.max_health = int(d.get("health", 100))
        self.health = self.max_health
        self.speed = max(2, int(d.get("speed", 5)))        # px per frame
        self.punch_damage = int(d.get("punch_damage", 8))
        self.kick_damage = int(d.get("kick_damage", 14))
        self.special_damage = int(d.get("special_damage", 25))
        self.special_name = d.get("special_name", "DIVINE STRIKE")
        self.special_color = d.get("special_color", GOLD)

        # ---- pose / physics state ----
        self.x = float(x)
        self.y = float(y)               # height above GROUND_Y
        self.vel_y = 0.0                # vertical velocity (jump physics)
        self.vx = 0.0                   # knockback slide velocity
        self.vy = 0.0                   # knockback LIFT velocity (air pop)
        self.facing = 1 if facing >= 0 else -1
        self.state = "idle"             # idle|walk|jump|crouch|block|
                                        # punch|kick|hurt|ko
        self.anim_time = 0.0            # accumulates frames for animations

        # =============== FULL COMBAT SYSTEM STATE ====================
        # Attacks run on a per-frame countdown so the active window is
        # deterministic: PUNCH = 20 total frames, KICK = 25 total frames.
        # The hitbox is live during FRAMES 12-20 of the move (i.e. while
        # the countdown sits between 8 and 0).
        self.punch_cooldown = 0         # frames until next punch allowed
        self.kick_cooldown = 0          # frames until next kick allowed
        self.attack_total = 0           # 20 or 25 — progress denominator
        self.attack_hit = False         # one connect per swing
        self.hit_flash = 0              # white-flash frames left (max 15)
        self.block_stun = 0             # 10 frames frozen while guarding
        self.combo_count = 0            # consecutive hits landed
        self.combo_timer = 0            # combo window (60 frames)
        self.special_meter = 0.0        # 0..100, +1.5x damage dealt
        self.projectiles = []           # this fighter's astral blasts
        self.ai_decision_timer = 0
        self.is_channeling = False        # True while casting the astral weapon

        # =============== SPECIAL MOVES SYSTEM STATE ===================
        self.astra = get_astra(self.name)   # this warrior's astral recipe
        # ---- METER GAIN: specials charge by DEALING *and* TAKING damage.
        # Dealt damage fills at METER_GAIN (1.5x); received damage fills at
        # a smaller fraction so comeback astras are possible but earned.
        self.meter_gain_dealt = self.METER_GAIN      # 1.5 x dmg dealt
        self.meter_gain_taken = 0.9                  # 0.9 x dmg taken
        self.controls_reversed_until = 0.0  # MAYA JAAL: reversed-input timer
        self.extra_stun = 0                 # DHARMA ASTRA: bonus stun frames
        self.vortex = None                  # CHAKRAVYUHA BREAKER active box
        self.beam_fx = None                 # BRAHMASHIRA beam display state
        self.pillar_fx = None               # DHARMA ASTRA pillar display state
        self.teleport_fx = None             # MAYAVI GADA purple flash state
        self.illusion_fx = None             # MAYA JAAL decoy copies state
        self._pending_fx_sparks = []        # impact sparks queued by astras
        self._special_credit = []           # dmg values needing meter credit
        # ---- PARTICLE & VISUAL EFFECTS SYSTEM hooks ------------------
        # The fight scene assigns its shared ParticleSystem here so the
        # fighter can emit landing dust, weapon trails and ready-meter
        # aura motes all over the place without a constructor change.
        self.fx = None                      # set by FightState per fighter
        self.was_airborne = False           # for landing-dust detection

    # ------------------------------------------------------------------
    # COMBAT TIMING CONSTANTS (per spec)
    # ------------------------------------------------------------------
    PUNCH_TOTAL = 20        # punch lasts 20 frames -> 20-frame cooldown
    KICK_TOTAL = 25         # kick lasts 25 frames -> 25-frame cooldown
    ACTIVE_FROM = 12        # hitbox live from frame 12 of the move ...
    ACTIVE_TO = 20          # ... through frame 20 (punch); kick stays
                            #     active to the end of its 25 frames
    HIT_STUN = 14           # hit reaction locks actions briefly
    HIT_FLASH_FRAMES = 15   # white flash duration when hit
    BLOCK_REDUCTION = 0.75  # blocking absorbs 75% of incoming damage
    BLOCK_STUN_FRAMES = 10  # blocker cannot act for 10 frames
    COMBO_WINDOW = 60       # consecutive hits within 60 frames = combo
    METER_GAIN = 1.5        # attacker gains 1.5x damage dealt as meter

    # ------------------------------------------------------------------
    # geometry & collision
    # ------------------------------------------------------------------
    def get_rect(self):
        """Body hitbox.  Crouching shrinks the effective height so low
        attacks slip under high ones and vice-versa."""
        h = CROUCH_HEIGHT if self.state == "crouch" else STAND_HEIGHT
        foot_y = GROUND_Y - self.y
        return pygame.Rect(int(self.x) - FIGHTER_WIDTH // 2,
                           int(foot_y - h), FIGHTER_WIDTH, h)

    # Backwards-compatible alias used elsewhere in the codebase.
    get_hitbox = get_rect

    @property
    def rect(self):
        return self.get_rect()

    def is_attack_active(self):
        """True only inside the attack's ACTIVE WINDOW.

        Frame numbering runs 1..TOTAL from the moment the move starts;
        state_timer counts *down*, so elapsed_frame = total - timer.
        Punch hitbox: frames 12-20.  Kick hitbox: frames 12-25
        (same start, longer reach and a wider window)."""
        if self.state not in ("punch", "kick"):
            return False
        elapsed = self.attack_total - self.state_timer   # 1 .. total
        if self.state == "punch":
            return self.ACTIVE_FROM <= elapsed <= self.ACTIVE_TO
        return elapsed >= self.ACTIVE_FROM               # kick: 12 .. 25

    def get_attack_rect(self):
        """Invisible hurt-box that extends IN FRONT of the fighter while a
        melee attack is in its active window; empty rect otherwise."""
        if not self.is_attack_active():
            return pygame.Rect(0, 0, 0, 0)
        reach = self.attack_range()
        box_h = 34
        if self.state == "kick":
            box_y = GROUND_Y - self.y - 70          # leg-level strike
        else:
            box_y = GROUND_Y - self.y - 118         # chest-level strike
        if self.facing > 0:
            return pygame.Rect(int(self.x + 15), int(box_y),
                               int(reach), box_h)
        return pygame.Rect(int(self.x - 15 - reach), int(box_y),
                           int(reach), box_h)

    # ------------------------------------------------------------------
    # actions
    # ------------------------------------------------------------------
    def move_left(self):
        """Walk left at this warrior's own speed (locked during attacks)."""
        if self._busy():
            return
        self.x -= self.speed
        self.state = "walk"
        self._clamp_to_stage()

    def move_right(self):
        if self._busy():
            return
        self.x += self.speed
        self.state = "walk"
        self._clamp_to_stage()

    def stop_walking(self):
        if self.state == "walk":
            self.state = "idle"

    def jump(self):
        """Launch upward — only from the ground, never mid-attack."""
        if self.y == 0 and not self._busy():
            self.vel_y = JUMP_VELOCITY
            self.state = "jump"

    def crouch(self, active=True):
        """Hold to shrink the hitbox; also guards low sweeps."""
        if active and self.y == 0 and self.state in ("idle", "walk",
                                                     "crouch", "block"):
            self.state = "crouch"
        elif not active and self.state == "crouch":
            self.state = "idle"

    def try_block(self):
        """Enter the guarding stance (grounded, neutral stances only)."""
        if self.block_stun > 0:
            return                       # still frozen from the last guard
        if self.y == 0 and self.state in ("idle", "walk", "crouch"):
            self.state = "block"

    def release_block(self):
        """Hold-to-block: the guard drops the instant the key is let go."""
        if self.state == "block" and self.block_stun == 0:
            self.state = "idle"

    def _busy(self):
        """States that lock out every other action (hit stun included)."""
        return (self.state in ("punch", "kick", "hurt", "ko")
                or self.block_stun > 0)

    # ---------- combat: attacks ----------
    def start_attack(self, kind):
        """Begin a punch (20f cycle) or kick (25f cycle).

        Rules enforced here:
          * only from neutral stances (idle / walk / crouch / grounded)
          * per-attack cooldown must have expired (20f / 25f)
          * you cannot be in hit-stun, knockback lift or KO'd
        """
        if self.health <= 0 or self.state == "ko":
            return
        if self.block_stun > 0 or self.vy != 0.0:
            return
        if self.state not in ("idle", "walk", "crouch", "block", "jump"):
            return
        if kind == "punch":
            if self.punch_cooldown > 0:
                return
            self.state = "punch"
            self.attack_total = self.PUNCH_TOTAL
            self.state_timer = self.PUNCH_TOTAL
            self.punch_cooldown = self.PUNCH_TOTAL   # 20-frame cooldown
        elif kind == "kick":
            if self.kick_cooldown > 0:
                return
            self.state = "kick"
            self.attack_total = self.KICK_TOTAL
            self.state_timer = self.KICK_TOTAL
            self.kick_cooldown = self.KICK_TOTAL     # 25-frame cooldown
        else:
            return
        self.attack_hit = False                      # fresh swing can connect

    def start_special(self, opponent=None, fx=None):
        """UNLEASH THE SIGNATURE ASTRAL WEAPON — the heart of the game.

        Requirements: special meter must be FULL (100) and the fighter
        must be in a neutral stance.  On success the meter drains to 0,
        the character channels for CAST_FRAMES and the unique effect for
        this warrior is spawned via _spawn_astra().

        Returns True if the astral was released (so the caller can shout
        the dramatic special_dialogue), False otherwise."""
        if self.special_meter < 100 or self.state not in ("idle", "walk"):
            return False
        if self.health <= 0 or self.state == "ko":
            return False

        # ---- drain the meter completely ----
        self.special_meter = 0.0
        # channeling pose: arms thrust forward, melee box must NOT connect
        self.state = "punch"
        self.attack_total = CAST_FRAMES
        self.state_timer = CAST_FRAMES
        self.punch_cooldown = max(self.punch_cooldown, CAST_FRAMES)
        self.attack_hit = True
        self.is_channeling = True
        self._spawn_astra(opponent, fx)
        return True

    # ------------------------------------------------------------------
    # SPECIAL MOVES SYSTEM — per-character astral spawner
    # ------------------------------------------------------------------
    def _make_projectile(self, x, y, dx, dy=0.0, damage=None, shape=None,
                         scale=1.0):
        """Build one astral projectile record with its own hitbox size.

        Velocity keys are "dx"/"dy" (matching the Particle naming used
        by the PARTICLE AND VISUAL EFFECTS SYSTEM); legacy "vx"/"vy"
        spellings are still honoured wherever projectiles are read."""
        a = self.astra
        w, h = a.get("size", (60, 16))
        return {
            "x": float(x), "y": float(y),
            "dx": dx, "dy": dy,
            "w": int(w * scale), "h": int(h * scale),
            "damage": self.special_damage if damage is None else damage,
            "shape": shape or a.get("shape", "arrow"),
            "scale": scale,
            "color": self.special_color,
            "trail": a.get("trail", ""),
            "owner": self,
            "hit": False,
        }

    def _spawn_astra(self, opponent, fx):
        """Create the visual/hitbox entities for this warrior's special.

        `fx` is the shared ParticleSystem of the fight scene; when it is
        None a private throw-away system is used so the call never breaks.

        PARTICLE AND VISUAL EFFECTS SYSTEM integration — every astral now:
          * spawns its signature particle effect through the new factory
            functions (create_divine_burst / create_lightning /
            create_divine_pillar / create_ground_dust / create_hit_sparks)
          * requests a screen SHAKE scaled to the astral's damage
          * requests a white FLASH overlay (big astras only)
          * requests a colour TINT veil in its own special_color
          * requests HIT-FREEZE frames proportional to the particles it
            created (the slow-mo punch-in on impact)
        """
        if fx is None:
            fx = ParticleSystem()
        a = self.astra
        kind = a["kind"]
        col = self.special_color
        foot_y = GROUND_Y - self.y
        hand_x = self.x + self.facing * 48
        hand_y = foot_y - 112
        dmg = a.get("damage", self.special_damage)
        # ---- shake intensity SCALES WITH DAMAGE (spec) ----
        power = max(4, min(18, int(dmg * 0.55)))
        shake = int(a.get("shake", 10))
        made = []                      # particles created by this astra

        def finish(flash_frames=0, tint=True):
            """Common tail: queue freeze frames from the particle count,
            an optional white flash and the astral's colour veil."""
            fx.freeze(min(MAX_FREEZE_FRAMES,
                          max(3, int(len(made) * FREEZE_PER_PARTICLE))))
            if flash_frames:
                fx.flash(flash_frames)
            if tint:
                fx.tint(col, TINT_FRAMES)
            fx.shake(shake, power)

        # ================= PROJECTILE / BARRAGE ASTRAS (archers) ========
        if kind in ("projectile", "barrage"):
            speed = a.get("speed", 13)
            if kind == "barrage":
                n = a.get("count", 3)
                spread = a.get("spread", 48)
                for i in range(n):
                    dy = (i - (n - 1) / 2.0) * spread
                    pr = self._make_projectile(hand_x, hand_y + dy * 0.4,
                                               self.facing * speed,
                                               damage=dmg, scale=0.6)
                    pr["dy"] = dy * 0.012      # gentle vertical fan-out
                    self.projectiles.append(pr)
            else:
                self.projectiles.append(
                    self._make_projectile(hand_x, hand_y,
                                          self.facing * speed, damage=dmg))
            # divine ring erupting from the bow-string
            made.extend(fx.create_divine_burst(hand_x, hand_y, col,
                                               count=random.randint(30, 50)))
            finish(flash_frames=FLASH_FRAMES if dmg >= 24 else 0)
            return

        # ================= SHOCKWAVE (BHIMA · MAHAGADA PRHAR) ===========
        if kind == "shockwave":
            speed = a.get("speed", 10)
            w, h = a.get("size", (70, 92))
            self.projectiles.append({
                "x": self.x + self.facing * 60,
                "y": GROUND_Y - h / 2.0,       # travels ALONG the ground
                "dx": self.facing * speed, "dy": 0.0,
                "w": w, "h": h,
                "damage": dmg, "shape": "wall", "scale": 1.0,
                "color": col, "trail": "dust",
                "life": a.get("life", 90),
                "owner": self, "hit": False,
            })
            # the ground slam itself: brown dust billowing off the earth
            made.extend(fx.create_ground_dust(self.x + self.facing * 40,
                                              GROUND_Y - 6))
            made.extend(fx.create_ground_dust(self.x + self.facing * 90,
                                              GROUND_Y - 4))
            # energy ring blasting out along the surface
            made.extend(fx.create_divine_burst(self.x + self.facing * 60,
                                               GROUND_Y - 20, col,
                                               count=random.randint(30, 45)))
            finish(flash_frames=FLASH_FRAMES)   # earth-shattering punch-in
            return

        # ================= VORTEX (ABHIMANYU · CHAKRAVYUHA BREAKER) =====
        if kind == "vortex":
            self.vortex = {
                "x": self.x, "y": foot_y - 80,
                "radius": a.get("radius", 120),
                "damage": dmg, "life": a.get("life", VORTEX_LIFE),
                "max_life": a.get("life", VORTEX_LIFE),
                "hit": False,                   # connects ONCE
                "angle": 0.0,
            }
            made.extend(fx.create_divine_burst(self.x, foot_y - 80, col,
                                               count=random.randint(40, 50)))
            finish(flash_frames=FLASH_FRAMES)
            return

        # ================= BEAM (ASHWATTHAMA · BRAHMASHIRA) =============
        if kind == "beam":
            self.beam_fx = {"life": a.get("life", BEAM_LIFE),
                            "max": a.get("life", BEAM_LIFE),
                            "y": foot_y - 100,
                            "bolt": None}
            # jagged lightning strobing across the whole arena width
            made.extend(fx.create_lightning(0, foot_y - 100,
                                            SCREEN_WIDTH, foot_y - 100, col))
            self.beam_fx["bolt"] = fx.create_lightning(
                0, foot_y - 100, SCREEN_WIDTH, foot_y - 100, WHITE)
            # instant full-screen-width strike (meter/combo credited by
            # the fight scene via _finish_special_credit)
            if opponent is not None and opponent.state != "ko":
                applied = opponent.take_hit(dmg, self)
                self._special_credit.append(applied)
                made.extend(fx.create_divine_burst(
                    opponent.x, GROUND_Y - opponent.y - 100, col,
                    count=random.randint(45, 50)))
                made.extend(fx.create_blood_splash(
                    opponent.x, GROUND_Y - opponent.y - 100))
                # remember where the impact happened for the spark layer
                self._pending_fx_sparks.append(
                    (opponent.x, GROUND_Y - opponent.y - 100, 18, col))
            # muzzle storm along the beam line
            for xx in range(0, SCREEN_WIDTH, 90):
                made.extend(fx.create_weapon_trail(xx, foot_y - 100, col))
            made.extend(fx.create_hit_sparks(hand_x, hand_y, WHITE, count=20))
            finish(flash_frames=FLASH_FRAMES + 2)   # cataclysmic white-out
            return

        # ================= PILLAR (YUDHISHTHIRA · DHARMA ASTRA) =========
        if kind == "pillar":
            tx = opponent.x if opponent is not None else self.x + \
                self.facing * 200
            ty = GROUND_Y - (opponent.y if opponent else 0)
            self.pillar_fx = {"x": tx, "life": a.get("life", PILLAR_LIFE),
                              "max": a.get("life", PILLAR_LIFE)}
            if opponent is not None and opponent.state != "ko":
                applied = opponent.take_hit(dmg, self)
                # DHARMA'S JUDGEMENT: 30 EXTRA frames of stun on top
                extra = a.get("extra_stun", EXTRA_STUN_FRAMES)
                if opponent.state == "hurt":
                    opponent.state_timer += extra
                    opponent.extra_stun = extra
                self.add_meter(applied)
            # column of blessed light raining down from the heavens
            made.extend(fx.create_divine_pillar(tx, ty, col, height=GROUND_Y))
            finish(flash_frames=FLASH_FRAMES)
            return

        # ================= TELEPORT (DURYODHANA · MAYAVI GADA) ==========
        if kind == "teleport":
            if opponent is not None and opponent.state != "ko":
                behind = opponent.x - opponent.facing * 70
                behind = max(BODY_LEFT_MARGIN,
                             min(SCREEN_WIDTH - BODY_LEFT_MARGIN, behind))
                self.teleport_fx = {"from_x": self.x, "at_x": behind,
                                    "life": a.get("life", TELEPORT_FLASH),
                                    "max": a.get("life", TELEPORT_FLASH)}
                self.x = behind
                self.facing = 1 if opponent.x > self.x else -1
                applied = opponent.take_hit(dmg, self)
                self.add_meter(applied)
                # illusion burst where he vanished + where he materialised
                made.extend(fx.create_divine_burst(
                    self.teleport_fx["from_x"], foot_y - 90, col, count=24))
                made.extend(fx.create_divine_burst(
                    opponent.x, GROUND_Y - opponent.y - 100, col,
                    count=random.randint(30, 40)))
                made.extend(fx.create_hit_sparks(
                    opponent.x, GROUND_Y - opponent.y - 100, col, count=15))
                fx.add_spark(opponent.x, GROUND_Y - opponent.y - 100,
                             16, col)
            else:
                self.teleport_fx = {"from_x": self.x, "at_x": self.x,
                                    "life": TELEPORT_FLASH,
                                    "max": TELEPORT_FLASH}
            finish(flash_frames=FLASH_FRAMES)     # purple illusion flash
            return

        # ================= ILLUSION (SHAKUNI · MAYA JAAL) ===============
        if kind == "illusion":
            dur_ms = a.get("life", int(MAYA_JAAL_SECONDS * FPS)) / FPS * 1000
            self.illusion_fx = {"life": a.get("life", 180),
                                "max": a.get("life", 180),
                                "offsets": [(-120, 0), (120, 0), (0, -40)]}
            if opponent is not None and opponent.state != "ko":
                applied = opponent.take_hit(dmg, self)
                self.add_meter(applied)
                # confuse the foe: their controls flip for 3 seconds
                opponent.controls_reversed_until = \
                    pygame.time.get_ticks() + dur_ms
            for ox, oy in self.illusion_fx["offsets"]:
                made.extend(fx.create_divine_burst(
                    self.x + ox, GROUND_Y - self.y - 90 + oy, col,
                    count=random.randint(12, 16)))
            finish(flash_frames=0)
            return

        # ---------- fallback: generic projectile ----------
        self.projectiles.append(
            self._make_projectile(hand_x, hand_y, self.facing * 13,
                                  damage=dmg))
        made.extend(fx.create_divine_burst(hand_x, hand_y, col, count=30))
        finish(flash_frames=0)

    def current_damage(self):
        """Damage table straight from the CHARACTERS database."""
        if self.state == "punch":
            return self.punch_damage
        if self.state == "kick":
            return self.kick_damage
        return self.special_damage

    def attack_range(self):
        """Melee reach depends on the strike — kicks travel further."""
        return 70 if self.state == "punch" else 95

    # ---------- combat: receiving damage ----------
    def take_hit(self, dmg, attacker=None):
        """Receive damage with the full hit-reaction pipeline:

          * BLOCKING  -> damage x (1 - 0.75), 10-frame block stun,
                         no combo credit for the attacker
          * HIT       -> white flash 15 frames, hit stun, knockback
                         AWAY from the attacker (slide + slight air pop)
          * health never drops below 0; KO locks the fighter down

        PARTICLE & VISUAL EFFECTS SYSTEM integration (all routed through
        self.fx so the fight scene drains them as camera requests):
          * every landed blow throws create_hit_sparks at chest height
          * HEAVY blows (>= HEAVY_HIT_THRESHOLD damage) add a mild
            create_blood_splash and queue a 3-5 frame HIT FREEZE
          * a KO fires a white FLASH overlay plus a violent screen SHAKE
        Returns the damage actually applied (used for sparks/meter)."""
        if self.state == "ko":
            return 0
        facing_in = attacker.facing if attacker is not None else self._last_attacker_facing(attacker)
        blocked = (self.state == "block") or \
                  (self.state == "crouch" and attacker is not None and
                   abs(self.x - attacker.x) < 140 and
                   attacker.state == "kick")   # crouching ducks punches

        chest_y = GROUND_Y - self.y - 100      # impact point for fx

        if blocked:
            applied = max(1, int(round(dmg * (1.0 - self.BLOCK_REDUCTION))))
            self.health = max(0, self.health - applied)
            self.block_stun = self.BLOCK_STUN_FRAMES      # 10 frozen frames
            self.vx = facing_in * 3                        # small push-back
            if self.fx is not None:                        # gold guard sparks
                self.fx.create_hit_sparks(self.x + facing_in * 30,
                                          chest_y, GOLD, count=8)
            return applied

        applied = int(dmg)
        self.health = max(0, self.health - applied)
        # SPECIAL METER also charges while RECEIVING damage (comeback astras)
        self.special_meter = min(100.0,
                                 self.special_meter +
                                 applied * self.meter_gain_taken)
        self.hit_flash = self.HIT_FLASH_FRAMES             # flash white 15f
        self.combo_count = 0                               # your own combo dies
        self.combo_timer = 0

        # ---- PARTICLE & VISUAL EFFECTS on a clean hit -----------------
        if self.fx is not None:
            self.fx.create_hit_sparks(self.x, chest_y, SAFFRON, count=15)
            if applied >= HEAVY_HIT_THRESHOLD:     # heavy blow: mild blood
                self.fx.create_blood_splash(self.x, chest_y)
                # hit-freeze slow-mo punch-in (3-5 frames, damage-scaled)
                self.fx.freeze(min(MAX_FREEZE_FRAMES,
                                   3 + applied // 12))

        if self.health <= 0:
            self.state = "ko"
            self.state_timer = 0
            self.vx = facing_in * 7
            self.vy = 4                                    # dramatic pop-up
            if self.fx is not None:                        # KO spectacle
                self.fx.flash(FLASH_FRAMES + 2)
                self.fx.shake(24, 12)
                self.fx.tint(self.special_color, TINT_FRAMES + 6)
                self.fx.create_divine_burst(self.x, chest_y,
                                            self.special_color, count=40)
                self.fx.freeze(6)
        else:
            self.state = "hurt"                            # hit stun
            self.state_timer = self.HIT_STUN
            self.vx = facing_in * 6                        # knockback slide
            self.vy = 2                                    # slight lift
        self._clamp_to_stage()
        return applied

    @staticmethod
    def _last_attacker_facing(attacker):
        return 1 if attacker is None else attacker.facing

    # ------------------------------------------------------------------
    # per-frame physics / animation update
    # ------------------------------------------------------------------
    def _clamp_to_stage(self):
        """Boundary clamping — a warrior can never leave the arena."""
        self.x = max(BODY_LEFT_MARGIN,
                     min(SCREEN_WIDTH - BODY_LEFT_MARGIN, self.x))

    def apply_gravity(self):
        """Vertical velocity + ground detection at y = GROUND_Y (offset 0).

        Two vertical channels are used:
          vel_y -> the fighter's own jump arc
          vy    -> knockback LIFT pushed by an opponent's strike
        Both feed the same position and stop dead on the ground line.

        PARTICLE & VISUAL EFFECTS integration: the exact frame a fighter
        touches back down after being airborne, create_ground_dust puffs
        brown smoke off the floor at their feet."""
        airborne = self.y > 0 or self.vel_y != 0 or self.vy != 0
        if airborne:
            self.vel_y -= GRAVITY
            self.vy -= GRAVITY * 0.6          # knockback lift falls sooner
            self.y += self.vel_y + self.vy
            if self.y <= 0:                   # touched down on the ground
                self.y, self.vel_y, self.vy = 0.0, 0.0, 0.0
                if self.state == "jump":
                    self.state = "idle"
                if self.fx is not None:       # landing dust puff
                    self.fx.create_ground_dust(self.x, GROUND_Y - 4)
        self.was_airborne = airborne

    def _emit_fx(self):
        """Per-frame PARTICLE AND VISUAL EFFECTS upkeep for this fighter:
          * subtle divine aura motes while the astral meter is FULL
          * weapon trail sparks during the active window of a swing"""
        fx = self.fx
        if fx is None:
            return
        fx.create_aura_particles(self)
        if self.is_attack_active():
            foot_y = GROUND_Y - self.y
            tip_x = self.x + self.facing * self.attack_range()
            tip_y = foot_y - (112 if self.state == "punch" else 60)
            fx.create_weapon_trail(tip_x, tip_y, self.special_color)

    def update(self, opponent):
        """One simulation step for this fighter (called once per frame)."""
        # --- jump / gravity physics ---
        self.apply_gravity()

        # --- knockback slide decay ---
        self.x += self.vx
        self.vx *= 0.8
        if abs(self.vx) < 0.3:
            self.vx = 0.0
        self._clamp_to_stage()

        # --- facing auto-updates to look at the opponent ---
        # (locked while committed to an attack, recoiling or KO'd)
        if opponent is not None and \
                self.state not in ("punch", "kick", "hurt", "ko"):
            self.facing = 1 if opponent.x > self.x else -1

        # --- attack / stun countdowns (per-frame, 60 FPS) ---
        if self.state_timer > 0:
            self.state_timer -= 1
            if self.state_timer == 0:
                if self.state in ("punch", "kick"):
                    self.is_channeling = False
                    self.state = "idle"
                elif self.state == "hurt":
                    self.state = "idle"       # hit stun over -> actionable

        # --- action cooldowns tick down every frame ---
        if self.punch_cooldown > 0:
            self.punch_cooldown -= 1
        if self.kick_cooldown > 0:
            self.kick_cooldown -= 1

        # --- block stun: frozen but still guarding ---
        if self.block_stun > 0:
            self.block_stun -= 1

        # --- white hit-flash timer ---
        if self.hit_flash > 0:
            self.hit_flash -= 1

        # --- COMBO SYSTEM: window decays; reset after 60 idle frames ---
        if self.combo_timer > 0:
            self.combo_timer -= 1
            if self.combo_timer == 0:
                self.combo_count = 0

        # --- SPECIAL MOVES SYSTEM: tick down astral effect lifetimes ---
        self._update_astra_effects()

        # --- advance the animation clock (bobbing / leg cycle) ---
        self.anim_time += 1.0

        # --- PARTICLE & VISUAL EFFECTS upkeep (aura / weapon trails) ---
        self._emit_fx()

        # --- AI control for player-less fighters ---
        if self.controls is None and opponent is not None:
            self.update_ai(opponent)

    # ---------- combo bookkeeping (used by the fight scene) ----------
    def register_hit(self, blocked=False):
        """Credit one landed hit toward this attacker's combo counter.

        Blocked hits do NOT extend a combo (they reset it), matching the
        'consecutive hits' rule.  The window refreshes to 60 frames on
        every clean hit."""
        if blocked:
            self.combo_count = 0
            self.combo_timer = 0
            return self.combo_count
        self.combo_count += 1
        self.combo_timer = self.COMBO_WINDOW      # 60-frame combo window
        return self.combo_count

    def add_meter(self, dmg):
        """Damage system: attacker charges the astral meter at 1.5x the
        damage actually dealt (capped at 100)."""
        self.special_meter = min(100.0,
                                 self.special_meter + dmg * self.METER_GAIN)

    # ------------------------------------------------------------------
    # SPECIAL MOVES SYSTEM — per-frame upkeep for lingering astral fx
    # ------------------------------------------------------------------
    def _update_astra_effects(self):
        """Decay the timers of every persistent special effect this
        fighter owns (vortex ring, beam, pillar, teleport flash and
        Shakuni's illusion copies).  Also keeps feeding the continuous
        PARTICLE & VISUAL EFFECTS while an astral is still on screen."""
        if self.extra_stun > 0:
            self.extra_stun -= 1
        for key in ("vortex", "beam_fx", "pillar_fx", "teleport_fx",
                    "illusion_fx"):
            fx = getattr(self, key)
            if fx is not None:
                fx["life"] -= 1
                if key == "vortex":
                    fx["angle"] = fx.get("angle", 0.0) + 0.45
                    fx["x"] = self.x          # vortex follows the spinner
                    fx["y"] = GROUND_Y - self.y - 80
                    # swirling energy wall feeding the whirlwind
                    if self.fx is not None:
                        a = fx["angle"]
                        r = fx["radius"] * (fx["life"] /
                                            max(1, fx["max_life"]))
                        self.fx.emit(fx["x"] + math.cos(a) * r,
                                     fx["y"] + math.sin(a) * r * 0.7,
                                     math.cos(a + 1.57) * 2.0,
                                     math.sin(a + 1.57) * 1.4,
                                     self.special_color, 16, 4,
                                     0.0, "energy")
                elif key == "beam_fx" and self.fx is not None:
                    # strobing lightning re-jagged every few frames
                    if fx["life"] % 3 == 0:
                        y = fx["y"]
                        fx["bolt"] = self.fx.create_lightning(
                            0, y, SCREEN_WIDTH, y, WHITE)
                elif key == "pillar_fx" and self.fx is not None:
                    # curtain of light still raining down while visible
                    self.fx.create_divine_pillar(
                        fx["x"], GROUND_Y - self.y, self.special_color,
                        height=GROUND_Y)
                if fx["life"] <= 0:
                    setattr(self, key, None)

    def vortex_rect(self):
        """Square hitbox of an active CHAKRAVYUHA BREAKER whirlwind."""
        v = self.vortex
        if v is None or v["hit"]:
            return None
        r = int(v["radius"])
        return pygame.Rect(int(v["x"] - r), int(v["y"] - r), r * 2, r * 2)

    def illusion_copies(self):
        """MAYA JAAL decoy positions (offsets relative to the caster)."""
        if self.illusion_fx is None:
            return []
        phase = self.illusion_fx["max"] - self.illusion_fx["life"]
        out = []
        for i, (ox, oy) in enumerate(self.illusion_fx["offsets"]):
            wob = math.sin(phase * 0.15 + i * 2.0) * 14
            out.append((self.x + ox + wob, GROUND_Y - self.y - 96 + oy))
        return out

    def update_ai(self, opponent):
        """Very simple aggressive AI so a solo player can fight someone."""
        if self._busy():
            return
        self.ai_decision_timer -= 1
        if self.ai_decision_timer > 0:
            return
        self.ai_decision_timer = random.randint(8, 20)

        dist = abs(self.x - opponent.x)
        roll = random.random()
        if self.special_meter >= 100 and roll < 0.55:
            # unleash the astral (fx=None => private particle system)
            self.start_special(opponent, None)
        elif dist > 110:
            # walk toward opponent at this warrior's own speed
            self.x += self.facing * max(2, self.speed)
            self.state = "walk"
        elif dist < 60 and roll < 0.25:
            self.x -= self.facing * max(2, self.speed)   # back off sometimes
        elif opponent.state in ("punch", "kick") and roll < 0.45:
            self.state = "block"               # try to guard
            self.block_stun = 15               # hold the guard a moment
        elif roll < 0.75:
            self.start_attack(random.choice(["punch", "kick"]))
        elif roll < 0.85 and self.y == 0:
            self.jump()                         # little hop
        else:
            self.state = "idle"

    # ==================================================================
    # DRAWING — a detailed procedural stick-figure WARRIOR
    # ==================================================================
    # Built entirely from pygame.draw primitives:
    #   head (circle + crown), torso (rect + sash), arms (lines + fists),
    #   legs (lines + feet), signature weapon silhouette, and a soft
    #   glowing aura tinted with the character's special_color.
    # ------------------------------------------------------------------
    def _draw_aura(self, target, cx, foot_y):
        """Pulsing translucent glow ring around the body, drawn in the
        character's special_color (brighter when the meter is full)."""
        pulse = 0.5 + 0.5 * math.sin(self.anim_time * 0.09)
        ready = self.special_meter >= 100
        base_alpha = 70 if not ready else 110
        layers = ((52, int(base_alpha * 0.35)),
                  (40, int(base_alpha * 0.6 + 14 * pulse)),
                  (28, int(base_alpha * 0.85 + 20 * pulse)))
        for radius, alpha in layers:
            surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*self.special_color, min(alpha, 255)),
                               (radius, radius), radius, 3)
            target.blit(surf, (cx - radius, int(foot_y - 82) - radius))

    def _draw_weapon(self, target, cx, foot_y, f, skin):
        """Signature weapon chosen from the database 'weapon' field."""
        wpn = str(self.weapon)
        if "Bow" in wpn:                    # Gandiva / Vijaya / divine bows
            pts = [(cx + f * 26, foot_y - 150), (cx + f * 40, foot_y - 115),
                   (cx + f * 26, foot_y - 80)]
            pygame.draw.lines(target, self.secondary_color, False, pts, 3)
            pygame.draw.line(target, GREY, pts[0], pts[2], 1)   # bowstring
        if "Gada" in wpn or "Mace" in wpn:  # Bhima / Duryodhana mace
            pygame.draw.line(target, (120, 80, 40),
                             (cx + f * 20, foot_y - 95),
                             (cx + f * 44, foot_y - 152), 5)
            pygame.draw.circle(target, self.secondary_color,
                               (cx + f * 47, foot_y - 157), 11)
            pygame.draw.circle(target, GOLD, (cx + f * 47, foot_y - 157),
                               11, 2)
        if "Spear" in wpn:                  # Yudhishthira's dharma spear
            pygame.draw.line(target, (120, 80, 40),
                             (cx + f * 18, foot_y - 70),
                             (cx + f * 46, foot_y - 165), 4)
            pygame.draw.polygon(target, self.secondary_color,
                                [(cx + f * 42, foot_y - 158),
                                 (cx + f * 52, foot_y - 178),
                                 (cx + f * 50, foot_y - 156)])
        if "Sword" in wpn:                  # Abhimanyu / Ashwatthama blade
            pygame.draw.line(target, (200, 200, 215),
                             (cx + f * 22, foot_y - 105),
                             (cx + f * 44, foot_y - 155), 4)
            pygame.draw.line(target, GOLD, (cx + f * 18, foot_y - 100),
                             (cx + f * 28, foot_y - 108), 4)   # guard
        if "Dice" in wpn:                   # Shakuni's enchanted dice
            t = self.anim_time * 0.12
            dcx = cx + f * 34 + int(3 * math.sin(t))
            dcy = foot_y - 118 + int(3 * math.cos(t))
            pygame.draw.rect(target, self.secondary_color,
                             (dcx - 8, dcy - 8, 16, 16), border_radius=3)
            for px, py in ((-4, -4), (0, 0), (4, 4)):
                pygame.draw.circle(target, BLACK, (dcx + px, dcy + py), 2)
        if "Kavach" in wpn or "Gem" in wpn:  # divine armour / forehead gem
            pygame.draw.circle(target, GOLD, (cx + f * 4, foot_y - 146), 4)

    def draw(self, target):
        f = self.facing
        cx = int(self.x)
        foot_y = int(GROUND_Y - self.y)
        skin = self.secondary_color          # limb / face tint
        leg_w, arm_w = 6, 5

        # ---- crouch compresses the whole skeleton proportionally ----
        squash = 0.62 if self.state == "crouch" else 1.0
        hip_y = foot_y - int(70 * squash)
        chest_y = foot_y - int(118 * squash)
        neck_y = foot_y - int(128 * squash)
        head_y = foot_y - int(142 * squash)

        # ---- idle bobbing (math.sin) & walking leg cycle ----
        bob = 0
        if self.state == "idle":
            bob = int(2.5 * math.sin(self.anim_time * 0.07))
        sway = 0
        if self.state == "walk":
            sway = int(7 * math.sin(self.anim_time * 0.25))
        # apply bob to everything above the hips
        hip_y += bob // 2
        chest_y += bob
        neck_y += bob
        head_y += bob

        # ---- MAYA JAAL: ghostly decoy copies flanking the caster ----
        for ix, iy in self.illusion_copies():
            ghost = pygame.Surface((46, STAND_HEIGHT), pygame.SRCALPHA)
            pygame.draw.circle(ghost, (*self.special_color, 70),
                               (23, 20), 13)
            pygame.draw.rect(ghost, (*self.color, 60),
                             (11, 38, 24, 62), border_radius=8)
            pygame.draw.line(ghost, (*self.secondary_color, 70),
                             (23, 100), (13, 146), 5)
            pygame.draw.line(ghost, (*self.secondary_color, 70),
                             (23, 100), (33, 146), 5)
            target.blit(ghost, (int(ix) - 23, int(iy) - STAND_HEIGHT))

        # ---- ground shadow (stays put while jumping) ----
        sh_scale = max(0.4, 1.0 - self.y / 260.0)
        sw = int(90 * sh_scale)
        sh = pygame.Surface((sw, 16), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, int(90 * sh_scale)),
                            (0, 0, sw, 16))
        target.blit(sh, (cx - sw // 2, GROUND_Y - 8))

        # ---- glowing astral aura (special_color; blazes when READY) ----
        self._draw_aura(target, cx, foot_y)
        # MAYA JAAL aftermath: shimmering violet ring while controls flip
        if pygame.time.get_ticks() < self.controls_reversed_until:
            _glow(target, cx, foot_y - 80, 62, (190, 90, 255), 70)

        # ---- legs (lines) + feet (small rects) ----
        # KICK VISUAL: the front leg extends outward.  Progress runs 0->1
        # across the 25-frame cycle; the leg snaps out fast and retracts.
        kick_ext = 0
        if self.state == "kick":
            progress = 1.0 - self.state_timer / max(1, self.attack_total)
            kick_ext = int(math.sin(min(1.0, progress * 1.15) * math.pi) * 62)
        if self.state != "kick":
            # left leg
            lx = cx - 14 + sway
            pygame.draw.line(target, skin, (cx, hip_y), (lx, foot_y), leg_w)
            pygame.draw.rect(target, GOLD, (lx - 7, foot_y - 4, 14, 6),
                             border_radius=2)          # foot
            # right leg
            rx = cx + 14 - sway
            pygame.draw.line(target, skin, (cx, hip_y), (rx, foot_y), leg_w)
            pygame.draw.rect(target, GOLD, (rx - 7, foot_y - 4, 14, 6),
                             border_radius=2)          # foot
        else:
            # support leg
            pygame.draw.line(target, skin, (cx, hip_y),
                             (cx - 12, foot_y), leg_w)
            pygame.draw.rect(target, GOLD, (cx - 19, foot_y - 4, 14, 6),
                             border_radius=2)
            # extended kicking leg + foot
            kx = cx + f * (25 + kick_ext)
            ky = foot_y - int(55 * squash)
            pygame.draw.line(target, skin, (cx, hip_y), (kx, ky), leg_w)
            # FOOT VISUAL: glows yellow while the kick hitbox is active
            foot_glow = self.is_attack_active()
            fc = GOLD if foot_glow else self.secondary_color
            pygame.draw.rect(target, fc, (kx - 6, ky - 4, 14, 7),
                             border_radius=2)

        # ---- torso (rectangle = battle tunic) ----
        torso_h = int(58 * squash)
        pygame.draw.rect(target, self.color,
                         (cx - 16, chest_y - 7, 32, torso_h),
                         border_radius=8)
        # golden armour sash across the chest
        pygame.draw.line(target, GOLD, (cx - 16, chest_y + torso_h - 18),
                         (cx + 16, chest_y - 2), 4)

        # ---- head (circle) + crown/mukut ----
        pygame.draw.circle(target, skin, (cx, head_y), 15)
        pygame.draw.polygon(target, GOLD, [(cx - 12, head_y - 6),
                                           (cx, head_y - 26),
                                           (cx + 12, head_y - 6)])
        # eye looking in facing direction
        pygame.draw.circle(target, BLACK, (cx + f * 6, head_y - 2), 2)

        # ---- signature weapon (bow/mace/sword/spear/dice) ----
        self._draw_weapon(target, cx, foot_y, f, skin)

        # ---- arms (lines) + fists (circles), pose per state ----
        shoulder_l = (cx - 15, chest_y)
        shoulder_r = (cx + 15, chest_y)

        # During an attack's ACTIVE WINDOW the fist / foot glows yellow.
        active_now = self.is_attack_active()
        fist_col = GOLD if active_now else skin
        foot_col = GOLD if active_now else self.secondary_color

        def glow_dot(px, py, radius=8):
            """Small yellow energy halo around a striking limb."""
            g = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(g, (*GOLD, 190), (radius, radius), radius)
            target.blit(g, (px - radius, py - radius))

        if self.is_channeling:
            # SPECIAL: both arms thrust forward channeling the astral weapon
            glow = int(20 + 12 * math.sin(self.state_timer * 0.5))
            end = (cx + f * 55, chest_y + 6)
            pygame.draw.line(target, skin, shoulder_l, end, arm_w)
            pygame.draw.line(target, skin, shoulder_r, end, arm_w)
            pygame.draw.circle(target, GOLD, end, 6)      # joined fists
            aura = pygame.Surface((glow * 2, glow * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura, (*self.special_color, 160),
                               (glow, glow), glow)
            target.blit(aura, (end[0] - glow, end[1] - glow))
        elif self.state == "punch":
            # PUNCH VISUAL: arm extends forward over the 20-frame cycle.
            progress = 1.0 - self.state_timer / max(1, self.attack_total)
            ext = int(math.sin(min(1.0, progress * 1.1) * math.pi) * 48)
            end = (cx + f * (28 + ext), chest_y + 6)
            front_shoulder = shoulder_r if f > 0 else shoulder_l
            pygame.draw.line(target, skin, front_shoulder, end, arm_w)
            pygame.draw.circle(target, fist_col, end, 7)   # fist
            if active_now:
                glow_dot(end[0], end[1])                   # glowing knuckles
            back = shoulder_l if f > 0 else shoulder_r
            pygame.draw.line(target, skin, back,
                             (cx - f * 12, chest_y + 22), arm_w)
            pygame.draw.circle(target, skin,
                               (cx - f * 12, chest_y + 24), 5)
        elif self.state == "kick":
            pygame.draw.line(target, skin, (cx, chest_y),
                             (cx - f * 18, chest_y + 18), arm_w)
            pygame.draw.line(target, skin, shoulder_l if f > 0 else
                             shoulder_r, (cx + f * 10, chest_y + 24), arm_w)
        elif self.state == "block":
            # Guard arms raised + a shield ARC drawn in front of the body
            pygame.draw.line(target, skin, shoulder_l,
                             (cx + f * 8, neck_y - 6), arm_w)
            pygame.draw.line(target, skin, shoulder_r,
                             (cx + f * 10, chest_y), arm_w)
            shield = pygame.Surface((56, 130), pygame.SRCALPHA)
            arc_cx = 28 if f > 0 else 28
            pygame.draw.arc(shield, (*GOLD, 230),
                            (arc_cx - 26, 6, 52, 118),
                            -1.15 if f > 0 else math.pi - 1.15,
                            1.15 if f > 0 else math.pi + 1.15, 4)
            inner = (*SAFFRON, 90) if self.block_stun == 0 else (*WHITE, 150)
            pygame.draw.arc(shield, inner,
                            (arc_cx - 18, 16, 36, 98),
                            -1.15 if f > 0 else math.pi - 1.15,
                            1.15 if f > 0 else math.pi + 1.15, 3)
            target.blit(shield, (cx + f * 16 - (0 if f > 0 else 56),
                                 neck_y - 20))
        elif self.state == "crouch":
            # arms tucked low, guarding stance
            pygame.draw.line(target, skin, shoulder_l,
                             (cx - f * 4, hip_y - 6), arm_w)
            pygame.draw.line(target, skin, shoulder_r,
                             (cx + f * 12, hip_y - 10), arm_w)
            pygame.draw.circle(target, GOLD, (cx + f * 12, hip_y - 10), 5)
        else:
            # relaxed guard: fists held at sides
            el = (cx - 18, chest_y + 28)
            er = (cx + 18, chest_y + 28)
            pygame.draw.line(target, skin, shoulder_l, el, arm_w)
            pygame.draw.line(target, skin, shoulder_r, er, arm_w)
            pygame.draw.circle(target, GOLD, el, 5)       # fists
            pygame.draw.circle(target, GOLD, er, 5)

        # ---- WHITE HIT FLASH (15 frames after taking a clean hit) ----
        if self.hit_flash > 0:
            alpha = int(150 * (self.hit_flash / self.HIT_FLASH_FRAMES))
            flash = pygame.Surface((64, STAND_HEIGHT + 12), pygame.SRCALPHA)
            pygame.draw.rect(flash, (255, 255, 255, alpha), flash.get_rect(),
                             border_radius=12)
            target.blit(flash, (cx - 32, foot_y - STAND_HEIGHT - 6))

        # ---- KO: slumped silhouette on the battlefield ----
        if self.state == "ko":
            pygame.draw.line(target, skin, (cx - f * 30, GROUND_Y - 10),
                             (cx + f * 30, GROUND_Y - 6), 8)
            pygame.draw.circle(target, skin, (cx + f * 38, GROUND_Y - 10), 12)

        # ---- name tag (P1/P2 prefix so sides are obvious) ----
        label = ("P2 · " if self.is_player2 else "P1 · ") + self.name
        draw_centered_text(target, label, FONT_SMALL, WHITE, cx,
                           foot_y - STAND_HEIGHT - 38, shadow=True)


# =====================================================================
# SECTION 5: CHARACTER DATABASE — the 10 legendary warriors of the epic
# =====================================================================
# Every entry is a self-contained data record used by character select,
# the fight scene (stats/damage/specials) and the dialogue banners.
#   health / speed           -> base combat stats (speed = px per frame)
#   punch/kick/special_damage -> damage values per attack type
#   intro_dialogue           -> list of 2 dramatic Hindi-English lines
#   special_color            -> colour of the astral projectile FX

CHARACTERS = {

    # ---- 1. ARJUNA : the peerless archer, Krishna's chosen instrument
    "ARJUNA": {
        "name": "ARJUNA",
        "color": (25, 60, 160),                 # royal blue
        "secondary_color": (120, 160, 235),     # sky-blue highlights
        "health": 100,
        "speed": 6,
        "punch_damage": 8,
        "kick_damage": 13,
        "special_damage": 22,                   # PWR 22
        "special_name": "BRAHMASTRA",
        "special_color": (255, 230, 120),       # blinding divine white-gold
        "intro_dialogue": [
            "Gandiva ko jhuka kar main ek hi lakshya dekhta hoon — sirf tera!",
            "Madhava ne kaha — 'Dharma yuddh hai'; ab baanh bolegi, vaada nahi!"
        ],
        "win_dialogue": "Jeet meri nahi, Keshav ki saarthi mein hai — rathi safal hua.",
        "lose_dialogue": "Haar gaya… par Krishna ka rath kabhi haar nahi maanta.",
        "special_dialogue": "BRAHMASTRA! Ek baanh, ek divya aag — Agni bhi shant ho jaaye!",
        "taunt": "Paanch senaon ko akela jhel chuka hoon — tu kaun? Ek baanh, khatam!",
        "description": "Pandava prince and invincible archer, student of Drona, "
                       "friend of Krishna. With the celestial bow Gandiva he never "
                       "missed — his focus can split a falling leaf's eye.",
        "weapon": "Gandiva Bow",
        "epithet": "The Peerless Archer",
    },

    # ---- 2. KARNA : sun-born, generous, tragic, proud
    "KARNA": {
        "name": "KARNA",
        "color": (214, 160, 30),                # golden yellow
        "secondary_color": (255, 220, 130),     # radiant gold
        "health": 105,
        "speed": 5,
        "punch_damage": 9,
        "kick_damage": 14,
        "special_damage": 25,                   # PWR 25
        "special_name": "SHAKTI ASTRA",
        "special_color": (255, 140, 40),        # Indra's thunderbolt orange
        "intro_dialogue": [
            "Kavach-Kundal se saja hoon — Surya ka putr hoon, suraj se darta nahi!",
            "Daanveer kehlaya, dosti nibhaai — aaj Vijaya ek hi cheez maangegi: tera ghamand!"
        ],
        "win_dialogue": "Vijaya ne sach bola — vidhataan aaj mere paksha jhuk gayi!",
        "lose_dialogue": "Shraap toh lagta hi hai mere naam par… phir bhi ladta rahunga.",
        "special_dialogue": "SHAKTI ASTRA! Rudra ka garaj le kar aaya hoon — dekh, aakash jhuk jaata hai!",
        "taunt": "Daan mein sab kuch deta hoon — aaj tujhe daan mein teri haar milenge!",
        "description": "Radheya — sun-born warrior, king of Anga, sworn friend of "
                       "Duryodhana. Born with divine armour and earrings, cursed yet "
                       "unbroken; his pride, generosity and loyalty are legend.",
        "weapon": "Vijaya Bow + Kavach-Kundal",
        "epithet": "Sun-Born, Daanveer",
    },

    # ---- 3. BHIMA : the wind son, mace of rage
    "BHIMA": {
        "name": "BHIMA",
        "color": (140, 25, 25),                 # dark red
        "secondary_color": (210, 90, 60),       # burnt copper
        "health": 140,
        "speed": 3,
        "punch_damage": 12,
        "kick_damage": 18,
        "special_damage": 30,                   # PWR 30
        "special_name": "MAHAGADA PRHAR",
        "special_color": (200, 60, 30),         # earthquake crimson
        "intro_dialogue": [
            "Vayu ke putr hoon! Bhookh lagi hai Kurukshetra ki — aur woh bhookh tu hai!",
            "Duryodhana yaad rakh — kali gaddi ka hisaab aaj gada se hoga!"
        ],
        "win_dialogue": "Gada chali, dharti kaanpi — adharma ka hisaab barabar!",
        "lose_dialogue": "Yeh gada thak gayi… par Bhima ka gussa kabhi nahi thakta.",
        "special_dialogue": "MAHAGADA PRHAR! Aasman-zameen ek ho jaayega — uth, aur dekh Dhartiraj kaanpte hue!",
        "taunt": "Aaj tere paas do raaste hain — bhaag, ya mera naashta ban ja!",
        "description": "Mightiest of the Pandavas, son of the Wind God Vayu. Wielder "
                       "of the giant gada, slayer of Keechaka and Dushasana — his rage "
                       "is an element of nature itself.",
        "weapon": "Gada (Mace)",
        "epithet": "Wind Son, Mighty Arms",
    },

    # ---- 4. DURYODHANA : proud emperor, unmatched mace-king
    "DURYODHANA": {
        "name": "DURYODHANA",
        "color": (75, 35, 120),                 # dark purple
        "secondary_color": (150, 100, 200),     # violet sheen
        "health": 130,
        "speed": 4,
        "punch_damage": 11,
        "kick_damage": 16,
        "special_damage": 28,                   # PWR 28
        "special_name": "MAYAVI GADA",
        "special_color": (170, 90, 220),        # illusion purple
        "intro_dialogue": [
            "Yeh swarg ka rajya nahi — Hastinapur ka simhasan hai, aur woh MERA hai!",
            "Pandavon ne paasaa khela, humne rajya haara — aaj gada se wapsi hogi!"
        ],
        "win_dialogue": "Dekha? Jis gada ne Bharat jeeta, woh tukde-tukde karti hai rakht ko!",
        "lose_dialogue": "Ranbhoomi mein gira raja… par Hastinapur ka ahankaar kabhi nahi marta.",
        "special_dialogue": "MAYAVI GADA! Mayavi vaar — kahan se aayi gada? Jahan dekhega, wahin tootega!",
        "taunt": "Ekla chala re? Aaj ekla CHALU main hoon — aur tu hawa mein ud jaayega!",
        "description": "Kaurava emperor, invincible mace-fighter, shielded by "
                       "Shakuni's cunning and feared even by Bhishma. His pride lost "
                       "a war — but never a single duel on his own terms.",
        "weapon": "Gada",
        "epithet": "Crown Prince, Gada King",
    },

    # ---- 5. BHISHMA : grandfather, oath-bound, iccha-mrityu
    "BHISHMA PITAMAH": {
        "name": "BHISHMA PITAMAH",
        "color": (185, 190, 200),               # silver / white
        "secondary_color": (230, 235, 245),     # bright silver
        "health": 120,
        "speed": 4,
        "punch_damage": 9,
        "kick_damage": 15,
        "special_damage": 26,                   # PWR 26
        "special_name": "PRATIGYA ASTRA",
        "special_color": (210, 235, 255),       # icy oathsilver
        "intro_dialogue": [
            "Bhishma ka pratigya hai — satya par likha, khoon se nahi mitne wala!",
            "Dono senaayein mere pota hain… aaj arthon ki baanh har dil ko chaati hai."
        ],
        "win_dialogue": "Pratigya nibh gayi — par jeet-haar se bada mera vachan hai.",
        "lose_dialogue": "Sharson ka shayan tay hai… ab iccha mrityu ka samay dekhna hai.",
        "special_dialogue": "PRATIGYA ASTRA! Meri kasam ka har baanh — akshay, anant, amar!",
        "taunt": "Main shayan par baitha hoon aur phir bhi tum sabke guru hoon — utho, ladai seekho!",
        "description": "Devavrata who became Bhishma — terrible for his terrible oath. "
                       "Commander of the Kaurava host, master of every weapon, holder of "
                       "iccha-mrityu: death only when he himself chooses it.",
        "weapon": "Divine Bow",
        "epithet": "Grandfather, Oathbound",
    },

    # ---- 6. ABHIMANYU : the chakravyuha breaker
    "ABHIMANYU": {
        "name": "ABHIMANYU",
        "color": (0, 180, 210),                 # bright cyan
        "secondary_color": (140, 240, 255),     # ice-cyan glow
        "health": 85,
        "speed": 8,
        "punch_damage": 7,
        "kick_damage": 11,
        "special_damage": 20,                   # PWR 20
        "special_name": "CHAKRAVYUHA BREAKER",
        "special_color": (90, 240, 255),        # vortex cyan
        "intro_dialogue": [
            "Solah varsh ka balak hoon — par vyuh ka rahasya mere khoon mein hai!",
            "Andar aana easy tha… bahar nikalna — wahi asli yuddh hai, jaan le!"
        ],
        "win_dialogue": "Chakravyuha mera hai aaj — aur aaj uska ant bhi mera hai!",
        "lose_dialogue": "Saat veer ghair… par ek baanh yaad rakhegi — tu Abhimanyu ko bhulayega nahi.",
        "special_dialogue": "CHAKRAVYUHA BREAKER! Ghoomti baanhon ka bhawansagar — jo andar gaya, woh bahar nahi!",
        "taunt": "Vyuh rachna dekh raha hai? Main use todte hue bhi jeet jaata hoon!",
        "description": "Arjuna's son, Subhadra's pride. He entered the impenetrable "
                       "Chakravyuha alone as a boy of sixteen and made the greatest "
                       "warriors of the age beg for combined honour.",
        "weapon": "Sword & Bow",
        "epithet": "Lotus of the Vortex",
    },

    # ---- 7. DRONACHARYA : guru of both armies
    "DRONACHARYA": {
        "name": "DRONACHARYA",
        "color": (20, 110, 50),                 # forest green
        "secondary_color": (90, 190, 120),      # leaf green
        "health": 95,
        "speed": 5,
        "punch_damage": 8,
        "kick_damage": 12,
        "special_damage": 24,                   # PWR 24
        "special_name": "NARAYANASTRA",
        "special_color": (255, 200, 90),        # Vishnu's saffron-gold
        "intro_dialogue": [
            "Dono taraf mere shishya — kisi ko bachaunga nahi, kisi ko chhodunga nahi!",
            "Guru dakshina ke liye yeh haath utha hain — aaj vidya ka fal chakhna padega."
        ],
        "win_dialogue": "Shishyo ko harana gurudakshina hai — vidyadaan pura hua.",
        "lose_dialogue": "Ashwatthama… putra… guru bhi rota hai jab sansar dharm bhool jaata hai.",
        "special_dialogue": "NARAYANASTRA! Vaikunth ki jyoti ka pravaah — ek baanh, anant roop!",
        "taunt": "Maine tumhe yuddh sikhaya — aaj usi vidya se tumhant hota hai. Seekho, phir ladna!",
        "description": "Drona, brahmin warrior and acharya of the Kuru princes — teacher "
                       "of Arjuna and Karna alike. Bound by debt to Hastinapur, torn by "
                       "love for his shishyas, master of the celestial Narayanastra.",
        "weapon": "Divine Bow",
        "epithet": "Guru of Both Armies",
    },

    # ---- 8. ASHWATTHAMA : the cursed immortal fury
    "ASHWATTHAMA": {
        "name": "ASHWATTHAMA",
        "color": (130, 15, 40),                 # dark crimson
        "secondary_color": (200, 60, 80),       # blood rose
        "health": 115,
        "speed": 5,
        "punch_damage": 10,
        "kick_damage": 15,
        "special_damage": 27,                   # PWR 27
        "special_name": "BRAHMASHIRA",
        "special_color": (255, 60, 60),         # annihilation red
        "intro_dialogue": [
            "Maathe ki manik jagmagati hai — aur mere shraap ki aag ab bujhi nahi!",
            "Guru ke pitra ka badla loonga — Brahmashira se, amar dard se!"
        ],
        "win_dialogue": "Jeet ka moh nahi — shraap amar hai, aur mera kaam abhi baaki hai.",
        "lose_dialogue": "Haar? Mujhe haar nahi milti — bas yug baar-baar badal jaata hai.",
        "special_dialogue": "BRAHMASHIRA! Srishti ka ant dene wali baanh — Madhava hi bacha sake toh bacha!",
        "taunt": "Hazaron saal tak zameen par ghoothe rahega — aaj bas ek jhalak dekh le!",
        "description": "Drona's son, avatar of Mahakala's fury, bearer of the forehead "
                       "gem. After the Brahmashira he was cursed by Krishna to wander "
                       "the earth, immortal and festering, until the end of the Kali Yuga.",
        "weapon": "Divine Sword + Gem on forehead",
        "epithet": "The Cursed Immortal",
    },

    # ---- 9. YUDHISHTHIRA : dharma's own son
    "YUDHISHTHIRA": {
        "name": "YUDHISHTHIRA",
        "color": (235, 235, 225),               # pure white
        "secondary_color": (240, 200, 90),      # gold trim
        "health": 100,
        "speed": 5,
        "punch_damage": 6,
        "kick_damage": 10,
        "special_damage": 18,                   # PWR 18
        "special_name": "DHARMA ASTRA",
        "special_color": (255, 240, 170),       # righteous warm light
        "intro_dialogue": [
            "Dharmraj kehte hain mujhe — bhed nahi, bhay nahi, bas satya ka path!",
            "Rajya mila, ladhna pada — kshama maangta hoon, par kadam nahi hataunga."
        ],
        "win_dialogue": "Dharma ki jeet hai yeh — Yudhishthira ne kuch nahi jeeta, sabko khoya hai.",
        "lose_dialogue": "Satyavat hoke bhi haar jaun — toh phir satya hi ant mein jeetega.",
        "special_dialogue": "DHARMA ASTRA! Jis paksha dharm ka, usi paksha yeh baanh — adharma ka naash!",
        "taunt": "Main jhooth bolkar bhi rajya bacha sakta tha — tumhare liye toh sach hi kaafi hai!",
        "description": "Son of Dharma, eldest Pandava, unshakeable in truth. His spear "
                       "never sought glory — only justice; even Yamraja bowed before his "
                       "uncompromising righteousness.",
        "weapon": "Spear of Dharma",
        "epithet": "Dharmraj, Son of Justice",
    },

    # ---- 10. SHAKUNI : the dice that drowned a kingdom
    "SHAKUNI": {
        "name": "SHAKUNI",
        "color": (60, 100, 45),                 # sickly green
        "secondary_color": (25, 28, 22),        # sooty black-green
        "health": 75,
        "speed": 7,
        "punch_damage": 5,
        "kick_damage": 9,
        "special_damage": 15,                   # PWR 15
        "special_name": "MAYA JAAL",
        "special_color": (140, 220, 120),       # venomous illusion green
        "intro_dialogue": [
            "Paase phekta hoon — aur teen lok ka itihaas palat jaata hai!",
            "Bal se nahi, buddhi se yuddh jeete jaate hain… tum dono haare hue lagte ho."
        ],
        "win_dialogue": "Jeet? Jeet toh wahi karta hai jiske paase uske niyam likhe hon.",
        "lose_dialogue": "Ek chaal bigad gayi… par Shakuni ki sharti kabhi khatam nahi hoti.",
        "special_dialogue": "MAYA JAAL! Jhooth ka jaal, sach ka dard — idhar dekho… nahin, Udhar dekho!",
        "taunt": "Tum ladai lad rahe ho, main pehle se bahut khel chuka hoon — haaro mat, seekho!",
        "description": "Master strategist of Gandhara and architect of the fateful game "
                       "of dice. With loaded dice forged from his family's grief, one "
                       "throw of his set the whole Mahabharat war ablaze.",
        "weapon": "Enchanted Dice",
        "epithet": "Rolls Fate, Weaves Lies",
    },
}



# --- ROSTER: ordered view of the database for the selection grid ---------
ROSTER = [CHARACTERS[key] for key in [
    "ARJUNA", "KARNA", "BHIMA", "DURYODHANA", "BHISHMA PITAMAH",
    "ABHIMANYU", "DRONACHARYA", "ASHWATTHAMA", "YUDHISHTHIRA", "SHAKUNI",
]]


def get_character(name):
    """Look up a full character record by name (safe fallback)."""
    return CHARACTERS.get(name, ROSTER[0])


# ---------------------------------------------------------------------
# PLAYER CONTROL MAPS  (spec: P1 = Arrow keys + Z/X,  P2 = IJKL + B/N)
#   "back" = the direction AWAY from the opponent; holding back + down
#   activates BLOCKING (classic fighting-game guard).
# ---------------------------------------------------------------------
P1_KEYS = {
    pygame.K_LEFT:   "left",       # arrow keys
    pygame.K_RIGHT:  "right",
    pygame.K_UP:     "jump",
    pygame.K_DOWN:   "back_down",  # crouch in place / block when held w/ back
    pygame.K_z:      "punch",      # fast, low damage  (20-frame cooldown)
    pygame.K_x:      "kick",       # medium, more dmg + longer range (25f)
}
P2_KEYS = {
    pygame.K_i:      "up",         # I J K L layout: I=jump
    pygame.K_j:      "left",
    pygame.K_k:      "down",       # crouch / block-with-back
    pygame.K_l:      "right",
    pygame.K_b:      "punch",      # B = punch
    pygame.K_n:      "kick",       # N = kick
}


# =====================================================================
# SECTION 5B: SPECIAL MOVES SYSTEM — ASTRA REGISTRY
# =====================================================================
# Every character's signature weapon is a UNIQUE special, driven by the
# full 100-point special meter.  The registry maps each fighter name to
# its behaviour; anything missing falls back to a generic projectile so
# custom characters still work.
#
#   kind == "projectile" : flies straight, one hit (arrow / bolt / disc)
#   kind == "barrage"    : spawns several small projectiles in a spread
#   kind == "shockwave"  : travels along the ground (mace slam)
#   kind == "vortex"     : spinning hitbox around the caster (30 frames)
#   kind == "beam"       : instant energy beam across the whole screen
#   kind == "pillar"     : pillar of light drops on the opponent + stun
#   kind == "teleport"   : blink behind the foe and strike
#   kind == "illusion"   : damage + reverse the opponent's controls 3 s
# =====================================================================

CAST_FRAMES = 24            # channeling/pose duration for any special
VORTEX_LIFE = 30            # CHAKRAVYUHA BREAKER spin window (frames)
MAYA_JAAL_SECONDS = 3.0     # SHAKUNI's control-reversal duration
EXTRA_STUN_FRAMES = 30      # YUDHISHTHIRA adds this stun on top of hitstun
BEAM_LIFE = 18              # BRAHMASHIRA beam visible frames
PILLAR_LIFE = 34            # DHARMA ASTRA light-pillar visible frames
TELEPORT_FLASH = 16         # MAYAVI GADA purple flash frames

ASTRAS = {
    # ---------------- PROJECTILE SPECIALS (archers) ----------------
    "ARJUNA": dict(                       # BRAHMASTRA — divine arrow
        kind="projectile", damage=25, speed=13, size=(74, 16),
        shape="arrow", trail="particles", shake=14, shake_power=9,
        glow_layers=((30, 70), (20, 130), (11, 255)),
    ),
    "KARNA": dict(                        # SHAKTI ASTRA — lightning bolt
        kind="projectile", damage=28, speed=15, size=(56, 56),
        shape="bolt", trail="crackle", shake=12, shake_power=8,
        glow_layers=((30, 70), (19, 130), (10, 255)),
    ),
    "BHISHMA PITAMAH": dict(              # PRATIGYA ASTRA — 3-arrow spread
        kind="barrage", damage=10, speed=14, size=(40, 10),
        shape="arrow", count=3, spread=52, shake=8, shake_power=5,
        glow_layers=((18, 60), (12, 120), (6, 255)),
    ),
    "DRONACHARYA": dict(                  # NARAYANASTRA — spinning disc
        kind="projectile", damage=24, speed=12, size=(44, 44),
        shape="disc", trail="spin", shake=10, shake_power=7,
        glow_layers=((26, 70), (17, 130), (9, 255)),
    ),
    # ---------------- MELEE SPECIALS (mace / sword users) ----------------
    "BHIMA": dict(                        # MAHAGADA PRHAR — ground shockwave
        kind="shockwave", damage=30, speed=10, size=(70, 92),
        shape="wall", life=90, shake=26, shake_power=14,
        glow_layers=((34, 80), (22, 150), (12, 255)),
    ),
    "DURYODHANA": dict(                   # MAYAVI GADA — teleport back-strike
        kind="teleport", damage=28, life=TELEPORT_FLASH,
        shake=12, shake_power=8,
    ),
    "ABHIMANYU": dict(                    # CHAKRAVYUHA BREAKER — vortex
        kind="vortex", damage=20, radius=120, life=VORTEX_LIFE,
        shake=10, shake_power=6,
    ),
    # ---------------- UNIQUE SPECIALS ----------------
    "ASHWATTHAMA": dict(                  # BRAHMASHIRA — full-screen beam
        kind="beam", damage=30, life=BEAM_LIFE, shake=25, shake_power=13,
    ),
    "YUDHISHTHIRA": dict(                 # DHARMA ASTRA — pillar of judgement
        kind="pillar", damage=22, life=PILLAR_LIFE, extra_stun=30,
        shake=12, shake_power=7,
    ),
    "SHAKUNI": dict(                      # MAYA JAAL — illusion trap
        kind="illusion", damage=10, life=int(MAYA_JAAL_SECONDS * FPS),
        shake=6, shake_power=4,
    ),
}

DEFAULT_ASTRA = dict(kind="projectile", damage=25, speed=13, size=(60, 16),
                     shape="arrow", shake=10, shake_power=6,
                     glow_layers=((26, 70), (17, 130), (10, 255)))


def get_astra(name):
    """Fetch this warrior's astral recipe (safe fallback for customs)."""
    return ASTRAS.get(name, DEFAULT_ASTRA)


# ---------------------------------------------------------------------
# ASTRA VISUAL SHAPES — every projectile is drawn with pure pygame.draw
# primitives so each divine weapon looks unique on the battlefield.
# ---------------------------------------------------------------------

def _glow(target, x, y, radius, color, alpha=180):
    """Soft translucent halo used by all astral effects."""
    radius = max(2, int(radius))
    g = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    pygame.draw.circle(g, (*color, alpha), (radius, radius), radius)
    target.blit(g, (int(x) - radius, int(y) - radius))


def draw_arrow_shape(target, x, y, facing, col, gold=GOLD, scale=1.0):
    """Divine arrow: shaft + arrowhead + fletching, pointing along facing."""
    ln = int(46 * scale)
    tip_x = x + facing * (ln // 2)
    tail_x = x - facing * (ln // 2)
    pygame.draw.line(target, gold, (tail_x, y), (tip_x, y),
                     max(2, int(4 * scale)))
    head = int(14 * scale)
    pygame.draw.polygon(target, col, [(tip_x + facing * head, y),
                                      (tip_x, y - head // 2),
                                      (tip_x, y + head // 2)])
    # fletching feathers
    for off in (-int(6 * scale), int(6 * scale)):
        pygame.draw.line(target, col, (tail_x, y),
                         (tail_x - facing * 8, y + off),
                         max(2, int(3 * scale)))
    _glow(target, tip_x, y, 10 * scale, col, 120)


def draw_bolt_shape(target, x, y, facing, col, t=0.0):
    """Crackling lightning bolt (zigzag polyline) with electric core."""
    pts = []
    segs = 6
    h = 44
    for i in range(segs + 1):
        frac = i / segs
        jitter = math.sin(t * 0.7 + i * 2.1) * 9
        pts.append((x + facing * (frac * 40 - 20) + jitter * 0.4,
                    y - h / 2 + frac * h + jitter))
    pygame.draw.lines(target, col, False, pts, 5)
    inner = tuple(min(255, c + 90) for c in col)
    pygame.draw.lines(target, inner, False, pts, 2)
    _glow(target, x, y, 26, col, 90)


def draw_disc_shape(target, x, y, col, angle):
    """Spinning celestial disc (NARAYANASTRA): ring + rotating spokes."""
    r = 20
    pygame.draw.circle(target, col, (int(x), int(y)), r, 4)
    pygame.draw.circle(target, tuple(min(255, c + 70) for c in col),
                       (int(x), int(y)), r - 8)
    for k in range(4):
        a = angle + k * math.pi / 2
        pygame.draw.line(target, GOLD, (x, y),
                         (x + math.cos(a) * r, y + math.sin(a) * r), 3)
    _glow(target, x, y, r + 8, col, 80)


def draw_projectile(target, pr, t=0.0):
    """Dispatch the right visual for one astral projectile."""
    shape = pr.get("shape", "arrow")
    col = pr.get("color", GOLD)
    x, y = pr["x"], pr["y"]
    f = 1 if pr.get("vx", 1) >= 0 else -1
    if shape == "bolt":
        draw_bolt_shape(target, x, y, f, col, t)
    elif shape == "disc":
        draw_disc_shape(target, x, y, col, t * 0.35)
    else:
        draw_arrow_shape(target, x, y, f, col, scale=pr.get("scale", 1.0))


# ---------------------------------------------------------------------
# MINI WARRIOR PORTRAIT (character-select cards)
#   Draws a compact stick-figure fighter — head, torso, limbs, weapon
#   and a faint special-colour aura — scaled down to fit inside a card.
#   Same drawing language as the in-game Fighter class so each card is
#   instantly recognisable as that warrior.
# ---------------------------------------------------------------------
def draw_mini_warrior(target, rect, char_data, t=0.0):
    """Render a small animated warrior preview inside `rect`."""
    cx = rect.centerx
    base_y = rect.bottom - 6                       # feet baseline
    s = max(0.25, min(1.0, rect.height / STAND_HEIGHT))
    col = char_data.get("color", SAFFRON)
    sec = char_data.get("secondary_color", WHITE)
    spc = char_data.get("special_color", GOLD)
    weapon = str(char_data.get("weapon", ""))

    def P(dx, dy):                                # local -> screen point
        return (int(cx + dx * s), int(base_y - dy * s))

    bob = math.sin(t * 0.08) * 2                  # gentle idle breathing

    # ---- soft aura halo (special colour) ----
    halo = pygame.Surface((76, 76), pygame.SRCALPHA)
    pygame.draw.circle(halo, (*spc, 45), (38, 38), 36)
    pygame.draw.circle(halo, (*spc, 25), (38, 38), 26)
    target.blit(halo, (cx - 38, int(base_y - 78 * s) - 38))

    # ---- legs (walking swing driven by sin) ----
    swing = math.sin(t * 0.18) * 4
    hip = P(0, 62 + bob)
    target_line = pygame.draw.line
    target_line(target, sec, hip, P(-7 - swing, 0), max(2, int(4 * s)))
    target_line(target, sec, hip, P(7 + swing, 0), max(2, int(4 * s)))
    pygame.draw.rect(target, col, (*P(-13 - swing, 4), 9, 4))   # feet
    pygame.draw.rect(target, col, (*P(5 + swing, 4), 9, 4))

    # ---- torso ----
    torso = pygame.Rect(0, 0, max(8, int(20 * s)), max(16, int(48 * s)))
    tx, ty = P(0, 62 + bob)
    torso.centerx, torso.bottom = tx, ty
    pygame.draw.rect(target, col, torso, border_radius=max(2, int(6 * s)))
    pygame.draw.line(target, sec, P(-10, 104 + bob), P(10, 104 + bob),
                     max(2, int(3 * s)))          # shoulder bar

    # ---- arms + fists ----
    hand_f = P(16, 82 + bob)
    hand_b = P(-16, 82 + bob)
    pygame.draw.line(target, sec, P(-9, 100 + bob), hand_b,
                     max(2, int(3 * s)))
    pygame.draw.line(target, sec, P(9, 100 + bob), hand_f,
                     max(2, int(3 * s)))
    pygame.draw.circle(target, GOLD, hand_f, max(2, int(4 * s)))
    pygame.draw.circle(target, sec, hand_b, max(2, int(4 * s)))

    # ---- head + crown / helmet crest ----
    head = P(0, 122 + bob)
    pygame.draw.circle(target, sec, head, max(4, int(11 * s)))
    pygame.draw.polygon(target, col, [P(-9, 130 + bob), P(0, 146 + bob),
                                      P(9, 130 + bob)])
    pygame.draw.circle(target, spc, P(0, 148 + bob), max(1, int(3 * s)))

    # ---- weapon silhouette from the database field ----
    if "Bow" in weapon:                            # Gandiva / Vijaya etc.
        pts = [P(20, 128), P(30, 100), P(20, 72)]
        pygame.draw.lines(target, GOLD, False, pts, max(2, int(2 * s)))
        pygame.draw.line(target, WHITE, pts[0], pts[2], 1)
    if "Gada" in weapon or "Mace" in weapon:       # Bhima / Duryodhana
        pygame.draw.line(target, (150, 100, 50), P(18, 96), P(26, 130),
                         max(2, int(3 * s)))
        pygame.draw.circle(target, col, P(27, 134), max(3, int(7 * s)))
        pygame.draw.circle(target, GOLD, P(27, 134),
                           max(3, int(7 * s)), 2)
    if "Sword" in weapon:                          # Abhimanyu / Ashwatthama
        pygame.draw.line(target, (220, 220, 230), P(16, 92), P(30, 122),
                         max(2, int(3 * s)))
        pygame.draw.line(target, GOLD, P(12, 96), P(20, 88),
                         max(2, int(2 * s)))
    if "Dice" in weapon:                           # Shakuni's loaded dice
        d = max(4, int(7 * s))
        pygame.draw.rect(target, (230, 230, 220), (P(14, 78)[0],
                                                    P(14, 78)[1], d, d))
        pygame.draw.rect(target, DEEP_RED, (P(14, 78)[0], P(14, 78)[1],
                                            d, d), 1)
    if "Spear" in weapon:                          # Yudhishthira's dharma spear
        pygame.draw.line(target, (180, 140, 60), P(18, 60), P(26, 140),
                         max(2, int(2 * s)))
        pygame.draw.polygon(target, GOLD, [P(24, 138), P(30, 152),
                                           P(28, 136)])



# =====================================================================
# SECTION 6: GAME STATES (the state machine scenes)
# =====================================================================

def wrap_text(text, font, max_w, max_lines=2):
    """Greedy word-wrap helper used by dialogue banners & result lines."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if font.size(trial)[0] <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:max_lines]


class GameState:
    """Base class for one scene of the state machine."""
    name = ""

    def __init__(self, game):
        self.game = game

    def handle_event(self, event):
        pass

    # ------------------------------------------------------------------
    # SPECIAL MOVES SYSTEM — damage credit & effect resolution
    # ------------------------------------------------------------------
    def _finish_special_credit(self, attacker, defender):
        """Charge meter / combo for astras that strike instantly at cast
        time (BRAHMASHIRA beam, DHARMA ASTRA pillar, MAYAVI GADA teleport,
        MAYA JAAL illusion).  Projectile-type astras are credited when the
        projectile itself connects instead."""
        for applied in attacker._special_credit:
            attacker.add_meter(applied)
            attacker.register_hit(blocked=(defender.state == "block"))
        attacker._special_credit.clear()
        for x, y, t, c in attacker._pending_fx_sparks:
            self.hit_sparks.append((x, y, t, c))
        attacker._pending_fx_sparks.clear()

    def _resolve_vortex(self):
        """CHAKRAVYUHA BREAKER: the spinning vortex hitbox surrounds the
        caster for 30 frames and connects ONCE on any foe caught inside."""
        for f in (self.f1, self.f2):
            v = f.vortex
            box = f.vortex_rect()
            if box is None:
                continue
            foe = self.f2 if f is self.f1 else self.f1
            if foe.state == "ko":
                continue
            if box.colliderect(foe.get_rect()):
                v["hit"] = True
                was_blocking = foe.state == "block"
                applied = foe.take_hit(v["damage"], f)
                f.add_meter(applied)
                combo = f.register_hit(blocked=was_blocking)
                if combo >= 2:
                    self.combo_pops.append((f, f"{combo} HIT COMBO!", 70))
                self.hit_sparks.append((foe.x, GROUND_Y - foe.y - 100,
                                        16, f.special_color))
                self.fx.spawn(foe.x, GROUND_Y - foe.y - 100,
                              f.special_color, count=30, speed=8, life=26)

    def _update_astra_projectiles(self):
        """Fly every astral projectile, spawn its signature trail and
        expire shockwaves.  Collision/damage stays in _resolve_projectiles."""
        for f in (self.f1, self.f2):
            col = f.special_color
            for pr in list(f.projectiles):
                pr["x"] += pr.get("vx", 0)
                pr["y"] += pr.get("vy", 0)
                shape = pr.get("shape", "arrow")
                trail = pr.get("trail", "")
                # ---- per-projectile particle trails (blue arrow streak,
                #      crackling gold lightning, green disc sparks,
                #      rolling shockwave dust) ----
                if trail == "particles":
                    self.fx.spawn(pr["x"], pr["y"], col, count=2,
                                  speed=1.5, life=14, size=4)
                elif trail == "crackle":
                    self.fx.spawn(pr["x"] + random.uniform(-14, 14),
                                  pr["y"] + random.uniform(-22, 22),
                                  col, count=2, speed=2.5, life=10, size=3)
                elif trail == "spin":
                    a = self.fight_frame * 0.3
                    self.fx.spawn(pr["x"] + math.cos(a) * 20,
                                  pr["y"] + math.sin(a) * 20,
                                  col, count=1, speed=1.2, life=12, size=3)
                elif trail == "dust":
                    self.fx.spawn(pr["x"] - pr.get("vx", 0),
                                  GROUND_Y - 6, col, count=2, speed=3,
                                  life=16, size=5, gravity=-0.05)
                    self.fx.particles[-1]["vy"] = -random.uniform(1, 3) \
                        if self.fx.particles else 0
                # ---- shockwaves die out after their lifetime ----
                if shape == "wall":
                    pr["life"] = pr.get("life", 90) - 1
                    if pr["life"] <= 0:
                        f.projectiles.remove(pr)
                        continue
                # ---- off-screen cleanup ----
                if pr["x"] < -90 or pr["x"] > SCREEN_WIDTH + 90 or \
                        pr["y"] < -90 or pr["y"] > SCREEN_HEIGHT + 90:
                    f.projectiles.remove(pr)

    def update(self, dt):
        pass

    def draw(self, target):
        pass


class MenuState(GameState):
    """Title screen: gold title, subtitle, blinking prompt."""
    name = STATE_MENU

    def __init__(self, game):
        super().__init__(game)
        self.enter_time = pygame.time.get_ticks()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and \
                event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.game.change_state(STATE_CHARACTER_SELECT)

    def draw(self, target):
        self.game.background.draw(target, dim=60)
        now = pygame.time.get_ticks()

        # gentle pulse on the title
        pulse = 1.0 + 0.03 * math.sin((now - self.enter_time) * 0.002)
        title_font = pygame.font.SysFont("arial", int(72 * pulse),
                                         bold=True)
        draw_centered_text(target, "MAHABHARAT", title_font, GOLD,
                           SCREEN_WIDTH // 2, 150, shadow=True)
        draw_centered_text(target, "DIVINE WARFARE",
                           pygame.font.SysFont("arial", 46, bold=True),
                           SAFFRON, SCREEN_WIDTH // 2, 225, shadow=True)

        # decorative divider
        pygame.draw.line(target, GOLD, (SCREEN_WIDTH // 2 - 220, 275),
                         (SCREEN_WIDTH // 2 + 220, 275), 3)
        pygame.draw.circle(target, GOLD, (SCREEN_WIDTH // 2, 275), 6)

        draw_centered_text(target, "The Kurukshetra Showdown",
                           FONT_MEDIUM, WHITE, SCREEN_WIDTH // 2, 315,
                           shadow=True)

        # blinking prompt
        if blink_visible(now - self.enter_time):
            draw_centered_text(target, "Press ENTER to Start",
                               FONT_MEDIUM, SAFFRON, SCREEN_WIDTH // 2,
                               430, shadow=True)

        draw_centered_text(
            target,
            "P1: ARROWS + Z punch / X kick      P2: IJKL + B punch / N kick",
            FONT_SMALL, SAFFRON, SCREEN_WIDTH // 2, 495)
        draw_centered_text(target,
                           "Hold DOWN + BACK to BLOCK  ·  meter full = special",
                           FONT_SMALL, GREY, SCREEN_WIDTH // 2, 525)
        draw_centered_text(target, "ESC to Quit", FONT_SMALL, GREY,
                           SCREEN_WIDTH // 2, 560)


class CharacterSelectState(GameState):
    """CHOOSE YOUR WARRIOR — 5x2 card grid, dual-cursor selection.

    LAYOUT
      * Gold title "CHOOSE YOUR WARRIOR" at the top
      * 10 cards (5 columns x 2 rows); every card shows the character
        name in their own colour, a mini drawn fighter preview, HP/SPD/PWR
        stat bars, weapon name and the special-move name in special_color
      * Dharma-chakra emblems decorate all four screen corners
      * Bottom panel: description + dialogue quote of the hovered hero

    SELECTION
      * P1 browses with the ARROW keys, confirms with ENTER
      * P2 browses with I/J/K/L, confirms with SPACE
      * The hovered card previews that character's intro dialogue
      * Glowing borders: red pulse for P1's cursor, blue pulse for P2's;
        locked cards show "✓ READY" in green
      * When BOTH are ready -> automatic countdown -> FIGHT! announcement
        inside the fight scene
    """
    name = STATE_CHARACTER_SELECT

    # ---- layout geometry -------------------------------------------
    COLS, ROWS = 5, 2
    CARD_W, CARD_H = 216, 148
    GRID_X, GRID_Y = 24, 138
    GAP_X, GAP_Y = 9, 12
    PANEL_TOP = 470                     # start of the info panel

    def __init__(self, game):
        super().__init__(game)
        self.p1_idx = 0                          # ARJUNA
        self.p2_idx = len(ROSTER) - 1            # SHAKUNI
        self.p1_ready = False
        self.p2_ready = False
        self.t = 0                               # animation timer (frames)
        self.launch_timer = None                 # frames until fight starts
        self.flash = 0                           # white flash on lock-in

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def cell_rect(self, i):
        """Screen rect of roster card number i (5 columns x 2 rows)."""
        col, row = i % self.COLS, i // self.COLS
        x = self.GRID_X + col * (self.CARD_W + self.GAP_X)
        y = self.GRID_Y + row * (self.CARD_H + self.GAP_Y)
        return pygame.Rect(x, y, self.CARD_W, self.CARD_H)

    def _move(self, idx, dx, dy):
        """Wrap-aware grid navigation for a cursor."""
        col, row = idx % self.COLS, idx // self.COLS
        col = (col + dx) % self.COLS
        row = (row + dy) % self.ROWS
        return row * self.COLS + col

    # ------------------------------------------------------------------
    # input
    # ------------------------------------------------------------------
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        if k == pygame.K_ESCAPE:
            self.game.change_state(STATE_MENU)
            return

        # ---------------- PLAYER 1 : ARROW KEYS + ENTER ----------------
        if k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self.p1_ready = not self.p1_ready    # ENTER locks / unlocks P1
            if self.p1_ready:
                self.flash = 8
        elif not self.p1_ready:
            if k == pygame.K_LEFT:
                self.p1_idx = self._move(self.p1_idx, -1, 0)
            elif k == pygame.K_RIGHT:
                self.p1_idx = self._move(self.p1_idx, +1, 0)
            elif k == pygame.K_UP:
                self.p1_idx = self._move(self.p1_idx, 0, -1)
            elif k == pygame.K_DOWN:
                self.p1_idx = self._move(self.p1_idx, 0, +1)

        # ---------------- PLAYER 2 : IJKL + SPACE ----------------------
        if k == pygame.K_SPACE:
            self.p2_ready = not self.p2_ready    # SPACE locks / unlocks P2
            if self.p2_ready:
                self.flash = 8
        elif not self.p2_ready:
            if k == pygame.K_j:
                self.p2_idx = self._move(self.p2_idx, -1, 0)
            elif k == pygame.K_l:
                self.p2_idx = self._move(self.p2_idx, +1, 0)
            elif k == pygame.K_i:
                self.p2_idx = self._move(self.p2_idx, 0, -1)
            elif k == pygame.K_k:
                self.p2_idx = self._move(self.p2_idx, 0, +1)

    # ------------------------------------------------------------------
    # per-frame update (auto-launch once both warriors are READY)
    # ------------------------------------------------------------------
    def update(self, dt):
        self.t += 1
        if self.flash > 0:
            self.flash -= 1
        if self.p1_ready and self.p2_ready and self.launch_timer is None:
            self.launch_timer = 90               # ~1.5 s dramatic pause
        if self.launch_timer is not None:
            self.launch_timer -= 1
            if self.launch_timer <= 0:
                self.game.start_fight(ROSTER[self.p1_idx],
                                      ROSTER[self.p2_idx])

    # ------------------------------------------------------------------
    # drawing — cards
    # ------------------------------------------------------------------
    def _draw_card(self, target, i, hero):
        r = self.cell_rect(i)
        hovered = i in (self.p1_idx, self.p2_idx)
        col = hero["color"]
        spc = hero["special_color"]

        # ---- dark card body with saffron inner trim ----
        pygame.draw.rect(target, (22, 12, 30), r, border_radius=10)
        pygame.draw.rect(target, (60, 34, 12), r.inflate(-6, -6), 1,
                         border_radius=8)
        if hovered:                              # subtle lift highlight
            pygame.draw.rect(target, (38, 22, 50), r.inflate(-4, -4),
                             border_radius=9)

        # ---- mini fighter preview (upper half of the card) ----
        prev = pygame.Rect(r.x + 4, r.y + 26, 62, r.height - 66)
        draw_mini_warrior(target, prev, hero, self.t + i * 13)

        # ---- name in the character's own colour ----
        nm = FONT_TINY.render(hero["name"], True, col)
        target.blit(nm, (r.x + 6, r.y + 5))
        pw = FONT_TINY.size(hero["weapon"])[0]
        wtag = FONT_TINY.render(hero["weapon"], True, GREY)
        target.blit(wtag, (r.right - pw - 6, r.y + 7))

        # ---- stat bars: HP / SPD / PWR ----
        bx = prev.right + 8
        bw = r.right - bx - 10
        stats = [("HP", hero["health"], 140, GREEN),
                 ("SPD", hero["speed"], 8, (90, 160, 255)),
                 ("PWR", hero["special_damage"], 30, SAFFRON)]
        sy = r.y + 30
        for label, val, vmax, bar_col in stats:
            lb = FONT_TINY.render(label, True, WHITE)
            target.blit(lb, (bx, sy - 3))
            track = pygame.Rect(bx + 30, sy, bw - 30, 8)
            pygame.draw.rect(target, (50, 30, 60), track, border_radius=4)
            frac = max(0.06, min(1.0, val / vmax))
            fill = track.copy()
            fill.width = max(3, int(track.width * frac))
            pygame.draw.rect(target, bar_col, fill, border_radius=4)
            pygame.draw.rect(target, (90, 60, 30), track, 1,
                             border_radius=4)
            sy += 22

        # ---- special move name in special_color ----
        sn = f"★ {hero['special_name']}"
        sw_ = FONT_TINY.size(sn)[0]
        if sw_ > r.width - 12:                  # shrink-fit long names
            sn = hero["special_name"][:14] + "…"
        st = FONT_TINY.render(sn, True, spc)
        target.blit(st, (r.centerx - st.get_width() // 2, r.bottom - 18))

        # ---- glowing cursor borders (red = P1, blue = P2) ----
        if i == self.p1_idx:
            pulse = 150 + 105 * abs(math.sin(self.t * 0.08))
            glow_surf = pygame.Surface((r.w + 16, r.h + 16), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (*DEEP_RED, int(pulse) // 3),
                             (0, 0, r.w + 16, r.h + 16), 8, border_radius=14)
            target.blit(glow_surf, (r.x - 8, r.y - 8))
            pygame.draw.rect(target, (255, 70, 70), r, 3, border_radius=10)
            tag = FONT_TINY.render("P1 ✓ READY" if self.p1_ready
                                   else "P1", True,
                                   (60, 220, 60) if self.p1_ready else WHITE)
            target.blit(tag, (r.x + 4, r.y - 20))
        if i == self.p2_idx:
            pulse = 150 + 105 * abs(math.sin(self.t * 0.08 + 1.3))
            glow_surf = pygame.Surface((r.w + 16, r.h + 16), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (*DARK_BLUE, int(pulse) // 2),
                             (0, 0, r.w + 16, r.h + 16), 8, border_radius=14)
            target.blit(glow_surf, (r.x - 8, r.y - 8))
            inner = r.inflate(-10, -10)
            pygame.draw.rect(target, (90, 150, 255), inner, 3,
                             border_radius=8)
            tag = FONT_TINY.render("P2 ✓ READY" if self.p2_ready
                                   else "P2", True,
                                   (60, 220, 60) if self.p2_ready else WHITE)
            target.blit(tag, (r.right - tag.get_width() - 4, r.y - 20))

    # ------------------------------------------------------------------
    # drawing — bottom info panel (description + dialogue quote)
    # ------------------------------------------------------------------
    def _draw_panel(self, target):
        p = pygame.Rect(24, self.PANEL_TOP, SCREEN_WIDTH - 48, 112)
        pygame.draw.rect(target, (18, 10, 26), p, border_radius=12)
        pygame.draw.rect(target, (120, 70, 20), p, 2, border_radius=12)
        draw_dharma_chakra(target, p.x + 26, p.centery, 16, SAFFRON,
                           spokes=12, angle_offset=self.t * 0.02)
        draw_dharma_chakra(target, p.right - 26, p.centery, 16, SAFFRON,
                           spokes=12, angle_offset=-self.t * 0.02)

        # two focus heroes: whoever is hovering (P1 takes precedence
        # visually, P2 shown mirrored on the right side)
        left_hero = ROSTER[self.p1_idx]
        right_hero = ROSTER[self.p2_idx]

        def block(hero, x, w, align_right=False):
            head = f"{hero['name']} — {hero['epithet']}"
            h = FONT_SMALL.render(head, True, hero["color"])
            desc = wrap_text(hero["description"], FONT_TINY, w - 20, 2)
            quote_src = (hero["intro_dialogue"][0]
                         if self.t // 45 % 2 == 0
                         else hero["intro_dialogue"][1])
            quote = wrap_text(f"“{quote_src}”", FONT_TINY, w - 20, 2)
            tx = x + (w - h.get_width()) // 2 if not align_right else \
                x + w - h.get_width()
            target.blit(h, (tx, p.y + 8))
            yy = p.y + 34
            for line in desc:
                img = FONT_TINY.render(line, True, GREY)
                target.blit(img, (x + 10, yy))
                yy += 17
            yy += 2
            for line in quote:
                img = FONT_TINY.render(line, True, GOLD)
                target.blit(img, (x + 10, yy))
                yy += 17

        half = (p.width - 90) // 2
        block(left_hero, p.x + 46, half)
        block(right_hero, p.x + 46 + half + 20, half)

        # VS emblem between the two blocks
        vs = FONT_MEDIUM.render("VS", True, DEEP_RED)
        target.blit(vs, (p.centerx - vs.get_width() // 2, p.centery - 14))

    # ------------------------------------------------------------------
    # main draw
    # ------------------------------------------------------------------
    def draw(self, target):
        self.game.background.draw(target, dim=110)   # dimmed sunset arena

        # ---- corner dharma chakras (decorative, slowly spinning) ----
        spin = self.t * 0.015
        draw_dharma_chakra(target, 26, 26, 20, SAFFRON, 16, spin)
        draw_dharma_chakra(target, SCREEN_WIDTH - 26, 26, 20, SAFFRON,
                           16, -spin)
        draw_dharma_chakra(target, 26, SCREEN_HEIGHT - 26, 20, GOLD, 16,
                           -spin)
        draw_dharma_chakra(target, SCREEN_WIDTH - 26, SCREEN_HEIGHT - 26,
                           20, GOLD, 16, spin)

        # ---- gold title + control hints ----
        draw_centered_text(target, "CHOOSE YOUR WARRIOR", FONT_LARGE,
                           GOLD, SCREEN_WIDTH // 2, 26, shadow=True)
        draw_centered_text(target,
                           "P1: ARROW KEYS browse · ENTER confirm      "
                           "P2: I J K L browse · SPACE confirm",
                           FONT_SMALL, SAFFRON, SCREEN_WIDTH // 2, 100)

        # ---- the 10 cards ----
        for i, hero in enumerate(ROSTER):
            self._draw_card(target, i, hero)

        # ---- bottom info panel ----
        self._draw_panel(target)

        # ---- status line under the grid ----
        status = []
        status.append(f"P1: {ROSTER[self.p1_idx]['name']}"
                      + ("  ✓ READY" if self.p1_ready else ""))
        status.append(f"P2: {ROSTER[self.p2_idx]['name']}"
                      + ("  ✓ READY" if self.p2_ready else ""))
        draw_centered_text(target, "      |      ".join(status),
                           FONT_SMALL, WHITE, SCREEN_WIDTH // 2,
                           self.GRID_Y + 2 * self.CARD_H + self.GAP_Y + 26)

        # ---- launch sequence: "FIGHT!" teaser banner ----
        if self.launch_timer is not None:
            grow = 1.0 + 0.35 * math.sin(self.t * 0.35)
            fs = pygame.font.SysFont("arial", max(20, int(56 * grow)),
                                     bold=True)
            draw_centered_text(target, "THE WAR BEGINS...", fs, SAFFRON,
                               SCREEN_WIDTH // 2, 250, shadow=True)
        elif blink_visible(pygame.time.get_ticks(), 900, 0.6):
            draw_centered_text(target,
                               "Both warriors must press their confirm key!",
                               FONT_SMALL, GREEN, SCREEN_WIDTH // 2, 250)

        # ---- white lock-in flash ----
        if self.flash > 0:
            veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT),
                                  pygame.SRCALPHA)
            veil.fill((255, 255, 255, self.flash * 12))
            target.blit(veil, (0, 0))


class FightState(GameState):
    """Real-time combat between the two selected fighters.

    All stats, weapons and dialogues come from the CHARACTERS database:
      intro_dialogue  -> shown during the "FIGHT!" banner
      special_dialogue-> shouted when the astral weapon is unleashed
      taunt           -> occasional mid-fight shout-outs
      win/lose_dialogue -> handed to the result screen
    """
    name = STATE_FIGHT

    def __init__(self, game, p1_data, p2_data):
        super().__init__(game)
        # Fighters are built straight from the CHARACTERS database records.
        # y = 0 means "standing on the ground line" (GROUND_Y == 430).
        self.f1 = Fighter(p1_data, 300, 0, facing=1, is_player2=False,
                          controls=P1_KEYS)
        self.f2 = Fighter(p2_data, 900, 0, facing=-1, is_player2=True,
                          controls=P2_KEYS)
        self.round_start = pygame.time.get_ticks()
        # spawn records so rounds can be reset with pristine fighters
        self.spawn_data = [
            {"data": p1_data, "x": 300},
            {"data": p2_data, "x": 900},
        ]
        # ---- PROFESSIONAL HUD state ---------------------------------
        # Best-of-3 round system: first fighter to 2 round wins takes the
        # match; on timeout the higher-HP fighter wins the round.
        self.round_number = 1
        self.round_wins = {self.f1: 0, self.f2: 0}
        self.match_over = False
        self.hud_freeze = False          # input lock during intro/announcer
        self.timer_left = 99.0           # 99-second countdown (HUD timer)
        # Smooth health-drain animation: display_health eases toward health
        for f in (self.f1, self.f2):
            f.display_health = float(f.health)
        self.winner = None               # round winner (None = still fighting)
        self.end_delay_until = None
        self.hit_sparks = []          # (x, y, frames_left, color)
        self.banner = None            # (text, colour, expires_ms)
        self.taunt_at = pygame.time.get_ticks() + random.randint(6000, 9000)
        # ---- COMBO SYSTEM pop-ups: (fighter, text, frames_left) ----
        self.combo_pops = []
        # frame counter that drives every cooldown / active-window check
        self.fight_frame = 0
        # ---- SPECIAL MOVES SYSTEM scene state ----
        self.fx = ParticleSystem()       # shared particles for both sides
        self.shake_frames = 0            # screen-shake budget (frames left)
        self.shake_intensity = 0         # max pixel amplitude right now
        # ---- PARTICLE AND VISUAL EFFECTS SYSTEM state ----------------
        # _drain_fx_requests() turns the ParticleSystem's queued requests
        # into these; draw() renders the flash / tint overlays on top of
        # everything and update() skips the simulation during hit freeze.
        self.flash_frames = 0            # white full-screen flash left
        self.tint_frames = 0             # colour veil frames remaining
        self.tint_max = 1                # fade denominator for the veil
        self.tint_color = WHITE          # current veil RGB
        self.hit_freeze_frames = 0       # simulation-pause frames left
        self.lightning_bolts = []        # [(points, color, ttl), ...]
        for f in (self.f1, self.f2):     # wire the shared fx into fighters
            f.fx = self.fx
        # dramatic pre-fight exchange (2 intro lines from the database)
        intro = (p1_data["intro_dialogue"][0] + "   ||   " +
                 p2_data["intro_dialogue"][0])
        self.set_banner(intro, SAFFRON, 4500)

    # ---------- helpers ----------
    def set_banner(self, text, color=WHITE, ms=2800):
        self.banner = (text, color, pygame.time.get_ticks() + ms)

    def _special_attempt(self, f):
        """Try to fire the astral weapon; on success shout the dialogue.

        The opponent and the shared ParticleSystem are handed to the
        Fighter so beam / pillar / teleport / illusion specials can strike
        instantly and spawn their 30-50 particle burst + screen shake."""
        foe = self.f2 if f is self.f1 else self.f1
        if f.start_special(opponent=foe, fx=self.fx):
            self.set_banner(f.data["special_dialogue"] + "  ·  "
                            + f.special_name, f.special_color, 2600)
            # credit meter/combo for astras that hit directly (beam etc.)
            self._finish_special_credit(f, foe)

    def handle_event(self, event):
        """KEYDOWN-driven actions: attacks, jump and the special.

        Movement / crouch / block are HOLD-based and handled per-frame in
        _process_movement(); attacks are edge-triggered so holding a key
        does not machine-gun (the 20/25-frame cooldowns also apply)."""
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_ESCAPE:
            self.game.change_state(STATE_MENU)
            return
        if self.hud_freeze or self.winner:
            return
        k = event.key
        # ---------------- PLAYER 1 : Arrow keys + Z (punch) X (kick) ------
        if k == pygame.K_UP:
            self.f1.jump()
        elif k == pygame.K_z:
            self.f1.start_attack("punch")
        elif k == pygame.K_x:
            self.f1.start_attack("kick")
        elif k == pygame.K_c or k == pygame.K_LCTRL or k == pygame.K_RCTRL:
            self._special_attempt(self.f1)      # P1 astral: C (or Ctrl)
        # ---------------- PLAYER 2 : IJKL + B (punch) N (kick) -----------
        elif k == pygame.K_i:
            self.f2.jump()
        elif k == pygame.K_b:
            self.f2.start_attack("punch")
        elif k == pygame.K_n:
            self.f2.start_attack("kick")
        elif k == pygame.K_m or k == pygame.K_SPACE:
            self._special_attempt(self.f2)      # P2 astral: M (or Space)

    @staticmethod
    def _back_key_action(held_back, down_held):
        return "block" if (held_back and down_held) else "crouch"

    def _process_movement(self):
        """HOLD-based controls, evaluated fresh every frame.

        P1: LEFT/RIGHT walk, UP jump (edge), DOWN crouch,
            DOWN + *back* direction  ->  BLOCK (guard)
        P2: J/L walk, I jump (edge), K crouch,
            K + *back* direction      ->  BLOCK (guard)

        "Back" simply means the arrow pointing away from the opponent,
        which is the classic fighting-game guard input."""
        pressed = pygame.key.get_pressed()
        if self.hud_freeze or self.winner:
            return
        now_ms = pygame.time.get_ticks()

        # ---------------- PLAYER 1 (arrows + Z/X) ----------------
        f = self.f1
        # MAYA JAAL: Shakuni's illusion trap flips this fighter's inputs
        rev1 = now_ms < f.controls_reversed_until
        left_held = bool(pressed[pygame.K_RIGHT]) if rev1 \
            else bool(pressed[pygame.K_LEFT])
        right_held = bool(pressed[pygame.K_LEFT]) if rev1 \
            else bool(pressed[pygame.K_RIGHT])
        down_held = bool(pressed[pygame.K_DOWN])
        back_held = (left_held if f.facing > 0 else right_held)
        blocking = down_held and back_held
        if blocking:
            f.try_block()                      # shield arc appears
        else:
            f.release_block()                  # hold-to-block only
            moved = False
            if left_held:
                f.move_left()
                moved = True
            if right_held:
                f.move_right()
                moved = True
            if down_held and f.state in ("idle", "walk", "crouch"):
                f.crouch(True)
            elif f.state == "crouch":
                f.crouch(False)
            if not moved and f.state == "walk":
                f.stop_walking()

        # ---------------- PLAYER 2 (IJKL + B/N) ------------------
        f = self.f2
        rev2 = now_ms < f.controls_reversed_until
        left_held = bool(pressed[pygame.K_l]) if rev2 \
            else bool(pressed[pygame.K_j])
        right_held = bool(pressed[pygame.K_j]) if rev2 \
            else bool(pressed[pygame.K_l])
        down_held = bool(pressed[pygame.K_k])
        back_held = (left_held if f.facing > 0 else right_held)
        blocking = down_held and back_held
        if blocking:
            f.try_block()
        else:
            f.release_block()
            moved = False
            if left_held:
                f.move_left()
                moved = True
            if right_held:
                f.move_right()
                moved = True
            if down_held and f.state in ("idle", "walk", "crouch"):
                f.crouch(True)
            elif f.state == "crouch":
                f.crouch(False)
            if not moved and f.state == "walk":
                f.stop_walking()

    def _resolve_hits(self):
        """FULL COMBAT RESOLUTION — melee attacks vs body hitboxes.

        Pipeline per swing:
          1. attacker must be inside the ACTIVE WINDOW (frames 12-20 of a
             punch / frames 12-25 of a kick) and this swing must not have
             connected yet (one hit per attack)
          2. get_attack_rect() (extends in front) vs defender.get_rect()
             (shrinks when crouching, so you can duck high punches)
          3. damage comes from the character database (punch/kick damage)
          4. defender.take_hit() applies BLOCK reduction (-75% + block
             stun) or the HIT reaction (white flash, hit stun, knockback)
          5. attacker charges the special meter (+1.5x damage dealt) and
             the COMBO counter is refreshed inside its 60-frame window
        """
        for attacker, defender in ((self.f1, self.f2), (self.f2, self.f1)):
            if attacker.is_channeling:          # astral cast, not a jab
                continue
            if not attacker.is_attack_active() or attacker.attack_hit:
                continue
            atk_box = attacker.get_attack_rect()
            if atk_box.width <= 0:
                continue
            if not atk_box.colliderect(defender.get_rect()):
                continue

            attacker.attack_hit = True
            raw_dmg = attacker.current_damage()
            was_blocking = defender.state == "block"
            applied = defender.take_hit(raw_dmg, attacker)

            # ---- DAMAGE SYSTEM: meter gain = 1.5x damage actually dealt --
            attacker.add_meter(applied)

            # ---- COMBO SYSTEM: consecutive hits within 60 frames ---------
            combo = attacker.register_hit(blocked=was_blocking)
            if combo >= 2:
                self.combo_pops.append(
                    (attacker, f"{combo} HIT COMBO!", 70))

            spark_col = GOLD if was_blocking else DEEP_RED
            self.hit_sparks.append((
                defender.x, GROUND_Y - defender.y - 110,
                12 if not was_blocking else 9, spark_col))
            if was_blocking:
                self.set_banner(f"{defender.name} BLOCKS!", GREY, 900)

    def _resolve_projectiles(self):
        """ASTRAL PROJECTILE COLLISIONS — Brahmastra arrows, Shakti bolts,
        Pratigya barrages, Narayanastra discs and Mahagada shockwaves all
        live in fighter.projectiles.  Movement/trails happen in
        _update_astra_projectiles(); here we only test them against the
        opponent's body box, apply each astral's OWN damage value
        (pr["damage"]), spark, burst particles and credit meter/combo."""
        for f in (self.f1, self.f2):
            foe = self.f2 if f is self.f1 else self.f1
            for pr in list(f.projectiles):
                w = pr.get("w", 40)
                h = pr.get("h", 40)
                rect = pygame.Rect(int(pr["x"] - w / 2),
                                   int(pr["y"] - h / 2), w, h)
                if foe.state != "ko" and rect.colliderect(foe.get_rect()):
                    was_blocking = foe.state == "block"
                    dmg = pr.get("damage", f.special_damage)
                    applied = foe.take_hit(dmg, f)
                    f.add_meter(applied)
                    combo = f.register_hit(blocked=was_blocking)
                    if combo >= 2:
                        self.combo_pops.append(
                            (f, f"{combo} HIT COMBO!", 70))
                    self.hit_sparks.append((pr["x"], pr["y"], 16,
                                            f.special_color))
                    # impact explosion in the astral's colour
                    self.fx.spawn(pr["x"], pr["y"], f.special_color,
                                  count=random.randint(30, 40), speed=8,
                                  life=26, size=5)
                    # shockwaves crumble on contact instead of sticking
                    if pr.get("shape") == "wall":
                        self.shake_frames = max(self.shake_frames, 10)
                        self.shake_intensity = max(self.shake_intensity, 6)
                    f.projectiles.remove(pr)

    def _drain_fx_requests(self):
        """Consume the ParticleSystem's queued shake / spark requests."""
        for frames, intensity in self.fx.drain_shakes():
            # strongest request wins the amplitude, durations add up
            self.shake_intensity = max(self.shake_intensity, intensity)
            self.shake_frames = max(self.shake_frames, frames)
        for x, y, t, c in self.fx.drain_sparks():
            self.hit_sparks.append((x, y, t, c))
        # direct sparks queued inside Fighter._spawn_astra
        for f in (self.f1, self.f2):
            if f._pending_fx_sparks:
                for x, y, t, c in f._pending_fx_sparks:
                    self.hit_sparks.append((x, y, t, c))
                f._pending_fx_sparks.clear()

    def update(self, dt_ms):
        # The main loop hands every state the frame time in MILLISECONDS
        # (clock.tick returns ms); the fight timer works in seconds.
        dt = dt_ms / 1000.0
        now = pygame.time.get_ticks()
        self.fight_frame += 1          # master frame clock (60 FPS)
        intro_left = (now - self.round_start) < 1400
        self.hud_freeze = bool(self.winner) or intro_left
        if not self.hud_freeze:
            # ---- TIMER: 99-second countdown, only while the fight is live
            self.timer_left -= dt
            if self.timer_left <= 0:
                self.timer_left = 0.0
                # time-up: the warrior with more HP takes the round
                w = self.f1 if self.f1.health >= self.f2.health \
                    else self.f2
                l = self.f2 if w is self.f1 else self.f1
                self._end_round(w, timeout=True)
            else:
                self._process_movement()
                self.f1.update(self.f2)
                self.f2.update(self.f1)
                self._resolve_hits()
                # ---- SPECIAL MOVES SYSTEM pipeline ----
                self._update_astra_projectiles()   # fly astras + spawn trails
                self._resolve_projectiles()        # astra <-> body collisions
                self._resolve_vortex()             # CHAKRAVYUHA BREAKER ring
                self._drain_fx_requests()          # shake/sparks queued by fx
                # occasional taunts straight out of the character database
                if now >= self.taunt_at:
                    self.taunt_at = now + random.randint(9000, 14000)
                    shouter = random.choice((self.f1, self.f2))
                    self.set_banner(shouter.data["taunt"], GREY, 2400)
                if self.f1.health <= 0 or self.f2.health <= 0:
                    self._end_round(
                        self.f1 if self.f1.health > 0 else self.f2)
        elif self.winner:
            # KO/timeout pose: physics keep running so bodies settle
            self.f1.update(self.f2)
            self.f2.update(self.f1)
            self._drain_fx_requests()
        # ---- HUD smooth health drain (display eases toward real HP) ----
        for f in (self.f1, self.f2):
            diff = f.health - f.display_health
            if abs(diff) < 0.25:
                f.display_health = float(f.health)
            else:
                f.display_health += diff * 0.12
        if self.banner and now > self.banner[2]:
            self.banner = None
        self.fx.update()               # advance every particle this frame
        self.hit_sparks = [(x, y, t - 1, c) for x, y, t, c in
                           self.hit_sparks if t > 1]
        # screen shake budget decays; intensity scales with what's left
        if self.shake_frames > 0:
            self.shake_frames -= 1
        # combo pop-ups fade out on their own frame budget
        self.combo_pops = [(f, txt, t - 1) for f, txt, t in self.combo_pops
                           if t > 1]
        if self.winner and now >= self.end_delay_until:
            if self.match_over:
                self.game.result_winner = self.winner.name
                self.game.change_state(STATE_RESULT)
            else:
                self._begin_next_round()

    # ------------------------------------------------------------------
    # PROFESSIONAL HUD — round management helpers
    # ------------------------------------------------------------------
    def _end_round(self, w, timeout=False):
        """Finish the current round: credit the win, shout a banner and
        schedule either the next round reset or the RESULT screen."""
        self.winner = w
        loser = self.f2 if w is self.f1 else self.f1
        self.round_wins[w] += 1
        self.game.result_win_line = w.data["win_dialogue"]
        self.game.result_lose_line = loser.data["lose_dialogue"]
        if timeout:
            self.set_banner("TIME UP!  " + w.name +
                            " takes the round on health!", GOLD, 2400)
        else:
            self.set_banner(w.data["win_dialogue"], GOLD, 3000)
        self.end_delay_until = pygame.time.get_ticks() + 2600
        # best of 3: two round wins ends the match
        if self.round_wins[w] >= 2:
            self.match_over = True

    def _reset_fighter(self, f, facing):
        """Put one fighter back to its starting stance for a new round.

        Rebuilds a completely fresh Fighter (so every attack / stun /
        astral-effect timer starts clean) using the stored char record,
        spawn x and keymap, then re-seeds the HUD's smooth-drain value."""
        slot = 0 if not f.is_player2 else 1
        fresh = Fighter(self.spawn_data[slot]["data"],
                        self.spawn_data[slot]["x"], 0,
                        facing=facing, is_player2=f.is_player2,
                        controls=f.controls)
        # swap the live fighter's whole state with the fresh instance
        f.__dict__.clear()
        f.__dict__.update(fresh.__dict__)
        f.display_health = float(f.health)

    def _begin_next_round(self):
        """Round interlude ended — restore both warriors and tick the
        round counter / countdown timer."""
        self.round_number += 1
        self.timer_left = 99.0
        self.winner = None
        self.end_delay_until = None
        self.hit_sparks.clear()
        self.combo_pops.clear()
        self.fx.particles.clear()
        self.shake_frames = 0
        self.shake_intensity = 0
        # PARTICLE & VISUAL EFFECTS: wipe every screen effect for round 2
        self.flash_frames = 0
        self.tint_frames = 0
        self.hit_freeze_frames = 0
        self.lightning_bolts.clear()
        for f in (self.f1, self.f2):
            f.fx = self.fx              # re-wire fresh fighters to the fx
        self._reset_fighter(self.f1, 1)
        self._reset_fighter(self.f2, -1)
        self.round_start = pygame.time.get_ticks()
        self.taunt_at = self.round_start + random.randint(6000, 9000)
        self.set_banner(f"ROUND {self.round_number}", SAFFRON, 1300)

    def draw(self, world_target):
        """Render the whole fight onto an off-screen canvas, then blit it
        to the display with a random offset while shake_frames > 0 —
        that offset IS the screen shake every special requests."""
        self.game.background.draw(world_target)
        self.f1.draw(world_target)
        self.f2.draw(world_target)

        # ---- SPECIAL MOVES SYSTEM visuals (all pure pygame shapes) ----
        self._draw_astra_projectiles(world_target)   # arrows/bolts/discs/walls
        for f in (self.f1, self.f2):
            self._draw_vortex(world_target, f)       # cyan whirlwind ring
            self._draw_beam(world_target, f)         # Brahmashira screen beam
            self._draw_pillar(world_target, f)       # Dharma pillar of light
            self._draw_teleport_flash(world_target, f)
        self.fx.draw(world_target)                   # every live particle

        # hit sparks
        for x, y, t, c in self.hit_sparks:
            rad = max(6, (12 - t) * 3 + 6)      # keep radius positive
            spark = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
            pygame.draw.circle(spark, (*c, 200), (rad, rad), rad)
            pygame.draw.circle(spark, (*GOLD, 255), (rad, rad), rad // 2)
            world_target.blit(spark, (x - rad, y - rad))

        self._draw_combo_pops(world_target)

        # ---------- camera: blit world -> screen with shake offset ------
        ox = oy = 0
        if self.shake_frames > 0:
            k = self.shake_frames / 30.0                 # decay factor
            amp = self.shake_intensity * min(1.0, k)
            ox = random.uniform(-amp, amp)
            oy = random.uniform(-amp, amp)
            if self.shake_frames <= 1:
                self.shake_intensity = 0
        screen.fill(BLACK)
        screen.blit(world_target, (int(ox), int(oy)))

        # ---------- HUD is rock-steady above the shaking world ----------
        self._draw_hud(screen)
        self._draw_banner(screen)

        # "FIGHT!" announcement for the first 1.4 s of every bout
        elapsed = pygame.time.get_ticks() - self.round_start
        if elapsed < 1400:
            if elapsed > 950:   # announcer punch-in right before controls
                draw_centered_text(screen, "FIGHT!", FONT_LARGE, GOLD,
                                   SCREEN_WIDTH // 2, 250, shadow=True)
            grow = 1.0 + 0.25 * math.sin(elapsed * 0.02)
            fsz = max(30, int(90 * grow))
            draw_centered_text(screen, "FIGHT!",
                               pygame.font.SysFont("arial", fsz, bold=True),
                               GOLD, SCREEN_WIDTH // 2, 250, shadow=True)
            intro = (self.f1.name + "  vs  " + self.f2.name)
            draw_centered_text(screen, intro, FONT_MEDIUM, SAFFRON,
                               SCREEN_WIDTH // 2, 320, shadow=True)
        elif self.winner:
            draw_centered_text(screen, f"{self.winner.name} WINS!",
                               FONT_LARGE, GOLD, SCREEN_WIDTH // 2, 250,
                               shadow=True)

    # ------------------------------------------------------------------
    # SPECIAL MOVES SYSTEM — drawing routines (pygame shapes only)
    # ------------------------------------------------------------------
    def _draw_astra_projectiles(self, target):
        """Each astral gets its own silhouette: Brahmastra is a huge
        blue-gold arrow, Shakti a crackling gold bolt, Pratigya small
        silver arrows, Narayanastra a spinning green disc and Mahagada
        a rumpling rectangle shockwave riding along the ground."""
        t = self.fight_frame
        for f in (self.f1, self.f2):
            col = f.special_color
            for pr in f.projectiles:
                if pr.get("shape") == "wall":
                    self._draw_shockwave(target, pr, col, t)
                else:
                    _glow(target, pr["x"], pr["y"],
                          max(18, pr.get("w", 40) // 2 + 8), col, 70)
                    draw_projectile(target, pr, t)

    @staticmethod
    def _draw_shockwave(target, pr, col, t):
        """MAHAGADA PRHAR: jagged energy wall travelling on the ground."""
        w, h = pr.get("w", 70), pr.get("h", 92)
        x, y = int(pr["x"]), int(pr["y"])
        wave = pygame.Surface((w, h), pygame.SRCALPHA)
        pts = [(0, h)]
        steps = 7
        for i in range(steps + 1):
            px = i * w // steps
            py = h - int(h * (0.35 + 0.5 * abs(
                math.sin(i * 1.3 + t * 0.4))))
            pts.append((px, py))
        pts.append((w, h))
        pygame.draw.polygon(wave, (*col, 200), pts)
        inner = tuple(min(255, c + 80) for c in col)
        small = pygame.transform.smoothscale(wave, (w // 2, h // 2))
        target.blit(small, (x - w // 4, GROUND_Y - h // 2))
        target.blit(wave, (x - w // 2, GROUND_Y - h))
        pygame.draw.line(target, inner, (x - w // 2, GROUND_Y - 3),
                         (x + w // 2, GROUND_Y - 3), 3)

    def _draw_vortex(self, target, f):
        """CHAKRAVYUHA BREAKER: concentric spinning arcs + orbiting cyan
        whirlwind particles centred on Abhimanyu."""
        v = f.vortex
        if v is None:
            return
        frac = v["life"] / max(1, v["max_life"])
        cx, cy = v["x"], v["y"]
        base_r = v["radius"] * (1.15 - 0.35 * frac)
        col = f.special_color
        for ring in range(3):
            r = int(base_r * (0.45 + 0.28 * ring))
            rect = pygame.Rect(int(cx - r), int(cy - r), r * 2, r * 2)
            start = v["angle"] + ring * 1.1
            pygame.draw.arc(target, (*col, int(220 * frac)), rect,
                            start, start + 2.1, 5)
            pygame.draw.arc(target, (*WHITE, int(140 * frac)), rect,
                            start + math.pi, start + math.pi + 2.1, 3)
        for k in range(8):
            a = v["angle"] * 1.6 + k * math.tau / 8
            px = cx + math.cos(a) * base_r
            py = cy + math.sin(a) * base_r * 0.75
            _glow(target, px, py, 7, col, int(200 * frac))

    def _draw_beam(self, target, f):
        """BRAHMASHIRA: red-black annihilation beam across the FULL width
        of the battlefield, fading over its lifetime."""
        b = f.beam_fx
        if b is None:
            return
        frac = b["life"] / max(1, b["max"])
        y = int(b["y"])
        core_h = max(4, int(30 * frac))
        col = f.special_color                       # crimson
        dark = (max(0, col[0] // 3), 0, 0)          # black-red edge
        pygame.draw.rect(target, (*dark, ), (0, y - core_h,
                                             SCREEN_WIDTH, core_h * 2))
        beam = pygame.Surface((SCREEN_WIDTH, core_h * 2), pygame.SRCALPHA)
        pygame.draw.rect(beam, (*col, int(230 * frac)),
                         beam.get_rect())
        inner = tuple(min(255, c + 100) for c in col)
        pygame.draw.rect(beam, (*inner, int(255 * frac)),
                         (0, core_h // 2, SCREEN_WIDTH, core_h))
        target.blit(beam, (0, y - core_h))
        # crackling edges
        for xx in range(0, SCREEN_WIDTH, 26):
            j = math.sin(xx * 0.35 + self.fight_frame * 0.9) * core_h
            _glow(target, xx, y + j, 6, col, int(180 * frac))
            _glow(target, xx + 13, y - j, 5, dark, int(160 * frac))

    def _draw_pillar(self, target, f):
        """DHARMA ASTRA: golden column of judgement falling from the sky
        onto the sinner's position, widening as it lands."""
        p = f.pillar_fx
        if p is None:
            return
        frac = p["life"] / max(1, p["max"])
        x = int(p["x"])
        top_y = 0
        bot_y = GROUND_Y
        grow = 1.0 - frac                           # 0 -> 1 as it falls
        reach = int(bot_y * min(1.0, grow * 2.2))
        half_w = int(14 + 26 * min(1.0, grow * 1.6))
        gold = GOLD
        shaft = pygame.Surface((half_w * 2, max(2, reach)), pygame.SRCALPHA)
        pygame.draw.rect(shaft, (*gold, int(170 * frac)), shaft.get_rect())
        bright = pygame.Surface((half_w, max(2, reach)), pygame.SRCALPHA)
        pygame.draw.rect(bright, (255, 255, 230, int(230 * frac)),
                         bright.get_rect())
        target.blit(shaft, (x - half_w, top_y))
        target.blit(bright, (x - half_w // 2, top_y))
        # impact halo at the ground
        _glow(target, x, GROUND_Y - 8, int(30 + 40 * grow), gold,
              int(160 * frac))
        # rising embers
        for k in range(5):
            ex = x + math.sin(self.fight_frame * 0.3 + k * 1.7) * half_w
            ey = GROUND_Y - ((self.fight_frame * 4 + k * 30) %
                             max(40, reach))
            _glow(target, ex, ey, 5, gold, 150)

    def _draw_teleport_flash(self, target, f):
        """MAYAVI GADA: after-image where Duryodhana vanished, purple
        burst where he appeared and a full-screen maya flash."""
        tp = f.teleport_fx
        if tp is None:
            return
        frac = tp["life"] / max(1, tp["max"])
        col = f.special_color
        # ghost at the origin
        ghost = pygame.Surface((44, STAND_HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(ghost, (*col, int(120 * frac)), (22, 20), 14)
        pygame.draw.rect(ghost, (*col, int(90 * frac)),
                         (8, 38, 28, 70), border_radius=8)
        target.blit(ghost, (int(tp["from_x"]) - 22,
                            GROUND_Y - STAND_HEIGHT))
        # burst at the destination (behind the foe)
        r = int(60 * (1.0 - frac) + 12)
        _glow(target, tp["at_x"], GROUND_Y - 95, r, col, int(200 * frac))
        for k in range(6):
            a = k * math.tau / 6 + self.fight_frame * 0.2
            _glow(target, tp["at_x"] + math.cos(a) * r,
                  GROUND_Y - 95 + math.sin(a) * r, 8, col,
                  int(180 * frac))
        # violet screen tint pulse
        veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        veil.fill((*col, int(46 * frac)))
        target.blit(veil, (0, 0))

    def _draw_combo_pops(self, target):
        """COMBO SYSTEM display — 'X HIT COMBO!' in gold above the fighter
        who strung the hits together.  Only shown when combo >= 2 and it
        pops/fades over its remaining frame budget."""
        for f, txt, frames_left in self.combo_pops:
            if f.combo_count < 2:
                continue                      # window already expired
            alpha = max(60, min(255, int(255 * frames_left / 70.0)))
            scale = 1.0 + 0.25 * (frames_left / 70.0)   # slight pop-in
            img = FONT_COMBO.render(txt, True, GOLD)
            if scale != 1.0:
                w = max(1, int(img.get_width() * scale))
                h = max(1, int(img.get_height() * scale))
                img = pygame.transform.smoothscale(img, (w, h))
            sh = img.copy()
            sh.set_alpha(alpha)
            x = int(max(10, min(SCREEN_WIDTH - img.get_width() - 10,
                                f.x - img.get_width() // 2)))
            # slight BOUNCE: pops rise then settle as they fade
            t01 = frames_left / 70.0
            bounce = abs(math.sin(t01 * math.pi * 2.2)) * 10.0 * t01
            y = int(GROUND_Y - f.y - STAND_HEIGHT - 78 - bounce)
            outline = img.copy()
            outline.set_alpha(min(alpha, 140))
            target.blit(outline, (x + 2, y + 2))
            img.set_alpha(alpha)
            target.blit(img, (x, y))

    def _draw_banner(self, target):
        """Dialogue ribbon near the bottom — intros / specials / taunts."""
        if not self.banner:
            return
        text, color, _ = self.banner
        lines = wrap_text(text, FONT_SMALL, SCREEN_WIDTH - 160)
        h = 22 * len(lines) + 18
        box = pygame.Surface((SCREEN_WIDTH - 120, h), pygame.SRCALPHA)
        pygame.draw.rect(box, (12, 6, 18, 210), box.get_rect(),
                         border_radius=10)
        pygame.draw.rect(box, (*color, 255), box.get_rect(), 2,
                         border_radius=10)
        target.blit(box, (60, 490 - h))
        y = 490 - h + 8
        for ln in lines:
            draw_centered_text(target, ln, FONT_SMALL, color,
                               SCREEN_WIDTH // 2, y)
            y += 22

    # ------------------------------------------------------------------
    # PROFESSIONAL HUD (Heads-Up Display)
    #   * 400x30 health bars, P1 left-anchored / P2 mirrored right
    #   * green -> yellow -> red tiers, smooth drain animation
    #   * 200x12 special meters that pulse when DIVINE POWER is ready
    #   * 99-second countdown in a gold-framed plate (red under 10 s)
    #   * ROUND indicator + filled/empty round-win pips
    #   * bouncing "X HIT COMBO!" pop-ups (see _draw_combo_pops)
    # ------------------------------------------------------------------
    def _health_tier_color(self, ratio):
        """Green above 50%, yellow between 25-50%, deep red below 25%."""
        if ratio > 0.50:
            return GREEN
        if ratio > 0.25:
            return YELLOW
        return DEEP_RED

    def _draw_health_bar(self, target, f, x, y, align_left):
        """One professional health bar: name tag above, 400x30 frame,
        smooth draining fill, colour tiers and 'HP/max' numbers inside."""
        bar_w, bar_h = 400, 30
        # ---- character name above the bar, in the fighter's own colour --
        name_img = FONT_SMALL.render(
            ("P1  " if not f.is_player2 else "") + f.name, True,
            f.color if f.color != WHITE else GOLD)
        if align_left:
            target.blit(name_img, (x, y - 26))
        else:
            target.blit(name_img, (x + bar_w - name_img.get_width(),
                                   y - 26))
        # ---- dark frame + inner well ------------------------------------
        pygame.draw.rect(target, BLACK, (x - 3, y - 3, bar_w + 6,
                                         bar_h + 6), border_radius=7)
        pygame.draw.rect(target, (45, 18, 18), (x, y, bar_w, bar_h),
                         border_radius=5)
        # ---- SMOOTH DRAIN: white "damage ghost" eases toward real HP ----
        disp_ratio = max(0.0, f.display_health / f.max_health)
        real_ratio = max(0.0, f.health / f.max_health)
        ghost_w = int(bar_w * disp_ratio)
        if ghost_w > 0:
            gcol = (255, 235, 200)   # pale 'damage ghost'
            if align_left:
                pygame.draw.rect(target, gcol, (x, y, ghost_w, bar_h),
                                 border_radius=5)
            else:
                pygame.draw.rect(target, gcol,
                                 (x + bar_w - ghost_w, y, ghost_w, bar_h),
                                 border_radius=5)
        # ---- coloured fill (green/yellow/red tiers) ----------------------
        fill_w = int(bar_w * real_ratio)
        col = self._health_tier_color(real_ratio)
        if fill_w > 0:
            if align_left:
                pygame.draw.rect(target, col, (x, y, fill_w, bar_h),
                                 border_radius=5)
            else:
                pygame.draw.rect(target, col,
                                 (x + bar_w - fill_w, y, fill_w, bar_h),
                                 border_radius=5)
            # glossy highlight strip on the live fill
            hl = pygame.Surface((fill_w, 8), pygame.SRCALPHA)
            hl.fill((255, 255, 255, 55))
            hx = x if align_left else x + bar_w - fill_w
            target.blit(hl, (hx, y + 3))
        # ---- crisp gold border ------------------------------------------
        pygame.draw.rect(target, GOLD, (x, y, bar_w, bar_h), 2,
                         border_radius=5)
        # ---- HP numbers inside the bar ----------------------------------
        hp_txt = f"{max(0, int(round(f.display_health)))}/{f.max_health}"
        img = FONT_SMALL.render(hp_txt, True, WHITE)
        ix = x + 10 if align_left else x + bar_w - img.get_width() - 10
        target.blit(img, (ix, y + (bar_h - img.get_height()) // 2))

    def _draw_special_meter(self, target, f, x, y, align_left):
        """Thin 200x12 meter below the health bar; fills in the astral's
        special_color and pulses gold + flashes 'DIVINE POWER READY!'."""
        mw, mh = 200, 12
        ratio = max(0.0, min(1.0, f.special_meter / 100.0))
        pygame.draw.rect(target, BLACK, (x - 2, y - 2, mw + 4, mh + 4),
                         border_radius=5)
        pygame.draw.rect(target, (28, 28, 42), (x, y, mw, mh),
                         border_radius=4)
        now = pygame.time.get_ticks()
        ready = ratio >= 1.0
        fill_w = int(mw * ratio)
        if ready:
            # pulsing glow: brightness oscillates while flashing
            pulse = 0.5 + 0.5 * math.sin(now * 0.012)
            base = pygame.Color(GOLD)
            col = (int(base.r * (0.6 + 0.4 * pulse)),
                   int(base.g * (0.6 + 0.4 * pulse)),
                   int(base.b * (0.6 + 0.4 * pulse)))
        else:
            col = f.special_color
        if fill_w > 0:
            if align_left:
                pygame.draw.rect(target, col, (x, y, fill_w, mh),
                                 border_radius=4)
            else:
                pygame.draw.rect(target, col,
                                 (x + mw - fill_w, y, fill_w, mh),
                                 border_radius=4)
        pygame.draw.rect(target, GREY, (x, y, mw, mh), 1, border_radius=4)
        label = "DIVINE POWER READY!" if ready else "ASTRA"
        if ready and blink_visible(now, period_ms=500, duty=0.6):
            img = FONT_TINY.render(label, True, GOLD)
        elif ready:
            img = FONT_TINY.render(label, True, (120, 95, 0))
        else:
            img = FONT_TINY.render(f"{label} {int(ratio * 100)}%",
                                   True, f.special_color)
        lx = x if align_left else x + mw - img.get_width()
        target.blit(img, (lx, y + mh + 3))

    def _draw_timer_frame(self, target):
        """Big 99s countdown centred top inside a dark gold-framed plate.
        Flashes red once fewer than 10 seconds remain."""
        cx, cy = SCREEN_WIDTH // 2, 46
        secs = max(0, int(math.ceil(self.timer_left)))
        low = secs < 10 and not self.winner
        now = pygame.time.get_ticks()
        flash = low and blink_visible(now, period_ms=420, duty=0.5)
        txt_col = DEEP_RED if flash else GOLD
        plate = pygame.Rect(cx - 52, cy - 34, 104, 68)
        pygame.draw.rect(target, BLACK, plate.inflate(8, 8),
                         border_radius=14)
        pygame.draw.rect(target, DARK_BLUE, plate, border_radius=12)
        pygame.draw.rect(target, SAFFRON if not low else DEEP_RED,
                         plate, 3, border_radius=12)
        font = pygame.font.SysFont("arial", 44, bold=True)
        draw_centered_text(target, str(secs), font, txt_col, cx, cy - 22)
        draw_centered_text(target, "TIME", FONT_TINY, GREY, cx, cy + 20)

    def _draw_round_indicator(self, target):
        """"ROUND n" beneath the timer plus win pips per fighter:
        filled circles = rounds won, empty circles = still to be claimed."""
        cx = SCREEN_WIDTH // 2
        label = (f"{self.winner.name} WINS ROUND {self.round_number}!"
                 if self.winner and self.match_over else
                 f"ROUND {self.round_number}")
        col = GOLD if self.winner else SAFFRON
        draw_centered_text(target, label, FONT_SMALL, col, cx, 88)
        # pips: 2 slots each side (best of 3)
        pip_r, gap = 7, 20
        for f, dirx in ((self.f1, -1), (self.f2, 1)):
            wins = self.round_wins[f]
            base_x = cx + dirx * 66
            for i in range(2):
                px = base_x + dirx * i * gap
                py = 112
                if i < wins:
                    pygame.draw.circle(target, GOLD, (px, py), pip_r)
                    pygame.draw.circle(target, SAFFRON, (px, py),
                                       pip_r, 2)
                else:
                    pygame.draw.circle(target, GREY, (px, py), pip_r, 2)

    def _draw_hud(self, target):
        """Assemble every HUD element — bars, meters, timer, rounds,
        control hints.  Combo pop-ups render in the shaking world layer
        so they stay glued to their fighter."""
        # P1 (left, fills left->right) and P2 (right, mirrored)
        self._draw_health_bar(target, self.f1, 40, 34, align_left=True)
        self._draw_health_bar(target, self.f2,
                              SCREEN_WIDTH - 40 - 400, 34, align_left=False)
        self._draw_special_meter(target, self.f1, 40, 72, align_left=True)
        self._draw_special_meter(target, self.f2,
                                 SCREEN_WIDTH - 40 - 200, 72,
                                 align_left=False)
        self._draw_timer_frame(target)
        self._draw_round_indicator(target)
        # VS emblem between the bars
        draw_centered_text(target, "VS", FONT_MEDIUM, GOLD,
                           SCREEN_WIDTH // 2, 130, shadow=True)
        # control reminder
        draw_centered_text(
            target,
            "P1: ←/→ move  ↑ jump  ↓+← crouch/block  Z punch  X kick  C special"
            "   ·   P2: J/L move  I jump  K+J crouch/block  B punch  N kick  M special",
            FONT_SMALL, GREY, SCREEN_WIDTH // 2, 580)


class ResultState(GameState):
    """Victory screen — shows the winner's win_dialogue and the
    loser's lose_dialogue, both pulled from the CHARACTERS database."""
    name = STATE_RESULT

    def __init__(self, game):
        super().__init__(game)
        self.enter_time = pygame.time.get_ticks()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.game.change_state(STATE_MENU)
            elif event.key == pygame.K_c:
                self.game.change_state(STATE_CHARACTER_SELECT)

    def draw(self, target):
        self.game.background.draw(target, dim=60)
        winner = getattr(self.game, "result_winner", "WARRIOR")
        win_line = getattr(self.game, "result_win_line", None)
        lose_line = getattr(self.game, "result_lose_line", None)

        draw_centered_text(target, "VICTORY", FONT_LARGE, GOLD,
                           SCREEN_WIDTH // 2, 80, shadow=True)
        draw_centered_text(target, f"{winner} claims the field at "
                                   "Kurukshetra!",
                           FONT_MEDIUM, SAFFRON, SCREEN_WIDTH // 2, 160,
                           shadow=True)
        # laurel-ish decoration
        pygame.draw.arc(target, GOLD,
                        (SCREEN_WIDTH // 2 - 180, 190, 160, 150),
                        math.pi * 0.75, math.pi * 1.6, 4)
        pygame.draw.arc(target, GOLD,
                        (SCREEN_WIDTH // 2 + 20, 190, 160, 150),
                        math.pi * 1.4, math.pi * 2.25, 4)

        # dialogue couplet from the character database (wrapped to fit)
        y = 260
        if win_line:
            for ln in wrap_text('"' + win_line + '"', FONT_SMALL,
                                SCREEN_WIDTH - 140, max_lines=3):
                draw_centered_text(target, ln, FONT_SMALL, GREEN,
                                   SCREEN_WIDTH // 2, y)
                y += 26
            y += 12
        if lose_line:
            for ln in wrap_text('"' + lose_line + '"', FONT_SMALL,
                                SCREEN_WIDTH - 140, max_lines=3):
                draw_centered_text(target, ln, FONT_SMALL, GREY,
                                   SCREEN_WIDTH // 2, y)
                y += 26

        now = pygame.time.get_ticks() - self.enter_time
        if blink_visible(now):
            draw_centered_text(target,
                               "ENTER: Main Menu    |    C: Rematch",
                               FONT_MEDIUM, WHITE, SCREEN_WIDTH // 2, 470,
                               shadow=True)


# =====================================================================
# SECTION 7: GAME CONTROLLER (state machine + main loop)
# =====================================================================

class Game:
    """Owns the state machine and the fixed 60 FPS game loop."""

    def __init__(self):
        self.background = BattlefieldBackground()
        self.result_winner = None
        self.states = {}
        self.state = None
        self.states[STATE_MENU] = MenuState(self)
        self.states[STATE_CHARACTER_SELECT] = CharacterSelectState(self)
        self.states[STATE_RESULT] = ResultState(self)
        self.state = self.states[STATE_MENU]

    # ----- state machine API -----
    def change_state(self, state_name):
        if state_name == STATE_FIGHT:
            return  # fights are created via start_fight()
        # re-create fresh instances so timers/counters reset
        if state_name == STATE_MENU:
            self.states[STATE_MENU] = MenuState(self)
        elif state_name == STATE_CHARACTER_SELECT:
            self.states[STATE_CHARACTER_SELECT] = CharacterSelectState(self)
        elif state_name == STATE_RESULT:
            self.states[STATE_RESULT] = ResultState(self)
        self.state = self.states[state_name]

    def start_fight(self, p1_data, p2_data):
        self.states[STATE_FIGHT] = FightState(self, p1_data, p2_data)
        self.state = self.states[STATE_FIGHT]

    # off-screen canvas used by FightState for the screen-shake camera
    world_canvas = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

    # ----- main loop -----
    def run(self):
        """Stable 60 FPS loop: events -> update -> draw -> tick."""
        running = True
        while running:
            dt = clock.tick(FPS)                 # ms since last frame

            # ---- event handling (quit + key press dispatch) ----
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE and \
                            self.state.name == STATE_MENU:
                        running = False           # ESC quits from the menu
                    else:
                        self.state.handle_event(event)

            # ---- update & draw current state ----
            self.background.update()
            self.state.update(dt)
            if self.state.name == STATE_FIGHT:
                # fights render the world to a canvas first (screen shake)
                self.state.draw(self.world_canvas)
            else:
                self.state.draw(screen)
            pygame.display.flip()

        pygame.quit()
        sys.exit()


# =====================================================================
# SECTION 8: ENTRY POINT
# =====================================================================

if __name__ == "__main__":
    Game().run()
