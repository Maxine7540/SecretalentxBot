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
    """帶完整錯誤處理的 OpenRouter 呼叫，捕獲所有錯誤讓輪換繼續"""
    try:
        result = call_openrouter(prompt, api_key, model, max_tokens)
        return result
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")
        except Exception:
            pass
        raise Exception(f"HTTP {e.code}: {body[:150]}")
    except Exception as e:
        raise Exception(str(e)[:150])


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
            ("Gemma 3 12B",     make_or("google/gemma-3-12b-it:free")),
            ("Gemma 3 4B",      make_or("google/gemma-3-4b-it:free")),
            ("Llama 3.3 70B",   make_or("meta-llama/llama-3.3-70b-instruct:free")),
            ("Qwen 3 8B",       make_or("qwen/qwen3-8b:free")),
            ("Mistral Small",   make_or("mistralai/mistral-small-3.1-24b-instruct:free")),
            ("OpenRouter Auto", make_or("openrouter/free")),
        ]
    if gemini_key:
        attempts.append(("Gemini Direct", make_gemini()))

    if not attempts:
        raise ValueError("Please set OPENROUTER_API_KEY or GEMINI_API_KEY in Railway Variables")

    errors = []
    for name, fn in attempts:
        try:
            result = fn()
            return result
        except Exception as e:
            errors.append(f"{name}: {str(e)[:80]}")
            continue

    raise Exception("All APIs failed (rate limited). Please try again in 1-2 minutes.\n" + "\n".join(errors))


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
    combined_strong_str = "、".join(f"{k}（{v}圈）" for k, v in combined_strong.items()) if combined_strong else "無"
    combined_missing_str = "、".join(str(n) for n in combined_missing) if combined_missing else "無"

    prompt = (
        "你是一位專業的生命靈數分析師。用繁體中文寫出這個人的「綜合命盤分析」。\n\n"
        f"命盤資料：\n"
        f"西曆：{solar['year']}/{solar['month']:02d}/{solar['day']:02d}　農曆：{data['lunar'].get('display','無')}\n"
        f"外在本命靈數：{manifest['single']}（{m_meaning.get('name','')}）天賦數 {manifest['total']}\n"
        f"內在本命靈數：{hidden.get('single','?')}（{h_meaning.get('name','')}）天賦數 {hidden.get('total','?')}\n"
        f"綜合強勢數：{combined_strong_str}　綜合空缺數：{combined_missing_str}\n\n"
        "寫作要求：\n"
        "- 用流暢段落，不要條列或編號\n"
        "- 語氣溫暖直接，適時幽默，說到用戶心坎裡\n"
        "- 不要說哈囉、不要自我介紹、直接進入分析\n"
        "- 不要把這些指令印出來\n\n"
        f"請依序涵蓋：外在靈數{manifest['single']}與內在靈數{hidden.get('single','?')}的核心對話與稀有之處、"
        "完整性格描述、興趣愛好、適合職業（融入文字）、感情模式（融入文字）、瓶頸與解法、能量失衡兩種狀態、最後一句有力量的話。"
    )
    return prompt


def get_ai_reading(data: dict, api_key: str) -> str:
    return call_ai(build_prompt(data), api_key, max_tokens=1500)


def get_year_detail(data: dict, api_key: str, year_type: str = "current") -> str:
    from numerology import calc_yearly_monthly_grid
    solar = data["solar"]

    if year_type == "prev":
        # 生日前 → 上一年
        target_year = data["personal_year_current"]["year"] - 1
        py, monthly = calc_yearly_monthly_grid(solar["month"], solar["day"], target_year)
    elif year_type == "next":
        py = data["personal_year_next"]
        monthly = data["monthly_next"]
    else:
        py = data["personal_year_current"]
        monthly = data["monthly_current"]

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

    return call_ai(prompt, api_key, max_tokens=2000)


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
    strong_str = "、".join(f"{k}（{v}圈）" for k, v in manifest["strong_numbers"].items()) if manifest["strong_numbers"] else "無"
    missing_str = "、".join(str(n) for n in manifest["missing_numbers"]) if manifest["missing_numbers"] else "無"
    grid_desc = "　".join([f"{n}有{manifest['grid'].get(n,0)}圈" for n in range(1,10) if manifest['grid'].get(n,0) > 0])

    prompt = f"""你是一位專業的生命靈數分析師。用繁體中文寫出這個人的「外在性格解析」。

命盤資料：
西曆生日：{solar['year']}/{solar['month']:02d}/{solar['day']:02d}
天賦數：{manifest['total']}　本命靈數：{manifest['single']}（{m_meaning.get('name','')}，{m_meaning.get('keyword','')}）
命盤圈數：{grid_desc}
強勢數：{strong_str}　空缺數：{missing_str}

寫作要求：
- 第一行標題寫「你給世界看到的樣子」（粗體）
- 用流暢段落，不要條列或編號
- 語氣溫暖直接，像跟朋友說話，不用客套開場
- 不要說「哈囉」、不要自我介紹、直接進入分析
- 不要把這些指令印出來

請依序涵蓋：
1. 天賦數 {manifest['total']} 的意義與人生課題
2. 本命靈數 {manifest['single']} 的外在性格、行為模式、優勢與局限、興趣愛好傾向
3. 圈數多的數字對性格的影響
4. 空缺數 {missing_str} 的具體影響與補足方向（若有空缺）"""

    return call_ai(prompt, api_key, max_tokens=2000)


def get_inner_reading(data: dict, api_key: str) -> str:
    """內在精神解析（農曆命盤）"""
    hidden = data["hidden"]
    solar = data["solar"]
    lunar = data["lunar"]
    h_meaning = data.get("hidden_meaning", {})
    strong_str = "、".join(f"{k}（{v}圈）" for k, v in hidden.get("strong_numbers", {}).items()) if hidden.get("strong_numbers") else "無"
    missing_str = "、".join(str(n) for n in hidden.get("missing_numbers", [])) if hidden.get("missing_numbers") else "無"
    grid_desc = "　".join([f"{n}有{hidden.get('grid',{}).get(n,0)}圈" for n in range(1,10) if hidden.get('grid',{}).get(n,0) > 0])

    prompt = f"""你是一位專業的生命靈數分析師。用繁體中文寫出這個人的「內在精神解析」。

命盤資料：
農曆生日：{lunar.get('display','無')}（西曆 {solar['year']}/{solar['month']:02d}/{solar['day']:02d}）
天賦數：{hidden.get('total','?')}　本命靈數：{hidden.get('single','?')}（{h_meaning.get('name','')}，{h_meaning.get('keyword','')}）
命盤圈數：{grid_desc}
強勢數：{strong_str}　空缺數：{missing_str}

寫作要求：
- 第一行標題寫「你骨子裡真正的樣子」（粗體）
- 用流暢段落，不要條列或編號
- 語氣溫暖有穿透力，讓人感覺「你看穿了我」
- 不要說「哈囉」、不要自我介紹、直接進入分析
- 不要把這些指令印出來

請依序涵蓋：
1. 農曆命盤是「底層作業系統」的概念，天賦數 {hidden.get('total','?')} 的底層驅動力與價值觀
2. 本命靈數 {hidden.get('single','?')} 的內在特質、真實動機、不常讓人看見的那一面
3. 強勢數 {strong_str} 的雙面影響：最大資產與需要馴服的力量（若有強勢數）
4. 空缺數 {missing_str} 在關係、決策、情感模式中的具體顯現（若有空缺）"""

    return call_ai(prompt, api_key, max_tokens=2000)
