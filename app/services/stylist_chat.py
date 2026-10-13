import os
import json
import requests
from typing import List, Dict, Optional
from flask import current_app
from app.config import Config
from app.models import WardrobeItem, UserPreference, WornHistory, Outfit
from app.routes.trends import TRENDS_DATA

# In-memory session conversation memory isolated per user
# user_id -> list of {"role": "user" | "assistant", "content": str}
USER_CONVERSATIONS: Dict[int, List[Dict[str, str]]] = {}

# Test hook to allow unit testing with dynamic mock responses
_MOCK_LLM_HANDLER = None

def set_mock_llm_handler(handler):
    """Sets a test handler for testing LLM interactions in unit tests."""
    global _MOCK_LLM_HANDLER
    _MOCK_LLM_HANDLER = handler

def get_user_history(user_id: int) -> List[Dict[str, str]]:
    """Retrieves recent conversation history for a given user."""
    return USER_CONVERSATIONS.get(user_id, [])

def add_to_history(user_id: int, role: str, content: str, max_turns: int = 12):
    """Appends a message to the user's conversation history, trimming older turns."""
    if user_id not in USER_CONVERSATIONS:
        USER_CONVERSATIONS[user_id] = []
    USER_CONVERSATIONS[user_id].append({"role": role, "content": content})
    if len(USER_CONVERSATIONS[user_id]) > max_turns:
        USER_CONVERSATIONS[user_id] = USER_CONVERSATIONS[user_id][-max_turns:]

def clear_user_history(user_id: int):
    """Clears conversation memory for a user."""
    if user_id in USER_CONVERSATIONS:
        USER_CONVERSATIONS[user_id] = []


def build_stylist_system_prompt(user_id: int) -> str:
    """
    Builds an authentic, comprehensive system prompt grounded in the user's
    actual database wardrobe, preferences, wear history, and 2026 fashion trends.
    """
    # 1. User's Wardrobe Items
    all_items = WardrobeItem.query.filter_by(user_id=user_id).all()
    available_items = [i for i in all_items if i.availability_status == "Available"]
    unavailable_items = [i for i in all_items if i.availability_status != "Available"]

    closet_sections = []
    if available_items:
        categories = ["Tops", "Bottoms", "Dresses / One-piece", "Footwear", "Accessories"]
        for cat in categories:
            cat_items = [i for i in available_items if i.category == cat]
            if cat_items:
                item_lines = []
                for item in cat_items:
                    fabric_str = f", Fabric: {item.fabric}" if item.fabric else ""
                    style_str = f", Style: {item.style}" if item.style else ""
                    item_lines.append(f"  - {item.name} (Color: {item.color}{fabric_str}{style_str})")
                closet_sections.append(f"[{cat}]\n" + "\n".join(item_lines))
        closet_text = "\n\n".join(closet_sections)
    else:
        closet_text = "The user has no available items in their closet currently."

    unavailable_text = ""
    if unavailable_items:
        unavail_lines = [f"  - {i.name} ({i.category}, Status: {i.availability_status})" for i in unavailable_items]
        unavailable_text = "\n[Currently In Laundry / Worn / Unavailable - Do NOT recommend these unless explicitly asked]:\n" + "\n".join(unavail_lines)

    # 2. User Preferences
    pref = UserPreference.query.filter_by(user_id=user_id).first()
    pref_text = ""
    if pref:
        pref_text = f"""User Style Preferences:
- Preferred Styles: {pref.preferred_styles}
- Favourite Colors: {pref.favourite_colors}
- Preferred Fits: {pref.preferred_fits}
- Common Occasions: {pref.common_occasions}
- Comfort Priority: {pref.comfort_preference}"""
    else:
        pref_text = "User Style Preferences: Default (Casual, Minimalist, Smart Casual)."

    # 3. Recent Wear History
    recent_worn = WornHistory.query.filter_by(user_id=user_id).order_by(WornHistory.date_worn.desc()).limit(5).all()
    history_text = "Recent Outfit History:\n"
    if recent_worn:
        for w in recent_worn:
            outfit = Outfit.query.get(w.outfit_id) if w.outfit_id else None
            outfit_title = outfit.title if outfit else "Custom Look"
            history_text += f"  - Worn on {w.date_worn}: {outfit_title}\n"
    else:
        history_text += "  - No outfits logged in wear history yet.\n"

    # 4. Editorial Trend Intelligence (2026)
    trends_summary = "Curated 2026 Trend Intelligence:\n"
    for t in TRENDS_DATA[:4]:
        colors = ", ".join(t.get("trending_colors", []))
        elements = ", ".join(t.get("key_elements", []))
        trends_summary += f"  - {t.get('title')} ({t.get('season')}): Trending colors: {colors}. Key elements: {elements}.\n"

    # 5. Live Weather status
    weather_note = ""
    if Config.WEATHER_API_KEY:
        weather_note = "Weather API is configured; if user specifies a location, incorporate current weather awareness."
    else:
        weather_note = "NOTE ON LIVE WEATHER: The live meteorological weather API is currently not configured. If the user asks about live today's weather in a specific city, politely clarify that live weather tracking is not connected, but provide seasonal styling recommendations for that expected climate."

    # Final Combined System Prompt
    system_prompt = f"""You are Wardrobe IQ's expert editorial personal fashion stylist.
You have a direct, friendly, sophisticated, and encouraging conversation with the user.

USER'S ACTUAL WARDROBE DATABASE:
================================
{closet_text}
{unavailable_text}

{pref_text}

{history_text}

{trends_summary}

{weather_note}

CORE STYLING RULES:
1. WARDROBE GROUNDING: When recommending what to wear or how to pair clothes, ALWAYS prioritize and recommend actual pieces from the user's available closet above. Wrap owned pieces in <strong>Piece Name</strong> (e.g. <strong>Charcoal Relaxed Blazer</strong>).
2. DO NOT INVENT CLOTHES: Never pretend the user owns an item that is not in their closet. If they need something they do not own (e.g. formal footwear or a tailored belt), clearly suggest it as an acquisition or suggest an alternative styling route using what they do own.
3. OPEN-ENDED STYLING EXPERTISE: Fully understand and provide sophisticated answers to open-ended fashion questions (e.g., cousin's engagement, styling a black shirt, elevating an outfit for elegance, 2026 trending colors, 3-day travel packing plans, why outfit combinations work, silhouette balance, and color harmony).
4. CONVERSATION CONTINUITY: You remember earlier questions and answers in this conversation. Address follow-up questions smoothly and contextually.
5. FOLLOW-UP QUESTIONS: If the user's styling request is missing key context (e.g., event formality, indoor vs outdoor, specific weather), give a thoughtful recommendation and ask a helpful follow-up question.
6. FORMATTING: Use clean, readable markdown with concise paragraphs and bullet points (•). Keep answers punchy, practical, and editorial (avoid generic AI fluff and avoid robotic headers like '✨ Styling Blueprint')."""

    return system_prompt.strip()


def sanitize_secret_text(text: str) -> str:
    """Removes API keys or secret tokens from messages to prevent any credential leakage."""
    if not text:
        return ""
    for key in [Config.GEMINI_API_KEY, Config.GROQ_API_KEY, Config.OPENAI_API_KEY, Config.OPENROUTER_API_KEY, Config.HF_TOKEN]:
        if key and len(key.strip()) > 5:
            text = text.replace(key.strip(), "[REDACTED]")
    import re
    text = re.sub(r'key=[A-Za-z0-9_\-\.]{8,}', 'key=[REDACTED]', text)
    return text


def _call_gemini(system_prompt: str, history: List[Dict[str, str]], user_message: str):
    """Calls Google Gemini models via REST API with fallback and error reporting."""
    api_key = Config.GEMINI_API_KEY.strip()
    if not api_key:
        return None, None

    # Current supported Flash models in Google AI Studio (Free Tier)
    models = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-flash-latest"]
    contents = []

    # Add conversation history
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({
            "role": role,
            "parts": [{"text": msg["content"]}]
        })
    # Add current user message
    contents.append({
        "role": "user",
        "parts": [{"text": user_message}]
    })

    payload = {
        "systemInstruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1024
        }
    }

    last_error = None
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        try:
            resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        text = parts[0].get("text", "").strip()
                        if text:
                            return text, None
            else:
                err_data = {}
                try:
                    err_data = resp.json().get("error", {})
                except Exception:
                    pass
                msg = err_data.get("message", f"HTTP {resp.status_code}")
                last_error = f"{model}: {msg}"
                continue
        except requests.exceptions.Timeout:
            last_error = f"{model}: Request timed out (15s)"
            continue
        except Exception:
            last_error = f"{model}: Connection error"
            continue

    return None, last_error


def _call_groq(system_prompt: str, history: List[Dict[str, str]], user_message: str) -> Optional[str]:
    """Calls Groq Cloud REST API with Llama-3.3-70b-versatile."""
    api_key = Config.GROQ_API_KEY.strip()
    if not api_key:
        return None

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
    except Exception:
        pass

    return None


def _call_openai(system_prompt: str, history: List[Dict[str, str]], user_message: str) -> Optional[str]:
    """Calls OpenAI gpt-4o-mini REST API."""
    api_key = Config.OPENAI_API_KEY.strip()
    if not api_key:
        return None

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
    except Exception:
        pass

    return None


def _call_openrouter(system_prompt: str, history: List[Dict[str, str]], user_message: str) -> Optional[str]:
    """Calls OpenRouter REST API."""
    api_key = Config.OPENROUTER_API_KEY.strip()
    if not api_key:
        return None

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
    except Exception:
        pass

    return None


def _call_ollama(system_prompt: str, history: List[Dict[str, str]], user_message: str) -> Optional[str]:
    """Calls Local Ollama if available on localhost:11434."""
    url = "http://localhost:11434/api/chat"
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    payload = {
        "model": "llama3.2",
        "messages": messages,
        "stream": False
    }

    try:
        resp = requests.post(url, json=payload, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("message", {}).get("content", "").strip()
    except Exception:
        pass

    return None


def get_unconfigured_service_message() -> str:
    """
    Returns an honest, user-friendly setup notification when no real AI model is configured.
    Strictly upholds Requirement 4: 'Never return a random, generic, or predefined answer
    while presenting it as a live AI-generated response. If the model is unavailable,
    show a clear, user-friendly message explaining that the AI service is not configured.'
    """
    return (
        '<div class="ai-config-notice">'
        '  <div class="ai-notice-header">'
        '    <span class="ai-notice-badge">⚡ Real AI Model Setup Required</span>'
        '  </div>'
        '  <p>Wardrobe IQ\'s conversational stylist connects to a live Large Language Model (such as <strong>Google Gemini</strong> or <strong>Groq Cloud</strong>) to generate real, dynamic, and wardrobe-grounded styling answers without hardcoded templates.</p>'
        '  <div class="ai-notice-steps">'
        '    <strong>Connect for free in 60 seconds:</strong>'
        '    <ol>'
        '      <li>Get a free Gemini API key from <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener">Google AI Studio</a> (Free, zero cost) or Groq from <a href="https://console.groq.com/keys" target="_blank" rel="noopener">console.groq.com</a>.</li>'
        '      <li>Add it to your project\'s <code>.env</code> file:<br><code>GEMINI_API_KEY=your_key_here</code> or <code>GROQ_API_KEY=your_key_here</code></li>'
        '      <li>Ask your stylist your question again!</li>'
        '    </ol>'
        '  </div>'
        '  <p class="ai-notice-footer"><em>In accordance with our no-fake-AI policy, predefined responses are disabled so you only experience genuine, dynamic intelligence.</em></p>'
        '</div>'
    )


def ask_stylist(user_id: int, user_message: str) -> str:
    """
    Main entry point for Wardrobe IQ conversational stylist.
    1. Builds grounded context prompt from user's actual database closet & preferences.
    2. Retrieves recent conversation memory for this user.
    3. Calls configured LLM provider (or mock test handler in unit tests).
    4. If no LLM is configured or available, returns honest setup notice (No Fake AI).
    5. Saves exchange to user's conversation memory.
    """
    user_message = user_message.strip()
    if not user_message:
        return "I'm here! What styling question or outfit advice can I help you with today?"

    system_prompt = build_stylist_system_prompt(user_id)
    history = get_user_history(user_id)

    # 1. Test Mock Hook (Allows unit tests to verify dynamic generation without live keys)
    if _MOCK_LLM_HANDLER is not None:
        mock_reply = _MOCK_LLM_HANDLER(user_id, system_prompt, history, user_message)
        if mock_reply:
            add_to_history(user_id, "user", user_message)
            add_to_history(user_id, "assistant", mock_reply)
            return mock_reply

    # 2. Tiered Live LLM Dispatcher
    reply = None
    gemini_error = None

    # Priority A: Google Gemini (Free tier, fast)
    if Config.GEMINI_API_KEY:
        reply, gemini_error = _call_gemini(system_prompt, history, user_message)

    # Priority B: Groq Cloud (Free tier, Llama-3.3-70B)
    if not reply and Config.GROQ_API_KEY:
        reply = _call_groq(system_prompt, history, user_message)

    # Priority C: OpenAI
    if not reply and Config.OPENAI_API_KEY:
        reply = _call_openai(system_prompt, history, user_message)

    # Priority D: OpenRouter
    if not reply and Config.OPENROUTER_API_KEY:
        reply = _call_openrouter(system_prompt, history, user_message)

    # Priority E: Local Ollama
    if not reply:
        reply = _call_ollama(system_prompt, history, user_message)

    # 3. Transparent Result Handling
    if reply:
        # Append to user's conversation memory
        add_to_history(user_id, "user", user_message)
        add_to_history(user_id, "assistant", reply)
        return reply

    # 4. If Gemini was configured but an API error occurred, present a clean notice
    if Config.GEMINI_API_KEY and gemini_error:
        clean_error = sanitize_secret_text(gemini_error)
        return (
            '<div class="ai-config-notice">'
            '  <div class="ai-notice-header">'
            '    <span class="ai-notice-badge" style="background:#FDE8E8; color:#9B1C1C; border-color:#F8B4B4;">⚠️ Gemini API Service Notice</span>'
            '  </div>'
            f'  <p>Your Gemini API key was loaded, but the service returned an issue: <em>{clean_error}</em>.</p>'
            '  <p class="ai-notice-footer"><em>Please verify your network connection or review your free tier quota at Google AI Studio. Predefined mock answers remain disabled under our no-fake-AI policy.</em></p>'
            '</div>'
        )

    # 5. Honest unconfigured notice when no real LLM model is reachable
    return get_unconfigured_service_message()
