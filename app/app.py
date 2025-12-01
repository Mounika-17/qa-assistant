from flask import Flask, render_template, request, jsonify
from .llm_client import get_qa_response


def create_app():
    app = Flask(__name__)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/chat", methods=["POST"])
    def chat():
        """
        Expected JSON body:
        {
          "messages": [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"}
          ]
        }
        """
        data = request.get_json(silent=True) or {}
        messages = data.get("messages", [])

        if not isinstance(messages, list):
            return jsonify({"error": "messages must be a list"}), 400

        try:
            reply = get_qa_response(messages)
            return jsonify({"reply": reply})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8000, debug=True)
