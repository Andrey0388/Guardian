import pygame
import os
import sys
from PIL import Image, ImageSequence
import random

pygame.init()
pygame.display.set_caption('Guardian')
size = width, height = 1200, 800
screen = pygame.display.set_mode(size)
all_sprites = pygame.sprite.Group()
screen_rect = (0, 0, width, height)
global FAST
FAST = 7
FAST_BOOM = 14
FAST_MOB = 2
JUMP = 20
FLOOR_GRAVITY = 8
GRAVITY = 0.3
PLATFORM_GRAVITY = 2
SHOTS_PER_SECOND = 2  # 65 - 70 максимум при скорости FAST_BOOM 14
MOBS_PER_SECOND = 0.5
X_MAG_POS = width // 2 + 100
Y_MAG_POS = height // 2 + 100
RESPAWNS = [(0, height - 200), (width - 50, height - 200), (100, 200), (width // 2, 5)]
POISONS = [(5, "JUMP")]

horizontal_borders = pygame.sprite.Group()
vertical_borders = pygame.sprite.Group()
platforms = pygame.sprite.Group()
magg = pygame.sprite.Group()
mag_group = pygame.sprite.Group()
shots = pygame.sprite.Group()
mobs = pygame.sprite.Group()

fps = 60


def terminate():
    pygame.quit()
    sys.exit()


def start_screen():
    intro_text = ["Guardian", "",
                  "Правила игры",
                  "Ваша задача не подпустить врагов в вашему золоту,",
                  "enter - стрелять,",
                  "space - прыжок,",
                  "a, d - движение"]

    fon = pygame.transform.scale(load_image('fon.jpg'), (width, height))
    screen.blit(fon, (0, 0))
    font = pygame.font.Font(None, 30)
    text_coord = 50
    for line in intro_text:
        string_rendered = font.render(line, 1, pygame.Color('red'))
        intro_rect = string_rendered.get_rect()
        text_coord += 10
        intro_rect.top = text_coord
        intro_rect.x = 10
        text_coord += intro_rect.height
        screen.blit(string_rendered, intro_rect)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()
            elif event.type == pygame.KEYDOWN or \
                    event.type == pygame.MOUSEBUTTONDOWN:
                return  # начинаем игру
        pygame.display.flip()
        clock.tick(fps)


def pilImageToSurface(pilImage):
    mode, size, data = pilImage.mode, pilImage.size, pilImage.tobytes()
    return pygame.image.fromstring(data, size, mode).convert_alpha()


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


def load_image(name, colorkey=None):
    fullname = os.path.join('data', name)
    if not os.path.isfile(fullname):
        print(f"Файл с изображением '{fullname}' не найден")
        sys.exit()
    image = pygame.image.load(fullname)
    if colorkey is not None:
        image = image.convert()
        if colorkey == -1:
            colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey)
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
                    all_sprites.remove(self)
        self.fps += 1


class Floor(pygame.sprite.Sprite):
    def __init__(self, x1, y1, x2, y2, f):
        super().__init__(all_sprites)
        magg.add(self)
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
        all_sprites.add(self)

    def update(self):
        if self.move_x > 0 and self.v:
            self.image = pygame.transform.flip(self.image, True, False)
            self.mask = pygame.mask.from_surface(self.image)
            floor.rect = floor.rect.move(5, 0)
            self.v = False
        if self.move_x < 0 and not self.v:
            self.image = pygame.transform.flip(self.image, True, False)
            self.mask = pygame.mask.from_surface(self.image)
            floor.rect = floor.rect.move(-5, 0)
            self.v = True

        self.rect = self.rect.move(self.move_x, self.move_y)
        floor.rect = floor.rect.move(self.move_x, self.move_y)

        if (pygame.sprite.spritecollideany(self, horizontal_borders)) \
                or (pygame.sprite.spritecollideany(floor, platforms) and self.move_y > 0):
            while (pygame.sprite.spritecollideany(self, horizontal_borders)) \
                    or (pygame.sprite.spritecollideany(floor, platforms)):
                self.rect = self.rect.move(0, -1)
                floor.rect = floor.rect.move(0, -1)
            self.move_y = 0
            self.kol_jump = 0
        else:
            if self.move_y < 30:
                self.move_y += 1
        while pygame.sprite.spritecollideany(self, vertical_borders):
            self.rect = self.rect.move(-self.move_x // abs(self.move_x), 0)
            floor.rect = floor.rect.move(-self.move_x // abs(self.move_x), 0)
        print(self.move_y)

    def move(self, x, y):
        self.move_x += x * FAST
        self.move_y += y * FAST

    def pos(self):
        return (self.rect.x, self.rect.y)

    def boom(self):
        shots.add(Fireball(self.pos(), -(int(self.v) * 2 - 1) * FAST_BOOM))

    def jumper(self):
        self.kol_jump += 1
        self.move_y = -JUMP

    def return_kol_jump(self):
        return self.kol_jump


class Fireball(pygame.sprite.Sprite):
    image = load_image("fireball.png")

    def __init__(self, pos1, move_x):
        super().__init__(all_sprites)
        self.image = Fireball.image
        self.rect = self.image.get_rect()
        self.rect.x = pos1[0] + 30
        self.rect.y = pos1[1] + 30
        self.move_x = move_x
        self.move_y = 0
        # вычисляем маску для эффективного сравнения
        self.mask = pygame.mask.from_surface(self.image)

    def update(self):
        self.rect = self.rect.move(self.move_x, self.move_y)
        if self.rect.x < 0 or self.rect.x > width - 60:
            shots.remove(self)
            all_sprites.remove(self)
            all_sprites.add(AnimatedSprite(load_image("boom.png"), 4, 4, self.rect.x - 25, self.rect.y - 25, 0))

    def death(self):
        shots.remove(self)
        all_sprites.remove(self)


class Border(pygame.sprite.Sprite):
    # строго вертикальный или строго горизонтальный отрезок
    def __init__(self, x1, y1, x2, y2, f, mag=0):
        super().__init__(all_sprites)
        if x1 == x2:  # вертикальная стенка
            self.add(vertical_borders)
            self.image = pygame.Surface([1, y2 - y1], pygame.SRCALPHA)
            self.rect = pygame.Rect(x1, y1, 1, y2 - y1)
            self.image.fill((0, 0, 0, f))
        else:  # горизонтальная стенка
            if mag:
                self.add(magg)
            else:
                self.add(horizontal_borders)
            self.image = pygame.Surface([x2 - x1, 1], pygame.SRCALPHA)
            self.rect = pygame.Rect(x1, y1, x2 - x1, 1)
            self.image.fill((0, 0, 0, f))


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
    image = load_image("rober.png")

    def __init__(self):
        super().__init__(all_sprites)
        self.image = Mob.image
        self.rect = self.image.get_rect()
        pos = RESPAWNS[random.randint(0, len(RESPAWNS) - 1)]
        self.rect.x = pos[0]
        self.rect.y = pos[1]
        # вычисляем маску для эффективного сравнения
        self.mask = pygame.mask.from_surface(self.image)
        self.platform = False
        self.move_x = 0
        self.move_y = 1
        self.add(mobs)
        self.v = True
        self.rx = random.randint(0, 1) * 2 - 1

    def update(self):
        if self.move_x > 0 and self.v:
            self.image = pygame.transform.flip(self.image, True, False)
            self.mask = pygame.mask.from_surface(self.image)
            self.v = False
        if self.move_x < 0 and not self.v:
            self.image = pygame.transform.flip(self.image, True, False)
            self.mask = pygame.mask.from_surface(self.image)
            self.v = True

        self.rect = self.rect.move(self.move_x, self.move_y)

        if (pygame.sprite.spritecollideany(self, horizontal_borders)) \
                or (pygame.sprite.spritecollideany(self, platforms) and self.move_y > 0):
            if pygame.sprite.spritecollideany(self, horizontal_borders):
                if (gold.rect.x - self.rect.x):
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
        while pygame.sprite.spritecollideany(self, vertical_borders) and self.move_x != 0:
            self.rect = self.rect.move(-self.move_x // abs(self.move_x), 0)
        self.move_x = self.rx * FAST_MOB

    def death(self):
        mobs.remove(self)
        all_sprites.remove(self)
        create_particles((self.rect.x, self.rect.y))
        all_sprites.add(AnimatedSprite(load_image("boom.png"), 4, 4, self.rect.x - 25, self.rect.y - 25, 0))


class Posion(pygame.sprite.Sprite):
    image = load_image("posion.png")

    def __init__(self):
        super().__init__(all_sprites)
        self.image = Posion.image
        self.rect = self.image.get_rect()
        self.rect.x = random.randint(100, width - 100)
        self.rect.y = random.randint(100, height - 100)
        # вычисляем маску для эффективного сравнения
        self.mask = pygame.mask.from_surface(self.image)

    def update(self):
        if pygame.sprite.spritecollideany(self, mag_group):
            x = random.randint(0, len(POISONS) - 1)
            if POISONS[x][1] == "JUMP":
                global JUMP
                JUMP += POISONS[x][0]
                self.death()

    def death(self):
        all_sprites.remove(self)
        create_particles((self.rect.x, self.rect.y))


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


def stop_window():
    running = True
    clock = pygame.time.Clock()
    start_ticks = pygame.time.get_ticks()  # starter tick
    kol_bombs = 0
    kol_mobs = 0
    while running:
        seconds = (pygame.time.get_ticks() - start_ticks) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEMOTION:
                if not flag:
                    flag = True
                    all_sprites.add(cursor)
                cursor.rect.topleft = event.pos
                if event.pos[0] == 0 or event.pos[1] == 0:
                    cursor.rect.topleft = (width, height)

        screen.fill((0, 0, 0))

        if bgfps % 300 == 0:
            currentFrame = (currentFrame + 1) % len(gifFrameList)
            bgfps = 0

        rect = gifFrameList[currentFrame].get_rect(center=(width // 2, height // 2))
        screen.blit(gifFrameList[currentFrame], rect)

        clock.tick(fps)
        bgfps += fps
        all_sprites.draw(screen)
        pygame.display.flip()


class Game_clock():
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
        font = pygame.font.SysFont('agencyfb', 50)
        t = f'{mins}:{secs}'
        text = font.render(t, True, (255, 0, 0))
        textRect = text.get_rect()
        textRect.center = (self.x, self.y)
        screen.blit(text, textRect)

    def a(self):
        self.i -= 1
        self.i %= 4

    def d(self):
        self.i += 1
        self.i %= 4


class Kills():
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def update(self, screen, kills):
        font = pygame.font.SysFont('agencyfb', 50)
        t = "Kills: " + str(kills)
        text = font.render(t, True, (255, 0, 0))
        textRect = text.get_rect()
        textRect.topleft = (self.x, self.y)
        screen.blit(text, textRect)


if __name__ == '__main__':

    clock = pygame.time.Clock()
    start_screen()

    # background
    Border(0, 760, width, 760, 0)
    Border(0, -1000, 0, height, 0)
    Border(width, -1000, width, height, 0)
    Platform(100, height // 2)
    Platform(400, height // 2 - 250)
    Platform(750, height // 2 + 100)
    gifFrameList = loadGIF("polyana.gif")
    currentFrame = 0

    # gold
    gold_image = load_image("gold.png")
    gold = pygame.sprite.Sprite()
    gold.image = gold_image
    gold.rect = gold_image.get_rect()
    all_sprites.add(gold)
    gold.rect.topleft = ((width - gold_image.get_width()) // 2, (height - gold_image.get_height()) // 2 + 330)

    # main character
    mag = Mag((X_MAG_POS, Y_MAG_POS))
    floor = Floor(X_MAG_POS, Y_MAG_POS + 109, X_MAG_POS + 70, Y_MAG_POS + 109, 0)
    running = True
    bgfps = 0
    flag = False
    image = load_image("arrow.png")
    cursor = pygame.sprite.Sprite()
    cursor.image = image
    cursor.rect = image.get_rect()
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()
    start_ticks = pygame.time.get_ticks()  # starter tick
    kol_bombs = 0
    kol_mobs = 0
    d_kol_mobs = 0
    game_clock = Game_clock(width - 70, 40)
    kills = Kills(20, 10)
    kills.update(screen, 0)

    Posion()

    while running:
        seconds = (pygame.time.get_ticks() - start_ticks) / 1000
        # if pygame.sprite.spritecollideany(gold, mobs):
        #     running = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            # mag
            if event.type == pygame.KEYDOWN and (event.key == 97):
                mag.move(-1, 0)
                game_clock.a()
            if event.type == pygame.KEYUP and (event.key == 97):
                mag.move(1, 0)
            if event.type == pygame.KEYDOWN and (event.key == 100):
                mag.move(1, 0)
                game_clock.d()
            if event.type == pygame.KEYUP and (event.key == 100):
                mag.move(-1, 0)
            if event.type == pygame.KEYDOWN and (event.key == 32) and mag.return_kol_jump() <= 1:
                mag.jumper()
            if event.type == pygame.KEYDOWN and (event.key == 13):
                mag.boom()

            if event.type == pygame.MOUSEMOTION:
                if not flag:
                    flag = True
                    all_sprites.add(cursor)
                cursor.rect.topleft = event.pos
                if event.pos[0] == 0 or event.pos[1] == 0:
                    cursor.rect.topleft = (width, height)

        hits1 = pygame.sprite.groupcollide(shots, mobs, False, False)
        hits2 = pygame.sprite.groupcollide(mobs, shots, False, False)
        for hit in hits1:
            hit.death()
        for hit in hits2:
            hit.death()
            d_kol_mobs += 1
            if d_kol_mobs % 5 == 0:
                MOBS_PER_SECOND *= 1.1

        screen.fill((0, 0, 0))

        if seconds > kol_mobs:
            Mob()
            kol_mobs += 1 / MOBS_PER_SECOND

        if bgfps % 300 == 0:
            currentFrame = (currentFrame + 1) % len(gifFrameList)
            bgfps = 0

        rect = gifFrameList[currentFrame].get_rect(center=(width // 2, height // 2))
        screen.blit(gifFrameList[currentFrame], rect)

        kills.update(screen, d_kol_mobs)
        game_clock.update(screen, seconds)
        clock.tick(fps)
        bgfps += fps
        all_sprites.draw(screen)
        all_sprites.update()
        pygame.display.flip()

    pygame.quit()
