# Ethics: consent, licences, labelling

## Consent

The pipeline enforces this. A character marked `real_person: true` in storyboard.json must have a
`consent_id` matching an entry below, or `film.py` refuses to run (`pipeline/common.py: validate`).

**Current film:** all on-screen characters are fictional and stylised (`real_person: false`). No real
person's face or likeness is generated. Narration uses a stock Gemini TTS voice (`Kore`), not a cloned voice.

**Permission to tell the story** (not likeness or voice):
- Story source: <relative, e.g. "my mother">. Asked on <date>, <how: in person/phone>. Agreed to the story
  being told publicly in a film. Reviewed the narration text on <date>.

<!-- If a real person is ever shown or voiced, add a record like this BEFORE generating anything:
### consent_id: C1
- Person: <name/relationship>
- What: likeness / voice / both, in this film only
- Words they agreed to: final narration text reviewed on <date>
- How recorded: <signed note / voice memo file outside the repo>, <date>
- Can withdraw: yes, by telling me; film would be taken down
-->

## Licences

| Component | Licence / terms | Output use | Checked |
|---|---|---|---|
| Gemini 3.8 Flash / Flash TTS (Google AI Studio free tier) | Gemini API Additional Terms; free-tier inputs may be used to improve Google products | Output may be used; SynthID watermark on audio | 2026-11-25 |
| FLUX.2 klein 4B (Black Forest Labs, via Cloudflare Workers AI) | Apache 2.0 (the 9B variant is non-commercial; not used) | Commercial use allowed | 2026-11-25 |
| FLUX.1 schnell (fallback) | Apache 2.0 | Commercial use allowed | 2026-11-25 |
| Wan 2.2 TI2V-5B | Apache 2.0 | Commercial use allowed | 2026-11-25 |
| ACE-Step 1.5 | MIT; trained on licensed, royalty-free and synthetic data | Commercial use allowed | 2026-11-25 |
| FFmpeg | LGPL/GPL (tool only) | n/a | |
| Fonts (Arial / Ebrima on Windows) | System fonts, used only for rendering | n/a | |

## Private data

Free-tier endpoints may use prompts for training. So:
- no family names, addresses or private details in prompts or narration beyond what the family agreed to publish;
- the story brief contains only what would be public in the film anyway.

## Labelling plan

- **In the film:** a 3-second end card states it was made with AI and names the models (`end_card` in storyboard.json).
- **On the platform:** the AI-generated content disclosure is switched on at upload (YouTube "altered or synthetic
  content" / TikTok "AI-generated" label). Screenshot kept for submission.
- **Provenance:** no watermark or metadata stripping. Gemini audio keeps SynthID. FFmpeg re-encoding does not add or
  remove C2PA. The post text says the film is AI-generated.
- **Style:** prompts describe qualities (warm, gouache, grain) and never name living artists.
