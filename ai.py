import os, json, google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key: raise ValueError("GEMINI_API_KEY missing")
genai.configure(api_key=api_key)

def generate_quiz_question(subject=None, difficulty=None):
    """Generates a quiz question via Gemini API."""
    prompt = f"Generate a {difficulty or 'medium'} difficulty multiple-choice quiz question about {subject or 'general knowledge'}."
    format_instr = """
    Return ONLY JSON:
    {"question": "text", "options": ["A", "B", "C", "D"], "answer": "correct_option_text"}
    """
    try:
        model = genai.GenerativeModel('gemini-3.1-flash-lite-preview')
        response = model.generate_content(prompt + format_instr)
        data = json.loads(response.text.strip().replace("```json", "").replace("```", "").strip())
        data["answer"] = data["options"].index(data["answer"])
        return data
    except Exception as e:
        print(f"AI Error: {e}")
        raise Exception("AI service unavailable")

if __name__ == '__main__':
    print(generate_quiz_question("Science", "hard"))
