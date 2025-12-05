import pygame
import os

os.makedirs("assets", exist_ok=True)
pygame.init()

def create_rect(name, width, height, color):
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill(color)
    # Add a small border or detail to see rotation better
    pygame.draw.rect(surf, (255, 255, 255), (0, 0, width, height), 2)
    pygame.draw.line(surf, (255, 255, 255), (0, 0), (width, height), 2)
    pygame.image.save(surf, f"assets/{name}.png")

# Body Parts
create_rect("torso", 50, 100, (100, 100, 200))
create_rect("head", 40, 40, (200, 150, 150))
create_rect("limb", 20, 70, (150, 150, 200))

def create_circle(name, radius, color):
    dia = radius * 2
    surf = pygame.Surface((dia, dia), pygame.SRCALPHA)
    pygame.draw.circle(surf, color, (radius, radius), radius)
    pygame.draw.circle(surf, (255, 255, 255), (radius, radius), radius, 2) # Outline
    # Add a line to show rotation
    pygame.draw.line(surf, (200, 200, 200), (radius, radius), (dia, radius), 2)
    pygame.image.save(surf, f"assets/{name}.png")

def create_triangle(name, width, height, color):
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    points = [(0, 0), (width, height//2), (0, height)]
    pygame.draw.polygon(surf, color, points)
    pygame.draw.polygon(surf, (255, 255, 255), points, 2)
    pygame.image.save(surf, f"assets/{name}.png")

# Robot Parts
create_rect("robot_base", 80, 40, (100, 100, 100))
create_rect("robot_arm_segment", 30, 120, (150, 150, 160))
create_circle("robot_joint", 20, (200, 50, 50))
create_triangle("robot_claw", 40, 60, (180, 180, 180))

# Snake Parts
create_circle("snake_head", 30, (50, 200, 50))
create_rect("snake_body", 40, 30, (50, 180, 50))
create_triangle("snake_tail", 40, 30, (50, 160, 50))

# Spider Parts
create_circle("spider_body", 40, (30, 30, 30))
create_rect("spider_leg_upper", 10, 60, (50, 50, 50))
create_rect("spider_leg_lower", 8, 50, (70, 70, 70))

print("Assets created in /assets")
pygame.quit()
