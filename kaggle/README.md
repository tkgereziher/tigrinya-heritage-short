# GPU jobs on Kaggle

Both jobs read `storyboard.json` and the committed keyframes straight from the public GitHub repo,
save each output as soon as it's made (sessions die), and write a `runs_gpu.jsonl` log.

## Setup (once)
1. kaggle.com → **Create → New Notebook**.
2. Right sidebar → **Session options**: Accelerator **GPU T4 x2**, **Internet on** (needs phone verification).
3. Push your latest keyframes to GitHub first (`git push`), since the notebook clones the repo.

## Job 1: Wan 2.2 image-to-video (about 10–20 min per clip on a T4; run it overnight)

```python
!git clone -q https://github.com/tkgereziher/tigrinya-heritage-short.git
%cd tigrinya-heritage-short
!pip install -q "git+https://github.com/huggingface/diffusers" transformers accelerate ftfy imageio imageio-ffmpeg
```
First, **one shot as a test**, to learn the real time per clip and whether fp16 works:
```python
!python kaggle/wan22_i2v.py --only S01 --device cuda:0
!tail -n 1 outputs/clips/runs_gpu.jsonl
```
- `ok`: note `gpu_s`. Then run the rest on both GPUs at once:
  ```python
  !python kaggle/wan22_i2v.py --shard 0/2 --device cuda:0 > gpu0.log 2>&1 & python kaggle/wan22_i2v.py --shard 1/2 --device cuda:1 > gpu1.log 2>&1
  ```
- `black/NaN frames`: rerun the test with `--dtype bf16`, then `--dtype fp32` (slower), and record which one worked.
- Out of memory: `--frames 49` (2 s) and/or `--width 640 --height 368`.

Then download the results:
```python
!zip -qr /kaggle/working/clips.zip outputs/clips
```
Download `clips.zip` from the notebook's **Output** panel and unzip it into the local repo so the files land
in `outputs/clips/`. Then run `python film.py ingest` and `python film.py status`. Shots that have a
fresh clip show `picture=wan`.

## Job 2: ACE-Step 1.5 score candidates (a few minutes)

New notebook (or the same one after Job 1), GPU T4, internet on:
```python
!git clone -q https://github.com/tkgereziher/tigrinya-heritage-short.git
!git clone -q https://github.com/ACE-Step/ACE-Step-1.5.git
!pip install -q -e ACE-Step-1.5
!python tigrinya-heritage-short/kaggle/acestep_music.py --acestep ACE-Step-1.5 --offload
!zip -qr /kaggle/working/music.zip tigrinya-heritage-short/outputs/music/candidates
```
Unzip `music.zip` into the local repo (`outputs/music/candidates/`), run `python film.py ingest`, listen to
the 3 candidates **under the narration at low volume**, and set `music.chosen` + `music.chosen_reason` in
storyboard.json. If the Python API has moved, the script fails with an import error. The fallback is the
Gradio UI (`!cd ACE-Step-1.5 && python -m acestep --share`) with the same caption, bpm, key and seeds from
storyboard.json; log those calls in FAILURES.md.

Write every error you hit into FAILURES.md. Kaggle/T4 problems are exactly the evidence the grading looks for.
