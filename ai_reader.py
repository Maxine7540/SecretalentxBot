"""
AI 解讀模組 - 多 API 自動輪換
失敗自動跳下一個，不重試避免被封
"""

import urllib.request
import urllib.error
import json
import os


def call_openrouter(prompt: str, api_key: str, model: str, max_tokens: int) -> str:
    """呼叫 OpenRouter API"""
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.8
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://telegram.org",
            "X-Title": "Numerology Bot"
        },
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))

    choices = result.get("choices", [])
    if not choices:
        raise Exception(f"回傳 choices 為空: {str(result)[:150]}")
    content = choices[0].get("message", {}).get("content", "")
    if not content or len(content.strip()) < 10:
        raise Exception("回傳內容為空或過短")
    return content


def call_gemini(prompt: str, api_key: str, max_tokens: int) -> str:
    """呼叫 Gemini API"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key={api_key}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.8}
    }).encode("utf-8")

    req = urllib.request.Request(
        url, data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result["candidates"][0]["content"]["parts"][0]["text"]


def call_openrouter_safe(prompt: str, api_key: str, model: str, max_tokens: int) -> str:
    """帶完整錯誤處理的 OpenRouter 呼叫"""
    try:
        result = call_openrouter(prompt, api_key, model, max_tokens)
        if not result or len(result.strip()) < 10:
            raise Exception("回傳內容為空")
        return result
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if hasattr(e, "read") else ""
        raise Exception(f"HTTP {e.code}: {body[:150]}")


def call_ai(prompt: str, api_key: str, max_tokens: int = 1500) -> str:
    """多 API 自動輪換，失敗立刻跳下一個"""
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
    gemini_key = os.environ.get("GEMINI_API_KEY", "")

    # 用預設參數固定變數，避免 lambda 捕獲問題
    def make_or(model, mt=max_tokens, key=None):
        k = key or openrouter_key
        return lambda: call_openrouter_safe(prompt, k, model, mt)

    def make_gemini(mt=max_tokens, key=None):
        k = key or gemini_key
        return lambda: call_gemini(prompt, k, mt)

    attempts = []
    if openrouter_key:
        attempts += [
            ("Llama 3.1 8B",     make_or("meta-llama/llama-3.1-8b-instruct:free")),
            ("Gemma 3 4B",       make_or("google/gemma-3-4b-it:free")),
            ("Gemma 3 12B",      make_or("google/gemma-3-12b-it:free")),
            ("Llama 3.3 70B",    make_or("meta-llama/llama-3.3-70b-instruct:free")),
            ("DeepSeek R1 free", make_or("deepseek/deepseek-r1:free")),
            ("Phi 3 Mini",       make_or("microsoft/phi-3-mini-128k-instruct:free")),
            ("Qwen 2 7B",        make_or("qwen/qwen-2-7b-instruct:free")),
        ]
    if gemini_key:
        attempts.append(("Gemini Direct", make_gemini()))

    if not attempts:
        raise ValueError("請在 Railway Variables 中設定 OPENROUTER_API_KEY 或 GEMINI_API_KEY")

    errors = []
    for name, fn in attempts:
        try:
            result = fn()
            return result
        except Exception as e:
            errors.append(f"{name}: {str(e)[:80]}")
            continue

    raise Exception("所有 API 均失敗：\n" + "\n".join(errors))


def build_prompt(data: dict) -> str:
    """綜合命盤分析 prompt"""
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
    combined_strong_str = "、".join(f"{k}({v}圈)" for k, v in combined_strong.items()) if combined_strong else "無"
    combined_missing_str = "、".join(str(n) for n in combined_missing) if combined_missing else "無"

    prompt = f"""你是一位專業的生命靈數分析師。請根據以下命盤數據，用繁體中文寫出「綜合命盤分析」。

【寫作風格要求】
- 語氣：溫暖、直接、適時帶一點幽默，讓人感覺這是為他量身定做的
- 格式：流暢的段落文字，不要條列式，不要用**粗體**或編號
- 深度：要說到心坎裡，每一句都要讓人覺得「這說的就是我」
- 範例語氣：「你是一個外冷內熱的人，而且這個溫差比大多數人都大」「你不需要想清楚所有的細節，你只需要開始」「你最大的天賦，是把深度變成力量」

【命盤資料】
西曆：{solar['year']}/{solar['month']:02d}/{solar['day']:02d}　農曆：{data['lunar'].get('display','無')}
外在本命靈數：{manifest['single']}（{m_meaning.get('name','')}）天賦數 {manifest['total']}
內在本命靈數：{hidden.get('single','?')}（{h_meaning.get('name','')}）天賦數 {hidden.get('total','?')}
綜合強勢數：{combined_strong_str}　綜合空缺數：{combined_missing_str}

【分析內容】請依序涵蓋以下內容，段落之間自然銜接：

第一段：外在靈數 {manifest['single']} 與內在靈數 {hidden.get('single','?')} 的核心對話——這兩股能量是互補、共鳴還是張力？當它們合作時，這個人會是什麼樣子？說出這個組合在人群中的稀有之處。

第二段：完整性格描述——結合外在與內在，描述這個人的思維模式、行事風格、人際相處方式。要大方向全面，讓人讀完覺得「這就是完整的我」。

第三段：興趣愛好——結合外在靈數 {manifest['single']} 與內在靈數 {hidden.get('single','?')}，說明這個組合天然會被哪些領域吸引，什麼事情讓他真正活起來。

第四段：職業方向——根據這個性格組合，自然地帶出最適合的工作類型與環境，說明為什麼這個組合適合，不要加「職業」標題，直接融入文字。

第五段：感情模式——這個人在感情裡是什麼樣的，需要什麼樣的伴侶，容易遇到什麼模式，愛的方式是什麼。不要加「感情」標題，直接融入文字。

第六段：瓶頸與能量失衡——描述這個人最常見的卡關狀態及解法，以及「外在壓過內在」與「內在壓過外在」兩種失衡狀態的症狀與解藥。

最後一句：用一句真正說到這個命盤核心的話作結，有力量，不陳腔濫調。"""

    return prompt


def get_ai_reading(data: dict, api_key: str) -> str:
    return call_ai(build_prompt(data), api_key, max_tokens=1500)


def get_year_detail(data: dict, api_key: str, year_type: str = "current") -> str:
    if year_type == "next":
        py = data["personal_year_next"]
        monthly = data["monthly_next"]
    else:
        py = data["personal_year_current"]
        monthly = data["monthly_current"]
    solar = data["solar"]
    birth_single = data["manifest"]["single"]
    is_personal_year = (py["single"] == birth_single)
    month_names = ["一","二","三","四","五","六","七","八","九","十","十一","十二"]
    monthly_str = "、".join([f"{month_names[i]}月={pm['single']}" for i, pm in enumerate(monthly)])

    prompt = f"""你是一位專業的生命靈數分析師。請根據以下資料，用繁體中文寫出 {py['year']} 年的「流年分析」。

【寫作風格要求】
- 語氣：溫暖、直接、具體，讓人感覺是為他量身分析的
- 格式：流暢段落文字，不要條列式，不要用**粗體**
- 深度：要有具體建議，不要只說「要注意」，要說「注意什麼、怎麼做」

【命盤資料】
出生：{solar['year']}/{solar['month']:02d}/{solar['day']:02d}　本命靈數：{birth_single}（天賦數 {data['manifest']['total']}）
{py['year']} 年流年數：{py['single']}（天賦數 {py['total']}）
各月流月數：{monthly_str}
{"【重要】這是本命年！流年數與本命靈數相同，能量特別強烈，請在分析中重點說明本命年的特殊意義。" if is_personal_year else ""}

【分析內容】請涵蓋以下內容，段落自然銜接：

整體能量與主題：流年數 {py['single']} 這一年的核心能量是什麼，適合做什麼、不適合做什麼，與本命靈數 {birth_single} 的互動關係。

事業與財運：今年在工作、財務方面的具體機會與挑戰，以及實際建議。

感情與人際：感情運勢與人際互動的重點提醒，要具體說明。

身心健康：需要特別注意的健康方向與調整建議。

{"本命年特別說明：本命年意味著什麼？這一年的能量有哪些特殊之處？機遇與挑戰各是什麼？如何善用這股能量？" if is_personal_year else "上下半年重點：上半年（1-6月）的整體走向，以及下半年（7-12月）的轉變。"}

重點月份：根據流月數，點出今年最值得把握的 3-4 個月份，說明各月的特別意義。

最後用一句真正說到這個流年核心的話作結。"""

    return call_ai(prompt, api_key, max_tokens=1200)


def get_monthly_detail(data: dict, month: int, api_key: str) -> str:
    py = data["personal_year_current"]
    pm = data["monthly_current"][month - 1]
    solar = data["solar"]
    month_names = ["一","二","三","四","五","六","七","八","九","十","十一","十二"]

    prompt = f"""你是一位專業的生命靈數分析師。請根據以下資料，用繁體中文寫出 {py['year']} 年 {month_names[month-1]} 月的「流月分析」。

【寫作風格要求】
- 語氣：溫暖、積極、具體可行
- 格式：流暢段落文字，不要條列式，不要用**粗體**
- 深度：每個分析都要有具體建議，不要空泛

【命盤資料】
出生：{solar['year']}/{solar['month']:02d}/{solar['day']:02d}　本命靈數：{data['manifest']['single']}
{py['year']} 年流年數：{py['single']}　{month_names[month-1]}月流月數：{pm['single']}

【分析內容】請涵蓋：整體能量與月份主題、事業財運方向、感情人際提示、身心調養建議、本月最值得做的三件事、幸運數字與顏色。段落自然銜接，語氣積極有溫度。"""

    return call_ai(prompt, api_key, max_tokens=800)


def get_outer_reading(data: dict, api_key: str) -> str:
    """外在性格解析（西曆命盤）"""
    manifest = data["manifest"]
    solar = data["solar"]
    m_meaning = data.get("manifest_meaning", {})
    strong_str = "、".join(f"{k}({v}圈)" for k, v in manifest["strong_numbers"].items()) if manifest["strong_numbers"] else "無"
    missing_str = "、".join(str(n) for n in manifest["missing_numbers"]) if manifest["missing_numbers"] else "無"

    prompt = f"""你是一位專業的生命靈數分析師。請根據以下命盤數據，用繁體中文寫出「外在性格解析」。

【寫作風格要求】
- 語氣：溫暖、直接、有時帶一點幽默，讓人感覺「這說的就是我」
- 格式：流暢的段落文字，不要條列式，不要用**粗體**或編號
- 深度：具體描述這個人的真實樣子，不要空泛的套話
- 範例語氣：「你的沉默裡藏著很多答案」「你不是那種只會空想的人，也不是埋頭苦幹卻不懂變通的人」「這不是你不愛，是你的愛比較內建」

【命盤資料】
西曆生日：{solar['year']}/{solar['month']:02d}/{solar['day']:02d}
天賦數：{manifest['total']}　本命靈數：{manifest['single']}（{m_meaning.get('name','')}）
關鍵詞：{m_meaning.get('keyword','')}
圈數分佈：{dict(sorted(manifest['grid'].items()))}
強勢數：{strong_str}　空缺數：{missing_str}

【分析內容】請依序涵蓋以下內容，每個段落自然銜接：

第一段：天賦數 {manifest['total']} 的深層意義——這個數字組合代表什麼樣的天生能力與人生課題，講出這個人與眾不同之處。

第二段：本命靈數 {manifest['single']}（{m_meaning.get('name','')}）塑造的外在性格——別人眼中的你是什麼樣子、你習慣的行為模式、你的優勢與局限，要全面且真實。

第三段：興趣愛好傾向——{manifest['single']} 號人會被哪些知識領域或活動吸引，哪類事物讓你真正活起來。

第四段（若有強勢數）：強勢數 {strong_str} 如何強化這個人的特質。

第五段：空缺數 {missing_str} 的具體影響——在日常生活、人際關係中如何體現，以及補足方向。用溫柔但直接的方式說出來，不要迴避。"""

    return call_ai(prompt, api_key, max_tokens=1200)


def get_inner_reading(data: dict, api_key: str) -> str:
    """內在精神解析（農曆命盤）"""
    hidden = data["hidden"]
    solar = data["solar"]
    lunar = data["lunar"]
    h_meaning = data.get("hidden_meaning", {})
    strong_str = "、".join(f"{k}({v}圈)" for k, v in hidden.get("strong_numbers", {}).items()) if hidden.get("strong_numbers") else "無"
    missing_str = "、".join(str(n) for n in hidden.get("missing_numbers", [])) if hidden.get("missing_numbers") else "無"

    prompt = f"""你是一位專業的生命靈數分析師。請根據以下命盤數據，用繁體中文寫出「內在精神解析」。

【寫作風格要求】
- 語氣：溫暖、直接、穿透力強，讓人感覺「你看穿了我」但不是批判，是理解
- 格式：流暢的段落文字，不要條列式，不要用**粗體**或編號
- 深度：寫出這個人不常讓外人看見的那一面，骨子裡真正的樣子
- 範例語氣：「農曆命盤是你的底層作業系統」「你表面上可以很隨和，但內心有一個非常清楚的標準在衡量一切」「別人以為你在聽，你其實在評估」

【命盤資料】
農曆生日：{lunar.get('display','無')}（西曆 {solar['year']}/{solar['month']:02d}/{solar['day']:02d}）
天賦數：{hidden.get('total','?')}　本命靈數：{hidden.get('single','?')}（{h_meaning.get('name','')}）
關鍵詞：{h_meaning.get('keyword','')}
圈數分佈：{dict(sorted(hidden.get('grid',{}).items()))}
強勢數：{strong_str}　空缺數：{missing_str}

【分析內容】請依序涵蓋以下內容，每個段落自然銜接：

第一段：農曆命盤的定位——說明這是「底層作業系統」，是這個人骨子裡的驅動力。天賦數 {hidden.get('total','?')} 代表什麼樣的底層價值觀與人生動力。

第二段：本命靈數 {hidden.get('single','?')}（{h_meaning.get('name','')}）的內在特質——這個人不常讓人看見的那一面、真實的內在需求、做決定時真正的動機是什麼。

第三段（若有強勢數）：強勢數 {strong_str} 的雙面影響——這股能量如何成為最大的資產，同時又是最需要馴服的力量。要說得具體，不要只說「優缺點」。

第四段：空缺數 {missing_str} 在內在層面的影響——這些空缺如何在這個人的關係、決策、情感模式中具體顯現。用理解的語氣，不要批判。"""

    return call_ai(prompt, api_key, max_tokens=1200)
