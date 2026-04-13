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
各位相加總數：{manifest['raw_sum']} → 總數：{manifest['total']} → 個位數：{manifest['single']}
命盤含義：{manifest['total']} = {data.get('manifest_meaning', {}).get('name', '')}（{data.get('manifest_meaning', {}).get('keyword', '')}）
命盤圈數分佈：{manifest['grid']}
強勢數（≥5圈）：{manifest['strong_numbers'] if manifest['strong_numbers'] else '無'}
空缺數：{manifest['missing_numbers'] if manifest['missing_numbers'] else '無'}

【隱性命盤（農曆）】
原始數字串：{hidden.get('all_digits', '無')}
各位相加總數：{hidden.get('raw_sum', '無')} → 總數：{hidden.get('total', '無')} → 個位數：{hidden.get('single', '無')}
命盤含義：{hidden.get('total', '')} = {data.get('hidden_meaning', {}).get('name', '')}（{data.get('hidden_meaning', {}).get('keyword', '')}）

【流年資料（今年 {data['personal_year_current']['year']}）】
流年數：{data['personal_year_current']['total']}（個位 {data['personal_year_current']['single']}）
今年主題：{data['year_theme']}

請按以下結構分析，每個部分都要具體且有溫度，避免空泛的描述：

**一、顯性命盤深度解析**
解讀總數 {manifest['total']} 與個位 {manifest['single']} 的意涵，這個人的核心性格、人生課題與天賦。

**二、隱性命盤解析**
隱性命盤反映潛意識層面的特質，與顯性命盤的互補或張力。

**三、命盤特殊影響**
- 若有強勢數（圈數≥5）：說明這個數字過度強化帶來的特質與挑戰
- 空缺數的影響：需要學習和補足的課題

**四、適合從事的工作**
根據命盤推薦 5 個最適合的職業方向，並說明原因。

**五、感情與人際**
- 最相容的生命靈數類型（{data['compatible_numbers']}）及原因
- 感情模式與注意事項

**六、流年分析（{data['personal_year_current']['year']}年）**
今年的整體能量、重點方向、機會與挑戰。
列出上半年（1-6月）與下半年（7-12月）的重點月份分析。

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


def get_monthly_detail(data: dict, month: int, api_key: str) -> str:
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
