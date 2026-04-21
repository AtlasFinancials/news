#!/usr/bin/env python3
"""
構成 v5（ジングル+タイトル重ね）:
  [0:00-2.0s]   ジングル単独
  [2.0s-5.12s]  ジングル + タイトルコール重ね
  [5.12-5.7s]   ジングル余韻のみ
  [5.7-6.0s]    無音 0.3秒
  [6.0s - END]  本編ナレーション + BGM -22dB ループ（末尾3秒フェードアウト）
"""
import json, os, subprocess
from mutagen.id3 import ID3, CHAP, CTOC, TIT2, CTOCFlags

ROOT = "/Users/yskzz121/ui-kabu-times"
WORK = os.path.join(ROOT, "morning/2026/04/audio_work_21")
FINAL = os.path.join(ROOT, "morning/2026/04/21.mp3")
JSON_OUT = os.path.join(ROOT, "morning/2026/04/21-chapters.json")

JINGLE = os.path.join(ROOT, "assets/bgm/jingle_trimmed.mp3")
TITLE = os.path.join(ROOT, "assets/bgm/titlecall.mp3")
BGM = os.path.join(ROOT, "assets/bgm/tropical-bounce.mp3")
NARRATION = os.path.join(WORK, "narration_only_backup.mp3")

TITLE_OFFSET = 2.0
GAP_AFTER_INTRO = 0.3
JINGLE_GAIN_DB = -4
TITLE_GAIN_DB = +5
MAIN_BGM_VOL = 0.08
BGM_FADE_IN = 2.0
BGM_FADE_OUT = 3.0

def dur(p):
    return float(subprocess.run(
        ["ffprobe","-v","error","-show_entries","format=duration",
         "-of","default=nw=1:nk=1",p],
        capture_output=True, text=True, check=True).stdout.strip())

print("[1/3] Intro生成 (jingle + title overlap at 2.0s) ...")
jingle_len = dur(JINGLE)
intro_mp3 = os.path.join(WORK, "intro_overlap.mp3")
subprocess.run([
    "ffmpeg", "-y",
    "-i", JINGLE,
    "-i", TITLE,
    "-filter_complex",
    f"[0]volume={JINGLE_GAIN_DB}dB[jAdj];"
    f"[1]volume={TITLE_GAIN_DB}dB,adelay={int(TITLE_OFFSET*1000)}|{int(TITLE_OFFSET*1000)}[titleDel];"
    f"[jAdj][titleDel]amix=inputs=2:duration=longest:normalize=0,"
    f"apad=pad_dur={GAP_AFTER_INTRO}[out]",
    "-map","[out]",
    "-c:a","libmp3lame","-b:a","128k","-ar","24000",
    intro_mp3,
], check=True, capture_output=True)

print("[2/3] Main合成 (narration + BGM looped) ...")
narr_dur = dur(NARRATION)
main_with_bgm = os.path.join(WORK, "main_with_bgm_v5.mp3")
subprocess.run([
    "ffmpeg","-y",
    "-stream_loop","-1","-i", BGM,
    "-i", NARRATION,
    "-filter_complex",
    f"[0]volume={MAIN_BGM_VOL},afade=t=in:st=0:d={BGM_FADE_IN}[bgm];"
    f"[1][bgm]amix=inputs=2:duration=first:normalize=0,"
    f"afade=t=out:st={narr_dur - BGM_FADE_OUT:.2f}:d={BGM_FADE_OUT}[out]",
    "-map","[out]",
    "-c:a","libmp3lame","-b:a","128k","-ar","24000",
    main_with_bgm,
], check=True, capture_output=True)

print("[3/3] Concat ...")
concat_list = os.path.join(WORK, "concat_v5.txt")
with open(concat_list, "w") as f:
    f.write(f"file '{intro_mp3}'\n")
    f.write(f"file '{main_with_bgm}'\n")
subprocess.run([
    "ffmpeg","-y","-f","concat","-safe","0","-i",concat_list,
    "-c:a","libmp3lame","-b:a","128k","-ar","24000",
    FINAL,
], check=True, capture_output=True)

intro_dur_ms = int(dur(intro_mp3) * 1000)

with open(JSON_OUT, "r", encoding="utf-8") as f:
    data = json.load(f)
orig = [c for c in data["chapters"] if c["id"] not in ("intro","jingle","title")]
if orig and orig[0]["start_ms"] != 0:
    offset = orig[0]["start_ms"]
    orig = [{**c, "start_ms": c["start_ms"]-offset, "end_ms": c["end_ms"]-offset} for c in orig]

def lbl(ms): return f"{ms//1000//60}:{(ms//1000)%60:02d}"

chapters = [
    {"id":"jingle", "title":"ジングル+タイトルコール",
     "start_ms":0, "end_ms":intro_dur_ms, "start_label":"0:00"},
]
for c in orig:
    s = c["start_ms"] + intro_dur_ms
    e = c["end_ms"] + intro_dur_ms
    chapters.append({
        "id":c["id"], "title":c["title"],
        "start_ms":s, "end_ms":e, "start_label":lbl(s),
    })

total_ms = int(dur(FINAL) * 1000)
with open(JSON_OUT, "w", encoding="utf-8") as f:
    json.dump({
        "date": "2026-04-21",
        "total_ms": total_ms,
        "total_label": lbl(total_ms),
        "chapters": chapters,
    }, f, ensure_ascii=False, indent=2)

try: tags = ID3(FINAL)
except: tags = ID3()
tags.delall("CHAP"); tags.delall("CTOC")
for ch in chapters:
    tags.add(CHAP(
        element_id=ch["id"], start_time=ch["start_ms"], end_time=ch["end_ms"],
        start_offset=0xFFFFFFFF, end_offset=0xFFFFFFFF,
        sub_frames=[TIT2(encoding=3, text=[ch["title"]])],
    ))
tags.add(CTOC(
    element_id="toc", flags=CTOCFlags.TOP_LEVEL | CTOCFlags.ORDERED,
    child_element_ids=[ch["id"] for ch in chapters],
    sub_frames=[TIT2(encoding=3, text=["目次"])],
))
tags.add(TIT2(encoding=3, text=["Atlas Morning Brief 2026-04-21"]))
tags.save(FINAL)

print(f"\n完成: {FINAL}")
print(f"  全長: {lbl(total_ms)}")
print(f"  サイズ: {os.path.getsize(FINAL)/1024/1024:.2f} MB")
print(f"  イントロ: 0:00 - {intro_dur_ms/1000:.2f}s")
print(f"  本編開始: {lbl(intro_dur_ms)}")
print(f"  チャプター数: {len(chapters)}")
