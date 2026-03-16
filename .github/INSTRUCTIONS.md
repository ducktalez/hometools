# INSTRUCTIONS - hometools Developer Guide

> Auto-generated overview. Run `hometools update-instructions` after structural changes.
> Last updated: 2026-03-16

## Project Structure

```text
hometools/
├── .github/
│   └── INSTRUCTIONS.md
├── src/
│   ├── hometools/
│   │   ├── audio/
│   │   ├── streaming/
│   │   ├── video/
│   │   ├── __init__.py
│   │   ├── cli.py
│   │   ├── config.py
│   │   ├── constants.py
│   │   ├── instructions.py
│   │   ├── logging_config.py
│   │   ├── print_tools.py
│   │   └── utils.py
│   └── hometools.egg-info/
│       ├── dependency_links.txt
│       ├── entry_points.txt
│       ├── PKG-INFO
│       ├── requires.txt
│       ├── SOURCES.txt
│       └── top_level.txt
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_instructions.py
│   ├── test_print_tools.py
│   ├── test_sanitize.py
│   ├── test_streaming_audio_catalog.py
│   ├── test_streaming_audio_server.py
│   ├── test_streaming_audio_sync.py
│   ├── test_utils.py
│   └── test_video_organizer.py
├── wa_data/
│   ├── 2raumwohnung - Wir Werden Sehen (Paul Kalkbrenner Remix) 😆😆😆 Δ ASAP Rocky feat. 2 Chainz, Drake & Kendrick Lamar - Fuckin Problem (Prod. By 40) many productions, (prod Simon), prod sdf erg34, prod. sdf erg34 asd - Topic official video (www.dfg).m4a
│   ├── Borat.mp4
│   ├── mp3files_lut.yaml
│   └── mp3files_lut2.yaml
├── .env.example
├── .gitignore
├── LICENSE
├── pyproject.toml
├── README.md
└── requirements.txt
```

## Quick Commands

```powershell
# Run tests
pytest

# Manual audio sync from NAS source
hometools sync-audio --dry-run
hometools sync-audio

# Start local audio streaming MVP
hometools serve-audio

# Regenerate this file
hometools update-instructions
```

## Notes

- Keep secrets in `.env`, never in source files.
- Keep side effects behind explicit CLI commands.
- Add tests for new pure functions in `tests/`.
- Audio sync runs only on command (no automatic NAS polling).
