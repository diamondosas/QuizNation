import os
import logging
import random
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv

from ai import generate_quiz_question
from sessions import create_session, get_session, delete_session

load_dotenv()
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
TOKEN = os.getenv("TELEGRAM_TOKEN")
SUBJECTS = open('assets/subjects.txt').read().splitlines() if os.path.exists('assets/subjects.txt') else ["Science", "History", "Movies", "Music", "Sports"]
DIFFS, MODES = ["Easy", "Medium", "Hard"], ["Single", "Multi"]

user_states, multi_queue = {}, []

def get_kb(options): return ReplyKeyboardMarkup([[o] for o in options], one_time_keyboard=True, resize_keyboard=True)

async def start(update, context):
    await update.message.reply_text(f"👋 Hello {update.effective_user.first_name}! Welcome!\n/quiz to start!")

async def quiz(update, context):
    u_id = update.effective_user.id
    user_states[u_id] = {"state": "MODE"}
    await update.message.reply_text("🎮 Select game mode:", reply_markup=get_kb(MODES))

async def stop(update, context):
    u_id = update.effective_user.id
    if u_id in user_states:
        s_id = user_states[u_id].get("s_id")
        if s_id:
            session = get_session(s_id)
            for p in session.players:
                user_states.pop(p, None)
                await context.bot.send_message(p, "⏹️ Quiz stopped.", reply_markup=ReplyKeyboardRemove())
            delete_session(s_id)
        else:
            user_states.pop(u_id, None)
            if u_id in multi_queue: multi_queue.remove(u_id)
            await update.message.reply_text("⏹️ Stopped.", reply_markup=ReplyKeyboardRemove())
    else: await update.message.reply_text("No active quiz.")

async def send_q(context, s_id):
    session = get_session(s_id)
    try:
        q = generate_quiz_question(random.choice(SUBJECTS), session.difficulty)
        session.questions.append(q)
        text = f"📝 <b>Question {len(session.questions)}/10</b>\n\n{q['question']}"
        for p in session.players:
            user_states[p]["state"] = "ANSWER"
            await context.bot.send_message(p, text, reply_markup=get_kb(q['options']), parse_mode=ParseMode.HTML)
    except:
        for p in session.players:
            await context.bot.send_message(p, "❌ AI Error.")
            user_states.pop(p, None)
        delete_session(s_id)

async def handle_msg(update, context):
    u_id = update.effective_user.id
    msg = update.message.text
    state = user_states.get(u_id, {}).get("state")
    if not state: return

    if state == "MODE" and msg in MODES:
        if msg == "Single":
            user_states[u_id].update({"state": "DIFF", "mode": "single"})
            await update.message.reply_text("🕹️ Select difficulty:", reply_markup=get_kb(DIFFS))
        elif u_id not in multi_queue:
            if multi_queue:
                opp_id = multi_queue.pop(0)
                s_id = create_session(u_id, mode="multi")
                session = get_session(s_id)
                session.players.append(opp_id)
                session.scores[opp_id] = 0
                for p in session.players:
                    user_states[p] = {"state": "DIFF", "s_id": s_id}
                    await context.bot.send_message(p, "🎉 Match found! Both players select difficulty:", reply_markup=get_kb(DIFFS))
            else:
                multi_queue.append(u_id)
                await update.message.reply_text("🔍 Looking for opponent...")

    elif state == "DIFF" and msg in DIFFS:
        s_id = user_states[u_id].get("s_id")
        if not s_id: # Single player
            s_id = create_session(u_id, difficulty=msg.lower())
            user_states[u_id]["s_id"] = s_id
        
        session = get_session(s_id)
        session.difficulty = msg.lower()
        session.ready.add(u_id)
        if len(session.ready) == len(session.players):
            await send_q(context, s_id)
        else:
            user_states[u_id]["state"] = "WAIT_DIFF"
            await update.message.reply_text("Waiting for other player...")

    elif state == "ANSWER":
        s_id = user_states[u_id]["s_id"]
        session = get_session(s_id)
        q = session.current_question()
        if msg not in q['options']: return
        
        correct = session.submit_answer(u_id, q['options'].index(msg))
        await update.message.reply_text("✅ Correct!" if correct else f"❌ Wrong! Correct: {q['options'][q['answer']]}")
        
        session.answered.add(u_id)
        if len(session.answered) == len(session.players):
            session.answered.clear()
            if len(session.questions) >= 10:
                res = "🎊 Quiz Complete!\n" + "\n".join([f"Score: {session.scores[p]}/10" for p in session.players])
                for p in session.players:
                    user_states.pop(p, None)
                    await context.bot.send_message(p, res, reply_markup=ReplyKeyboardRemove())
                delete_session(s_id)
            else: 
                await send_q(context, s_id)
        else:
            await update.message.reply_text("Waiting for opponent...")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quiz", quiz))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app.run_polling()

if __name__ == "__main__": main()
