# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

### TTS

- Provider: ElevenLabs
- Preferred voice: Rachel (voice_id: 21m00Tcm4TlvDq8ikWAM) — 따뜻한 여성 음성
- Model: eleven_multilingual_v2
- Voice settings: stability=0.18, similarity_boost=0.88, style=0.8, use_speaker_boost=true, speed=1.2
- API key: configured in openclaw.json env

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.
