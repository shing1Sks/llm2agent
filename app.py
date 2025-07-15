from flask import Flask, request, jsonify, render_template
import requests
import os
from dotenv import load_dotenv

load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

app = Flask(__name__)

GOAL = "Get a discount on a car service by calling a representative."
OBJECTIVES = [
    "Introduce yourself and state your intent",
    "Gather service details",
    "Ask about pricing",
    "Ask for discounts",
    "End the conversation politely",
]

convo_history = []
current_objective_index = 0


@app.route("/")
def index():
    return render_template("index.html")


def query_groq(user_input, current_objective, history):
    prompt = f"""
You are an autonomous agent working towards a goal.

Goal: {GOAL}
Current Objective: {current_objective}

Conversation History:
{history}

Respond in a way that accomplishes the current objective.

Return your response and a flag:
- "continue" to keep working on this objective
- "shift" to move to the next objective
- "conclude" to end the conversation

Format strictly as:
{{ "res": "<response>", "flag": "<continue|shift|conclude>" }}
"""

    res = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        json={
            "model": "llama3-70b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        },
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
    )

    data = res.json()

    # Check for error response
    if "error" in data:
        print("Groq API Error:", data["error"])
        return (
            '{ "res": "Sorry, an error occurred: '
            + data["error"]["message"]
            + '", "flag": "conclude" }'
        )

    return data["choices"][0]["message"]["content"]


@app.route("/chat", methods=["POST"])
def chat():
    global current_objective_index, convo_history
    user_msg = request.json["message"]
    convo_history.append(f"User: {user_msg}")

    if current_objective_index >= len(OBJECTIVES):
        return jsonify(
            {
                "response": "All objectives completed.",
                "objective": "None",
                "flag": "conclude",
            }
        )

    current_objective = OBJECTIVES[current_objective_index]
    llm_response = query_groq(user_msg, current_objective, "\n".join(convo_history))

    try:
        parsed = eval(llm_response)
    except:
        return jsonify({"error": "Failed to parse LLM response", "raw": llm_response})

    convo_history.append(f"Agent: {parsed['res']}")

    if parsed["flag"] == "shift":
        current_objective_index += 1
    elif parsed["flag"] == "conclude":
        current_objective_index = len(OBJECTIVES)

    return jsonify(
        {
            "response": parsed["res"],
            "objective": OBJECTIVES[current_objective_index]
            if current_objective_index < len(OBJECTIVES)
            else "Completed",
            "flag": parsed["flag"],
        }
    )


@app.route("/basic-chat", methods=["POST"])
def basic_chat():
    global convo_history  # reuse the same conversation memory
    user_msg = request.json["message"]
    convo_history.append(f"User: {user_msg}")

    prompt = f"""
You are an intelligent assistant acting on behalf of the user to help accomplish the following goal:

🎯 Goal: Negotiate a discount on a car service by speaking with a service representative.

You are having a conversation with a car service agent. Your role is to guide the discussion in a friendly, natural, and persuasive way that supports the user's objective.

To achieve this goal, follow these key tasks (but adapt naturally to the flow of conversation):

1. Introduce yourself and clearly state your intent.
2. Gather important service details.
3. Inquire about pricing and any existing offers.
4. Politely and confidently ask for available discounts.
5. Conclude the conversation on a polite and professional note.

Here is the current conversation history:
{chr(10).join(convo_history)}

Please respond in a natural and helpful tone. Keep the goal in mind, but do not repeat it unless necessary.
"""

    res = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        json={
            "model": "llama3-70b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
        },
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
    )

    data = res.json()
    if "error" in data:
        return jsonify({"response": "Error from Groq", "raw": data["error"]})

    response_text = data["choices"][0]["message"]["content"]
    convo_history.append(f"Agent: {response_text}")

    return jsonify(
        {
            "response": response_text,
            "objective": "Goal-Oriented (Freeform)",
            "mode": "basic",
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
