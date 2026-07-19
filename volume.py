#!/usr/bin/env python3
"""Прибавляет системную громкость на Windows, Linux и macOS.

Использование:
    python volume.py            # прибавить на 10%
    python volume.py 25         # прибавить на 25%
    python volume.py -25        # убавить на 25%
    python volume.py --set 80   # установить громкость 80%
    python volume.py --get      # показать текущую громкость

Внешние библиотеки не нужны: используются штатные средства каждой ОС
(WinAPI на Windows, pactl/amixer на Linux, osascript на macOS).
"""

import argparse
import platform
import shutil
import subprocess
import sys


# ---------------------------------------------------------------- Windows

def _windows_backend():
    import ctypes

    winmm = ctypes.windll.winmm

    def get() -> int:
        # waveOutGetVolume возвращает громкость левого и правого канала
        # (по 16 бит на канал, 0xFFFF = 100%)
        vol = ctypes.c_uint()
        winmm.waveOutGetVolume(0, ctypes.byref(vol))
        left = vol.value & 0xFFFF
        return round(left * 100 / 0xFFFF)

    def set_(percent: int) -> None:
        value = round(max(0, min(100, percent)) * 0xFFFF / 100)
        winmm.waveOutSetVolume(0, value | (value << 16))

    return get, set_


# ------------------------------------------------------------------ Linux

def _run(cmd: list[str]) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def _pactl_backend():
    sink = "@DEFAULT_SINK@"

    def get() -> int:
        out = _run(["pactl", "get-sink-volume", sink])
        # строка вида: "Volume: front-left: 39321 /  60% / ..."
        for token in out.split():
            if token.endswith("%"):
                return int(token.rstrip("%"))
        raise RuntimeError(f"не удалось разобрать вывод pactl: {out!r}")

    def set_(percent: int) -> None:
        _run(["pactl", "set-sink-volume", sink, f"{max(0, min(100, percent))}%"])

    return get, set_


def _amixer_backend():
    def get() -> int:
        out = _run(["amixer", "get", "Master"])
        # ищем "[60%]"
        start = out.index("[") + 1
        return int(out[start:out.index("%", start)])

    def set_(percent: int) -> None:
        _run(["amixer", "-q", "set", "Master", f"{max(0, min(100, percent))}%"])

    return get, set_


# ------------------------------------------------------------------ macOS

def _macos_backend():
    def get() -> int:
        out = _run(["osascript", "-e", "output volume of (get volume settings)"])
        return int(out.strip())

    def set_(percent: int) -> None:
        _run(["osascript", "-e", f"set volume output volume {max(0, min(100, percent))}"])

    return get, set_


# ----------------------------------------------------------------- выбор

def pick_backend():
    system = platform.system()
    if system == "Windows":
        return _windows_backend()
    if system == "Darwin":
        return _macos_backend()
    if system == "Linux":
        if shutil.which("pactl"):
            return _pactl_backend()
        if shutil.which("amixer"):
            return _amixer_backend()
        sys.exit("Ошибка: не найден ни pactl (PulseAudio/PipeWire), ни amixer (ALSA). "
                 "Установите, например: sudo apt install pulseaudio-utils или alsa-utils")
    sys.exit(f"Ошибка: ОС {system!r} не поддерживается")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Прибавляет (или убавляет) громкость всей системы.")
    parser.add_argument("step", nargs="?", type=int, default=10,
                        help="на сколько процентов изменить громкость "
                             "(по умолчанию +10, можно отрицательное)")
    parser.add_argument("--set", dest="set_to", type=int, metavar="N",
                        help="установить громкость ровно N%%")
    parser.add_argument("--get", action="store_true",
                        help="только показать текущую громкость")
    args = parser.parse_args()

    get, set_ = pick_backend()

    if args.get:
        print(f"Текущая громкость: {get()}%")
        return

    current = get()
    target = args.set_to if args.set_to is not None else current + args.step
    target = max(0, min(100, target))
    set_(target)
    print(f"Громкость: {current}% -> {target}%")


if __name__ == "__main__":
    main()
