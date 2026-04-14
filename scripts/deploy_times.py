#!/usr/bin/env python3
"""
deploy_times.py
===============
U&I株倶楽部新聞（朝刊・号外）をGitHub Pagesにデプロイし、
LINE U&I株倶楽部グループに自動通知するスクリプト。

使い方:
  # 朝刊
  python3 deploy_times.py morning <HTMLパス> <YYYY-MM-DD> "<見出し>"

  # 号外
  python3 deploy_times.py extra <HTMLパス> <YYYY-MM-DD> <スラッグ> "<見出し>"

オプション:
  --line    LINE通知を送信する（デフォルトはOFF）

例:
  python3 deploy_times.py morning ~/Desktop/UI_KabuClub_HP/morning_20260318.html 2026-03-18 "NVIDIA GTC効果で反発、本日FOMC"
  python3 deploy_times.py morning ~/Desktop/UI_KabuClub_HP/morning_20260318.html 2026-03-18 "見出し" --line
  python3 deploy_times.py extra ~/Desktop/UI_KabuClub_HP/gogai_gtc2026.html 2026-03-17 gtc-2026 "NVIDIA GTC 2026 完全レポート"
"""

import sys, os, shutil, subprocess, json, re
from datetime import datetime
try:
    import urllib.request as urlreq
    import urllib.error
except ImportError:
    pass

REPO_DIR        = os.path.expanduser("~/ui-kabu-times")
PAGES_BASE_URL  = "https://atlas-financials.jp/news"
LINE_CONFIG     = os.path.expanduser("~/.line_config")

WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]


# ─────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────
def run(cmd, cwd=None):
    result = subprocess.run(cmd, shell=True, cwd=cwd or REPO_DIR,
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"コマンド失敗: {cmd}\n{result.stderr}")
    return result.stdout.strip()


def load_line_config():
    config = {}
    if not os.path.exists(LINE_CONFIG):
        return config
    with open(LINE_CONFIG) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                config[k.strip()] = v.strip()
    return config


def send_line(token, group_id, message, max_retries=3):
    import time
    data = json.dumps({
        "to": group_id,
        "messages": [{"type": "text", "text": message}]
    }).encode("utf-8")
    for attempt in range(1, max_retries + 1):
        req = urlreq.Request(
            "https://api.line.me/v2/bot/message/push",
            data=data,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        try:
            with urlreq.urlopen(req, timeout=10) as res:
                return res.status == 200
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries:
                wait = int(e.headers.get("Retry-After", 5 * attempt))
                print(f"  ⏳ レート制限（429）。{wait}秒後にリトライ ({attempt}/{max_retries})...")
                time.sleep(wait)
            else:
                print(f"⚠️  LINE送信エラー: {e}")
                return False
        except Exception as e:
            print(f"⚠️  LINE送信エラー: {e}")
            return False
    return False


def extract_headline(html_path):
    """HTMLから見出しを抽出（複数パターンにフォールバック）"""
    try:
        with open(html_path, encoding="utf-8") as f:
            content = f.read(30000)
        # 0. extra-headline メタタグ（号外用の短い見出し、最優先）
        m = re.search(r'name="extra-headline"\s+content="([^"]+)"', content)
        if m:
            return m.group(1).strip()[:80]
        # 1. summary-topic（朝刊マーケットサマリーの見出し）
        m = re.search(r'class="summary-topic[^"]*">(.*?)</span>', content)
        if m:
            return re.sub(r'<[^>]+>', '', m.group(1)).strip()
        # 2. top-story-title（朝刊TOP STORY）
        m = re.search(r'class="top-story-title">(.*?)</h2>', content, re.DOTALL)
        if m:
            return re.sub(r'<[^>]+>', '', m.group(1)).strip()[:80]
        # 3. og:description（OGPメタタグ）
        m = re.search(r'og:description"\s+content="([^"]+)"', content)
        if m:
            return m.group(1).strip()[:80]
        # 4. og:title から「—」以降を抽出（例: "号外 — NVIDIA GTC 2026 特集"）
        m = re.search(r'og:title"\s+content="[^"]*—\s*([^"]+)"', content)
        if m:
            return m.group(1).strip()[:80]
        # 5. <title>タグから「—」以降を抽出
        m = re.search(r'<title>[^<]*—\s*([^<]+)</title>', content)
        if m:
            return m.group(1).strip()[:80]
    except Exception:
        pass
    return ""


# ─────────────────────────────────────────
# latest.html updaters
# ─────────────────────────────────────────
def update_morning_latest(date_obj):
    y = date_obj.strftime("%Y")
    m = date_obj.strftime("%m")
    d = str(date_obj.day)
    rel = f"{y}/{m}/{d}.html"
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="0;url={rel}">
<title>U&amp;I株倶楽部新聞 朝刊 - 最新号</title>
</head>
<body>
<p>最新号にリダイレクトしています... <a href="{rel}">こちらをクリック</a></p>
</body>
</html>
"""
    with open(os.path.join(REPO_DIR, "morning", "latest.html"), "w", encoding="utf-8") as f:
        f.write(html)


def update_extra_latest(date_obj, slug):
    y = date_obj.strftime("%Y")
    m = date_obj.strftime("%m")
    d = str(date_obj.day)
    rel = f"{y}/{m}/{d}-{slug}.html"
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta http-equiv="refresh" content="0;url={rel}">
<title>U&amp;I株倶楽部新聞 号外 - 最新号</title>
</head>
<body>
<p>最新号にリダイレクトしています... <a href="{rel}">こちらをクリック</a></p>
</body>
</html>
"""
    with open(os.path.join(REPO_DIR, "extra", "latest.html"), "w", encoding="utf-8") as f:
        f.write(html)


# ─────────────────────────────────────────
# Portal index.html updater
# ─────────────────────────────────────────
def scan_articles(section_dir, article_type):
    """指定ディレクトリ内の全記事をスキャンして (date, rel_path, headline, type) のリストを返す"""
    articles = []
    base = os.path.join(REPO_DIR, section_dir)

    if article_type == "special":
        # special/*.html — 階層なし、mtimeから日付取得
        for fname in os.listdir(base):
            if not fname.endswith(".html") or fname in ("index.html", "latest.html"):
                continue
            fpath = os.path.join(base, fname)
            rel = os.path.relpath(fpath, REPO_DIR)
            try:
                mtime = os.path.getmtime(fpath)
                dt = datetime.fromtimestamp(mtime).replace(hour=0, minute=0, second=0, microsecond=0)
                headline = extract_headline(fpath)
                if not headline:
                    # ファイル名からスラッグを整形（ハイフン→スペース、.html除去）
                    headline = fname.replace(".html", "").replace("-", " ").replace("_", " ")
                articles.append((dt, rel, headline, article_type))
            except Exception:
                pass
    else:
        for root, dirs, files in os.walk(base):
            for fname in files:
                if not fname.endswith(".html") or fname in ("index.html", "latest.html"):
                    continue
                fpath = os.path.join(root, fname)
                rel = os.path.relpath(fpath, REPO_DIR)
                # 多言語版（-en/-ko/-zh）はスキップ
                stem = fname.replace(".html", "")
                if stem.endswith(("-en", "-ko", "-zh")):
                    continue
                # parse date from path: YYYY/MM/{file}.html
                parts = os.path.relpath(fpath, base).replace("\\", "/").split("/")
                if len(parts) == 3:
                    try:
                        y, m = int(parts[0]), int(parts[1])
                        if article_type == "morning":
                            d = int(parts[2].replace(".html", ""))
                        else:
                            d = int(parts[2].split("-")[0])
                        dt = datetime(y, m, d)
                        headline = extract_headline(fpath)
                        articles.append((dt, rel, headline, article_type))
                    except (ValueError, IndexError):
                        pass

    articles.sort(key=lambda x: x[0], reverse=True)
    return articles


def rebuild_portal_index():
    """ポータルindex.htmlの統合アーカイブリストを更新"""
    index_path = os.path.join(REPO_DIR, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 3種類を統合して日付降順ソート
    all_articles = []
    all_articles += scan_articles("morning", "morning")
    all_articles += scan_articles("extra", "extra")
    all_articles += scan_articles("special", "special")
    all_articles.sort(key=lambda x: x[0], reverse=True)

    # archive-list の各 article-item を生成
    items_html = ""
    for dt, rel, headline, atype in all_articles:
        date_iso = dt.strftime("%Y-%m-%d")
        month_key = dt.strftime("%Y/%m")
        title = headline if headline else f"{dt.month}月{dt.day}日の{atype}"
        # エスケープ
        title_escaped = (title.replace("&", "&amp;").replace('"', "&quot;")
                             .replace("<", "&lt;").replace(">", "&gt;"))
        items_html += (
            f'      <a class="article-item" href="{rel}"'
            f' data-type="{atype}"'
            f' data-date="{date_iso}"'
            f' data-month="{month_key}"'
            f' data-title="{title_escaped}"></a>\n'
        )

    archive_block = (
        '    <div class="archive-list" id="archiveList">\n'
        + items_html
        + '    </div>'
    )

    # <!-- Archive --> アンカーで囲まれた archive-list を置換
    content = re.sub(
        r'<!-- Archive -->\s*<div class="archive-list" id="archiveList">.*?</div>',
        '<!-- Archive -->\n    ' + archive_block,
        content, count=1, flags=re.DOTALL
    )

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(content)


# ─────────────────────────────────────────
# Main
# ─────────────────────────────────────────
def main():
    if len(sys.argv) < 4:
        print("使い方:")
        print('  python3 deploy_times.py morning <HTMLパス> <YYYY-MM-DD> "<見出し>"')
        print('  python3 deploy_times.py extra <HTMLパス> <YYYY-MM-DD> <スラッグ> "<見出し>"')
        print('  python3 deploy_times.py special <HTMLパス> <スラッグ> "<見出し>"')
        sys.exit(1)

    # --line フラグの検出（どの位置にあっても対応）
    send_line_flag = "--line" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--line"]

    article_type = args[0] if len(args) > 0 else ""
    html_path = os.path.abspath(args[1]) if len(args) > 1 else ""

    if article_type == "special":
        # special: python3 deploy_times.py special <HTML> <slug> "<headline>"
        slug = args[2] if len(args) > 2 else os.path.basename(html_path).replace(".html", "")
        headline = args[3] if len(args) > 3 else ""
        date_str = None
        date_obj = datetime.now()
    elif article_type == "extra":
        date_str = args[2] if len(args) > 2 else ""
        slug = args[3] if len(args) > 3 else "special"
        headline = args[4] if len(args) > 4 else ""
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    else:
        date_str = args[2] if len(args) > 2 else ""
        slug = None
        headline = args[3] if len(args) > 3 else ""
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")

    if not os.path.exists(html_path):
        print(f"❌ ファイルが見つかりません: {html_path}")
        sys.exit(1)

    y = date_obj.strftime("%Y")
    m = date_obj.strftime("%m")
    d = str(date_obj.day)
    weekday = WEEKDAYS[date_obj.weekday()]

    if article_type == "morning":
        type_label = "朝刊"
        type_icon = "📰"
    elif article_type == "extra":
        type_label = "号外"
        type_icon = "🔴"
    else:
        type_label = "特集"
        type_icon = "📑"

    print(f"{type_icon} U&I株倶楽部新聞 {type_label}デプロイ")
    if article_type != "special":
        print(f"   日付: {y}年{int(m)}月{d}日（{weekday}）")
    if slug:
        print(f"   スラッグ: {slug}")
    print()

    # 0. ブランチチェック（gh-pages以外なら中断）
    current_branch = run("git rev-parse --abbrev-ref HEAD", cwd=REPO_DIR)
    if current_branch != "gh-pages":
        print(f"❌ エラー: 現在のブランチが '{current_branch}' です。'gh-pages' に切り替えてください。")
        print(f"   → cd {REPO_DIR} && git checkout gh-pages")
        sys.exit(1)

    # 1. HTMLをコピー
    if article_type == "morning":
        dest_dir = os.path.join(REPO_DIR, "morning", y, m)
        fname = f"{d}.html"
    elif article_type == "special":
        dest_dir = os.path.join(REPO_DIR, "special")
        fname = f"{slug}.html"
    else:
        dest_dir = os.path.join(REPO_DIR, "extra", y, m)
        fname = f"{d}-{slug}.html"

    os.makedirs(dest_dir, exist_ok=True)
    dest_file = os.path.join(dest_dir, fname)
    shutil.copy2(html_path, dest_file)
    if article_type == "special":
        print(f"1️⃣  HTMLをコピー → special/{fname}")
    else:
        print(f"1️⃣  HTMLをコピー → {article_type}/{y}/{m}/{fname}")

    # 3. latest.html 更新
    if article_type == "morning":
        update_morning_latest(date_obj)
        print(f"2️⃣  {article_type}/latest.html を更新")
    elif article_type == "extra":
        update_extra_latest(date_obj, slug)
        print(f"2️⃣  {article_type}/latest.html を更新")
    else:
        print("2️⃣  special は latest.html なし（スキップ）")

    # 4. ポータルindex.html 再構築
    rebuild_portal_index()
    print("3️⃣  ポータル index.html を再構築")

    # 5. Cloudflare Pages にデプロイ
    print("4️⃣  Cloudflare Pages にデプロイ...")
    run(f"npx wrangler pages deploy {REPO_DIR} --project-name atlas-news --commit-dirty=true", cwd=REPO_DIR)
    print("   ✅ Cloudflare Pages にデプロイ完了")

    # 6. Gitにもコミット（バックアップ・履歴管理用）
    commit_msg = f"{type_icon} {type_label} {y}/{int(m)}/{d}（{weekday}）"
    if slug:
        commit_msg += f" {slug}"
    try:
        run("git add -A", cwd=REPO_DIR)
        run(f'git commit -m "{commit_msg}"', cwd=REPO_DIR)
        run("git push", cwd=REPO_DIR)
    except Exception as e:
        print(f"   ⚠️ Git push スキップ（Cloudflareデプロイは成功済み）: {e}")

    # 7. LINE通知
    if not send_line_flag:
        print("5️⃣  LINE通知... スキップ（--line フラグなし）")
    else:
        print("5️⃣  LINE通知...")
    line_cfg = load_line_config() if send_line_flag else {}
    token = line_cfg.get("LINE_TOKEN")
    group_id = line_cfg.get("LINE_GROUP_ID")

    if send_line_flag and token and group_id:
        if article_type == "special":
            url = f"{PAGES_BASE_URL}/special/{fname}"
        else:
            url = f"{PAGES_BASE_URL}/{article_type}/{y}/{m}/{fname}"
        now_str = datetime.now().strftime("%Y/%m/%d %H:%M")
        msg = f"{type_icon} 【U&I株倶楽部 {type_label}】{y}年{int(m)}月{d}日（{weekday}）\n"
        if headline:
            msg += f"💬 {headline}\n"
        msg += (
            f"\n"
            f"🔗 {type_label}はこちら:\n"
            f"{url}\n"
            f"\n"
            f"🏠 新聞ポータル:\n"
            f"{PAGES_BASE_URL}/\n"
            f"\n"
            f"({now_str} 自動配信)"
        )
        ok = send_line(token, group_id, msg)
        if ok:
            print("   ✅ LINE通知 送信完了")
        else:
            print("   ⚠️  LINE通知 送信失敗（記事は公開済み）")
    elif send_line_flag:
        print("   ⚠️  LINE設定が見つかりません（スキップ）")

    print()
    if article_type == "special":
        url = f"{PAGES_BASE_URL}/special/{fname}"
    else:
        url = f"{PAGES_BASE_URL}/{article_type}/{y}/{m}/{fname}"
    print(f"🎉 デプロイ完了!")
    print(f"   📎 {url}")


if __name__ == "__main__":
    main()
