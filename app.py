from flask import Flask, render_template, request
import requests
from datetime import datetime

app = Flask(__name__)

import os
API_KEY = os.environ.get("TIMEQL_API_KEY", "yao_live_8f2fc94a5f349f35b1e076c70d9e284d")
API_URL = "https://api.timeql.com/api/v1/natal_chart"
DEFAULT_LOCATION = "Tokyo"

# ===== 星座・元素データ =====
ELEMENTS = {
    "牡羊座": "火", "獅子座": "火", "射手座": "火",
    "牡牛座": "地", "乙女座": "地", "山羊座": "地",
    "双子座": "風", "天秤座": "風", "水瓶座": "風",
    "蟹座":   "水", "蠍座":   "水", "魚座":   "水",
}
ELEMENT_COMPAT = {
    ("火", "火"): 90, ("火", "風"): 85, ("火", "地"): 45, ("火", "水"): 40,
    ("地", "地"): 90, ("地", "水"): 85, ("地", "火"): 45, ("地", "風"): 40,
    ("風", "風"): 90, ("風", "火"): 85, ("風", "水"): 45, ("風", "地"): 40,
    ("水", "水"): 90, ("水", "地"): 85, ("水", "風"): 45, ("水", "火"): 40,
}

def element_compat(sign_a, sign_b):
    ea = ELEMENTS.get(sign_a, "")
    eb = ELEMENTS.get(sign_b, "")
    if not ea or not eb:
        return 60
    key = (ea, eb) if (ea, eb) in ELEMENT_COMPAT else (eb, ea)
    return ELEMENT_COMPAT.get(key, 60)

# ===== API呼び出し =====
def get_natal_chart(name, birth_date, birth_time):
    dt = datetime.strptime(f"{birth_date} {birth_time}", "%Y%m%d %H:%M")
    iso = dt.strftime("%Y-%m-%dT%H:%M:%S")
    resp = requests.post(
        API_URL,
        headers={"X-API-Key": API_KEY},
        json={"name": name, "datetime": iso, "location": DEFAULT_LOCATION},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()

# ===== 星座・解釈の取得 =====
def extract_sign(chart, planet_key):
    if planet_key == "ascendant":
        for h in chart.get("houses", []):
            if h.get("house") == 1:
                return h.get("sign", "")
        return ""
    for p in chart.get("planets", []):
        if p.get("name") == planet_key:
            return p.get("sign", "")
    return ""

def get_interpretation(chart, planet_key):
    """interpretationsリストから指定惑星のreadingを取得"""
    for item in chart.get("interpretations", {}).get("planets", []):
        if item.get("planet") == planet_key:
            return {
                "title":    item.get("title", ""),
                "reading":  item.get("reading", ""),
                "keywords": item.get("sign_keywords", ""),
            }
    return {}

# ===== 相性スコア計算 =====
def calc_compatibility(chart_a, chart_b):
    sun_a   = extract_sign(chart_a, "sun")
    moon_a  = extract_sign(chart_a, "moon")
    venus_a = extract_sign(chart_a, "venus")
    mars_a  = extract_sign(chart_a, "mars")
    asc_a   = extract_sign(chart_a, "ascendant")

    sun_b   = extract_sign(chart_b, "sun")
    moon_b  = extract_sign(chart_b, "moon")
    venus_b = extract_sign(chart_b, "venus")
    mars_b  = extract_sign(chart_b, "mars")
    asc_b   = extract_sign(chart_b, "ascendant")

    scores = {
        "太陽星座の相性（価値観・生き方）":      element_compat(sun_a,   sun_b),
        "月星座の相性（感情・日常のリズム）":     element_compat(moon_a,  moon_b),
        "金星・火星の相性（恋愛・引き合い）":     element_compat(venus_a, mars_b),
        "アセンダントの相性（第一印象・居心地）": element_compat(asc_a,   asc_b),
    }

    bonus = 0
    if sun_a and sun_a == sun_b:   bonus += 3
    if moon_a and moon_a == moon_b: bonus += 5

    weighted = (
        scores["太陽星座の相性（価値観・生き方）"]      * 0.35 +
        scores["月星座の相性（感情・日常のリズム）"]     * 0.30 +
        scores["金星・火星の相性（恋愛・引き合い）"]     * 0.25 +
        scores["アセンダントの相性（第一印象・居心地）"] * 0.10
    )
    total = min(100, round(weighted + bonus))

    signs = {
        "A": {"sun": sun_a, "moon": moon_a, "venus": venus_a, "mars": mars_a, "ascendant": asc_a},
        "B": {"sun": sun_b, "moon": moon_b, "venus": venus_b, "mars": mars_b, "ascendant": asc_b},
    }
    return total, scores, signs

# ===== 総合コメント =====
def generate_comment(score, signs, name_a, name_b):
    sun_a  = signs["A"]["sun"]  or "不明"
    sun_b  = signs["B"]["sun"]  or "不明"
    moon_a = signs["A"]["moon"] or "不明"
    moon_b = signs["B"]["moon"] or "不明"

    if score >= 85:
        level = "非常に高い"
        summary = (
            f"{name_a}さん（{sun_a}）と{name_b}さん（{sun_b}）は、"
            f"星占い的に非常に高い相性を持つカップルです。"
            f"価値観や感情のリズムが自然と噛み合い、深い信頼関係を築きやすい組み合わせです。"
            f"月星座（{moon_a}/{moon_b}）の面でも感情的な理解が深く、日常のすれ違いが起きにくいでしょう。"
            f"長期的なパートナーシップに向いており、積極的な交際をお勧めします。"
        )
    elif score >= 70:
        level = "高い"
        summary = (
            f"{name_a}さん（{sun_a}）と{name_b}さん（{sun_b}）の相性は良好です。"
            f"基本的な価値観に共通点が多く、一緒にいると居心地の良さを感じやすい関係です。"
            f"月星座（{moon_a}/{moon_b}）の違いで感情表現に差が出ることもありますが、"
            f"お互いを尊重することで補い合えます。コミュニケーションを大切にすれば安定した関係が期待できます。"
        )
    elif score >= 55:
        level = "普通"
        summary = (
            f"{name_a}さん（{sun_a}）と{name_b}さん（{sun_b}）の相性は中程度です。"
            f"異なる部分もありますが、それがお互いの成長を促す可能性もあります。"
            f"月星座（{moon_a}/{moon_b}）の違いから感情のペースに差が出やすいため、"
            f"意識的なコミュニケーションが大切です。努力次第で良いパートナーになれます。"
        )
    else:
        level = "要注意"
        summary = (
            f"{name_a}さん（{sun_a}）と{name_b}さん（{sun_b}）は、"
            f"価値観や感情のリズムに違いが出やすい組み合わせです。"
            f"相性の数値だけが全てではありませんが、実際のコミュニケーションを通じて"
            f"お互いの違いを理解し、思いやりを持って接することが特に重要です。"
        )
    return level, summary

# ===== 成婚アドバイス生成 =====
def generate_advice(chart_a, chart_b, signs, name_a, name_b):
    """APIのinterpretationsを使い、成婚に向けた具体的アドバイスを生成する"""

    # 各人の主要惑星のreading取得
    sun_a   = get_interpretation(chart_a, "sun")
    moon_a  = get_interpretation(chart_a, "moon")
    venus_a = get_interpretation(chart_a, "venus")
    mars_a  = get_interpretation(chart_a, "mars")

    sun_b   = get_interpretation(chart_b, "sun")
    moon_b  = get_interpretation(chart_b, "moon")
    venus_b = get_interpretation(chart_b, "venus")
    mars_b  = get_interpretation(chart_b, "mars")

    # 元素バランス
    elem_a = chart_a.get("modality_element", {}).get("elements", {})
    elem_b = chart_b.get("modality_element", {}).get("elements", {})

    # 主要元素を取得
    def dominant_elem(elem_dict):
        if not elem_dict:
            return ""
        return max(elem_dict, key=lambda k: elem_dict[k])

    dom_a = dominant_elem(elem_a)
    dom_b = dominant_elem(elem_b)

    advice_list = []

    # ---- 1. お互いの性格・個性の理解 ----
    block1_title = f"お互いの個性を理解する"
    block1_items = []

    if sun_a.get("reading"):
        block1_items.append(
            f"【{name_a}さん】{sun_a['title']}：{sun_a['reading']}"
        )
    if sun_b.get("reading"):
        block1_items.append(
            f"【{name_b}さん】{sun_b['title']}：{sun_b['reading']}"
        )
    if block1_items:
        advice_list.append({"title": block1_title, "items": block1_items})

    # ---- 2. 感情・日常生活の相性 ----
    block2_title = "日常生活での感情の合わせ方"
    block2_items = []

    moon_sign_a = signs["A"]["moon"] or ""
    moon_sign_b = signs["B"]["moon"] or ""
    elem_moon_a = ELEMENTS.get(moon_sign_a, "")
    elem_moon_b = ELEMENTS.get(moon_sign_b, "")

    if moon_a.get("reading"):
        block2_items.append(
            f"【{name_a}さんの感情パターン】{moon_a['title']}：{moon_a['reading']}"
        )
    if moon_b.get("reading"):
        block2_items.append(
            f"【{name_b}さんの感情パターン】{moon_b['title']}：{moon_b['reading']}"
        )

    if elem_moon_a and elem_moon_b:
        compat_score = element_compat(moon_sign_a, moon_sign_b)
        if compat_score >= 80:
            block2_items.append(
                f"お二人の月星座は{elem_moon_a}と{elem_moon_b}の組み合わせで、感情のリズムが自然と合いやすい傾向にあります。"
                f"日常生活でのすれ違いが少なく、安心できる関係を築きやすいでしょう。"
            )
        elif compat_score >= 60:
            block2_items.append(
                f"お二人の月星座は{elem_moon_a}と{elem_moon_b}の組み合わせです。"
                f"感情の表現方法に違いが出ることがありますが、相手のペースを尊重し合うことで安定した日常を作れます。"
            )
        else:
            block2_items.append(
                f"お二人の月星座は{elem_moon_a}と{elem_moon_b}の組み合わせで、感情のリズムに差が出やすい傾向にあります。"
                f"「なぜこんな反応をするのか」と感じることがあっても、相手の感情パターンの違いとして受け入れる姿勢が大切です。"
                f"定期的に気持ちを言葉にして伝え合う時間を作りましょう。"
            )

    if block2_items:
        advice_list.append({"title": block2_title, "items": block2_items})

    # ---- 3. 恋愛・パートナーシップの築き方 ----
    block3_title = "恋愛・パートナーシップの築き方"
    block3_items = []

    if venus_a.get("reading"):
        block3_items.append(
            f"【{name_a}さんの愛情表現】{venus_a['title']}：{venus_a['reading']}"
        )
    if venus_b.get("reading"):
        block3_items.append(
            f"【{name_b}さんの愛情表現】{venus_b['title']}：{venus_b['reading']}"
        )
    if mars_a.get("reading"):
        block3_items.append(
            f"【{name_a}さんの行動エネルギー】{mars_a['title']}：{mars_a['reading']}"
        )

    venus_sign_a = signs["A"]["venus"] or ""
    mars_sign_b  = signs["B"]["mars"]  or ""
    vm_compat = element_compat(venus_sign_a, mars_sign_b)
    if venus_sign_a and mars_sign_b:
        if vm_compat >= 80:
            block3_items.append(
                f"{name_a}さんの金星（{venus_sign_a}）と{name_b}さんの火星（{mars_sign_b}）の組み合わせは、"
                f"自然な引き合いが生まれやすく、恋愛としての発展が期待できます。"
            )
        else:
            block3_items.append(
                f"{name_a}さんの金星（{venus_sign_a}）と{name_b}さんの火星（{mars_sign_b}）は異なる性質を持ちます。"
                f"最初はアプローチの仕方に戸惑う場面もあるかもしれませんが、"
                f"お互いの愛情表現の違いを「個性」として楽しむ余裕が関係を深めます。"
            )

    if block3_items:
        advice_list.append({"title": block3_title, "items": block3_items})

    # ---- 4. 成婚に向けた具体的アドバイス ----
    block4_title = "成婚に向けた具体的なアドバイス"
    block4_items = []

    sun_sign_a = signs["A"]["sun"] or ""
    sun_sign_b = signs["B"]["sun"] or ""
    elem_sun_a = ELEMENTS.get(sun_sign_a, "")
    elem_sun_b = ELEMENTS.get(sun_sign_b, "")

    # 元素の組み合わせ別アドバイス
    elem_pair = tuple(sorted([elem_sun_a, elem_sun_b])) if elem_sun_a and elem_sun_b else ()
    elem_advice = {
        ("火", "火"): "お二人とも情熱的で行動力があります。デートや共同作業など「一緒に何かをする」体験を積み重ねると関係が深まりやすいです。",
        ("火", "風"): "火と風の相性は非常に良く、お互いを刺激し合えます。会話を大切にしながら、積極的に新しい体験を共有しましょう。",
        ("地", "地"): "お二人とも安定・堅実を重視します。将来の生活設計（住まい・貯金・家族計画）について早めに具体的な話し合いをすると安心感が生まれます。",
        ("地", "水"): "地と水は非常に相性が良く、安定した愛情関係を築きやすい組み合わせです。日常の小さな気遣いを大切にしましょう。",
        ("風", "風"): "お二人とも知的でコミュニケーションを大切にします。共通の趣味や話題を見つけることが仲を深める近道です。",
        ("水", "水"): "お二人とも感受性が豊かで共感力があります。感情を言葉にして伝え合う習慣をつけると、より深い絆が生まれます。",
    }
    if elem_pair in elem_advice:
        block4_items.append(elem_advice[elem_pair])
    elif elem_sun_a and elem_sun_b:
        block4_items.append(
            f"{elem_sun_a}と{elem_sun_b}の組み合わせです。"
            f"異なる性質を持つからこそ、お互いの強みで補い合える関係が築けます。"
            f"相手の「違い」を否定せず、まず受け入れる姿勢から始めましょう。"
        )

    # 共通アドバイス
    block4_items.append(
        "交際初期は月に2〜3回のペースでデートを重ね、「安心できる存在」としての信頼を築くことを優先しましょう。"
        "結婚の話題は交際3〜6か月以降、お互いの価値観（お金・家事・家族関係）をしっかり確認した上で進めるのが理想です。"
    )
    block4_items.append(
        "成婚相談所のカウンセラーへの相談も積極的に活用し、"
        "進捗や迷いを一人で抱え込まずにサポートを受けながら関係を進めてください。"
    )

    if block4_items:
        advice_list.append({"title": block4_title, "items": block4_items})

    return advice_list

# ===== ルーティング =====
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/result", methods=["POST"])
def result():
    name_a = request.form.get("name_a", "").strip() or "Aさん"
    date_a = request.form.get("date_a", "").strip()
    time_a = "12:00"

    name_b = request.form.get("name_b", "").strip() or "Bさん"
    date_b = request.form.get("date_b", "").strip()
    time_b = "12:00"

    errors = []
    for label, val in [
        (f"{name_a}の生年月日", date_a),
        (f"{name_b}の生年月日", date_b),
    ]:
        if len(val) != 8 or not val.isdigit():
            errors.append(f"{label}は8桁の数字で入力してください（例：19940529）")

    if errors:
        return render_template("index.html", errors=errors,
                               name_a=name_a, date_a=date_a,
                               name_b=name_b, date_b=date_b)

    try:
        chart_a = get_natal_chart(name_a, date_a, time_a)
        chart_b = get_natal_chart(name_b, date_b, time_b)
    except requests.exceptions.RequestException as e:
        return render_template("index.html",
                               errors=[f"APIエラーが発生しました: {e}"],
                               name_a=name_a, date_a=date_a,
                               name_b=name_b, date_b=date_b)

    score, scores, signs = calc_compatibility(chart_a, chart_b)
    level, comment      = generate_comment(score, signs, name_a, name_b)
    advice_list         = generate_advice(chart_a, chart_b, signs, name_a, name_b)

    return render_template("result.html",
                           name_a=name_a, name_b=name_b,
                           score=score, level=level,
                           scores=scores, signs=signs,
                           comment=comment,
                           advice_list=advice_list)

if __name__ == "__main__":
    app.run(debug=True, port=5000)
