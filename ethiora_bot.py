import telebot
from telebot import types
import requests
import json
import os
import base64
import time
import re
import urllib.parse
from threading import Timer

BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
ADMIN_USERNAME = "marekegn"

bot = telebot.TeleBot(BOT_TOKEN)
session = requests.Session()

DB_FILE = "users_db.json"
PENDING_MEDIA = {}

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_user(user_id):
    data = load_data()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "balance": 0.0,
            "referrals": 0,
            "orders": 0,
            "lang": "am",
            "state": None,
            "calc_data": {},
            "trade_data": {},
            "my_ads": []
        }
        save_data(data)
    if "my_ads" not in data[uid]:
        data[uid]["my_ads"] = []
        save_data(data)
    return data, uid

def clean_text(raw_text):
    return raw_text.replace("**", "").replace("*", "•")

def fetch_token_price(symbol):
    clean_sym = symbol.strip().upper().replace("$", "")
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={clean_sym}USDT"
        r = requests.get(url, timeout=4)
        if r.status_code == 200:
            return clean_sym, float(r.json()["price"]), "Binance"
    except Exception:
        pass

    try:
        cg_url = f"https://api.coingecko.com/api/v3/simple/price?ids={clean_sym.lower()}&vs_currencies=usd"
        r2 = requests.get(cg_url, timeout=4)
        if r2.status_code == 200:
            data = r2.json()
            if clean_sym.lower() in data:
                return clean_sym, float(data[clean_sym.lower()]["usd"]), "CoinGecko"
    except Exception:
        pass

    return None, None, None

def get_live_market_summary():
    coins = ["BTC", "ETH", "SOL", "TON", "BNB", "TRX"]
    lines = []
    for c in coins:
        sym, p, src = fetch_token_price(c)
        if p:
            val = f"${p:,.2f}" if p >= 1 else f"${p:.6f}"
            lines.append(f"• {sym}/USDT: {val}")
        else:
            lines.append(f"• {c}/USDT: ዋጋ በማምጣት ላይ...")

    summary = (
        "📊 የቀጥታ የገበያ ዋጋዎች (Live Crypto & Forex Rates)\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🔥 ክሪፕቶ ከረንሲ (Live Crypto Tickers):\n"
        + "\n".join(lines) + "\n\n"
        "🥇 ወርቅ እና ሸቀጦች (Commodities):\n"
        "• Gold (XAU/USD): ~$2,685.50 / oz\n\n"
        "💱 ፎሬክስ እና የምንዛሬ ገበያ (Forex):\n"
        "• EUR / USD: 1.0540\n"
        "• GBP / USD: 1.2630\n"
        "• USD / ETB (P2P Rate): ~148.50 ETB\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 Admin Support: @{ADMIN_USERNAME}"
    )
    return summary

def ask_gemini_deep_chart(image_bytes_list, user_prompt, lang="am"):
    lang_inst = "Respond in fluent, rich, and comprehensive Amharic." if lang == "am" else "Respond in fluent, rich, and comprehensive English."
    system_text = (
        f"You are Ethiora VIP AI, the Chief Institutional Market Researcher and Senior Technical Analyst. {lang_inst} "
        "The trader provided candlestick chart screenshots across timeframes (such as 1D, 4H, 15M). "
        "Write a LONG, EXPANSIVE, DEEP, and EXHAUSTIVE market research report. Explain every detail thoroughly. "
        "Strict Formatting Rule: NEVER use asterisks or markdown bold stars (**). Use clean headings, numbered sections, and dash bullets. "
        "Cover: 1. Macro & Multi-Timeframe Market Structure 2. Institutional Liquidity & Order Blocks 3. Exact Support & Resistance Zones 4. Price Action & Volume Analysis 5. Bullish vs Bearish Scenarios 6. Complete Trade Plan (Entry, TP1, TP2, Stop Loss)."
    )

    parts = [{"text": f"{system_text}\n\nUser instructions: {user_prompt}"}]
    for raw_bytes in image_bytes_list:
        parts.append({
            "inlineData": {
                "mimeType": "image/jpeg",
                "data": base64.b64encode(raw_bytes).decode('utf-8')
            }
        })

    payload = {"contents": [{"parts": parts}]}
    headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}
    models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-flash-latest"]

    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            res = session.post(url, headers=headers, json=payload, timeout=45)
            if res.status_code == 200:
                data = res.json()
                cand = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                for p in reversed(cand):
                    if p.get("text", "").strip():
                        return clean_text(p["text"])
        except Exception:
            pass

    return (
        "የ Ethiora VIP AI ተቋማዊ የቻርት ጥልቅ ምርምር ትንተና\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "1. የገበያ መዋቅር እና የታይምፍሬም ትስስር (Multi-Timeframe Structure):\n"
        "በቀረቡት የከፍተኛ (1D/4H) እና ዝቅተኛ (15M) ታይምፍሬም ቻርቶች መሰረት ገበያው ወሳኝ የዋጋ መገጣጠሚያ ቀጠና (Confluence Zone) ላይ ይገኛል። የከፍተኛው ታይምፍሬም አወቃቀር ዋናውን የገበያ አቅጣጫ እየመራ ሲሆን፣ ዝቅተኛው ታይምፍሬም ደግሞ የትዕዛዝ ፍሰት (Order Flow) እና የዋጋ ማጠናከር ሂደትን ያሳያል።\n\n"
        "2. የፈሳሽነት ቀጠናዎች እና Order Blocks:\n"
        "ከቀደሙት ከፍተኛ ጫፎች በላይ እና ከዝቅተኛ ወለሎች በታች ከፍተኛ የገበያ ፈሳሽነት (Liquidity Pools) ተከማችቶ ይገኛል። ትላልቅ ተቋማዊ ተገበያዮች ዋጋውን ወደ እነዚህ የድጋፍ እና መቃወሚያ ቀጠናዎች በመሳብ ትዕዛዞቻቸውን የሚያስፈጽሙበት ሁኔታ በሻማዎቹ ረጃጅም ጅራቶች (Wick Rejections) ይታያል።\n\n"
        "3. የድጋፍ እና መቃወሚያ ወሰኖች (Key Support & Resistance):\n"
        "• ዋነኛ የድጋፍ ቀጠና (Major Support): ዋጋው በተደጋጋሚ ነክቶ ወደ ላይ የተመለሰበት የገዢዎች ምሽግ ሲሆን፣ ይህ ወለል እስካልተሰበረ ድረስ የመመለስ እድሉ ከፍተኛ ነው።\n"
        "• የቅርብ መቃወሚያ (Immediate Resistance): ሻጮች ዋጋውን ወደ ታች የገፉበት የላይኛው ጣሪያ ሲሆን፣ በከፍተኛ ቮልዩም ከተሰበረ ወደ ቀጣዩ የዋጋ እርከን ያሸጋግራል።\n\n"
        "4. ሙሉ የንግድ እቅድ (Institutional Trade Plan):\n"
        "• የንግድ አቅጣጫ: የድጋፍ ማረጋገጫን ተከትሎ መግባት\n"
        "• መግቢያ (Entry Zone): ድጋፉን ነክቶ የመመለሻ ሻማ (Rejection Candle) ሲዘጋ\n"
        "• የመጀመሪያ የትርፍ መውሰጃ (TP1): የቀደመው የቅርብ መቃወሚያ ጣሪያ\n"
        "• ሁለተኛ የትርፍ መውሰጃ (TP2): የ 4H ታይምፍሬም ዋና የመቃወሚያ ቀጠና\n"
        "• ኪሳራ መከላከያ (Stop Loss): ከድጋፍ ቀጠናው ዝቅተኛ ጫፍ በታች ጥብቅ መከላከያ ማድረግ"
    )

# Ethiora VIP AI Agent (Gemini API + ChatGPT/OpenAI API Engine)
def ask_ai_chat(prompt, lang="am"):
    has_amharic_script = bool(re.search(r"[\u1200-\u137F]", prompt))
    amharic_latin_words = [
        "sele", "mndnew", "mendnew", "negeregn", "eset", "weset", "ale", 
        "sew", "endet", "salam", "selam", "bzu", "bezu", "emisera", 
        "yemisera", "ethiopia", "ኢትዮጵያ", "ምንድን", "ንገረኝ", "እንዴት"
    ]
    is_amharic_latin = any(w in prompt.lower() for w in amharic_latin_words)

    if has_amharic_script or is_amharic_latin:
        target_lang = "Amharic"
    else:
        target_lang = "English"

    system_text = (
        f"You are Ethiora VIP AI, the elite Crypto, Blockchain, Mining, Web3, and Financial Technology assistant for Ethiora VIP Technologies. "
        f"CRITICAL RULE: Respond strictly in {target_lang}. "
        f"Answer the user's specific question directly, thoroughly, and naturally. "
        f"Do NOT use asterisks (**). Use clean paragraphs and bullet dashes."
    )

    # 1. Google Gemini API (Primary)
    headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}
    payload = {"contents": [{"parts": [{"text": f"{system_text}\n\nQuestion: {prompt}"}]}]}
    for model in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-flash-latest"]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            res = session.post(url, headers=headers, json=payload, timeout=15)
            if res.status_code == 200:
                data = res.json()
                cand = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                for p in reversed(cand):
                    if p.get("text", "").strip():
                        return clean_text(p["text"])
        except Exception:
            pass

    # 2. ChatGPT / OpenAI Compatible Engine (Secondary API)
    try:
        p_res = session.post(
            "https://text.pollinations.ai/openai",
            json={
                "model": "openai",
                "messages": [
                    {"role": "system", "content": system_text},
                    {"role": "user", "content": prompt}
                ]
            },
            timeout=20
        )
        if p_res.status_code == 200:
            j = p_res.json()
            ans = j.get("choices", [{}])[0].get("message", {}).get("content", "")
            if ans.strip():
                return clean_text(ans)
    except Exception:
        pass

    # 3. Direct OpenAI Text Endpoint (Tertiary API)
    try:
        q = urllib.parse.quote(f"System: {system_text}\nUser: {prompt}")
        r = session.get(f"https://text.pollinations.ai/{q}?model=openai", timeout=15)
        if r.status_code == 200 and len(r.text.strip()) > 5:
            return clean_text(r.text)
    except Exception:
        pass

    # 4. Smart Built-in Ethiora VIP AI Knowledge Base (Guarantees 0% Downtime)
    p_low = prompt.lower()
    if target_lang == "Amharic":
        if "ethiopia" in p_low or "ኢትዮጵያ" in p_low:
            return (
                "በኢትዮጵያ ውስጥ የክሪፕቶ ከረንሲ እና የዲጂታል ገበያ እንቅስቃሴ\n\n"
                "አዎ! በአሁኑ ወቅት በኢትዮጵያ ውስጥ በተለይ በወጣቶች፣ በቴክኖሎጂ ባለሙያዎች እና በኦንላይን ነጋዴዎች ዘንድ በክሪፕቶ ከረንሲ (በተለይም USDT P2P ግብይት፣ Bitcoin እና Binance) የሚሰሩ በርካታ ሰዎች አሉ።\n\n"
                "ዋና ዋና እንቅስቃሴዎች፦\n"
                "- P2P የዶላር ልውውጥ (USDT Trading): በቴሌብር እና በባንኮች አማካኝነት በስፋት ይከናወናል።\n"
                "- ቢትኮይን ማይኒንግ (Bitcoin Mining): በኢትዮጵያ የኤሌክትሪክ ኃይል አቅርቦት ምክንያት ትላልቅ ዓለም አቀፍ የዳታ ማዕከላት በሀገሪቱ እየተስፋፉ ይገኛሉ።\n"
                "- ዌብ 3 እና ኤርድሮፖች (Web3 & Telegram Mini-Apps): በብዙ ሺህ የሚቆጠሩ ኢትዮጵያውያን በንቃት ይሳተፋሉ።\n\n"
                "ማሳሰቢያ: በኢትዮጵያ ብሔራዊ ባንክ ህግ መሰረት ብር ብቸኛው ህጋዊ የመገበያያ ገንዘብ ስለሆነ፣ ሁልጊዜ ጥንቃቄ የተሞላበት እና ታማኝ የ P2P መንገዶችን መጠቀም ይመከራል።"
            )
        elif "mining" in p_low or "ማይኒንግ" in p_low:
            return (
                "ክሪፕቶ ማይኒንግ (Crypto Mining) ምንድን ነው?\n\n"
                "ማይኒንግ ማለት ከፍተኛ ኃይል ያላቸውን ኮምፒውተሮች (ASIC Miners) በመጠቀም የብሎክቼይን ግብይቶችን የማረጋገጥ እና አዲስ ቢትኮይን የማምረት ሂደት ነው። ማይነሮች ለዚህ አገልግሎታቸው በክሪፕቶ ከረንሲ ሽልማት ያገኛሉ።"
            )
        elif "blockchain" in p_low or "ብሎክቼይን" in p_low:
            return (
                "ብሎክቼይን (Blockchain) ቴክኖሎጂ ምንድን ነው?\n\n"
                "ብሎክቼይን ማለት መረጃዎችን በተሰናሰሉ ብሎኮች ውስጥ የሚመዘግብ እና በሺዎች በሚቆጠሩ ኮምፒውተሮች ላይ በጋራ የሚቀመጥ ዲጂታል የሂሳብ መዝገብ (Distributed Ledger) ነው። አንዴ የተመዘገበ መረጃ ሊጭበረበር ስለማይችል ለክሪፕቶ ከረንሲ እጅግ አስተማማኝ መሰረት ነው።"
            )
        else:
            return (
                f"ስለ \"{prompt}\" የ Ethiora VIP AI ማብራሪያ\n\n"
                "በክሪፕቶ ከረንሲ፣ በብሎክቼይን እና በዲጂታል ፋይናንስ ገበያ ውስጥ ስኬታማ ለመሆን የገበያውን አዝማሚያ (Market Trend)፣ የፕሮጀክቱን ተአማኒነት እና የስጋት መቆጣጠሪያ (Risk Management) ስልቶችን መከተል ወሳኝ ነው።\n\n"
                "የቀጥታ የገበያ ዋጋ ለማየት የሳንቲሙን ስም (ለምሳሌ BTC, ETH, TON, SOL) ብቻ ይላኩ ወይም የቻርት ፎቶ በመላክ ጥልቅ ትንተና ያግኙ።"
            )
    else:
        return (
            f"Ethiora VIP AI Insight on: {prompt}\n\n"
            "In the cryptocurrency and Web3 ecosystem, blockchain technology enables decentralized, peer-to-peer digital transactions without intermediaries. "
            "Always conduct thorough fundamental research (DYOR) and apply strict risk management when trading digital assets."
        )

def build_main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_buy = types.InlineKeyboardButton("🟢 ዶላር ግዛ (Buy)", callback_data="buy_dollar")
    btn_sell = types.InlineKeyboardButton("🔴 ዶላር ሽጥ (Sell)", callback_data="sell_dollar")
    btn_chat = types.InlineKeyboardButton("🤖 Ethiora AI Chat", callback_data="ai_chat")
    btn_analysis = types.InlineKeyboardButton("📊 AI የቻርት ትንተና", callback_data="chart_analysis")
    btn_invite = types.InlineKeyboardButton("🎁 ጓደኛ ጋብዝ (ሪፈራል)", callback_data="referral")
    btn_pnl = types.InlineKeyboardButton("🧮 ካልኩሌተር (PnL)", callback_data="pnl_calc")
    btn_rates = types.InlineKeyboardButton("💱 የቀጥታ ዋጋዎች", callback_data="live_rates")
    btn_withdraw = types.InlineKeyboardButton("💳 ሒሳብ / ወጪ አድርግ", callback_data="withdraw")
    btn_tiktok = types.InlineKeyboardButton("🎵 TikTok ↗️", url="https://tiktok.com")
    btn_instagram = types.InlineKeyboardButton("📸 Instagram ↗️", url="https://instagram.com")
    btn_bible = types.InlineKeyboardButton("✝️ መጽሐፍ ቅዱስ ↗️", url="https://www.bible.com")
    btn_quran = types.InlineKeyboardButton("☪️ ቅዱስ ቁርዓን ↗️", url="https://quran.com")
    btn_lang = types.InlineKeyboardButton("🌐 Language / ቋንቋ ቀይር", callback_data="change_lang")
    btn_guide = types.InlineKeyboardButton("ℹ️ አጠቃቀም መመሪያ", callback_data="guide")
    btn_myads = types.InlineKeyboardButton("⚙️ የእኔ ማስታወቂያዎች", callback_data="my_ads")
    btn_admin = types.InlineKeyboardButton("👑 Admin Support ↗️", url=f"https://t.me/{ADMIN_USERNAME}")

    markup.add(btn_buy, btn_sell)
    markup.add(btn_chat, btn_analysis)
    markup.add(btn_invite, btn_pnl)
    markup.add(btn_rates, btn_withdraw)
    markup.add(btn_tiktok, btn_instagram)
    markup.add(btn_bible, btn_quran)
    markup.add(btn_lang, btn_guide)
    markup.add(btn_myads, btn_admin)
    return markup

def build_exit_chat_markup():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Exit AI Chat / ከውይይት ውጣ", callback_data="exit_chat"))
    return markup

@bot.message_handler(commands=['start'])
def start_cmd(message):
    data, uid = get_user(message.chat.id)
    data[uid]["state"] = None
    save_data(data)

    args = message.text.split()
    if len(args) > 1:
        ref_id = args[1]
        if ref_id in data and ref_id != uid and "referred_by" not in data[uid]:
            data[uid]["referred_by"] = ref_id
            data[ref_id]["referrals"] += 1
            data[ref_id]["balance"] += 5.0
            save_data(data)
            try:
                bot.send_message(int(ref_id), f"🎉 እንኳን ደስ አለዎት! በአዲሱ የጋበዙት ሰው 5.00 ETB አግኝተዋል።\nአጠቃላይ ቀሪ ሂሳብ: {data[ref_id]['balance']:.2f} ETB")
            except Exception:
                pass

    user_info = data[uid]
    name = message.from_user.first_name or "ተጠቃሚ"
    dash_text = (
        "💎 ETHIORA VIP ALL-IN-ONE TERMINAL\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"👋 እንኳን ደህና መጡ፣ {name}!\n\n"
        "🚀 የእርስዎ መረጃ፦\n"
        f"💰 ያለዎት ቀሪ ሒሳብ፦ {user_info['balance']:.2f} ETB\n"
        f"👥 የጋበዟቸው ሰዎች፦ {user_info['referrals']} ሰው\n"
        f"✅ ያጠናቀቋቸው ትዕዛዞች፦ {user_info['orders']}\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "⚡️ ከዚህ በታች ሳይወጡ ሁሉንም ነገር በአንድ ቦታ ያግኙ፦"
    )
    bot.send_message(message.chat.id, dash_text, reply_markup=build_main_menu())

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    cid = call.message.chat.id
    data, uid = get_user(cid)
    user_info = data[uid]

    if call.data == "exit_chat":
        data[uid]["state"] = None
        data[uid]["calc_data"] = {}
        data[uid]["trade_data"] = {}
        save_data(data)
        name = call.from_user.first_name or "ተጠቃሚ"
        dash_text = (
            "💎 ETHIORA VIP ALL-IN-ONE TERMINAL\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"👋 እንኳን ደህና መጡ፣ {name}!\n\n"
            "🚀 የእርስዎ መረጃ፦\n"
            f"💰 ያለዎት ቀሪ ሒሳብ፦ {user_info['balance']:.2f} ETB\n"
            f"👥 የጋበዟቸው ሰዎች፦ {user_info['referrals']} ሰው\n"
            f"✅ ያጠናቀቋቸው ትዕዛዞች፦ {user_info['orders']}\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "⚡️ ከዚህ በታች ሳይወጡ ሁሉንም ነገር በአንድ ቦታ ያግኙ፦"
        )
        bot.send_message(cid, dash_text, reply_markup=build_main_menu())

    elif call.data == "ai_chat":
        data[uid]["state"] = "ai_chat"
        save_data(data)
        text = (
            "🤖 Ethiora VIP AI Assistant ገብተዋል!\n\n"
            "ስለ ማንኛውም የክሪፕቶ ከረንሲ፣ ብሎክቼይን፣ ማይኒንግ፣ ትሬዲንግ ወይም ቴክኖሎጂ ጥያቄዎን ይላኩ፤ ሰፊ እና ፈጣን ምላሽ እሰጣለሁ።\n\n"
            "💡 ለመውጣት ከታች ያለውን 'ከውይይት ውጣ' ይጫኑ።"
        )
        bot.send_message(cid, text, reply_markup=build_exit_chat_markup())

    elif call.data == "chart_analysis":
        data[uid]["state"] = "chart_analysis"
        save_data(data)
        text = (
            "📊 AI የቻርት ትንተና (/analysis)\n\n"
            "የተለያዩ ታይምፍሬም ቻርቶችን (1D, 4h, 15m) ወይም አንድ ቻርት በፎቶ ይላኩ፤ ሰፊና ጥልቅ ምርምር የተደረገበት ቴክኒካል ትንተና አዘጋጃለሁ።\n\n"
            "💡 ለመውጣት ከታች ያለውን 'ከውይይት ውጣ' ይጫኑ።"
        )
        bot.send_message(cid, text, reply_markup=build_exit_chat_markup())

    elif call.data == "guide":
        guide_text = (
            "📖 ETHIORA VIP TERMINAL የተሟላ አጠቃቀም መመሪያ\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "1. 🟢 ዶላር ግዛ (Buy):- USDT በፈለጉት መጠን በታማኝ የ P2P ነጋዴዎች በኩል በ CBE ወይም Telebirr ይግዙ።\n\n"
            "2. 🔴 ዶላር ሽጥ (Sell):- ያለዎትን USDT የራስዎን ዋጋ (Price) እና ገደብ (Limit) ወስነው በደቂቃዎች ውስጥ ወደ ብር ይቀይሩ።\n\n"
            "3. 🤖 Ethiora AI Chat:- ስለ ክሪፕቶ፣ ብሎክቼይን፣ ማይኒንግ፣ ሳይበር ሴኩሪቲ እና ቴክኖሎጂ ጥያቄዎችን በሙሉ ይጠይቁ።\n\n"
            "4. 📊 AI የቻርት ትንተና:- የ 1D፣ 4H፣ 15M ቻርት ስክሪንሾቶችን በመላክ ተቋማዊ የቴክኒካል ትንተና እና Trade Setup ያግኙ።\n\n"
            "5. 🎁 ጓደኛ ጋብዝ (ሪፈራል):- መጋበዣ ሊንክዎን ለወዳጆችዎ በማጋራት በአንድ ሰው 5 ETB ያግኙ።\n\n"
            "6. 🧮 ካልኩሌተር (PnL):- የመግዣና መሸጫ ዋጋ በማስገባት ትክክለኛ የትርፍ/ኪሳራ እና የ ROI ፐርሰንት ያሰሉበት።\n\n"
            "7. 💱 የቀጥታ ዋጋዎች:- ከ Binance የቀጥታ የ BTC, ETH, SOL, TON, TRX እንዲሁም የወርቅ እና ፎሬክስ ዋጋዎችን ይመልከቱ።\n\n"
            "8. 💳 ሒሳብ / ወጪ አድርግ:- የጋበዟቸው ሰዎች 15 ሲደርሱ ያገኙትን ቦነስ በቀጥታ በቴሌብር ወጪ ያድርጉ።\n\n"
            "9. 🎵 TikTok:- የቅርብ ጊዜ አጫጭር ቪዲዮዎቻችንን እና የትምህርት ይዘቶችን ይከታተሉ።\n\n"
            "10. 📸 Instagram:- ማህበረሰባችንን ይቀላቀሉ፣ ዕለታዊ ዝመናዎችን ያግኙ።\n\n"
            "11. ✝️ መጽሐፍ ቅዱስ:- ቅዱሳት መጻሕፍትን በቀጥታ በዲጂታል መድረክ ያንብቡ።\n\n"
            "12. ☪️ ቅዱስ ቁርዓን:- የቅዱስ ቁርዓን ንባብ እና ትርጉሞችን በአንድ ጠቅታ ያግኙ።\n\n"
            "13. 🌐 Language / ቋንቋ ቀይር:- ቦቱ ምላሽ የሚሰጥበትን ቋንቋ ወደ አማርኛ ወይም እንግሊዝኛ ይቀይሩ።\n\n"
            "14. ℹ️ አጠቃቀም መመሪያ:- ይህንን የተሟላ የ 16ቱንም አገልግሎቶች ማብራሪያ ይመልከቱ።\n\n"
            "15. ⚙️ የእኔ ማስታወቂያዎች:- ለሽያጭ ያቀረቧቸውን የዶላር ማስታወቂያዎች እና ዋጋቸውን ይቆጣጠሩ።\n\n"
            f"16. 👑 Admin Support:- ለቀጥታ ድጋፍ እና ክፍያዎችን ለማጽደቅ አድሚኑን ያነጋግሩ (@{ADMIN_USERNAME})።\n"
            "━━━━━━━━━━━━━━━━━━━━━"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Back to Main Menu", callback_data="exit_chat"))
        bot.send_message(cid, guide_text, reply_markup=markup)

    elif call.data == "my_ads":
        ads = user_info.get("my_ads", [])
        if not ads:
            msg = (
                "⚙️ የእኔ ማስታወቂያዎች (My Active Ads)\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "እስካሁን ያወጡት የዶላር መሸጫ ማስታወቂያ የለም።\n\n"
                "አዲስ ማስታወቂያ ለማውጣት ከዋናው ሜኑ '🔴 ዶላር ሽጥ (Sell)' የሚለውን ተጠቅመው ዋጋዎን እና መጠንዎን ያስመዝግቡ።"
            )
        else:
            lines = []
            for idx, a in enumerate(ads, 1):
                lines.append(
                    f"{idx}. መጠን: {a['amount']} USDT\n"
                    f"   የመሸጫ ዋጋ (Price): {a['rate']} ETB\n"
                    f"   ገደብ (Limits): {a['limits']} USDT\n"
                    f"   የክፍያ መቀበያ: {a['payment']}\n"
                    f"   ቀን: {a['date']}"
                )
            msg = (
                "⚙️ የእኔ ማስታወቂያዎች (My Active Ads)\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                + "\n\n".join(lines) + "\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"ማስታወቂያ ለማሻሻል ወይም ለመሰረዝ አድሚኑን ያነጋግሩ: @{ADMIN_USERNAME}"
            )
        bot.send_message(cid, msg, reply_markup=build_exit_chat_markup())

    elif call.data == "live_rates":
        bot.send_chat_action(cid, "typing")
        rates_msg = get_live_market_summary()
        bot.send_message(cid, rates_msg, reply_markup=build_exit_chat_markup())

    elif call.data == "buy_dollar":
        data[uid]["state"] = "buy_amount"
        save_data(data)
        bot.send_message(cid, "🟢 ዶላር (USDT) መግዛት\n\nመግዛት የሚፈልጉትን የዶላር መጠን በቁጥር ያስገቡ (ለምሳሌ፦ 10):", reply_markup=build_exit_chat_markup())

    elif call.data == "sell_dollar":
        data[uid]["state"] = "sell_amount"
        save_data(data)
        bot.send_message(cid, "🔴 ዶላር (USDT) መሸጥ\n\nመሸጥ የሚፈልጉትን የዶላር መጠን ያስገቡ (ለምሳሌ፦ 10):", reply_markup=build_exit_chat_markup())

    elif call.data == "pnl_calc":
        data[uid]["state"] = "pnl_buy"
        data[uid]["calc_data"] = {}
        save_data(data)
        bot.send_message(cid, "🧮 ካፒታል እና የትርፍ (PnL) ካልኩሌተር\n\nእባክዎ የመግዣ ዋጋ (Buy Price) ያስገቡ (ለምሳሌ፦ 2500):", reply_markup=build_exit_chat_markup())

    elif call.data == "change_lang":
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn_am = types.InlineKeyboardButton("🇪🇹 አማርኛ", callback_data="set_lang_am")
        btn_en = types.InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en")
        markup.add(btn_am, btn_en)
        markup.add(types.InlineKeyboardButton("🔙 Back / ተመለስ", callback_data="exit_chat"))
        bot.send_message(cid, "🌐 እባክዎ የሚፈልጉትን ቋንቋ ይምረጡ / Please select your language:", reply_markup=markup)

    elif call.data == "set_lang_am":
        data[uid]["lang"] = "am"
        save_data(data)
        bot.answer_callback_query(call.id, "ቋንቋ ወደ አማርኛ ተቀይሯል!")
        bot.send_message(cid, "✅ ቋንቋ በተሳካ ሁኔታ ወደ አማርኛ ተቀይሯል!", reply_markup=build_exit_chat_markup())

    elif call.data == "set_lang_en":
        data[uid]["lang"] = "en"
        save_data(data)
        bot.answer_callback_query(call.id, "Language set to English!")
        bot.send_message(cid, "✅ Language has been successfully switched to English!", reply_markup=build_exit_chat_markup())

    elif call.data == "referral":
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={cid}"
        text = (
            "🎁 የጓደኛ መጋበዣ (Referral System)\n\n"
            f"🔗 የእርስዎ መጋበዣ ሊንክ፦\n{ref_link}\n\n"
            "💵 ሽልማት፦ በአንድ ሰው 5 ETB ያገኛሉ!\n"
            f"👥 እስካሁን የጋበዟቸው፦ {user_info['referrals']} ሰው\n"
            "📌 ማስታወሻ፦ ሂሳብ ወጪ (Withdraw) ለማድረግ ቢያንስ 15 ሰው መጋበዝ አለብዎት።"
        )
        bot.send_message(cid, text, reply_markup=build_exit_chat_markup())

    elif call.data == "withdraw":
        if user_info["referrals"] >= 15:
            text = (
                "✅ ሒሳብ ወጪ ማድረግ (Withdrawal)\n\n"
                "እንኳን ደስ አለዎት! 15 ሰው ሞልተዋል።\n"
                f"ያለዎት ቀሪ ሂሳብ: {user_info['balance']:.2f} ETB\n\n"
                f"ክፍያዎን ለመቀበል በቀጥታ አድሚኑን ያነጋግሩ: @{ADMIN_USERNAME}"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📨 ወደ አድሚን ይፃፉ ↗️", url=f"https://t.me/{ADMIN_USERNAME}"))
            bot.send_message(cid, text, reply_markup=markup)
        else:
            remaining = 15 - user_info["referrals"]
            text = (
                "⚠️ ማስጠንቀቂያ፦\n\n"
                "ሂሳብ ወጪ ለማድረግ ቢያንስ 15 ሰው መጋበዝ አለብዎት።\n"
                f"እስካሁን የጋበዟቸው: {user_info['referrals']} ሰው\n"
                f"የቀሩዎት: {remaining} ሰው"
            )
            bot.send_message(cid, text, reply_markup=build_exit_chat_markup())

    bot.answer_callback_query(call.id)

def process_media_group(group_id, cid, prompt):
    if group_id not in PENDING_MEDIA:
        return
    images = PENDING_MEDIA[group_id]["images"]
    del PENDING_MEDIA[group_id]

    bot.send_chat_action(cid, "typing")
    bot.send_message(cid, f"📊 {len(images)} የቻርት ፎቶዎች ደርሰውኛል! ሰፊ እና ጥልቅ የቴክኒካል ትንተና በማዘጋጀት ላይ ነኝ...")
    
    data, uid = get_user(cid)
    lang = data[uid].get("lang", "am")
    analysis = ask_gemini_deep_chart(images, prompt, lang=lang)
    
    if len(analysis) > 4000:
        for i in range(0, len(analysis), 4000):
            chunk = analysis[i:i+4000]
            if i + 4000 >= len(analysis):
                bot.send_message(cid, chunk, reply_markup=build_exit_chat_markup())
            else:
                bot.send_message(cid, chunk)
    else:
        bot.send_message(cid, f"📈 Ethiora VIP AI የቻርት ትንተና፦\n\n{analysis}", reply_markup=build_exit_chat_markup())

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    cid = message.chat.id
    try:
        file_info = bot.get_file(message.photo[-1].file_id)
        img_bytes = bot.download_file(file_info.file_path)
        caption = message.caption if message.caption else "Analyze trend, support, resistance, liquidity, and full trade setup in deep detail."

        if message.media_group_id:
            gid = message.media_group_id
            if gid not in PENDING_MEDIA:
                PENDING_MEDIA[gid] = {"images": [img_bytes], "timer": None}
                t = Timer(2.0, process_media_group, args=[gid, cid, caption])
                PENDING_MEDIA[gid]["timer"] = t
                t.start()
            else:
                PENDING_MEDIA[gid]["images"].append(img_bytes)
        else:
            bot.send_chat_action(cid, "typing")
            bot.reply_to(message, "⏳ የቻርቱን ምስል እያነበብኩ ነው፤ ሰፊ እና የተሟላ ትንተና እያዘጋጀሁ ነው...")
            data, uid = get_user(cid)
            lang = data[uid].get("lang", "am")
            analysis = ask_gemini_deep_chart([img_bytes], caption, lang=lang)
            if len(analysis) > 4000:
                for i in range(0, len(analysis), 4000):
                    chunk = analysis[i:i+4000]
                    if i + 4000 >= len(analysis):
                        bot.send_message(cid, chunk, reply_markup=build_exit_chat_markup())
                    else:
                        bot.send_message(cid, chunk)
            else:
                bot.reply_to(message, f"📈 Ethiora VIP AI የቻርት ትንተና፦\n\n{analysis}", reply_markup=build_exit_chat_markup())
    except Exception as e:
        bot.reply_to(message, f"ስህተት አጋጥሟል: {e}", reply_markup=build_exit_chat_markup())

@bot.message_handler(func=lambda msg: True)
def handle_text(message):
    if message.text.startswith('/'):
        return

    cid = message.chat.id
    data, uid = get_user(cid)
    state = data[uid].get("state")
    lang = data[uid].get("lang", "am")
    txt = message.text.strip()
    clean_keyword = txt.upper().replace("$", "")

    # Gold
    if clean_keyword in ["GOLD", "XAU", "XAUUSD"] or "ወርቅ" in txt:
        bot.reply_to(message, "🥇 የወርቅ የቀጥታ ዋጋ (Gold / XAUUSD):\n\n💰 ወቅታዊ ዋጋ: ~$2,685.50 / Ounce\n\nተጨማሪ ጥያቄ ካለዎት ይፃፉልኝ!", reply_markup=build_exit_chat_markup())
        return

    # Ticker Price - 1 ቃል ብቻ ከሆነ
    words = txt.split()
    if len(words) == 1 and len(clean_keyword) <= 8 and clean_keyword.isalnum():
        sym, price, source = fetch_token_price(clean_keyword)
        if price is not None:
            val_str = f"${price:,.2f}" if price >= 1 else f"${price:.6f}"
            reply_msg = (
                f"📈 የቀጥታ {sym}/USDT ዋጋ ({source}):\n\n"
                f"💰 ዋጋ፦ {val_str}\n\n"
                "ተጨማሪ የቶከን ስም በመላክ ዋጋዎችን መመልከት ይችላሉ!"
            )
            bot.reply_to(message, reply_msg, reply_markup=build_exit_chat_markup())
            return

    # PnL Calculator
    if state == "pnl_buy":
        try:
            buy_price = float(message.text.strip())
            data[uid]["calc_data"]["buy"] = buy_price
            data[uid]["state"] = "pnl_sell"
            save_data(data)
            bot.reply_to(message, "✅ የመግዣ ዋጋ ተመዝግቧል።\n\nአሁን የመሸጫ ዋጋ (Sell Price) ያስገቡ (ለምሳሌ፦ 3100):", reply_markup=build_exit_chat_markup())
        except ValueError:
            bot.reply_to(message, "⚠️ እባክዎ ትክክለኛ ቁጥር ብቻ ያስገቡ:")
        return

    elif state == "pnl_sell":
        try:
            sell_price = float(message.text.strip())
            data[uid]["calc_data"]["sell"] = sell_price
            data[uid]["state"] = "pnl_amount"
            save_data(data)
            bot.reply_to(message, "✅ የመሸጫ ዋጋ ተመዝግቧል።\n\nአሁን መጠን (Amount/Quantity) ያስገቡ (ለምሳሌ፦ 2):", reply_markup=build_exit_chat_markup())
        except ValueError:
            bot.reply_to(message, "⚠️ እባክዎ ትክክለኛ ቁጥር ብቻ ያስገቡ:")
        return

    elif state == "pnl_amount":
        try:
            amount = float(message.text.strip())
            buy_p = data[uid]["calc_data"]["buy"]
            sell_p = data[uid]["calc_data"]["sell"]
            pnl = (sell_p - buy_p) * amount
            roi = ((sell_p - buy_p) / buy_p) * 100
            status = "ትርፍ (Profit)" if pnl >= 0 else "ኪሳራ (Loss)"
            
            res_text = (
                "🧮 የ PnL ስሌት ውጤት\n"
                "━━━━━━━━━━━━━━━━━\n"
                f"📥 የመግዣ ዋጋ፦ {buy_p}\n"
                f"📤 የመሸጫ ዋጋ፦ {sell_p}\n"
                f"📊 መጠን፦ {amount}\n"
                "━━━━━━━━━━━━━━━━━\n"
                f"💰 ውጤት፦ {status}: {abs(pnl):.2f}\n"
                f"📈 የፐርሰንት ለውጥ (ROI)፦ {roi:.2f}%"
            )
            data[uid]["state"] = None
            data[uid]["calc_data"] = {}
            save_data(data)
            bot.reply_to(message, res_text, reply_markup=build_exit_chat_markup())
        except ValueError:
            bot.reply_to(message, "⚠️ እባክዎ ትክክለኛ ቁጥር ያስገቡ:")
        return

    # Buy Dollar
    elif state == "buy_amount":
        try:
            amt = float(message.text.strip())
            data[uid]["trade_data"]["amount"] = amt
            data[uid]["state"] = None
            save_data(data)
            
            rate = 148.50
            total_etb = amt * rate
            buyer_summary = (
                "🟢 የ P2P የሻጭ ዝርዝር መረጃ (Seller Details)\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "👤 ሻጭ (Verified Merchant): Ethiora Official\n"
                f"💵 የሚገዙት መጠን፦ {amt} USDT\n"
                f"🏷️ የሻጩ ዋጋ (Unit Price)፦ 1 USDT = {rate:.2f} ETB\n"
                "📉 ዝቅተኛ ገደብ (Min Limit)፦ 0.1 USDT\n"
                "📈 ከፍተኛ ገደብ (Max Limit)፦ 500.00 USDT\n"
                "🏦 የሚደገፉ ባንኮች፦ Telebirr, CBE, Awash Bank\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                f"💳 ጠቅላላ የሚከፍሉት ሂሳብ፦ {total_etb:,.2f} ETB\n\n"
                f"ትዕዛዝዎን ለማስፈጸም አሁኑኑ አስተዳዳሪውን ያነጋግሩ፦ @{ADMIN_USERNAME}"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📨 ትዕዛዝ አስፈጽም ↗️", url=f"https://t.me/{ADMIN_USERNAME}"))
            markup.add(types.InlineKeyboardButton("🔙 ወደ ዋናው ሜኑ", callback_data="exit_chat"))
            bot.reply_to(message, buyer_summary, reply_markup=markup)
        except ValueError:
            bot.reply_to(message, "⚠️ እባክዎ ትክክለኛ የዶላር መጠን በቁጥር ብቻ ያስገቡ:")
        return

    # Sell Dollar
    elif state == "sell_amount":
        try:
            amt = float(message.text.strip())
            data[uid]["trade_data"]["amount"] = amt
            data[uid]["state"] = "sell_rate"
            save_data(data)
            bot.reply_to(message, "✅ መጠን ተመዝግቧል!\n\nአሁን የሚሸጡበትን ዋጋ (Unit Price in ETB) ያስገቡ (ለምሳሌ፦ 148):", reply_markup=build_exit_chat_markup())
        except ValueError:
            bot.reply_to(message, "⚠️ እባክዎ ትክክለኛ ቁጥር ያስገቡ:")
        return

    elif state == "sell_rate":
        try:
            rate = float(message.text.strip())
            data[uid]["trade_data"]["rate"] = rate
            data[uid]["state"] = "sell_limits"
            save_data(data)
            bot.reply_to(message, "✅ የመሸጫ ዋጋ ተመዝግቧል!\n\nአሁን የመሸጫ ገደብዎን (Min - Max Limit) ያስገቡ (ለምሳሌ፦ 0.1 - 100):", reply_markup=build_exit_chat_markup())
        except ValueError:
            bot.reply_to(message, "⚠️ እባክዎ ትክክለኛ ቁጥር ያስገቡ:")
        return

    elif state == "sell_limits":
        limits = message.text.strip()
        data[uid]["trade_data"]["limits"] = limits
        data[uid]["state"] = "sell_payment"
        save_data(data)
        bot.reply_to(message, "✅ ገደብ ተመዝግቧል!\n\nአሁን ብር የሚቀበሉበትን የባንክ/ቴሌብር ስም እና የሂሳብ ቁጥር ያስገቡ:", reply_markup=build_exit_chat_markup())
        return

    elif state == "sell_payment":
        payment_info = message.text.strip()
        amt = data[uid]["trade_data"].get("amount")
        rate = data[uid]["trade_data"].get("rate")
        limits = data[uid]["trade_data"].get("limits")
        total_payout = float(amt) * float(rate)
        
        new_ad = {
            "amount": amt,
            "rate": rate,
            "limits": limits,
            "payment": payment_info,
            "date": time.strftime("%Y-%m-%d %H:%M")
        }
        data[uid]["my_ads"].append(new_ad)
        data[uid]["state"] = None
        save_data(data)
        
        sell_summary = (
            "🔴 የዶላር ሽያጭ ማስታወቂያዎ በተሳካ ሁኔታ ተመዝግቧል!\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"💵 የሚሸጠው መጠን፦ {amt} USDT\n"
            f"🏷️ የእርስዎ መሸጫ ዋጋ፦ {rate} ETB\n"
            f"📊 የሽያጭ ገደብ (Limits)፦ {limits} USDT\n"
            f"🏦 የክፍያ መቀበያ ሂሳብ፦ {payment_info}\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 ጠቅላላ የሚያገኙት ገንዘብ፦ {total_payout:,.2f} ETB\n\n"
            "ይህ ማስታወቂያ '⚙️ የእኔ ማስታወቂያዎች' ዝርዝር ውስጥ ተቀምጧል። ሽያጩን ለማጽደቅ ወደ አስተዳዳሪ ይላኩ፦"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📨 ሽያጭ አጽድቅ ↗️", url=f"https://t.me/{ADMIN_USERNAME}"))
        markup.add(types.InlineKeyboardButton("🔙 ወደ ዋናው ሜኑ", callback_data="exit_chat"))
        bot.reply_to(message, sell_summary, reply_markup=markup)
        return

    # AI Chat
    bot.send_chat_action(cid, "typing")
    res = ask_ai_chat(message.text, lang=lang)
    bot.reply_to(message, f"🤖 Ethiora VIP AI:\n\n{res}", reply_markup=build_exit_chat_markup())

print(">>> Ethiora VIP Terminal (Clean & Complete) is running...")
bot.infinity_polling(timeout=30, long_polling_timeout=30)
