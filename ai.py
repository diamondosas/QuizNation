import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
import google.api_core.exceptions

# Load environment variables
load_dotenv()

# Configure the Gemini API
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file. Please add it.")
genai.configure(api_key=api_key)

def generate_quiz_question(subject=None, difficulty=None):
    """
    Generate a quiz question using the Gemini API.

    Args:
        subject (str): Optional subject for the question.
        difficulty (str): Optional difficulty level (easy, medium, hard).

    Returns:
        dict: Question in JSON format with question, options, and correct answer index.
    """
    # Build the prompt based on subject and difficulty
    if subject:
        prompt = f"Generate a multiple-choice quiz question about {subject}."
    else:
        prompt = "Generate a random multiple-choice quiz question on a general knowledge topic."
    
    # Add difficulty level to the prompt
    if difficulty:
        prompt += f" The difficulty level should be {difficulty}."
    
    # Add specific instructions for format
    full_prompt = f'''
    {prompt}

    The question should be in JSON format with the following structure:
    {{
      "question": "The question text.",
      "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
      "answer": "The correct answer text from the options array."
    }}

    Ensure the 'answer' field exactly matches one of the strings in the 'options' array.
    
    For difficulty levels:
    - Easy: Questions should be straightforward and suitable for beginners
    - Medium: Questions should require some knowledge but not be too challenging
    - Hard: Questions should be challenging and require deep knowledge of the topic
    '''

    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(full_prompt)

        # Clean the response to extract only the JSON part
        cleaned_response = response.text.strip().replace("```json", "").replace("```", "").strip()

        question_data = json.loads(cleaned_response)

        # Find the index of the correct answer
        try:
            answer_index = question_data["options"].index(question_data["answer"])
            question_data["answer"] = answer_index
            return question_data
        except (ValueError, KeyError):
            raise Exception("AI response did not format the answer correctly.")

    except google.api_core.exceptions.PermissionDenied as e:
        print(f"Gemini API Permission Denied: {e}")
        raise Exception("Gemini API key is invalid or has insufficient permissions. Please check your API key and project settings.")
    except google.api_core.exceptions.NotFound as e:
        print(f"Gemini Model Not Found: {e}")
        raise Exception("The specified Gemini model was not found. Please check the model name.")
    except Exception as e:
        # A more descriptive error for the user
        print(f"Error generating quiz question: {e}")
        raise Exception("The AI service is currently unavailable. Please try again later.")


if __name__ == '__main__':
    try:
        question = generate_quiz_question("The Renaissance", "medium")
        print(json.dumps(question, indent=2))
    except Exception as e:
        print(e)
