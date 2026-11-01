"""
=====================================================================
  MAHABHARAT: DIVINE WARFARE
  A 2D fighting game built with Python + Pygame
=====================================================================

  Controls
  --------
  MENU             : ENTER  -> start game
  CHARACTER_SELECT : P1 uses A/D to browse, W to confirm
                     P2 uses LEFT/RIGHT to browse, UP to confirm
  FIGHT            : P1: A/D move, W jump, S block, F punch, G kick
                     P2: arrows move/jump/block, K punch, L kick
  RESULT           : ENTER  -> back to main menu
  Anywhere         : ESC    -> quit

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

    def draw(self, target):
        target.blit(self.surface, (0, 0))
        for x, y, _, r in self.dust_particles:
            dust = pygame.Surface((6, 6), pygame.SRCALPHA)
            pygame.draw.circle(dust, (*SAFFRON, 60), (3, 3), int(r) + 1)
            target.blit(dust, (x, y))


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
# SECTION 4: FIGHTER (simple stick-warrior with health, attacks, AI)
# =====================================================================

GROUND_Y = int(SCREEN_HEIGHT * 0.72) + 200   # feet baseline


class Fighter:
    """A procedurally-drawn warrior with basic fighting behaviour."""

    def __init__(self, name, color, accent, x, facing, controls=None):
        self.name = name
        self.color = color            # body/tunic colour
        self.accent = accent          # armour/skin tint
        self.controls = controls      # dict of key->action, None => AI
        self.reset(x, facing)

        # Stats
        self.max_health = 100
        self.health = 100

    # ---------- state helpers ----------
    def reset(self, x, facing):
        self.x = float(x)
        self.y = 0.0                  # height above ground (jump offset)
        self.vy = 0.0
        self.facing = facing          # +1 looks right, -1 looks left
        self.vx = 0.0
        self.state = "idle"           # idle/walk/jump/punch/kick/block/hurt
        self.state_timer = 0
        self.attack_hit = False
        self.ai_decision_timer = 0

    @property
    def rect(self):
        """Body hitbox (feet anchored to GROUND_Y minus jump height)."""
        foot_y = GROUND_Y - self.y
        return pygame.Rect(int(self.x) - 25, foot_y - 150, 50, 150)

    # ---------- combat ----------
    def start_attack(self, kind):
        if self.state in ("idle", "walk"):
            self.state = kind
            self.state_timer = 18 if kind == "punch" else 26
            self.attack_hit = False

    def current_damage(self):
        return 8 if self.state == "punch" else 14

    def attack_range(self):
        return 70 if self.state == "punch" else 95

    def take_hit(self, dmg, from_facing):
        self.health = max(0, self.health - dmg)
        self.state = "hurt"
        self.state_timer = 14
        self.vx = from_facing * 6      # knockback
        if self.x < 40:
            self.x = 40
        if self.x > SCREEN_WIDTH - 40:
            self.x = SCREEN_WIDTH - 40

    # ---------- per-frame update ----------
    def update(self, opponent):
        # gravity / jump
        if self.y > 0 or self.vy != 0:
            self.vy -= 0.9
            self.y += self.vy
            if self.y <= 0:
                self.y, self.vy = 0, 0
                if self.state == "jump":
                    self.state = "idle"

        # knockback decay
        self.x += self.vx
        self.vx *= 0.8
        if abs(self.vx) < 0.3:
            self.vx = 0
        self.x = max(35, min(SCREEN_WIDTH - 35, self.x))

        # face the opponent unless mid-attack
        if self.state not in ("punch", "kick", "hurt"):
            self.facing = 1 if opponent.x > self.x else -1

        # timers
        if self.state_timer > 0:
            self.state_timer -= 1
            if self.state_timer == 0 and self.state in (
                    "punch", "kick", "hurt", "block"):
                self.state = "idle"

        # AI control for player-less fighters
        if self.controls is None:
            self.update_ai(opponent)

    def update_ai(self, opponent):
        """Very simple aggressive AI so a solo player can fight someone."""
        if self.state in ("punch", "kick", "hurt"):
            return
        self.ai_decision_timer -= 1
        if self.ai_decision_timer > 0:
            return
        self.ai_decision_timer = random.randint(8, 20)

        dist = abs(self.x - opponent.x)
        roll = random.random()
        if dist > 110:
            # walk toward opponent
            self.x += self.facing * 4
            self.state = "walk"
        elif dist < 60 and roll < 0.25:
            self.x -= self.facing * 4          # back off sometimes
        elif opponent.state in ("punch", "kick") and roll < 0.45:
            self.state = "block"               # try to guard
            self.state_timer = 15
        elif roll < 0.75:
            self.start_attack(random.choice(["punch", "kick"]))
        elif roll < 0.85 and self.y == 0:
            self.vy = 16                        # hop
            self.state = "jump"
        else:
            self.state = "idle"

    # ---------- drawing ----------
    def draw(self, target):
        foot_y = GROUND_Y - self.y
        f = self.facing
        cx = int(self.x)

        # shadow
        sh = pygame.Surface((90, 16), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 90), (0, 0, 90, 16))
        target.blit(sh, (cx - 45, GROUND_Y - 8))

        skin = tuple(min(255, c + 60) for c in self.accent)
        leg_w, arm_w = 6, 5

        # legs (slight walk sway)
        sway = 0
        if self.state == "walk":
            sway = int(6 * math.sin(pygame.time.get_ticks() * 0.02))
        pygame.draw.line(target, skin, (cx, foot_y - 70),
                         (cx - 14 + sway, foot_y), leg_w)
        pygame.draw.line(target, skin, (cx, foot_y - 70),
                         (cx + 14 - sway, foot_y), leg_w)

        # torso (tunic)
        pygame.draw.rect(target, self.color,
                         (cx - 16, foot_y - 125, 32, 58), border_radius=8)
        # golden armour sash
        pygame.draw.line(target, GOLD, (cx - 16, foot_y - 100),
                         (cx + 16, foot_y - 112), 4)

        # head + crown/helmet
        pygame.draw.circle(target, skin, (cx, foot_y - 140), 15)
        pygame.draw.polygon(target, GOLD, [(cx - 12, foot_y - 148),
                                           (cx, foot_y - 168),
                                           (cx + 12, foot_y - 148)])

        # arms — pose depends on state
        shoulder_l = (cx - 15, foot_y - 118)
        shoulder_r = (cx + 15, foot_y - 118)
        if self.state == "punch":
            ext = int(self.state_timer / 18 * 45)
            end = (cx + f * (30 + 45 - ext), foot_y - 112)
            pygame.draw.line(target, skin, (cx, foot_y - 118), end, arm_w)
            pygame.draw.circle(target, GOLD, end, 7)     # fist glow
            pygame.draw.line(target, skin, shoulder_l if f > 0
                             else shoulder_r,
                             (cx - f * 12, foot_y - 95), arm_w)
        elif self.state == "kick":
            pygame.draw.line(target, skin, (cx, foot_y - 118),
                             (cx - f * 18, foot_y - 100), arm_w)
            # extended kicking leg
            ext = int(math.sin(self.state_timer / 26 * math.pi) * 55)
            pygame.draw.line(target, skin, (cx, foot_y - 70),
                             (cx + f * (25 + ext), foot_y - 55), leg_w)
        elif self.state == "block":
            pygame.draw.line(target, skin, shoulder_l, (cx + f * 8,
                             foot_y - 135), arm_w)
            pygame.draw.line(target, skin, shoulder_r, (cx + f * 10,
                             foot_y - 125), arm_w)
            shield = pygame.Surface((44, 90), pygame.SRCALPHA)
            pygame.draw.rect(shield, (*GOLD, 120), (0, 0, 44, 90),
                             border_radius=10)
            target.blit(shield, (cx + f * 14 - (0 if f > 0 else 44),
                                 foot_y - 140))
        else:
            pygame.draw.line(target, skin, shoulder_l,
                             (cx - 18, foot_y - 90), arm_w)
            pygame.draw.line(target, skin, shoulder_r,
                             (cx + 18, foot_y - 90), arm_w)

        # hurt flash
        if self.state == "hurt":
            flash = pygame.Surface((60, 160), pygame.SRCALPHA)
            pygame.draw.rect(flash, (255, 60, 60, 90), (0, 0, 60, 160),
                             border_radius=10)
            target.blit(flash, (cx - 30, foot_y - 160))

        # name tag
        draw_centered_text(target, self.name, FONT_SMALL, WHITE, cx,
                           foot_y - 185, shadow=True)


# =====================================================================
# SECTION 5: ROSTER OF WARRIORS (data only — colours + stats flavour)
# =====================================================================

ROSTER = [
    {"name": "ARJUNA",    "color": (30, 60, 160),  "accent": (90, 120, 200),
     "epithet": "The Peerless Archer"},
    {"name": "BHIMA",     "color": (140, 30, 30),  "accent": (190, 90, 60),
     "epithet": "Wind Son, Mighty Arms"},
    {"name": "KRISHNA",   "color": (40, 90, 200),  "accent": (100, 150, 230),
     "epithet": "Charioteer of Destiny"},
    {"name": "KARNA",     "color": (170, 120, 20), "accent": (220, 180, 80),
     "epithet": "Sun-Born Warrior"},
    {"name": "DURYODHANA","color": (60, 120, 40),  "accent": (110, 170, 90),
     "epithet": "Crown Prince, Gada King"},
    {"name": "BHISHMA",   "color": (110, 110, 130),"accent": (170, 170, 190),
     "epithet": "Grandfather, Oathbound"},
]

P1_KEYS = {pygame.K_a: "left", pygame.K_d: "right", pygame.K_w: "jump",
           pygame.K_s: "block", pygame.K_f: "punch", pygame.K_g: "kick"}
P2_KEYS = {pygame.K_LEFT: "left", pygame.K_RIGHT: "right",
           pygame.K_UP: "jump", pygame.K_DOWN: "block",
           pygame.K_k: "punch", pygame.K_l: "kick"}


# =====================================================================
# SECTION 6: GAME STATES (the state machine scenes)
# =====================================================================

class GameState:
    """Base class for one scene of the state machine."""
    name = ""

    def __init__(self, game):
        self.game = game

    def handle_event(self, event):
        pass

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
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.game.change_state(STATE_CHARACTER_SELECT)

    def draw(self, target):
        self.game.background.draw(target)
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

        draw_centered_text(target, "ESC to Quit", FONT_SMALL, GREY,
                           SCREEN_WIDTH // 2, 560)


class CharacterSelectState(GameState):
    """Both players pick a warrior from the roster grid."""
    name = STATE_CHARACTER_SELECT

    def __init__(self, game):
        super().__init__(game)
        self.p1_idx = 0
        self.p2_idx = len(ROSTER) - 1
        self.p1_ready = False
        self.p2_ready = False

    # -- helpers --
    def cell_rect(self, i):
        """Grid: 3 columns x 2 rows of portrait cards."""
        col, row = i % 3, i // 3
        x = 180 + col * 300
        y = 170 + row * 200
        return pygame.Rect(x, y, 220, 160)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        if not self.p1_ready:
            if k == pygame.K_a:
                self.p1_idx = (self.p1_idx - 1) % len(ROSTER)
            elif k == pygame.K_d:
                self.p1_idx = (self.p1_idx + 1) % len(ROSTER)
            elif k == pygame.K_w:
                self.p1_ready = True
        if not self.p2_ready:
            if k == pygame.K_LEFT:
                self.p2_idx = (self.p2_idx - 1) % len(ROSTER)
            elif k == pygame.K_RIGHT:
                self.p2_idx = (self.p2_idx + 1) % len(ROSTER)
            elif k == pygame.K_UP:
                self.p2_ready = True
        if self.p1_ready and self.p2_ready:
            if k == pygame.K_RETURN:
                self.game.start_fight(ROSTER[self.p1_idx],
                                      ROSTER[self.p2_idx])
        if k == pygame.K_ESCAPE:
            self.game.change_state(STATE_MENU)

    def draw(self, target):
        self.game.background.draw(target)
        draw_centered_text(target, "CHOOSE YOUR WARRIOR", FONT_LARGE,
                           GOLD, SCREEN_WIDTH // 2, 60, shadow=True)
        draw_centered_text(target,
                           "P1: A/D move, W confirm    |    "
                           "P2: ARROWS move, UP confirm",
                           FONT_SMALL, WHITE, SCREEN_WIDTH // 2, 115)

        for i, hero in enumerate(ROSTER):
            r = self.cell_rect(i)
            pygame.draw.rect(target, (25, 15, 35), r, border_radius=12)

            border_color, width = None, 3
            if i == self.p1_idx:
                border_color, width = SAFFRON, 5
            pygame.draw.rect(target, border_color or GREY, r, width,
                             border_radius=12)
            if i == self.p2_idx:
                inner = r.inflate(-14, -14)
                pygame.draw.rect(target, DARK_BLUE, inner, 5,
                                 border_radius=10)

            # mini portrait: coloured circle "warrior" bust
            pcx, pcy = r.centerx, r.centery - 15
            pygame.draw.circle(target, hero["accent"], (pcx, pcy), 26)
            pygame.draw.rect(target, hero["color"],
                             (pcx - 20, pcy + 18, 40, 30), border_radius=6)
            pygame.draw.polygon(target, GOLD, [(pcx - 14, pcy - 18),
                                               (pcx, pcy - 38),
                                               (pcx + 14, pcy - 18)])

            draw_centered_text(target, hero["name"], FONT_SMALL, WHITE,
                               r.centerx, r.bottom - 38)
            draw_centered_text(target, hero["epithet"], FONT_SMALL,
                               GREY, r.centerx, r.bottom - 16)

        # selection tags floating over chosen cards
        for idx, ready, label, col in ((self.p1_idx, self.p1_ready, "P1",
                                        SAFFRON),
                                       (self.p2_idx, self.p2_ready, "P2",
                                        DARK_BLUE)):
            r = self.cell_rect(idx)
            tag = FONT_SMALL.render(
                f"{label}: {'READY!' if ready else 'select'}", True,
                GOLD if col is SAFFRON else WHITE)
            if col is DARK_BLUE:
                tag = FONT_SMALL.render(
                    f"{label}: {'READY!' if ready else 'select'}", True,
                    WHITE)
            target.blit(tag, (r.x + 4, r.y - 26))

        if self.p1_ready and self.p2_ready:
            if blink_visible(pygame.time.get_ticks()):
                draw_centered_text(target, "Press ENTER to Begin the War!",
                                   FONT_MEDIUM, GREEN, SCREEN_WIDTH // 2,
                                   560, shadow=True)


class FightState(GameState):
    """Real-time combat between the two selected fighters."""
    name = STATE_FIGHT

    def __init__(self, game, p1_data, p2_data):
        super().__init__(game)
        self.f1 = Fighter(p1_data["name"], p1_data["color"],
                          p1_data["accent"], 300, 1, P1_KEYS)
        self.f2 = Fighter(p2_data["name"], p2_data["color"],
                          p2_data["accent"], 900, -1, P2_KEYS)
        self.round_start = pygame.time.get_ticks()
        self.winner = None
        self.end_delay_until = None
        self.hit_sparks = []          # (x, y, frames_left, color)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.game.change_state(STATE_MENU)
                return
            if self.winner:
                return
            # map raw keydown to action for each fighter
            for f in (self.f1, self.f2):
                if f.controls is None:
                    continue
                for key, action in f.controls.items():
                    if event.key == key:
                        if action == "jump" and f.y == 0 and \
                                f.state in ("idle", "walk"):
                            f.vy = 16
                            f.state = "jump"
                        elif action == "punch":
                            f.start_attack("punch")
                        elif action == "kick":
                            f.start_attack("kick")
                        elif action == "block" and \
                                f.state in ("idle", "walk"):
                            f.state = "block"
                            f.state_timer = 20

    def _process_movement(self):
        """Continuous movement while keys held down."""
        pressed = pygame.key.get_pressed()
        for f in (self.f1, self.f2):
            if f.controls is None or self.winner:
                continue
            speed = 6
            moving = False
            for key, action in f.controls.items():
                if pressed[key]:
                    if action == "left":
                        f.x -= speed
                        moving = True
                    elif action == "right":
                        f.x += speed
                        moving = True
            f.x = max(35, min(SCREEN_WIDTH - 35, f.x))
            if f.state == "walk" and not moving:
                f.state = "idle"
            if moving and f.state == "idle":
                f.state = "walk"

    def _resolve_hits(self):
        """Check active attacks against the opponent's hitbox."""
        for attacker, defender in ((self.f1, self.f2), (self.f2, self.f1)):
            if attacker.state not in ("punch", "kick") or attacker.attack_hit:
                continue
            total = 18 if attacker.state == "punch" else 26
            progress = 1 - attacker.state_timer / total
            if not (0.3 < progress < 0.75):     # only the active window hits
                continue
            reach = attacker.attack_range()
            dx = defender.x - attacker.x
            if 0 < dx * attacker.facing and abs(dx) < reach and \
                    abs(defender.y - attacker.y) < 120:
                attacker.attack_hit = True
                dmg = attacker.current_damage()
                if defender.state == "block":
                    dmg = max(1, dmg // 4)
                    spark_col = GOLD
                else:
                    spark_col = DEEP_RED
                defender.take_hit(dmg, attacker.facing)
                self.hit_sparks.append((attacker.x + attacker.facing *
                                        reach * 0.7,
                                        GROUND_Y - defender.y - 110,
                                        12, spark_col))

    def update(self, dt):
        if not self.winner:
            self._process_movement()
            self.f1.update(self.f2)
            self.f2.update(self.f1)
            self._resolve_hits()
            if self.f1.health <= 0 or self.f2.health <= 0:
                self.winner = self.f1 if self.f1.health > 0 else self.f2
                self.end_delay_until = pygame.time.get_ticks() + 2200
        self.hit_sparks = [(x, y, t - 1, c) for x, y, t, c in
                           self.hit_sparks if t > 1]
        if self.winner and pygame.time.get_ticks() >= self.end_delay_until:
            self.game.result_winner = self.winner.name
            self.game.change_state(STATE_RESULT)

    def draw(self, target):
        self.game.background.draw(target)
        self.f1.draw(target)
        self.f2.draw(target)

        # hit sparks
        for x, y, t, c in self.hit_sparks:
            rad = (12 - t) * 3 + 6
            spark = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
            pygame.draw.circle(spark, (*c, 200), (rad, rad), rad)
            pygame.draw.circle(spark, (*GOLD, 255), (rad, rad), rad // 2)
            target.blit(spark, (x - rad, y - rad))

        self._draw_hud(target)

        # "FIGHT!" banner for first second
        elapsed = pygame.time.get_ticks() - self.round_start
        if elapsed < 1000:
            draw_centered_text(target, "FIGHT!",
                               pygame.font.SysFont("arial", 90, bold=True),
                               GOLD, SCREEN_WIDTH // 2, 250, shadow=True)
        elif self.winner:
            draw_centered_text(target, f"{self.winner.name} WINS!",
                               FONT_LARGE, GOLD, SCREEN_WIDTH // 2, 250,
                               shadow=True)

    def _draw_hud(self, target):
        bar_w, bar_h = 420, 26
        for f, x, align_left in ((self.f1, 40, True),
                                 (self.f2, SCREEN_WIDTH - 40 - bar_w,
                                  False)):
            ratio = f.health / f.max_health
            fill_w = int(bar_w * ratio)
            color = GREEN if ratio > 0.5 else (
                SAFFRON if ratio > 0.25 else DEEP_RED)
            pygame.draw.rect(target, BLACK, (x - 3, 27, bar_w + 6,
                               bar_h + 6), border_radius=6)
            pygame.draw.rect(target, (60, 20, 20), (x, 30, bar_w, bar_h),
                             border_radius=5)
            if align_left:
                pygame.draw.rect(target, color, (x, 30, fill_w, bar_h),
                                 border_radius=5)
            else:
                pygame.draw.rect(target, color,
                                 (x + bar_w - fill_w, 30, fill_w, bar_h),
                                 border_radius=5)
            name_img = FONT_SMALL.render(f.name, True, WHITE)
            target.blit(name_img, (x, 60) if align_left else
                        (x + bar_w - name_img.get_width(), 60))
        # VS emblem
        draw_centered_text(target, "VS", FONT_MEDIUM, GOLD,
                           SCREEN_WIDTH // 2, 42, shadow=True)
        # control reminder
        draw_centered_text(target,
                           "P1: A/D W S F G     P2: ARROWS K L     ESC: menu",
                           FONT_SMALL, GREY, SCREEN_WIDTH // 2, 580)


class ResultState(GameState):
    """Victory screen after the fight ends."""
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
        self.game.background.draw(target)
        winner = getattr(self.game, "result_winner", "WARRIOR")
        draw_centered_text(target, "VICTORY", FONT_LARGE, GOLD,
                           SCREEN_WIDTH // 2, 150, shadow=True)
        draw_centered_text(target, f"{winner} claims the field at "
                                   "Kurukshetra!",
                           FONT_MEDIUM, SAFFRON, SCREEN_WIDTH // 2, 250,
                           shadow=True)
        # laurel-ish decoration
        pygame.draw.arc(target, GOLD,
                        (SCREEN_WIDTH // 2 - 180, 300, 160, 200),
                        math.pi * 0.75, math.pi * 1.6, 4)
        pygame.draw.arc(target, GOLD,
                        (SCREEN_WIDTH // 2 + 20, 300, 160, 200),
                        math.pi * 1.4, math.pi * 2.25, 4)

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
            self.state.draw(screen)
            pygame.display.flip()

        pygame.quit()
        sys.exit()


# =====================================================================
# SECTION 8: ENTRY POINT
# =====================================================================

if __name__ == "__main__":
    Game().run()
