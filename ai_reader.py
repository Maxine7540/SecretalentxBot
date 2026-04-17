"""
AI 解讀模組
使用 Google Gemini API（免費方案）根據命盤數據生成深度分析
"""

import os
import urllib.request
import urllib.error
import json


def call_gemini(prompt: str, api_key: str, max_tokens: int = 3500) -> str:
    """呼叫 Google Gemini API，含自動重試"""
    import time
    if not api_key:
        raise ValueError("GEMINI_API_KEY 未設定，請在 Railway Variables 中加入此環境變數")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key={api_key}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.8}
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            return result["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = 30 * (attempt + 1)
                time.sleep(wait)
                continue
            raise
    raise Exception("請求次數過多，請稍候 2 分鐘後再試")


def build_prompt(data: dict) -> str:
    manifest = data["manifest"]
    hidden = data["hidden"]
    solar = data["solar"]
    m_meaning = data.get("manifest_meaning", {})
    h_meaning = data.get("hidden_meaning", {})

    combined_grid = {}
    for n in range(1, 10):
        combined_grid[n] = manifest["grid"].get(n, 0) + hidden.get("grid", {}).get(n, 0)
    combined_strong = {k: v for k, v in combined_grid.items() if v >= 5}
    combined_missing = [n for n in range(1, 10) if combined_grid.get(n, 0) == 0]

    manifest_strong_str = "、".join(f"{k}（{v}圈）" for k, v in manifest["strong_numbers"].items()) if manifest["strong_numbers"] else "無"
    manifest_missing_str = "、".join(str(n) for n in manifest["missing_numbers"]) if manifest["missing_numbers"] else "無"
    hidden_strong_str = "、".join(f"{k}（{v}圈）" for k, v in hidden.get("strong_numbers", {}).items()) if hidden.get("strong_numbers") else "無"
    hidden_missing_str = "、".join(str(n) for n in hidden.get("missing_numbers", [])) if hidden.get("missing_numbers") else "無"
    combined_strong_str = "、".join(f"{k}（{v}圈）" for k, v in combined_strong.items()) if combined_strong else "無"
    combined_missing_str = "、".join(str(n) for n in combined_missing) if combined_missing else "無"

    prompt = f"""你是一位專業的生命靈數分析師，請根據以下完整命盤數據，用繁體中文撰寫深入且個人化的綜合命盤分析。

【基本資料】
西曆生日：{solar['year']}/{solar['month']:02d}/{solar['day']:02d}
農曆生日：{data['lunar'].get('display', '無法轉換')}
{'出生時辰：' + str(solar['hour']) + '時' if solar.get('hour') is not None else ''}

【外在性格命盤（西曆）】
天賦數：{manifest['total']}　本命靈數：{manifest['single']}（{m_meaning.get('name', '')}）
關鍵詞：{m_meaning.get('keyword', '')}
圈數分佈：{dict(sorted(manifest['grid'].items()))}
強勢數（≥3圈）：{manifest_strong_str}
空缺數：{manifest_missing_str}

【內在精神命盤（農曆）】
天賦數：{hidden.get('total', '?')}　本命靈數：{hidden.get('single', '?')}（{h_meaning.get('name', '')}）
關鍵詞：{h_meaning.get('keyword', '')}
圈數分佈：{dict(sorted(hidden.get('grid', {}).items()))}
強勢數（≥3圈）：{hidden_strong_str}
空缺數：{hidden_missing_str}

【綜合命盤】
圈數分佈：{dict(sorted(combined_grid.items()))}
強勢數（≥5圈）：{combined_strong_str}
空缺數：{combined_missing_str}

---

請嚴格按照以下三個部分撰寫。語氣風格：溫暖地說出直接的話，適合的地方加一點幽默感，讓用戶感覺這是為他量身定做的，要說到他的心坎裡。不要空泛，不要套話，每一句都要讓人覺得「這說的就是我」。

---

**一、外在性格解析（西曆命盤）**
天賦數 {manifest['total']}　本命靈數 {manifest['single']}　{'空缺：' + manifest_missing_str if manifest['missing_numbers'] else '無空缺'}

請涵蓋：
- 天賦數 {manifest['total']} 的深層意義：這個數字組合代表什麼樣的天生能力與人生課題
- 本命靈數 {manifest['single']}（{m_meaning.get('name', '')}）塑造的外在性格：別人眼中的你、你習慣的行為模式、你的優勢與局限，性格描述要大方向全面
- {manifest['single']} 號人的興趣愛好傾向：會被哪些知識領域、活動或事物吸引，哪類事物讓你真正活起來
- 圈數較多的數字對性格的加強影響
- 空缺數的具體影響：在日常生活與關係中如何體現，需要如何有意識地補足
- 語氣直接，像在說一個真實的人，不是在背定義

**二、內在精神解析（農曆命盤）**
天賦數 {hidden.get('total', '?')}　本命靈數 {hidden.get('single', '?')}　{'強勢數：' + hidden_strong_str if hidden.get('strong_numbers') else ''}　{'空缺：' + hidden_missing_str if hidden.get('missing_numbers') else '無空缺'}

請涵蓋：
- 天賦數 {hidden.get('total', '?')} 的深層意義：你骨子裡的驅動力與底層價值觀
- 本命靈數 {hidden.get('single', '?')}（{h_meaning.get('name', '')}）的內在特質：你不常讓人看見的那一面、你的內在需求、你的真實動機
- 強勢數的雙面影響：這股能量如何成為你的最大資產，同時又是你需要馴服的力量（若有強勢數）
- 空缺數在內在層面的具體影響：這些空缺如何在你的關係、決策、情感模式中顯現
- 語氣要讓人感覺「你看穿了我」，但不是批判，是理解

**三、綜合命盤總結**
強勢數 {combined_strong_str}　空缺數 {combined_missing_str}

這是最重要的部分，篇幅最長、最深入。請涵蓋：

- 外在靈數 {manifest['single']} 與內在靈數 {hidden.get('single', '?')} 的核心對話：兩股能量的關係，當它們合作時你是什麼樣的人，這個組合在人群中的稀有之處
- 全面性格描述：個性特質、思維模式、行事風格、人際相處方式，讓人讀完覺得「這就是完整的我」
- 興趣愛好：結合外在與內在兩個靈數，說明這個組合天然會被哪些領域吸引
- 強勢數對整體人生的主導影響與如何善用（若有）
- 空缺數的綜合意義，或無空缺代表什麼
- 職業方向（直接融入文字，不加標題）：根據這個性格組合，自然帶出最適合的工作類型與環境，說明為什麼
- 感情與關係（直接融入文字，不加標題）：這個人在感情裡是什麼樣的，需要什麼樣的伴侶，容易遇到什麼模式，愛的方式是什麼
- 可能遇到的瓶頸與解決方式：最常見的卡關狀態是什麼，根源在哪裡，具體怎麼破解
- 能量失衡的兩種狀態（融入文字）：「外在壓過內在」時會出現什麼症狀與解藥，「內在壓過外在」時又是什麼狀況與解藥
- 用一句真正說到這個命盤核心的話作結，有力量，不陳腔濫調

格式要求：
- 三個部分各有清楚標題
- 段落之間留空行，易於閱讀
- 盡量用流暢的段落文字，少用列點
- 篇幅：外在約400字、內在約400字、綜合700字以上
"""
    return prompt


def get_ai_reading(data: dict, api_key: str) -> str:
    """呼叫 Gemini API 生成綜合命盤解讀"""
    prompt = build_prompt(data)
    return call_gemini(prompt, api_key, max_tokens=3500)


def get_year_detail(data: dict, api_key: str) -> str:
    """流年詳細分析"""
    py = data["personal_year_current"]
    solar = data["solar"]
    birth_single = data["manifest"]["single"]
    is_personal_year = (py["single"] == birth_single)
    monthly = data["monthly_current"]
    month_names = ["一","二","三","四","五","六","七","八","九","十","十一","十二"]
    monthly_str = "、".join([f"{month_names[i]}月={pm['single']}" for i, pm in enumerate(monthly)])

    personal_year_note = ""
    if is_personal_year:
        personal_year_note = f"\n⭐ 特別注意：這是命主的本命年（流年數={birth_single}，與生命靈數相同），能量特別強烈，請在分析中重點說明本命年的意義與注意事項。"

    prompt = f"""你是生命靈數分析師。請用繁體中文為以下命主做詳細的流年分析。
語氣溫暖直接，具體可行，讓人感覺是為他量身分析的。

出生日期：{solar['year']}/{solar['month']:02d}/{solar['day']:02d}
本命靈數：{birth_single}（天賦數 {data['manifest']['total']}）
{py['year']}年流年數：{py['single']}（天賦數 {py['total']}）
各月流月數：{monthly_str}
{personal_year_note}

請按以下結構分析：

**{py['year']}年流年數 {py['single']} 完整解析**

**整體能量與主題**
深入說明流年數 {py['single']} 的意義，這一年的核心能量，適合做什麼、不適合做什麼，以及與本命靈數 {birth_single} 的互動關係（4-5句）

**事業與財運**
今年在事業發展、財務機會上的具體方向與建議（3-4句）

**感情與人際**
感情運勢、人際互動的重點提醒（3-4句）

**身心健康**
需要特別注意的健康方向與調整建議（2-3句）

{"**本命年特別說明**\\n本命年意味著什麼？這一年的能量有哪些特殊之處？機遇與挑戰各是什麼？如何善用本命年的能量？（4-5句）" if is_personal_year else "**上下半年能量分析**\\n上半年（1-6月）的整體走向，與下半年（7-12月）的轉變（各2-3句）"}

**重點月份**
根據流月數，點出今年最值得把握的3-4個月份，說明各月的特別意義

**今年送給自己的一句話**
一句真正說到這個流年核心的話，有力量，不陳腔濫調"""

    return call_gemini(prompt, api_key, max_tokens=1500)


def get_monthly_detail(data: dict, month: int, api_key: str) -> str:
    """單月詳細流月分析"""
    py = data["personal_year_current"]
    monthly = data["monthly_current"]
    pm = monthly[month - 1]
    solar = data["solar"]

    prompt = f"""你是生命靈數分析師。請用繁體中文分析以下流月詳情。
語氣溫暖直接，積極正向，具體可行，讓人感覺是為他量身分析的。

出生日期：{solar['year']}/{solar['month']:02d}/{solar['day']:02d}
本命靈數：{data['manifest']['single']}（天賦數 {data['manifest']['total']}）
{py['year']}年流年數：{py['single']}（{data['year_theme']}）
{py['year']}年{month}月流月數：{pm['single']}（天賦數 {pm['total']}）

請分析這個流月的：

**整體能量與主題**
這個月的核心能量是什麼，整體基調如何，與流年數的互動（3-4句）

**事業財運**
這個月在工作、財務方面的機會與注意點（2-3句）

**感情人際**
感情與人際關係的能量走向（2-3句）

**身心提醒**
健康與情緒方面需要注意的事（1-2句）

**本月三大行動建議**
具體可執行的三件事，讓這個月的能量發揮最大

**幸運提示**
本月幸運數字與建議顏色"""

    return call_gemini(prompt, api_key, max_tokens=800)
