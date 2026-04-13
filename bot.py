"""
生命靈數 Telegram Bot 主程式
"""

import os
import logging
from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler, CallbackQueryHandler
)
from numerology import full_analysis, NUMBER_MEANINGS, PERSONAL_YEAR_THEMES
from ai_reader import get_ai_reading, get_monthly_detail

# ── 設定 ──────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "")

# 對話狀態
ASK_DATE, ASK_TIME, SHOW_MENU = range(3)

# 暫存用戶數據
user_data_store = {}


# ── 訊息格式化工具 ────────────────────────────
def format_grid(grid: dict) -> str:
    """格式化命盤九宮格"""
    lines = []
    for row in [[7, 8, 9], [4, 5, 6], [1, 2, 3]]:
        parts = []
        for n in row:
            count = grid.get(n, 0)
            if count == 0:
                parts.append(f"  ◻{n} ")
            else:
                parts.append(f"  {'●' * count}{n}")
        lines.append("".join(parts))
    return "\n".join(lines)


def format_manifest(manifest: dict, meaning: dict) -> str:
    total = manifest["total"]
    single = manifest["single"]
    name = meaning.get("name", "")
    keyword = meaning.get("keyword", "")

    text = f"📅 *西曆 {manifest['date_str']}*\n"
    text += f"數字加總：`{manifest['all_digits']}` → {manifest['raw_sum']} → **{total}** → 個位 **{single}**\n\n"
    text += f"✨ *顯性命數：{total}（{single}）— {name}*\n"
    text += f"關鍵詞：{keyword}\n\n"
    text += "命盤圈數：\n```\n" + format_grid(manifest["grid"]) + "\n```\n"

    if manifest["strong_numbers"]:
        nums = "、".join([f"{k}（{v}圈）" for k, v in manifest["strong_numbers"].items()])
        text += f"\n⚡ 強勢數：{nums}\n"
    if manifest["missing_numbers"]:
        nums = "、".join(str(n) for n in manifest["missing_numbers"])
        text += f"🕳 空缺數：{nums}\n"

    return text


def format_hidden(hidden: dict, meaning: dict) -> str:
    if "error" in hidden:
        return f"⚠️ 農曆轉換失敗：{hidden['error']}"

    total = hidden["total"]
    single = hidden["single"]
    name = meaning.get("name", "")
    keyword = meaning.get("keyword", "")

    text = f"🌙 *農曆 {hidden['date_str']}*\n"
    text += f"數字加總：`{hidden['all_digits']}` → {hidden['raw_sum']} → **{total}** → 個位 **{single}**\n\n"
    text += f"🌕 *隱性命數：{total}（{single}）— {name}*\n"
    text += f"關鍵詞：{keyword}\n\n"
    text += "命盤圈數：\n```\n" + format_grid(hidden["grid"]) + "\n```\n"

    if hidden["strong_numbers"]:
        nums = "、".join([f"{k}（{v}圈）" for k, v in hidden["strong_numbers"].items()])
        text += f"\n⚡ 強勢數：{nums}\n"
    if hidden["missing_numbers"]:
        nums = "、".join(str(n) for n in hidden["missing_numbers"])
        text += f"🕳 空缺數：{nums}\n"

    return text


def format_yearly_grid(py: dict, monthly: list, year: int) -> str:
    month_names = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二"]
    text = f"📆 *{year}年流年：{py['total']}（{py['single']}）*\n"
    text += f"主題：{PERSONAL_YEAR_THEMES.get(py['single'], '')}\n\n"
    text += "*各月流月數：*\n"
    for i, pm in enumerate(monthly):
        text += f"  {month_names[i]}月：**{pm['single']}**"
        if (i + 1) % 4 == 0:
            text += "\n"
        else:
            text += "　"
    return text


# ── 指令處理 ──────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔢 *歡迎來到生命靈數分析 Bot！*\n\n"
        "我可以為你計算：\n"
        "✅ 顯性命盤（西曆）\n"
        "✅ 隱性命盤（農曆）\n"
        "✅ 命盤強勢數與空缺數分析\n"
        "✅ 適合職業與感情對象\n"
        "✅ 流年流月詳細分析\n\n"
        "請輸入指令開始：\n"
        "👉 /analyze — 開始分析\n"
        "👉 /help — 查看說明",
        parse_mode="Markdown"
    )


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


async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📅 請輸入你的*西曆出生日期*\n\n"
        "格式：YYYY/MM/DD\n"
        "範例：1990/05/15",
        parse_mode="Markdown"
    )
    return ASK_DATE


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
    user_data_store[user_id] = {"year": year, "month": month, "day": day}

    await update.message.reply_text(
        "🕐 請輸入你的*出生時辰*（24小時制，例如：14 代表下午2點）\n\n"
        "如果不知道，請輸入：略過",
        parse_mode="Markdown"
    )
    return ASK_TIME


async def receive_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    stored = user_data_store.get(user_id, {})

    birth_hour = None
    if text not in ["略過", "skip", "無", "不知道"]:
        try:
            birth_hour = int(text)
            assert 0 <= birth_hour <= 23
        except Exception:
            await update.message.reply_text("⚠️ 時間格式不正確，請輸入 0-23 之間的數字，或輸入「略過」")
            return ASK_TIME

    stored["hour"] = birth_hour
    user_data_store[user_id] = stored

    # 計算命盤
    await update.message.reply_text("⏳ 正在計算你的命盤，請稍候...")

    try:
        data = full_analysis(
            stored["year"], stored["month"], stored["day"], birth_hour
        )
        user_data_store[user_id]["analysis"] = data
    except Exception as e:
        await update.message.reply_text(f"⚠️ 計算出現問題：{e}")
        return ConversationHandler.END

    # 顯示基本命盤
    manifest_text = format_manifest(data["manifest"], data.get("manifest_meaning", {}))
    hidden_text = format_hidden(data["hidden"], data.get("hidden_meaning", {}))
    yearly_text = format_yearly_grid(
        data["personal_year_current"],
        data["monthly_current"],
        data["personal_year_current"]["year"]
    )

    await update.message.reply_text(
        "═══════════════\n"
        "🌟 *你的生命靈數命盤*\n"
        "═══════════════\n\n" +
        manifest_text,
        parse_mode="Markdown"
    )

    await update.message.reply_text(hidden_text, parse_mode="Markdown")
    await update.message.reply_text(yearly_text, parse_mode="Markdown")

    # 顯示選單按鈕
    keyboard = [
        [InlineKeyboardButton("🤖 AI深度解讀（完整分析）", callback_data="ai_full")],
        [
            InlineKeyboardButton("💼 適合職業", callback_data="career"),
            InlineKeyboardButton("💕 感情對象", callback_data="love"),
        ],
        [
            InlineKeyboardButton("📅 本月詳細流月", callback_data="month_now"),
            InlineKeyboardButton("📆 下一年流年", callback_data="next_year"),
        ],
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
    stored = user_data_store.get(user_id, {})
    data = stored.get("analysis")

    if not data:
        await query.edit_message_text("⚠️ 找不到你的分析資料，請重新輸入 /analyze")
        return SHOW_MENU

    action = query.data

    if action == "ai_full":
        await query.edit_message_text("🤖 AI 正在深度解讀你的命盤，這需要約 30 秒...")
        reading = get_ai_reading(data, CLAUDE_API_KEY)
        # 分段發送（避免超過 TG 字數限制）
        chunks = [reading[i:i+3500] for i in range(0, len(reading), 3500)]
        for i, chunk in enumerate(chunks):
            if i == 0:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"🌟 *AI 命盤深度解讀*\n\n{chunk}",
                    parse_mode="Markdown"
                )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=chunk,
                    parse_mode="Markdown"
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
            text += f"• 命數 **{n}**（{meaning.get('name', '')}）— {meaning.get('keyword', '')}\n"
        text += "\n💡 相容不代表一定合適，命盤僅供參考"
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=text, parse_mode="Markdown"
        )

    elif action == "month_now":
        current_month = date.today().month
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"📅 正在分析 {date.today().year} 年 {current_month} 月的流月..."
        )
        detail = get_monthly_detail(data, current_month, CLAUDE_API_KEY)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🗓 *{date.today().year}年{current_month}月流月分析*\n\n{detail}",
            parse_mode="Markdown"
        )

    elif action == "next_year":
        next_py = data["personal_year_next"]
        next_monthly = data["monthly_next"]
        text = format_yearly_grid(next_py, next_monthly, next_py["year"])
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=text, parse_mode="Markdown"
        )

    # 重新顯示選單
    keyboard = [
        [InlineKeyboardButton("🤖 AI深度解讀（完整分析）", callback_data="ai_full")],
        [
            InlineKeyboardButton("💼 適合職業", callback_data="career"),
            InlineKeyboardButton("💕 感情對象", callback_data="love"),
        ],
        [
            InlineKeyboardButton("📅 本月詳細流月", callback_data="month_now"),
            InlineKeyboardButton("📆 下一年流年", callback_data="next_year"),
        ],
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
    if not CLAUDE_API_KEY:
        print("警告：未設定 CLAUDE_API_KEY，AI 解讀功能將無法使用")

    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("analyze", analyze)],
        states={
            ASK_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_date)],
            ASK_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_time)],
            SHOW_MENU: [CallbackQueryHandler(handle_callback)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(conv_handler)

    print("🤖 生命靈數 Bot 已啟動...")
    app.run_polling()


if __name__ == "__main__":
    main()
