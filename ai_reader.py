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
    return result["choices"][0]["message"]["content"]


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


def call_ai(prompt: str, api_key: str, max_tokens: int = 1200) -> str:
    """
    多 API 自動輪換：
    1. OpenRouter Gemini 2.0 Flash（免費）
    2. OpenRouter DeepSeek（免費）
    3. OpenRouter Llama（免費）
    4. Gemini 直接 API（備用）
    """
    # api_key 格式：openrouter key 或 gemini key
    # 優先嘗試 OpenRouter（用 OPENROUTER_API_KEY）
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "")
    gemini_key = os.environ.get("GEMINI_API_KEY", "")

    errors = []

    # 嘗試順序
    attempts = []

    if openrouter_key:
        attempts += [
            ("OpenRouter Gemini", lambda: call_openrouter(prompt, openrouter_key, "google/gemini-2.0-flash-exp:free", max_tokens)),
            ("OpenRouter DeepSeek", lambda: call_openrouter(prompt, openrouter_key, "deepseek/deepseek-r1:free", max_tokens)),
            ("OpenRouter Llama", lambda: call_openrouter(prompt, openrouter_key, "meta-llama/llama-3.1-8b-instruct:free", max_tokens)),
        ]

    if gemini_key:
        attempts.append(
            ("Gemini Direct", lambda: call_gemini(prompt, gemini_key, max_tokens))
        )

    if not attempts:
        raise ValueError("請在 Railway Variables 中設定 OPENROUTER_API_KEY 或 GEMINI_API_KEY")

    for name, fn in attempts:
        try:
            result = fn()
            if result and len(result) > 10:
                return result
        except Exception as e:
            errors.append(f"{name}: {str(e)[:80]}")
            continue

    raise Exception("所有 API 均失敗：\n" + "\n".join(errors))


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

    manifest_strong_str = "、".join(f"{k}({v}圈)" for k, v in manifest["strong_numbers"].items()) if manifest["strong_numbers"] else "無"
    manifest_missing_str = "、".join(str(n) for n in manifest["missing_numbers"]) if manifest["missing_numbers"] else "無"
    hidden_strong_str = "、".join(f"{k}({v}圈)" for k, v in hidden.get("strong_numbers", {}).items()) if hidden.get("strong_numbers") else "無"
    hidden_missing_str = "、".join(str(n) for n in hidden.get("missing_numbers", [])) if hidden.get("missing_numbers") else "無"
    combined_strong_str = "、".join(f"{k}({v}圈)" for k, v in combined_strong.items()) if combined_strong else "無"
    combined_missing_str = "、".join(str(n) for n in combined_missing) if combined_missing else "無"

    prompt = f"""你是專業生命靈數分析師，請用繁體中文撰寫深入個人化的綜合命盤分析。

西曆：{solar['year']}/{solar['month']:02d}/{solar['day']:02d} 農曆：{data['lunar'].get('display','無')}
外在命盤：天賦數{manifest['total']} 本命靈數{manifest['single']}（{m_meaning.get('name','')}）{m_meaning.get('keyword','')} 強勢：{manifest_strong_str} 空缺：{manifest_missing_str}
內在命盤：天賦數{hidden.get('total','?')} 本命靈數{hidden.get('single','?')}（{h_meaning.get('name','')}）{h_meaning.get('keyword','')} 強勢：{hidden_strong_str} 空缺：{hidden_missing_str}
綜合命盤：強勢{combined_strong_str} 空缺{combined_missing_str}

請分三部分撰寫，語氣溫暖直接，說到用戶心坎裡：

一、外在性格解析
天賦數{manifest['total']}的意義、本命靈數{manifest['single']}的外在性格與興趣愛好、空缺數影響。

二、內在精神解析
天賦數{hidden.get('total','?')}的底層驅動力、本命靈數{hidden.get('single','?')}的內在特質、強勢數雙面影響、空缺數影響。

三、綜合總結（最重要最長）
外在{manifest['single']}與內在{hidden.get('single','?')}的對話、完整性格、職業方向（融入文字）、感情模式（融入文字）、瓶頸與解法、能量失衡兩種狀態、最後一句有力量的話。"""

    return prompt


def get_ai_reading(data: dict, api_key: str) -> str:
    return call_ai(build_prompt(data), api_key, max_tokens=1200)


def get_year_detail(data: dict, api_key: str) -> str:
    py = data["personal_year_current"]
    solar = data["solar"]
    birth_single = data["manifest"]["single"]
    is_personal_year = (py["single"] == birth_single)
    monthly = data["monthly_current"]
    month_names = ["一","二","三","四","五","六","七","八","九","十","十一","十二"]
    monthly_str = "、".join([f"{month_names[i]}月={pm['single']}" for i, pm in enumerate(monthly)])

    prompt = f"""生命靈數流年分析，繁體中文，語氣溫暖直接。

出生：{solar['year']}/{solar['month']:02d}/{solar['day']:02d} 本命靈數{birth_single}（天賦數{data['manifest']['total']}）
{py['year']}年流年數{py['single']} 各月：{monthly_str}
{"本命年！流年數與生命靈數相同，能量特別強烈。" if is_personal_year else ""}

請分析：整體能量主題、事業財運、感情人際、身心健康、{"本命年說明" if is_personal_year else "上下半年"}、重點月份、今年一句話。"""

    return call_ai(prompt, api_key, max_tokens=1000)


def get_monthly_detail(data: dict, month: int, api_key: str) -> str:
    py = data["personal_year_current"]
    pm = data["monthly_current"][month - 1]
    solar = data["solar"]

    prompt = f"""生命靈數流月分析，繁體中文，溫暖積極具體。

出生：{solar['year']}/{solar['month']:02d}/{solar['day']:02d} 本命靈數{data['manifest']['single']}
{py['year']}年流年{py['single']} {month}月流月{pm['single']}

分析：整體能量、事業財運、感情人際、身心提醒、三大行動建議、幸運數字與顏色。"""

    return call_ai(prompt, api_key, max_tokens=600)
