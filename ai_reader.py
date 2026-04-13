"""
AI 解讀模組
使用 Claude API 根據命盤數據生成深度分析
"""

import anthropic
import json


def build_prompt(data: dict) -> str:
    manifest = data["manifest"]
    hidden = data["hidden"]
    solar = data["solar"]

    prompt = f"""你是一位專業的生命靈數分析師，請根據以下命盤數據，用繁體中文提供深入且個人化的分析。

【基本資料】
西曆生日：{solar['year']}/{solar['month']:02d}/{solar['day']:02d}
農曆生日：{data['lunar'].get('display', '無法轉換')}
{'出生時辰：' + str(solar['hour']) + '時' if solar.get('hour') is not None else ''}

【顯性命盤（西曆）】
原始數字串：{manifest['all_digits']}
加總：{manifest['raw_sum']} → 總數：{manifest['total']} → 個位數：{manifest['single']}
含義：{manifest['total']} = {data.get('manifest_meaning', {}).get('name', '')}（{data.get('manifest_meaning', {}).get('keyword', '')}）
圈數分佈：{manifest['grid']}
強勢數（≥5圈）：{manifest['strong_numbers'] if manifest['strong_numbers'] else '無'}
空缺數：{manifest['missing_numbers'] if manifest['missing_numbers'] else '無'}

【隱性命盤（農曆）】
原始數字串：{hidden.get('all_digits', '無')}
加總：{hidden.get('raw_sum', '無')} → 總數：{hidden.get('total', '無')} → 個位數：{hidden.get('single', '無')}
含義：{hidden.get('total', '')} = {data.get('hidden_meaning', {}).get('name', '')}（{data.get('hidden_meaning', {}).get('keyword', '')}）
圈數分佈：{hidden.get('grid', {})}
強勢數（≥5圈）：{hidden.get('strong_numbers') if hidden.get('strong_numbers') else '無'}
空缺數：{hidden.get('missing_numbers') if hidden.get('missing_numbers') else '無'}

【流年資料（今年 {data['personal_year_current']['year']}）】
流年數：{data['personal_year_current']['total']}（個位 {data['personal_year_current']['single']}）
今年主題：{data['year_theme']}

請按以下結構分析，每個部分都要具體且有溫度，避免空泛的描述。
⚠️ 重要：顯性命盤與隱性命盤必須合併一起解讀，不可拆開分析。每個部分都要同時考慮兩個命盤的互動與影響。

**一、顯性＋隱性命盤綜合解析**
同時解讀顯性命數（西曆{manifest['total']}/{manifest['single']}）與隱性命數（農曆{hidden.get('total', '?')}/{hidden.get('single', '?')}）：
- 兩個命盤呈現的核心性格與天賦
- 顯性（外在表現）與隱性（內在驅動）之間的關係：是互補、共鳴還是張力？
- 這個組合對人生方向的整體影響

**二、命盤特殊能量**
綜合兩個命盤分析：
- 強勢數帶來的特質與挑戰（若有）
- 空缺數反映的人生課題與補足方向
- 兩個命盤的空缺或強勢數若有重疊，說明其加乘效果

**三、適合從事的工作**
根據顯性＋隱性命盤合併推薦 5 個最適合的職業方向，說明為何這個組合適合這些職業。

**四、感情與人際**
- 最相容的生命靈數類型（{data['compatible_numbers']}）及原因
- 結合兩個命盤說明感情模式、需要注意的事項

**五、流年分析（{data['personal_year_current']['year']}年）**
今年的整體能量、重點方向、機會與挑戰。
列出上半年（1-6月）與下半年（7-12月）的重點月份分析。

**六、給自己的一句話**
用一段溫暖有力量的話，總結這個顯性＋隱性命盤組合的核心人生訊息。

語氣要真誠、具體，避免過於玄秘，讓沒有靈數基礎的人也能理解。"""

    return prompt

**七、給自己的一句話**
用一段溫暖有力量的話總結這個命盤的核心訊息。

語氣要真誠、具體，避免過於玄秘，讓沒有靈數基礎的人也能理解。"""

    return prompt


def get_ai_reading(data: dict, api_key: str) -> str:
    """
    呼叫 Claude API 生成命盤解讀
    """
    client = anthropic.Anthropic(api_key=api_key)
    prompt = build_prompt(data)

    try:
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=2500,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        return f"AI 解讀暫時無法使用：{str(e)}\n\n請稍後再試，或聯絡管理員。"


def get_year_detail(data: dict, api_key: str) -> str:
    """
    流年詳細分析，包含本命年說明
    """
    client = anthropic.Anthropic(api_key=api_key)
    py = data["personal_year_current"]
    solar = data["solar"]
    birth_single = data["manifest"]["single"]
    is_personal_year = (py["single"] == birth_single)
    monthly = data["monthly_current"]
    month_names = ["一","二","三","四","五","六","七","八","九","十","十一","十二"]
    monthly_str = "、".join([f"{month_names[i]}月={pm['single']}" for i, pm in enumerate(monthly)])

    personal_year_note = ""
    if is_personal_year:
        personal_year_note = f"\n⭐ 特別注意：這是命主的本命年（流年數={birth_single}，與生命靈數相同），能量特別強烈，請在本命年段落中重點說明本命年的意義與注意事項。"

    prompt = f"""你是生命靈數分析師。請用繁體中文為以下命主做詳細的流年分析。

出生日期：{solar['year']}/{solar['month']:02d}/{solar['day']:02d}
生命靈數（主命數）：{birth_single}（總數 {data['manifest']['total']}）
{py['year']}年流年數：{py['single']}（總數 {py['total']}）
各月流月數：{monthly_str}
{personal_year_note}

請按以下結構分析，內容要具體、有深度：

**{py['year']}年流年數 {py['single']} 完整解析**

**一、今年整體能量與主題**
深入說明流年數 {py['single']} 的意義，這一年的核心能量是什麼，適合做什麼、不適合做什麼（4-5句）

**二、事業與財運**
今年在事業發展、財務機會上的具體建議（3-4句）

**三、感情與人際關係**
感情運勢、人際互動的重點提醒（3-4句）

**四、健康與身心**
需要特別注意的健康方向（2-3句）

{"**五、本命年特別說明**\\n本命年意味著什麼？會帶來哪些特殊的機遇與挑戰？如何善用本命年的能量？（4-5句）" if is_personal_year else "**五、上下半年重點**"}

**六、各季度重點月份**
根據流月數，指出今年最重要的3-4個月份及其意義

**七、給自己的年度一句話**
一段有力量的總結"""

    try:
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        return f"流年分析暫時無法使用：{str(e)}"


(data: dict, month: int, api_key: str) -> str:
    """
    單月詳細流月分析
    """
    client = anthropic.Anthropic(api_key=api_key)
    py = data["personal_year_current"]
    monthly = data["monthly_current"]
    pm = monthly[month - 1]
    solar = data["solar"]

    prompt = f"""你是生命靈數分析師。請用繁體中文分析以下流月詳情：

出生日期：{solar['year']}/{solar['month']:02d}/{solar['day']:02d}
命主生命靈數：{data['manifest']['single']}（總數 {data['manifest']['total']}）
今年流年數：{py['single']}（{data['year_theme']}）
{py['year']}年{month}月流月數：{pm['single']}（總數 {pm['total']}）

請分析這個流月的：
1. 整體能量與主題（3-4句）
2. 事業財運方向（2-3句）
3. 感情人際提示（2-3句）
4. 健康注意事項（1-2句）
5. 本月最佳行動建議（列3點）
6. 幸運數字與顏色

語氣積極正向，具體可行。"""

    try:
        message = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        return f"流月分析暫時無法使用：{str(e)}"
