# zvuk

Программа, которая прибавляет звук во всей системе. Работает на Windows, Linux и macOS, внешние библиотеки не нужны — только Python 3.9+.

## Использование

```bash
python volume.py            # прибавить громкость на 10%
python volume.py 25         # прибавить на 25%
python volume.py -25        # убавить на 25%
python volume.py --set 80   # установить ровно 80%
python volume.py --get      # показать текущую громкость
```

## Как это работает

| ОС      | Механизм                                   |
|---------|--------------------------------------------|
| Windows | WinAPI (`winmm.waveOutSetVolume`)          |
| Linux   | `pactl` (PulseAudio/PipeWire) или `amixer` (ALSA) |
| macOS   | `osascript` (AppleScript)                  |

На Linux нужна одна из утилит: `pactl` (обычно уже установлена вместе с PulseAudio/PipeWire) или `amixer` (`sudo apt install alsa-utils`).
