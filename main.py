import os
import logging
import random
import asyncio
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, BotCommand
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Import our custom modules
from ai import generate_quiz_question
from sessions import (
    create_session, 
    get_session, 
    update_session, 
    add_question_to_session, 
    get_current_question, 
    move_to_next_question, 
    submit_answer, 
    get_session_score, 
    is_session_complete
)

# Load environment variables from .env file
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Load token from environment
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    TOKEN = "8448601963:AAFw6ly7sQSWxN403Ty7MmDuZ3-ks_FNWGg"

# Store user states (in production, use a database)
user_states = {}

# Load subjects from file
try:
    with open('assets/subjects.txt', 'r', encoding='utf-8') as f:
        SUBJECTS = [line.strip() for line in f if line.strip()]
except FileNotFoundError:
    logger.warning("subjects.txt not found. Using a default list of subjects.")
    SUBJECTS = [
        "General Knowledge", "Science", "History", "Geography", "Movies",
        "Music", "Sports", "Literature", "Art", "Technology"
    ]
except Exception as e:
    logger.error(f"Error reading subjects.txt: {e}. Using a default list of subjects.")
    SUBJECTS = [
        "General Knowledge", "Science", "History", "Geography", "Movies",
        "Music", "Sports", "Literature", "Art", "Technology"
    ]

# Ensure we have subjects
if not SUBJECTS:
    logger.warning("SUBJECTS list is empty. Using a default list of subjects.")
    SUBJECTS = [
        "General Knowledge", "Science", "History", "Geography", "Movies",
        "Music", "Sports", "Literature", "Art", "Technology"
    ]

# Define difficulty levels
DIFFICULTY_LEVELS = {
    "easy": "Easy - suitable for beginners",
    "medium": "Medium - suitable for intermediate learners", 
    "hard": "Hard - suitable for advanced learners"
}

# Define quiz modes
QUIZ_MODES = {
    "single": "Single Player - Test your knowledge alone",
    "multi": "Multiplayer - Compete with another player!"
}

# Define command handler for /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Hello {user.first_name}! Welcome to QuizNation!\n\n"
        f"🎯 This is a quiz bot where you can test your knowledge with 10 questions.\n\n"
        f" Type /quiz to start a new quiz!"
    )

# Define command handler for /quiz
async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start a new quiz session - ask for game mode first."""
    user_id = update.effective_user.id
    
    # Ask user to select quiz mode
    keyboard = list(QUIZ_MODES.keys())
    keyboard = [[mode.capitalize()] for mode in keyboard]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    user_states[user_id] = {"awaiting_mode": True}
    
    await update.message.reply_text(
        "🎮 Please select a game mode:",
        reply_markup=reply_markup
    )

# Handle game mode selection
async def handle_mode_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user's game mode selection."""
    user_id = update.effective_user.id
    user_answer = update.message.text.lower()
    
    # Check if user is selecting mode
    if user_id in user_states and user_states[user_id].get("awaiting_mode", False):
        if user_answer not in QUIZ_MODES.keys():
            keyboard = [[mode.capitalize()] for mode in QUIZ_MODES.keys()]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            
            await update.message.reply_text(
                "👆 Please select a valid game mode:",
                reply_markup=reply_markup
            )
            return
        
        # Store game mode
        user_states[user_id]["quiz_mode"] = user_answer
        user_states[user_id]["awaiting_mode"] = False
        
        if user_answer == "single":
            # Ask for difficulty level for single player
            keyboard = [[level.capitalize()] for level in DIFFICULTY_LEVELS.keys()]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            
            user_states[user_id]["awaiting_difficulty"] = True
            
            await update.message.reply_text(
                "🕹️ Please select a difficulty level:",
                reply_markup=reply_markup
            )
        elif user_answer == "multi":
            # Start multiplayer mode - looking for opponent
            await start_multiplayer_mode(update, context, user_id)
        return

# Multiplayer setup
multiplayer_queue = {}  # Store users waiting for opponents
multiplayer_sessions = {}  # Store active multiplayer games

# Start multiplayer mode
async def start_multiplayer_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    """Start multiplayer mode - looking for opponent or creating new game."""
    # Check if there's already someone waiting
    if len(multiplayer_queue) > 0:
        # Find the first user waiting
        opponent_id = list(multiplayer_queue.keys())[0]
        
        # Create a multiplayer session
        session_id = f"multi_{user_id}_{opponent_id}"
        
        multiplayer_sessions[session_id] = {
            "player1": user_id,
            "player2": opponent_id,
            "current_question": 0,
            "scores": {user_id: 0, opponent_id: 0},
            "question_count": 0,
            "questions": [],
            "difficulty": "medium",  # Default difficulty for now
            "subject": "random"
        }
        
        # Remove opponent from queue
        del multiplayer_queue[opponent_id]
        
        # Update both users' states
        user_states[user_id] = {
            "session_id": session_id,
            "player_id": "player1",
            "awaiting_answer": False,
            "quiz_mode": "multi"
        }
        
        user_states[opponent_id] = {
            "session_id": session_id,
            "player_id": "player2", 
            "awaiting_answer": False,
            "quiz_mode": "multi"
        }
        
        # Let both users know they're matched
        await update.message.reply_text(
            "🎉 Match found! You're now in a multiplayer battle!"
        )
        
        # Notify the opponent
        try:
            context.bot.send_message(
                chat_id=opponent_id,
                text="🎉 You've been matched for a multiplayer battle! Get ready..."
            )
        except Exception as e:
            logger.error(f"Failed to notify opponent: {e}")
        
        # Ask both users for difficulty level
        keyboard = [[level.capitalize()] for level in DIFFICULTY_LEVELS.keys()]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        await update.message.reply_text(
            "🕹️ Both players select difficulty level:",
            reply_markup=reply_markup
        )
        
        # Update session state to wait for difficulty selection
        multiplayer_sessions[session_id]["awaiting_difficulty"] = {user_id, opponent_id}
        
    else:
        # Add this user to the queue
        multiplayer_queue[user_id] = True
        
        await update.message.reply_text(
            "🔍 Looking for an opponent... Waiting for another player to join."
        )

# Show subject selection - no longer used since subjects are always random
async def show_subject_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    """Show subject selection options - no longer used since subjects are always random."""
    await update.message.reply_text(
        "🤔 Subjects are now always random. Please select difficulty level again.",
        reply_markup=ReplyKeyboardRemove()
    )

# Handle single player difficulty selection
async def handle_difficulty_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user's difficulty selection for single player mode."""
    user_id = update.effective_user.id
    user_answer = update.message.text.lower()
    
    # Check if user is selecting difficulty
    if user_id in user_states and user_states[user_id].get("awaiting_difficulty", False):
        if user_answer not in DIFFICULTY_LEVELS.keys():
            keyboard = [[level.capitalize()] for level in DIFFICULTY_LEVELS.keys()]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            
            await update.message.reply_text(
                "👆 Please select a valid difficulty level:",
                reply_markup=reply_markup
            )
            return
        
        # Store difficulty and start quiz
        user_states[user_id]["difficulty"] = user_answer
        user_states[user_id]["awaiting_difficulty"] = False
        
        # Start quiz with random subjects
        await start_quiz_with_random_subjects(update, context, user_id)
        return

# Handle multiplayer difficulty selection
async def handle_multi_difficulty_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle difficulty selection for multiplayer mode."""
    user_id = update.effective_user.id
    user_answer = update.message.text.lower()
    
    if user_id in user_states and user_states[user_id].get("quiz_mode") == "multi":
        session_id = user_states[user_id]["session_id"]
        session = multiplayer_sessions.get(session_id)
        
        if session and "awaiting_difficulty" in session:
            if user_answer not in DIFFICULTY_LEVELS.keys():
                keyboard = [[level.capitalize()] for level in DIFFICULTY_LEVELS.keys()]
                reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
                
                await update.message.reply_text(
                    "👆 Please select a valid difficulty level:",
                    reply_markup=reply_markup
                )
                return
            
            # Store difficulty for this user
            session["difficulty"] = user_answer
            
            # Remove user from awaiting_difficulty set
            session["awaiting_difficulty"].discard(user_id)
            
            # Check if both players have selected difficulty
            if not session["awaiting_difficulty"]:
                # Both players ready, start multiplayer quiz
                session.pop("awaiting_difficulty", None)
                await start_multiplayer_quiz(update, context, session_id, user_id)
            
            return
    
    await update.message.reply_text(
        "🤔 You're not in a multiplayer setup. Start a new quiz with /quiz."
    )

# Handle subject selection - no longer used since subjects are always random
async def handle_subject_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user's subject choice - no longer used since subjects are always random."""
    user_id = update.effective_user.id
    
    # Since subjects are always random, just start the quiz with the already selected difficulty
    await update.message.reply_text(
        "🤔 Subjects are now always random. Starting quiz with your selected difficulty...",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Start quiz with random subjects
    await start_quiz_with_random_subjects(update, context, user_id)

# Start multiplayer quiz
async def start_multiplayer_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, session_id: str, user_id: int) -> None:
    """Start the multiplayer quiz session."""
    session = multiplayer_sessions[session_id]
    difficulty = session["difficulty"]
    subject_choice = session["subject"]
    
    await update.message.reply_text(
        f"🎮 Starting multiplayer battle!\n"
        f"Difficulty: {difficulty.capitalize()}\n"
        f"Subject: {subject_choice if subject_choice != 'random' else 'Random'}\n\n"
        f"Get ready for 10 questions to test your knowledge against your opponent!\n\n"
        f"Generating your first question...",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Notify both players that the quiz is starting
    opponent_id = session["player1"] if user_id == session["player2"] else session["player2"]
    try:
        context.bot.send_message(
            chat_id=opponent_id,
            text=f"🎮 The multiplayer battle is starting!\n"
                 f"Difficulty: {difficulty.capitalize()}\n"
                 f"Subject: {subject_choice if subject_choice != 'random' else 'Random'}\n\n"
                 f"Get ready for 10 questions to test your knowledge!"
        )
    except Exception as e:
        logger.error(f"Failed to notify opponent about quiz start: {e}")
    
    # Generate first question for both players
    await generate_and_send_multi_question(update, context, session_id)

# Start quiz with random subjects
async def start_quiz_with_random_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    """Start quiz with random subjects."""
    user_states[user_id]["subject"] = "random"
    user_states[user_id]["awaiting_subject"] = False
    
    # Start the quiz
    await start_quiz(update, context, user_id)

# Start the actual quiz
async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    """Start the actual quiz session."""
    difficulty = user_states[user_id].get("difficulty", "medium")
    subject_choice = user_states[user_id].get("subject", "random")
    
    # Create a new session
    session_id = create_session(user_id, subject_choice)
    user_states[user_id]["session_id"] = session_id
    user_states[user_id]["awaiting_answer"] = False
    
    await update.message.reply_text(
        f"🎮 Starting a new quiz!\n"
        f"Difficulty: {difficulty.capitalize()}\n"
        f"Subject: {subject_choice if subject_choice != 'random' else 'Random'}\n\n"
        f"Get ready for 10 questions to test your knowledge.\n"
        f"You can stop at any time by typing /stop.\n\n"
        f"Generating your first question...",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Generate first question
    await generate_and_send_question(update, context, session_id)

# Generate and send multiplayer question
async def generate_and_send_multi_question(update: Update, context: ContextTypes.DEFAULT_TYPE, session_id: str) -> None:
    """Generate a new question and send it to both players in multiplayer mode."""
    session = multiplayer_sessions[session_id]
    user_id = update.effective_user.id
    
    # Determine subject - random or fixed
    if session.get("subject") == "random" or session.get("subject") is None:
        subject = random.choice(SUBJECTS)
    else:
        subject = session.get("subject")
    
    # Get difficulty level
    difficulty = session["difficulty"]
    
    # Generate a question using AI with difficulty level
    try:
        question_data = generate_quiz_question(subject, difficulty)
    except Exception as e:
        logger.error(f"Error generating multiplayer question: {e}")
        await update.message.reply_text(
            "❌ Oops! I couldn't generate a question right now. The AI service might be down. Please try again later."
        )
        # Clear multiplayer session
        del multiplayer_sessions[session_id]
        if user_id in user_states:
            del user_states[user_id]
        return

    # Store question in session
    session["questions"].append(question_data)
    session["question_count"] += 1
    
    # Send question to both players
    question_text = question_data["question"]
    options = question_data["options"]
    
    # Create keyboard with options
    keyboard = [[option] for option in options]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    # Improve UI with emojis and better formatting
    text = f"📝 <b>Question {session['question_count']}/10</b>\n\n{question_text}"

    # Send to current user
    await update.message.reply_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    
    # Mark that both players are waiting for answers
    session["awaiting_answers"] = {session["player1"], session["player2"]}
    session["current_question_data"] = question_data

# Generate and send a question
async def generate_and_send_question(update: Update, context: ContextTypes.DEFAULT_TYPE, session_id: str) -> None:
    """Generate a new question and send it to the user."""
    session = get_session(session_id)
    user_id = session["user_id"]
    
    # Determine subject - random or fixed
    if session.get("subject") == "random" or session.get("subject") is None:
        subject = random.choice(SUBJECTS)
    else:
        subject = session.get("subject")
    
    # Get difficulty level
    difficulty = user_states[user_id].get("difficulty", "medium")
    
    # Generate a question using AI with difficulty level
    try:
        question_data = generate_quiz_question(subject, difficulty)
    except Exception as e:
        logger.error(f"Error generating question: {e}")
        await update.message.reply_text(
            "❌ Oops! I couldn't generate a question right now. The AI service might be down. Please try again later."
        )
        # Clear user state
        if user_id in user_states:
            del user_states[user_id]
        return

    # Add question to session
    add_question_to_session(session_id, question_data)
    
    # Send question to user
    question_text = question_data["question"]
    options = question_data["options"]
    
    # Create keyboard with options
    keyboard = [[option] for option in options]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    
    # Improve UI with emojis and better formatting
    text = f"📝 <b>Question {session['current_question'] + 1}/10</b>\n\n{question_text}"

    await update.message.reply_text(
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )
    
    # Mark that we're waiting for an answer
    user_states[user_id]["awaiting_answer"] = True

# Handle user answers
async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user's answer to a question."""
    user_id = update.effective_user.id
    
    # Check if user is in any part of the quiz process
    if user_id not in user_states:
        await update.message.reply_text(
            "🤔 You're not in a quiz right now. Start one with /quiz",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    # Check if we're waiting for mode selection
    if user_states[user_id].get("awaiting_mode", False):
        await handle_mode_selection(update, context)
        return
    
    # Check if we're waiting for difficulty selection
    if user_states[user_id].get("awaiting_difficulty", False):
        await handle_difficulty_selection(update, context)
        return
    
    # Check if we're waiting for multiplayer difficulty selection
    if user_states[user_id].get("quiz_mode") == "multi" and "session_id" in user_states[user_id]:
        session_id = user_states[user_id]["session_id"]
        session = multiplayer_sessions.get(session_id)
        
        if session and "awaiting_difficulty" in session and user_id in session["awaiting_difficulty"]:
            await handle_multi_difficulty_selection(update, context)
            return
    
    # Check if we're in legacy subject choice mode (no longer applicable)
    if user_states[user_id].get("difficulty") and not user_states[user_id].get("subject"):
        await handle_subject_choice(update, context)
        return
    
    # Check if user is in multiplayer mode and waiting for an answer
    if user_states[user_id].get("quiz_mode") == "multi" and "session_id" in user_states[user_id]:
        session_id = user_states[user_id]["session_id"]
        session = multiplayer_sessions.get(session_id)
        
        if session and "awaiting_answers" in session and user_id in session["awaiting_answers"]:
            # Handle multiplayer answer
            current_question = session["current_question_data"]
            
            if not current_question:
                await update.message.reply_text(
                    "⁉️ Error retrieving question. Please try again later.",
                    reply_markup=ReplyKeyboardRemove()
                )
                return
            
            # Get user's answer
            user_answer = update.message.text
            options = current_question["options"]
            
            # Check if answer is valid
            if user_answer not in options:
                keyboard = [[option] for option in options]
                reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
                
                await update.message.reply_text(
                    "👆 Please select one of the provided options:",
                    reply_markup=reply_markup
                )
                return
            
            # Find answer index
            answer_index = options.index(user_answer)
            correct_answer_index = current_question["answer"]
            is_correct = (answer_index == correct_answer_index)
            
            # Update player score
            if is_correct:
                session["scores"][user_id] += 1
                await update.message.reply_text("🎉 ✅ Correct! Good job!")
            else:
                correct_answer = options[correct_answer_index]
                await update.message.reply_text(f"😢 ❌ Incorrect. The correct answer was:\n<b>{correct_answer}</b>", parse_mode=ParseMode.HTML)
            
            # Remove user from awaiting answers
            session["awaiting_answers"].discard(user_id)
            
            # Check if both players have answered or timeout
            opponent_id = session["player1"] if user_id == session["player2"] else session["player2"]
            
            # Notify opponent about their score this round
            try:
                current_score = session["scores"][user_id]
                opponent_score = session["scores"][opponent_id]
                round_number = session["question_count"]
                
                context.bot.send_message(
                    chat_id=opponent_id,
                    text=f"🔔 Your opponent answered! Question {round_number}:\n"
                         f"Your current score: {opponent_score}\n"
                         f"Opponent's score: {current_score}"
                )
            except Exception as e:
                logger.error(f"Failed to notify opponent about answer: {e}")
            
            # Check if round is complete (both answered or timeout)
            if not session["awaiting_answers"] or session["question_count"] >= 10:
                # Round is complete, move to next question or finish
                if session["question_count"] >= 10:
                    # Multiplayer quiz complete
                    await finish_multiplayer_quiz(update, context, session_id)
                else:
                    # Move to next question
                    session["current_question"] += 1
                    await generate_and_send_multi_question(update, context, session_id)
            return
    
    # Check if we're waiting for an answer to a question
    if user_states[user_id].get("awaiting_answer", False) and "session_id" in user_states[user_id]:
        session_id = user_states[user_id]["session_id"]
        session = get_session(session_id)
        
        if not session:
            await update.message.reply_text(
                "⏰ Session expired. Start a new quiz with /quiz",
                reply_markup=ReplyKeyboardRemove()
            )
            if user_id in user_states:
                del user_states[user_id]
            return
        
        # Get current question
        current_question = get_current_question(session_id)
        if not current_question:
            await update.message.reply_text(
                "⁉️ Error retrieving question. Please start a new quiz with /quiz",
                reply_markup=ReplyKeyboardRemove()
            )
            return
        
        # Get user's answer
        user_answer = update.message.text
        options = current_question["options"]
        
        # Check if answer is valid
        if user_answer not in options:
            keyboard = [[option] for option in options]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
            
            await update.message.reply_text(
                "👆 Please select one of the provided options:",
                reply_markup=reply_markup
            )
            return
        
        # Find answer index
        answer_index = options.index(user_answer)
        
        # Submit answer
        is_correct = submit_answer(session_id, answer_index)
        
        # Provide feedback with emojis
        correct_answer = options[current_question["answer"]]
        if is_correct:
            await update.message.reply_text("🎉 ✅ Correct! Good job!")
        else:
            await update.message.reply_text(f"😢 ❌ Incorrect. The correct answer was:\n<b>{correct_answer}</b>", parse_mode=ParseMode.HTML)
        
        # Move to next question or finish quiz
        if is_session_complete(session_id):
            # Quiz complete
            score = get_session_score(session_id)
            percentage = int((score / 10) * 100)
            
            # Add performance feedback with emojis
            if percentage >= 80:
                performance = "🏆 Excellent!"
            elif percentage >= 60:
                performance = "👍 Good job!"
            elif percentage >= 40:
                performance = "👌 Not bad!"
            else:
                performance = "📚 Keep learning!"
            
            difficulty = user_states[user_id].get("difficulty", "medium")
            subject = get_session(session_id).get("subject", "random")
            
            await update.message.reply_text(
                f"🎊 Quiz complete! Your final score is {score}/10 ({percentage}%)\n\n"
                f"Difficulty: {difficulty.capitalize()}\n"
                f"Subject: {subject if subject != 'random' else 'Random'}\n\n"
                f"{performance}\n\n"
                f"Thanks for playing! Start a new quiz with /quiz",
                reply_markup=ReplyKeyboardRemove()
            )
            # Clear user state
            del user_states[user_id]
        else:
            # Move to next question
            move_to_next_question(session_id)
            await generate_and_send_question(update, context, session_id)
        return
    
    # If we get here, user is in a quiz setup but not in a specific state
    await update.message.reply_text(
        "🤔 You're not in a quiz right now. Start one with /quiz",
        reply_markup=ReplyKeyboardRemove()
    )

# Finish multiplayer quiz
async def finish_multiplayer_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, session_id: str) -> None:
    """Finish multiplayer quiz and determine winner."""
    session = multiplayer_sessions[session_id]
    user_id = update.effective_user.id
    
    player1_score = session["scores"][session["player1"]]
    player2_score = session["scores"][session["player2"]]
    
    # Prepare results for both players
    result_text = (
        f"🎊 Multiplayer Battle Complete!\n\n"
        f"🏆 Final Scores:\n"
        f"Player 1: {player1_score}/10\n"
        f"Player 2: {player2_score}/10\n\n"
    )
    
    # Determine winner and add appropriate emoji
    if player1_score > player2_score:
        winner_text = "🏆 Player 1 Wins! 🎉"
    elif player2_score > player1_score:
        winner_text = "🏆 Player 2 Wins! 🎉"
    else:
        winner_text = "🤝 It's a Tie! 🤝"
    
    result_text += f"{winner_text}\n\nGreat battle! Thanks for playing!"
    
    # Notify current user
    await update.message.reply_text(
        result_text,
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Notify the other player
    opponent_id = session["player1"] if user_id == session["player2"] else session["player2"]
    try:
        context.bot.send_message(
            chat_id=opponent_id,
            text=f"🎊 Multiplayer Battle Complete!\n\n"
                 f"🏆 Final Scores:\n"
                 f"You: {session['scores'][opponent_id]}/10\n"
                 f"Opponent: {'player1' if user_id == session['player1'] else 'player2'}: {player1_score if user_id == session['player2'] else player2_score}/10\n\n"
                 f"{winner_text}\n\n"
                 f"Great battle! Thanks for playing!"
        )
    except Exception as e:
        logger.error(f"Failed to notify opponent about multiplayer finish: {e}")
    
    # Clean up multiplayer session and user states
    del multiplayer_sessions[session_id]
    if session["player1"] in user_states:
        del user_states[session["player1"]]
    if session["player2"] in user_states:
        del user_states[session["player2"]]

# Define command handler for /stop
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    
    if user_id in user_states and "session_id" in user_states[user_id]:
        session_id = user_states[user_id]["session_id"]
        quiz_mode = user_states[user_id].get("quiz_mode", "single")
        
        if quiz_mode == "multi":
            # Handle multiplayer stop
            session = multiplayer_sessions.get(session_id)
            if session:
                # Get scores
                player1_score = session["scores"].get(session["player1"], 0)
                player2_score = session["scores"].get(session["player2"], 0)
                current_question = session["question_count"]
                
                # Determine whose turn/message this is
                is_player1 = user_id == session["player1"]
                is_player2 = user_id == session["player2"]
                
                # Find opponent
                opponent_id = session["player2"] if is_player1 else session["player1"]
                opponent_player = "Player 2" if is_player1 else "Player 1"
                
                await update.message.reply_text(
                    f"⏹️ Multiplayer battle stopped by {opponent_player}.\n\n"
                    f"Scores when stopped:\n"
                    f"You: {player1_score if is_player1 else player2_score}\n"
                    f"{opponent_player}: {player2_score if is_player1 else player1_score}\n\n"
                    f"👋 Thanks for playing! Start a new quiz with /quiz",
                    reply_markup=ReplyKeyboardRemove()
                )
                
                # Notify opponent
                try:
                    context.bot.send_message(
                        chat_id=opponent_id,
                        text=f"⏹️ Your opponent left the multiplayer battle.\n\n"
                             f"Final scores:\n"
                             f"You: {player2_score if is_player1 else player1_score}\n"
                             f"Opponent: {player1_score if is_player1 else player2_score}\n\n"
                             f"👋 Thanks for playing! Start a new quiz with /quiz"
                    )
                except Exception as e:
                    logger.error(f"Failed to notify opponent about multiplayer stop: {e}")
                
                # Clean up multiplayer session
                del multiplayer_sessions[session_id]
                if session["player1"] in user_states:
                    del user_states[session["player1"]]
                if session["player2"] in user_states:
                    del user_states[session["player2"]]
        else:
            # Handle single player stop
            score = get_session_score(session_id)
            current_question = get_session(session_id)["current_question"] + 1
            
            difficulty = user_states[user_id].get("difficulty", "medium")
            subject = get_session(session_id).get("subject", "random")
            
            await update.message.reply_text(
                f"⏹️ Quiz stopped. Your current score is {score}/{current_question}.\n\n"
                f"Difficulty: {difficulty.capitalize()}\n"
                f"Subject: {subject if subject != 'random' else 'Random'}\n\n"
                f"👋 Thanks for playing! Start a new quiz with /quiz",
                reply_markup=ReplyKeyboardRemove()
            )
            
            # Clear user state
            del user_states[user_id]
    else:
        await update.message.reply_text(
            "🤔 You're not in a quiz right now. Start one with /quiz",
            reply_markup=ReplyKeyboardRemove()
        )

# Define command handler for /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "ℹ️ <b>QuizNation Bot Help</b>\n\n"
        "Commands:\n"
        "• /start - Start the bot\n"
        "• /quiz - Start a new quiz session\n"
        "• /stop - Stop the current quiz\n"
        "• /help - Show this help message\n\n"
        "Quiz Modes:\n"
        "🎮 Single Player - Test your knowledge alone\n"
        "🎮 Multiplayer - Compete against another player in real-time!\n\n"
        "During a quiz setup, you'll be asked to select:\n"
        "1. Game Mode (Single or Multiplayer)\n"
        "2. Difficulty level (Easy, Medium, Hard)\n"
        "3. Questions automatically use random subjects\n\n"
        "In Multiplayer mode:\n"
        "- Wait for another player to join\n"
        "- Both players answer the same questions\n"
         "- Real-time score tracking and winner announcement\n\n"
        "During the quiz, you'll receive multiple choice questions. "
        "Select one of the options to answer. Answer all 10 questions to complete the quiz! 🎯",
        parse_mode=ParseMode.HTML
    )

# Define main function
def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(TOKEN).build()

    # Set bot commands
    commands = [
        BotCommand("start", "Start the BOT"),
        BotCommand("quiz", "Start a Quiz"),
        BotCommand("stop", "Stop a Quiz"),
        BotCommand("help", "HELP"),
    ]
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("quiz", quiz))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("help", help_command))

    # Add message handler for game mode, difficulty, and answers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()