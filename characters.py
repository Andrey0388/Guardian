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
POISONS = [(5, "JUMP"), (-5, "JUMP"), (0, "BOOMS")]
FLAG = False

horizontal_borders = pygame.sprite.Group()
vertical_borders = pygame.sprite.Group()
platforms = pygame.sprite.Group()
magg = pygame.sprite.Group()
mag_group = pygame.sprite.Group()
shots = pygame.sprite.Group()
mobs = pygame.sprite.Group()
text_effects = []

fps = 60


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
