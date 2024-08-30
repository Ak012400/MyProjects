import pygame
import time

# Initialize pygame
pygame.init()

# Define colors
white = (255, 255, 255)
black = (0, 0, 0)
red = (213, 50, 80)

# Window dimensions
width = 800
height = 600

# Creating game window
game_window = pygame.display.set_mode((width, height))
pygame.display.set_caption('Snake Game by Arun')

# Frame Per Second controller
clock = pygame.time.Clock()

# Snake block size
snake_block = 10

# Game loop
def game_loop():
    game_over = False
    close_game = False

    # Starting position of snake
    x = width / 2
    y = height / 2

    x_change = 0
    y_change = 0

    while not game_over:

        while close_game:
            game_window.fill(black)
            font_style = pygame.font.SysFont("bahnschrift", 25)
            msg = font_style.render("You Lost! Press C-Play Again or Q-Quit", True, red)
            game_window.blit(msg, [width / 6, height / 3])

            pygame.display.update()

            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        game_over = True
                        close_game = False
                    if event.key == pygame.K_c:
                        game_loop()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_over = True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    x_change = -snake_block
                    y_change = 0
                elif event.key == pygame.K_RIGHT:
                    x_change = snake_block
                    y_change = 0
                elif event.key == pygame.K_UP:
                    y_change = -snake_block
                    x_change = 0
                elif event.key == pygame.K_DOWN:
                    y_change = snake_block
                    x_change = 0

        x += x_change
        y += y_change

        game_window.fill(white)
        pygame.draw.rect(game_window, black, [x, y, snake_block, snake_block])

        pygame.display.update()

        if x >= width or x < 0 or y >= height or y < 0:
            close_game = True

        clock.tick(30)

    pygame.quit()
    quit()

game_loop()
