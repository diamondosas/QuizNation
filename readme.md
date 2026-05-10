
NOTE : BOT IS NOT CURRENTLY WORKING BEACUSE BACKEND SERVICE HAS EXPIRED
# QuizNation - Telegram Quiz Bot

## Project Overview
A Telegram bot that connects people to test their knowledge with AI-generated quizzes of 10 questions on various subjects.

## Key Features
- **AI-generated questions**: Uses AI API to create quizzes dynamically
- **Multiple game modes**: Single Player and Competitive Multiplayer
- **Multiple difficulty levels**: Easy, Medium, Hard
- **Random subjects**: Questions automatically use random subjects from predefined categories
- **10-question quizzes**: Complete quiz experience with scoring
- **Interactive UI**: Keyboard-based interface with emojis
- **Real-time multiplayer**: Battle mode where 2 players compete on the same questions

## Game Modes

### Single Player
- Test your knowledge alone
- Choose difficulty level
- Answer 10 questions automatically from random subjects
- Get performance feedback based on score

### Multiplayer
- Real-time competitive battles
- Wait for opponent or start searching
- Both players answer the same questions
- Live score tracking during the battle
- Winner announcement at the end

## Technology Stack
- Python (main)
- Telegram Bot API
- AI integration for question generation
- Session management for quiz state
- In-memory multiplayer session tracking

## Main Files
- `main.py` - Main bot application with command handlers, quiz logic, and multiplayer functionality
- `assets/subjects.txt` - Available quiz subjects (if missing, defaults to built-in list)
- Environment variables via `.env` file with `TELEGRAM_TOKEN`

## Important Code Information
- **Token**: Currently hardcoded as `8448601963:AAFw6ly7sQSWxN403Ty7MmDuZ3-ks_FNWGg` (should use environment variable in production)
- **Dependency modules**: `ai` (question generation), `sessions` (session management)
- **User states**: In-memory dictionary for tracking user quiz progress and game mode
- **Multiplayer sessions**: Separate dictionary (`multiplayer_sessions`) for managing competitive games
- **Multiplayer queue**: Dictionary (`multiplayer_queue`) for matching waiting players
- **Subjects**: Loaded from file or defaults to 10 predefined categories (always used randomly)

## Commands
- `/start` - Start the bot
- `/quiz` - Start a new quiz (asks for game mode)
- `/stop` - Stop current quiz (works for both single and multiplayer)
- `/help` - Show help message

## Quiz Flow

### Single Player Mode
1. User starts quiz with `/quiz`
2. Selects "Single Player" mode
3. Selects difficulty level (Easy, Medium, Hard)
4. Quiz starts with questions on random subjects
5. 10 questions with multiple choice answers
6. Score calculation and performance feedback
7. Option to start new quiz

### Multiplayer Mode
1. User starts quiz with `/quiz`
2. Selects "Multiplayer" mode
3. Bot either:
   - Matches with waiting opponent, or
   - Adds user to queue for matching
4. Both players select difficulty level independently
5. Quiz starts with same questions for both players
6. Real-time score tracking during questions
7. Winner announcement after 10 questions
8. Option to start new battle

## Multiplayer Details
- **Matching**: Players are automatically matched when one player is waiting
- **Session Management**: Each multiplayer game has its own session ID
- **Score Tracking**: Individual scores are tracked for each player
- **Real-time Updates**: Players are notified when opponent answers questions
- **Winner Determination**: Higher score wins, tie if equal

## Performance Notes
- Optimized for simplicity and performance
- Clear user states to track quiz progress and game mode
- Graceful error handling for AI service issues and multiplayer failures
- Memory-efficient multiplayer session cleanup
- Responsive user interface with timely updates

## Known Considerations
- Multiplayer matching depends on timing - requires players to start quiz around same time
- If opponent leaves during multiplayer game, both players are notified
- AI service downtime affects single and multiplayer modes equally
- Sessions are stored in memory only (not persistent)
