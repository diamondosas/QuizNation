import json
import time
import random
import string

# In-memory storage for sessions
# In a production environment, you might want to use a database
sessions = {}

def generate_session_id(length=10):
    """Generate a random session ID"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def create_session(user_id, subject=None):
    """Create a new quiz session for a user"""
    session_id = generate_session_id()
    
    sessions[session_id] = {
        "user_id": user_id,
        "subject": subject,  # Initial subject, but we'll change it per question
        "questions": [],
        "current_question": 0,
        "score": 0,
        "total_questions": 10,
        "created_at": time.time(),
        "updated_at": time.time()
    }
    
    return session_id

def get_session(session_id):
    """Retrieve a session by ID"""
    return sessions.get(session_id)

def update_session(session_id, **kwargs):
    """Update session data"""
    if session_id in sessions:
        for key, value in kwargs.items():
            sessions[session_id][key] = value
        sessions[session_id]["updated_at"] = time.time()
        return True
    return False

def add_question_to_session(session_id, question_data):
    """Add a question to the session"""
    if session_id in sessions:
        sessions[session_id]["questions"].append(question_data)
        sessions[session_id]["updated_at"] = time.time()
        return True
    return False

def get_current_question(session_id):
    """Get the current question for a session"""
    session = get_session(session_id)
    if session and session["current_question"] < len(session["questions"]):
        return session["questions"][session["current_question"]]
    return None

def move_to_next_question(session_id):
    """Move to the next question in the session"""
    session = get_session(session_id)
    if session:
        if session["current_question"] < session["total_questions"] - 1:
            sessions[session_id]["current_question"] += 1
            sessions[session_id]["updated_at"] = time.time()
            return True
    return False

def submit_answer(session_id, answer_index):
    """Submit an answer and update score if correct"""
    session = get_session(session_id)
    if session:
        current_q = get_current_question(session_id)
        if current_q and "answer" in current_q:
            if current_q["answer"] == answer_index:
                sessions[session_id]["score"] += 1
                sessions[session_id]["updated_at"] = time.time()
                return True
    return False

def get_session_score(session_id):
    """Get the current score for a session"""
    session = get_session(session_id)
    return session["score"] if session else 0

def get_multiplayer_scores(session_id):
    """Get both player scores for a multiplayer session"""
    session = get_session(session_id)
    if session:
        return session.get("scores", {})
    return {}

def is_session_complete(session_id):
    """Check if the session is complete"""
    session = get_session(session_id)
    if session:
        return session["current_question"] >= session["total_questions"] - 1
    return True

def delete_session(session_id):
    """Delete a session"""
    if session_id in sessions:
        del sessions[session_id]
        return True
    return False

# For testing purposes
if __name__ == "__main__":
    # Create a test session
    session_id = create_session("test_user", "easy", "general knowledge")
    print(f"Created session: {session_id}")
    
    # Retrieve session
    session = get_session(session_id)
    print(f"Session data: {session}")