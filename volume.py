#!/usr/bin/env python3
"""Управление системной громкостью на Windows, Linux и macOS.

Использование:
    python volume.py            # прибавить на 10%
    python volume.py 25         # прибавить на 25%
    python volume.py -25        # убавить на 25%
    python volume.py --set 150  # установить громкость 150%
    python volume.py --get      # показать текущую громкость

Максимум — 300% там, где это поддерживает звуковой сервер
(PulseAudio/PipeWire через pactl). На Windows, macOS и ALSA предел — 100%.

Внешние библиотеки не нужны: используются штатные средства каждой ОС
(WinAPI на Windows, pactl/amixer на Linux, osascript на macOS).
"""

import argparse
import platform
import shutil
import subprocess
import sys


class Backend:
    """Пара get/set плюс верхний предел громкости в процентах."""

    name = "base"
    max_volume = 100

    def get(self) -> int:
        raise NotImplementedError

    def set(self, percent: int) -> int:
        raise NotImplementedError

    def clamp(self, percent: int) -> int:
        return max(0, min(self.max_volume, percent))


# ---------------------------------------------------------------- Windows

class WindowsBackend(Backend):
    name = "winmm"

    def __init__(self):
        import ctypes
        self._ctypes = ctypes
        self._winmm = ctypes.windll.winmm

    def get(self) -> int:
        # waveOutGetVolume возвращает громкость левого и правого канала
        # (по 16 бит на канал, 0xFFFF = 100%)
        vol = self._ctypes.c_uint()
        self._winmm.waveOutGetVolume(0, self._ctypes.byref(vol))
        left = vol.value & 0xFFFF
        return round(left * 100 / 0xFFFF)

    def set(self, percent: int) -> int:
        percent = self.clamp(percent)
        value = round(percent * 0xFFFF / 100)
        self._winmm.waveOutSetVolume(0, value | (value << 16))
        return percent


# ------------------------------------------------------------------ Linux

def _run(cmd: list[str]) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


class PactlBackend(Backend):
    """PulseAudio/PipeWire: единственный бэкенд с усилением сверх 100%."""

    name = "pactl"
    max_volume = 300
    _sink = "@DEFAULT_SINK@"

    def get(self) -> int:
        out = _run(["pactl", "get-sink-volume", self._sink])
        # строка вида: "Volume: front-left: 39321 /  60% / ..."
        for token in out.split():
            if token.endswith("%"):
                return int(token.rstrip("%"))
        raise RuntimeError(f"не удалось разобрать вывод pactl: {out!r}")

    def set(self, percent: int) -> int:
        percent = self.clamp(percent)
        _run(["pactl", "set-sink-volume", self._sink, f"{percent}%"])
        return percent


class AmixerBackend(Backend):
    name = "amixer"

    def get(self) -> int:
        out = _run(["amixer", "get", "Master"])
        # ищем "[60%]"
        start = out.index("[") + 1
        return int(out[start:out.index("%", start)])

    def set(self, percent: int) -> int:
        percent = self.clamp(percent)
        _run(["amixer", "-q", "set", "Master", f"{percent}%"])
        return percent


# ------------------------------------------------------------------ macOS

class MacBackend(Backend):
    name = "osascript"

    def get(self) -> int:
        out = _run(["osascript", "-e", "output volume of (get volume settings)"])
        return int(out.strip())

    def set(self, percent: int) -> int:
        percent = self.clamp(percent)
        _run(["osascript", "-e", f"set volume output volume {percent}"])
        return percent


# ------------------------------------------------------------- демо-режим

class DemoBackend(Backend):
    """Хранит громкость в памяти — для машин без звуковой подсистемы."""

    name = "demo"
    max_volume = 300

    def __init__(self):
        self._volume = 50

    def get(self) -> int:
        return self._volume

    def set(self, percent: int) -> int:
        self._volume = self.clamp(percent)
        return self._volume


# ----------------------------------------------------------------- выбор

def pick_backend(allow_demo: bool = False) -> Backend:
    system = platform.system()
    if system == "Windows":
        return WindowsBackend()
    if system == "Darwin":
        return MacBackend()
    if system == "Linux":
        if shutil.which("pactl"):
            return PactlBackend()
        if shutil.which("amixer"):
            return AmixerBackend()
        if allow_demo:
            return DemoBackend()
        sys.exit("Ошибка: не найден ни pactl (PulseAudio/PipeWire), ни amixer (ALSA). "
                 "Установите, например: sudo apt install pulseaudio-utils или alsa-utils")
    if allow_demo:
        return DemoBackend()
    sys.exit(f"Ошибка: ОС {system!r} не поддерживается")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Прибавляет (или убавляет) громкость всей системы, максимум 300%%.")
    parser.add_argument("step", nargs="?", type=int, default=10,
                        help="на сколько процентов изменить громкость "
                             "(по умолчанию +10, можно отрицательное)")
    parser.add_argument("--set", dest="set_to", type=int, metavar="N",
                        help="установить громкость ровно N%%")
    parser.add_argument("--get", action="store_true",
                        help="только показать текущую громкость")
    args = parser.parse_args()

    backend = pick_backend()

    if args.get:
        print(f"Текущая громкость: {backend.get()}% (максимум {backend.max_volume}%)")
        return

    current = backend.get()
    target = args.set_to if args.set_to is not None else current + args.step
    target = backend.set(target)
    print(f"Громкость: {current}% -> {target}%")


if __name__ == "__main__":
    main()
