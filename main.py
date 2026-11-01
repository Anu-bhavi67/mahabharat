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

  SOUND SYSTEM (see SECTION 2B - class SoundManager)
  --------------------------------------------------
  The game runs perfectly WITHOUT any audio files: every trigger point
  below is a safe function call that falls back to a generated pygame
  "beep" tone when the file is missing.  To upgrade from beeps to real
  audio, drop these files into a "sounds/" folder next to main.py:

      SFX (one-shots, .ogg preferred; .wav also fine):
          punch.ogg            -- every punch hit
          kick.ogg             -- every kick hit
          block.ogg            -- successful guard
          ko.ogg               -- a fighter's HP reaches 0
          round_start.ogg      -- the "FIGHT!" announcement
          combo.ogg            -- combo hits 3+
          select.ogg           -- menu / cursor navigation
          confirm.ogg          -- character lock-in / mode start
          special_arjuna.ogg       -- BRAHMASTRA      (divine arrow whoosh)
          special_karna.ogg        -- SHAKTI ASTRA     (thunder crack)
          special_bhima.ogg        -- MAHAGADA PRHAR   (earth slam)
          special_duryodhana.ogg   -- MAYAVI GADA      (mystic teleport pop)
          special_bhishma.ogg      -- PRATIGYA ASTRA   (triple-arrow volley)
          special_abhimanyu.ogg    -- CHAKRAVYUHA BRK  (whirlwind spin)
          special_drona.ogg        -- NARAYANASTRA     (celestial hum)
          special_ashwatthama.ogg  -- BRAHMASHIRA      (doom beam)
          special_yudhishthira.ogg -- DHARMA ASTRA     (temple bell + light)
          special_shakuni.ogg      -- MAYA JAAL        (dice rattle + laugh)
      BGM (looping music, .ogg/.mp3):
          menu.ogg                 -- title screen theme
          story.ogg                -- narrative screens
          battle_kurukshetra.ogg   -- stage 1 sunset plains
          battle_hastinapur.ogg    -- stage 2 palace at night
          battle_dyut_sabha.ogg    -- stage 3 gambling hall
          battle_chakravyuha.ogg   -- stage 4 vortex formation

  Recommended FREE sources for those files:
      https://freesound.org         (search: "punch impact", "whoosh",
                                     "temple bell", "swords clash")
      https://opengameart.org       (CC0 combat SFX packs & loops)
      https://mixkit.co/free-sound-effects   (royalty-free hits)
      https://pixabay.com/sound-effects       (royalty-free, no login)
  Convert anything to .ogg:   ffmpeg -i in.wav -c:a libvorbis out.ogg
  Volume is adjustable live in SETTINGS (from the title screen), saved
  to sound_settings.json so it persists between sessions.
=====================================================================
"""

import os
import sys
import json
import math
import array
import random
import pygame

# =====================================================================
# SECTION 1: INITIALISATION, GLOBAL CLOCK & CONSTANTS
# =====================================================================

# Initialise ONLY the mixer first, with tolerant settings, so a machine
# without any audio device still boots the game (the sound layer then
# simply reports itself muted and everything keeps working).
try:
    pygame.mixer.pre_init(44100, -16, 2, 512)
except Exception:
    pass
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
# ---- STORY MODE scenes (the Mahabharat narrative campaign) ----
STATE_STORY = "STORY"            # chapter / narrative text screen
STATE_STORY_ENDING = "STORY_ENDING"   # "DHARMA KI VIJAY!" + credits
STATE_SETTINGS = "SETTINGS"           # volume control panel (sound)
STATE_HOWTO = "HOWTO"               # controls/rules tutorial screen

# --- Fonts (created once, reused everywhere) --------------------------
FONT_SMALL  = pygame.font.SysFont("arial", 22)
FONT_TINY   = pygame.font.SysFont("arial", 15)   # character-card micro text
FONT_COMBO  = pygame.font.SysFont("arial", 34, bold=True)   # "X HIT COMBO!"
FONT_MEDIUM = pygame.font.SysFont("arial", 32, bold=True)
FONT_LARGE  = pygame.font.SysFont("arial", 64, bold=True)
FONT_TITLE  = pygame.font.SysFont("arial", 72, bold=True)
FONT_XL     = pygame.font.SysFont("arial", 96, bold=True)


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


# =====================================================================
# SECTION 2B: SOUND SYSTEM — SoundManager (graceful, file-optional)
# =====================================================================
# Everything audio lives here.  Design goals:
#   * NO audio files are required.  The game boots and plays perfectly
#     on a machine with no sounds/ folder and even with no sound card.
#   * Every trigger point in the game is a plain call to the module
#     helpers play_sound(name) / play_bgm(name); if the matching file
#     exists it is used, otherwise a generated sine "beep" tone plays
#     so there is still audible feedback.
#   * Volumes are adjustable in the SETTINGS screen and persist in
#     sound_settings.json next to main.py.
# ---------------------------------------------------------------------
# REQUIRED FILES (drop them into ./sounds/) — see the big list at the
# top of this file for names + free download sources.
# ---------------------------------------------------------------------

def _tone(freq_hz, ms, vol=1.0, shape="sine", rate=22050, slide=0.0):
    """Synthesise a short pygame.mixer.Sound from scratch (no assets).

    This is the fallback "beep": a pure tone built with pygame.sndarray
    when numpy is available, or with raw bytes.array otherwise.  `slide`
    bends the pitch over the note (negative = falling, feels like an
    impact), which makes the placeholder audio far less annoying.
    """
    n = max(1, int(rate * ms / 1000.0))
    samples = array.array("h", bytes(2 * n))
    amp = int(12000 * max(0.0, min(1.0, vol)))
    f0 = max(40.0, freq_hz)
    for i in range(n):
        t = i / rate
        f = f0 + slide * (i / n) * f0            # pitch bend
        ph = 2 * _math.pi * f * t
        if shape == "square":
            v = 1.0 if (ph % (2 * _math.pi)) < _math.pi else -1.0
        elif shape == "noise":
            v = random.uniform(-1.0, 1.0)
        else:
            v = _math.sin(ph)
        env = 1.0 - (i / n)                      # linear decay envelope
        s = int(amp * v * env * env)
        samples[i] = max(-32000, min(32000, s))
    try:
        import numpy as _np
        arr = _np.frombuffer(samples.tobytes(), dtype=_np.int16)
        arr = arr.reshape((n, 1)) if pygame.mixer.get_init()[1] == 8 \
            else arr.reshape((n, 2)) if pygame.mixer.get_init()[2] == 2 \
            else arr.reshape((n, 1))
        return pygame.sndarray.make_sound(_np.ascontiguousarray(arr))
    except Exception:
        pass
    # raw-bytes fallback (works with the default 16-bit stereo mixer)
    try:
        buf = bytearray()
        for i in range(n):
            t = i / rate
            f = f0 + slide * (i / n) * f0
            ph = 2 * _math.pi * f * t
            v = _math.sin(ph) if shape != "square" else \
                (1.0 if (ph % (2 * _math.pi)) < _math.pi else -1.0)
            env = (1.0 - (i / n)) ** 2
            s = int(amp * v * env)
            buf += s.to_bytes(2, "little", signed=True) * 2
        snd = pygame.mixer.Sound(buffer=bytes(buf))
        return snd
    except Exception:
        return None


class SoundManager:
    """File-optional audio layer with synthesised-beep fallbacks.

    Usage anywhere in the code:
        play_sound("punch")                 -- one-shot effect
        play_sound("special_arjuna")        -- per-character astral cue
        play_bgm("battle_kurukshetra")      -- looping music track
        play_bgm(None)                      -- stop the music

    Loading rules (all wrapped in try/except so nothing ever crashes):
        sounds/<name>.ogg  ->  sounds/<name>.wav ->  sounds/<name>.mp3
        bgm/<name>.ogg     ->  bgm/<name>.wav    ->  bgm/<name>.mp3
        (a flat ./sounds/ folder holding everything also works)
    If none exist, a themed beep from _TONE_TABLE is generated instead,
    so the player still hears distinct feedback for every action.
    """

    EXTENSIONS = (".ogg", ".wav", ".mp3")

    # Fallback beeps: name -> (freq Hz, length ms, wave, pitch slide)
    _TONE_TABLE = {
        "punch":         (210,  70, "square", -0.55),
        "kick":          (150,  95, "square", -0.60),
        "block":         (520,  55, "sine",    0.00),
        "combo":         (760,  70, "sine",    0.45),
        "ko":            (95,  420, "square", -0.70),
        "round_start":   (660,  240, "sine",    0.30),
        "select":        (430,  45, "sine",     0.00),
        "confirm":       (880,  120, "sine",    0.25),
        "menu":          (330,  300, "sine",    0.10),
        "story":         (247,  380, "sine",   -0.10),
        "default":       (300,  60, "sine",     0.00),
    }
    # Astral cues get unique pitches so each warrior "sounds" different.
    _ASTRA_TONES = {
        "special_arjuna":       (990, 260, "sine",   0.55),
        "special_karna":        (140, 300, "square", -0.30),
        "special_bhima":        (70,  380, "square", -0.20),
        "special_duryodhana":   (600, 200, "noise",   0.00),
        "special_bhishma":      (830, 180, "sine",    0.35),
        "special_abhimanyu":    (700, 320, "sine",   -0.45),
        "special_drona":        (520, 340, "sine",    0.20),
        "special_ashwatthama":  (110, 460, "square",  0.15),
        "special_yudhishthira": (1180, 420, "sine",    0.00),
        "special_shakuni":      (380, 240, "noise",   0.60),
    }

    def __init__(self, base_dir=None):
        self.base = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.sound_dir = os.path.join(self.base, "sounds")
        self.bgm_dir = os.path.join(self.base, "bgm")
        self.settings_path = os.path.join(self.base, "sound_settings.json")
        self.available = False           # mixer usable at all?
        self.sfx_cache = {}              # name -> Sound (file or beep)
        self.bgm_cache = {}              # name -> Sound | None
        self.current_bgm = None
        self._pending_beep = None        # reused buffer for synth tones
        self.master_volume = 1.0
        self.sfx_volume = 0.8
        self.bgm_volume = 0.5
        self.load_settings()
        self._init_mixer()

    # ------------------------------------------------------------------
    # bootstrapping
    # ------------------------------------------------------------------
    def _init_mixer(self):
        try:
            if pygame.mixer.get_init() is None:
                pygame.mixer.init(44100, -16, 2, 512)
            self.available = pygame.mixer.get_init() is not None
        except Exception:
            self.available = False
        if self.available:
            try:
                pygame.mixer.set_num_channels(16)
            except Exception:
                pass
            self.apply_volumes()

    def load_settings(self):
        """Read persisted volumes; silently ignore any problem."""
        try:
            with open(self.settings_path, "r", encoding="utf-8") as fh:
                d = json.load(fh)
            self.master_volume = float(d.get("master", self.master_volume))
            self.sfx_volume = float(d.get("sfx", self.sfx_volume))
            self.bgm_volume = float(d.get("bgm", self.bgm_volume))
        except Exception:
            pass

    def save_settings(self):
        try:
            with open(self.settings_path, "w", encoding="utf-8") as fh:
                json.dump({"master": round(self.master_volume, 3),
                           "sfx": round(self.sfx_volume, 3),
                           "bgm": round(self.bgm_volume, 3)}, fh, indent=2)
        except Exception:
            pass

    def apply_volumes(self):
        if not self.available:
            return
        try:
            pygame.mixer.music.set_volume(self.master_volume *
                                          self.bgm_volume)
        except Exception:
            pass
        for snd in list(self.sfx_cache.values()):
            try:
                snd.set_volume(self.master_volume * self.sfx_volume)
            except Exception:
                pass
        for snd in list(self.bgm_cache.values()):
            if snd is not None:
                try:
                    snd.set_volume(self.master_volume * self.bgm_volume)
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # loading
    # ------------------------------------------------------------------
    def _find_file(self, directory, name):
        for ext in self.EXTENSIONS:
            p = os.path.join(directory, name + ext)
            if os.path.isfile(p):
                return p
        return None

    def _load_sfx(self, name):
        """Return a pygame Sound for `name`: real file, else a beep."""
        if name in self.sfx_cache:
            return self.sfx_cache[name]
        snd = None
        if self.available:
            path = self._find_file(self.sound_dir, name) or \
                self._find_file(self.bgm_dir, name)
            if path:
                try:
                    snd = pygame.mixer.Sound(path)
                except Exception:
                    snd = None
            if snd is None:                       # ---- BEEP FALLBACK --
                spec = self._ASTRA_TONES.get(name) or \
                    self._TONE_TABLE.get(name) or \
                    self._TONE_TABLE["default"]
                try:
                    snd = _tone(spec[0], spec[1], vol=0.9, shape=spec[2],
                                slide=spec[3])
                except Exception:
                    snd = None
        if snd is not None:
            try:
                snd.set_volume(self.master_volume * self.sfx_volume)
            except Exception:
                pass
        self.sfx_cache[name] = snd
        return snd

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def play_sound(self, name):
        """Fire a one-shot effect.  Never raises, never blocks."""
        if not self.available:
            return
        try:
            snd = self._load_sfx(name)
            if snd is not None:
                snd.play()
        except Exception:
            pass

    def play_bgm(self, name):
        """Loop background music `name`; None stops it.

        Prefers pygame.mixer.music (streams from disk, low memory).  If
        no file exists a soft two-note drone is synthesised once and
        looped, so menus/fights still have some ambience.
        """
        if not self.available:
            return
        if name is None:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
            self.current_bgm = None
            return
        if self.current_bgm == name:
            return
        path = self._find_file(self.bgm_dir, name) or \
            self._find_file(self.sound_dir, name)
        try:
            if path:
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(self.master_volume *
                                              self.bgm_volume)
                pygame.mixer.music.play(loops=-1, fade_ms=600)
            else:
                # --- silent-but-honest fallback: no looping beeps, we
                # simply keep the last track / stay quiet ------------
                pygame.mixer.music.stop()
        except Exception:
            pass
        self.current_bgm = name

    def stop_bgm(self):
        self.play_bgm(None)

    def set_volume(self, kind, value):
        """kind is 'master' | 'sfx' | 'bgm'; value 0.0 - 1.0."""
        value = max(0.0, min(1.0, value))
        setattr(self, kind + "_volume", value)
        self.apply_volumes()
        self.save_settings()

    def status_line(self):
        n_files = len([k for k, v in self.sfx_cache.items() if v])
        mode = "mixer OFF (silent)" if not self.available else \
            ("real audio" if n_files >= 3 else "beep fallback")
        return "%s · SFX %d%% · BGM %d%%" % (
            mode, int(self.sfx_volume * 100), int(self.bgm_volume * 100))


# ---- module-level singleton + tiny wrappers (the trigger points) -----
# Created lazily on first use so importing this file (e.g. for tests or
# headless checks) never touches the audio device.
SOUNDS = None


def get_sounds():
    """Return the shared SoundManager, building it on first call."""
    global SOUNDS
    if SOUNDS is None:
        SOUNDS = SoundManager()
    return SOUNDS


def play_sound(name):
    """THE sound trigger point used all over the combat code.

    Safe to call anywhere: a missing mixer / missing file simply means
    a synthesised beep (or silence) instead — never an exception.
    """
    try:
        get_sounds().play_sound(name)
    except Exception:
        pass


def play_bgm(name):
    """Music trigger point ('menu', 'story', 'battle_<stage>', None)."""
    try:
        get_sounds().play_bgm(name)
    except Exception:
        pass


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
        # ---- SOUND SYSTEM: remember the spawn height so the landing
        # "thud" (play_sound("jump")) only fires after a REAL jump,
        # never on the round-reset snap back to the floor.
        self._prev_y = float(y)
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
        self.armor_active = False         # POLISH: super armour this frame

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
        # ---- DIALOGUE & CINEMATIC INTRO SYSTEM hooks ----------------
        # intro_lock   : True while the pre-fight cinematic plays — the
        #                fighter keeps animating but cannot act or fall.
        # draw_scale   : slow zoom factor used by the cinematic spotlight
        #                shots (1.0 == normal size).
        self.intro_lock = False
        self.draw_scale = 1.0
        # ---- AI OPPONENT SYSTEM -------------------------------------
        # `brain` is set by the fight scene when this fighter is run by
        # the CPU.  The brain only *publishes intent* (a set of virtual
        # key names); FightState injects those keys into the very same
        # input pipeline a human uses, so the AI walks / jumps / blocks /
        # crouches exactly like a player would.
        self.brain = None                 # AIBrain | None (human controlled)
        # =================== BUG-FIX GUARANTEED DEFAULTS ================
        # Every combat timer / pose flag the simulation may read MUST have
        # a default here so no code path can ever raise AttributeError.
        # (state_timer is the master attack/hurt countdown; the mirrored
        #  boolean flags below are derived from `self.state` every frame.)
        self.state_timer = 0              # frames left in punch/kick/hurt
        self.attack_timer = 0             # alias of state_timer (compat)
        self.hit_timer = 0                # alias of hit_flash   (compat)
        self.special_timer = 0            # frames left casting an astra
        self.stun_timer = 0               # total stun budget this frame
        self.dodge_timer = 0              # invulnerability frames left
        self.anim_frame = 0               # integer animation step
        self.is_hit = False               # True while recoiling
        self.is_blocking = False          # guarding right now
        self.is_crouching = False         # ducking right now
        self.is_jumping = False           # airborne right now
        self.is_punching = False          # punch swing active
        self.is_kicking = False           # kick swing active
        self.is_special = False           # astral move in progress
        self.on_ground = True             # grounded contact flag

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
        """States that lock out every other action (hit stun included).

        The cinematic intro lock also counts as busy so nobody can move,
        jump or swing while the spotlight dialogue is playing."""
        return (self.state in ("punch", "kick", "hurt", "ko")
                or self.block_stun > 0 or self.intro_lock)

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
        # SOUND TRIGGER: per-character astral cue ("special_arjuna" etc.)
        play_sound("special_" + self.name.lower())
        # channeling pose: arms thrust forward, melee box must NOT connect
        self.state = "punch"
        self.attack_total = CAST_FRAMES
        self.state_timer = CAST_FRAMES
        self._cast_frames = CAST_FRAMES   # drives Fighter.special_timer
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

        # ---- POLISH: SUPER ARMOR -----------------------------------
        # Bhima / Duryodhana shrug off interruptions while their astra is
        # being cast; Bhishma's iccha-mrityu makes him unbreakable once he
        # is down to his last 20% of health.  Damage still lands, but the
        # hit stun / knockback / flash are skipped entirely.
        armored = self.has_super_armor()
        if armored:
            blocked = False

        if blocked:
            applied = max(1, int(round(dmg * (1.0 - self.BLOCK_REDUCTION))))
            self.health = max(0, self.health - applied)
            self.block_stun = self.BLOCK_STUN_FRAMES      # 10 frozen frames
            self.vx = facing_in * 3                        # small push-back
            play_sound("block")                            # SOUND TRIGGER
            if self.fx is not None:                        # gold guard sparks
                self.fx.create_hit_sparks(self.x + facing_in * 30,
                                          chest_y, GOLD, count=8)
            return applied

        # ---- SOUND TRIGGERS: impact cue for the incoming blow ----------
        # punch/kick sounds fire where the attack lands (FightState);
        # astral projectiles and instant specials announce themselves with
        # their per-character cue; everything that bleeds HP also plays
        # the generic "hit" thud.
        if getattr(attacker, "_special_credit", None) or \
                getattr(attacker, "is_channeling", False):
            play_sound("special_" + attacker.name.lower())
        play_sound("hit")

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
            play_sound("ko")                               # SOUND TRIGGER
            if self.fx is not None:                        # KO spectacle
                self.fx.flash(FLASH_FRAMES + 2)
                self.fx.shake(24, 12)
                self.fx.tint(self.special_color, TINT_FRAMES + 6)
                self.fx.create_divine_burst(self.x, chest_y,
                                            self.special_color, count=40)
                self.fx.freeze(6)
        else:
            if armored and self.health > 0:
                # SUPER ARMOR: the blow bites but never breaks the stance —
                # no hit stun, no knockback, no white flash.  Golden guard
                # sparks mark the "clink" of an unbreakable warrior.
                self.vx = 0.0
                self.vy = 0.0
                if self.fx is not None:
                    self.fx.create_hit_sparks(self.x + facing_in * 26,
                                              chest_y, GOLD, count=10)
            else:
                self.state = "hurt"                            # hit stun
                self.state_timer = self.HIT_STUN
                self.vx = facing_in * 6                        # knockback slide
                self.vy = 2                                    # slight lift
        self._clamp_to_stage()
        return applied

    # ------------------------------------------------------------------
    # POLISH — SUPER ARMOR rules
    #   * BHIMA & DURYODHANA: immune to interruption while their astra is
    #     being channelled (the gada never stops swinging).
    #   * BHISHMA PITAMAH: iccha-mrityu — death comes only when he wills
    #     it, so in his last 20% of health he cannot be staggered at all.
    # ------------------------------------------------------------------
    def has_super_armor(self):
        if self.is_channeling and self.name in ("BHIMA", "DURYODHANA"):
            return True
        if self.name == "BHISHMA PITAMAH" and self.max_health > 0 and \
                self.health <= self.max_health * 0.2 and self.health > 0:
            return True
        return False

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
                landed_high = self._prev_y    # height before this step
                self.y, self.vel_y, self.vy = 0.0, 0.0, 0.0
                if self.state == "jump":
                    self.state = "idle"
                if self.fx is not None:       # landing dust puff
                    self.fx.create_ground_dust(self.x, GROUND_Y - 4)
                # SOUND TRIGGER: fighter lands after a real jump -> thud.
                # (Only fires when they were genuinely airborne, so round
                #  resets and spawn snaps stay silent.)
                if landed_high > 24.0:
                    play_sound("jump")
        self._prev_y = self.y
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

    def _sync_flags(self):
        """Keep the boolean pose flags mirrored with `self.state`.

        The engine's single source of truth is the string state machine;
        these flags exist so every consumer (HUD, AI brain, drawing and
        any future code) can read a plain bool without risking an
        AttributeError or desync.  Called first thing every frame.
        """
        s = self.state
        self.is_punching = (s == "punch")
        self.is_kicking = (s == "kick")
        self.is_hit = (s == "hurt")
        self.is_blocking = (s == "block")
        self.is_crouching = (s == "crouch")
        self.is_jumping = (self.y < 0)
        self.on_ground = (self.y >= 0)
        self.is_special = bool(self.is_channeling or self.vortex
                               or self.beam_fx or self.pillar_fx
                               or self.teleport_fx or self.illusion_fx)
        # compatibility aliases used by older call-sites
        self.attack_timer = self.state_timer
        self.hit_timer = self.hit_flash
        self.special_timer = getattr(self, "_cast_frames", 0)
        self.anim_frame = int(self.anim_time) % 360
        # stun budget = whatever locks this fighter right now
        self.stun_timer = max(self.state_timer if s == "hurt" else 0,
                              self.block_stun, self.extra_stun)
        if self.dodge_timer > 0:
            self.dodge_timer -= 1

    def update(self, opponent):
        """One simulation step for this fighter (called once per frame)."""
        self._sync_flags()          # BUG-FIX: flags always fresh & defined
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
        # When a professional AIController/AIBrain is attached it owns the
        # fighter (virtual-key intents injected by FightState), so skip the
        # legacy built-in brain to avoid double-driving.  The old simple
        # update_ai() fallback still runs only for fighters with NO brain
        # at all (e.g. headless demos).
        if self.controls is None and opponent is not None \
                and getattr(self, "brain", None) is None:
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

    def _draw_body(self, target):
        """Core procedural warrior rendering (head, torso, limbs, weapon,
        aura, hit-flash, KO slump, name tag).  Wrapped by draw()."""
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

    def draw(self, target):
        """Draw the warrior, honouring the cinematic `draw_scale`.

        During the pre-fight spotlight shots FightState animates a slow
        zoom-in; we render the body onto a transparent canvas and scale
        it about the fighter's FEET so the camera push-in never lifts or
        sinks the character off the ground line."""
        s = float(getattr(self, "draw_scale", 1.0))
        if abs(s - 1.0) < 0.004:
            self._draw_body(target)
            return
        pad_x, pad_top, pad_bottom = 190, 70, 46
        w = int(SCREEN_WIDTH + pad_x * 2)
        h = int(SCREEN_HEIGHT + pad_top + pad_bottom)
        canvas = pygame.Surface((w, h), pygame.SRCALPHA)
        self._draw_body(canvas)
        sw, sh = max(1, int(w * s)), max(1, int(h * s))
        zoomed_canvas = pygame.transform.smoothscale(canvas, (sw, sh))
        # keep the feet planted at the same screen point while zooming
        fx, fy = int(self.x), int(GROUND_Y - self.y)
        # feet sit at (pad_x + fx, pad_top + fy) on the off-screen canvas;
        # after scaling they must land back on that same screen point
        dx = int((pad_x + fx) * (1.0 - s))
        dy = int((pad_top + fy) * (1.0 - s))
        target.blit(zoomed_canvas, (dx, dy))

    # ------------------------------------------------------------------
    # AI VISUAL INDICATOR (spec STEP 5): small "CPU" tag above the head
    # with a pulsing gold/red dot so you can see who the machine drives.
    # Drawn OUTSIDE the zoom canvas so it never scales during cutscenes.
    # ------------------------------------------------------------------
    def draw_ai_tag(self, target):
        if getattr(self, "brain", None) is None or self.state == "ko":
            return
        cx = int(self.x)
        head_y = int(GROUND_Y - self.y) - 138     # just above the crown
        pulse = 0.5 + 0.5 * math.sin(self.anim_time * 0.12)
        col = (255, 90, 60) if pulse > 0.5 else GOLD   # red/gold heartbeat
        tag = FONT_TINY.render("CPU", True, col)
        tw = tag.get_width()
        bg = pygame.Surface((tw + 10, tag.get_height() + 4), pygame.SRCALPHA)
        bg.fill((10, 6, 4, 170))
        pygame.draw.rect(bg, (*col, 220), bg.get_rect(), 1, border_radius=3)
        target.blit(bg, (cx - (tw + 10) // 2, head_y - 14))
        target.blit(tag, (cx - tw // 2, head_y - 12))
        # blinking activity dot — brighter the harder the difficulty
        lvl = getattr(self.brain, "level", "MEDIUM")
        r = {"EASY": 2, "MEDIUM": 3, "HARD": 4}.get(lvl, 3)
        if pulse > 0.35:
            pygame.draw.circle(target, col, (cx + tw // 2 + 8, head_y - 5), r)


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
        "low_hp_dialogue": "Krishna, guide my arrow… haath kaanp rahe hain, par lakshya nahi!",
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
        "low_hp_dialogue": "Mera kavach… gaya! Shraap ka samay aa gaya… phir bhi main jhukunga nahi!",
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
        "low_hp_dialogue": "Duryodhana… yeh dard tera karz hai! Bhima abhi zinda hai — gada abhi zinda hai!",
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
        "low_hp_dialogue": "Rajya ke liye rota nahi Duryodhana… par aaj ranbhoomi sharminda kar rahi hai!",
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
        "low_hp_dialogue": "Sharson ka shayan bulata hai… pratigya adhoori hai, mrityu abhi nahi!",
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
        "low_hp_dialogue": "Saat veer ghair hain… par ek Abhimanyu abhi zinda hai — vyuh abhi nahi jita!",
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
        "low_hp_dialogue": "Shishya hi vidyarthi ka ant likhe… guru aaj bhool gaya — ya bhulaya gaya!",
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
        "low_hp_dialogue": "Yeh dard… hazaron saal ka shraap jhaank raha hai — par mera kaam abhi baaki!",
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
        "low_hp_dialogue": "Satyavat hoke bhi dard hota hai… par dharm ka raasta kabhi chhoda nahi jaata.",
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
        "low_hp_dialogue": "Chaal bigad rahi hai… par Shakuni haar mein bhi paase badal leta hai!",
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
# NOTE (OVERHAUL STEP 2): local 2-player mode has been REMOVED.
# The right-hand fighter is ALWAYS AI-controlled, so there is no human
# P2 keymap any more — only the CPU's virtual intents drive that slot.
P2_KEYS = {}                      # kept as an empty dict for compatibility



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
# SECTION 6A: DIALOGUE SYSTEM — typewriter boxes + queue
# =====================================================================
# A DialogueBox renders one dramatic line at the bottom of the screen
# with a typewriter reveal (DIALOGUE_CHARS_PER_FRAME letters per frame),
# a dark semi-transparent panel bordered in the SPEAKER's colour and
# the speaker's name floating above it in that same colour.
#
#   * auto-dismiss after `duration` frames          (spec: 90f = 1.5 s)
#   * skip on ANY key press -> finish the line instantly; pressing again
#     while the box is already complete dismisses it and moves to the
#     next queued entry
#   * queue system: add() several entries and they play back in order
# =====================================================================

DIALOGUE_BOX_H = 118            # panel height (px)
DIALOGUE_BOX_MARGIN = 46        # left/right inset from the screen edges
DIALOGUE_LINE_H = 24            # wrapped-line pitch inside the panel
DIALOGUE_CHARS_PER_FRAME = 2    # typewriter speed: 2 characters / frame
DIALOGUE_DEFAULT_DURATION = 90  # frames a line stays up (1.5 s @ 60 FPS)


class DialogueBox:
    """One typewriter dialogue entry plus its playback state."""

    def __init__(self, text, speaker=None, color=None,
                 duration=DIALOGUE_DEFAULT_DURATION):
        self.text = str(text)
        self.speaker = speaker or ""
        self.color = tuple(color) if color else GOLD
        self.duration = int(max(30, duration))
        self.timer = 0              # frames this entry has been visible
        self.shown = 0              # characters revealed so far (typewriter)
        self._lines_cache = None    # wrapped lines (computed lazily)
        self._cache_key = None

    # ---------- typewriter helpers ----------
    def wrapped_lines(self, max_w):
        """Wrap the full text once and cache it (cheap per-frame reuse)."""
        if self._cache_key != max_w:
            self._lines_cache = wrap_text(self.text, FONT_SMALL, max_w,
                                          max_lines=3)
            self._cache_key = max_w
        return self._lines_cache

    def visible_text(self):
        """The prefix of the line revealed by the typewriter so far."""
        return self.text[:self.shown]

    @property
    def typing_done(self):
        return self.shown >= len(self.text)

    # ---------- playback ----------
    def update(self):
        """Advance one frame: reveal 2 chars/frame, then time out."""
        self.timer += 1
        if self.shown < len(self.text):
            self.shown = min(len(self.text),
                             self.shown + DIALOGUE_CHARS_PER_FRAME)

    def skip_typing(self):
        """INSTANT-SKIP: reveal the whole line immediately."""
        self.shown = len(self.text)

    @property
    def expired(self):
        """True once the line is fully shown AND held for its duration."""
        return self.typing_done and self.timer >= self.duration

    def draw(self, target, y=None):
        """Dark semi-transparent panel, coloured border + speaker tag."""
        inner_w = SCREEN_WIDTH - DIALOGUE_BOX_MARGIN * 2 - 28
        lines = self.wrapped_lines(inner_w)
        h = DIALOGUE_BOX_H
        y = SCREEN_HEIGHT - h - 26 if y is None else y
        x = DIALOGUE_BOX_MARGIN

        panel = pygame.Surface((SCREEN_WIDTH - DIALOGUE_BOX_MARGIN * 2, h),
                               pygame.SRCALPHA)
        panel.fill((10, 5, 16, 225))                    # dark translucent
        pygame.draw.rect(panel, (*self.color, 255),
                         panel.get_rect(), 3, border_radius=12)
        # inner hairline for a gilded look
        pygame.draw.rect(panel, (*self.color, 90),
                         panel.get_rect().inflate(-10, -10), 1,
                         border_radius=10)
        target.blit(panel, (x, y))

        # ---- speaker name plate ABOVE the box, in the speaker's colour --
        if self.speaker:
            name_img = FONT_SMALL.render(self.speaker, True, self.color)
            nw = name_img.get_width() + 22
            plate = pygame.Surface((nw, 26), pygame.SRCALPHA)
            plate.fill((10, 5, 16, 235))
            pygame.draw.rect(plate, (*self.color, 255),
                             plate.get_rect(), 2, border_radius=8)
            target.blit(plate, (x + 14, y - 30))
            target.blit(name_img, (x + 25, y - 28))

        # ---- typewriter text (partial until fully revealed) ------------
        txt = self.visible_text()
        yy = y + 22
        partial_line = None
        remaining = len(txt)
        for i, ln in enumerate(lines):
            take = min(len(ln), max(0, remaining))
            shown_part = ln[:take]
            remaining -= len(ln) + 1          # +1 ~ the dropped space
            if shown_part:
                img = FONT_SMALL.render(shown_part, True, WHITE)
                target.blit(img, (x + 16, yy))
            if take < len(ln):
                partial_line = i
                break
            yy += DIALOGUE_LINE_H
        # ---- blinking caret while the typewriter is still running -----
        if not self.typing_done:
            idx = partial_line if partial_line is not None else 0
            shown_here = remaining_before = None      # readability only
            cur_text = ""
            if idx < len(lines):
                used = sum(len(l) + 1 for l in lines[:idx])
                cur_text = lines[idx][:max(0, len(txt) - used)]
            cxc = x + 16 + FONT_SMALL.size(cur_text)[0]
            cyc = y + 22 + DIALOGUE_LINE_H * idx
            if blink_visible(self.timer * 16.6, period_ms=520, duty=0.6):
                pygame.draw.rect(target, self.color, (cxc + 2, cyc + 2, 3, 20))


class DialogueQueue:
    """Sequential playback of several DialogueBox entries."""

    def __init__(self):
        self.entries = []       # list[DialogueBox]
        self.current = None

    # ---------- API ----------
    def add(self, text, speaker=None, color=None,
            duration=DIALOGUE_DEFAULT_DURATION):
        self.entries.append(DialogueBox(text, speaker, color, duration))

    def extend(self, pairs, speaker=None, color=None,
               duration=DIALOGUE_DEFAULT_DURATION):
        """Queue many lines at once (e.g. both intro_dialogue lines)."""
        for t in pairs:
            self.add(t, speaker, color, duration)

    def clear(self):
        self.entries.clear()
        self.current = None

    @property
    def active(self):
        return self.current is not None

    @property
    def empty(self):
        return not self.entries and self.current is None

    def _promote(self):
        """Move the next queued entry into the current slot."""
        if self.entries:
            self.current = self.entries.pop(0)
        else:
            self.current = None

    # ---------- playback ----------
    def update(self):
        if self.current is None:
            self._promote()
        if self.current is not None:
            self.current.update()
            if self.current.expired:
                self.current = None
                self._promote()

    def handle_key(self):
        """ANY key press: first finishes the typewriter, second skips."""
        if self.current is None:
            self._promote()
            return True
        if not self.current.typing_done:
            self.current.skip_typing()
        else:
            self.current = None
            self._promote()
        return True

    def draw(self, target, y=None):
        if self.current is not None:
            self.current.draw(target, y)


# =====================================================================
# SECTION 6B: CINEMATIC PRE-FIGHT INTRO
# =====================================================================
# Timeline (frames @ 60 FPS) — every step keeps the fighters frozen:
#   0..INTRO_FADE_IN          black screen fades in over the arena
#   P1 spotlight + 2 intro lines (90 frames each, slow zoom-in)
#   camera SWISH
#   P2 spotlight + 2 intro lines (90 frames each, slow zoom-in)
#   VS screen: both warriors facing each other, huge gold "VS"
#   "YUDDH AARAMBH!" (Battle Begin!) Sanskrit-style gold flourish
# ---------------------------------------------------------------------
INTRO_FADE_IN = 20
INTRO_SPOT_FRAMES = 18          # light beam sweeps onto the hero
INTRO_LINE_FRAMES = 90          # each intro_dialogue line = 90 frames
INTRO_SWISH_FRAMES = 22         # camera switch between the two heroes
INTRO_VS_FRAMES = 70            # VS standoff
INTRO_BEGIN_FRAMES = 55         # "YUDDH AARAMBH!" flourish

INTRO_ZOOM_MIN = 0.82           # slow zoom effect range (scale factor)
INTRO_ZOOM_MAX = 1.12
INTRO_SPOT_RADIUS = 132         # spotlight disc radius around a fighter


def _intro_zoom(frac):
    """Slow cinematic push-in: scale grows linearly across the segment."""
    return INTRO_ZOOM_MIN + (INTRO_ZOOM_MAX - INTRO_ZOOM_MIN) * frac


def draw_spotlight(target, cx, foot_y, radius, tint=(255, 220, 150)):
    """Cinematic stage light: dim everything, then punch a bright cone
    and floor ellipse around (cx, foot_y).  Pure alpha surfaces."""
    # 1) darken the whole frame
    dim = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    dim.fill((0, 0, 0, 205))
    target.blit(dim, (0, 0))
    # 2) cut the lit pool back out of the darkness
    pool = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for rr, aa in ((radius, 60), (int(radius * 0.72), 95),
                   (int(radius * 0.45), 150)):
        pygame.draw.circle(pool, (*tint, aa), (radius, radius), rr)
    target.blit(pool, (int(cx) - radius, int(foot_y - 80) - radius))
    # 3) light cone from above + glowing floor ellipse
    cone = pygame.Surface((radius * 2, 300), pygame.SRCALPHA)
    pygame.draw.polygon(cone, (*tint, 46),
                        [(radius - 16, 0), (radius + 16, 0),
                         (radius * 2, 300), (0, 300)])
    target.blit(cone, (int(cx) - radius, int(foot_y) - 300))
    ell = pygame.Surface((radius * 2, 40), pygame.SRCALPHA)
    pygame.draw.ellipse(ell, (*tint, 70), (0, 0, radius * 2, 40))
    target.blit(ell, (int(cx) - radius, int(foot_y) - 20))


# =====================================================================
# SECTION 5D: STORY MODE — THE MAHABHARAT CAMPAIGN (8 chapters)
# =====================================================================
# The player always fights on the side of the PANDAVAS.  Each chapter
# pins down a fixed hero, a fixed opponent, a fixed arena and the AI
# difficulty that opponent runs at.  Stage names map onto the four
# procedurally-drawn battle stages; unknown names fall back to the
# Kurukshetra plains.
# ---------------------------------------------------------------------
GAME_VS = "VS"          # arcade versus (1P vs CPU or 2P local)
GAME_STORY = "STORY"    # the narrative campaign below

STAGE_BY_NAME = {                       # display name -> stage key
    "kurukshetra": "kurukshetra",
    "training ground": "kurukshetra",
    "lake dwaipayana": "dwaipayana",
    "night camp": "dyut_sabha",
    "hastinapur": "hastinapur",
    "dyut sabha": "dyut_sabha",
    "chakravyuha": "chakravyuha",
}


def resolve_stage(name):
    """Best-effort mapping from a story chapter's arena text to one of
    the four battle stages ('kurukshetra', 'hastinapur', 'dyut_sabha',
    'chakravyuha')."""
    n = (name or "").lower()
    for key, val in STAGE_BY_NAME.items():
        if key in n:
            return val
    return "kurukshetra"


STORY_CHAPTERS = [
    dict(
        num=1,
        title="The Rivalry Begins",
        subtitle="Chapter I — Hastinapur's Training Ground",
        pre_text=["The princes of Hastinapur clash in the arena...",
                  "Gurus watch from the shade. Duryodhana's eyes burn "
                  "with envy at Arjuna's flawless aim."],
        player="ARJUNA", opponent="DURYODHANA",
        stage_name="Training Ground, Hastinapur", stage="kurukshetra",
        ai="MEDIUM",
        after_text=["The Pandava prince proves his skill — but rivalry, "
                    "once watered, grows like a weed through the realm."],
    ),
    dict(
        num=2,
        title="The Dice of Doom",
        subtitle="Chapter II — Dyut Sabha, the Gambling Hall",
        pre_text=["The cursed dice game seals the fate of the Pandavas...",
                  "Yudhishthira stakes his kingdom, his brothers, "
                  "himself — and Shakuni's loaded dice laugh."],
        player="YUDHISHTHIRA", opponent="SHAKUNI",
        stage_name="Dyut Sabha", stage="dyut_sabha",
        ai="MEDIUM",
        after_text=["Thirteen years of exile are written in those dice. "
                    "Dharma bleeds, but it does not break."],
    ),
    dict(
        num=3,
        title="Guru's Test",
        subtitle="Chapter III — Kurukshetra, the Testing Field",
        pre_text=["The young warrior faces the master of warfare...",
                  "Dronacharya asks for his thumb as fee — Abhimanyu "
                  "cuts through every test with arrows of light."],
        player="ABHIMANYU", opponent="DRONACHARYA",
        stage_name="Kurukshetra Battlefield", stage="kurukshetra",
        ai="HARD",
        after_text=["The Guru smiles: no student has ever pierced "
                    "his guard so boldly."],
    ),
    dict(
        num=4,
        title="The Unbreakable Oath",
        subtitle="Chapter IV — Kurukshetra, Day 10",
        pre_text=["The grandsire stands invincible. Only Arjuna can "
                  "face him...",
                  "Bhishma lies on a bed of arrows, yet his bow still "
                  "darkens the sky. His oath: fall only by his own will."],
        player="ARJUNA", opponent="BHISHMA PITAMAH",
        stage_name="Kurukshetra, Day 10", stage="kurukshetra",
        ai="HARD",
        after_text=["Arrows rise like a canopy and hold the grandsire "
                    "aloft. Iccha-mrityu — he chooses his moment."],
    ),
    dict(
        num=5,
        title="Karna's Destiny",
        subtitle="Chapter V — Kurukshetra, Day 17",
        pre_text=["Two greatest warriors. One battlefield. "
                  "Destiny awaits...",
                  "The sun-born king and the peerless archer — brothers "
                  "unknowing — finally stand face to face."],
        player="ARJUNA", opponent="KARNA",
        stage_name="Kurukshetra, Day 17", stage="kurukshetra",
        ai="HARD",
        after_text=["The Vijaya bow falls silent. Karma collects its "
                    "debt, and both brothers weep unseen."],
    ),
    dict(
        num=6,
        title="The Mace Duel",
        subtitle="Chapter VI — Lake Dwaipayana",
        pre_text=["The final reckoning. Bhima's oath will be fulfilled...",
                  "Two gadas, two bodies tempered by war — the wind son "
                  "against the crown prince of Hastinapur."],
        player="BHIMA", opponent="DURYODHANA",
        stage_name="Lake Dwaipayana", stage="hastinapur",
        ai="HARD",
        after_text=["The gada crashes home. An empire's pride sinks "
                    "into the red water of the lake."],
    ),
    dict(
        num=7,
        title="Night of Vengeance",
        subtitle="Chapter VII — The Pandava Camp, After Midnight",
        pre_text=["The son of Drona unleashes hell in the darkness...",
                  "Ashwatthama, cursed and burning, creeps into the camp "
                  "with the Brahmashira glowing on his brow."],
        player="ARJUNA", opponent="ASHWATTHAMA",
        stage_name="Night Camp", stage="dyut_sabha",
        ai="HARD",
        after_text=["The gem is torn from his forehead; the curse "
                    "follows him into endless ages."],
    ),
    dict(
        num=8,
        title="Dharma's Victory",
        subtitle="Final Chapter — Kurukshetra, the Last Hour",
        pre_text=["The ultimate battle. The fate of dharma hangs "
                  "in balance...",
                  "Krishna's chariot wheels touch the earth one last "
                  "time. Aim true, Parth."],
        player="ARJUNA", opponent="KARNA",
        stage_name="Kurukshetra, the Last Hour", stage="chakravyuha",
        ai="HARD",
        powered=True,               # "powered-up" Karna: +stats
        after_text=["The dust settles over Kurukshetra. Dharma stands, "
                    "scarred but unbroken."],
    ),
]

STORY_CREDITS = [
    ("A PRODUCTION", "MAHABHARAT: DIVINE WARFARE"),
    ("WRITING & CODE", "One artist, one pygame, zero image assets"),
    ("LORE SOURCES", "Vyasa's Mahabharata · Ganguli · Neelakantha"),
    ("CAST", "Arjuna · Karna · Bhima · Yudhishthira · Shakuni"),
    ("", "Duryodhana · Bhishma · Drona · Abhimanyu · Ashwatthama"),
    ("MUSIC IN YOUR HEAD", "Conch shells, war-drums and Krishna's flute"),
    ("SPECIAL THANKS", "Every reader who ever wondered who would win"),
]


def powered_up(char_data):
    """Return a copy of a character record buffed for the FINAL chapter
    (used for the powered-up Karna)."""
    d = dict(char_data)
    d["health"] = int(d.get("health", 100) * 1.35)
    d["speed"] = min(9, int(d.get("speed", 5)) + 2)
    d["punch_damage"] = int(d.get("punch_damage", 8) * 1.3)
    d["kick_damage"] = int(d.get("kick_damage", 12) * 1.3)
    d["special_damage"] = int(d.get("special_damage", 25) * 1.25)
    d["name"] = d.get("name", "WARRIOR") + " (DIVINE FORM)"
    d["epithet"] = "Empowered by the Sun's Last Wrath"
    return d


# =====================================================================
# SECTION 5F: AI OPPONENT SYSTEM (single-player CPU fighter)
# =====================================================================
# The brain never touches the Fighter directly.  Every frame it publishes
# a set of *virtual key names* ("left", "punch", ...) in .held; the fight
# scene's _apply_ai_input() maps those onto pygame key constants so the
# CPU walks / blocks / attacks through the EXACT same input pipeline as
# a human.  Decisions are re-rolled every DECIDE_EVERY frames (10f).

AI_LEVELS = ("EASY", "MEDIUM", "HARD")


class AIBrain:
    """Decision engine for one CPU-controlled fighter.

    Difficulty profiles (per spec):
      EASY   - Duryodhana's army soldier: slow reactions, random attacks,
               blocks rarely (30% guard chance), long idle pauses.
      MEDIUM - Kaurava warrior: reacts to player attacks (50% block),
               anti-airs sometimes, uses short combos + specials.
      HARD   - Bhishma-level: predicts movement, blocks most attacks
               (80%), optimal 2-4 hit combos, strategic special usage.

    Per-character personality overrides the profile bias:
      BHIMA/DURYODHANA  aggressive rushers, heavy attacks
      ARJUNA/KARNA      keep distance, fire specials often
      SHAKUNI           defensive trickster, waits for openings
      ABHIMANYU         hyper-aggressive, jumps a lot, fast combos
    """

    DECIDE_EVERY = 10                     # think on a 10-frame cadence

    PROFILES = {
        "EASY":   dict(block=.30, antiair=.40, dodge=.25, combo_max=2,
                       attack_gap=(25, 60), approach=.70, jump=.05),
        "MEDIUM": dict(block=.50, antiair=.60, dodge=.50, combo_max=3,
                       attack_gap=(14, 34), approach=.80, jump=.10),
        "HARD":   dict(block=.80, antiair=.80, dodge=.80, combo_max=4,
                       attack_gap=(8, 20),  approach=.90, jump=.15),
    }

    def __init__(self, fighter, opponent, level="MEDIUM"):
        self.fighter = fighter
        self.opponent = opponent
        self.level = level if level in AI_LEVELS else "MEDIUM"
        self.p = dict(self.PROFILES[self.level])
        self._apply_personality()
        self.held = set()                 # virtual keys pressed this frame
        self.frame = 0
        self.plan = []                    # queued (action, hold_frames)
        self.idle_timer = 0               # human-like hesitation counter

    # ------------------------------------------------------------------
    def _apply_personality(self):
        name = getattr(self.fighter, "name", "")
        if "BHIMA" in name or "DURYODHANA" in name:      # rage rushers
            self.p["approach"] = 0.95
            lo, hi = self.p["attack_gap"]
            self.p["attack_gap"] = (max(6, lo - 6), max(12, hi - 14))
        elif "ARJUNA" in name or "KARNA" in name:        # ranged duelists
            self.p["special_bias"] = 1.4                 # fire astras sooner
        elif "SHAKUNI" in name:                          # defensive trickster
            self.p["block"] = min(0.95, self.p["block"] + 0.15)
            self.p["approach"] = 0.45
        elif "ABHIMANYU" in name:                        # leaping whirlwind
            self.p["jump"] = 0.30
            self.p["attack_gap"] = (6, 14)

    def reset(self):
        """Clear all intent between rounds (brain object survives reset)."""
        self.held.clear()
        self.plan.clear()
        self.idle_timer = 0

    # ------------------------------------------------------------------
    def _distance(self):
        return abs(self.fighter.x - self.opponent.x)

    def _decide(self):
        f, o, p = self.fighter, self.opponent, self.p
        dist = self._distance()
        actions = []

        # ---- REACTION LOGIC (defence reads first — feels human) --------
        o_attacking = o.state in ("punch", "kick") and not o.attack_hit
        o_special = getattr(o, "is_channeling", False)
        o_jumping = o.y < -20                            # airborne threat

        if o_special and random.random() < p["dodge"]:
            actions.append("jump" if random.random() < 0.5 else "back")
        elif o_attacking and dist < 150 and random.random() < p["block"]:
            actions.append("block")
        elif o_jumping and dist < 140 and random.random() < p["antiair"]:
            actions.append("kick")                       # anti-air kick

        # ---- ATTACK PLAN (combo queue built last decision still live?) -
        if self.plan:
            act, n = self.plan[0]
            if act == "wait":
                if n <= 1:
                    self.plan.pop(0)
                else:
                    self.plan[0] = ("wait", n - 1)
                return actions
            actions.append(act)
            if n <= 1:
                self.plan.pop(0)
            else:
                self.plan[0] = (act, n - 1)
            return actions

        # ---- SPECIAL when meter is full AND target is in range ---------
        if f.special_meter >= 100 and dist < 420 \
                and random.random() < 0.55 * p.get("special_bias", 1.0):
            actions.append("special")
            self.idle_timer = random.randint(10, 25)     # recover after cast
            return actions

        # ---- DISTANCE CHECK ---------------------------------------------
        if dist > 200:                                   # FAR: close in
            if random.random() < p["approach"]:
                actions.append("forward")
            if random.random() < p["jump"]:              # leap-in mix-up
                actions.append("jump")
        elif dist > 95:                                  # MEDIUM: mix-up
            if random.random() < p["approach"]:
                actions.append("forward")
            elif random.random() < 0.4:
                actions.append(random.choice(("punch", "kick")))
        else:                                            # CLOSE: strike/guard
            if self.idle_timer > 0:                      # hesitate (human feel)
                self.idle_timer -= self.DECIDE_EVERY
                if random.random() < 0.35:
                    actions.append("block")              # patient bait stance
            elif random.random() < 0.85:
                # build a 2-4 hit combo with random punch/kick timing
                for _ in range(random.randint(2, p["combo_max"])):
                    self.plan.append(
                        (random.choice(("punch", "punch", "kick")), 4))
                    lo, hi = p["attack_gap"]
                    self.plan.append(("wait", random.randint(3, 9)))
                act, n = self.plan.pop(0)
                actions.append(act)
            else:
                actions.append("back")                   # space check

        return actions

    # ------------------------------------------------------------------
    def update(self):
        """Called once per fight frame by FightState (10-frame thinking)."""
        self.frame += 1
        if self.fighter.health <= 0 or self.opponent.health <= 0:
            self.held.clear()
            return
        if self.frame % self.DECIDE_EVERY != 0:
            return
        acts = set(self._decide())
        held = set()
        forward = "right" if self.fighter.facing > 0 else "left"
        back = "left" if self.fighter.facing > 0 else "right"
        if "forward" in acts:
            held.add(forward)
        if "back" in acts:
            held.add(back)
        if "block" in acts:                              # down + back = guard
            held.update(("down", back))
        if "jump" in acts:
            held.add("up")
        for k in ("punch", "kick", "special"):
            if k in acts:
                held.add(k)
        self.held = held


# ---------------------------------------------------------------------
# AIController — PROFESSIONAL wrapper around AIBrain (per spec STEP 1)
# ---------------------------------------------------------------------
# The spec asks for a class taking (fighter, opponent, difficulty).  It
# extends AIBrain with the four-zone distance model, HP-driven behaviour
# phases, optimal-range special usage and the direct-action API
# (move_left / move_right / jump / crouch / punch / kick / block /
# use_special).  Everything still funnels through .held virtual keys so
# the CPU uses the identical input pipeline as the human player.
AI_ZONES = {
    "very_far": 400.0,     # >400px : walk toward player, occasional dash
    "far":      200.0,     # 200-400: cautious approach, prepare to strike
    "medium":   100.0,     # 100-200: jump in / ranged specials
    # <100px is the CLOSE zone: attack, combo or block
}
AI_HP_PHASES = {"aggressive": 70.0, "balanced": 30.0}   # % of max health
AI_REACTION_DELAYS = {"EASY": 30, "MEDIUM": 15, "HARD": 5}   # frames
AI_ATTACK_CHANCE = {"EASY": 0.40, "MEDIUM": 0.60, "HARD": 0.80}
AI_BLOCK_CHANCE = {"EASY": 0.20, "MEDIUM": 0.50, "HARD": 0.75}


class AIController(AIBrain):
    """Professional AI opponent: distance zones + HP phases + personas.

    Difficulty profiles follow the spec exactly:
      EASY   reaction delay 30f, attacks 40%, blocks 20%
      MEDIUM reaction delay 15f, attacks 60%, blocks 50%, uses specials
      HARD   reaction delay  5f, attacks 80%, blocks 75%, perfect specials
    """

    def __init__(self, fighter, opponent, difficulty="MEDIUM"):
        super().__init__(fighter, opponent, difficulty)
        self.difficulty = self.level          # spec-friendly alias
        # ---- spec timing knobs ------------------------------------
        self.reaction_delay = AI_REACTION_DELAYS.get(self.level, 15)
        self.attack_chance = AI_ATTACK_CHANCE.get(self.level, 0.60)
        self.block_chance = AI_BLOCK_CHANCE.get(self.level, 0.50)
        # cadence: one decision every reaction_delay frames (min 5f)
        self.DECIDE_EVERY = max(5, self.reaction_delay // 3)
        # HARD gets near-perfect special play (fires whenever it can)
        if self.level == "HARD":
            self.p["special_bias"] = 1.6
            self.p["combo_max"] = 4
        elif self.level == "EASY":
            self.p["special_bias"] = 0.5      # wastes/forgets astras
        # ---- plan bookkeeping ---------------------------------------
        self.dash_timer = 0                   # frames of dash left
        self.cautious_timer = 0               # far-zone pacing counter
        self.last_zone = ""                   # debug / telemetry
        self.last_phase = "normal"

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    def _zone(self):
        """Four-band distance check (spec STEP 2.1)."""
        d = self._distance()
        if d > AI_ZONES["very_far"]:
            return "very_far"
        if d > AI_ZONES["far"]:
            return "far"
        if d > AI_ZONES["medium"]:
            return "medium"
        return "close"

    def _hp_percent(self):
        f = self.fighter
        try:
            return max(0.0, min(100.0, 100.0 * f.health / max(1, f.max_health)))
        except Exception:                     # never crash mid-fight
            return 100.0

    def _phase(self):
        """HP-based behaviour mode (spec STEP 2.3)."""
        hp = self._hp_percent()
        if hp > AI_HP_PHASES["aggressive"]:
            return "normal"                    # healthy: standard pressure
        if hp >= AI_HP_PHASES["balanced"]:
            return "balanced"                  # midway: mix it up + astras
        return "desperate"                     # <30%: all-or-nothing rush

    def _optimal_range(self):
        """Range where THIS warrior's astral actually lands."""
        kind = getattr(getattr(self.fighter, "astra", None), "get",
                       lambda *_: None)("kind") \
            if isinstance(getattr(self.fighter, "astra", None), dict) else None
        name = getattr(self.fighter, "name", "")
        if kind in ("projectile", "barrage", "disc", "beam"):
            return 180.0, 520.0                # archers: fire from mid range
        if "SHAKUNI" in name:
            return 120.0, 360.0                # trap works at arm's length+
        if "ABHIMANYU" in name:
            return 0.0, 120.0                  # vortex needs to be on top
        return 0.0, 170.0                      # mace/sword melee astras

    def _player_is_dodging(self):
        o = self.opponent
        return (o.y < -20 or o.state in ("crouch", "jump")
                or getattr(o, "dodge_timer", 0) > 0)

    def _player_blocking(self):
        o = self.opponent
        return o.state == "block" or getattr(o, "is_blocking", False)

    def _player_hurt(self):
        o = self.opponent
        return (getattr(o, "is_hit", False) or o.state == "hurt"
                or getattr(o, "stun_timer", 0) > 0
                or getattr(o, "hit_flash", 0) > 6)

    # ------------------------------------------------------------------
    # DIRECT ACTION API (spec STEP 4)
    # Every helper adds a small random delay so the CPU never feels like
    # a metronome; intents still flow through .held -> _apply_ai_input.
    # ------------------------------------------------------------------
    def move_left(self):
        self.held.add("left")
        self.idle_timer = 0

    def move_right(self):
        self.held.add("right")
        self.idle_timer = 0

    def move_toward_player(self):
        if self.opponent.x < self.fighter.x:
            self.move_left()
        else:
            self.move_right()

    def back_off(self):
        if self.opponent.x < self.fighter.x:
            self.move_right()
        else:
            self.move_left()

    def dash(self):
        """Short burst sprint used in the very-far band."""
        self.dash_timer = random.randint(8, 14)
        self.move_toward_player()

    def jump(self):
        self.held.add("up")

    def crouch(self):
        self.held.add("down")

    def punch(self):
        self.held.add("punch")
        self.idle_timer = random.randint(0, 6)     # human-ish follow-up gap

    def kick(self):
        self.held.add("kick")
        self.idle_timer = random.randint(2, 9)

    def anti_air(self):
        """Uppercut-style answer to a leaping opponent: rising kick."""
        self.kick()

    def block(self):
        back = "left" if self.fighter.facing > 0 else "right"
        self.held.update(("down", back))

    def use_special(self):
        self.held.add("special")
        self.idle_timer = random.randint(14, 30)   # recover after the cast

    def throw_or_backoff(self):
        """Vs a blocking player: close in with a heavy kick (grab-ish) or
        step out — chosen by personality roll."""
        if random.random() < 0.55:
            self.plan.append(("kick", 4))           # armour-breaking habit
        else:
            self.back_off()

    # ------------------------------------------------------------------
    # main per-frame brain (spec STEP 2)
    # ------------------------------------------------------------------
    def _decide(self):
        f, o = self.fighter, self.opponent
        p = self.p
        dist = self._distance()
        zone = self._zone()
        phase = self._phase()
        self.last_zone, self.last_phase = zone, phase
        actions = []

        # desperate mode overrides hesitation entirely
        if phase == "desperate":
            self.idle_timer = 0

        # ---- 2. PLAYER STATE AWARENESS (react first) ------------------
        o_attacking = o.state in ("punch", "kick") and not o.attack_hit
        o_special = getattr(o, "is_channeling", False)
        o_jumping = o.y < -20
        react_ok = self.frame % max(1, self.reaction_delay // 3) == 0

        if o_special and random.random() < p["dodge"]:
            # dodge the astra: hop backwards or duck under it
            if random.random() < 0.5:
                self.back_off()
                self.jump()
            else:
                self.crouch()
            return ["evade"]
        if o_attacking and dist < 170 and react_ok \
                and random.random() < self.block_chance:
            self.block()
            return ["block"]
        if o_jumping and dist < 150 and react_ok \
                and random.random() < p["antiair"]:
            self.anti_air()
            return ["antiair"]
        if self._player_hurt() and dist < 130 and phase != "desperate" \
                and random.random() < self.attack_chance + 0.2:
            # punish window: queue a quick 2-4 hit combo
            for _ in range(random.randint(2, p["combo_max"])):
                self.plan.append((random.choice(("punch", "kick")), 4))
            act, n = self.plan.pop(0)
            (self.punch() if act == "punch" else self.kick())
            return [act]
        if self._player_blocking() and dist < 150 and react_ok:
            self.throw_or_backoff()
            return ["vs_block"]

        # ---- queued combo still running? ------------------------------
        if self.plan:
            act, n = self.plan[0]
            if act == "wait":
                if n <= 1:
                    self.plan.pop(0)
                else:
                    self.plan[0] = ("wait", n - 1)
                return actions
            actions.append(act)
            if n <= 1:
                self.plan.pop(0)
            else:
                self.plan[0] = (act, n - 1)
            return actions

        # ---- 4. SPECIAL USAGE (full meter AND optimal range) ----------
        lo_rng, hi_rng = self._optimal_range()
        if f.special_meter >= 100 and lo_rng <= dist <= hi_rng:
            want = {"normal": 0.45, "balanced": 0.70,
                    "desperate": 1.00}[phase] * p.get("special_bias", 1.0)
            if self.level == "HARD":
                want = 1.0 if phase == "desperate" else max(want, 0.8)
            if not (self._player_is_dodging() and self.level != "HARD"
                    and random.random() < 0.6):      # don't waste it
                if random.random() < want:
                    self.use_special()
                    return ["special"]

        # ---- 1. DISTANCE ZONES ----------------------------------------
        if zone == "very_far":
            self.move_toward_player()                 # close the gap
            if random.random() < 0.12:
                self.dash()                           # occasional dash-in
            if random.random() < p["jump"] * 0.5:
                self.jump()
            actions.append("approach")
        elif zone == "far":
            # cautious prodding: step in, stop, re-read the player
            self.cautious_timer += 1
            if self.cautious_timer % 3 == 0:
                self.move_toward_player()
            elif random.random() < 0.25:
                self.back_off()
            if f.special_meter >= 100 and random.random() < 0.25:
                self.use_special()
                actions.append("special")
            actions.append("caution")
        elif zone == "medium":
            # jump-ins and ranged pokes
            if random.random() < p["approach"]:
                self.move_toward_player()
            if random.random() < p["jump"] * (1.6 if "ABHIMANYU"
                                              in getattr(f, "name", "") else 1):
                self.jump()
                self.move_toward_player()
            elif random.random() < 0.35 * self.attack_chance / 0.6:
                actions.append(random.choice(("punch", "kick")))
                self.punch() if actions[-1] == "punch" else self.kick()
            actions.append("mixup")
        else:  # close (<100px)
            if phase == "desperate" and f.special_meter >= 100:
                self.use_special()
                return ["special_desperate"]
            if self.idle_timer > 0 and phase != "desperate":
                self.idle_timer -= self.DECIDE_EVERY
                if random.random() < 0.30:
                    self.block()
                    actions.append("guard")
            elif random.random() < self.attack_chance:
                heavy = "BHIMA" in getattr(f, "name", "") or \
                        "DURYODHANA" in getattr(f, "name", "")
                for _ in range(random.randint(2, p["combo_max"])):
                    pick = "kick" if (heavy and random.random() < 0.6) \
                        else random.choice(("punch", "punch", "kick"))
                    self.plan.append((pick, 4))
                    l_, h_ = p["attack_gap"]
                    self.plan.append(("wait", random.randint(3, 9)))
                act, n = self.plan.pop(0)
                actions.append(act)
                (self.punch() if act == "punch" else self.kick())
            else:
                self.back_off()                       # space check
                actions.append("retreat")
        return actions

    # ------------------------------------------------------------------
    # 3. CHARACTER PERSONALITY (spec STEP 3) — richer than the base map
    # ------------------------------------------------------------------
    def _apply_personality(self):
        name = getattr(self.fighter, "name", "")
        p = self.p
        if "BHIMA" in name:                # rage rusher, heavy swings
            p["approach"], p["attack_bias_heavy"] = 0.97, True
            lo, hi = p["attack_gap"]
            p["attack_gap"] = (max(5, lo - 7), max(11, hi - 15))
            p["special_bias"] = 1.3         # mace astra point-blank
        elif "DURYODHANA" in name:         # aggressive mauler, taunts a lot
            p["approach"] = 0.93
            p["attack_bias_heavy"] = True
            p["taunt"] = True
        elif "ARJUNA" in name:             # zoner: keeps distance, spams astras
            p["approach"] = 0.55
            p["special_bias"] = 1.6
            p["jump"] = max(p["jump"], 0.18)     # tactical hops
        elif "KARNA" in name:              # balanced, banks the meter
            p["special_bias"] = 0.85
            p["patience"] = True
        elif "BHISHMA" in name:            # defensive counter-puncher
            p["block"] = min(0.95, p["block"] + 0.2)
            p["approach"] = 0.5
            p["special_bias"] = 1.1
        elif "ABHIMANYU" in name:          # leaping whirlwind
            p["jump"] = 0.32
            p["approach"] = 0.9
            p["attack_gap"] = (5, 12)
            p["special_bias"] = 1.2
        elif "DRONACHARYA" in name:        # patient, calculated, long range
            p["approach"] = 0.5
            p["attack_gap"] = tuple(c + 6 for c in p["attack_gap"])
            p["special_bias"] = 1.25
        elif "ASHWATTHAMA" in name:        # unpredictable bursts
            p["erratic"] = True
            p["approach"] = 0.75
            p["special_bias"] = 1.15
        elif "YUDHISHTHIRA" in name:       # honourable: waits for openings
            p["approach"] = 0.6
            p["block"] = min(0.95, p["block"] + 0.1)
            p["patient"] = True
        elif "SHAKUNI" in name:            # trickster hit-and-run
            p["approach"] = 0.4
            p["block"] = min(0.95, p["block"] + 0.15)
            p["hit_run"] = True
            p["jump"] = max(p["jump"], 0.2)


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
                if combo >= 3:                     # SOUND TRIGGER: combo 3+
                    play_sound("combo")
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
    """FINAL title screen - six-option menu over an animated battlefield.

        MAHABHARAT          (huge pulsing gold)
        DIVINE WARFARE      (deep red below)

        QUICK BATTLE | STORY MODE | SETTINGS
        HOW TO PLAY  | EXIT

    Up/Down (or W/S) move the cursor, ENTER/SPACE activates, number keys
    1-6 jump straight to an entry.  Background: Kurukshetra sunset +
    drifting embers + slowly rotating dharma chakra; menu BGM starts on
    entry (placeholder-safe: silent without sound files).
    """
    name = STATE_MENU

    # OVERHAUL STEP 3: clean five-option menu (local 2-player removed).
    OPTIONS = ("QUICK", "STORY", "SETTINGS", "HOWTO", "EXIT")
    LABELS = {
        "QUICK":    "\u2694\uFE0F  QUICK BATTLE \u2014 pick your warrior, fight the CPU",
        "STORY":    "\U0001F4DC  STORY MODE \u2014 the Mahabharat campaign",
        "SETTINGS": "\u2699\uFE0F  SETTINGS \u2014 volume \u00b7 controls \u00b7 AI level",
        "HOWTO":    "\U0001F4D6  HOW TO PLAY \u2014 controls & lore",
        "EXIT":     "\U0001F6AA  EXIT",
    }

    def __init__(self, game):
        super().__init__(game)
        self.enter_time = pygame.time.get_ticks()
        self.sel = 0                          # highlighted option index
        # drifting ember/dust particles for the animated background
        self.embers = [[random.uniform(0, SCREEN_WIDTH),
                        random.uniform(0, SCREEN_HEIGHT),
                        random.uniform(0.2, 0.9),                   # rise
                        random.uniform(1, 3),                       # size
                        random.choice((SAFFRON, GOLD, DEEP_RED))]
                       for _ in range(45)]
        self.chakra_angle = 0.0               # slow rotation phase
        play_bgm("menu")                      # music trigger point

    # ------------------------------------------------------------------
    def _activate(self, idx=None):
        key = self.OPTIONS[idx if idx is not None else self.sel]
        g = self.game
        play_sound("confirm")
        if key == "EXIT":
            g.running = False                 # main loop closes gracefully
            return
        if key == "SETTINGS":
            g.change_state(STATE_SETTINGS)
            return
        if key == "HOWTO":
            g.change_state(STATE_HOWTO)
            return
        if key == "STORY":
            g.game_mode = GAME_STORY
            g.two_player = False              # story is always you vs CPU
            g.story_index = 0
            g.story_progress = 0
            g.change_state(STATE_STORY)
            return
        # QUICK BATTLE: hero -> opponent -> difficulty -> fight vs CPU
        g.game_mode = GAME_VS
        g.two_player = False                  # 2-player mode REMOVED
        g.change_state(STATE_CHARACTER_SELECT)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        if k in (pygame.K_UP, pygame.K_w):
            self.sel = (self.sel - 1) % len(self.OPTIONS)
            play_sound("select")
        elif k in (pygame.K_DOWN, pygame.K_s):
            self.sel = (self.sel + 1) % len(self.OPTIONS)
            play_sound("select")
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._activate()
        elif pygame.K_1 <= k <= pygame.K_5:
            self._activate(k - pygame.K_1)

    # ------------------------------------------------------------------
    def update(self, dt_ms):
        # drift the embers upward, recycle at the bottom
        for p in self.embers:
            p[1] -= p[2] * (dt_ms / 16.7)
            p[0] += math.sin(p[1] * 0.02) * 0.35
            if p[1] < -4:
                p[1] = SCREEN_HEIGHT + random.uniform(0, 40)
                p[0] = random.uniform(0, SCREEN_WIDTH)
        self.chakra_angle += dt_ms * 0.00012      # ~one turn / 52 s

    def draw(self, target):
        self.game.background.draw(target, dim=60)
        now = pygame.time.get_ticks()

        # ---- animated background extras: embers + rotating chakra ------
        for x, y, _r, size, col in self.embers:
            glow = pygame.Surface((int(size * 4), int(size * 4)),
                                  pygame.SRCALPHA)
            pygame.draw.circle(glow, (*col, 90),
                               (int(size * 2), int(size * 2)), int(size))
            target.blit(glow, (int(x), int(y)))
        draw_dharma_chakra(target, SCREEN_WIDTH // 2, 486, 92, GOLD,
                           angle_offset=self.chakra_angle)
        draw_dharma_chakra(target, 84, 84, 32, SAFFRON,
                           angle_offset=-self.chakra_angle * 1.7)
        draw_dharma_chakra(target, SCREEN_WIDTH - 84, 84, 32, SAFFRON,
                           angle_offset=self.chakra_angle * 1.7)

        # ---- epic title block -------------------------------------------
        pulse = 1.0 + 0.035 * math.sin((now - self.enter_time) * 0.002)
        big = pygame.font.SysFont("georgia", int(84 * pulse), bold=True)
        draw_centered_text(target, "MAHABHARAT", big, GOLD,
                           SCREEN_WIDTH // 2, 84, shadow=True)
        sub = pygame.font.SysFont("georgia", 40, bold=True)
        draw_centered_text(target, "DIVINE WARFARE", sub, DEEP_RED,
                           SCREEN_WIDTH // 2, 150, shadow=True)
        pygame.draw.line(target, GOLD, (SCREEN_WIDTH // 2 - 240, 186),
                         (SCREEN_WIDTH // 2 + 240, 186), 3)
        pygame.draw.circle(target, GOLD, (SCREEN_WIDTH // 2, 186), 6)
        draw_centered_text(target, "The Kurukshetra Showdown",
                           FONT_MEDIUM, WHITE, SCREEN_WIDTH // 2, 212,
                           shadow=True)

        # ---- five options in one clean centered column ------------------
        # OVERHAUL STEP 3: the selected entry glows GOLD and a small
        # spinning dharma chakra sits beside it as the cursor emblem.
        row_y = 262
        row_gap = 44
        for i, key in enumerate(self.OPTIONS):
            sel = (i == self.sel)
            font = FONT_MEDIUM if sel else FONT_SMALL
            col = GOLD if sel else SAFFRON
            prefix = "" if sel else "   "
            rect = draw_centered_text(target, prefix + self.LABELS[key],
                                      font, col, SCREEN_WIDTH // 2,
                                      row_y + i * row_gap, shadow=sel)
            if sel:
                # underline sweep
                pygame.draw.line(target, SAFFRON,
                                 (rect.x - 10, rect.bottom + 4),
                                 (rect.right + 10, rect.bottom + 4), 2)
                # small chakra icon just left of the highlighted label
                draw_dharma_chakra(target, rect.x - 34,
                                   rect.centery, 11, GOLD, spokes=8,
                                   angle_offset=self.chakra_angle * 6)
                # soft gold glow bar behind the row
                glow = pygame.Surface((rect.width + 60, 34),
                                      pygame.SRCALPHA)
                glow.fill((*GOLD, 34))
                target.blit(glow, (SCREEN_WIDTH // 2 - (rect.width + 60)
                                   // 2, rect.centery - 17))

        # blinking classic prompt kept from v1
        if blink_visible(now - self.enter_time):
            draw_centered_text(target, "Press ENTER to Start",
                               FONT_MEDIUM, SAFFRON, SCREEN_WIDTH // 2,
                               430, shadow=True)

        ai_note = "AI difficulty: %s (change in Settings)" % \
            getattr(self.game, "ai_level", "MEDIUM")
        draw_centered_text(target, ai_note, FONT_SMALL, GREY,
                           SCREEN_WIDTH // 2, 560)
        draw_centered_text(
            target,
            "UP/DOWN navigate \u00b7 ENTER choose \u00b7 1-6 quick pick"
            " \u00b7 ESC quits from menu",
            FONT_SMALL, GREY, SCREEN_WIDTH // 2, 582)


# =====================================================================
# SECTION 7B: SETTINGS SCREEN (volume / controls / AI difficulty)
# =====================================================================

class SettingsState(GameState):
    """SETTINGS panel reached from the title screen.

    Rows (Up/Down or W/S to move, LEFT/RIGHT or A/D to adjust):
      MASTER VOLUME   0..100  (live, persisted to sound_settings.json)
      SFX VOLUME      0..100
      BGM VOLUME      0..100
      AI DIFFICULTY   EASY / MEDIUM / HARD  (used by VS AI + STORY)
    Below the sliders: full control reference for P1 and P2.
    BACK: ESC or B returns to the title screen.
    """
    name = STATE_SETTINGS

    ROWS = ("master", "sfx", "bgm", "ai")

    def __init__(self, game):
        super().__init__(game)
        self.sel = 0
        self.snd = get_sounds()

    # ------------------------------------------------------------------
    def _value(self):
        row = self.ROWS[self.sel]
        if row == "ai":
            return list(AI_LEVELS).index(self.game.ai_level)
        return int(getattr(self.snd, row + "_volume", 1.0) * 100)

    def _adjust(self, delta):
        row = self.ROWS[self.sel]
        if row == "ai":
            cur = list(AI_LEVELS).index(self.game.ai_level)
            step = 1 if delta > 0 else -1
            self.game.ai_level = AI_LEVELS[(cur + step) % len(AI_LEVELS)]
        else:
            cur = int(getattr(self.snd, row + "_volume", 1.0) * 100)
            new = max(0, min(100, cur + (5 if delta > 0 else -5)))
            self.snd.set_volume(row, new / 100.0)
        play_sound("select")

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        if k in (pygame.K_ESCAPE, pygame.K_b):
            play_sound("confirm")
            self.game.change_state(STATE_MENU)
        elif k in (pygame.K_UP, pygame.K_w):
            self.sel = (self.sel - 1) % len(self.ROWS)
            play_sound("select")
        elif k in (pygame.K_DOWN, pygame.K_s):
            self.sel = (self.sel + 1) % len(self.ROWS)
            play_sound("select")
        elif k in (pygame.K_LEFT, pygame.K_a, pygame.K_MINUS):
            self._adjust(-1)
        elif k in (pygame.K_RIGHT, pygame.K_d, pygame.K_EQUALS,
                   pygame.K_PLUS):
            self._adjust(+1)

    def draw(self, target):
        self.game.background.draw(target, dim=140)
        draw_centered_text(target, "SETTINGS",
                           pygame.font.SysFont("georgia", 44, bold=True),
                           GOLD, SCREEN_WIDTH // 2, 56, shadow=True)

        labels = {"master": "MASTER VOLUME", "sfx": "SOUND EFFECTS",
                  "bgm": "BACKGROUND MUSIC", "ai": "AI DIFFICULTY"}
        x0, bar_w = 320, 460
        y = 130
        for i, row in enumerate(self.ROWS):
            sel = (i == self.sel)
            col = GOLD if sel else WHITE
            font = FONT_MEDIUM if sel else FONT_SMALL
            img = font.render(labels[row], True, col)
            target.blit(img, (120, y - img.get_height() // 2))
            val = self._value()
            if row == "ai":
                txt = AI_LEVELS[val]
                tcol = (DEEP_RED, GOLD, GREEN)[val]
                img2 = font.render(txt, True, tcol)
                target.blit(img2, (x0 + bar_w // 2 - img2.get_width() // 2,
                                   y - img2.get_height() // 2))
                if sel:
                    draw_centered_text(
                        target, "\u25C4 EASY / MEDIUM / HARD \u25BA",
                        FONT_SMALL, SAFFRON, x0 + bar_w + 150, y)
            else:
                pygame.draw.rect(target, (40, 30, 20),
                                 (x0, y - 8, bar_w, 16), border_radius=8)
                fill = int(bar_w * val / 100)
                if fill:
                    pygame.draw.rect(target, SAFFRON,
                                     (x0, y - 8, fill, 16), border_radius=8)
                pygame.draw.circle(target, GOLD if sel else WHITE,
                                   (x0 + fill, y), 10)
                img2 = FONT_SMALL.render("%d%%" % val, True, col)
                target.blit(img2, (x0 + bar_w + 18, y - 9))
            y += 52

        # ---- controls reference ---------------------------------------
        pygame.draw.line(target, GOLD, (100, y + 4),
                         (SCREEN_WIDTH - 100, y + 4), 2)
        y += 26
        draw_centered_text(target, "CONTROLS REFERENCE", FONT_MEDIUM, GOLD,
                           SCREEN_WIDTH // 2, y, shadow=True)
        p1_lines = [
            "PLAYER 1",
            "MOVE \u2190 \u2192   JUMP \u2191   CROUCH \u2193",
            "BLOCK: hold \u2193 + away-from-foe",
            "PUNCH Z   KICK X   SPECIAL C",
        ]
        p2_lines = [
            "PLAYER 2",
            "MOVE J L   JUMP I   CROUCH K",
            "BLOCK: hold K + away-from-foe",
            "PUNCH B   KICK N   SPECIAL M",
        ]
        yy = y + 28
        for line in p1_lines:
            draw_centered_text(target, line, FONT_SMALL,
                               DARK_BLUE if line == "PLAYER 1" else WHITE,
                               SCREEN_WIDTH // 2 - 290, yy)
            yy += 24
        yy = y + 28
        for line in p2_lines:
            draw_centered_text(target, line, FONT_SMALL,
                               DEEP_RED if line == "PLAYER 2" else WHITE,
                               SCREEN_WIDTH // 2 + 290, yy)
            yy += 24

        draw_centered_text(target, "Audio status: " + self.snd.status_line(),
                           FONT_SMALL, GREY, SCREEN_WIDTH // 2, 546)
        draw_centered_text(target, "BACK: press ESC or B", FONT_MEDIUM,
                           SAFFRON, SCREEN_WIDTH // 2, 576, shadow=True)


# =====================================================================
# SECTION 7C: HOW TO PLAY SCREEN (controls diagram + rules + lore)
# =====================================================================

class HowToPlayState(GameState):
    """HOW TO PLAY - one-page tutorial drawn with pygame shapes only."""
    name = STATE_HOWTO

    def __init__(self, game):
        super().__init__(game)
        self.t0 = pygame.time.get_ticks()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            self.game.change_state(STATE_MENU)

    def _keycap(self, target, text, x, y, color=DARK_BLUE):
        """Draw a little keyboard key cap centred on (x, y)."""
        f = FONT_SMALL
        img = f.render(text, True, WHITE)
        w, h = img.get_width() + 18, 26
        pygame.draw.rect(target, color, (x - w // 2, y - h // 2, w, h),
                         border_radius=6)
        pygame.draw.rect(target, GOLD, (x - w // 2, y - h // 2, w, h), 2,
                         border_radius=6)
        target.blit(img, img.get_rect(center=(x, y)))

    def _panel(self, target, cx, title, cols, rows):
        """One player's control diagram: mini fighter + labelled keycaps."""
        draw_centered_text(target, title, FONT_MEDIUM, GOLD, cx, 104)
        t = (pygame.time.get_ticks() - self.t0) * 0.004
        bob = int(3 * math.sin(t))
        pygame.draw.circle(target, cols, (cx, 150 + bob), 14)         # head
        pygame.draw.rect(target, cols, (cx - 10, 164 + bob, 20, 34))  # torso
        pygame.draw.lines(target, GOLD, False,                        # arms
                          [(cx - 10, 170), (cx - 26, 188),
                           (cx + 26, 188), (cx + 10, 170)], 3)
        pygame.draw.lines(target, cols, False,                        # legs
                          [(cx - 6, 198), (cx - 11, 226),
                           (cx + 11, 226), (cx + 6, 198)], 3)
        y = 258
        for keys, lab in rows:
            xx = cx - 70
            for k in keys:
                self._keycap(target, k, xx, y, cols)
                xx += 34
            img = FONT_SMALL.render(lab, True, WHITE)
            target.blit(img, (cx + 52, y - img.get_height() // 2))
            y += 36

    def draw(self, target):
        self.game.background.draw(target, dim=150)
        draw_centered_text(target, "HOW TO PLAY",
                           pygame.font.SysFont("georgia", 44, bold=True),
                           GOLD, SCREEN_WIDTH // 2, 50, shadow=True)

        # ---- control diagrams for both players -------------------------
        self._panel(target, 300, "PLAYER 1", DARK_BLUE, [
            (("\u2190", "\u2192"), "move"),
            (("\u2191",), "jump"),
            (("\u2193", "+ back"), "block / crouch"),
            (("Z",), "punch"),
            (("X",), "kick"),
            (("C",), "special (meter full)"),
        ])
        self._panel(target, 900, "PLAYER 2", DEEP_RED, [
            (("J", "L"), "move"),
            (("I",), "jump"),
            (("K", "+ back"), "block / crouch"),
            (("B",), "punch"),
            (("N",), "kick"),
            (("M",), "special (meter full)"),
        ])
        pygame.draw.line(target, GOLD, (600, 110), (600, 460), 2)

        # ---- mechanics explainer --------------------------------------
        lines = [
            ("SPECIAL METER", GOLD,
             "Deal AND take damage to fill the divine meter. At 100% the "
             "warrior glows and 'DIVINE POWER READY!' flashes \u2014 then "
             "unleash the signature Astra!"),
            ("COMBOS", GREEN,
             "Chain hits within one second to raise the combo counter; "
             "'X HIT COMBO!' pops above the attacker."),
            ("BLOCKING", (120, 160, 255),
             "Hold down + back to guard: incoming damage drops to 25%, "
             "but a blocked hit briefly stuns the guard."),
            ("ROUNDS", SAFFRON,
             "Best of 3 rounds, 99 seconds each. On time-out the fighter "
             "with more HP takes the round. Win 2 to claim the match."),
        ]
        y = 300
        for head, col, body in lines:
            target.blit(FONT_SMALL.render(head, True, col), (70, y))
            words, cur, ly = body.split(), "", y
            for w in words:
                if FONT_SMALL.size(cur + " " + w)[0] > 460:
                    target.blit(FONT_SMALL.render(cur, True, WHITE),
                                (210, ly))
                    ly += 18
                    cur = w
                else:
                    cur = (cur + " " + w).strip()
            target.blit(FONT_SMALL.render(cur, True, WHITE), (210, ly))
            y = ly + 30

        # ---- brief lore ------------------------------------------------
        draw_centered_text(
            target,
            "THE LORE: sixteen days of war at Kurukshetra decide the fate "
            "of Dharma vs Adharma \u2014 ten great warriors, one destiny.",
            FONT_SMALL, SAFFRON, SCREEN_WIDTH // 2, 552)
        draw_centered_text(
            target, "Choose your hero wisely \u2014 press any key to return",
            FONT_MEDIUM, GOLD, SCREEN_WIDTH // 2, 580, shadow=True)


class CharacterSelectState(GameState):
    """OVERHAUL STEP 4 — three-phase selection flow for QUICK BATTLE.

      PHASE 1  "CHOOSE YOUR WARRIOR"   - pick your hero (arrows + ENTER)
      PHASE 2  "CHOOSE YOUR OPPONENT"  - pick the CPU fighter (arrows + ENTER)
      PHASE 3  "SELECT DIFFICULTY"     - EASY / MEDIUM / HARD (arrows + ENTER)

    The card grid keeps the classic look: 5x2 cards, each showing the name
    in character colour, a mini drawn warrior, HP/SPD/PWR stat bars, weapon
    and special-move name; dharma chakras spin in the corners; the bottom
    panel previews description + intro dialogue of the hovered hero.

    Local 2-player has been REMOVED, so only ONE cursor exists and every
    match ends with an AI-controlled opponent.
    """
    name = STATE_CHARACTER_SELECT

    # ---- layout geometry -------------------------------------------
    COLS, ROWS = 5, 2
    CARD_W, CARD_H = 216, 148
    GRID_X, GRID_Y = 24, 138
    GAP_X, GAP_Y = 9, 12
    PANEL_TOP = 470                     # start of the info panel

    PHASES = ("hero", "opponent", "difficulty")
    PHASE_TITLES = {
        "hero":       "CHOOSE YOUR WARRIOR",
        "opponent":   "CHOOSE YOUR OPPONENT",
        "difficulty": "SELECT DIFFICULTY",
    }

    def __init__(self, game):
        super().__init__(game)
        self.phase_idx = 0                       # index into PHASES
        self.hero_idx = 0                        # ARJUNA default
        self.opp_idx = len(ROSTER) - 1           # SHAKUNI default
        self.cursor = 0                          # live grid cursor
        self.diff_idx = 1                        # EASY/MED/HARD -> MED
        self.t = 0                               # animation timer (frames)
        self.launch_timer = None                 # frames until fight starts
        self.flash = 0                           # white flash on lock-in

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    @property
    def phase(self):
        return self.PHASES[self.phase_idx]

    def cell_rect(self, i):
        """Screen rect of roster card number i (5 columns x 2 rows)."""
        col, row = i % self.COLS, i // self.COLS
        x = self.GRID_X + col * (self.CARD_W + self.GAP_X)
        y = self.GRID_Y + row * (self.CARD_H + self.GAP_Y)
        return pygame.Rect(x, y, self.CARD_W, self.CARD_H)

    def _move(self, idx, dx, dy):
        """Wrap-aware grid navigation for the single cursor."""
        col, row = idx % self.COLS, idx // self.COLS
        col = (col + dx) % self.COLS
        row = (row + dy) % self.ROWS
        return row * self.COLS + col

    def _confirm(self):
        """Lock the current phase and advance the flow."""
        play_sound("confirm")
        self.flash = 8
        if self.phase == "hero":
            self.hero_idx = self.cursor
            self.phase_idx = 1
        elif self.phase == "opponent":
            self.opp_idx = self.cursor
            self.phase_idx = 2
        else:                                    # difficulty confirmed
            self.game.ai_level = AI_LEVELS[self.diff_idx]
            self.launch_timer = 60               # short dramatic pause
            return
        # never let you fight yourself as the CPU
        if self.hero_idx == self.opp_idx:
            self.opp_idx = (self.opp_idx + 1) % len(ROSTER)
        # reposition the one shared cursor for the new phase
        self.cursor = (self.hero_idx if self.phase == "hero"
                       else self.opp_idx)

    # ------------------------------------------------------------------
    # input - arrows navigate everything, ENTER confirms, ESC steps back
    # ------------------------------------------------------------------
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        if k == pygame.K_ESCAPE:
            if self.launch_timer is not None:
                self.launch_timer = None
            elif self.phase == "difficulty":
                self.phase_idx = 1
                self.cursor = self.opp_idx
            elif self.phase == "opponent":
                self.phase_idx = 0
                self.cursor = self.hero_idx
            else:
                self.game.change_state(STATE_MENU)
            return
        if self.launch_timer is not None:
            return

        if self.phase == "difficulty":
            # simple left/right selector over EASY | MEDIUM | HARD
            if k in (pygame.K_LEFT, pygame.K_a):
                self.diff_idx = (self.diff_idx - 1) % len(AI_LEVELS)
                play_sound("select")
            elif k in (pygame.K_RIGHT, pygame.K_d):
                self.diff_idx = (self.diff_idx + 1) % len(AI_LEVELS)
                play_sound("select")
            elif k in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._confirm()
            return

        # grid phases -------------------------------------------------
        if k == pygame.K_LEFT:
            self.cursor = self._move(self.cursor, -1, 0)
            play_sound("select")
        elif k == pygame.K_RIGHT:
            self.cursor = self._move(self.cursor, +1, 0)
            play_sound("select")
        elif k == pygame.K_UP:
            self.cursor = self._move(self.cursor, 0, -1)
            play_sound("select")
        elif k == pygame.K_DOWN:
            self.cursor = self._move(self.cursor, 0, +1)
            play_sound("select")
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._confirm()

    # ------------------------------------------------------------------
    # per-frame update (auto-launch once difficulty is locked)
    # ------------------------------------------------------------------
    def update(self, dt):
        self.t += 1
        if self.flash > 0:
            self.flash -= 1
        if self.launch_timer is not None:
            self.launch_timer -= 1
            if self.launch_timer <= 0:
                self.game.start_fight(ROSTER[self.hero_idx],
                                      ROSTER[self.opp_idx])

    # ------------------------------------------------------------------
    # drawing - cards
    # ------------------------------------------------------------------
    def _draw_card(self, target, i, hero):
        r = self.cell_rect(i)
        hovered = (i == self.cursor and self.phase != "difficulty")
        chosen_hero = (i == self.hero_idx and self.phase != "hero")
        chosen_opp = (i == self.opp_idx and self.phase == "opponent"
                      and i != self.cursor)
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
        wtag = FONT_TINY.render(hero["weapon"], True, GREY)
        target.blit(wtag, (r.right - wtag.get_width() - 6, r.y + 7))

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
        sn = "\u2605 " + hero["special_name"]
        if FONT_TINY.size(sn)[0] > r.width - 12:     # shrink-fit long names
            sn = "\u2605 " + hero["special_name"][:14] + "\u2026"
        st = FONT_TINY.render(sn, True, spc)
        target.blit(st, (r.centerx - st.get_width() // 2, r.bottom - 18))

        # ---- glowing cursor border: red = picking hero, blue = CPU pick
        if hovered:
            warm = self.phase == "hero"
            base = DEEP_RED if warm else DARK_BLUE
            edge = (255, 70, 70) if warm else (90, 150, 255)
            pulse = 150 + 105 * abs(math.sin(self.t * 0.08))
            glow_surf = pygame.Surface((r.w + 16, r.h + 16),
                                       pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (*base, int(pulse) // 2),
                             (0, 0, r.w + 16, r.h + 16), 8,
                             border_radius=14)
            target.blit(glow_surf, (r.x - 8, r.y - 8))
            pygame.draw.rect(target, edge, r, 3, border_radius=10)
            tag_txt = "YOU" if self.phase == "hero" else "CPU"
            tag = FONT_TINY.render(tag_txt, True, WHITE)
            target.blit(tag, (r.x + 4, r.y - 20))

        # ---- locked picks show a green check mark ----
        if chosen_hero:
            ok = FONT_TINY.render("\u2713 YOU", True, GREEN)
            target.blit(ok, (r.x + 4, r.y - 20))
        if chosen_opp:
            ok = FONT_TINY.render("\u2713 CPU", True, GREEN)
            target.blit(ok, (r.right - ok.get_width() - 4, r.y - 20))

    # ------------------------------------------------------------------
    # drawing - difficulty picker (phase 3)
    # ------------------------------------------------------------------
    DIFF_INFO = {
        "EASY":   ("Duryodhana\u2019s army soldier \u2014 slow reactions, "
                   "random attacks, rarely blocks.", (120, 200, 120)),
        "MEDIUM": ("Kaurava warrior \u2014 reads your attacks, strings "
                   "combos, fires astras when ready.", GOLD),
        "HARD":   ("Bhishma-level \u2014 predicts movement, blocks almost "
                   "everything, punishes hard.", DEEP_RED),
    }

    def _draw_difficulty(self, target):
        y = self.GRID_Y + 20
        cw, gap = 260, 40
        total = len(AI_LEVELS) * cw + (len(AI_LEVELS) - 1) * gap
        x0 = (SCREEN_WIDTH - total) // 2
        for i, lvl in enumerate(AI_LEVELS):
            r = pygame.Rect(x0 + i * (cw + gap), y, cw, 150)
            sel = (i == self.diff_idx)
            pygame.draw.rect(target, (22, 12, 30), r, border_radius=12)
            desc_col = self.DIFF_INFO[lvl][1]
            if sel:
                pulse = 150 + 105 * abs(math.sin(self.t * 0.09))
                glow = pygame.Surface((r.w + 18, r.h + 18), pygame.SRCALPHA)
                pygame.draw.rect(glow, (*GOLD, int(pulse) // 2),
                                 (0, 0, r.w + 18, r.h + 18), 6,
                                 border_radius=16)
                target.blit(glow, (r.x - 9, r.y - 9))
                pygame.draw.rect(target, GOLD, r, 3, border_radius=12)
            draw_centered_text(target, lvl, FONT_LARGE,
                               GOLD if sel else GREY,
                               r.centerx, r.y + 22)
            lines = wrap_text(self.DIFF_INFO[lvl][0], FONT_TINY,
                              r.width - 24, 3)
            ly = r.y + 80
            for ln in lines:
                img = FONT_TINY.render(ln, True, desc_col)
                target.blit(img, (r.centerx - img.get_width() // 2, ly))
                ly += 17
        draw_centered_text(
            target, "Your warrior: " + ROSTER[self.hero_idx]["name"] +
                    "   vs   CPU: " + ROSTER[self.opp_idx]["name"],
            FONT_SMALL, WHITE, SCREEN_WIDTH // 2, y + 180)

    # ------------------------------------------------------------------
    # drawing - bottom info panel (description + dialogue quote)
    # ------------------------------------------------------------------
    def _draw_panel(self, target):
        p = pygame.Rect(24, self.PANEL_TOP, SCREEN_WIDTH - 48, 112)
        pygame.draw.rect(target, (18, 10, 26), p, border_radius=12)
        pygame.draw.rect(target, (120, 70, 20), p, 2, border_radius=12)
        draw_dharma_chakra(target, p.x + 26, p.centery, 16, SAFFRON,
                           spokes=12, angle_offset=self.t * 0.02)
        draw_dharma_chakra(target, p.right - 26, p.centery, 16, SAFFRON,
                           spokes=12, angle_offset=-self.t * 0.02)

        hero = ROSTER[self.cursor]
        head = hero["name"] + " \u2014 " + hero["epithet"]
        h = FONT_SMALL.render(head, True, hero["color"])
        target.blit(h, (p.x + 56, p.y + 8))
        desc = wrap_text(hero["description"], FONT_TINY, 520, 2)
        yy = p.y + 34
        for line in desc:
            target.blit(FONT_TINY.render(line, True, GREY), (p.x + 56, yy))
            yy += 17
        # hovering previews the intro dialogue (rotates between the lines)
        quote_src = (hero["intro_dialogue"][0]
                     if self.t // 45 % 2 == 0 else hero["intro_dialogue"][1])
        qlines = wrap_text("\u201c" + quote_src + "\u201d", FONT_TINY,
                           470, 2)
        qy = p.y + 34
        for line in qlines:
            img = FONT_TINY.render(line, True, GOLD)
            target.blit(img, (p.right - 56 - img.get_width() - 8, qy))
            qy += 17

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
        draw_centered_text(target, self.PHASE_TITLES[self.phase],
                           FONT_LARGE, GOLD, SCREEN_WIDTH // 2, 26,
                           shadow=True)
        hint = ("ARROW KEYS browse \u00b7 ENTER confirm \u00b7 ESC back"
                if self.phase != "difficulty"
                else "LEFT/RIGHT choose \u00b7 ENTER start battle "
                     "\u00b7 ESC back")
        draw_centered_text(target, hint, FONT_SMALL, SAFFRON,
                           SCREEN_WIDTH // 2, 100)

        # ---- phase progress dots ----
        for pi in range(len(self.PHASES)):
            cx = SCREEN_WIDTH // 2 + (pi - 1) * 34
            done = pi < self.phase_idx
            now = pi == self.phase_idx
            pygame.draw.circle(target, GOLD if now else
                               (GREEN if done else GREY), (cx, 78), 6)

        # ---- content of the current phase ----
        if self.phase == "difficulty":
            self._draw_difficulty(target)
        else:
            for i, hero in enumerate(ROSTER):
                self._draw_card(target, i, hero)

        # ---- bottom info panel ----
        self._draw_panel(target)

        # ---- status line under the grid ----
        if self.phase != "difficulty":
            who = "YOU" if self.phase == "hero" else "CPU OPPONENT"
            status = who + ": " + ROSTER[self.cursor]["name"]
            if self.phase == "opponent":
                status = ("YOU: " + ROSTER[self.hero_idx]["name"] +
                          "   |   " + status)
            draw_centered_text(target, status, FONT_SMALL, WHITE,
                               SCREEN_WIDTH // 2,
                               self.GRID_Y + 2 * self.CARD_H +
                               self.GAP_Y + 26)

        # ---- launch sequence banner ----
        if self.launch_timer is not None:
            grow = 1.0 + 0.35 * math.sin(self.t * 0.35)
            fs = pygame.font.SysFont("arial", max(20, int(56 * grow)),
                                     bold=True)
            draw_centered_text(target, "THE WAR BEGINS...", fs, SAFFRON,
                               SCREEN_WIDTH // 2, 250, shadow=True)
            draw_centered_text(target,
                               "AI LEVEL: " + AI_LEVELS[self.diff_idx],
                               FONT_MEDIUM, GOLD, SCREEN_WIDTH // 2, 310)

        # ---- white lock-in flash ----
        if self.flash > 0:
            veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT),
                                  pygame.SRCALPHA)
            veil.fill((255, 255, 255, self.flash * 12))
            target.blit(veil, (0, 0))


class FightState(GameState):
    """Real-time combat between the two selected fighters.

    All stats, weapons and dialogues come from the CHARACTERS database:
      intro_dialogue   -> cinematic pre-fight spotlight scene (Round 1)
      low_hp_dialogue  -> desperate cry when HP falls below 30%
      special_dialogue -> typewriter box when an astra is unleashed
      taunt            -> shouted when a combo reaches 5 hits (+idle barks)
      win_dialogue     -> typewriter box as the round is won
      lose_dialogue    -> typewriter box on the RESULT screen
    """
    name = STATE_FIGHT

    def __init__(self, game, p1_data, p2_data, show_intro=True):
        super().__init__(game)
        # Fighters are built straight from the CHARACTERS database records.
        # y = 0 means "standing on the ground line" (GROUND_Y == 430).
        self.f1 = Fighter(p1_data, 300, 0, facing=1, is_player2=False,
                          controls=P1_KEYS)
        # OVERHAUL STEP 2: the opponent slot is ALWAYS machine-driven now.
        self.f2 = Fighter(p2_data, 900, 0, facing=-1, is_player2=True,
                          controls=None)
        # ---- AI OPPONENT SYSTEM: P2's slot is run by an AIController.
        # The brain publishes virtual key intents which _apply_ai_input()
        # folds into the same input pipeline the human player uses.  It
        # also re-points at the live fighters after every round reset.
        self.ai_level = getattr(game, "ai_level", "MEDIUM")
        self.p2_is_ai = True                    # fixed: no local 2-player
        self.f2.brain = AIController(self.f2, self.f1, self.ai_level)
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

        # ============ DIALOGUE AND CINEMATIC INTRO SYSTEM =============
        # Three independent queues: the long pre-fight cinematic, the
        # short mid-fight shouts (specials) and the round-end speeches.
        self.dialogues = DialogueQueue()
        self.intro_dialogues = DialogueQueue()
        self.end_dialogues = DialogueQueue()
        self.intro_playing = False          # cinematic owns the screen?
        self.intro_frame = 0                # frames elapsed in the segment
        self.intro_segment = ""             # FADE/P1_SPOT/SWISH/P2_SPOT/VS/BEGIN
        self.intro_zoom = 1.0               # slow zoom factor this segment
        self.show_intro = bool(show_intro)  # STORY MODE skips the film
        # ---- BATTLE STAGE hook ----
        # Story chapters pin an arena ("kurukshetra"/"hastinapur"/
        # "dyut_sabha"/"chakravyuha"); arcade bouts fall back to the
        # default sunset plains of Kurukshetra.
        self.stage_name = getattr(game, "story_stage", None) or "kurukshetra"
        # SOUND TRIGGERS: battle music for THIS stage (falls back to the
        # generic "battle" track name if no per-stage file is present —
        # SoundManager tries both before resorting to silence/beeps), and
        # the round-start cue when the announcer shouts "FIGHT!".
        play_bgm("battle_" + self.stage_name)
        self._round_start_cued = False     # armed once controls unlock
        self._intro_build(p1_data, p2_data)
        if self.show_intro:
            self._intro_start("FADE")
        else:                               # straight to combat (story mode)
            self.intro_segment = "DONE"
            self._intro_start("DONE")
        self.banner = None                  # legacy ribbon not used for intro

    # ---------- helpers ----------
    def set_banner(self, text, color=WHITE, ms=2800):
        self.banner = (text, color, pygame.time.get_ticks() + ms)

    def say(self, text, speaker=None, color=None,
            duration=DIALOGUE_DEFAULT_DURATION):
        """DIALOGUE SYSTEM entry point — queue one typewriter line."""
        self.dialogues.add(text, speaker=speaker or "",
                           color=color or GOLD, duration=duration)

    # ==================================================================
    # CINEMATIC PRE-FIGHT INTRO (plays once, before Round 1)
    #   FADE -> P1_SPOT (2 lines) -> SWISH -> P2_SPOT (2 lines)
    #        -> VS standoff -> "YUDDH AARAMBH!" -> live combat
    # Each spotlight shot animates a slow zoom by scaling the fighter.
    # ==================================================================
    INTRO_ORDER = ("P1_SPOT", "SWISH", "P2_SPOT", "SWISH",
                   "VS", "BEGIN")

    def _intro_build(self, p1_data, p2_data):
        """Queue both intro_dialogue lines for P1, then for P2."""
        q = self.intro_dialogues
        q.clear()
        for line in list(p1_data.get("intro_dialogue", []))[:2]:
            q.add(line, speaker=p1_data.get("name", "P1"),
                  color=p1_data.get("color", SAFFRON),
                  duration=INTRO_LINE_FRAMES)
        for line in list(p2_data.get("intro_dialogue", []))[:2]:
            q.add(line, speaker=p2_data.get("name", "P2"),
                  color=p2_data.get("color", DARK_BLUE),
                  duration=INTRO_LINE_FRAMES)

    def _intro_start(self, segment):
        """Jump the cinematic to a new beat and reset its frame clock."""
        self.intro_segment = segment
        self.intro_frame = 0
        if segment == "FADE":
            self.intro_playing = True
            for f in (self.f1, self.f2):
                f.intro_lock = True           # nobody moves during the film
                f.draw_scale = 1.0
        elif segment == "P1_SPOT":
            self.f2.x = 940.0                 # push the foe out of the shot
            self.f1.facing = 1
            self.f1.state = "idle"
        elif segment == "P2_SPOT":
            self.f1.x = 260.0
            self.f2.facing = -1
            self.f2.state = "idle"
        elif segment == "VS":
            self.f1.x = 300.0
            self.f2.x = 900.0
            self.f1.facing, self.f2.facing = 1, -1
            self.fx.shake(10, 5)              # the clash shakes the lens
            self.fx.flash(FLASH_FRAMES + 1)
        elif segment == "BEGIN":
            self.fx.shake(8, 4)
        elif segment == "DONE":
            self.intro_playing = False
            for f in (self.f1, self.f2):
                f.intro_lock = False
                f.draw_scale = 1.0
            self.round_start = pygame.time.get_ticks()   # start the 99 s clock
            self.taunt_at = self.round_start + random.randint(9000, 14000)
            self.set_banner("ROUND 1  —  YUDDH AARAMBH!", SAFFRON, 1600)

    def _intro_segment_len(self, segment):
        """Frames this beat runs when no dialogue is attached to it."""
        if segment == "FADE":
            return INTRO_FADE_IN
        if segment == "SWISH":
            return INTRO_SWISH_FRAMES
        if segment in ("P1_SPOT", "P2_SPOT"):
            return max(INTRO_SPOT_FRAMES,
                       len(self.intro_dialogues.entries) *
                       INTRO_LINE_FRAMES)
        if segment == "VS":
            return INTRO_VS_FRAMES
        if segment == "BEGIN":
            return INTRO_BEGIN_FRAMES
        return 10

    def _intro_next(self):
        seq = list(self.INTRO_ORDER)
        try:
            i = seq.index(self.intro_segment)
        except ValueError:
            i = -1
        if i + 1 < len(seq):
            self._intro_start(seq[i + 1])
        else:
            self._intro_start("DONE")

    def _update_intro(self):
        """Advance the cinematic one frame (also drains fx request queues)."""
        self.intro_frame += 1
        seg = self.intro_segment
        if seg in ("P1_SPOT", "P2_SPOT"):
            self.intro_dialogues.update()
            held = self.intro_dialogues.active
            span = self._intro_segment_len(seg)
            frac = min(1.0, self.intro_frame / max(1, span))
            self.intro_zoom = _intro_zoom(frac)
            hero = self.f1 if seg == "P1_SPOT" else self.f2
            hero.draw_scale = self.intro_zoom
            if held:
                self.intro_frame = min(self.intro_frame, span - 1)
            elif self.intro_frame >= span:
                self.intro_dialogues.clear()
                self._intro_next()
        else:
            self.intro_zoom = 1.0
            self.f1.draw_scale = 1.0
            self.f2.draw_scale = 1.0
            if self.intro_frame >= self._intro_segment_len(seg):
                self._intro_next()
        # particles / camera requests still tick while the film plays
        self.fx.update()
        self._drain_fx_requests()
        if self.hit_freeze_frames > 0:
            self.hit_freeze_frames -= 1
        if self.flash_frames > 0:
            self.flash_frames -= 1
        if self.tint_frames > 0:
            self.tint_frames -= 1
        if self.shake_frames > 0:
            self.shake_frames -= 1

    def _draw_intro(self, world_target):
        """Render whichever beat of the film is currently playing."""
        seg = self.intro_segment
        if seg == "FADE":
            k = self.intro_frame / max(1, INTRO_FADE_IN)
            veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT),
                                  pygame.SRCALPHA)
            veil.fill((0, 0, 0, int(255 * max(0.0, 1.0 - k))))
            world_target.blit(veil, (0, 0))
            draw_centered_text(world_target, "KURUKSHETRA", FONT_MEDIUM,
                               GREY, SCREEN_WIDTH // 2, 60)
            return
        if seg == "SWISH":
            self._draw_spot_shot(world_target, None)
            k = self.intro_frame / max(1, INTRO_SWISH_FRAMES)
            band = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT),
                                  pygame.SRCALPHA)
            band.fill((0, 0, 0, 255))
            gap_h = int(SCREEN_HEIGHT * (1.0 - abs(k - 0.5) * 2.0))
            pygame.Rect(0, 0, SCREEN_WIDTH, 0)
            cut = int(SCREEN_HEIGHT // 2 - gap_h // 2)
            pygame.draw.rect(band, (0, 0, 0, 255), (0, 0, SCREEN_WIDTH, cut))
            pygame.draw.rect(band, (0, 0, 0, 255),
                             (0, cut + gap_h, SCREEN_WIDTH,
                              SCREEN_HEIGHT - cut - gap_h))
            world_target.blit(band, (0, 0))
            return
        if seg in ("P1_SPOT", "P2_SPOT"):
            self._draw_spot_shot(world_target, seg)
            return
        if seg == "VS":
            self._draw_vs_screen(world_target)
            return
        if seg == "BEGIN":
            self._draw_begin_screen(world_target)
            return

    def _spot_focus(self, seg):
        """Which warrior owns the current spotlight shot ('' for none)."""
        if seg == "P1_SPOT":
            return self.f1
        if seg == "P2_SPOT":
            return self.f2
        return None

    def _draw_spot_shot(self, world_target, seg):
        """Black stage + spotlight cone on ONE fighter + his dialogue box."""
        hero = self._spot_focus(seg)
        # black backdrop first so nothing of the arena leaks through
        bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        bg.fill((2, 1, 6, 255))
        world_target.blit(bg, (0, 0))
        # faint dharma chakra watermark behind the hero
        if hero is not None:
            draw_dharma_chakra(world_target, int(hero.x), 200, 150,
                               hero.special_color, spokes=16,
                               angle_offset=self.intro_frame * 0.01,
                               width=2, alpha=45)
            foot_y = int(GROUND_Y - hero.y)
            radius = int(INTRO_SPOT_RADIUS *
                         (0.75 + 0.25 * min(1.0, self.intro_frame /
                                           max(1, INTRO_SPOT_FRAMES))))
            draw_spotlight(world_target, hero.x, foot_y, radius,
                           tint=tuple(min(255, c + 90)
                                      for c in hero.color))
            hero.draw(world_target)
            # speaker stripe so the eye knows who is talking
            name_col = hero.color if hero.color != WHITE else GOLD
            draw_centered_text(world_target, hero.name, FONT_LARGE,
                               name_col, SCREEN_WIDTH // 2, 78, shadow=True)
            epithet = hero.data.get("epithet", "")
            if epithet:
                draw_centered_text(world_target, epithet, FONT_SMALL,
                                   GREY, SCREEN_WIDTH // 2, 118)
        else:                                       # swish: pure darkness
            veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT),
                                  pygame.SRCALPHA)
            veil.fill((0, 0, 0, 235))
            world_target.blit(veil, (0, 0))
        self.intro_dialogues.draw(world_target)
        # skip hint
        draw_centered_text(world_target, "koi bhi key: dialogue skip",
                           FONT_TINY, GREY, SCREEN_WIDTH - 120,
                           SCREEN_HEIGHT - 22)

    def _draw_vs_screen(self, world_target):
        """Dramatic VS standoff: both warriors facing each other."""
        self.game.background.draw(world_target)
        veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        veil.fill((6, 3, 12, 200))
        world_target.blit(veil, (0, 0))
        # radial speed-lines bursting from the centre
        cx, cy = SCREEN_WIDTH // 2, 250
        for i in range(20):
            a = i * math.tau / 20 + self.intro_frame * 0.03
            r0 = 120 + (self.intro_frame * 3 % 60)
            pygame.draw.line(world_target, (*SAFFRON, ),
                             (cx + math.cos(a) * r0, cy + math.sin(a) * r0),
                             (cx + math.cos(a) * (r0 + 70),
                              cy + math.sin(a) * (r0 + 70)), 2)
        self.f1.draw(world_target)
        self.f2.draw(world_target)
        # huge gold VS slamming together
        k = min(1.0, self.intro_frame / max(1, INTRO_VS_FRAMES * 0.45))
        size = int(60 + 90 * k)
        vs_font = pygame.font.SysFont("arial", max(30, size), bold=True)
        left = self.f1.name + "  "
        right = "  " + self.f2.name
        draw_centered_text(world_target, left + "VS" + right, FONT_MEDIUM,
                           WHITE, cx, 150, shadow=True)
        img = vs_font.render("VS", True, GOLD)
        img = pygame.transform.rotate(img, -8 + 8 * k)
        world_target.blit(img, img.get_rect(center=(cx, 250)))
        sh = vs_font.render("VS", True, DEEP_RED)
        world_target.blit(sh, sh.get_rect(center=(cx + 5, 255)))
        draw_centered_text(world_target, "DHARMA YUDDH", FONT_SMALL,
                           SAFFRON, cx, 330, shadow=True)

    def _draw_begin_screen(self, world_target):
        """"YUDDH AARAMBH!" (Battle Begin!) in Sanskrit-style gold."""
        self.game.background.draw(world_target)
        veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 150))
        world_target.blit(veil, (0, 0))
        self.f1.draw(world_target)
        self.f2.draw(world_target)
        cx, cy = SCREEN_WIDTH // 2, 250
        k = min(1.0, self.intro_frame / max(1, INTRO_BEGIN_FRAMES * 0.5))
        pulse = 1.0 + 0.06 * math.sin(self.intro_frame * 0.35)
        big = pygame.font.SysFont("arial", max(30, int(64 * k * pulse)),
                                  bold=True)
        # Devanagari flourish + romanised transliteration
        draw_centered_text(world_target, "युद्ध आरम्भ!", FONT_MEDIUM,
                           SAFFRON, cx, cy - 58, shadow=True)
        draw_centered_text(world_target, "YUDDH AARAMBH!", big, GOLD,
                           cx, cy, shadow=True)
        draw_centered_text(world_target, "— BATTLE BEGIN! —", FONT_SMALL,
                           WHITE, cx, cy + 52, shadow=True)
        # gold rule lines sweeping outward
        half = int(300 * k)
        pygame.draw.line(world_target, GOLD, (cx - half, cy + 26),
                         (cx - 40, cy + 26), 3)
        pygame.draw.line(world_target, GOLD, (cx + 40, cy + 26),
                         (cx + half, cy + 26), 3)
        pygame.draw.circle(world_target, GOLD, (cx, cy + 26), 5)

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
        # NOTE (OVERHAUL STEP 2): the old human-P2 bindings (I/J/K/L move,
        # B punch, N kick, M special) are GONE — the opponent slot is now
        # exclusively driven by AIBrain via _apply_ai_input().
        # ---- CPU JUMP: brains hold "up" virtually; the human pipeline
        # only sees KEYDOWN, so we translate the rising edge here.
        if getattr(self.f2, "brain", None):
            held_now = "up" in self.f2.brain.held
            if held_now and not getattr(self, "_ai_up_prev", False):
                self.f2.jump()
            self._ai_up_prev = held_now

    @staticmethod
    def _back_key_action(held_back, down_held):
        return "block" if (held_back and down_held) else "crouch"

    # ------------------------------------------------------------------
    # AI CONTROL LAYER — virtual keyboard for the CPU fighter
    # ------------------------------------------------------------------
    # The fight scene drives both fighters through pygame.key.get_pressed.
    # For the CPU we build a *virtual* key state: every frame the brain
    # publishes its intent as key names ("left", "punch", ...) and those
    # names are mapped onto real pygame key constants inside a copy of the
    # pressed-keys array.  That way the AI uses exactly the same input
    # pipeline (and therefore the same blocking / crouching rules) as a
    # human player.
    AI_KEYMAP = {
        "left": pygame.K_LEFT, "right": pygame.K_RIGHT,
        "up": pygame.K_UP, "down": pygame.K_DOWN,
        "punch": pygame.K_z, "kick": pygame.K_x, "special": pygame.K_c,
    }

    def _apply_ai_input(self):
        """Return the held-key array, with P2's slots overwritten by the
        CPU's virtual presses whenever an AI fighter occupies that slot."""
        pressed = pygame.key.get_pressed()
        cpu = None
        if getattr(self.f2, "brain", None):   # ALWAYS true post-overhaul
            cpu = self.f2
        elif getattr(self.f1, "brain", None):
            cpu = self.f1
        if cpu is None:
            return pressed
        arr = pressed[:]                     # private copy for the CPU slot
        for code in list(self.AI_KEYMAP.values()):
            arr[code] = False
        for act in cpu.brain.held:
            code = self.AI_KEYMAP.get(act)
            if code is not None:
                arr[code] = True
        return arr

    def _process_movement(self):
        """HOLD-based controls, evaluated fresh every frame.

        P1: LEFT/RIGHT walk, UP jump (edge), DOWN crouch,
            DOWN + *back* direction  ->  BLOCK (guard)
        P2: J/L walk, I jump (edge), K crouch,
            K + *back* direction      ->  BLOCK (guard)

        "Back" simply means the arrow pointing away from the opponent,
        which is the classic fighting-game guard input.

        When a fighter is CPU-controlled its brain publishes a set of
        virtual key presses (_apply_ai_input) so the AI walks, jumps,
        blocks and crouches through exactly the same code path as a human.
        """
        pressed = self._apply_ai_input()
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

        # ---------------- CPU OPPONENT (AI brain only) ----------------
        # OVERHAUL STEP 2: no human ever controls fighter #2 any more.
        # The brain's virtual keys were already folded into `pressed` by
        # _apply_ai_input(), so we simply run the SAME movement rules on
        # that array for f2.  (rev2 keeps MAYA JAAL mind-games working.)
        f = self.f2
        rev2 = now_ms < f.controls_reversed_until
        left_held = bool(pressed[pygame.K_RIGHT]) if rev2 \
            else bool(pressed[pygame.K_LEFT])
        right_held = bool(pressed[pygame.K_LEFT]) if rev2 \
            else bool(pressed[pygame.K_RIGHT])
        down_held = bool(pressed[pygame.K_DOWN])
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
            # SOUND TRIGGER: the swing itself (punch / kick) connects...
            play_sound(attacker.state if attacker.state in ("punch", "kick")
                       else "hit")
            applied = defender.take_hit(raw_dmg, attacker)

            # ---- DAMAGE SYSTEM: meter gain = 1.5x damage actually dealt --
            attacker.add_meter(applied)

            # ---- COMBO SYSTEM: consecutive hits within 60 frames ---------
            combo = attacker.register_hit(blocked=was_blocking)
            if combo >= 2:
                self.combo_pops.append(
                    (attacker, f"{combo} HIT COMBO!", 70))
            if combo >= 3:                     # SOUND TRIGGER: combo 3+
                play_sound("combo")

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
                    if combo >= 3:                 # SOUND TRIGGER: combo 3+
                        play_sound("combo")
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
        # SOUND TRIGGER: the "FIGHT!" announcer cue, fired exactly once
        # per round the moment controls unlock (also re-armed by the
        # round reset in _begin_next_round).
        if intro_left:
            self._round_start_cued = False
        elif not self._round_start_cued and not self.winner:
            self._round_start_cued = True
            play_sound("round_start")
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
                # ---- AI OPPONENT SYSTEM: think before the input pass ----
                for f in (self.f1, self.f2):
                    if getattr(f, "brain", None):
                        try:
                            f.brain.update()       # never crash mid-fight
                        except Exception as _exc:  # pragma: no cover
                            print(f"[ai-guard] {f.name}: {_exc!r}")
                            f.brain.held.clear()
                self._process_movement()
                for _f, _o in ((self.f1, self.f2), (self.f2, self.f1)):
                    try:
                        _f.update(_o)              # guarded: never crash
                    except Exception as _exc:      # pragma: no cover
                        print(f"[fighter-guard] {_f.name}: {_exc!r}")
                # ---- CRASH-PROOF COMBAT PIPELINE --------------------
                # try/except guards around every risky step (projectile
                # flight, hitbox intersections, particle bookkeeping).
                # A single bad frame must NEVER close the game mid-fight:
                # we simply log and let the next frame continue.
                for _step in (self._resolve_hits,
                              self._update_astra_projectiles,
                              self._resolve_projectiles,
                              self._resolve_vortex,
                              self._drain_fx_requests):
                    try:
                        _step()
                    except Exception as _exc:      # pragma: no cover
                        print(f"[fx-guard] {_step.__name__}: {_exc!r}")
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
                if getattr(self.game, "game_mode", GAME_VS) == GAME_STORY:
                    # ---- STORY MODE: chapter resolved, no result screen --
                    ch = STORY_CHAPTERS[min(self.game.story_index,
                                            len(STORY_CHAPTERS) - 1)]
                    player_won = (self.winner is self.f1)
                    self.game.story_last_win = player_won
                    if player_won:
                        self.game.story_progress = max(
                            self.game.story_progress, ch["num"])
                        self.game.story_index = min(
                            self.game.story_index + 1,
                            len(STORY_CHAPTERS) - 1)
                    self.game.change_state(STATE_STORY)
                else:
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
            # SOUND TRIGGER: the bout is decided -> victory music takes
            # over from the battle loop (fade-style stop, then load).
            play_bgm("victory")

    def _reset_fighter(self, f, facing):
        """Put one fighter back to its starting stance for a new round.

        Rebuilds a completely fresh Fighter (so every attack / stun /
        astral-effect timer starts clean) using the stored char record,
        spawn x and keymap, then re-seeds the HUD's smooth-drain value."""
        slot = 0 if not f.is_player2 else 1
        old_brain = getattr(f, "brain", None)   # POLISH: keep the CPU alive
        fresh = Fighter(self.spawn_data[slot]["data"],
                        self.spawn_data[slot]["x"], 0,
                        facing=facing, is_player2=f.is_player2,
                        controls=f.controls)
        # swap the live fighter's whole state with the fresh instance
        f.__dict__.clear()
        f.__dict__.update(fresh.__dict__)
        f.display_health = float(f.health)
        # POLISH: the AI brain survives a round reset — re-attach it and
        # clear any stale plan so the CPU starts the new round fresh.
        if old_brain is not None:
            f.brain = old_brain
            old_brain.reset()
            # keep the brain wired to the LIVE fighter pair after reset —
            # __dict__ swap replaced self.f2's identity inside the brain
            old_brain.fighter = f
            old_brain.opponent = self.f1 if f.is_player2 else self.f2

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

    # ------------------------------------------------------------------
    # BATTLE STAGES — four arenas drawn entirely with pygame shapes
    #   kurukshetra : sunset plains (the baked BattlefieldBackground)
    #   hastinapur  : moonlit palace hall with flickering torches
    #   dyut_sabha  : the dim gambling hall, dice & oil lamps
    #   chakravyuha : the vortex formation, stormy sky & rotating rings
    # The story mode pins one arena per chapter; arcade bouts use the
    # Kurukshetra plains.  Backdrops are baked once and cached.
    # ------------------------------------------------------------------
    STAGE_TITLES = {
        "kurukshetra": "KURUKSHETRA — THE FIELD OF DHARMA",
        "hastinapur": "HASTINAPUR — THE PALACE OF KINGS",
        "dyut_sabha": "DYUT SABHA — THE HALL OF DOOMED DICE",
        "chakravyuha": "CHAKRAVYUHA — THE ENDLESS VORTEX",
    }

    def _bake_stage(self, key):
        """Paint one static backdrop for `key` onto a cached surface."""
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        gy = GROUND_Y                       # 430 — fighters stand here
        if key == "hastinapur":
            # night sky + moon + stars
            draw_vertical_gradient(s, (6, 8, 34), (48, 26, 78))
            for _ in range(90):
                sx, sy = random.randint(0, SCREEN_WIDTH), \
                    random.randint(0, int(gy * 0.55))
                pygame.draw.circle(s, (230, 230, 255), (sx, sy),
                                   random.choice((1, 1, 2)))
            pygame.draw.circle(s, (238, 236, 210), (1010, 96), 44)
            pygame.draw.circle(s, (6, 8, 34), (1028, 84), 40)
            # marble floor
            draw_vertical_gradient_region(
                s, (0, gy, SCREEN_WIDTH, SCREEN_HEIGHT - gy),
                (150, 140, 150), (58, 50, 66))
            for i in range(0, SCREEN_WIDTH, 100):
                pygame.draw.line(s, (96, 88, 104), (i, gy),
                                 (i - 60, SCREEN_HEIGHT), 2)
            # pillars + archways
            for px in (90, 330, 870, 1110):
                pygame.draw.rect(s, (72, 52, 96),
                                 (px - 34, 150, 68, gy - 150))
                pygame.draw.rect(s, (110, 84, 140),
                                 (px - 42, 138, 84, 22), border_radius=6)
                pygame.draw.arc(s, (150, 120, 60),
                                (px - 30, 170, 60, 120), 0, math.pi, 5)
            for ax in (480, 720):
                pygame.draw.rect(s, (30, 20, 48), (ax - 70, 210, 140,
                                                   gy - 210))
                pygame.draw.arc(s, (150, 120, 60), (ax - 70, 150, 140,
                                                    140), 0, math.pi, 6)
            # royal banners
            for bx, col in ((200, DEEP_RED), (1000, (60, 40, 150))):
                pygame.draw.rect(s, col, (bx - 26, 160, 52, 170))
                pygame.draw.polygon(s, col, [(bx - 26, 330), (bx, 356),
                                             (bx + 26, 330)])
                pygame.draw.circle(s, GOLD, (bx, 250), 10)
        elif key == "dyut_sabha":
            # oppressive dim interior
            draw_vertical_gradient(s, (14, 8, 12), (52, 26, 16))
            # ornate pillars
            for px in (120, 360, 840, 1080):
                pygame.draw.rect(s, (60, 36, 22), (px - 30, 120, 60,
                                                   gy - 120))
                pygame.draw.rect(s, (120, 84, 30), (px - 38, 108, 76, 20))
                for k in range(3):
                    pygame.draw.line(s, (90, 60, 24), (px - 26, 180 + k * 70),
                                     (px + 26, 180 + k * 70), 3)
            # throne dais
            pygame.draw.rect(s, (70, 44, 20), (500, 300, 200, gy - 300))
            pygame.draw.rect(s, (110, 74, 28), (520, 190, 160, 130),
                             border_radius=10)
            pygame.draw.circle(s, GOLD, (600, 200), 22)
            pygame.draw.rect(s, (40, 24, 12), (560, 250, 80, 70))
            # marble carpet
            draw_vertical_gradient_region(
                s, (0, gy, SCREEN_WIDTH, SCREEN_HEIGHT - gy),
                (74, 40, 30), (28, 14, 10))
            pygame.draw.rect(s, (120, 84, 30), (0, gy, SCREEN_WIDTH, 6))
            # scattered gambling dice on the floor
            for _ in range(9):
                dx = random.randint(60, SCREEN_WIDTH - 90)
                dy = random.randint(gy + 30, SCREEN_HEIGHT - 46)
                dsz = random.randint(16, 26)
                pygame.draw.rect(s, (235, 228, 210), (dx, dy, dsz, dsz),
                                 border_radius=4)
                pygame.draw.rect(s, (120, 100, 80), (dx, dy, dsz, dsz), 1,
                                 border_radius=4)
                for _pip in range(random.randint(1, 5)):
                    pygame.draw.circle(
                        s, DEEP_RED,
                        (dx + random.randint(3, dsz - 3),
                         dy + random.randint(3, dsz - 3)), 2)
        else:                                # chakravyuha (and fallbacks)
            draw_vertical_gradient(s, (10, 12, 48), (74, 40, 120))
            # storm clouds
            for _ in range(26):
                cx, cy = random.randint(0, SCREEN_WIDTH), \
                    random.randint(20, 200)
                pygame.draw.ellipse(s, (34, 30, 70),
                                    (cx, cy, random.randint(90, 220),
                                     random.randint(24, 50)))
            # floating weapon silhouettes in the sky
            for _ in range(10):
                wx, wy = random.randint(40, SCREEN_WIDTH - 60), \
                    random.randint(60, 250)
                ang = random.uniform(0, math.tau)
                ln = random.randint(26, 52)
                pygame.draw.line(s, (150, 150, 200), (wx, wy),
                                 (wx + math.cos(ang) * ln,
                                  wy + math.sin(ang) * ln), 3)
            # violet ground with concentric rings (aerial feel)
            draw_vertical_gradient_region(
                s, (0, gy, SCREEN_WIDTH, SCREEN_HEIGHT - gy),
                (44, 26, 84), (16, 10, 34))
            cxs = SCREEN_WIDTH // 2
            for r in range(40, 620, 56):
                pygame.draw.ellipse(s, (96, 70, 170),
                                    (cxs - r, gy + 130 - r // 3,
                                     r * 2, max(10, r // 2)), 2)
        return s

    def _get_stage_surface(self, key):
        cache = self.game.stage_cache
        if key not in cache:
            cache[key] = self._bake_stage(key)
        return cache[key]

    def _draw_battle_stage(self, target):
        """Blit the current arena, then paint its animated layer."""
        key = getattr(self, "stage_name", "kurukshetra")
        if key == "kurukshetra":
            self.game.background.draw(target)
            return
        target.blit(self._get_stage_surface(key), (0, 0))
        t = self.fight_frame
        gy = GROUND_Y
        if key == "hastinapur":
            # flickering torches on every pillar
            for px in (90, 330, 870, 1110):
                for tx in (px - 34, px + 34):
                    fy = 250 + math.sin(t * 0.3 + tx) * 3
                    fl = random.randint(9, 15)
                    pygame.draw.circle(target, (255, 170, 60),
                                       (tx, int(fy)), fl, )
                    pygame.draw.circle(target, (255, 230, 120),
                                       (tx, int(fy)), max(3, fl - 6))
                    glow = pygame.Surface((90, 90), pygame.SRCALPHA)
                    pygame.draw.circle(glow, (255, 150, 40, 46),
                                       (45, 45), 40)
                    target.blit(glow, (tx - 45, int(fy) - 45))
        elif key == "dyut_sabha":
            # swaying oil lamps with warm halos
            for lx in (240, 600, 960):
                ly = 170 + math.sin(t * 0.05 + lx) * 4
                pygame.draw.line(target, (120, 84, 30), (lx, 120),
                                 (lx, ly), 3)
                pygame.draw.ellipse(target, (200, 140, 60),
                                    (lx - 14, ly, 28, 16))
                pygame.draw.circle(target, (255, 200, 90),
                                   (lx, int(ly) + 4),
                                   random.randint(4, 7))
                halo = pygame.Surface((160, 160), pygame.SRCALPHA)
                pygame.draw.circle(halo, (255, 170, 60, 34), (80, 80), 70)
                target.blit(halo, (lx - 80, int(ly) - 60))
            veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT),
                                  pygame.SRCALPHA)
            veil.fill((0, 0, 0, 70))
            target.blit(veil, (0, 0))
        elif key == "chakravyuha":
            # swirling energy rings + random lightning strobes
            cx = SCREEN_WIDTH // 2
            for i in range(4):
                r = 60 + i * 46
                a0 = t * 0.02 * (1 if i % 2 else -1)
                pygame.draw.arc(target, (120, 200, 255),
                                (cx - r, gy + 120 - r // 3, r * 2,
                                 max(14, r // 2)),
                                a0, a0 + math.pi * 1.4, 3)
            if (t % 210) < 6 or random.random() < 0.006:
                flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT),
                                       pygame.SRCALPHA)
                flash.fill((220, 230, 255, 90))
                target.blit(flash, (0, 0))
                x = random.randint(100, SCREEN_WIDTH - 100)
                pts = [(x, 0)]
                for yy in range(40, 300, 40):
                    pts.append((x + random.randint(-46, 46), yy))
                pygame.draw.lines(target, WHITE, False, pts, 3)

    def _draw_stage_name(self, target):
        """Arena title card that fades out at the start of every round."""
        if not hasattr(self, "round_start"):
            return
        elapsed = pygame.time.get_ticks() - self.round_start
        if elapsed > 2200:
            return
        alpha = 255 if elapsed < 1500 else int(255 * (1 - (elapsed - 1500)
                                                      / 700.0))
        label = self.STAGE_TITLES.get(getattr(self, "stage_name", ""), "")
        if not label:
            return
        img = FONT_MEDIUM.render(label, True, GOLD)
        box = pygame.Surface((img.get_width() + 46, img.get_height() + 22),
                             pygame.SRCALPHA)
        box.fill((10, 5, 16, max(0, min(200, alpha))))
        rect = box.get_rect(center=(SCREEN_WIDTH // 2, 400))
        target.blit(box, rect)
        img.set_alpha(max(0, min(255, alpha)))
        target.blit(img, img.get_rect(center=rect.center))

    def draw(self, world_target):
        """Render the whole fight onto an off-screen canvas, then blit it
        to the display with a random offset while shake_frames > 0 —
        that offset IS the screen shake every special requests."""
        self._draw_battle_stage(world_target)
        self.f1.draw(world_target)
        self.f2.draw(world_target)
        # ---- AI VISUAL INDICATOR: "CPU" tag floating over the head ----
        for _f in (self.f1, self.f2):
            try:
                _f.draw_ai_tag(world_target)
            except Exception:               # never crash the render pass
                pass

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
        self._draw_stage_name(screen)   # fading arena title card

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
        # AI VISUAL INDICATOR (spec STEP 5): the CPU slot shows its level
        # right next to the health bar, e.g. "AI - HARD".
        prefix = "P1  " if not f.is_player2 else ""
        if getattr(f, "brain", None) is not None:
            lvl = getattr(f.brain, "level", "?")
            prefix += "AI - %s   " % lvl
        name_img = FONT_SMALL.render(prefix + f.name, True,
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


class StoryNarrativeState(GameState):
    """STORY MODE narrative screen — black background, dramatic text.

    Three flavours, chosen from the game controller's bookkeeping:
      * INTRO   : chapter title + pre-fight text ("press any key")
      * OUTRO   : after_text of the chapter just won -> next chapter
      * DEFEAT  : "The Mahabharat ends differently..." -> retry option

    Pressing any key advances; ENTER on the defeat screen retries the
    same chapter, ESC returns to the title menu.
    """
    name = STATE_STORY

    def __init__(self, game):
        super().__init__(game)
        self.enter_time = pygame.time.get_ticks()
        # decide which flavour this visit is
        if getattr(game, "story_last_win", None) is False:
            self.flavour = "DEFEAT"
        elif game.story_progress > 0 and                 not getattr(game, "_story_intro_shown", True):
            self.flavour = "INTRO"
        else:
            self.flavour = "INTRO"
        # if a chapter was just won, show its outro instead of an intro
        if game.story_last_win is True:
            self.flavour = "OUTRO"
        idx = min(game.story_index, len(STORY_CHAPTERS) - 1)
        self.chapter_idx = idx
        # the outro reads the chapter that was just finished
        if self.flavour == "OUTRO":
            self.chapter_idx = max(0, idx - 1) if game.story_progress >=                 STORY_CHAPTERS[idx]["num"] else idx
            self.chapter_idx = max(0, min(idx, len(STORY_CHAPTERS) - 1))
            # story_index already advanced -> last played was index-1
            self.chapter_idx = max(0, idx - 1)
        self.chapter = STORY_CHAPTERS[self.chapter_idx]
        self.fade_in_frames = 0

    # ------------------------------------------------------------------
    # launching the pinned fight for the current chapter
    # ------------------------------------------------------------------
    def _begin_chapter_fight(self, ch=None):
        g = self.game
        ch = ch or self.chapter
        p1 = get_character(ch["player"])
        opp = get_character(ch["opponent"])
        if ch.get("powered"):
            opp = powered_up(opp)
        g.story_stage = resolve_stage(ch.get("stage_name")
                                      or ch.get("stage", ""))
        g.story_final = (ch["num"] == len(STORY_CHAPTERS))
        g.two_player = False          # story mode is always single player
        g.start_fight(p1, opp, show_intro=False)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        if k == pygame.K_ESCAPE:
            self.game.game_mode = GAME_VS
            self.game.change_state(STATE_MENU)
            return
        if self.flavour == "DEFEAT":
            if k in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_y):
                self.game.story_last_win = None
                self._begin_chapter_fight()
            elif k == pygame.K_n:
                self.game.game_mode = GAME_VS
                self.game.change_state(STATE_MENU)
            return
        if self.flavour == "OUTRO":
            ch_now = STORY_CHAPTERS[min(self.game.story_index,
                                        len(STORY_CHAPTERS) - 1)]
            if self.game.story_progress >= len(STORY_CHAPTERS):
                self.game.change_state(STATE_STORY_ENDING)
            else:
                # outro done -> show the NEXT chapter's intro card
                self.game.story_last_win = None
                nxt = STORY_CHAPTERS[min(self.game.story_index,
                                         len(STORY_CHAPTERS) - 1)]
                self.chapter = nxt
                self.chapter_idx = min(self.game.story_index,
                                       len(STORY_CHAPTERS) - 1)
                self.flavour = "INTRO"
                self.enter_time = pygame.time.get_ticks()
                del ch_now
            return
        # INTRO -> straight into the battle
        self._begin_chapter_fight()

    def update(self, dt):
        self.fade_in_frames += 1

    def draw(self, target):
        target.fill(BLACK)
        now = pygame.time.get_ticks()
        alpha = min(255, self.fade_in_frames * 8)
        spin = (now - self.enter_time) * 0.0006
        # faint dharma chakras watching from the corners
        draw_dharma_chakra(target, 40, 40, 26, SAFFRON, 16, spin, alpha=90)
        draw_dharma_chakra(target, SCREEN_WIDTH - 40, 40, 26, SAFFRON,
                           16, -spin, alpha=90)
        draw_dharma_chakra(target, 40, SCREEN_HEIGHT - 40, 26, GOLD, 16,
                           -spin, alpha=70)
        draw_dharma_chakra(target, SCREEN_WIDTH - 40, SCREEN_HEIGHT - 40,
                           26, GOLD, 16, spin, alpha=70)

        if self.flavour == "DEFEAT":
            draw_centered_text(target, "PARAJAY — DEFEAT", FONT_LARGE,
                               DEEP_RED, SCREEN_WIDTH // 2, 110, shadow=True)
            lines = ["The Mahabharat ends differently..."]
            sub = [f"You fell in Chapter {self.chapter['num']}: "
                   f"“{self.chapter['title']}”.",
                   "Vyasa's scroll curls at the edges — but fate can be",
                   "read again. RISE, warrior. The war is not over."]
            y = 230
            for ln in lines:
                draw_centered_text(target, ln, FONT_MEDIUM, WHITE,
                                   SCREEN_WIDTH // 2, y)
                y += 44
            for ln in sub:
                draw_centered_text(target, ln, FONT_SMALL, GREY,
                                   SCREEN_WIDTH // 2, y)
                y += 26
            if blink_visible(now - self.enter_time):
                draw_centered_text(target,
                                   "ENTER: Fight the chapter again    |    "
                                   "N: Abandon the saga",
                                   FONT_MEDIUM, SAFFRON,
                                   SCREEN_WIDTH // 2, 470, shadow=True)
            return

        ch = self.chapter
        if self.flavour == "INTRO":
            draw_centered_text(target, f"CHAPTER {ch['num']} OF "
                               f"{len(STORY_CHAPTERS)}", FONT_SMALL, GREY,
                               SCREEN_WIDTH // 2, 70)
            draw_centered_text(target, ch["title"], FONT_LARGE, GOLD,
                               SCREEN_WIDTH // 2, 130, shadow=True)
            draw_centered_text(target, ch["subtitle"], FONT_SMALL, SAFFRON,
                               SCREEN_WIDTH // 2, 190)
            y = 250
            for para in ch["pre_text"]:
                for ln in wrap_text(para, FONT_MEDIUM,
                                    SCREEN_WIDTH - 260, max_lines=3):
                    draw_centered_text(target, ln, WHITE,
                                       SCREEN_WIDTH // 2, y)
                    y += 34
                y += 8
            # matchup plate
            p1 = get_character(ch["player"])
            p2 = get_character(ch["opponent"])
            plate = pygame.Rect(SCREEN_WIDTH // 2 - 300, y + 20, 600, 74)
            pygame.draw.rect(target, (20, 10, 28), plate, border_radius=12)
            pygame.draw.rect(target, (*SAFFRON, ), plate, 2,
                             border_radius=12)
            draw_mini_warrior(target, pygame.Rect(plate.x + 12,
                                                  plate.y + 6, 56, 62),
                              p1, self.fade_in_frames)
            draw_mini_warrior(target, pygame.Rect(plate.right - 68,
                                                  plate.y + 6, 56, 62),
                              p2, self.fade_in_frames + 30)
            draw_centered_text(target, f"{p1['name']}   VS   "
                               f"{p2['name']}", FONT_MEDIUM, GOLD,
                               plate.centerx, plate.centery - 10)
            arena = ch.get("stage_name", "Kurukshetra")
            ai_tag = f"Foe temperament: {ch.get('ai', 'MEDIUM')}"
            draw_centered_text(target, f"Arena: {arena}   ·   {ai_tag}",
                               FONT_TINY, GREY, plate.centerx,
                               plate.centery + 22)
            if blink_visible(now - self.enter_time):
                draw_centered_text(target, "Press any key to enter the arena",
                                   FONT_SMALL, SAFFRON, SCREEN_WIDTH // 2,
                                   560)
        else:  # OUTRO
            draw_centered_text(target, "CHAPTER COMPLETE", FONT_MEDIUM,
                               GREEN, SCREEN_WIDTH // 2, 80, shadow=True)
            draw_centered_text(target, ch["title"], FONT_LARGE, GOLD,
                               SCREEN_WIDTH // 2, 150, shadow=True)
            y = 250
            for para in ch.get("after_text", []):
                for ln in wrap_text(para, FONT_MEDIUM,
                                    SCREEN_WIDTH - 260, max_lines=3):
                    draw_centered_text(target, ln, WHITE,
                                       SCREEN_WIDTH // 2, y)
                    y += 34
            prog = self.game.story_progress
            bar_w = 520
            bx = SCREEN_WIDTH // 2 - bar_w // 2
            by = 430
            pygame.draw.rect(target, (40, 24, 12), (bx, by, bar_w, 18),
                             border_radius=9)
            fill = int(bar_w * prog / len(STORY_CHAPTERS))
            pygame.draw.rect(target, GOLD, (bx, by, max(4, fill), 18),
                             border_radius=9)
            pygame.draw.rect(target, SAFFRON, (bx, by, bar_w, 18), 2,
                             border_radius=9)
            draw_centered_text(target, f"The Saga: {prog} / "
                               f"{len(STORY_CHAPTERS)} chapters told",
                               FONT_SMALL, SAFFRON, SCREEN_WIDTH // 2,
                               by + 34)
            if blink_visible(now - self.enter_time):
                draw_centered_text(target, "Press any key to continue",
                                   FONT_SMALL, WHITE, SCREEN_WIDTH // 2,
                                   540)
        # dim-in veil so the cut between screens feels cinematic
        if alpha < 255:
            veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT),
                                  pygame.SRCALPHA)
            veil.fill((0, 0, 0, 255 - alpha))
            target.blit(veil, (0, 0))


class StoryEndingState(GameState):
    """Victory-of-Dharma finale: "DHARMA KI VIJAY!" plus rolling credits."""
    name = STATE_STORY_ENDING

    def __init__(self, game):
        super().__init__(game)
        self.enter_time = pygame.time.get_ticks()
        self.scroll = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.game.game_mode = GAME_VS
                self.game.change_state(STATE_MENU)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.game.game_mode = GAME_VS
                self.game.change_state(STATE_MENU)

    def update(self, dt):
        self.scroll += 1

    def draw(self, target):
        target.fill(BLACK)
        now = pygame.time.get_ticks()
        spin = (now - self.enter_time) * 0.0008
        draw_dharma_chakra(target, SCREEN_WIDTH // 2, 250, 120, GOLD,
                           24, spin, width=3, alpha=120)
        pulse = 1.0 + 0.04 * math.sin((now - self.enter_time) * 0.003)
        big = pygame.font.SysFont("arial", max(40, int(70 * pulse)),
                                  bold=True)
        draw_centered_text(target, "धर्म की विजय", FONT_LARGE, SAFFRON,
                           SCREEN_WIDTH // 2, 110, shadow=True)
        draw_centered_text(target, "DHARMA KI VIJAY!", big, GOLD,
                           SCREEN_WIDTH // 2, 190, shadow=True)
        draw_centered_text(target, "Victory of Righteousness — the saga "
                           "of Kurukshetra is told", FONT_SMALL, WHITE,
                           SCREEN_WIDTH // 2, 350)
        # rolling credits
        y = 400 - (self.scroll % (len(STORY_CREDITS) * 40 + 200))
        for label, text in STORY_CREDITS:
            if -30 < y < SCREEN_HEIGHT:
                if label:
                    lb = FONT_TINY.render(label, True, SAFFRON)
                    target.blit(lb, (SCREEN_WIDTH // 2 - 300, y))
                tx = FONT_SMALL.render(text, True, GREY)
                target.blit(tx, (SCREEN_WIDTH // 2 - 120, y - 3))
            y += 40
        if blink_visible(now - self.enter_time):
            draw_centered_text(target, "Press ENTER to return to the title",
                               FONT_SMALL, SAFFRON, SCREEN_WIDTH // 2, 570)


# =====================================================================
# SECTION 7: GAME CONTROLLER (state machine + main loop)
# =====================================================================

class Game:
    """Owns the state machine and the fixed 60 FPS game loop."""

    def __init__(self):
        self.background = BattlefieldBackground()
        self.result_winner = None
        # ---- STORY MODE bookkeeping ----
        self.game_mode = GAME_VS          # GAME_VS | GAME_STORY
        self.two_player = False           # True only for local 2P versus
        self.story_index = 0              # next chapter to play
        self.story_progress = 0           # chapters already won
        self.story_final = False          # True while stage 8 is fought
        self.story_stage = None           # arena pinned by the chapter
        self.story_last_win = None        # last chapter outcome (bool)
        self.stage_cache = {}             # baked battle-stage surfaces
        # ---- AI OPPONENT SYSTEM: difficulty chosen in SETTINGS -------
        self.ai_level = "MEDIUM"          # EASY | MEDIUM | HARD
        self.states = {}
        self.state = None
        self.states[STATE_MENU] = MenuState(self)
        self.states[STATE_CHARACTER_SELECT] = CharacterSelectState(self)
        self.states[STATE_RESULT] = ResultState(self)
        self.states[STATE_SETTINGS] = SettingsState(self)
        self.states[STATE_HOWTO] = HowToPlayState(self)
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
        elif state_name == STATE_SETTINGS:
            self.states[STATE_SETTINGS] = SettingsState(self)
        elif state_name == STATE_HOWTO:
            self.states[STATE_HOWTO] = HowToPlayState(self)
        elif state_name == STATE_STORY:
            self.states[STATE_STORY] = StoryNarrativeState(self)
        elif state_name == STATE_STORY_ENDING:
            self.states[STATE_STORY_ENDING] = StoryEndingState(self)
        self.state = self.states[state_name]

    def start_fight(self, p1_data, p2_data, show_intro=True):
        """Create the fight scene and switch to it.

        show_intro=False is used by STORY MODE: the narrative screen has
        already set the scene, so the bout opens instantly with the
        classic "FIGHT!" announcement instead of the spotlight film."""
        self.states[STATE_FIGHT] = FightState(self, p1_data, p2_data,
                                              show_intro=show_intro)
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
