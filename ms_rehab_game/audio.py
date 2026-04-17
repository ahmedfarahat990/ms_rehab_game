from __future__ import annotations

import math

import numpy as np
import pygame


def generate_tone(frequency: float, duration_ms: int, volume: float = 0.5, sample_rate: int = 44100) -> pygame.mixer.Sound:
    duration_s = duration_ms / 1000.0
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), False)
    wave = np.sin(2 * math.pi * frequency * t) * volume
    audio = np.column_stack((wave, wave))
    samples = np.int16(audio * 32767)
    return pygame.sndarray.make_sound(samples)


class SoundBank:
    def __init__(self) -> None:
        if not pygame.mixer.get_init():
            self.enabled = False
            self.channels = []
            return
        self.enabled = True
        self.success = generate_tone(880, 150)
        self.miss = generate_tone(200, 200)
        self.streak_a = generate_tone(1046, 100)
        self.streak_b = generate_tone(1318, 100)
        self.end_a = generate_tone(523, 300)
        self.end_b = generate_tone(659, 300)
        self.end_c = generate_tone(784, 300)
        self.achievement = generate_tone(1174, 200)
        self.channels = [pygame.mixer.Channel(i) for i in range(min(8, pygame.mixer.get_num_channels()))]

    def play_success(self) -> None:
        if not self.enabled:
            return
        self.channels[0].play(self.success)

    def play_miss(self) -> None:
        if not self.enabled:
            return
        self.channels[1].play(self.miss)

    def play_streak(self) -> None:
        if not self.enabled:
            return
        self.channels[2].play(self.streak_a)
        self.channels[2].queue(self.streak_b)

    def play_end(self) -> None:
        if not self.enabled:
            return
        self.channels[3].play(self.end_a)
        self.channels[3].queue(self.end_b)
        self.channels[3].queue(self.end_c)

    def play_achievement(self) -> None:
        if not self.enabled:
            return
        self.channels[4].play(self.achievement)
