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
RESPAWNS = [(0, 0), (200, 0)]

horizontal_borders = pygame.sprite.Group()
vertical_borders = pygame.sprite.Group()
platforms = pygame.sprite.Group()
magg = pygame.sprite.Group()
shots = pygame.sprite.Group()
mobs = pygame.sprite.Group()


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


class Mag(pygame.sprite.Sprite):
    image = load_image("mag.png")

    def __init__(self, pos):
        super().__init__(all_sprites)
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

        self.floor = Border(X_MAG_POS, Y_MAG_POS + 109, X_MAG_POS + 70, Y_MAG_POS + 109, 0, 1)

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
            self.move_y += 1
        while pygame.sprite.spritecollideany(self, vertical_borders):
            self.rect = self.rect.move(-self.move_x // abs(self.move_x), 0)
            self.floor.rect = self.floor.rect.move(-self.move_x // abs(self.move_x), 0)

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
            if mag:
                self.add(magg)
            else:
                self.add(vertical_borders)
            self.image = pygame.Surface([1, y2 - y1], pygame.SRCALPHA)
            self.rect = pygame.Rect(x1, y1, 1, y2 - y1)
            self.image.fill((0, 0, 0, f))
        else:  # горизонтальная стенка
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
        pos = RESPAWNS[random.randint(0, 1)]
        self.rect.x = pos[0]
        self.rect.y = pos[1]
        # вычисляем маску для эффективного сравнения
        self.mask = pygame.mask.from_surface(self.image)
        self.move_x = (((width // 2) - self.rect.x) // abs((width // 2) - self.rect.x)) * FAST_MOB
        self.move_y = 0
        self.add(mobs)
        self.v = True

        self.platform = False
        self.rx = 1

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
                self.rx = 1
            else:
                if not self.platform:
                    self.rx = random.randint(0, 1) * 2 - 1
                    self.platform = True

            while (pygame.sprite.spritecollideany(self, horizontal_borders))\
                    or (pygame.sprite.spritecollideany(self, platforms)):
                self.rect = self.rect.move(0, -1)

            self.move_y = 1
            self.kol_jump = 0
        else:
            self.move_y += 1
            self.platform = False
        while pygame.sprite.spritecollideany(self, vertical_borders):
            self.rect = self.rect.move(-self.move_x // abs(self.move_x), 0)
        if abs((width // 2) - self.rect.x):
            self.move_x = (((width // 2) - self.rect.x) // abs((width // 2) - self.rect.x)) * FAST // 3 * self.rx
        else:
            self.move_x = 0

    def death(self):
        mobs.remove(self)
        all_sprites.remove(self)
        create_particles((self.rect.x, self.rect.y))
        all_sprites.add(AnimatedSprite(load_image("boom.png"), 4, 4, self.rect.x - 25, self.rect.y - 25, 0))


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


if __name__ == '__main__':
    # background
    Border(0, 760, width, 760, 0)
    Border(0, -1000, 0, height, 0)
    Border(width, -1000, width, height, 0)
    Platform(100, height // 2)
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
    running = True
    fps = 60
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
    while running:
        seconds = (pygame.time.get_ticks() - start_ticks) / 1000
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
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

        screen.fill((0, 0, 0))

        if seconds > kol_bombs:
            mag.boom()
            kol_bombs += 1 / SHOTS_PER_SECOND

        if seconds > kol_mobs:
            Mob()
            kol_mobs += 1 / MOBS_PER_SECOND

        if bgfps % 300 == 0:
            currentFrame = (currentFrame + 1) % len(gifFrameList)
            bgfps = 0

        rect = gifFrameList[currentFrame].get_rect(center=(width // 2, height // 2))
        screen.blit(gifFrameList[currentFrame], rect)

        clock.tick(fps)
        bgfps += fps
        all_sprites.draw(screen)
        all_sprites.update()
        pygame.display.flip()
    pygame.quit()
