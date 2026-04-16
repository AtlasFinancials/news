#!/usr/bin/env python3
"""
Atlas Morning Brief 16.mp3 にタイトルコール+BGMを合成
- Intro:  [0.0-5.5s]  BGM -6dB (fade in 1s) + Title call @1.2s
- Main:   [5.5s-end]  Main narration + BGM looped @-22dB (last 3s fade out)
- Chapters: 既存12章の開始時刻をintro長だけシフトし、先頭に「イントロ」章を追加
"""
import json, os, subprocess, shutil
from mutagen.id3 import ID3, CHAP, CTOC, TIT2, CTOCFlags

ROOT = "/Users/yskzz121/ui-kabu-times"
WORK = os.path.join(ROOT, "morning/2026/04/audio_work_16")
FINAL = os.path.join(ROOT, "morning/2026/04/16.mp3")
JSON_OUT = os.path.join(ROOT, "morning/2026/04/16-chapters.json")

TITLE = "/Users/yskzz121/Desktop/atlas_radio_bgm_preview/titlev3_rate112.mp3"
BGM = os.path.join(ROOT, "assets/bgm/tropical-bounce.mp3")
MAIN = os.path.join(WORK, "narration_only_backup.mp3")

INTRO_DUR = 5.5       # Intro segment length (seconds)
INTRO_BGM_VOL = 0.55  # ~-5dB during intro
MAIN_BGM_VOL = 0.08   # ~-22dB during main
FADE_OUT_DUR = 3.0    # last N seconds fade

# バックアップ（元の16.mp3をnarration_only_backup.mp3に保存）— 初回のみ
if not os.path.exists(MAIN):
    shutil.copy(FINAL, MAIN)
    print(f"バックアップ作成: {MAIN}")

intro_mp3 = os.path.join(WORK, "intro_titlebgm.mp3")
main_with_bgm = os.path.join(WORK, "main_with_bgm.mp3")

# --- Step 1: intro 作成 (BGM intro + title call) ---
print("[1/3] Intro生成 (title + BGM intro) ...")
subprocess.run([
    "ffmpeg", "-y",
    "-i", TITLE,
    "-i", BGM,
    "-filter_complex",
    f"[0]adelay=1200|1200[titleD];"
    f"[1]atrim=0:{INTRO_DUR},volume={INTRO_BGM_VOL},afade=t=in:st=0:d=1,afade=t=out:st={INTRO_DUR-0.5}:d=0.5[bgmIntro];"
    f"[bgmIntro][titleD]amix=inputs=2:duration=first:normalize=0[out]",
    "-map", "[out]",
    "-c:a", "libmp3lame", "-b:a", "128k", "-ar", "24000",
    intro_mp3,
], check=True, capture_output=True)

# --- Step 2: main_with_bgm 作成 (narration + BGM looped) ---
print("[2/3] Main合成 (narration + BGM looped) ...")
# get main dur
main_dur = float(subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
     "-of", "default=nw=1:nk=1", MAIN],
    capture_output=True, text=True, check=True).stdout.strip())

# BGM loop with volume, fade out last 3s, pad to main_dur
subprocess.run([
    "ffmpeg", "-y",
    "-stream_loop", "-1", "-i", BGM,
    "-i", MAIN,
    "-filter_complex",
    f"[0]volume={MAIN_BGM_VOL}[bgmLoop];"
    f"[1][bgmLoop]amix=inputs=2:duration=first:normalize=0,"
    f"afade=t=out:st={main_dur - FADE_OUT_DUR:.2f}:d={FADE_OUT_DUR}[out]",
    "-map", "[out]",
    "-c:a", "libmp3lame", "-b:a", "128k", "-ar", "24000",
    main_with_bgm,
], check=True, capture_output=True)

# --- Step 3: intro + main concat ---
print("[3/3] Concat ...")
concat_list = os.path.join(WORK, "concat_final.txt")
with open(concat_list, "w") as f:
    f.write(f"file '{intro_mp3}'\n")
    f.write(f"file '{main_with_bgm}'\n")

# Use re-encode for safer concat (different encoding params possible)
subprocess.run([
    "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
    "-c:a", "libmp3lame", "-b:a", "128k", "-ar", "24000",
    FINAL,
], check=True, capture_output=True)

# --- Step 4: chapters 更新 ---
print("Chapters更新中...")
# Load existing chapters
with open(JSON_OUT, "r", encoding="utf-8") as f:
    data = json.load(f)

# intro実長を取得
intro_dur_ms = int(float(subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
     "-of", "default=nw=1:nk=1", intro_mp3],
    capture_output=True, text=True, check=True).stdout.strip()) * 1000)

# 既存章を intro_dur_ms だけシフト
shifted = []
for ch in data["chapters"]:
    shifted.append({
        "id": ch["id"],
        "title": ch["title"],
        "start_ms": ch["start_ms"] + intro_dur_ms,
        "end_ms": ch["end_ms"] + intro_dur_ms,
        "start_label": f"{(ch['start_ms'] + intro_dur_ms) // 1000 // 60}:{((ch['start_ms'] + intro_dur_ms) // 1000) % 60:02d}",
    })

# 先頭に「イントロ」章を追加
intro_chapter = {
    "id": "intro",
    "title": "イントロ",
    "start_ms": 0,
    "end_ms": intro_dur_ms,
    "start_label": "0:00",
}
new_chapters = [intro_chapter] + shifted

# Final total
total_ms = int(float(subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
     "-of", "default=nw=1:nk=1", FINAL],
    capture_output=True, text=True, check=True).stdout.strip()) * 1000)

# JSON出力
with open(JSON_OUT, "w", encoding="utf-8") as f:
    json.dump({
        "date": "2026-04-16",
        "total_ms": total_ms,
        "total_label": f"{total_ms // 1000 // 60}:{(total_ms // 1000) % 60:02d}",
        "chapters": new_chapters,
    }, f, ensure_ascii=False, indent=2)

# ID3チャプター再埋め込み
try:
    tags = ID3(FINAL)
except Exception:
    tags = ID3()
tags.delall("CHAP")
tags.delall("CTOC")
for ch in new_chapters:
    tags.add(CHAP(
        element_id=ch["id"],
        start_time=ch["start_ms"],
        end_time=ch["end_ms"],
        start_offset=0xFFFFFFFF,
        end_offset=0xFFFFFFFF,
        sub_frames=[TIT2(encoding=3, text=[ch["title"]])],
    ))
tags.add(CTOC(
    element_id="toc",
    flags=CTOCFlags.TOP_LEVEL | CTOCFlags.ORDERED,
    child_element_ids=[ch["id"] for ch in new_chapters],
    sub_frames=[TIT2(encoding=3, text=["目次"])],
))
tags.add(TIT2(encoding=3, text=["Atlas Morning Brief 2026-04-16"]))
tags.save(FINAL)

print(f"\n完成: {FINAL}")
print(f"  全長: {total_ms // 1000 // 60}:{(total_ms // 1000) % 60:02d}")
print(f"  サイズ: {os.path.getsize(FINAL)/1024/1024:.2f} MB")
print(f"  チャプター数: {len(new_chapters)}")
print(f"  Intro長: {intro_dur_ms/1000:.2f}s")
