| stage | provider | model | calls | ok | median latency s | max latency s | GPU min | list-price USD |
|---|---|---|---|---|---|---|---|---|
| experiment | gemini | gemini-3.8-flash-tts | 5 | 5 | 5.0 | 5.6 | 0.0 | 0.0000 |
| keyframes | cloudflare | @cf/black-forest-labs/flux-2-klein-4b | 36 | 36 | 8.9 | 107.2 | 0.0 | 0.0430 |
| music | kaggle | ACE-Step-1.5/acestep-v15-turbo+none | 1 | 1 | 32.5 | 32.5 | 0.5 | 0.0032 |
| narration | gemini | gemini-3.1-flash-tts-preview | 2 | 2 | 5.6 | 5.6 | 0.0 | 0.0000 |
| narration | gemini | gemini-3.8-flash-tts | 26 | 23 | 4.7 | 59.6 | 0.0 | 0.0000 |
| script | gemini | gemini-3.6-flash | 2 | 2 | 81.1 | 81.1 | 0.0 | 0.0000 |
| script | gemini | gemini-3.8-flash | 4 | 1 | 138.8 | 318.5 | 0.0 | 0.0000 |
| smoke | cloudflare | @cf/black-forest-labs/flux-2-klein-4b | 2 | 2 | 10.2 | 10.2 | 0.0 | 0.0000 |
| smoke | gemini | gemini-3.8-flash-tts | 6 | 6 | 3.7 | 4.5 | 0.0 | 0.0000 |
| smoke | gemini | models.list | 2 | 2 | 1.4 | 1.4 | 0.0 | 0.0000 |

**Total:** 86 calls, 80 ok, 0.5 GPU minutes, list-price equivalent $0.05. Actual spend: $0.

**Failed calls:** 6
- 2026-11-25T07:08:08+00:00 script  gemini-3.8-flash: HTTP 503: {
  "error": {
    "code": 503,
    "message": "This model is currently experiencing high demand. Spikes in de
- 2026-11-25T07:35:48+00:00 script  gemini-3.8-flash: HTTP 503: {
  "error": {
    "code": 503,
    "message": "This model is currently experiencing high demand. Spikes in de
- 2026-11-25T07:38:07+00:00 narration S06 gemini-3.8-flash-tts: HTTP 429: {
  "error": {
    "code": 429,
    "message": "You exceeded your current quota, please check your plan and bi
- 2026-11-25T07:56:28+00:00 script  gemini-3.8-flash: HTTP 503: {
  "error": {
    "code": 503,
    "message": "This model is currently experiencing high demand. Spikes in de
- 2026-11-26T17:57:05+00:00 narration S08 gemini-3.8-flash-tts: provider asks to wait 14.0 h (daily quota?). Switch model for this stage or rerun after the reset. HTTP 429 (retry in 50
- 2026-11-26T17:57:30+00:00 narration S09 gemini-3.8-flash-tts: provider asks to wait 14.0 h (daily quota?). Switch model for this stage or rerun after the reset. HTTP 429 (retry in 50
