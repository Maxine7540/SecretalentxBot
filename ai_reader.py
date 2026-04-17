"""
AI 解讀模組 - 使用 Groq API（免費）
"""

import urllib.request
import urllib.error
import json


def call_ai(prompt: str, api_key: str, max_tokens: int = 3500) -> str:
    """呼叫 Groq API"""
    if not api_key:
        raise ValueError("GROQ_API_KEY 未設定，請在 Railway Variables 中加入")

    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = json.dumps({
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.8
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        raise Exception(f"API 錯誤 {e.code}: {body[:300]}")


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

西曆生日：{solar['year']}/{solar['month']:02d}/{solar['day']:02d}
農曆生日：{data['lunar'].get('display', '無法轉換')}

外在命盤：天賦數{manifest['total']} 本命靈數{manifest['single']}（{m_meaning.get('name','')}）關鍵詞：{m_meaning.get('keyword','')}
圈數：{dict(sorted(manifest['grid'].items()))} 強勢數：{manifest_strong_str} 空缺：{manifest_missing_str}

內在命盤：天賦數{hidden.get('total','?')} 本命靈數{hidden.get('single','?')}（{h_meaning.get('name','')}）關鍵詞：{h_meaning.get('keyword','')}
圈數：{dict(sorted(hidden.get('grid',{}).items()))} 強勢數：{hidden_strong_str} 空缺：{hidden_missing_str}

綜合命盤：圈數{dict(sorted(combined_grid.items()))} 強勢數：{combined_strong_str} 空缺：{combined_missing_str}

請按三個部分撰寫，語氣溫暖直接，適時幽默，說到用戶心坎裡：

一、外在性格解析（西曆命盤）
涵蓋：天賦數{manifest['total']}的深層意義、本命靈數{manifest['single']}的外在性格與行為模式、興趣愛好傾向、空缺數{manifest_missing_str}的具體影響與補足方向。性格描述要全面真實。

二、內在精神解析（農曆命盤）
涵蓋：天賦數{hidden.get('total','?')}的底層驅動力、本命靈數{hidden.get('single','?')}的內在特質與真實動機、強勢數的雙面影響、空缺數在關係與決策中的顯現。讓人感覺「你看穿了我」。

三、綜合命盤總結（最重要，篇幅最長）
涵蓋：外在靈數{manifest['single']}與內在靈數{hidden.get('single','?')}的核心對話、完整性格描述、興趣愛好、強勢數主導影響、適合職業（融入文字）、感情模式與理想伴侶（融入文字）、常見瓶頸與解決方式、能量失衡的兩種狀態與解藥、最後一句有力量的話作結。

格式：三個部分各有標題，段落間空行，流暢段落文字。"""

    return prompt


def get_ai_reading(data: dict, api_key: str) -> str:
    """生成綜合命盤解讀"""
    return call_ai(build_prompt(data), api_key, max_tokens=3500)


def get_year_detail(data: dict, api_key: str) -> str:
    """流年詳細分析"""
    py = data["personal_year_current"]
    solar = data["solar"]
    birth_single = data["manifest"]["single"]
    is_personal_year = (py["single"] == birth_single)
    monthly = data["monthly_current"]
    month_names = ["一","二","三","四","五","六","七","八","九","十","十一","十二"]
    monthly_str = "、".join([f"{month_names[i]}月={pm['single']}" for i, pm in enumerate(monthly)])
    personal_year_note = f"\n注意：這是本命年，流年數={birth_single}與生命靈數相同，能量特別強烈，請重點說明。" if is_personal_year else ""

    prompt = f"""你是生命靈數分析師，請用繁體中文做詳細流年分析，語氣溫暖直接具體。

出生：{solar['year']}/{solar['month']:02d}/{solar['day']:02d} 本命靈數：{birth_single}（天賦數{data['manifest']['total']}）
{py['year']}年流年數：{py['single']}（天賦數{py['total']}）各月流月：{monthly_str}{personal_year_note}

請分析：整體能量與主題、事業財運、感情人際、身心健康、{"本命年特別說明" if is_personal_year else "上下半年分析"}、重點月份、今年一句話。"""

    return call_ai(prompt, api_key, max_tokens=1500)


def get_monthly_detail(data: dict, month: int, api_key: str) -> str:
    """單月詳細流月分析"""
    py = data["personal_year_current"]
    pm = data["monthly_current"][month - 1]
    solar = data["solar"]

    prompt = f"""你是生命靈數分析師，請用繁體中文分析流月，語氣溫暖積極具體。

出生：{solar['year']}/{solar['month']:02d}/{solar['day']:02d} 本命靈數：{data['manifest']['single']}
{py['year']}年流年數：{py['single']} {py['year']}年{month}月流月數：{pm['single']}

請分析：整體能量、事業財運、感情人際、身心提醒、本月三大行動建議、幸運數字與顏色。"""

    return call_ai(prompt, api_key, max_tokens=800)
