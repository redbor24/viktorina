import logging

from redis import Redis
from environs import Env
from telegram import KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (CommandHandler, ConversationHandler, Filters,
                          MessageHandler, RegexHandler, Updater)

from quiz_loader import load_quiz

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

CHOOSING, NEXT_QUESTION, REPEAT_QUESTION, CHECK_ANSWER, END_GAME, REPEAT_GAME, UNKNOWN = range(7)

HELPME = 'ПАМАГИТИИИ!!!!'
yes_no_keyboard = [['Да', 'Нет']]
yes_no_markup = ReplyKeyboardMarkup(yes_no_keyboard, resize_keyboard=True, one_time_keyboard=True)
helpme_markup = ReplyKeyboardMarkup([[HELPME]], resize_keyboard=True, one_time_keyboard=True)

quiz_questions = None
redis = None


def get_quiz_questions():
    quizzes = load_quiz('quiz-questions/1vs1200.txt')
    return len(quizzes), iter(quizzes)


def set_redis_var(user_id, name, value):
    global redis
    redis.set(f'{str(user_id)}:{name}', value)


def get_redis_var(user_id, name):
    global redis
    return redis.get(f'{str(user_id)}:{name}').decode('utf-8')


def start(update, _):
    update.message.reply_text(
        f'Привет, {update.effective_user.first_name}!\n'
        'Хочешь поучаствовать в викторине?',
        reply_markup=yes_no_markup)
    return CHOOSING


def next_question(user_id, questions):
    query = next(questions)
    set_redis_var(user_id, 'query', query['query'])
    set_redis_var(user_id, 'answer', query['answer'])


def start_game(update, context):
    global quiz_questions

    if update.message.text == 'Да':
        update.message.reply_text('Поехали!!!')
        questions_count, quiz_questions = get_quiz_questions()
        context.bot_data['questions_count'] = questions_count
        context.bot_data['good_answers'] = 0

        next_question(update.effective_user.id, quiz_questions)
        update.message.reply_text(f'Вопрос:\n{get_redis_var(update.effective_user.id, "query")}',
                                  reply_markup=helpme_markup)

        return CHECK_ANSWER

    elif update.message.text == 'Нет':
        update.message.reply_text('Ну, что ж... Заходи как-нибудь, поиграем...')
        return ConversationHandler.END

    else:
        return UNKNOWN


def check_answer(update, context):
    global quiz_questions

    if update.message.text == HELPME:
        update.message.reply_text(f'Правильный ответ:\n{get_redis_var(update.effective_user.id, "answer")}')
        try:
            next_question(update.effective_user.id, quiz_questions)
            update.message.reply_text(f'Вопрос:\n{get_redis_var(update.effective_user.id, "query")}',
                                      reply_markup=helpme_markup)
            return CHECK_ANSWER
        except StopIteration as exc:
            end_game(update, context)
            return END_GAME

    if update.message.text.lower() in get_redis_var(update.effective_user.id, 'answer').lower():
        update.message.reply_text('Правильно!')
        context.bot_data['good_answers'] += 1

        try:
            next_question(update.effective_user.id, quiz_questions)
            update.message.reply_text(f'Вопрос:\n{get_redis_var(update.effective_user.id, "query")}',
                                      reply_markup=helpme_markup)
            return CHECK_ANSWER
        except StopIteration as exc:
            end_game(update, context)
            return END_GAME
    else:
        update.message.reply_text('Неправильный ответ... Попробуешь ещё раз ответить?', reply_markup=yes_no_markup)
        return REPEAT_QUESTION


def repeat_question(update, context):
    if update.message.text == 'Да':
        update.message.reply_text(f'Вопрос:\n{get_redis_var(update.effective_user.id, "query")}',
                                  reply_markup=helpme_markup)

        return CHECK_ANSWER
    elif update.message.text == 'Нет':
        update.message.reply_text('Ну, что ж... Может, сыграем в новую игру?', reply_markup=yes_no_markup)
        return REPEAT_GAME


def repeat_game(update, context):
    if update.message.text == 'Да':
        start_game(update, context)
        return CHECK_ANSWER
    elif update.message.text == 'Нет':
        update.message.reply_text('Ну, что ж... Заходи как-нибудь, поиграем...')
        return ConversationHandler.END


def end_game(update, context):
    update.message.reply_text(
        'Больше вопросов нет.\n'
        f'Вы правильно ответили на {context.bot_data["good_answers"]} '
        f'вопросов из {context.bot_data["questions_count"]}\n'
        'Хотите сыграть ещё раз?', reply_markup=yes_no_markup)
    return REPEAT_GAME


def done(update, _):
    update.message.reply_text('Ок, до свидания!')
    return ConversationHandler.END


def error(update, update_error):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, update_error)


def main():
    global redis

    env = Env()
    env.read_env()

    redis_link = env('REDIS_LINK')
    redis_port = env('REDIS_PORT', 6379)
    redis_db = env('REDIS_DB', 0)
    redis = Redis(host=redis_link, port=redis_port, db=redis_db)

    tg_token = env('TG_TOKEN')
    updater = Updater(tg_token)
    dp = updater.dispatcher

    main_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            CHOOSING: [MessageHandler(Filters.text & ~Filters.command, start_game)],
            CHECK_ANSWER: [MessageHandler(Filters.text & ~Filters.command, check_answer)],
            REPEAT_QUESTION: [MessageHandler(Filters.text & ~Filters.command, repeat_question)],
            END_GAME: [MessageHandler(Filters.text & ~Filters.command, end_game)],
            REPEAT_GAME: [MessageHandler(Filters.text & ~Filters.command, repeat_game)],
        },

        fallbacks=[MessageHandler(Filters.text & ~Filters.command, done)]
    )
    dp.add_handler(main_conv_handler)
    dp.add_error_handler(error)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
