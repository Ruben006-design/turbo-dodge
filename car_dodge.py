"""
TURBO DODGE - a Car Dodge game (pygame)

Controls
  LEFT / RIGHT or A / D ... steer
  SPACE or SHIFT .......... nitro boost
  P or ESC ................ pause
  M ....................... mute / unmute

Optional: put background.png, car.png and obstacle.png next to this file
and they will be used. If they are missing, the game draws its own graphics.
"""
import math
import os
import random
import sys
from array import array

import pygame

# ----------------------------------------------------------------------------
# Setup
# ----------------------------------------------------------------------------
try:
    pygame.mixer.pre_init(22050, -16, 1, 512)
except pygame.error:
    pass
pygame.init()

WIDTH, HEIGHT = 500, 700
ROAD_L, ROAD_R = 70, 430
LANES = 4
LANE_W = (ROAD_R - ROAD_L) // LANES
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Turbo Dodge")
clock = pygame.time.Clock()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HS_FILE = os.path.join(BASE_DIR, "highscore.txt")

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GOLD = (255, 205, 40)
RED = (235, 60, 60)
BLUE = (70, 160, 255)
GREEN = (80, 220, 120)
PINK = (255, 95, 150)
PURPLE = (170, 110, 255)
ORANGE = (255, 150, 40)

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------
_fonts = {}


def get_font(size, bold=True):
    key = (size, bold)
    if key not in _fonts:
        _fonts[key] = pygame.font.SysFont("arial", size, bold=bold)
    return _fonts[key]


def draw_text(surf, text, size, color, x, y, anchor="center", shadow=True, alpha=255):
    font = get_font(size)
    img = font.render(str(text), True, color)
    rect = img.get_rect()
    setattr(rect, anchor, (x, y))
    if shadow:
        sh = font.render(str(text), True, (0, 0, 0))
        sh.set_alpha(int(alpha * 0.6))
        surf.blit(sh, rect.move(2, 2))
    if alpha < 255:
        img.set_alpha(alpha)
    surf.blit(img, rect)
    return rect


def panel(surf, rect, color=(0, 0, 0, 150), radius=14):
    s = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(s, color, s.get_rect(), border_radius=radius)
    surf.blit(s, rect.topleft)


def draw_heart(surf, cx, cy, size, color):
    r = size * 0.27
    pygame.draw.circle(surf, color, (cx - r, cy - r * 0.4), r)
    pygame.draw.circle(surf, color, (cx + r, cy - r * 0.4), r)
    pygame.draw.polygon(surf, color, [(cx - 2 * r + 1, cy - r * 0.1),
                                      (cx + 2 * r - 1, cy - r * 0.1),
                                      (cx, cy + size * 0.55)])


def load_image(name, size):
    try:
        img = pygame.image.load(os.path.join(BASE_DIR, name)).convert_alpha()
        return pygame.transform.smoothscale(img, size)
    except (pygame.error, FileNotFoundError):
        return None


def load_high():
    try:
        with open(HS_FILE) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return 0


def save_high(v):
    try:
        with open(HS_FILE, "w") as f:
            f.write(str(int(v)))
    except OSError:
        pass


# ----------------------------------------------------------------------------
# Sound (synthesised, no files needed)
# ----------------------------------------------------------------------------
def make_sound(f0, f1, dur, vol=0.35, noise=False, sr=22050):
    n = int(sr * dur)
    buf = array("h")
    phase = 0.0
    for i in range(n):
        p = i / n
        env = (1 - p) ** 1.5
        if noise:
            v = random.uniform(-1, 1)
        else:
            f = f0 + (f1 - f0) * p
            phase += 2 * math.pi * f / sr
            v = math.sin(phase)
        buf.append(int(v * env * vol * 32767))
    return pygame.mixer.Sound(buffer=buf.tobytes())


SOUNDS = {}
try:
    SOUNDS = {
        "coin": make_sound(900, 1500, 0.12),
        "crash": make_sound(0, 0, 0.45, vol=0.5, noise=True),
        "power": make_sound(400, 1000, 0.25),
        "level": make_sound(500, 900, 0.4),
        "over": make_sound(400, 80, 0.8, vol=0.45),
        "shield": make_sound(700, 200, 0.3),
    }
except Exception:
    SOUNDS = {}

muted = False


def play(name):
    if not muted and name in SOUNDS:
        SOUNDS[name].play()


# ----------------------------------------------------------------------------
# Procedural art
# ----------------------------------------------------------------------------
def make_car(body, roof, headlights=True):
    s = pygame.Surface((50, 90), pygame.SRCALPHA)
    for wx, wy in ((0, 14), (43, 14), (0, 58), (43, 58)):
        pygame.draw.rect(s, (20, 20, 20), (wx, wy, 7, 20), border_radius=3)
    pygame.draw.rect(s, body, (5, 2, 40, 86), border_radius=14)
    pygame.draw.rect(s, tuple(max(0, c - 40) for c in body), (5, 2, 40, 86), 2, border_radius=14)
    pygame.draw.rect(s, (150, 215, 255), (11, 22, 28, 18), border_radius=5)   # windshield
    pygame.draw.rect(s, roof, (11, 41, 28, 18), border_radius=4)               # roof
    pygame.draw.rect(s, (110, 170, 215), (11, 60, 28, 12), border_radius=4)    # rear window
    if headlights:
        pygame.draw.circle(s, (255, 245, 170), (13, 7), 4)
        pygame.draw.circle(s, (255, 245, 170), (37, 7), 4)
    pygame.draw.rect(s, (255, 255, 255), (23, 2, 4, 84))  # racing stripe
    s.set_alpha(None)
    return s


def make_cone():
    s = pygame.Surface((40, 44), pygame.SRCALPHA)
    pygame.draw.rect(s, (40, 40, 40), (2, 36, 36, 7), border_radius=2)
    pygame.draw.polygon(s, (255, 120, 20), [(20, 2), (32, 38), (8, 38)])
    pygame.draw.polygon(s, WHITE, [(16, 14), (24, 14), (26, 22), (14, 22)])
    return s


def make_rock():
    s = pygame.Surface((50, 44), pygame.SRCALPHA)
    pts = [(4, 38), (8, 18), (20, 5), (34, 8), (46, 22), (44, 38)]
    pygame.draw.polygon(s, (110, 110, 118), pts)
    pygame.draw.polygon(s, (75, 75, 82), pts, 3)
    pygame.draw.polygon(s, (145, 145, 152), [(14, 18), (22, 10), (30, 12), (22, 22)])
    return s


def make_coin(width_scale=1.0):
    s = pygame.Surface((30, 30), pygame.SRCALPHA)
    pygame.draw.circle(s, (200, 140, 10), (15, 15), 14)
    pygame.draw.circle(s, GOLD, (15, 15), 12)
    pygame.draw.circle(s, (255, 235, 140), (15, 15), 8, 2)
    pygame.draw.line(s, (200, 140, 10), (15, 9), (15, 21), 3)
    return s


def make_powerup(kind):
    s = pygame.Surface((40, 40), pygame.SRCALPHA)
    colors = {"shield": BLUE, "slow": PURPLE, "heart": PINK}
    col = colors[kind]
    pygame.draw.circle(s, (255, 255, 255), (20, 20), 19)
    pygame.draw.circle(s, col, (20, 20), 16)
    if kind == "shield":
        pygame.draw.polygon(s, WHITE, [(20, 8), (30, 12), (28, 24), (20, 32), (12, 24), (10, 12)])
    elif kind == "slow":
        pygame.draw.circle(s, WHITE, (20, 20), 10, 2)
        pygame.draw.line(s, WHITE, (20, 20), (20, 13), 2)
        pygame.draw.line(s, WHITE, (20, 20), (26, 22), 2)
    else:
        draw_heart(s, 20, 19, 22, WHITE)
    return s


# Assets built after display init
CAR_COLORS = [((220, 50, 50), (150, 30, 30)), ((60, 140, 230), (30, 80, 150)),
              ((240, 190, 40), (170, 130, 20)), ((90, 200, 110), (50, 130, 70)),
              ((170, 90, 220), (110, 50, 160)), ((240, 240, 245), (170, 170, 180))]

custom_car = load_image("car.png", (50, 80))
custom_obstacle = load_image("obstacle.png", (50, 50))
custom_bg = load_image("background.png", (WIDTH, HEIGHT))

PLAYER_IMG = custom_car or make_car((250, 215, 50), (190, 150, 20))
ENEMY_IMGS = [pygame.transform.flip(make_car(b, r, False), False, True) for b, r in CAR_COLORS]
CONE_IMG = make_cone()
ROCK_IMG = make_rock()
COIN_IMG = make_coin()
POWER_IMGS = {k: make_powerup(k) for k in ("shield", "slow", "heart")}


# ----------------------------------------------------------------------------
# Game objects
# ----------------------------------------------------------------------------
class Particle:
    def __init__(self, x, y, vx, vy, life, color, size):
        self.x, self.y, self.vx, self.vy = x, y, vx, vy
        self.life = self.max_life = life
        self.color, self.size = color, size

    def update(self, dt):
        f = dt * 60
        self.x += self.vx * f
        self.y += self.vy * f
        self.life -= dt

    def draw(self, surf):
        r = self.size * max(self.life, 0) / self.max_life
        if r >= 0.6:
            pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), max(1, int(r)))


class FloatText:
    def __init__(self, text, x, y, color):
        self.text, self.x, self.y, self.color = text, x, y, color
        self.life = 1.0

    def update(self, dt):
        self.life -= dt
        self.y -= 40 * dt

    def draw(self, surf):
        draw_text(surf, self.text, 24, self.color, self.x, self.y, alpha=int(255 * max(self.life, 0)))


class Thing:
    """Anything that scrolls down the road: obstacles, coins, power-ups."""

    def __init__(self, kind, img, cx, y, sub=None):
        self.kind = kind          # "obstacle", "coin", "power"
        self.sub = sub
        self.img = img
        self.x = cx - img.get_width() / 2
        self.y = y

    def rect(self):
        r = pygame.Rect(int(self.x), int(self.y), self.img.get_width(), self.img.get_height())
        if self.kind == "obstacle":
            return r.inflate(-14, -12)
        return r.inflate(-4, -4)


# ----------------------------------------------------------------------------
# Game
# ----------------------------------------------------------------------------
class Game:
    def __init__(self):
        self.canvas = pygame.Surface((WIDTH, HEIGHT))
        self.state = "menu"
        self.high = load_high()
        self.road_offset = 0.0
        self.time = 0.0
        self.decor = [[random.choice((20, 45)) if random.random() < 0.5 else random.choice((455, 480)),
                       random.uniform(0, HEIGHT), random.randint(12, 20)] for _ in range(14)]
        self.reset()

    # ----- state --------------------------------------------------------
    def reset(self):
        self.px = WIDTH / 2 - 25
        self.py = HEIGHT - 140
        self.vx = 0.0
        self.lives = 3
        self.score = 0.0
        self.coins = 0
        self.level = 1
        self.things, self.particles, self.texts = [], [], []
        self.spawn_t = 1.0
        self.coin_t = 3.0
        self.power_t = 12.0
        self.shield = 0.0
        self.slow = 0.0
        self.nitro = 100.0
        self.boost = False
        self.invinc = 0.0
        self.shake = 0.0
        self.banner = 0.0
        self.new_record = False
        self.last_lane = 0

    def road_speed(self):
        s = min(5 + (self.level - 1) * 0.9, 13)
        if self.slow > 0:
            s *= 0.55
        if self.boost:
            s *= 1.6
        return s

    def end_game(self):
        self.state = "over"
        play("over")
        if int(self.score) > self.high:
            self.high = int(self.score)
            self.new_record = True
            save_high(self.high)

    # ----- events -------------------------------------------------------
    def handle(self, event):
        global muted
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type != pygame.KEYDOWN:
            return
        k = event.key
        if k == pygame.K_m:
            muted = not muted
        if self.state == "menu":
            if k in (pygame.K_RETURN, pygame.K_SPACE):
                self.reset()
                self.state = "play"
            elif k == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()
        elif self.state == "play":
            if k in (pygame.K_p, pygame.K_ESCAPE):
                self.state = "pause"
        elif self.state == "pause":
            if k in (pygame.K_p, pygame.K_ESCAPE, pygame.K_RETURN):
                self.state = "play"
            elif k == pygame.K_q:
                self.state = "menu"
        elif self.state == "over":
            if k in (pygame.K_r, pygame.K_RETURN):
                self.reset()
                self.state = "play"
            elif k == pygame.K_ESCAPE:
                self.state = "menu"
            elif k == pygame.K_q:
                pygame.quit()
                sys.exit()

    # ----- spawning -----------------------------------------------------
    def lane_x(self, lane):
        return ROAD_L + LANE_W * lane + LANE_W / 2

    def spawn_obstacle(self):
        lanes = list(range(LANES))
        random.shuffle(lanes)
        count = 2 if (self.level >= 3 and random.random() < 0.3) else 1
        for lane in lanes[:count]:
            r = random.random()
            if custom_obstacle:
                img = custom_obstacle
            elif r < 0.5:
                img = random.choice(ENEMY_IMGS)
            elif r < 0.78:
                img = CONE_IMG
            else:
                img = ROCK_IMG
            jitter = random.randint(-10, 10)
            self.things.append(Thing("obstacle", img, self.lane_x(lane) + jitter, -100))
            self.last_lane = lane

    def spawn_coins(self):
        lane = random.randrange(LANES)
        for t in self.things:
            if t.kind == "obstacle" and t.y < 260 and abs(t.x + t.img.get_width() / 2 - self.lane_x(lane)) < LANE_W:
                return False
        for i in range(random.randint(4, 6)):
            self.things.append(Thing("coin", COIN_IMG, self.lane_x(lane), -40 - i * 48))
        return True

    def spawn_power(self):
        kind = random.choice(("shield", "slow", "heart"))
        if kind == "heart" and self.lives >= 5:
            kind = "shield"
        lane = random.randrange(LANES)
        self.things.append(Thing("power", POWER_IMGS[kind], self.lane_x(lane), -60, kind))

    # ----- effects ------------------------------------------------------
    def burst(self, x, y, colors, n=30, speed=6, size=7, life=0.7):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            sp = random.uniform(1, speed)
            self.particles.append(Particle(x, y, math.cos(a) * sp, math.sin(a) * sp,
                                           random.uniform(0.3, life), random.choice(colors),
                                           random.uniform(3, size)))

    # ----- update -------------------------------------------------------
    def update(self, dt, keys):
        self.time += dt
        f = dt * 60

        if self.state == "menu":
            self.road_offset += 3 * f
            self.scroll_decor(3, f)
            return
        if self.state == "pause":
            return

        speed = self.road_speed() if self.state == "play" else 2.0
        self.road_offset += speed * f
        self.scroll_decor(speed, f)
        self.shake *= 0.9 ** f

        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]
        for t in self.texts:
            t.update(dt)
        self.texts = [t for t in self.texts if t.life > 0]

        if self.state == "over":
            return

        # --- player movement
        left = keys[pygame.K_LEFT] or keys[pygame.K_a]
        right = keys[pygame.K_RIGHT] or keys[pygame.K_d]
        target = (right - left) * 7.5
        self.vx += (target - self.vx) * min(1.0, 0.18 * f)
        self.px += self.vx * f
        self.px = max(ROAD_L + 4, min(ROAD_R - 54, self.px))

        # --- nitro
        want = (keys[pygame.K_SPACE] or keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
        if want and self.nitro > 0:
            self.boost = True
            self.nitro = max(0, self.nitro - 35 * dt)
        else:
            self.boost = False
            self.nitro = min(100, self.nitro + 12 * dt)

        # --- exhaust
        cx = self.px + 25
        if self.boost:
            for _ in range(2):
                self.particles.append(Particle(cx + random.uniform(-10, 10), self.py + 88,
                                               random.uniform(-0.5, 0.5), random.uniform(3, 6), 0.35,
                                               random.choice((ORANGE, GOLD, (255, 90, 30))), 7))
        elif random.random() < 0.4:
            self.particles.append(Particle(cx + random.uniform(-8, 8), self.py + 90,
                                           random.uniform(-0.3, 0.3), random.uniform(1, 2), 0.4,
                                           (150, 150, 150), 4))

        # --- score / level / timers
        self.score += speed * dt * (1.6 if self.boost else 1.0) * 4
        new_level = 1 + int(self.score // 400)
        if new_level > self.level:
            self.level = new_level
            self.banner = 2.0
            play("level")
        self.banner = max(0, self.banner - dt)
        self.invinc = max(0, self.invinc - dt)
        self.shield = max(0, self.shield - dt)
        self.slow = max(0, self.slow - dt)

        # --- spawning (spacing scales with speed)
        gap = max(170, 300 - self.level * 14)
        self.spawn_t -= dt
        if self.spawn_t <= 0:
            self.spawn_obstacle()
            self.spawn_t = random.uniform(0.8, 1.2) * gap / (speed * 60)
        self.coin_t -= dt
        if self.coin_t <= 0:
            self.coin_t = random.uniform(4, 7) if self.spawn_coins() else 0.5
        self.power_t -= dt
        if self.power_t <= 0:
            self.spawn_power()
            self.power_t = random.uniform(14, 22)

        # --- move things + collisions
        player = pygame.Rect(int(self.px) + 8, int(self.py) + 6, 34, 78)
        for t in self.things:
            t.y += speed * f
        remaining = []
        for t in self.things:
            if t.y > HEIGHT + 100:
                continue
            hit = player.colliderect(t.rect())
            cx, cy = t.x + t.img.get_width() / 2, t.y + t.img.get_height() / 2
            if hit and t.kind == "coin":
                self.coins += 1
                self.score += 10
                play("coin")
                self.burst(cx, cy, (GOLD, WHITE), n=8, speed=3, size=4, life=0.4)
                self.texts.append(FloatText("+10", cx, cy, GOLD))
                continue
            if hit and t.kind == "power":
                play("power")
                self.burst(cx, cy, (WHITE, GREEN), n=16, speed=4, size=5)
                if t.sub == "shield":
                    self.shield = 8.0
                    self.texts.append(FloatText("SHIELD!", cx, cy, BLUE))
                elif t.sub == "slow":
                    self.slow = 6.0
                    self.texts.append(FloatText("SLOW-MO!", cx, cy, PURPLE))
                else:
                    self.lives = min(5, self.lives + 1)
                    self.texts.append(FloatText("+1 LIFE", cx, cy, PINK))
                continue
            if hit and t.kind == "obstacle":
                if self.shield > 0:
                    self.shield = 0
                    play("shield")
                    self.burst(cx, cy, (BLUE, WHITE), n=30, speed=7)
                    self.shake = 6
                    self.invinc = 0.8
                    continue
                if self.invinc <= 0:
                    self.lives -= 1
                    self.invinc = 1.6
                    self.shake = 16
                    play("crash")
                    self.burst(cx, cy, (ORANGE, RED, GOLD, (90, 90, 90)), n=45, speed=8, size=9, life=0.9)
                    self.texts.append(FloatText("-1", self.px + 25, self.py, RED))
                    if self.lives <= 0:
                        self.end_game()
                    continue
            remaining.append(t)
        self.things = remaining

    def scroll_decor(self, speed, f):
        for d in self.decor:
            d[1] += speed * f
            if d[1] > HEIGHT + 40:
                d[1] = -40
                d[0] = random.choice((20, 45, 455, 480))
                d[2] = random.randint(12, 20)

    # ----- drawing ------------------------------------------------------
    def draw_road(self, c):
        if custom_bg:
            off = int(self.road_offset) % HEIGHT
            c.blit(custom_bg, (0, off))
            c.blit(custom_bg, (0, off - HEIGHT))
            return
        c.fill((46, 128, 62))
        off = self.road_offset
        for y in range(-120, HEIGHT + 120, 120):
            yy = y + off % 120
            pygame.draw.rect(c, (52, 140, 68), (0, yy, ROAD_L, 60))
            pygame.draw.rect(c, (52, 140, 68), (ROAD_R, yy, WIDTH - ROAD_R, 60))
        # road + curbs
        pygame.draw.rect(c, (52, 52, 58), (ROAD_L, 0, ROAD_R - ROAD_L, HEIGHT))
        for y in range(-40, HEIGHT + 40, 40):
            yy = y + off % 40
            col = RED if (y // 40) % 2 == 0 else WHITE
            pygame.draw.rect(c, col, (ROAD_L - 8, yy, 8, 20))
            pygame.draw.rect(c, col, (ROAD_R, yy, 8, 20))
        pygame.draw.line(c, (235, 235, 235), (ROAD_L + 5, 0), (ROAD_L + 5, HEIGHT), 3)
        pygame.draw.line(c, (235, 235, 235), (ROAD_R - 5, 0), (ROAD_R - 5, HEIGHT), 3)
        for i in range(1, LANES):
            x = ROAD_L + i * LANE_W
            for y in range(-70, HEIGHT + 70, 70):
                pygame.draw.rect(c, (230, 230, 120), (x - 2, y + off % 70, 4, 38))
        # trees
        for x, y, r in self.decor:
            pygame.draw.circle(c, (0, 0, 0), (int(x) + 3, int(y) + 4), r)
            pygame.draw.circle(c, (28, 100, 45), (int(x), int(y)), r)
            pygame.draw.circle(c, (45, 135, 62), (int(x) - 3, int(y) - 3), r * 2 // 3)

    def draw_player(self, c):
        if self.invinc > 0 and int(self.time * 14) % 2 == 0:
            return
        img = pygame.transform.rotate(PLAYER_IMG, -self.vx * 1.6)
        rect = img.get_rect(center=(self.px + 25, self.py + 45))
        # shadow
        sh = pygame.Surface((54, 94), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 70), sh.get_rect())
        c.blit(sh, (self.px - 2, self.py + 6))
        c.blit(img, rect)
        if self.shield > 0:
            pulse = 4 * math.sin(self.time * 8)
            s = pygame.Surface((120, 140), pygame.SRCALPHA)
            alpha = 90 if self.shield > 2 or int(self.time * 10) % 2 else 30
            pygame.draw.ellipse(s, (*BLUE, alpha), (10 - pulse, 10 - pulse, 100 + 2 * pulse, 120 + 2 * pulse))
            pygame.draw.ellipse(s, (*WHITE, min(255, alpha + 80)), (10 - pulse, 10 - pulse, 100 + 2 * pulse, 120 + 2 * pulse), 3)
            c.blit(s, (self.px + 25 - 60, self.py + 45 - 70))

    def draw_things(self, c):
        for t in self.things:
            if t.kind == "obstacle":
                sh = pygame.Surface(t.img.get_size(), pygame.SRCALPHA)
                pygame.draw.ellipse(sh, (0, 0, 0, 60), sh.get_rect().inflate(0, -6))
                c.blit(sh, (t.x + 3, t.y + 6))
                c.blit(t.img, (t.x, t.y))
            elif t.kind == "coin":
                w = max(4, int(30 * abs(math.cos(self.time * 5 + t.y * 0.02))))
                img = pygame.transform.scale(t.img, (w, 30))
                c.blit(img, (t.x + 15 - w / 2, t.y))
            else:
                glow = 24 + 4 * math.sin(self.time * 6)
                g = pygame.Surface((80, 80), pygame.SRCALPHA)
                pygame.draw.circle(g, (255, 255, 255, 60), (40, 40), int(glow))
                c.blit(g, (t.x + 20 - 40, t.y + 20 - 40))
                c.blit(t.img, (t.x, t.y + 3 * math.sin(self.time * 5)))

    def draw_hud(self, c):
        panel(c, pygame.Rect(8, 8, WIDTH - 16, 58), (0, 0, 0, 150))
        draw_text(c, "SCORE", 14, (190, 190, 200), 22, 14, "topleft", shadow=False)
        draw_text(c, int(self.score), 30, WHITE, 22, 28, "topleft")
        draw_text(c, "BEST", 14, (190, 190, 200), 170, 14, "topleft", shadow=False)
        draw_text(c, max(self.high, int(self.score)), 22, GOLD, 170, 32, "topleft")
        draw_text(c, f"LVL {self.level}", 22, GREEN, 270, 37, "center")
        # coins
        pygame.draw.circle(c, GOLD, (318, 37), 8)
        draw_text(c, self.coins, 20, WHITE, 332, 37, "midleft")
        # hearts
        for i in range(5):
            col = PINK if i < self.lives else (70, 70, 80)
            draw_heart(c, 392 + i * 20 - 6, 35, 18, col)

        # nitro bar
        bar = pygame.Rect(16, HEIGHT - 34, 160, 16)
        panel(c, bar.inflate(8, 8), (0, 0, 0, 150), 10)
        fill = bar.copy()
        fill.width = int(bar.width * self.nitro / 100)
        col = ORANGE if self.nitro > 25 else RED
        if fill.width > 0:
            pygame.draw.rect(c, col, fill, border_radius=6)
        pygame.draw.rect(c, WHITE, bar, 2, border_radius=6)
        draw_text(c, "NITRO", 13, WHITE, bar.centerx, bar.centery, shadow=False)

        # speedometer
        draw_text(c, f"{int(self.road_speed() * 14)} km/h", 20, WHITE, WIDTH - 16, HEIGHT - 26, "midright")

        # active power-up pills
        y = 76
        for label, t, col in (("SHIELD", self.shield, BLUE), ("SLOW-MO", self.slow, PURPLE)):
            if t > 0:
                r = pygame.Rect(12, y, 120, 22)
                panel(c, r, (0, 0, 0, 150), 10)
                pygame.draw.rect(c, col, (r.x + 3, r.y + 3, int((r.w - 6) * min(1, t / 8)), r.h - 6), border_radius=8)
                draw_text(c, f"{label} {t:.1f}", 14, WHITE, r.centerx, r.centery, shadow=False)
                y += 28

        if self.banner > 0:
            a = int(255 * min(1, self.banner))
            draw_text(c, f"LEVEL {self.level}", 64, GOLD, WIDTH // 2, HEIGHT // 3, alpha=a)
            draw_text(c, "Speed up!", 26, WHITE, WIDTH // 2, HEIGHT // 3 + 50, alpha=a)

    def draw_menu(self, c):
        panel(c, pygame.Rect(0, 0, WIDTH, HEIGHT), (0, 0, 0, 120), 0)
        bob = math.sin(self.time * 2) * 6
        draw_text(c, "TURBO", 84, GOLD, WIDTH // 2, 130 + bob)
        draw_text(c, "DODGE", 84, WHITE, WIDTH // 2, 205 + bob)
        draw_text(c, "Dodge traffic. Grab coins. Survive.", 22, (220, 220, 230), WIDTH // 2, 262)
        c.blit(PLAYER_IMG, (WIDTH // 2 - 25 + math.sin(self.time * 1.5) * 90, 300))
        panel(c, pygame.Rect(80, 410, 340, 150), (0, 0, 0, 170))
        lines = [("<  >  /  A  D", "Steer"), ("SPACE / SHIFT", "Nitro boost"),
                 ("P / ESC", "Pause"), ("M", "Mute")]
        for i, (k, v) in enumerate(lines):
            draw_text(c, k, 20, GOLD, 100, 432 + i * 30, "midleft", shadow=False)
            draw_text(c, v, 20, WHITE, 400, 432 + i * 30, "midright", shadow=False)
        if int(self.time * 2) % 2 == 0:
            draw_text(c, "PRESS ENTER TO START", 30, GREEN, WIDTH // 2, 610)
        draw_text(c, f"Best score: {self.high}", 22, GOLD, WIDTH // 2, 660)

    def draw_pause(self, c):
        panel(c, pygame.Rect(0, 0, WIDTH, HEIGHT), (0, 0, 0, 150), 0)
        draw_text(c, "PAUSED", 70, WHITE, WIDTH // 2, HEIGHT // 2 - 40)
        draw_text(c, "P / ESC to resume   -   Q for menu", 22, (210, 210, 220), WIDTH // 2, HEIGHT // 2 + 20)

    def draw_over(self, c):
        panel(c, pygame.Rect(0, 0, WIDTH, HEIGHT), (0, 0, 0, 160), 0)
        box = pygame.Rect(60, 190, WIDTH - 120, 330)
        panel(c, box, (15, 15, 25, 230), 20)
        pygame.draw.rect(c, RED, box, 3, border_radius=20)
        draw_text(c, "GAME OVER", 54, RED, WIDTH // 2, 240)
        draw_text(c, f"Score  {int(self.score)}", 38, WHITE, WIDTH // 2, 310)
        draw_text(c, f"Coins {self.coins}    Level {self.level}", 24, GOLD, WIDTH // 2, 355)
        if self.new_record:
            draw_text(c, "NEW HIGH SCORE!", 30, GREEN if int(self.time * 3) % 2 else GOLD, WIDTH // 2, 400)
        else:
            draw_text(c, f"Best  {self.high}", 26, (200, 200, 215), WIDTH // 2, 400)
        draw_text(c, "R  Restart", 24, WHITE, WIDTH // 2, 450)
        draw_text(c, "ESC  Menu      Q  Quit", 20, (190, 190, 205), WIDTH // 2, 485)

    def draw(self):
        c = self.canvas
        self.draw_road(c)
        if self.state == "menu":
            self.draw_menu(c)
        else:
            self.draw_things(c)
            if self.state != "over":
                self.draw_player(c)
            for p in self.particles:
                p.draw(c)
            for t in self.texts:
                t.draw(c)
            self.draw_hud(c)
            if self.state == "pause":
                self.draw_pause(c)
            elif self.state == "over":
                self.draw_over(c)
        if muted:
            draw_text(c, "MUTED", 14, (200, 200, 200), WIDTH - 12, 74, "topright", shadow=False)

        screen.fill(BLACK)
        s = int(self.shake)
        off = (random.randint(-s, s), random.randint(-s, s)) if s > 0 else (0, 0)
        screen.blit(c, off)
        pygame.display.flip()


def main():
    game = Game()
    while True:
        dt = min(clock.tick(FPS) / 1000, 0.05)
        for event in pygame.event.get():
            game.handle(event)
        game.update(dt, pygame.key.get_pressed())
        game.draw()


if __name__ == "__main__":
    main()
