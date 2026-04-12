import random 
import string

class QuizSession:
    def __init__(self, user_id, mode="single", difficulty="medium"):
        self.mode = mode
        self.difficulty = difficulty
        self.questions = []
        self.players = [user_id]
        self.scores = {user_id: 0}
        self.ready = set()
        self.answered = set()

    def current_question(self):
        return self.questions[-1] if self.questions else None

    def submit_answer(self, user_id, answer_idx):
        if self.current_question()["answer"] == answer_idx:
            self.scores[user_id] += 1
            return True
        return False

sessions = {}

def create_session(user_id, **kwargs):
    s_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    sessions[s_id] = QuizSession(user_id, **kwargs)
    return s_id

def get_session(s_id): return sessions.get(s_id)
def delete_session(s_id): sessions.pop(s_id, None)
