import pygame
import os
import sys

pygame.init()
pygame.display.set_caption('Guardian')
size = width, height = 640, 480
screen = pygame.display.set_mode(size)
all_sprites = pygame.sprite.Group()
FAST = 5


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


class mag(pygame.sprite.Sprite):
    image = load_image("mag.png")

    def __init__(self, pos):
        super().__init__(all_sprites)
        self.image = mag.image
        self.rect = self.image.get_rect()
        self.rect.x = pos[0]
        self.rect.y = pos[1]
        # вычисляем маску для эффективного сравнения
        self.mask = pygame.mask.from_surface(self.image)
        self.move_x = 0
        self.move_y = 0
        self.v = True

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
        if pygame.sprite.collide_mask(self, gold):
            self.rect = self.rect.move(-self.move_x, -self.move_y)

    def move(self, x, y):
        self.move_x += x * FAST
        self.move_y += y * FAST

if __name__ == '__main__':
    # background
    bg_image = load_image("polyana.png")
    bg = pygame.sprite.Sprite()
    bg.image = bg_image
    bg.rect = bg_image.get_rect()
    all_sprites.add(bg)
    bg.rect.topleft = (0, 0)

    # background
    gold_image = load_image("gold.png")
    gold = pygame.sprite.Sprite()
    gold.image = gold_image
    gold.rect = gold_image.get_rect()
    all_sprites.add(gold)
    gold.rect.topleft = ((width - gold_image.get_width()) // 2, (height - gold_image.get_height()) // 2)

    # main character
    mag = mag((width // 2 + 50, height // 2 + 50))
    all_sprites.add(mag)
    running = True
    v = 20  # пикселей в секунду
    fps = 60
    flag = False
    image = load_image("arrow.png")
    cursor = pygame.sprite.Sprite()
    cursor.image = image
    cursor.rect = image.get_rect()
    pygame.mouse.set_visible(False)
    clock = pygame.time.Clock()
    start_ticks = pygame.time.get_ticks()  # starter tick
    while running:
        seconds = int((pygame.time.get_ticks() - start_ticks) / 1000)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and (event.key == 119):
                mag.move(0, -1)
            if event.type == pygame.KEYUP and (event.key == 119):
                mag.move(0, 1)
            if event.type == pygame.KEYDOWN and (event.key == 97):
                mag.move(-1, 0)
            if event.type == pygame.KEYUP and (event.key == 97):
                mag.move(1, 0)
            if event.type == pygame.KEYDOWN and (event.key == 115):
                mag.move(0, 1)
            if event.type == pygame.KEYUP and (event.key == 115):
                mag.move(0, -1)
            if event.type == pygame.KEYDOWN and (event.key == 100):
                mag.move(1, 0)
            if event.type == pygame.KEYUP and (event.key == 100):
                mag.move(-1, 0)
            if event.type == pygame.MOUSEMOTION:
                if not flag:
                    flag = True
                    all_sprites.add(cursor)
                cursor.rect.topleft = event.pos
                if event.pos[0] == 0 or event.pos[1] == 0:
                    cursor.rect.topleft = (width, height)
        screen.fill((0, 0, 0))
        clock.tick(fps)
        all_sprites.draw(screen)
        all_sprites.update()
        pygame.display.flip()
        print(seconds)
    pygame.quit()
