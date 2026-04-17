"""
生命靈數核心計算引擎
支援：顯性命盤、隱性命盤、圈數/空缺、流年流月
"""

from lunardate import LunarDate
from datetime import date


# ───────────────────────────────────────────────
# 數字加總（持續相加至 ≤ 22 或個位數）
# ───────────────────────────────────────────────
def digit_sum(n: int) -> int:
    """將數字各位相加，直到得到個位數（1-9）"""
    while n > 9:
        n = sum(int(d) for d in str(n))
    return n


def reduce_to_single(n: int):
    """
    返回 (天賦數, 本命靈數)
    天賦數 = 第一次加總後的兩位數（保留，不再縮減）
    本命靈數 = 繼續縮到個位數（1-9）
    特例：11、22 為主命數，保留不縮
    """
    # 第一步：把所有位數加到兩位數（≤99）
    total = n
    while total > 99:
        total = sum(int(d) for d in str(total))

    # 本命靈數：繼續縮到個位數，但保留 11、22 主命數
    single = total
    if single not in (11, 22):
        while single > 9:
            single = sum(int(d) for d in str(single))

    return total, single


# ───────────────────────────────────────────────
# 農曆轉換
# ───────────────────────────────────────────────
ZODIAC_LIST = ["鼠","牛","虎","兔","龍","蛇","馬","羊","猴","雞","狗","豬"]

def solar_to_lunar(year: int, month: int, day: int) -> dict:
    """西曆轉農曆，返回農曆年月日及生肖"""
    try:
        lunar = LunarDate.fromSolarDate(year, month, day)
        zodiac = ZODIAC_LIST[(lunar.year - 4) % 12]
        return {
            "year": lunar.year,
            "month": lunar.month,
            "day": lunar.day,
            "is_leap_month": lunar.isLeapMonth,
            "zodiac": zodiac,
            "display": f"{lunar.year}年{'閏' if lunar.isLeapMonth else ''}{lunar.month}月{lunar.day}日（{zodiac}年）"
        }
    except Exception as e:
        return {"error": str(e)}


# ───────────────────────────────────────────────
# 命盤計算
# ───────────────────────────────────────────────
def calc_manifest_chart(year: int, month: int, day: int) -> dict:
    """
    外在性格命盤：用西曆生日計算
    將 YYYY + MM + DD 所有數字相加，本命靈數額外加一圈
    """
    all_digits = f"{year}{month:02d}{day:02d}"
    raw_sum = sum(int(d) for d in all_digits)
    total, single = reduce_to_single(raw_sum)

    # 命盤圈數第一層：生日數字串（0不計）
    grid = {}
    for d in all_digits:
        if d != '0':
            grid[int(d)] = grid.get(int(d), 0) + 1

    # 命盤圈數第二層：天賦數（total）的各位數字（0不計）
    for d in str(total):
        if d != '0':
            grid[int(d)] = grid.get(int(d), 0) + 1

    # 命盤圈數第三層：本命靈數（single）額外再加一圈
    grid[single] = grid.get(single, 0) + 1

    # 強勢數（單盤 ≥3 圈）
    strong = {k: v for k, v in grid.items() if v >= 3}
    # 空缺數（1-9 中未出現的）
    missing = [i for i in range(1, 10) if i not in grid]

    # 計算過程：每個數字用 + 連接，顯示 raw_sum，再顯示 total 拆解
    digits_display = "+".join(list(all_digits))
    # 第二步拆解：如 34 → 3+4 = 7
    if total > 9:
        step2 = "+".join(list(str(total))) + f" = {single}"
    else:
        step2 = None

    return {
        "date_str": f"{year}/{month:02d}/{day:02d}",
        "all_digits": all_digits,
        "digits_display": digits_display,
        "raw_sum": raw_sum,
        "total": total,
        "single": single,
        "step2": step2,
        "grid": grid,
        "strong_numbers": strong,
        "missing_numbers": missing,
    }


def calc_hidden_chart(lunar: dict) -> dict:
    """內在精神命盤：用農曆生日計算，本命靈數額外加一圈"""
    if "error" in lunar:
        return {"error": lunar["error"]}

    year = lunar["year"]
    month = lunar["month"]
    day = lunar["day"]

    all_digits = f"{year}{month:02d}{day:02d}"
    raw_sum = sum(int(d) for d in all_digits)
    total, single = reduce_to_single(raw_sum)

    # 命盤圈數第一層：生日數字串（0不計）
    grid = {}
    for d in all_digits:
        if d != '0':
            grid[int(d)] = grid.get(int(d), 0) + 1

    # 命盤圈數第二層：天賦數（total）的各位數字（0不計）
    for d in str(total):
        if d != '0':
            grid[int(d)] = grid.get(int(d), 0) + 1

    # 命盤圈數第三層：本命靈數（single）額外再加一圈
    grid[single] = grid.get(single, 0) + 1

    strong = {k: v for k, v in grid.items() if v >= 3}
    missing = [i for i in range(1, 10) if i not in grid]

    digits_display = "+".join(list(all_digits))
    if total > 9:
        step2 = "+".join(list(str(total))) + f" = {single}"
    else:
        step2 = None

    return {
        "date_str": lunar["display"],
        "all_digits": all_digits,
        "digits_display": digits_display,
        "raw_sum": raw_sum,
        "total": total,
        "single": single,
        "step2": step2,
        "grid": grid,
        "strong_numbers": strong,
        "missing_numbers": missing,
    }


# ───────────────────────────────────────────────
# 流年流月
# ───────────────────────────────────────────────
def calc_personal_year(birth_month: int, birth_day: int, target_year: int) -> dict:
    """計算流年數：年份所有數字 + 月 + 日"""
    all_digits = f"{target_year}{birth_month:02d}{birth_day:02d}"
    raw_sum = sum(int(d) for d in all_digits)
    total, single = reduce_to_single(raw_sum)
    return {"year": target_year, "total": total, "single": single, "raw_sum": raw_sum, "all_digits": all_digits}


def calc_personal_month(personal_year_single: int, target_month: int) -> dict:
    """計算流月數"""
    raw = personal_year_single + target_month
    total, single = reduce_to_single(raw)
    return {"month": target_month, "total": total, "single": single}


def calc_yearly_monthly_grid(birth_month: int, birth_day: int, target_year: int) -> list:
    """計算一整年的流月"""
    py = calc_personal_year(birth_month, birth_day, target_year)
    months = []
    for m in range(1, 13):
        pm = calc_personal_month(py["single"], m)
        months.append(pm)
    return py, months


# ───────────────────────────────────────────────
# 數字含義對照表（生命靈數 1-9 及主命數 10-22）
# ───────────────────────────────────────────────
NUMBER_MEANINGS = {
    1: {"name": "領袖數", "element": "太陽", "keyword": "獨立、創新、開創"},
    2: {"name": "合作數", "element": "月亮", "keyword": "協調、敏感、外交"},
    3: {"name": "創意數", "element": "木星", "keyword": "表達、藝術、社交"},
    4: {"name": "穩定數", "element": "天王星", "keyword": "務實、紀律、建設"},
    5: {"name": "自由數", "element": "水星", "keyword": "變化、冒險、溝通"},
    6: {"name": "責任數", "element": "金星", "keyword": "家庭、療癒、美感"},
    7: {"name": "智慧數", "element": "海王星", "keyword": "分析、靈性、研究"},
    8: {"name": "豐盛數", "element": "土星", "keyword": "事業、財富、權威"},
    9: {"name": "博愛數", "element": "火星", "keyword": "慈悲、完成、國際"},
    11: {"name": "直覺主命數", "element": "月亮/太陽", "keyword": "靈感、啟示、靈媒"},
    22: {"name": "建設主命數", "element": "土星/天王星", "keyword": "宏觀、落地、偉大工程"},
}

CAREER_MAP = {
    1: ["創業家", "執行長", "導演", "政治家", "運動員"],
    2: ["外交官", "諮商師", "護理師", "人資", "調解員"],
    3: ["作家", "演員", "設計師", "老師", "行銷"],
    4: ["工程師", "會計師", "建築師", "專案管理", "律師"],
    5: ["記者", "旅遊業", "銷售", "翻譯", "自由工作者"],
    6: ["醫師", "社工", "美容師", "室內設計", "廚師"],
    7: ["研究員", "哲學家", "心理學家", "科學家", "占星師"],
    8: ["企業家", "金融業", "不動產", "管理階層", "投資人"],
    9: ["慈善家", "藝術家", "外交官", "牧師/靈性導師", "國際NGO"],
    11: ["靈性導師", "心理諮商", "藝術家", "發明家", "預言家"],
    22: ["建築師", "政策制定者", "工程師", "企業顧問", "社會改革者"],
}

COMPATIBILITY_MAP = {
    1: [1, 3, 5],
    2: [2, 4, 8],
    3: [1, 3, 6, 9],
    4: [2, 4, 8],
    5: [1, 5, 7],
    6: [3, 6, 9],
    7: [5, 7, 11],
    8: [2, 4, 8],
    9: [3, 6, 9],
    11: [2, 7, 11, 22],
    22: [4, 8, 11, 22],
}

PERSONAL_YEAR_THEMES = {
    1: "新週期開始，播種與行動之年",
    2: "耐心等待，關係與合作之年",
    3: "表達自我，創意與社交之年",
    4: "努力建設，打基礎的一年",
    5: "改變與自由，突破舒適圈之年",
    6: "責任與家庭，療癒修復之年",
    7: "內省與靈性成長之年",
    8: "豐收與成就，財務事業之年",
    9: "結束與放下，完成循環之年",
}


def full_analysis(
    solar_year: int, solar_month: int, solar_day: int,
    birth_hour: int = None
) -> dict:
    """
    完整分析：返回所有命盤資料供 AI 解讀使用
    """
    lunar = solar_to_lunar(solar_year, solar_month, solar_day)
    manifest = calc_manifest_chart(solar_year, solar_month, solar_day)
    hidden = calc_hidden_chart(lunar)

    current_year = date.today().year
    py, monthly = calc_yearly_monthly_grid(solar_month, solar_day, current_year)
    next_py, next_monthly = calc_yearly_monthly_grid(solar_month, solar_day, current_year + 1)

    manifest_single = manifest["single"]
    careers = CAREER_MAP.get(manifest_single, CAREER_MAP.get(manifest["total"], []))
    compatible = COMPATIBILITY_MAP.get(manifest_single, [])

    return {
        "solar": {"year": solar_year, "month": solar_month, "day": solar_day, "hour": birth_hour},
        "lunar": lunar,
        "manifest": manifest,
        "hidden": hidden,
        "manifest_meaning": NUMBER_MEANINGS.get(manifest["total"], NUMBER_MEANINGS.get(manifest_single, {})),
        "hidden_meaning": NUMBER_MEANINGS.get(hidden.get("total"), NUMBER_MEANINGS.get(hidden.get("single"), {})),
        "careers": careers,
        "compatible_numbers": compatible,
        "personal_year_current": py,
        "monthly_current": monthly,
        "personal_year_next": next_py,
        "monthly_next": next_monthly,
        "year_theme": PERSONAL_YEAR_THEMES.get(py["single"], ""),
    }