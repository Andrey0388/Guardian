import pygame
import os
import sys
from PIL import Image, ImageSequence
import random
from math import sqrt

pygame.mixer.pre_init(44100, -16, 2, 2048)  # setup mixer to avoid sound lag
pygame.init()
pygame.display.set_caption('Guardian')
size = width, height = 1200, 800
screen = pygame.display.set_mode(size)
all_sprites = pygame.sprite.Group()
screen_rect = (0, 0, width, height)
FAST = 7
FAST_BOOM = 14
FAST_MOB = 2
JUMP = 20
FLOOR_GRAVITY = 8
GRAVITY = 0.3
PLATFORM_GRAVITY = 2
SHOTS_PER_SECOND = 2  # 65 - 70 максимум при скорости FAST_BOOM 14
MOBS_PER_SECOND = 1
X_MAG_POS = width // 2 + 100
Y_MAG_POS = height // 2 + 100
RESPAWNS = [(50, height - 150), (width - 50, height - 150), (100, 200), (width // 2, 5)]
POISONS = [(5, "JUMP"), (-5, "JUMP"), (0, "BOOMS")]
DEATHS = ["sounds/death1.mp3", "sounds/death2.mp3", "sounds/death3.mp3", "sounds/death4.mp3"]
background_fps = 0
FLAG = False
running = False

horizontal_borders = pygame.sprite.Group()
vertical_borders = pygame.sprite.Group()
platforms = pygame.sprite.Group()
floor_group = pygame.sprite.Group()
mag_group = pygame.sprite.Group()
shots = pygame.sprite.Group()
mobs = pygame.sprite.Group()
golds = pygame.sprite.Group()
gold_coins = []
text_effects = []
text_waves = []
objects = []

fps = 60


def terminate():
    pygame.quit()
    sys.exit()


def start_screen():
    intro_text = ["Guardian", "",
                  "Правила игры",
                  "Ваша задача не подпустить врагов к вашему золоту,",
                  "У вас будет 20 монет (в левом верхнем углу)",
                  "Гномы будут их красть (по 1 монете)",
                  "Каждую пятую волну приходить босс, который медленнее остальных,",
                  "но имеет большой запас здоровья и крадёт 5 монет",
                  "зелья появляются каждые 20 секунд и могут принести баф или дебаф",
                  "enter - стрелять,",
                  "space - прыжок,",
                  "a, d - движение"]

    fon = pygame.transform.scale(load_image('fon.png'), (width, height))
    screen.blit(fon, (0, 0))
    font = pygame.font.SysFont('gabriola', 50)
    text_coord = 50
    Button(width - 450, 50, 400, 100, 'НАЧАТЬ ИГРУ', new_game)
    for line in intro_text:
        string_rendered = font.render(line, 1, pygame.Color('yellow'))
        intro_rect = string_rendered.get_rect()
        text_coord += 10
        intro_rect.top = text_coord
        intro_rect.x = 10
        text_coord += intro_rect.height
        screen.blit(string_rendered, intro_rect)
    while True:
        for new_event in pygame.event.get():
            if new_event.type == pygame.QUIT:
                terminate()

        for new_object in objects:
            new_object.process()
            if running:
                return  # начинаем игру

        pygame.display.flip()
        clock.tick(fps)


def new_game():
    global running
    running = True


def pilImageToSurface(pilImage):
    mode, size_image, data = pilImage.mode, pilImage.size, pilImage.tobytes()
    return pygame.image.fromstring(data, size_image, mode).convert_alpha()


def loadGIF(filename):
    pilImage = Image.open(filename)
    frames = []
    if pilImage.format == 'GIF' and pilImage.is_animated:
        for frame in ImageSequence.Iterator(pilImage):
            pygameImage = pilImageToSurface(frame.convert('RGBA'))
            frames.append(pygameImage)
    else:
        frames.append(pilImageToSurface(pilImage))
    return frames


def load_image(name, color_key=None):
    fullname = os.path.join('data', name)
    if not os.path.isfile(fullname):
        print(f"Файл с изображением '{fullname}' не найден")
        sys.exit()
    image = pygame.image.load(fullname)
    if color_key is not None:
        image = image.convert()
        if color_key == -1:
            color_key = image.get_at((0, 0))
        image.set_colorkey(color_key)
    else:
        image = image.convert_alpha()
    return image


class AnimatedSprite(pygame.sprite.Sprite):
    def __init__(self, sheet, columns, rows, x, y, coff):
        super().__init__(all_sprites)
        self.frames = []
        self.cut_sheet(sheet, columns, rows)
        self.cur_frame = 0
        self.image = self.frames[self.cur_frame]
        self.rect = self.rect.move(x, y)
        self.coff = coff
        self.fps = 0

    def cut_sheet(self, sheet, columns, rows):
        self.rect = pygame.Rect(0, 0, sheet.get_width() // columns,
                                sheet.get_height() // rows)
        for j in range(rows):
            for i in range(columns):
                frame_location = (self.rect.w * i, self.rect.h * j)
                self.frames.append(sheet.subsurface(pygame.Rect(
                    frame_location, self.rect.size)))

    def update(self):
        if self.fps % 2 == 0:
            if self.coff:
                self.cur_frame = (self.cur_frame + 1) % len(self.frames)
                self.image = self.frames[self.cur_frame]
            else:
                self.cur_frame += 1
                if self.cur_frame < len(self.frames):
                    self.image = self.frames[self.cur_frame]
                else:
                    self.kill()
        self.fps += 1


class Border(pygame.sprite.Sprite):
    # строго вертикальный или строго горизонтальный отрезок
    def __init__(self, x1, y1, x2, y2, f):
        super().__init__(all_sprites)
        if x1 == x2:  # вертикальная стенка
            self.add(vertical_borders)
            self.image = pygame.Surface([1, y2 - y1], pygame.SRCALPHA)
            self.rect = pygame.Rect(x1, y1, 1, y2 - y1)
            self.image.fill((0, 0, 0, f))
        else:  # горизонтальная стенка
            self.add(horizontal_borders)
            self.image = pygame.Surface([x2 - x1, 1], pygame.SRCALPHA)
            self.rect = pygame.Rect(x1, y1, x2 - x1, 1)
            self.image.fill((0, 0, 0, f))


class Fireball(pygame.sprite.Sprite):
    image = load_image("fireball.png")

    def __init__(self, pos1, move_x):
        super().__init__(all_sprites, shots)
        self.image = Fireball.image
        self.rect = self.image.get_rect()
        self.rect.x = pos1[0] + 30
        self.rect.y = pos1[1] + 40
        self.move_x = move_x
        self.move_y = 0
        # вычисляем маску для эффективного сравнения
        self.mask = pygame.mask.from_surface(self.image)
        global boom_sound, booms
        boom_sound.play(0)
        booms += 1

    def update(self):
        self.rect = self.rect.move(self.move_x, self.move_y)
        if self.rect.x < 0 or self.rect.x > width - 60:
            self.kill()
            AnimatedSprite(load_image("boom.png"), 4, 4, self.rect.x - 25, self.rect.y - 25, 0)

    def death(self):
        self.kill()


class Floor(pygame.sprite.Sprite):
    def __init__(self, x1, y1, x2, y2, f):
        super().__init__(all_sprites, floor_group)
        self.image = pygame.Surface([x2 - x1, 1], pygame.SRCALPHA)
        self.rect = pygame.Rect(x1, y1, x2 - x1, 1)
        self.image.fill((0, 0, 0, f))


class Mag(pygame.sprite.Sprite):
    image = load_image("mag.png")

    def __init__(self, pos):
        super().__init__(all_sprites, mag_group)
        self.image = Mag.image
        self.rect = self.image.get_rect()
        self.rect.x = pos[0]
        self.rect.y = pos[1]
        # вычисляем маску для эффективного сравнения
        self.mask = pygame.mask.from_surface(self.image)
        self.move_x = 0
        self.move_y = 0
        self.v = True
        self.jump = 0
        self.kol_jump = 0
        self.floor = Floor(X_MAG_POS, Y_MAG_POS + 109, X_MAG_POS + 70, Y_MAG_POS + 109, 0)

    def update(self):
        if self.move_x > 0 and self.v:
            self.image = pygame.transform.flip(self.image, True, False)
            self.mask = pygame.mask.from_surface(self.image)
            self.floor.rect = self.floor.rect.move(5, 0)
            self.v = False
        if self.move_x < 0 and not self.v:
            self.image = pygame.transform.flip(self.image, True, False)
            self.mask = pygame.mask.from_surface(self.image)
            self.floor.rect = self.floor.rect.move(-5, 0)
            self.v = True

        self.rect = self.rect.move(self.move_x, self.move_y)
        self.floor.rect = self.floor.rect.move(self.move_x, self.move_y)

        if (pygame.sprite.spritecollideany(self, horizontal_borders)) \
                or (pygame.sprite.spritecollideany(self.floor, platforms) and self.move_y > 0):
            while (pygame.sprite.spritecollideany(self, horizontal_borders)) \
                    or (pygame.sprite.spritecollideany(self.floor, platforms)):
                self.rect = self.rect.move(0, -1)
                self.floor.rect = self.floor.rect.move(0, -1)
            self.move_y = 0
            self.kol_jump = 0
        else:
            if self.move_y < 30:
                self.move_y += 1
        while pygame.sprite.spritecollideany(self, vertical_borders):
            if self.move_x:
                self.rect = self.rect.move(-self.move_x // abs(self.move_x), 0)
                self.floor.rect = self.floor.rect.move(-self.move_x // abs(self.move_x), 0)
            else:
                self.rect = self.rect.move(1, 0)
                self.floor.rect = self.floor.rect.move(1, 0)

    def move(self, x, y):
        self.move_x += x * FAST
        self.move_y += y * FAST

    def boom(self):
        Fireball((self.rect.x, self.rect.y), -(int(self.v) * 2 - 1) * FAST_BOOM)

    def jumper(self):
        self.kol_jump += 1
        self.move_y = -JUMP

    def return_kol_jump(self):
        return self.kol_jump


class Platform(pygame.sprite.Sprite):
    image = load_image("platform.png")

    def __init__(self, x, y):
        super().__init__(all_sprites)
        self.image = Platform.image
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        # вычисляем маску для эффективного сравнения
        self.mask = pygame.mask.from_surface(self.image)
        self.add(platforms)


class Mob(pygame.sprite.Sprite):
    image = load_image("robber.png")
    image1 = load_image("robber1.png")

    def __init__(self):
        super().__init__(all_sprites, mobs)
        self.kol_jump = 0
        self.image = Mob.image
        self.image = pygame.transform.scale(self.image, (50, 50))
        self.rect = self.image.get_rect()
        pos = RESPAWNS[random.randint(0, len(RESPAWNS) - 1)]
        self.rect.x = pos[0]
        self.rect.y = pos[1]
        # вычисляем маску для эффективного сравнения
        self.mask = pygame.mask.from_surface(self.image)
        self.platform = False
        self.move_x = 0
        self.move_y = 1
        self.v = True
        self.rx = random.randint(0, 1) * 2 - 1
        self.stor = 1

        self.run = False

    def update(self):
        if self.move_x > 0 and self.v and not self.run:
            self.image = pygame.transform.flip(self.image, True, False)
            self.mask = pygame.mask.from_surface(self.image)
            self.v = False
        if self.move_x < 0 and not self.v and not self.run:
            self.image = pygame.transform.flip(self.image, True, False)
            self.mask = pygame.mask.from_surface(self.image)
            self.v = True

        if self.run:
            self.move_x = 5 * self.stor
        self.rect = self.rect.move(self.move_x, self.move_y)

        if (pygame.sprite.spritecollideany(self, horizontal_borders)) \
                or (pygame.sprite.spritecollideany(self, platforms) and self.move_y > 0):
            if pygame.sprite.spritecollideany(self, horizontal_borders):
                if gold.rect.x - self.rect.x:
                    self.rx = (gold.rect.x - self.rect.x) // abs(gold.rect.x - self.rect.x)
            else:
                if not self.platform:
                    self.rx = random.randint(0, 1) * 2 - 1
                    self.platform = True

            while (pygame.sprite.spritecollideany(self, horizontal_borders)) \
                    or (pygame.sprite.spritecollideany(self, platforms)):
                self.rect = self.rect.move(0, -1)

            self.move_y = 1
            self.kol_jump = 0
        else:
            self.move_y += 1
            self.platform = False

        while not self.run and pygame.sprite.spritecollideany(self, vertical_borders) and self.move_x != 0:
            self.rect = self.rect.move(-self.move_x // abs(self.move_x), 0)
        if not self.run:
            self.move_x = self.rx * FAST_MOB

        if self.rect.x < -50 or self.rect.x > width + 50:
            self.kill()

    def running(self):
        x = self.rect.x
        y = self.rect.y
        self.image = Mob.image1
        self.rect = self.image.get_rect()
        # вычисляем маску для эффективного сравнения
        self.mask = pygame.mask.from_surface(self.image)
        self.rect.x = x - 29
        self.rect.y = y - 15
        mobs.remove(self)
        self.run = True
        if self.rect.x != mag.rect.x:
            self.stor = (self.rect.x - mag.rect.x) // abs(self.rect.x - mag.rect.x)
            if self.stor > 0:
                self.image = pygame.transform.flip(self.image, True, False)
                self.mask = pygame.mask.from_surface(self.image)
        else:
            self.stor = self.move_x // abs(self.move_x)
        self.move_x = self.stor * 5

    def death(self):
        self.kill()
        create_particles((self.rect.x, self.rect.y))
        AnimatedSprite(load_image("boom.png"), 4, 4, self.rect.x - 25, self.rect.y - 25, 0)
        i = random.randint(0, 3)
        sound = pygame.mixer.Sound(DEATHS[i])
        sound.play()


class Boss(pygame.sprite.Sprite):
    image = load_image("boss.png")
    image1 = load_image("boss1.png")

    def __init__(self, num_wave):
        super().__init__(all_sprites, mobs)
        self.image = Boss.image
        self.image = pygame.transform.scale(self.image, (80, 117))
        self.rect = self.image.get_rect()
        pos = RESPAWNS[random.randint(0, len(RESPAWNS) - 1)]
        self.rect.x = pos[0] - 50
        self.rect.y = pos[1] - 96
        # вычисляем маску для эффективного сравнения
        self.mask = pygame.mask.from_surface(self.image)
        self.platform = False
        self.move_x = 0
        self.move_y = 1
        self.v = True
        self.rx = random.randint(0, 1) * 2 - 1
        self.stor = 1
        self.process_bar = ProgressBar((self.rect.x, self.rect.y - 15, 80, 10))
        self.per = num_wave
        self.run = False

    def update(self):
        if self.move_x > 0 and self.v and not self.run:
            self.image = pygame.transform.flip(self.image, True, False)
            self.mask = pygame.mask.from_surface(self.image)
            self.v = False
        if self.move_x < 0 and not self.v and not self.run:
            self.image = pygame.transform.flip(self.image, True, False)
            self.mask = pygame.mask.from_surface(self.image)
            self.v = True

        if self.run:
            self.move_x = 3 * self.stor
        self.rect = self.rect.move(self.move_x, self.move_y)
        self.process_bar.move(self.move_x, self.move_y)

        if (pygame.sprite.spritecollideany(self, horizontal_borders)) \
                or (pygame.sprite.spritecollideany(self, platforms) and self.move_y > 0):
            if pygame.sprite.spritecollideany(self, horizontal_borders):
                if gold.rect.x - self.rect.x:
                    self.rx = (gold.rect.x - self.rect.x) // abs(gold.rect.x - self.rect.x)
            else:
                if not self.platform:
                    self.rx = random.randint(0, 1) * 2 - 1
                    self.platform = True

            while (pygame.sprite.spritecollideany(self, horizontal_borders)) \
                    or (pygame.sprite.spritecollideany(self, platforms)):
                self.rect = self.rect.move(0, -1)
                self.process_bar.move(0, -1)

            self.move_y = 1
        else:
            self.move_y += 1
            self.platform = False

        while not self.run and pygame.sprite.spritecollideany(self, vertical_borders) and self.move_x != 0:
            self.rect = self.rect.move(-self.move_x // abs(self.move_x), 0)
            self.process_bar.move(-self.move_x // abs(self.move_x), 0)
        if not self.run:
            self.move_x = self.rx * FAST_MOB // 2

        if self.rect.x < -100 or self.rect.x > width + 100:
            self.kill()
        else:
            self.process_bar.update(screen, 0)

    def running(self):
        x = self.rect.x
        y = self.rect.y
        self.image = Boss.image1
        self.image = pygame.transform.scale(self.image, (108, 140))
        self.rect = self.image.get_rect()
        # вычисляем маску для эффективного сравнения
        self.mask = pygame.mask.from_surface(self.image)
        self.rect.x = x - 14
        self.rect.y = y - 23
        mobs.remove(self)
        self.run = True
        if self.rect.x != mag.rect.x:
            self.stor = (self.rect.x - mag.rect.x) // abs(self.rect.x - mag.rect.x)
            if self.stor > 0:
                self.image = pygame.transform.flip(self.image, True, False)
                self.mask = pygame.mask.from_surface(self.image)
        else:
            self.stor = self.move_x // abs(self.move_x)
        self.move_x = self.stor * 3
        self.process_bar.move(0, -23)

    def death(self):
        self.process_bar.update(screen, 100 / self.per)
        if self.process_bar.width_progress_bar == 0:
            self.kill()
            create_particles((self.rect.x, self.rect.y))
            for _ in range(10):
                AnimatedSprite(load_image("boom.png"), 4, 4,
                               random.randint(self.rect.x - 40, self.rect.x + 40),
                               random.randint(self.rect.y - 57, self.rect.y + 57), 0)
            global boss
            boss = False
            i = random.randint(0, 3)
            sound = pygame.mixer.Sound(DEATHS[i])
            sound.play()


class ProgressBar:
    def __init__(self, rectangle):
        self.rect = pygame.Rect(rectangle)
        self.width_progress_bar = self.rect.width
        self.complete = False
        self.percent = 100

    def update(self, scr, per):
        if not self.complete:
            self.percent -= per
        self.width_progress_bar = self.percent * self.rect.width / 100
        if self.width_progress_bar <= 0:
            self.width_progress_bar = 0
            self.complete = True
        else:
            self.complete = False
        pygame.draw.rect(scr, (0, 0, 0),
                         (self.rect.left, self.rect.top, self.rect.width - self.width_progress_bar, self.rect.height))
        pygame.draw.rect(scr, (255, 255, 255),
                         (self.rect.left, self.rect.top, self.rect.width, self.rect.height))
        pygame.draw.rect(scr, (0, 255, 0),
                         (self.rect.left, self.rect.top, self.width_progress_bar, self.rect.height))

    def move(self, x, y):
        self.rect.left += x
        self.rect.top += y


class Potion(pygame.sprite.Sprite):
    image = load_image("potion.png")

    def __init__(self):
        super().__init__(all_sprites)
        self.image = Potion.image
        self.rect = self.image.get_rect()
        self.rect.x = random.randint(100, width - 100)
        self.rect.y = random.randint(100, height - 100)
        # вычисляем маску для эффективного сравнения
        self.mask = pygame.mask.from_surface(self.image)
        self.cnt = 0

    def update(self):
        self.cnt += 1
        if pygame.sprite.spritecollideany(self, mag_group):
            self.x = random.randint(0, len(POISONS) - 1)
            if POISONS[self.x][1] == "JUMP":
                global JUMP
                JUMP += POISONS[self.x][0]
                self.death()
            if POISONS[self.x][1] == "BOOMS":
                global FLAG
                FLAG = True
                self.death()
        if self.cnt > 200:
            self.death()

    def death(self):
        self.kill()
        if self.cnt <= 200:
            global potion_sound
            potion_sound.play()
            create_particles((self.rect.x, self.rect.y))
            Effect(POISONS[self.x][0], POISONS[self.x][1])
            Effect_text(POISONS[self.x][1])


class Effect(pygame.sprite.Sprite):
    image = load_image("effect.png")

    def __init__(self, effect, name):
        super().__init__(all_sprites)
        self.image = pygame.transform.scale(Effect.image, (width, height))
        pygame.Surface.set_alpha(self.image, 120)
        self.rect = self.image.get_rect()
        self.rect.x = 0
        self.rect.y = 0
        # вычисляем маску для эффективного сравнения
        self.mask = pygame.mask.from_surface(self.image)
        self.effect = effect
        self.name = name
        self.alpha = 120

    def update(self):
        if self.alpha <= 0:
            if self.name == "JUMP":
                global JUMP
                JUMP -= self.effect
                self.kill()
                text_effects.clear()
            if self.name == "BOOMS":
                global FLAG
                FLAG = False
                self.kill()
                text_effects.clear()
        self.alpha -= 0.2
        pygame.Surface.set_alpha(self.image, self.alpha)


class Particle(pygame.sprite.Sprite):
    # сгенерируем частицы разного размера
    fire = [load_image("star.png")]
    for scale in (5, 10, 20):
        fire.append(pygame.transform.scale(fire[0], (scale, scale)))

    def __init__(self, pos, dx, dy):
        super().__init__(all_sprites)
        self.image = random.choice(self.fire)
        self.rect = self.image.get_rect()

        # у каждой частицы своя скорость — это вектор
        self.velocity = [dx, dy]
        # и свои координаты
        self.rect.x, self.rect.y = pos

        # гравитация будет одинаковой (значение константы)
        self.gravity = GRAVITY

    def update(self):
        # применяем гравитационный эффект:
        # движение с ускорением под действием гравитации
        self.velocity[1] += self.gravity
        # перемещаем частицу
        self.rect.x += self.velocity[0]
        self.rect.y += self.velocity[1]
        # убиваем, если частица ушла за экран
        if not self.rect.colliderect(screen_rect):
            self.kill()


def create_particles(position):
    # количество создаваемых частиц
    particle_count = 20
    # возможные скорости
    numbers = range(-5, 6)
    for _ in range(particle_count):
        Particle(position, random.choice(numbers), random.choice(numbers))


class Effect_text:
    def __init__(self, text):
        font = pygame.font.SysFont('gabriola', 50)
        self.text = font.render(text, True, (255, 0, 0))
        self.textRect = self.text.get_rect()
        self.textRect.topleft = (width // 2 + 300, 10)
        self.alpha = 255
        pygame.Surface.set_alpha(self.text, 0)
        text_effects.append(self)

    def update(self, scr):
        self.alpha -= 0.425
        pygame.Surface.set_alpha(self.text, self.alpha)
        scr.blit(self.text, self.textRect)


class Wave_text:
    def __init__(self, number_wave):
        text = f'Wave {number_wave}'
        if number_wave % 5 == 0:
            text += " boss"
        font = pygame.font.SysFont('gabriola', 100)
        self.text = font.render(text, True, (255, 0, 0))
        self.textRect = self.text.get_rect()
        self.textRect.center = (width // 2, height // 2)
        self.alpha = 0
        pygame.Surface.set_alpha(self.text, 0)
        text_waves.append(self)
        self.alpha_plus = 2

    def update(self, screen):
        self.alpha += self.alpha_plus
        if self.alpha > 255:
            self.alpha -= self.alpha_plus
            self.alpha_plus *= -1
        if self.alpha < 0:
            text_waves.remove(self)
        pygame.Surface.set_alpha(self.text, self.alpha)
        screen.blit(self.text, self.textRect)


class Game_clock:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.i = 0

    def update(self, screen, seconds):
        mins = str(int(seconds // 60))
        if len(mins) < 2:
            mins = "0" + mins
        secs = str(int(seconds % 60 // 1))
        if len(secs) < 2:
            secs = "0" + secs
        font = pygame.font.SysFont('gabriola', 50)
        t = f'{mins}:{secs}'
        text = font.render(t, True, (255, 0, 0))
        textRect = text.get_rect()
        textRect.center = (self.x, self.y)
        screen.blit(text, textRect)


class Kills:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def update(self, screen, kills):
        font = pygame.font.SysFont("gabriola", 50)
        t = "Kills: " + str(kills)
        text = font.render(t, True, (255, 0, 0))
        textRect = text.get_rect()
        textRect.topright = (self.x, self.y)
        screen.blit(text, textRect)


class Coin(pygame.sprite.Sprite):
    image = load_image("coin.png")

    def __init__(self, x, y, coin_size):
        super().__init__(all_sprites)
        self.image = Coin.image
        self.image = pygame.transform.scale(self.image, (coin_size, coin_size))
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        # вычисляем маску для эффективного сравнения
        self.mask = pygame.mask.from_surface(self.image)
        gold_coins.append(self)

    def death(self):
        self.kill()
        gold_coins.remove(self)


def create_coins(columns, row):
    coin_size = (57 // columns) - 3
    x = 10
    y = 10
    for i in range(columns):
        for j in range(row):
            x_pos = j * (coin_size + 3) + x
            y_pos = i * (coin_size + 3) + y
            Coin(x_pos, y_pos, coin_size)


class Button:
    def __init__(self, x, y, width, height, buttonText, onclickFunction):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.onclickFunction = onclickFunction
        self.alreadyPressed = False

        self.fillColors = {
            'normal': '#ffffff',
            'hover': '#666666',
            'pressed': '#333333',
        }

        self.buttonSurface = pygame.Surface((self.width, self.height))
        self.buttonRect = pygame.Rect(self.x, self.y, self.width, self.height)
        font = pygame.font.SysFont('Arial', 40)
        self.buttonSurf = font.render(buttonText, True, (20, 20, 20))

        objects.append(self)

    def process(self):
        mousePos = pygame.mouse.get_pos()
        self.buttonSurface.fill(self.fillColors['normal'])
        if self.buttonRect.collidepoint(mousePos):
            self.buttonSurface.fill(self.fillColors['hover'])
            if pygame.mouse.get_pressed(num_buttons=3)[0]:
                if not self.alreadyPressed:
                    self.buttonSurface.fill(self.fillColors['pressed'])
                    self.onclickFunction()
                    self.alreadyPressed = True
            else:
                self.alreadyPressed = False

        self.buttonSurface.blit(self.buttonSurf, [
            self.buttonRect.width / 2 - self.buttonSurf.get_rect().width / 2,
            self.buttonRect.height / 2 - self.buttonSurf.get_rect().height / 2
        ])
        screen.blit(self.buttonSurface, self.buttonRect)


def show_go_screen():
    global background_fps, currentFrame, gifFrameList, kol_mobs_wave, d_kol_mobs, boss
    global number_wave, kol_mobs, poisons, MOBS_PER_SECOND, kol_bombs, seconds, booms
    Atime = seconds
    Akills = d_kol_mobs
    Awave = number_wave
    Abooms = booms
    f = True
    background = pygame.transform.scale(load_image('gm.png'), (width, height))
    width_gameover = -width - 5
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                with open("sessions.txt", "a") as text_file:
                    acc = 0
                    if Abooms:
                        acc = int(Akills / Abooms * 100)
                    text_file.write(
                        f'\n{int(Atime)} seconds, {Akills} kills, {Awave} wave, {Abooms} shots, {acc}% accuracy')
                waiting = False
                terminate()
        # main
        if f:
            seconds = (pygame.time.get_ticks() - start_ticks) / 1000
            for event in pygame.event.get():
                # mag
                if event.type == pygame.KEYDOWN and (event.key == 97):
                    mag.move(-1, 0)
                if event.type == pygame.KEYUP and (event.key == 97):
                    mag.move(1, 0)
                if event.type == pygame.KEYDOWN and (event.key == 100):
                    mag.move(1, 0)
                if event.type == pygame.KEYUP and (event.key == 100):
                    mag.move(-1, 0)
                if event.type == pygame.KEYDOWN and (event.key == 32) and mag.return_kol_jump() <= 1:
                    mag.jumper()
                if event.type == pygame.KEYDOWN and (event.key == 13):
                    mag.boom()

            mobs_golds = pygame.sprite.groupcollide(mobs, golds, False, False)
            for mob in mobs_golds:
                mob.running()
                rob_sound.play()

            hits1 = pygame.sprite.groupcollide(shots, mobs, False, False)
            hits2 = pygame.sprite.groupcollide(mobs, shots, False, False)
            for hit in hits1:
                hit.death()
            for hit in hits2:
                hit.death()
                d_kol_mobs += 1

            if kol_mobs_wave >= number_wave * 10 and not mobs:
                MOBS_PER_SECOND = sqrt(number_wave)
                number_wave += 1
                Wave_text(number_wave)
                kol_mobs_wave = 0

            screen.fill((0, 0, 0))
            if FLAG and (seconds // 0.1 / 10) > kol_bombs:
                mag.boom()
                kol_bombs += 0.1
            else:
                kol_bombs = seconds // 0.1 / 10

            if seconds > kol_mobs:
                if kol_mobs_wave < number_wave * 10 and not text_waves:
                    if number_wave % 5 == 0 and kol_mobs_wave == (number_wave * 10 // 3 * 2):
                        boss = True
                        last_boss = Boss(number_wave * 3)
                    else:
                        Mob()
                    kol_mobs_wave += 1
                kol_mobs += 1 / MOBS_PER_SECOND

            if background_fps % 300 == 0:
                currentFrame = (currentFrame + 1) % len(gifFrameList)
                background_fps = 0

            if seconds > 1 and int(seconds) // 20 > poisons:
                Potion()
                poisons += 1

            rect = gifFrameList[currentFrame].get_rect(center=(width // 2, height // 2))
            screen.blit(gifFrameList[currentFrame], rect)

            kills.update(screen, d_kol_mobs)
            clock.tick(fps)
            background_fps += fps
            all_sprites.draw(screen)
            all_sprites.update()

            for i in text_effects:
                i.update(screen)
            for i in text_waves:
                i.update(screen)

            width_gameover += 5
            screen.blit(background, (width_gameover, 0))
            Border(width_gameover + width, -1000, width_gameover + width, height, 0)
            if width_gameover >= 0:
                f = False

            pygame.display.flip()
        else:
            font = pygame.font.SysFont('gabriola', 100)

            t = "Kills: " + str(Akills)
            text = font.render(t, True, (255, 0, 0))
            textRect = text.get_rect()
            textRect.topleft = (50, 50)
            screen.blit(text, textRect)

            t = "Wave: " + str(Awave)
            text = font.render(t, True, (255, 0, 0))
            textRect = text.get_rect()
            textRect.topright = (width - 50, 50)
            screen.blit(text, textRect)

            t = "Time: " + str(int(Atime)) + " sec"
            text = font.render(t, True, (255, 0, 0))
            textRect = text.get_rect()
            textRect.bottomleft = (50, height - 50)
            screen.blit(text, textRect)

            acc = 0
            if Abooms:
                acc = int(Akills / Abooms * 100)
            t = "Accuracy: " + str(acc) + "%"
            text = font.render(t, True, (255, 0, 0))
            textRect = text.get_rect()
            textRect.bottomright = (width - 50, height - 50)
            screen.blit(text, textRect)

            pygame.display.flip()


class Gold(pygame.sprite.Sprite):
    image = load_image("gold.png")

    def __init__(self, x, y):
        super().__init__(all_sprites, golds)
        self.image = Gold.image
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        # вычисляем маску для эффективного сравнения
        self.mask = pygame.mask.from_surface(self.image)


if __name__ == '__main__':
    pygame.mixer.music.load("sounds/start.mp3")
    pygame.mixer.music.play(-1)
    clock = pygame.time.Clock()
    start_screen()
    pygame.mixer.music.stop()
    pygame.mixer.music.load("sounds/fight.mp3")
    pygame.mixer.music.play(-1)
    boom_sound = pygame.mixer.Sound('sounds/boom.mp3')
    boom_sound.set_volume(0.7)
    potion_sound = pygame.mixer.Sound('sounds/potion.mp3')
    rob_sound = pygame.mixer.Sound('sounds/rob.mp3')
    gameover_sound = pygame.mixer.Sound('sounds/gameover.mp3')

    # background
    Border(0, 760, width, 760, 0)
    Border(0, -1000, 0, height, 0)
    Border(width, -1000, width, height, 0)
    Platform(100, height // 2)
    Platform(400, height // 2 - 250)
    Platform(750, height // 2 + 100)
    gifFrameList = loadGIF("data/map.gif")
    currentFrame = 0

    # gold
    gold = Gold((width - 210) // 2, (height - 80) // 2 + 320)

    # main character
    mag = Mag((X_MAG_POS, Y_MAG_POS))

    # coins
    create_coins(2, 10)

    start_ticks = pygame.time.get_ticks()  # starter tick
    kol_bombs = 0
    kol_mobs = 0
    d_kol_mobs = 0
    kills = Kills(width - 10, 10)
    kills.update(screen, 0)
    poisons = 0
    number_wave = 1
    kol_mobs_wave = 0
    Wave_text(1)
    booms = 0
    while running:
        seconds = (pygame.time.get_ticks() - start_ticks) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                terminate()
            # mag
            if event.type == pygame.KEYDOWN and (event.key == 97):
                mag.move(-1, 0)
            if event.type == pygame.KEYUP and (event.key == 97):
                mag.move(1, 0)
            if event.type == pygame.KEYDOWN and (event.key == 100):
                mag.move(1, 0)
            if event.type == pygame.KEYUP and (event.key == 100):
                mag.move(-1, 0)
            if event.type == pygame.KEYDOWN and (event.key == 32) and mag.return_kol_jump() <= 1:
                mag.jumper()
            if event.type == pygame.KEYDOWN and (event.key == 13):
                mag.boom()

        mobs_golds = pygame.sprite.groupcollide(mobs, golds, False, False)
        for mob in mobs_golds:
            mob.running()
            gold_coins[-1].death()
            if isinstance(mob, Boss):
                for i in range(4):
                    if gold_coins:
                        gold_coins[-1].death()
            rob_sound.play()
            if not gold_coins:
                gameover_sound.play()
                show_go_screen()
                running = False
                terminate()

        hits1 = pygame.sprite.groupcollide(shots, mobs, False, False)
        hits2 = pygame.sprite.groupcollide(mobs, shots, False, False)
        for hit in hits1:
            hit.death()
        for hit in hits2:
            hit.death()
            d_kol_mobs += 1

        if kol_mobs_wave >= number_wave * 10 and not mobs:
            MOBS_PER_SECOND = sqrt(number_wave)
            number_wave += 1
            Wave_text(number_wave)
            kol_mobs_wave = 0

        screen.fill((0, 0, 0))
        if FLAG and (seconds // 0.1 / 10) > kol_bombs:
            mag.boom()
            kol_bombs += 0.1
        else:
            kol_bombs = seconds // 0.1 / 10

        if seconds > kol_mobs:
            if kol_mobs_wave < number_wave * 10 and not text_waves:
                if number_wave % 5 == 0 and kol_mobs_wave == (number_wave * 10 // 3 * 2):
                    Boss(number_wave * 3)
                else:
                    Mob()
                kol_mobs_wave += 1
            kol_mobs += 1 / MOBS_PER_SECOND

        if background_fps % 300 == 0:
            currentFrame = (currentFrame + 1) % len(gifFrameList)
            background_fps = 0

        if seconds > 1 and int(seconds) // 20 > poisons:
            Potion()
            poisons += 1

        rect = gifFrameList[currentFrame].get_rect(center=(width // 2, height // 2))
        screen.blit(gifFrameList[currentFrame], rect)

        kills.update(screen, d_kol_mobs)
        clock.tick(fps)
        background_fps += fps
        all_sprites.draw(screen)
        all_sprites.update()

        for i in text_effects:
            i.update(screen)
        for i in text_waves:
            i.update(screen)

        pygame.display.flip()

    pygame.quit()
