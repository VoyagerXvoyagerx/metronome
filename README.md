# Metronome

A clean and elegant desktop metronome designed for ukulele practice, powered by Pygame's low-level mixer for stable, low-latency audio.

## Features

- **Visual beat indicator**: First beat of each measure highlighted in red, remaining beats in blue
- **BPM range**: 40 ~ 180 BPM, adjustable via slider or quick-select buttons
- **Multiple time signatures**: Supports 2/4, 3/4, 4/4, and 6/8
- **Spacebar shortcut**: Start/stop without touching the mouse
- **Stable on Win11**: Uses Pygame mixer instead of system beeps to avoid OS suppression
- **Accurate timing**: Self-calibrating loop based on `time.perf_counter()` keeps the beat steady

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python metronome.py
```

## Requirements

- Python 3.x
- Windows 10/11 (recommended, for Pygame low-latency audio)

## Preview

- Large-font BPM display
- Real-time beat LEDs
- Quick-speed buttons: 50 / 60 / 70 / 80 / 90 / 100 / 110 / 120

## Technical Details

- Uses `pygame.mixer.Sound` to play in-memory WAV audio with zero file-I/O latency
- Synthesized click includes pitch drop and inharmonic overtones to mimic the crisp, dry sound of a plastic electronic metronome
- Multi-threaded architecture separates UI and audio logic to prevent interface stuttering

## License

MIT

---

*For the Chinese version, see [README_zh.md](README_zh.md).*
