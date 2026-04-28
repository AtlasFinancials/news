#!/usr/bin/env python3
"""
Atlas Morning Brief — 2026年4月16日 ラジオ版生成
- ja-JP-Neural2-C（男性・低めで温かみ）
- speaking_rate=1.12
- セクション別にTTS→連結、ID3v2 CHAPでチャプター埋め込み、JSON出力
"""
import json, os, subprocess, sys

# Cloudflare/Claude Code 環境での DNS 解決罠回避
os.environ.setdefault("GRPC_DNS_RESOLVER", "native")
from google.cloud import texttospeech
from mutagen.id3 import ID3, CHAP, CTOC, TIT2, CTOCFlags

OUT_DIR = "/Users/yskzz121/ui-kabu-times/morning/2026/04"
WORK_DIR = os.path.join(OUT_DIR, "audio_work_16")
FINAL_MP3 = os.path.join(OUT_DIR, "16.mp3")
CHAPTERS_JSON = os.path.join(OUT_DIR, "16-chapters.json")

SECTIONS = [
    ("opening", "オープニング", """
Atlas Morning Brief、2026年4月16日木曜日、ニュースラジオ版です。
本日のハイライトは3つ。
1つめ、S&P500が史上初めて、終値で7,000の大台を突破。連騰相場が、記録更新を続けています。
2つめ、モルガン・スタンレーとバンク・オブ・アメリカの銀行決算が、揃って市場予想を大きく上回るダブルビート。
3つめ、テスラがAI5チップのタペアウト、つまり設計完了を発表し、株価は8%の急伸です。
およそ13分で、昨夜の米国市場を、丸ごとお届けします。
"""),

    ("market_summary", "マーケット・サマリー", """
まずは昨夜の米国市場のサマリーです。
主要3指数のうち、2指数が記録更新となりました。
S&P500は0.80%上昇し、7,022.95。終値ベースで、初めて7,000の大台を突破しました。
NASDAQ総合は1.59%上昇の24,016.02で、連騰は11日目。2021年以来、最長の上昇記録に迫る勢いです。
一方、ダウは48,463.72と0.15%の小幅下落。キャタピラーの5%安が、指数の重しとなりました。
セクター別に見ると、半導体が2.8%、テクノロジーが2.1%、一般消費財が1.6%と、グロース主導の明確な買い。
対照的に、資本財はキャタピラー安で1.1%マイナス、エネルギーは0.6%マイナスと、景気敏感株の一部で弱さが出ました。
リスクメーターは、100点満点中36点。黄色、注意圏です。
VIX恐怖指数は18.36と、落ち着いた水準。しかし、テールリスクを測るSKEW指数は145と高止まりしており、「沈黙の危機」シグナルが点灯しています。
相場が記録を更新する局面で、機関投資家が水面下で保険を積み増している。この構図は、歴史的には注目すべきパターンです。
"""),

    ("news_sp7000", "ヘッドライン1　S&P500、史上初の7,000突破", """
ここからは、注目ニュースを6本、お届けします。
1本目。S&P500が、終値ベースで史上初めて7,000の大台を突破しました。
3月下旬のイラン戦争開戦時、指数は6,250付近まで急落。そこから、およそ2週間で11%超の急反発を遂げ、7,022.95まで回復しています。
NASDAQは連騰11日目で、2021年以来の最長記録に接近。
トランプ大統領は「イラン戦争は、終わりに近い」と発言。パキスタン仲介の第2ラウンド和平協議が、数日内に再開する見通しです。
記録更新の背景には、地政学リスクの後退、銀行決算の強さ、AI半導体サイクルの加速、この3つの追い風が同時に発火した構図があります。
ただし、SKEW指数145の高止まりは、プロが静かに下方リスクに備えている証拠でもあります。
勢いに乗るのか、ヘッジを厚くするのか。投資家の判断が問われる局面です。
"""),

    ("news_ms", "ヘッドライン2　モルガン・スタンレー、四半期売上初の200億ドル突破", """
2本目。モルガン・スタンレーの第1四半期決算です。
総売上高は206億ドル。モルガン・スタンレーとしては、四半期売上高が初めて200億ドルを突破しました。
EPS1株利益は3ドル43セント。市場予想の3ドル2セントを大きく上回る、ダブルビート決算です。
特に注目すべきは、株式トレーディング収益。25%増の51.5億ドルで、過去15年間で最高の数字を記録しました。
投資銀行収益も36%急増。2022年以降、冬の時代が続いていたM&Aおよび株式発行サイクルが、本格的に復活している証拠です。
ウェルスマネジメント部門も16%増の85.2億ドルで、過去最高を更新。
ROTCE、つまり有形自己資本利益率は27.1%と、極めて高い資本効率を示しました。
株価は5%以上、上昇しています。
"""),

    ("news_bac", "ヘッドライン3　バンク・オブ・アメリカ、純利益86億ドルで約20年ぶり高水準", """
3本目。バンク・オブ・アメリカの第1四半期決算です。
EPSは1ドル11セントで、予想の1ドルを上回り。売上高は304.3億ドルで、予想の299.3億ドルを超過。純利益は86億ドルと、前年同期比17%の増加で、約20年ぶりの高水準となりました。
こちらも、株式トレーディング部門が30%増の28.3億ドルで、事前のStreetAccount予想を3.5億ドル上回る好成績。投資銀行も21%増の18億ドル。
ただし、債券トレーディングは、コンセンサスを3.3億ドル下回るミスとなっています。
モルガン・スタンレーとバンク・オブ・アメリカ。両社揃ってのダブルビートは、「金融セクターは2025年下期の関税不況を乗り切った」ことを、明確に示しました。
株価は2.5%上昇です。
"""),

    ("news_tesla", "ヘッドライン4　テスラ、AI5チップ・タペアウト完了", """
4本目。テスラのAI5チップです。
CEOのイーロン・マスク氏は15日、次世代AI推論チップ「AI5」のタペアウトを発表しました。タペアウトとは、設計が完了し、量産準備に入ったことを意味します。
前世代のHW4と比較して、演算性能は8倍から10倍。メモリは192GBと、9倍に増強。メモリ帯域も5倍です。
マスク氏は「AI5チップ1つで、Nvidia H100 GPU相当の性能」と主張しました。
量産は、2027年中盤から後半の予定。用途は、ヒト型ロボットOptimusと、スーパーコンピューター・クラスターが中心です。
株価は、8%の急伸。テスラは、過去2週間で急反発局面入りしました。
Nvidiaも、AIインフラ投資期待を背景に、11営業日連続の上昇で、記録を更新中です。
"""),

    ("news_sec", "ヘッドライン5　SEC、デイトレード2万5000ドル規則を撤廃", """
5本目。規制面での、大きな転換点です。
SEC米国証券取引委員会は14日、25年以上続いたパターンデイトレーダー規則、通称PDTルールを撤廃しました。
従来は、5営業日以内に4回以上のデイトレードを行う場合、口座に2万5000ドル以上の維持証拠金が必要でした。
新しい規制では、「実際の日中エクスポージャーに応じた証拠金」モデルに移行。最低口座額は2,000ドルから可能となり、小口個人投資家の参入障壁が大幅に下がります。
これを受けて、Robinhood株は10%の急伸。Webullも9%を超える上昇です。
個人投資家向けのオプション取引、信用取引の裾野が一気に広がる可能性があり、ブローカー各社にとっては、構造的な追い風となります。
"""),

    ("news_asml", "ヘッドライン6　ASML、通期ガイダンスを上方修正", """
6本目。オランダの半導体露光装置大手、ASMLの第1四半期決算です。
売上高は88億ユーロで、予想の85億ユーロを上回り。純利益は28億ユーロで、予想の25億ユーロを超過。粗利益率は53.0%と、ガイダンスの上限に届きました。
そして、最大の注目は、2026年通期売上ガイダンス。
従来の340億ユーロから、360億ユーロから400億ユーロのレンジに、上方修正しました。差分にして、プラス20億ユーロから60億ユーロの引き上げです。
中国向け規制強化の逆風はあるものの、AI用EUV露光装置の需要の強さが、全体を牽引しています。
本日16日には、半導体受託製造最大手のTSMCが、第1四半期決算を発表予定。コンセンサス売上は352億ドル、EPSは2ドル47セント。
ASMLの強気ガイダンスが、TSMCの決算でもさらに裏付けられるか。ここが、本日の最大の注目点です。
"""),

    ("risk_meter", "Atlasリスクメーター　沈黙の危機シグナル点灯", """
Atlasリスクメーターの解説です。
本日の総合スコアは、36点。黄色、注意圏です。
VIX恐怖指数は18.36と、落ち着いた水準。スコアは28。
10年債2年債のイールドカーブは、プラス0.45%の順イールド。スコアは28。
10年債利回りは4.12%で、スコア42。
EPSリビジョンは、銀行決算の好調を受けて、やや上方修正。スコアは20と低めです。
Fear&Greed Indexは72で、貪欲寄り。スコアは40。
SPXA50R、つまりS&P500構成銘柄のうち、50日移動平均線を上回る銘柄の比率は76%。スコアは55と、やや過熱気味です。
200日移動平均線からの乖離率は、プラス9.5%。スコア38です。
そして最重要。SKEW指数は145と高止まりしており、「沈黙の危機」シグナルが、5つ星の最高警戒レベルで点灯しています。
このシグナルは、VIXが20未満かつSKEWが135超という、矛盾した状態を示します。
表面的には穏やかな相場。しかし、機関投資家は水面下で、テールリスクへのヘッジを積み増している。これが、「沈黙の危機」の正体です。
過去、2018年1月、2020年2月、2022年1月にいずれもこのシグナルが点灯していた事実は、記憶にとどめておくべきです。
"""),

    ("keyword", "今日のキーワード　沈黙の危機", """
今日のキーワードは、「沈黙の危機」。英語では、Silent Distressと呼ばれます。
VIX指数は、現在の恐怖を測る指標です。これに対して、SKEW指数は、S&P500オプションのうち、アウトオブザマネー・プットに対するヘッジ需要を測定します。
SKEWが135を超え、かつVIXが20未満。この矛盾した組み合わせは、「表面的には穏やかだが、機関投資家は水面下で保険を積み増している」という、プロの行動を映し出しています。
過去の前例を挙げます。
2018年1月、ボラマゲドンと呼ばれる大暴落の直前。
2020年2月、新型コロナウイルスによる急落の直前。
2022年1月、年初下落の直前。
いずれも、この「沈黙の危機」シグナルが、点灯していました。
単独では売りシグナルとはなりません。しかし、勢いのある株高と、SKEWの高止まり。この組み合わせは、過去の類似局面で、2週間から4週間後に、5%から10%の調整を引き起こしたケースがあります。
今日の投資家に求められるのは、過度な強気ではなく、ポジションの裾野管理。レバレッジの縮小や、プロテクティブプットの検討を、意識すべき局面です。
"""),

    ("editorial", "編集部の目線　7,000突破の舞台裏", """
ここからは、編集部の目線です。テーマは、「S&P500、7,000突破の舞台裏」。
3月下旬、イラン戦争開戦時、S&P500は6,250付近まで急落しました。そこから、わずか2週間で11%超の急反発を遂げ、終値ベースで7,000を突破。この記録更新の背後には、3つの構造的変化があります。
1つ目は、銀行決算の質。
モルガン・スタンレーとバンク・オブ・アメリカは、どちらもトレーディングと投資銀行の、ダブル・エンジンで予想を大幅に上回りました。「金融セクターは、2025年下期の関税不況を乗り切った」ことの明確な証拠です。特に、投資銀行収益の21%から36%の増加は、2022年以降、冬の時代が続いてきたM&A・ECMサイクルの、本格復活を意味します。
2つ目は、AI半導体サイクルのアクセル。
テスラのAI5タペアウトで、株価は8%急伸。Nvidiaも、AIインフラ投資期待を背景に、11連騰で記録更新。ASMLは、通期ガイダンスを大きく上方修正。本日16日のTSMC決算で、Q1売上が346億から358億ドルのレンジ、中央値を超えれば、AI半導体の2026年下期ピーク論を、先送り、あるいは否定する、強力な証拠となります。
3つ目は、地政学の陰。
イラン和平は「終わりに近い」とされていますが、米海軍のイラン港封鎖は継続中。パキスタン仲介協議は、まだ合意に至っていません。原油は90ドル台で高止まりし、Fed Beige Bookも低所得層の苦境を強調しています。そして、SKEW指数145の高止まり。これは、「相場が記録を更新する局面で、テールヘッジが積み増される」という、典型的な「沈黙の危機」パターンです。
編集部の見解です。本日16日のTSMC、Netflix、UnitedHealthの決算、そして来週以降の米系大手銀行決算、さらにイラン第2ラウンド交渉。このどこかで、今回の記録更新が「本物のブレイクアウト」か、「典型的な期待先行」か、判明します。
向こう3営業日は、「追加買い」よりも「現状確認」のフェーズ。そう見ます。
"""),

    ("closing", "本日の予定とクロージング", """
最後に、本日16日の注目スケジュールです。
日本時間の夜9時半、米国の3月小売売上高、新規失業保険申請件数、そして、フィラデルフィア連銀製造業景況指数が、同時発表されます。消費と労働、製造の3点セットです。
同時に、半導体受託製造最大手TSMCの第1四半期決算が、朝から発表。コンセンサス売上は352億ドル、EPSは2ドル47セント。
市場引け後には、Netflix、UnitedHealthの決算も予定されています。
そして、明日17日金曜日は、Good Fridayで米国株式市場は休場。経済指標の発表も、ありません。
以上、Atlas Morning Brief、2026年4月16日ニュースラジオ版でした。
本日も、良い相場との1日を。
""")
]


def synth_section(client, text, out_path):
    synthesis_input = texttospeech.SynthesisInput(text=text.strip())
    voice = texttospeech.VoiceSelectionParams(
        language_code="ja-JP", name="ja-JP-Neural2-C"
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=1.12,
        pitch=-2.0,
        sample_rate_hertz=24000,
    )
    resp = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    with open(out_path, "wb") as f:
        f.write(resp.audio_content)


def duration_ms(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True,
    )
    return int(float(r.stdout.strip()) * 1000)


def format_time(ms):
    s = ms // 1000
    return f"{s//60:d}:{s%60:02d}"


def main():
    client = texttospeech.TextToSpeechClient()

    section_files = []
    chapters = []
    cursor_ms = 0

    for i, (sid, title, text) in enumerate(SECTIONS):
        part_path = os.path.join(WORK_DIR, f"{i:02d}_{sid}.mp3")
        print(f"[{i+1}/{len(SECTIONS)}] {title}...")
        synth_section(client, text, part_path)
        dur = duration_ms(part_path)
        chapters.append({
            "id": sid,
            "title": title,
            "start_ms": cursor_ms,
            "end_ms": cursor_ms + dur,
            "start_label": format_time(cursor_ms),
        })
        cursor_ms += dur
        section_files.append(part_path)

    concat_list = os.path.join(WORK_DIR, "concat.txt")
    with open(concat_list, "w") as f:
        for p in section_files:
            f.write(f"file '{p}'\n")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
         "-c", "copy", FINAL_MP3],
        check=True, capture_output=True,
    )

    try:
        tags = ID3(FINAL_MP3)
    except Exception:
        tags = ID3()
    tags.delall("CHAP")
    tags.delall("CTOC")
    for ch in chapters:
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
        child_element_ids=[ch["id"] for ch in chapters],
        sub_frames=[TIT2(encoding=3, text=["目次"])],
    ))
    tags.add(TIT2(encoding=3, text=["Atlas Morning Brief 2026-04-16"]))
    tags.save(FINAL_MP3)

    total_ms = cursor_ms
    with open(CHAPTERS_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "date": "2026-04-16",
            "total_ms": total_ms,
            "total_label": format_time(total_ms),
            "chapters": chapters,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n完成: {FINAL_MP3}")
    print(f"  全長: {format_time(total_ms)}")
    print(f"  サイズ: {os.path.getsize(FINAL_MP3)/1024/1024:.1f} MB")
    print(f"  チャプター数: {len(chapters)}")


if __name__ == "__main__":
    main()
