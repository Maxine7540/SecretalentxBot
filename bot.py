"""
生命靈數 Telegram Bot 主程式
"""

import os
import logging
from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler, CallbackQueryHandler
)
from numerology import full_analysis, NUMBER_MEANINGS, PERSONAL_YEAR_THEMES
from ai_reader import get_ai_reading, get_monthly_detail, get_year_detail

# ── 設定 ──────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# 對話狀態
ASK_DATE, ASK_TIME, SHOW_MENU = range(3)

# 暫存用戶數據（使用 context.user_data，跟隨 Telegram session）
# user_data_store 已棄用，改用 context.user_data


# emoji 數字對照
NUM_EMOJI = {1:"1️⃣",2:"2️⃣",3:"3️⃣",4:"4️⃣",5:"5️⃣",6:"6️⃣",7:"7️⃣",8:"8️⃣",9:"9️⃣"}


def format_grid(grid: dict, color: str = "purple") -> str:
    """格式化命盤圈數：emoji數字 + 圓點"""
    dot = "🟣" if color == "purple" else ("🟡" if color == "gold" else "🟢")
    lines = []
    for n in range(1, 10):
        count = grid.get(n, 0)
        emoji = NUM_EMOJI[n]
        if count == 0:
            lines.append(f"{emoji}  空缺")
        else:
            lines.append(f"{emoji}  {dot * count}")
    return "\n".join(lines)


def format_combined_chart(data: dict) -> str:
    """將外在性格命盤、內在精神命盤、綜合命盤合併成一個完整訊息"""
    manifest = data["manifest"]
    hidden = data["hidden"]
    m_meaning = data.get("manifest_meaning", {})
    h_meaning = data.get("hidden_meaning", {})
    solar = data["solar"]

    # 加總過程字串（西曆）
    calc_m = f"{manifest['digits_display']} = {manifest['raw_sum']}"
    if manifest.get("step2"):
        calc_m += f" → {manifest['step2']}"

    text = "✨ *靈數命盤*\n\n"

    # ── 外在性格命盤（西曆）──
    text += "☀️ *西曆生日*\n"
    text += f"{solar['year']} / {solar['month']:02d} / {solar['day']:02d}\n"
    text += f"{calc_m}\n"
    text += f"天賦數 *{manifest['total']}*　本命靈數 *{manifest['single']}*\n"
    text += f"{m_meaning.get('name', '')} — {m_meaning.get('keyword', '')}\n\n"
    text += "*外在性格命盤*\n"
    text += format_grid(manifest["grid"], "purple") + "\n\n"
    if manifest["strong_numbers"]:
        nums = "、".join([f"{k}（{v}圈）" for k, v in manifest["strong_numbers"].items()])
        text += f"⚡ 強勢數：{nums}\n"
    else:
        text += "⚡ 強勢數：無\n"
    if manifest["missing_numbers"]:
        nums = "、".join(str(n) for n in manifest["missing_numbers"])
        text += f"🕳 空缺數：{nums}\n"
    else:
        text += "🕳 空缺數：無\n"

    text += "\n━━━━━━━━━━━━━━━\n\n"

    # ── 內在精神命盤（農曆）──
    if "error" in hidden:
        text += f"🌙 *農曆生日*\n⚠️ 農曆轉換失敗：{hidden['error']}\n"
    else:
        lunar = data["lunar"]
        calc_h = f"{hidden['digits_display']} = {hidden['raw_sum']}"
        if hidden.get("step2"):
            calc_h += f" → {hidden['step2']}"

        text += f"🌙 *農曆生日*\n"
        text += f"{lunar['year']} / {lunar['month']:02d} / {lunar['day']:02d}（{lunar.get('zodiac','')}年）\n"
        text += f"{calc_h}\n"
        text += f"天賦數 *{hidden['total']}*　本命靈數 *{hidden['single']}*\n"
        text += f"{h_meaning.get('name', '')} — {h_meaning.get('keyword', '')}\n\n"
        text += "*內在精神命盤*\n"
        text += format_grid(hidden["grid"], "gold") + "\n\n"
        if hidden["strong_numbers"]:
            nums = "、".join([f"{k}（{v}圈）" for k, v in hidden["strong_numbers"].items()])
            text += f"⚡ 強勢數：{nums}\n"
        else:
            text += "⚡ 強勢數：無\n"
        if hidden["missing_numbers"]:
            nums = "、".join(str(n) for n in hidden["missing_numbers"])
            text += f"🕳 空缺數：{nums}\n"
        else:
            text += "🕳 空缺數：無\n"

    text += "\n━━━━━━━━━━━━━━━\n\n"

    # ── 綜合命盤 ──
    combined_grid = {}
    for n in range(1, 10):
        combined_grid[n] = manifest["grid"].get(n, 0) + (hidden.get("grid", {}).get(n, 0) if "error" not in hidden else 0)
    combined_strong = {k: v for k, v in combined_grid.items() if v >= 5}
    # 若無 ≥5 圈，取最多圈的數（需 ≥1）
    if not combined_strong:
        max_val = max(combined_grid.values())
        if max_val >= 1:
            combined_strong_display = "、".join([f"{k}（{v}圈）" for k, v in combined_grid.items() if v == max_val])
        else:
            combined_strong_display = "無"
    else:
        combined_strong_display = "、".join([f"{k}（{v}圈）" for k, v in combined_strong.items()])
    combined_missing = [n for n in range(1, 10) if combined_grid.get(n, 0) == 0]

    text += "*綜合命盤圈數分佈*\n"
    text += format_grid(combined_grid, "teal") + "\n\n"
    text += f"⚡ 強勢數：{combined_strong_display}\n"
    if combined_missing:
        text += f"🕳 空缺數：{'、'.join(str(n) for n in combined_missing)}\n"
    else:
        text += "🕳 空缺數：無\n"

    return text


def format_yearly_grid(py: dict, monthly: list, year: int, birth_single: int) -> str:
    is_personal_year = (py["single"] == birth_single)
    all_digits = py.get("all_digits", "")
    digits_str = "+".join(all_digits) if all_digits else ""
    raw = py.get("raw_sum", "")
    single = py["single"]

    # 計算過程：例如 2+0+2+6+0+8+1+6 = 25 → 2+5 = 7
    if raw > 9:
        second_step = "+".join(str(d) for d in str(raw))
        calc_str = f"`{digits_str} = {raw} → {second_step} = {single}`"
    else:
        calc_str = f"`{digits_str} = {single}`"

    text = f"📆 *{year}年流年*\n"
    text += f"{calc_str}\n"
    text += f"流年數 *{single}*　{PERSONAL_YEAR_THEMES.get(single, '')}\n"
    if is_personal_year:
        text += "⭐ 本命年！能量特別強烈\n"
    text += "\n💡 點下方按鈕查看流年詳解或各月流月分析"
    return text


# ── 指令處理 ──────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("開始")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "✨ 歡迎來到生命靈數 Bot！\n\n"
        "我可以為你找出你的隱藏天賦：\n"
        "☀️ 外在性格命盤\n"
        "🌙 內在精神命盤\n"
        "🔮 綜合命盤深度解析\n\n"
        "📅 請輸入你的西曆出生日期\n"
        "格式：YYYY/MM/DD\n"
        "範例：1990/05/15",
        reply_markup=reply_markup
    )
    return ASK_DATE


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *使用說明*\n\n"
        "1. 輸入 /analyze 開始\n"
        "2. 輸入你的西曆出生日期（格式：YYYY/MM/DD）\n"
        "   例如：1990/05/15\n"
        "3. 輸入出生時辰（或輸入「略過」）\n"
        "4. 選擇你想要的分析類型\n\n"
        "💡 所有分析均免費使用",
        parse_mode="Markdown"
    )



async def receive_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace("-", "/").replace(".", "/")
    try:
        parts = text.split("/")
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        assert 1900 <= year <= 2100
        assert 1 <= month <= 12
        assert 1 <= day <= 31
    except Exception:
        await update.message.reply_text(
            "⚠️ 日期格式不正確，請重新輸入\n例如：1990/05/15"
        )
        return ASK_DATE

    user_id = update.effective_user.id
    context.user_data["year"] = year
    context.user_data["month"] = month
    context.user_data["day"] = day

    await update.message.reply_text(
        "🕐 請輸入你的*出生時辰*（24小時制，例如：14 代表下午2點）\n\n"
        "如果不知道，請輸入：略過",
        parse_mode="Markdown"
    )
    return ASK_TIME


async def receive_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    stored = context.user_data

    birth_hour = None
    if text not in ["略過", "skip", "無", "不知道"]:
        try:
            birth_hour = int(text)
            assert 0 <= birth_hour <= 23
        except Exception:
            await update.message.reply_text("⚠️ 時間格式不正確，請輸入 0-23 之間的數字，或輸入「略過」")
            return ASK_TIME

    context.user_data["hour"] = birth_hour

    # 計算命盤
    await update.message.reply_text("⏳ 正在計算你的命盤，請稍候...")

    try:
        data = full_analysis(
            stored["year"], stored["month"], stored["day"], birth_hour
        )
        context.user_data["analysis"] = data
    except Exception as e:
        await update.message.reply_text(f"⚠️ 計算出現問題：{e}")
        return ConversationHandler.END

    # 顯示合併命盤（顯性＋隱性合為一則）
    combined_text = format_combined_chart(data)
    yearly_text = format_yearly_grid(
        data["personal_year_current"],
        data["monthly_current"],
        data["personal_year_current"]["year"],
        data["manifest"]["single"]
    )

    await update.message.reply_text(combined_text, parse_mode="Markdown")
    await update.message.reply_text(yearly_text, parse_mode="Markdown")

    # 顯示選單按鈕
    keyboard = [
        [InlineKeyboardButton("🔮 綜合命盤分析", callback_data="ai_full")],
        [
            InlineKeyboardButton("💼 適合職業", callback_data="career"),
            InlineKeyboardButton("💕 感情對象", callback_data="love"),
        ],
        [
            InlineKeyboardButton("📅 流年詳解", callback_data="year_detail"),
            InlineKeyboardButton("📆 下一年流年", callback_data="next_year"),
        ],
        [InlineKeyboardButton("🗓 選擇流月分析", callback_data="month_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "請選擇你想要深入了解的內容：",
        reply_markup=reply_markup
    )
    return SHOW_MENU


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    stored = context.user_data
    data = stored.get("analysis")

    if not data:
        await query.edit_message_text("⚠️ 找不到你的分析資料，請重新輸入 /analyze")
        return SHOW_MENU

    action = query.data

    if action == "ai_full":
        await query.edit_message_text("🔮 正在進行綜合命盤分析，請稍候約 60 秒，請勿重複點擊...")
        try:
            reading = get_ai_reading(data, GROQ_API_KEY)
            chunks = [reading[i:i+4000] for i in range(0, len(reading), 4000)]
            for i, chunk in enumerate(chunks):
                header = "🔮 綜合命盤分析\n\n" if i == 0 else ""
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"{header}{chunk}",
                )
        except Exception as e:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚠️ 分析出錯，請稍後再試。\n錯誤：{str(e)[:100]}"
            )

    elif action == "career":
        careers = data.get("careers", [])
        single = data["manifest"]["single"]
        text = f"💼 *適合從事的職業方向*\n\n"
        text += f"你的命數 {single} 最適合：\n\n"
        for i, c in enumerate(careers, 1):
            text += f"{i}. {c}\n"
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=text, parse_mode="Markdown"
        )

    elif action == "love":
        compatible = data.get("compatible_numbers", [])
        single = data["manifest"]["single"]
        text = f"💕 *感情相容分析*\n\n"
        text += f"你的命數 {single} 最相容的對象：\n\n"
        for n in compatible:
            meaning = NUMBER_MEANINGS.get(n, {})
            text += f"• 命數 *{n}*（{meaning.get('name', '')}）— {meaning.get('keyword', '')}\n"
        text += "\n💡 相容不代表一定合適，命盤僅供參考"
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=text, parse_mode="Markdown"
        )

    elif action == "year_detail":
        py = data["personal_year_current"]
        await query.edit_message_text(f"📅 正在分析 {py['year']} 年流年詳解，請稍候...")
        detail = get_year_detail(data, GROQ_API_KEY)
        chunks = [detail[i:i+4000] for i in range(0, len(detail), 4000)]
        for chunk in chunks:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=chunk,
                )
            except Exception:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=chunk[:4000],
                )

    elif action == "month_menu":
        # 顯示12個月份按鈕
        month_names = ["1月","2月","3月","4月","5月","6月","7月","8月","9月","10月","11月","12月"]
        monthly = data["monthly_current"]
        keyboard = []
        row = []
        for i, pm in enumerate(monthly):
            row.append(InlineKeyboardButton(
                f"{month_names[i]}（{pm['single']}）",
                callback_data=f"month_{i+1}"
            ))
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🗓 *{data['personal_year_current']['year']}年 — 選擇要分析的月份：*\n括號內為該月流月數",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return SHOW_MENU

    elif action.startswith("month_"):
        target_month = int(action.split("_")[1])
        year = data["personal_year_current"]["year"]
        await query.edit_message_text(f"📅 正在分析 {year} 年 {target_month} 月的流月，請稍候約15秒...")
        detail = get_monthly_detail(data, target_month, GROQ_API_KEY)
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🗓 {year}年{target_month}月流月分析\n\n{detail}",
            )
        except Exception:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=detail[:4000],
            )

    elif action == "next_year":
        next_py = data["personal_year_next"]
        next_monthly = data["monthly_next"]
        birth_single = data["manifest"]["single"]
        text = format_yearly_grid(next_py, next_monthly, next_py["year"], birth_single)
        # 附上12個月流月數一覽
        month_names = ["一","二","三","四","五","六","七","八","九","十","十一","十二"]
        text += "\n\n*各月流月數一覽：*\n"
        for i, pm in enumerate(next_monthly):
            text += f"  {month_names[i]}月：{pm['single']}"
            if (i + 1) % 4 == 0:
                text += "\n"
            else:
                text += "　　"
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=text, parse_mode="Markdown"
        )

    # 重新顯示選單
    keyboard = [
        [InlineKeyboardButton("🔮 綜合命盤分析", callback_data="ai_full")],
        [
            InlineKeyboardButton("💼 適合職業", callback_data="career"),
            InlineKeyboardButton("💕 感情對象", callback_data="love"),
        ],
        [
            InlineKeyboardButton("📅 流年詳解", callback_data="year_detail"),
            InlineKeyboardButton("📆 下一年流年", callback_data="next_year"),
        ],
        [InlineKeyboardButton("🗓 選擇流月分析", callback_data="month_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="還想了解什麼？",
        reply_markup=reply_markup
    )
    return SHOW_MENU


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("已取消。輸入 /analyze 重新開始。")
    return ConversationHandler.END


# ── 主程式 ────────────────────────────────────
def main():
    if not BOT_TOKEN:
        print("錯誤：請設定環境變數 BOT_TOKEN")
        return
    if not GROQ_API_KEY:
        print("警告：未設定 GROQ_API_KEY，AI 解讀功能將無法使用")

    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("analyze", start),
            MessageHandler(filters.Regex("^開始$"), start),
        ],
        states={
            ASK_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_date)],
            ASK_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_time)],
            SHOW_MENU: [CallbackQueryHandler(handle_callback)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_cmd))

    print("🤖 生命靈數 Bot 已啟動...")
    app.run_polling()


if __name__ == "__main__":
    main()
