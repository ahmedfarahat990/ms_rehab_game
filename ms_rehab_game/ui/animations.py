from __future__ import annotations

import math
import random

import pygame

from ms_rehab_game.settings import WHITE


class ParticleSystem:
    def __init__(self) -> None:
        self.particles: list[dict] = []

    def emit(self, pos: tuple[float, float], color: tuple[int, int, int], count: int = 20, speed: float = 160) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            magnitude = random.uniform(speed * 0.4, speed)
            self.particles.append(
                {
                    "x": pos[0],
                    "y": pos[1],
                    "vx": math.cos(angle) * magnitude,
                    "vy": math.sin(angle) * magnitude,
                    "life": random.uniform(0.4, 0.9),
                    "color": color,
                    "radius": random.randint(2, 4),
                }
            )

    def update(self, dt: float) -> None:
        alive = []
        for particle in self.particles:
            particle["life"] -= dt
            if particle["life"] <= 0:
                continue
            particle["x"] += particle["vx"] * dt
            particle["y"] += particle["vy"] * dt
            particle["vy"] += 240 * dt
            alive.append(particle)
        self.particles = alive

    def draw(self, surface: pygame.Surface) -> None:
        for particle in self.particles:
            pygame.draw.circle(surface, particle["color"], (int(particle["x"]), int(particle["y"])), particle["radius"])


class Fireworks:
    def __init__(self, particles: ParticleSystem) -> None:
        self.particles = particles
        self.active = False
        self.cooldown = 0.0

    def start(self) -> None:
        self.active = True
        self.cooldown = 0.0

    def stop(self) -> None:
        self.active = False

    def update(self, dt: float, bounds: tuple[int, int]) -> None:
        if not self.active:
            return
        self.cooldown -= dt
        if self.cooldown <= 0:
            self.cooldown = 0.35
            pos = (random.randint(120, bounds[0] - 120), random.randint(80, bounds[1] // 2))
            color = random.choice([(231, 76, 60), (46, 204, 113), (52, 152, 219), (241, 196, 15), WHITE])
            self.particles.emit(pos, color, count=28, speed=220)
