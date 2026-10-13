from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.services.stylist_chat import ask_stylist, clear_user_history

chatbot_bp = Blueprint("chatbot", __name__)

@chatbot_bp.route("/api/chatbot/ask", methods=["POST"])
@login_required
def ask():
    data = request.get_json() or {}
    message = data.get("message", "").strip()

    if not message:
        return jsonify({"reply": "I'm listening! Ask me about styling, mood combinations, or wardrobe advice."})

    reply = ask_stylist(current_user.id, message)
    return jsonify({"reply": reply})

@chatbot_bp.route("/api/chatbot/reset", methods=["POST"])
@login_required
def reset():
    clear_user_history(current_user.id)
    return jsonify({"status": "ok", "message": "Conversation history reset successfully."})
