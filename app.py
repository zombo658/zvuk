#!/usr/bin/env python3
"""Десктопная программа управления громкостью всей системы (до 300%).

Запуск:  python app.py

Обычное окно на Tkinter (входит в стандартную поставку Python) —
никаких серверов и браузеров. Меняет реальную системную громкость
через бэкенды из volume.py: pactl / amixer / WinAPI / osascript.

Горячие клавиши: стрелки вверх/вниз — ±5%, PgUp/PgDn — ±25%.
"""

import tkinter as tk
import tkinter.font as tkfont

from volume import pick_backend

# палитра (фиолетовый стиль)
BG = "#14042b"
CARD = "#1e0a40"
TRACK = "#332052"
VIOLET = "#a855f7"
VIOLET_SOFT = "#c084fc"
MAGENTA = "#e879f9"
TEXT = "#f3e8ff"
MUTED = "#b79ed9"

W, H = 420, 440
TRACK_X0, TRACK_X1, TRACK_Y = 40, W - 40, 258
THUMB_R = 12


def _blend(c1: str, c2: str, t: float) -> str:
    """Линейная интерполяция двух цветов '#rrggbb'."""
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


class App:
    def __init__(self):
        self.backend = pick_backend(allow_demo=True)
        self.volume = self.backend.get()
        self.dragging = False

        root = self.root = tk.Tk()
        root.title("Zvuk — громкость системы")
        root.configure(bg=BG)
        root.geometry(f"{W}x{H}")
        root.resizable(False, False)

        big = tkfont.Font(family="Segoe UI", size=44, weight="bold")
        small = tkfont.Font(family="Segoe UI", size=9)
        btn_font = tkfont.Font(family="Segoe UI", size=11, weight="bold")

        tk.Label(root, text="Z V U K", fg=VIOLET_SOFT, bg=BG,
                 font=tkfont.Font(family="Segoe UI", size=13, weight="bold")
                 ).pack(pady=(22, 0))
        tk.Label(root, text=f"громкость всей системы · максимум {self.backend.max_volume}%",
                 fg=MUTED, bg=BG, font=small).pack()

        self.value_lbl = tk.Label(root, text="—", fg=VIOLET_SOFT, bg=BG, font=big)
        self.value_lbl.pack(pady=(14, 0))

        self.boost_lbl = tk.Label(root, text="⚡ усиление >100%", fg=MAGENTA, bg=BG, font=small)
        self.boost_lbl.pack()

        # свой ползунок на Canvas — со градиентной заливкой
        self.canvas = tk.Canvas(root, width=W, height=70, bg=BG,
                                highlightthickness=0, cursor="hand2")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_drag)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        row = tk.Frame(root, bg=BG)
        row.pack(pady=(6, 0))
        self._button(row, "− 10", lambda: self.change(-10), font=btn_font, w=12)
        self._button(row, "+ 10", lambda: self.change(+10), font=btn_font, w=12, primary=True)

        presets = tk.Frame(root, bg=BG)
        presets.pack(pady=(10, 0))
        for p in (0, 50, 100, self.backend.max_volume):
            self._button(presets, f"{p}%", lambda p=p: self.set(p), font=small, w=8)

        self.status_lbl = tk.Label(
            root, fg=MUTED, bg=BG, font=small,
            text=("демо-режим: звуковая подсистема не найдена"
                  if self.backend.name == "demo" else f"бэкенд: {self.backend.name}"))
        self.status_lbl.pack(side="bottom", pady=12)

        root.bind("<Up>", lambda e: self.change(+5))
        root.bind("<Down>", lambda e: self.change(-5))
        root.bind("<Prior>", lambda e: self.change(+25))
        root.bind("<Next>", lambda e: self.change(-25))

        self._render()
        self._poll()

    def _button(self, parent, text, cmd, font, w, primary=False):
        b = tk.Button(parent, text=text, command=cmd, font=font, width=w,
                      fg=TEXT, bg=(VIOLET if primary else CARD),
                      activebackground=(MAGENTA if primary else TRACK),
                      activeforeground=TEXT, relief="flat", bd=0,
                      highlightthickness=0, cursor="hand2", pady=7)
        b.pack(side="left", padx=5)
        return b

    # ------------------------------------------------------------ логика

    def set(self, percent: int) -> None:
        try:
            self.volume = self.backend.set(percent)
        except Exception as exc:
            self.status_lbl.config(text=f"ошибка: {exc}", fg="#fda4af")
        self._render()

    def change(self, delta: int) -> None:
        self.set(self.volume + delta)

    def _poll(self) -> None:
        # подхватываем громкость, изменённую снаружи (клавишами, микшером)
        if not self.dragging:
            try:
                self.volume = self.backend.get()
                self._render()
            except Exception:
                pass
        self.root.after(2000, self._poll)

    # -------------------------------------------------------- отрисовка

    def _x_to_percent(self, x: int) -> int:
        t = (x - TRACK_X0) / (TRACK_X1 - TRACK_X0)
        return round(max(0.0, min(1.0, t)) * self.backend.max_volume)

    def _on_drag(self, event) -> None:
        self.dragging = True
        self.volume = self._x_to_percent(event.x)
        self._render()

    def _on_release(self, event) -> None:
        self.dragging = False
        self.set(self._x_to_percent(event.x))

    def _render(self) -> None:
        maxv = self.backend.max_volume
        self.value_lbl.config(text=f"{self.volume}%")
        self.boost_lbl.config(fg=MAGENTA if self.volume > 100 else BG)

        c = self.canvas
        c.delete("all")
        y = 30
        # серый трек
        c.create_line(TRACK_X0, y, TRACK_X1, y, width=8, fill=TRACK, capstyle="round")
        # заполненная часть — градиент фиолетовый -> пурпурный
        fill_x = TRACK_X0 + (TRACK_X1 - TRACK_X0) * self.volume / maxv
        if self.volume > 0:
            steps = max(1, int(fill_x - TRACK_X0))
            for i in range(steps):
                t = i / max(1, steps - 1)
                c.create_line(TRACK_X0 + i, y, TRACK_X0 + i + 2, y, width=8,
                              fill=_blend(VIOLET, MAGENTA, t), capstyle="round")
        # бегунок
        c.create_oval(fill_x - THUMB_R, y - THUMB_R, fill_x + THUMB_R, y + THUMB_R,
                      fill=VIOLET_SOFT, outline=VIOLET, width=3)
        # подписи делений
        for p in (0, 100, 200, 300):
            if p > maxv:
                break
            px = TRACK_X0 + (TRACK_X1 - TRACK_X0) * p / maxv
            c.create_text(px, y + 26, text=f"{p}%", fill=MUTED,
                          font=("Segoe UI", 8))

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
