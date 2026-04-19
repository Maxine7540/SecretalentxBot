"""
生命靈數 Telegram Bot — 多語言版
"""

import os
import logging
from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler, CallbackQueryHandler
)
from numerology import full_analysis, NUMBER_MEANINGS
from ai_reader import get_ai_reading, get_monthly_detail, get_year_detail
from career_data import format_career_text
from reading_data import format_outer_reading, format_inner_reading
from i18n import t, SUPPORTED_LANGUAGES, AVAILABLE_LANGUAGES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

ASK_DATE, ASK_TIME, SHOW_MENU = range(3)

NUM_EMOJI = {1:"1️⃣",2:"2️⃣",3:"3️⃣",4:"4️⃣",5:"5️⃣",6:"6️⃣",7:"7️⃣",8:"8️⃣",9:"9️⃣"}


def get_lang(context) -> str:
    return context.user_data.get("lang", "zh_tw")


def format_grid(grid: dict, color: str = "purple", lang: str = "zh_tw") -> str:
    dot = "🟣" if color == "purple" else ("🟡" if color == "gold" else "🟢")
    empty_label = t("empty", lang)
    lines = []
    for n in range(1, 10):
        count = grid.get(n, 0)
        emoji = NUM_EMOJI[n]
        if count == 0:
            lines.append(f"{emoji}  {empty_label}")
        else:
            lines.append(f"{emoji}  {dot * count}")
    return "\n".join(lines)


def format_combined_chart(data: dict, lang: str = "zh_tw") -> str:
    manifest = data["manifest"]
    hidden = data["hidden"]
    m_meaning = data.get("manifest_meaning", {})
    h_meaning = data.get("hidden_meaning", {})
    solar = data["solar"]

    calc_m = f"{manifest['digits_display']} = {manifest['raw_sum']}"
    if manifest.get("step2"):
        calc_m += f" → {manifest['step2']}"

    text = f"✨ {t('chart_title', lang)}\n\n"
    text += f"{t('solar_label', lang)}\n"
    text += f"{solar['year']} / {solar['month']:02d} / {solar['day']:02d}\n"
    text += f"{calc_m}\n"
    text += f"{t('talent_number', lang)} *{manifest['total']}*　{t('life_number', lang)} *{manifest['single']}*\n"
    text += f"{m_meaning.get('name', '')} — {m_meaning.get('keyword', '')}\n\n"
    text += f"*{t('outer_chart', lang)}*\n"
    text += format_grid(manifest["grid"], "purple", lang) + "\n\n"
    if manifest["strong_numbers"]:
        nums = "、".join([f"{k}（{v}圈）" for k, v in manifest["strong_numbers"].items()])
        text += f"{t('strong_number', lang)}：{nums}\n"
    else:
        text += f"{t('strong_number', lang)}：{t('none', lang)}\n"
    if manifest["missing_numbers"]:
        text += f"{t('missing_number', lang)}：{'、'.join(str(n) for n in manifest['missing_numbers'])}\n"
    else:
        text += f"{t('missing_number', lang)}：{t('none', lang)}\n"

    text += "\n━━━━━━━━━━━━━━━\n\n"

    if "error" in hidden:
        text += f"{t('lunar_label', lang)}\n{t('lunar_error', lang)}: {hidden['error']}\n"
    else:
        lunar = data["lunar"]
        calc_h = f"{hidden['digits_display']} = {hidden['raw_sum']}"
        if hidden.get("step2"):
            calc_h += f" → {hidden['step2']}"
        text += f"{t('lunar_label', lang)}\n"
        text += f"{lunar['year']} / {lunar['month']:02d} / {lunar['day']:02d}（{lunar.get('zodiac','')}年）\n"
        text += f"{calc_h}\n"
        text += f"{t('talent_number', lang)} *{hidden['total']}*　{t('life_number', lang)} *{hidden['single']}*\n"
        text += f"{h_meaning.get('name', '')} — {h_meaning.get('keyword', '')}\n\n"
        text += f"*{t('inner_chart', lang)}*\n"
        text += format_grid(hidden["grid"], "gold", lang) + "\n\n"
        if hidden["strong_numbers"]:
            nums = "、".join([f"{k}（{v}圈）" for k, v in hidden["strong_numbers"].items()])
            text += f"{t('strong_number', lang)}：{nums}\n"
        else:
            text += f"{t('strong_number', lang)}：{t('none', lang)}\n"
        if hidden["missing_numbers"]:
            text += f"{t('missing_number', lang)}：{'、'.join(str(n) for n in hidden['missing_numbers'])}\n"
        else:
            text += f"{t('missing_number', lang)}：{t('none', lang)}\n"

    text += "\n━━━━━━━━━━━━━━━\n\n"

    combined_grid = {}
    for n in range(1, 10):
        combined_grid[n] = manifest["grid"].get(n, 0) + (hidden.get("grid", {}).get(n, 0) if "error" not in hidden else 0)
    combined_strong = {k: v for k, v in combined_grid.items() if v >= 5}
    if not combined_strong:
        max_val = max(combined_grid.values())
        combined_strong_display = "、".join([f"{k}（{v}圈）" for k, v in combined_grid.items() if v == max_val]) if max_val >= 1 else t("none", lang)
    else:
        combined_strong_display = "、".join([f"{k}（{v}圈）" for k, v in combined_strong.items()])
    combined_missing = [n for n in range(1, 10) if combined_grid.get(n, 0) == 0]

    text += f"*{t('combined_chart', lang)}*\n"
    text += format_grid(combined_grid, "teal", lang) + "\n\n"
    text += f"{t('strong_number', lang)}：{combined_strong_display}\n"
    if combined_missing:
        text += f"{t('missing_number', lang)}：{'、'.join(str(n) for n in combined_missing)}\n"
    else:
        text += f"{t('missing_number', lang)}：{t('none', lang)}\n"

    return text


def format_yearly_grid(py: dict, monthly: list, year: int, birth_single: int, lang: str = "zh_tw") -> str:
    is_personal_year = (py["single"] == birth_single)
    all_digits = py.get("all_digits", "")
    digits_str = "+".join(all_digits) if all_digits else ""
    raw = py.get("raw_sum", "")
    single = py["single"]

    if raw > 9:
        second_step = "+".join(str(d) for d in str(raw))
        calc_str = f"`{digits_str} = {raw} → {second_step} = {single}`"
    else:
        calc_str = f"`{digits_str} = {single}`"

    year_themes = t("year_themes", lang)
    theme = year_themes.get(single, "") if isinstance(year_themes, dict) else ""

    text = f"📆 *{year}{t('annual_number', lang)}*\n"
    text += f"{calc_str}\n"
    text += f"{t('annual_number', lang)} *{single}*　{theme}\n"
    if is_personal_year:
        text += f"{t('personal_year_msg', lang)}\n"
    text += f"\n{t('annual_hint', lang)}"
    return text


def main_keyboard(lang: str) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(t("btn_chart", lang), callback_data="chart_menu")],
        [InlineKeyboardButton(t("btn_annual", lang), callback_data="year_menu")],
        [InlineKeyboardButton(t("btn_monthly", lang), callback_data="month_menu")],
        [InlineKeyboardButton(t("btn_language", lang), callback_data="change_lang")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for code in AVAILABLE_LANGUAGES:
        keyboard.append([InlineKeyboardButton(SUPPORTED_LANGUAGES[code], callback_data=f"set_lang_{code}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    bottom = ReplyKeyboardMarkup([[KeyboardButton("開始"), KeyboardButton("Start")]], resize_keyboard=True)
    await update.message.reply_text(
        "🌏 請選擇語言 / Please select your language",
        reply_markup=reply_markup
    )
    return SHOW_MENU


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    lang = get_lang(context)

    # ── 語言設定 ──
    if action.startswith("set_lang_"):
        chosen = action.replace("set_lang_", "")
        if chosen in AVAILABLE_LANGUAGES:
            context.user_data["lang"] = chosen
            lang = chosen
            bottom = ReplyKeyboardMarkup([[KeyboardButton("開始"), KeyboardButton("Start")]], resize_keyboard=True)
            await query.edit_message_text(t("language_set", lang))
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=t("welcome", lang),
                reply_markup=bottom
            )
        return ASK_DATE

    if action == "change_lang":
        keyboard = []
        for code in AVAILABLE_LANGUAGES:
            keyboard.append([InlineKeyboardButton(SUPPORTED_LANGUAGES[code], callback_data=f"set_lang_{code}")])
        await query.edit_message_text(
            "🌏 請選擇語言 / Please select your language",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SHOW_MENU

    # ── 需要命盤資料的操作 ──
    data = context.user_data.get("analysis")
    if not data:
        await query.edit_message_text(t("error_no_data", lang))
        return SHOW_MENU

    if action == "chart_menu":
        keyboard = [
            [InlineKeyboardButton(t("btn_outer", lang), callback_data="outer"),
             InlineKeyboardButton(t("btn_inner", lang), callback_data="inner")],
            [InlineKeyboardButton(t("btn_combined", lang), callback_data="ai_full")],
            [InlineKeyboardButton(t("btn_career", lang), callback_data="career"),
             InlineKeyboardButton(t("btn_love", lang), callback_data="love")],
        ]
        await query.edit_message_text(
            t("select_analysis", lang),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SHOW_MENU

    elif action == "outer":
        text = format_outer_reading(data["manifest"], data.get("manifest_meaning", {}))
        if lang != "zh_tw":
            text = await translate_text(text, lang, context)
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for chunk in chunks:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=chunk)

    elif action == "inner":
        text = format_inner_reading(data["hidden"], data.get("hidden_meaning", {}), data["lunar"])
        if lang != "zh_tw":
            text = await translate_text(text, lang, context)
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for chunk in chunks:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=chunk)

    elif action == "ai_full":
        await query.edit_message_text(t("analyzing_combined", lang))
        try:
            from ai_reader import build_prompt, call_ai
            prompt = build_prompt(data)
            if lang != "zh_tw":
                prompt += f"\n\nWrite the entire analysis in English."
            reading = call_ai(prompt, "", max_tokens=1500)
            if lang != "zh_tw":
                reading = await translate_text(reading, lang, context)
            chunks = [reading[i:i+4000] for i in range(0, len(reading), 4000)]
            for i, chunk in enumerate(chunks):
                header = f"{t('combined_title', lang)}\n\n" if i == 0 else ""
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{header}{chunk}")
        except Exception as e:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=t("error_analysis", lang, error=str(e)[:80]))

    elif action == "career":
        single = data["manifest"]["single"]
        total = data["manifest"]["total"]
        text = format_career_text(single, total)
        if lang != "zh_tw":
            text = await translate_text(text, lang, context)
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for chunk in chunks:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=chunk)

    elif action == "love":
        compatible = data.get("compatible_numbers", [])
        single = data["manifest"]["single"]
        text = f"{t('love_title', lang)}\n\n{t('love_intro', lang, single=single)}\n\n"
        for n in compatible:
            meaning = NUMBER_MEANINGS.get(n, {})
            text += f"• {n}（{meaning.get('name', '')}）— {meaning.get('keyword', '')}\n"
        text += f"\n{t('love_disclaimer', lang)}"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    elif action == "year_menu":
        current_year = data["personal_year_current"]["year"]
        solar = data["solar"]
        keyboard = [[
            InlineKeyboardButton(t("btn_before_birthday", lang, year=current_year), callback_data="year_prev"),
            InlineKeyboardButton(t("btn_after_birthday", lang, year=current_year), callback_data="year_curr"),
        ]]
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=t("birthday_question", lang, year=current_year, month=solar["month"], day=solar["day"]),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SHOW_MENU

    elif action in ("year_prev", "year_curr"):
        year_type = "prev" if action == "year_prev" else "current"
        label_key = "analyzing_annual_prev" if action == "year_prev" else "analyzing_annual_curr"
        await query.edit_message_text(t(label_key, lang))
        try:
            detail = get_year_detail(data, "", year_type=year_type)
            if lang != "zh_tw":
                detail = await translate_text(detail, lang, context)
            chunks = [detail[i:i+4000] for i in range(0, len(detail), 4000)]
            for chunk in chunks:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=chunk)
        except Exception as e:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=t("error_analysis", lang, error=str(e)[:80]))

    elif action == "month_menu":
        month_names = t("month_names", lang)
        monthly = data["monthly_current"]
        keyboard = []
        row = []
        for i, pm in enumerate(monthly):
            row.append(InlineKeyboardButton(f"{month_names[i]}（{pm['single']}）", callback_data=f"month_{i+1}"))
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🗓 {data['personal_year_current']['year']} — {t('select_month', lang)}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SHOW_MENU

    elif action.startswith("month_"):
        target_month = int(action.split("_")[1])
        year = data["personal_year_current"]["year"]
        await query.edit_message_text(t("analyzing_monthly", lang, year=year, month=target_month))
        try:
            detail = get_monthly_detail(data, target_month, "")
            if lang != "zh_tw":
                detail = await translate_text(detail, lang, context)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"{t('monthly_title', lang, year=year, month=target_month)}\n\n{detail}",
            )
        except Exception as e:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=t("error_analysis", lang, error=str(e)[:80]))

    elif action == "next_year":
        next_py = data["personal_year_next"]
        next_monthly = data["monthly_next"]
        birth_single = data["manifest"]["single"]
        text = format_yearly_grid(next_py, next_monthly, next_py["year"], birth_single, lang)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    # 重新顯示選單
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=t("want_more", lang),
        reply_markup=main_keyboard(lang)
    )
    return SHOW_MENU


async def translate_text(text: str, lang: str, context) -> str:
    """把中文文字翻譯成目標語言"""
    from ai_reader import call_ai
    lang_names = {
        "en": "English",
        "zh_cn": "Simplified Chinese",
        "ja": "Japanese",
        "ko": "Korean",
        "km": "Khmer",
        "vi": "Vietnamese",
        "th": "Thai",
    }
    target = lang_names.get(lang, "English")
    prompt = (
        f"Translate the following numerology reading into {target}. "
        f"Keep all section titles bold (with **). "
        f"Translate naturally and warmly. Do not add or remove content.\n\n{text[:2000]}"
    )
    try:
        return call_ai(prompt, "", max_tokens=1500)
    except Exception:
        return text


async def receive_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    text = update.message.text.strip().replace("-", "/").replace(".", "/")

    # 如果用戶按了「開始/Start」，顯示語言選單
    if text.lower() in ["開始", "start", "/start"]:
        return await start(update, context)

    try:
        parts = text.split("/")
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        assert 1900 <= year <= 2100
        assert 1 <= month <= 12
        assert 1 <= day <= 31
    except Exception:
        await update.message.reply_text(t("invalid_date", lang))
        return ASK_DATE

    context.user_data["year"] = year
    context.user_data["month"] = month
    context.user_data["day"] = day

    await update.message.reply_text(t("ask_time", lang))
    return ASK_TIME


async def receive_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    text = update.message.text.strip()
    skip_keywords = t("skip_keywords", lang)

    birth_hour = None
    if text not in skip_keywords:
        try:
            birth_hour = int(text)
            assert 0 <= birth_hour <= 23
        except Exception:
            await update.message.reply_text(t("invalid_time", lang))
            return ASK_TIME

    context.user_data["hour"] = birth_hour
    await update.message.reply_text(t("calculating", lang))

    try:
        data = full_analysis(
            context.user_data["year"],
            context.user_data["month"],
            context.user_data["day"],
            birth_hour
        )
        context.user_data["analysis"] = data
    except Exception as e:
        await update.message.reply_text(t("error_analysis", lang, error=str(e)))
        return ConversationHandler.END

    combined_text = format_combined_chart(data, lang)
    yearly_text = format_yearly_grid(
        data["personal_year_current"],
        data["monthly_current"],
        data["personal_year_current"]["year"],
        data["manifest"]["single"],
        lang
    )

    await update.message.reply_text(combined_text, parse_mode="Markdown")
    await update.message.reply_text(yearly_text, parse_mode="Markdown")
    await update.message.reply_text(
        t("select_content", lang),
        reply_markup=main_keyboard(lang)
    )
    return SHOW_MENU


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    await update.message.reply_text(t("cancel_msg", lang))
    return ConversationHandler.END


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    await update.message.reply_text(t("welcome", lang))
    return ASK_DATE


def main():
    if not BOT_TOKEN:
        print("錯誤：請設定環境變數 BOT_TOKEN")
        return
    if not OPENROUTER_API_KEY:
        print("警告：未設定 OPENROUTER_API_KEY，AI 解讀功能將無法使用")

    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex("^(開始|Start)$"), start),
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

    print("🤖 生命靈數 Bot 已啟動（多語言版）...")
    app.run_polling()


if __name__ == "__main__":
    main()
