# Design

> Fill sections 1–2 **before** generating any keyframe. Sections 3–4 are your user-test notes.
> Graders check that the audience was set before generation, that ≥3 people saw each cut, and that
> the storyboard visibly changed (bump `version`, set `changed_by` on the shots you changed).

## 1. Brief (written 2026-11-25, before any keyframe was generated; full brief in story/brief.md)
- **Story:** ንጉስ ኣራዊት ኣያ ኣንበሳ (Is the grass green or blue?), a traditional Tigrinya animal fable told in my family.
- **Audience:** Tigrinya-speaking families, especially diaspora parents watching with children aged 6–12, and
  young adults who grew up with these tales. They watch on a phone, vertical, shared on WhatsApp, TikTok and Facebook.
  Many of the children understand some spoken Tigrinya but read English, so the subtitles are English.
- **Intent:** they laugh at the lion's surprising verdict, then get the twist: *don't waste your wisdom and
  time arguing with someone who refuses to see*. Parents want to retell it at home.
- **Define:** How might we help diaspora children hear a Tigrinya fable in Tigrinya, follow it, and remember its lesson?
- **Constraints:** 60–90 s; Tigrinya narration plus English subtitles; free tier only; fictional animal characters,
  so no likeness consent is needed; **the grass must be visibly green in every shot**, since the joke depends on it.

## 2. Ideate: options considered
| Option | Why yes | Why not | Chosen? |
|---|---|---|---|
| A family member's life story | Very personal | Needs likeness/voice consent; harder consistency with real faces | No |
| This animal fable | Strong twist, a clear lesson, three distinct non-human characters, no consent risk | Three characters to keep consistent | **Yes** |
| Full original text, 8 shots | Keeps every word | Measured TTS pace (E3) makes it ~130 s | No |
| Condensed text, 12 shots | Fits 90 s, one beat per shot | Loses some wording, reviewed line by line (E4) | **Yes (v2)** |

**Why every shot exists:** see `reason` on each shot in storyboard.json.

## 3. User test 1: first cut (storyboard v2, 83.4 s, shared 2026-11-25 evening)
Verbatim responses. Names withheld; relationship and channel to be filled in.

| Viewer | How | What they said (verbatim) | Reading |
|---|---|---|---|
| 1 | <channel> | "Wawww no laughing at all its very touching end of story 👍" | Moved; read the ending as touching, **not funny** |
| 2 | <channel> | "ይካዓረኒሎ 😁 ... it's in great sync though" | Amused; narration/picture/subtitle **timing works**. Possibly quoting how S07 «ይካትዓኒ ኣሎ» sounded (to confirm) |
| 3 | <channel> | "I didn't lough bro" | **No laugh** |
| 4 | <channel> | «ነብሪ ምስ ኣድጊ ለይጋነ😁 / ሳዕሪ ሰማያዊ እዩ ኢሉ እንታይ እዩ ዝበለ / ሰብ ናብ ሰቡ ዝብኢ ናብ ገረቡ ነገር እያ😜» | Enjoyed it, but **asked what the "grass is blue" verdict meant**; answered with a proverb about keeping to your own kind |

**Insights:**
1. **The comedy intent failed.** I expected the lion's verdict to get a laugh. 0 of 4 reported laughing; two said
   explicitly that they didn't, and one called the ending *touching*. The audience reads this fable as wisdom, not a joke.
2. **The lesson isn't clear enough.** Viewer 4 asked what the verdict meant. The lesson is spoken once (S11) at the
   lively pace adopted in E3b for length, so the most important line is the most rushed.
3. **Sync works** (viewer 2). Picture cut to the measured voice track does its job, so keep that approach.
4. Viewer 4's reply is itself a proverb, so the audience thinks in proverbs. A clearly stated moral fits how they
   already talk about stories.
5. **Pronunciation:** viewer 2's «ይካዓረኒሎ» is how the TTS said S07's «ይካትዓኒ ኣሎ»: it dropped the ት and merged the
   two words. A native listener caught it; I could not have from the waveform. That is the one concrete defect they named.

**Decisions (storyboard v2 → v3):**
| What | Before | After | Why |
|---|---|---|---|
| `intent` | "they laugh at the verdict, then get the twist" | moved by the lion's wisdom, leave with the lesson | none of 4 said they laughed (2 said they did not), 1 called it touching. The story works, my *intent* was wrong, so the intent changes, not the story |
| `end_card.lines` | title, credits | + "Don't waste your wisdom arguing with someone who refuses to see." | viewer 4 asked what the verdict meant; state the moral in plain words (text, no TTS cost) |
| S07 narration | «… ይካትዓኒ ኣሎ» mispronounced | same words + a "two distinct words" instruction (variant A of 3, EXPERIMENTS.md E8) | viewer 2 |
| Kept | sync, pacing, shot order | unchanged | viewer 2: "in great sync" |

## 4. User test 2: near-final cut (storyboard vN)
| Who | How | What they said | Where they reacted |
|---|---|---|---|
| 1. | | | |
| 2. | | | |
| 3. | | | |

**Insights:**
**Changes made:**
