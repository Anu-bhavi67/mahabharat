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

    def start_special(self):
        """Unleash the character's signature astral weapon (needs full meter)."""
        if self.special_meter >= 100 and self.state in ("idle", "walk"):
            self.special_meter = 0.0
            self.state = "punch"                 # channeling pose = thrust
            self.attack_total = 20
            self.state_timer = 20
            self.punch_cooldown = max(self.punch_cooldown, 20)
            self.attack_hit = True               # the melee box must NOT hit
            self.is_channeling = True
            foot_y = GROUND_Y - self.y
            self.projectiles.append({
                "x": self.x + self.facing * 45,
                "y": foot_y - 110,
                "vx": self.facing * 13,
                "owner": self,
                "hit": False,
            })
            return True
        return False

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
        Returns the damage actually applied (used for sparks/meter)."""
        if self.state == "ko":
            return 0
        facing_in = attacker.facing if attacker is not None else self._last_attacker_facing(attacker)
        blocked = (self.state == "block") or \
                  (self.state == "crouch" and attacker is not None and
                   abs(self.x - attacker.x) < 140 and
                   attacker.state == "kick")   # crouching ducks punches

        if blocked:
            applied = max(1, int(round(dmg * (1.0 - self.BLOCK_REDUCTION))))
            self.health = max(0, self.health - applied)
            self.block_stun = self.BLOCK_STUN_FRAMES      # 10 frozen frames
            self.vx = facing_in * 3                        # small push-back
            return applied

        applied = int(dmg)
        self.health = max(0, self.health - applied)
        self.hit_flash = self.HIT_FLASH_FRAMES             # flash white 15f
        self.combo_count = 0                               # your own combo dies
        self.combo_timer = 0
        if self.health <= 0:
            self.state = "ko"
            self.state_timer = 0
            self.vx = facing_in * 7
            self.vy = 4                                    # dramatic pop-up
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
        Both feed the same position and stop dead on the ground line."""
        airborne = self.y > 0 or self.vel_y != 0 or self.vy != 0
        if airborne:
            self.vel_y -= GRAVITY
            self.vy -= GRAVITY * 0.6          # knockback lift falls sooner
            self.y += self.vel_y + self.vy
            if self.y <= 0:                   # touched down on the ground
                self.y, self.vel_y, self.vy = 0.0, 0.0, 0.0
                if self.state == "jump":
                    self.state = "idle"

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

        # --- advance the animation clock (bobbing / leg cycle) ---
        self.anim_time += 1.0

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
            self.start_special()                      # unleash the astral!
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

        # ---- ground shadow (stays put while jumping) ----
        sh_scale = max(0.4, 1.0 - self.y / 260.0)
        sw = int(90 * sh_scale)
        sh = pygame.Surface((sw, 16), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, int(90 * sh_scale)),
                            (0, 0, sw, 16))
        target.blit(sh, (cx - sw // 2, GROUND_Y - 8))

        # ---- glowing astral aura (special_color) ----
        self._draw_aura(target, cx, foot_y)

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
    """Both players pick a warrior from the roster grid (5 x 2 cards)."""
    name = STATE_CHARACTER_SELECT

    def __init__(self, game):
        super().__init__(game)
        self.p1_idx = 0
        self.p2_idx = len(ROSTER) - 1
        self.p1_ready = False
        self.p2_ready = False

    # -- helpers --
    def cell_rect(self, i):
        """Grid: 5 columns x 2 rows of portrait cards."""
        col, row = i % 5, i // 5
        x = 30 + col * 234
        y = 150 + row * 178
        return pygame.Rect(x, y, 210, 150)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        # ---- PLAYER 1 : A/D/W/S or the ARROW keys, ENTER to confirm ----
        if not self.p1_ready:
            if k in (pygame.K_a, pygame.K_LEFT):
                self.p1_idx = (self.p1_idx - 1) % len(ROSTER)
            elif k in (pygame.K_d, pygame.K_RIGHT):
                self.p1_idx = (self.p1_idx + 1) % len(ROSTER)
            elif k in (pygame.K_w, pygame.K_UP):
                self.p1_idx = (self.p1_idx - 5) % len(ROSTER)
            elif k in (pygame.K_s, pygame.K_DOWN):
                self.p1_idx = (self.p1_idx + 5) % len(ROSTER)
            elif k in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.p1_ready = True
        # ---- PLAYER 2 : I/J/K/L, B or N to confirm ----
        if not self.p2_ready:
            if k == pygame.K_j:
                self.p2_idx = (self.p2_idx - 1) % len(ROSTER)
            elif k == pygame.K_l:
                self.p2_idx = (self.p2_idx + 1) % len(ROSTER)
            elif k == pygame.K_i:
                self.p2_idx = (self.p2_idx - 5) % len(ROSTER)
            elif k == pygame.K_k:
                self.p2_idx = (self.p2_idx + 5) % len(ROSTER)
            elif k in (pygame.K_b, pygame.K_n, pygame.K_SPACE):
                self.p2_ready = True
        if self.p1_ready and self.p2_ready:
            if k == pygame.K_RETURN or k == pygame.K_KP_ENTER:
                self.game.start_fight(ROSTER[self.p1_idx],
                                      ROSTER[self.p2_idx])
        if k == pygame.K_ESCAPE:
            self.game.change_state(STATE_MENU)

    def _draw_stats_panel(self, target):
        """Show hovered character's lore + stat bars at the bottom."""
        hero = ROSTER[self.p1_idx]
        py = 512
        pygame.draw.rect(target, (18, 10, 26, 200),
                         (20, py - 6, SCREEN_WIDTH - 40, 84),
                         border_radius=10)
        # name + weapon + epithet line
        draw_centered_text(target,
                           f"{hero['name']}  —  {hero['weapon']}",
                           FONT_SMALL, SAFFRON, SCREEN_WIDTH // 2, py + 6)
        desc = hero["description"]
        if len(desc) > 118:
            desc = desc[:116].rsplit(" ", 1)[0] + "…"
        draw_centered_text(target, desc, FONT_SMALL, GREY,
                           SCREEN_WIDTH // 2, py + 30)

        # compact stat chips: HP / SPD / PWR(special) / punch / kick
        chips = [(f"HP {hero['health']}", GREEN),
                 (f"SPD {hero['speed']}", DARK_BLUE),
                 (f"PWR {hero['special_damage']}", DEEP_RED),
                 (f"SPECIAL: {hero['special_name']}", GOLD)]
        total_w = sum(FONT_SMALL.size(t)[0] + 26 for t, _ in chips)
        x = (SCREEN_WIDTH - total_w) // 2
        for text, col in chips:
            w = FONT_SMALL.size(text)[0] + 22
            chip = pygame.Rect(x, py + 52, w, 24)
            pygame.draw.rect(target, (40, 25, 55), chip, border_radius=8)
            pygame.draw.rect(target, col, chip, 2, border_radius=8)
            img = FONT_SMALL.render(text, True, col if col != GOLD else GOLD)
            target.blit(img, (chip.x + 11, chip.y + 3))
            x += w + 4

    def draw(self, target):
        self.game.background.draw(target)
        draw_centered_text(target, "CHOOSE YOUR WARRIOR", FONT_LARGE,
                           GOLD, SCREEN_WIDTH // 2, 40, shadow=True)
        draw_centered_text(target,
                           "P1: A/D/W/S or ARROWS browse · ENTER lock    |    "
                           "P2: I/J/K/L browse · B/N lock    |    "
                           "both locked -> press ENTER to FIGHT",
                           FONT_SMALL, WHITE, SCREEN_WIDTH // 2, 95)

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
            pcx, pcy = r.centerx, r.centery - 20
            pygame.draw.circle(target, hero["secondary_color"],
                               (pcx, pcy), 24)
            pygame.draw.rect(target, hero["color"],
                             (pcx - 19, pcy + 16, 38, 28), border_radius=6)
            pygame.draw.polygon(target, GOLD, [(pcx - 13, pcy - 16),
                                               (pcx, pcy - 34),
                                               (pcx + 13, pcy - 16)])

            name_c = WHITE if i != self.p1_idx else SAFFRON
            draw_centered_text(target, hero["name"], FONT_SMALL, name_c,
                               r.centerx, r.bottom - 36)
            draw_centered_text(target, hero["epithet"], FONT_SMALL,
                               GREY, r.centerx, r.bottom - 14)

        # selection tags floating over chosen cards
        for idx, ready, label in ((self.p1_idx, self.p1_ready, "P1"),
                                  (self.p2_idx, self.p2_ready, "P2")):
            r = self.cell_rect(idx)
            tag = FONT_SMALL.render(
                f"{label}: {'READY!' if ready else 'select'}", True,
                SAFFRON if label == "P1" else WHITE)
            target.blit(tag, (r.x + 4, r.y - 24))

        self._draw_stats_panel(target)

        if self.p1_ready and self.p2_ready:
            if blink_visible(pygame.time.get_ticks()):
                draw_centered_text(target,
                                   "Press ENTER then G to Begin the War!",
                                   FONT_MEDIUM, GREEN, SCREEN_WIDTH // 2,
                                   470, shadow=True)


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
        self.winner = None
        self.end_delay_until = None
        self.hit_sparks = []          # (x, y, frames_left, color)
        self.banner = None            # (text, colour, expires_ms)
        self.taunt_at = pygame.time.get_ticks() + random.randint(6000, 9000)
        # ---- COMBO SYSTEM pop-ups: (fighter, text, frames_left) ----
        self.combo_pops = []
        # frame counter that drives every cooldown / active-window check
        self.fight_frame = 0
        # dramatic pre-fight exchange (2 intro lines from the database)
        intro = (p1_data["intro_dialogue"][0] + "   ||   " +
                 p2_data["intro_dialogue"][0])
        self.set_banner(intro, SAFFRON, 4500)

    # ---------- helpers ----------
    def set_banner(self, text, color=WHITE, ms=2800):
        self.banner = (text, color, pygame.time.get_ticks() + ms)

    def _special_attempt(self, f):
        """Try to fire the astral weapon; on success shout the dialogue."""
        if f.start_special():
            self.set_banner(f.data["special_dialogue"] + "  ·  "
                            + f.special_name, f.special_color, 2600)

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
        if self.winner:
            return
        k = event.key
        # ---------------- PLAYER 1 : Arrow keys + Z (punch) X (kick) ------
        if k == pygame.K_UP:
            self.f1.jump()
        elif k == pygame.K_z:
            self.f1.start_attack("punch")
        elif k == pygame.K_x:
            self.f1.start_attack("kick")
        elif k == pygame.K_LCTRL or k == pygame.K_RCTRL:
            self._special_attempt(self.f1)      # P1 astral weapon
        # ---------------- PLAYER 2 : IJKL + B (punch) N (kick) -----------
        elif k == pygame.K_i:
            self.f2.jump()
        elif k == pygame.K_b:
            self.f2.start_attack("punch")
        elif k == pygame.K_n:
            self.f2.start_attack("kick")
        elif k == pygame.K_SPACE:
            self._special_attempt(self.f2)      # P2 astral weapon

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
        if self.winner:
            return

        # ---------------- PLAYER 1 (arrows + Z/X) ----------------
        f = self.f1
        left_held = bool(pressed[pygame.K_LEFT])
        right_held = bool(pressed[pygame.K_RIGHT])
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
        left_held = bool(pressed[pygame.K_j])
        right_held = bool(pressed[pygame.K_l])
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
        """Astral weapon blasts (specials) fly across the field until they
        connect; they use special_damage and charge meter like any hit."""
        for f in (self.f1, self.f2):
            foe = self.f2 if f is self.f1 else self.f1
            for pr in list(f.projectiles):
                pr["x"] += pr["vx"]
                rect = pygame.Rect(int(pr["x"]) - 20, int(pr["y"]) - 20,
                                   40, 40)
                if rect.colliderect(foe.get_rect()):
                    was_blocking = foe.state == "block"
                    applied = foe.take_hit(f.special_damage, f)
                    f.add_meter(applied)
                    f.register_hit(blocked=was_blocking)
                    self.hit_sparks.append((pr["x"], pr["y"], 16,
                                            f.special_color))
                    f.projectiles.remove(pr)
                elif pr["x"] < -40 or pr["x"] > SCREEN_WIDTH + 40:
                    f.projectiles.remove(pr)

    def update(self, dt):
        now = pygame.time.get_ticks()
        self.fight_frame += 1          # master frame clock (60 FPS)
        if not self.winner:
            self._process_movement()
            self.f1.update(self.f2)
            self.f2.update(self.f1)
            self._resolve_hits()
            self._resolve_projectiles()
            # occasional taunts straight out of the character database
            if now >= self.taunt_at:
                self.taunt_at = now + random.randint(9000, 14000)
                shouter = random.choice((self.f1, self.f2))
                self.set_banner(shouter.data["taunt"], GREY, 2400)
            if self.f1.health <= 0 or self.f2.health <= 0:
                self.winner = self.f1 if self.f1.health > 0 else self.f2
                loser = self.f2 if self.winner is self.f1 else self.f1
                self.game.result_win_line = self.winner.data["win_dialogue"]
                self.game.result_lose_line = loser.data["lose_dialogue"]
                self.set_banner(self.winner.data["win_dialogue"], GOLD, 3000)
                self.end_delay_until = now + 2600
        if self.banner and now > self.banner[2]:
            self.banner = None
        self.hit_sparks = [(x, y, t - 1, c) for x, y, t, c in
                           self.hit_sparks if t > 1]
        # combo pop-ups fade out on their own frame budget
        self.combo_pops = [(f, txt, t - 1) for f, txt, t in self.combo_pops
                           if t > 1]
        if self.winner and now >= self.end_delay_until:
            self.game.result_winner = self.winner.name
            self.game.change_state(STATE_RESULT)

    def draw(self, target):
        self.game.background.draw(target)
        self.f1.draw(target)
        self.f2.draw(target)

        # astral projectiles (each fighter's special_color, glowing comet)
        for f in (self.f1, self.f2):
            for pr in f.projectiles:
                px, py = int(pr["x"]), int(pr["y"])
                col = f.special_color
                for r, a in ((26, 90), (18, 160), (10, 255)):
                    glow = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                    pygame.draw.circle(glow, (*col, a), (r, r), r)
                    target.blit(glow, (px - r, py - r))
                pygame.draw.line(target, col,
                                 (px - int(pr["vx"]) * 2, py), (px, py), 4)

        # hit sparks
        for x, y, t, c in self.hit_sparks:
            rad = max(6, (12 - t) * 3 + 6)      # keep radius positive
            spark = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
            pygame.draw.circle(spark, (*c, 200), (rad, rad), rad)
            pygame.draw.circle(spark, (*GOLD, 255), (rad, rad), rad // 2)
            target.blit(spark, (x - rad, y - rad))

        self._draw_combo_pops(target)
        self._draw_hud(target)
        self._draw_banner(target)

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
            y = int(GROUND_Y - f.y - STAND_HEIGHT - 78)
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
            # special meter under the health bar (fills the astral weapon)
            m_ratio = f.special_meter / 100.0
            m_fill = int(bar_w * m_ratio)
            pygame.draw.rect(target, (30, 30, 45), (x, 58, bar_w, 8),
                             border_radius=4)
            ready = m_ratio >= 1.0
            m_col = GOLD if ready else f.special_color
            if align_left:
                pygame.draw.rect(target, m_col, (x, 58, m_fill, 8),
                                 border_radius=4)
            else:
                pygame.draw.rect(target, m_col,
                                 (x + bar_w - m_fill, 58, m_fill, 8),
                                 border_radius=4)
            name_img = FONT_SMALL.render(
                f"{f.name} [{f.weapon}]", True, WHITE)
            tag = " ★ READY" if ready else ""
            if tag:
                tag_img = FONT_SMALL.render(tag, True, GOLD)
                if blink_visible(pygame.time.get_ticks()):
                    if align_left:
                        target.blit(tag_img, (x + name_img.get_width() + 8,
                                              70))
                    else:
                        target.blit(tag_img,
                                    (x + bar_w - tag_img.get_width(), 70))
            target.blit(name_img, (x, 70) if align_left else
                        (x + bar_w - name_img.get_width(), 70))
        # VS emblem
        draw_centered_text(target, "VS", FONT_MEDIUM, GOLD,
                           SCREEN_WIDTH // 2, 42, shadow=True)
        # control reminder
        draw_centered_text(
            target,
            "P1: ←/→ move  ↑ jump  ↓+← crouch/block  Z punch  X kick  CTRL special"
            "   ·   P2: J/L move  I jump  K+J crouch/block  B punch  N kick  SPACE special",
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
        self.game.background.draw(target)
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
