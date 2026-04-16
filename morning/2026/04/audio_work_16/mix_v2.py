#!/usr/bin/env python3
"""
構成 v2:
  [0:00-~3.6s]  タイトルコール（BGMなし、クリア）+ 0.5秒の余白
  [~3.6s-end]   本編ナレーション + BGM -22dB でフェードインしつつループ（末尾3秒フェードアウト）
  ※ ジングルは将来的にタイトルコール前に前置する
"""
import json, os, subprocess, shutil
from mutagen.id3 import ID3, CHAP, CTOC, TIT2, CTOCFlags

ROOT = "/Users/yskzz121/ui-kabu-times"
WORK = os.path.join(ROOT, "morning/2026/04/audio_work_16")
FINAL = os.path.join(ROOT, "morning/2026/04/16.mp3")
JSON_OUT = os.path.join(ROOT, "morning/2026/04/16-chapters.json")

TITLE = "/Users/yskzz121/Desktop/atlas_radio_bgm_preview/titlev3_rate112.mp3"
BGM = os.path.join(ROOT, "assets/bgm/tropical-bounce.mp3")
NARRATION = os.path.join(WORK, "narration_only_backup.mp3")

TITLE_TAIL_SILENCE = 0.5    # タイトル後の余白
MAIN_BGM_VOL = 0.08         # ~-22dB
BGM_FADE_IN = 2.0
BGM_FADE_OUT = 3.0

# --- Step 1: title + 0.5s silence ---
title_padded = os.path.join(WORK, "intro_title_clean.mp3")
print("[1/3] Intro生成 (title call + 0.5s silence) ...")
subprocess.run([
    "ffmpeg", "-y", "-i", TITLE,
    "-af", f"apad=pad_dur={TITLE_TAIL_SILENCE}",
    "-c:a", "libmp3lame", "-b:a", "128k", "-ar", "24000",
    title_padded,
], check=True, capture_output=True)

# --- Step 2: narration + BGM ---
print("[2/3] Main合成 (narration + BGM looped, fade in/out) ...")
narr_dur = float(subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
     "-of", "default=nw=1:nk=1", NARRATION],
    capture_output=True, text=True, check=True).stdout.strip())

main_with_bgm = os.path.join(WORK, "main_with_bgm_v2.mp3")
subprocess.run([
    "ffmpeg", "-y",
    "-stream_loop", "-1", "-i", BGM,
    "-i", NARRATION,
    "-filter_complex",
    f"[0]volume={MAIN_BGM_VOL},afade=t=in:st=0:d={BGM_FADE_IN}[bgm];"
    f"[1][bgm]amix=inputs=2:duration=first:normalize=0,"
    f"afade=t=out:st={narr_dur - BGM_FADE_OUT:.2f}:d={BGM_FADE_OUT}[out]",
    "-map", "[out]",
    "-c:a", "libmp3lame", "-b:a", "128k", "-ar", "24000",
    main_with_bgm,
], check=True, capture_output=True)

# --- Step 3: concat ---
print("[3/3] Concat ...")
concat_list = os.path.join(WORK, "concat_v2.txt")
with open(concat_list, "w") as f:
    f.write(f"file '{title_padded}'\n")
    f.write(f"file '{main_with_bgm}'\n")

subprocess.run([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
    "-c:a", "libmp3lame", "-b:a", "128k", "-ar", "24000",
    FINAL,
], check=True, capture_output=True)

# --- Chapters ---
intro_dur_ms = int(float(subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
     "-of", "default=nw=1:nk=1", title_padded],
    capture_output=True, text=True, check=True).stdout.strip()) * 1000)

with open(JSON_OUT, "r", encoding="utf-8") as f:
    data = json.load(f)

# Remove any existing "intro" chapter, keep only the 12 narration chapters
orig = [c for c in data["chapters"] if c["id"] != "intro"]
# If previous version left chapters shifted by old intro, re-normalize:
# Detect if chapters are shifted (first chapter start_ms != 0)
if orig and orig[0]["start_ms"] != 0:
    offset = orig[0]["start_ms"]
    orig = [{**c, "start_ms": c["start_ms"]-offset, "end_ms": c["end_ms"]-offset} for c in orig]

# Apply new intro offset
shifted = []
for ch in orig:
    new_start = ch["start_ms"] + intro_dur_ms
    new_end = ch["end_ms"] + intro_dur_ms
    shifted.append({
        "id": ch["id"],
        "title": ch["title"],
        "start_ms": new_start,
        "end_ms": new_end,
        "start_label": f"{new_start//1000//60}:{(new_start//1000)%60:02d}",
    })

intro_chapter = {
    "id": "intro",
    "title": "タイトルコール",
    "start_ms": 0,
    "end_ms": intro_dur_ms,
    "start_label": "0:00",
}
new_chapters = [intro_chapter] + shifted

total_ms = int(float(subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
     "-of", "default=nw=1:nk=1", FINAL],
    capture_output=True, text=True, check=True).stdout.strip()) * 1000)

with open(JSON_OUT, "w", encoding="utf-8") as f:
    json.dump({
        "date": "2026-04-16",
        "total_ms": total_ms,
        "total_label": f"{total_ms//1000//60}:{(total_ms//1000)%60:02d}",
        "chapters": new_chapters,
    }, f, ensure_ascii=False, indent=2)

try:
    tags = ID3(FINAL)
except Exception:
    tags = ID3()
tags.delall("CHAP"); tags.delall("CTOC")
for ch in new_chapters:
    tags.add(CHAP(
        element_id=ch["id"], start_time=ch["start_ms"], end_time=ch["end_ms"],
        start_offset=0xFFFFFFFF, end_offset=0xFFFFFFFF,
        sub_frames=[TIT2(encoding=3, text=[ch["title"]])],
    ))
tags.add(CTOC(
    element_id="toc", flags=CTOCFlags.TOP_LEVEL | CTOCFlags.ORDERED,
    child_element_ids=[ch["id"] for ch in new_chapters],
    sub_frames=[TIT2(encoding=3, text=["目次"])],
))
tags.add(TIT2(encoding=3, text=["Atlas Morning Brief 2026-04-16"]))
tags.save(FINAL)

print(f"\n完成: {FINAL}")
print(f"  全長: {total_ms//1000//60}:{(total_ms//1000)%60:02d}")
print(f"  サイズ: {os.path.getsize(FINAL)/1024/1024:.2f} MB")
print(f"  タイトルコール長: {intro_dur_ms/1000:.2f}s")
print(f"  チャプター数: {len(new_chapters)}")
