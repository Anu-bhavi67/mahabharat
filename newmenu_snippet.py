class MenuState(GameState):
    """FINAL title screen - six-option menu over an animated battlefield.

        MAHABHARAT          (huge pulsing gold)
        DIVINE WARFARE      (deep red below)

        STORY MODE | 2 PLAYER BATTLE | VS AI
        SETTINGS   | HOW TO PLAY     | QUIT

    Up/Down (or W/S) move the cursor, ENTER/SPACE activates, number keys
    1-6 jump straight to an entry.  Background: Kurukshetra sunset +
    drifting embers + slowly rotating dharma chakra; menu BGM starts on
    entry (placeholder-safe: silent without sound files).
    """
    name = STATE_MENU

    OPTIONS = ("STORY", "2P", "AI", "SETTINGS", "HOWTO", "QUIT")
    LABELS = {
        "STORY":    "\u2694  STORY MODE \u2014 the Mahabharat campaign",
        "2P":       "\U0001F465 2 PLAYER BATTLE \u2014 local versus",
        "AI":       "\U0001F916 VS AI \u2014 single player vs CPU",
        "SETTINGS": "\u2699  SETTINGS \u2014 volume \u00b7 controls \u00b7 AI level",
        "HOWTO":    "\U0001F4D6 HOW TO PLAY \u2014 controls & lore",
        "QUIT":     "\U0001F6AA QUIT",
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
        if key == "QUIT":
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
            g.two_player = False
            g.story_index = 0
            g.story_progress = 0
            g.change_state(STATE_STORY)
            return
        # both versus flavors land on character select afterwards
        g.game_mode = GAME_VS
        g.two_player = (key == "2P")
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
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self._activate()
        elif pygame.K_1 <= k <= pygame.K_6:
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

        # ---- six options in two columns of three ------------------------
        col_x = (SCREEN_WIDTH // 2 - 255, SCREEN_WIDTH // 2 + 255)
        row_y = (272, 322, 372)
        for i, key in enumerate(self.OPTIONS):
            sel = (i == self.sel)
            c, r = i % 2, i // 2
            font = FONT_MEDIUM if sel else FONT_SMALL
            col = GOLD if sel else SAFFRON
            prefix = "\u25BA  " if sel else "      "
            rect = draw_centered_text(target, prefix + self.LABELS[key],
                                      font, col, col_x[c], row_y[r],
                                      shadow=sel)
            if sel:
                pygame.draw.line(target, SAFFRON,
                                 (rect.x - 10, rect.bottom + 4),
                                 (rect.right + 10, rect.bottom + 4), 2)

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
