---
name: tts
description: "Generate high-fidelity speech audio using text to speech with voice cloning and subtitles."
---

# Installation
If not installed, install it first with:
`which tts || uv tool install --default-index https://pypi.org/simple git+https://github.com/codescv/tts`.

# Parameters
- `--text`: The target text to synthesize.
- `--output`: Full path to the output `.wav` file.
- `--ref_audio`: Path to a 5-30 second clear reference audio file.
- `--ref_text`: The exact text spoken in the reference audio.
- `--srt`: Generate an .srt subtitles file.
- `--model_type`:
  - `qwen3`: use this by default.
  - `fishaudio` when you need **cross language voice cloning** (input text and ref text are in different languages) or **emotion control** (see below).

# Emotion Control (fishaudio Model ONLY, DOES NOT work for qwen3)
Fish Audio Model supports natural language emotion and style tags using square brackets `[ ]`. You can place them at the beginning of the text or between words.

**Examples:**
- `[angry] Stop it! I told you I'm tired.`
- `[whisper] Be quiet, the baby is sleeping.`
- `[excited] Oh my god! This is amazing!`
- `[sad] I feel a bit lonely today.`
- `[laughing] Haha, that's actually quite funny!`

You can also use natural language descriptions like `[speaking slowly and clearly]` or `[nervous whisper]`.

# Performance Tip
- Generation for a short sentence takes about 30-60 seconds on M4 Max.
- Ensure the reference audio is clean and the `ref_text` matches exactly for the best timbre alignment.
