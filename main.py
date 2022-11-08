import logging

from environs import Env
from redis import Redis
from telegram import KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (CommandHandler, ConversationHandler, Filters,
                          MessageHandler, RegexHandler, Updater)

import config
from quiz_loader import load_quiz

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

CHOOSING, NEXT_QUESTION, REPEAT_QUESTION, CHECK_ANSWER, END_GAME, REPEAT_GAME, UNKNOWN = range(7)

yes_no_keyboard = [[config.YES, config.NO]]
yes_no_markup = ReplyKeyboardMarkup(yes_no_keyboard, resize_keyboard=True, one_time_keyboard=True)

helpme_markup = ReplyKeyboardMarkup([[config.HELPME]], resize_keyboard=True, one_time_keyboard=True)

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
        config.START_GAME.format(update.effective_user.first_name),
        reply_markup=yes_no_markup)
    return CHOOSING


def next_question(user_id, questions):
    query = next(questions)
    set_redis_var(user_id, 'query', query['query'])
    set_redis_var(user_id, 'answer', query['answer'])


def start_game(update, context):
    global quiz_questions

    if update.message.text == config.YES:
        update.message.reply_text(config.GOGOGO)
        questions_count, quiz_questions = get_quiz_questions()
        context.bot_data['questions_count'] = questions_count
        context.bot_data['good_answers'] = 0

        next_question(update.effective_user.id, quiz_questions)
        update.message.reply_text(config.QUESTION.format(get_redis_var(update.effective_user.id, 'query')),
                                  reply_markup=helpme_markup)

        return CHECK_ANSWER

    elif update.message.text == config.NO:
        update.message.reply_text(config.LET_ANOTHER_TIME)
        return ConversationHandler.END

    else:
        return UNKNOWN


def check_answer(update, context):
    global quiz_questions

    if update.message.text == config.HELPME:
        update.message.reply_text(config.RIGHT_ANSWER.format(get_redis_var(update.effective_user.id, 'answer')))
        try:
            next_question(update.effective_user.id, quiz_questions)
            update.message.reply_text(config.QUESTION.format(get_redis_var(update.effective_user.id, 'query')),
                                      reply_markup=helpme_markup)
            return CHECK_ANSWER
        except StopIteration as exc:
            end_game(update, context)
            return END_GAME

    if update.message.text.lower() in get_redis_var(update.effective_user.id, 'answer').lower():
        update.message.reply_text(config.PRAISE)
        context.bot_data['good_answers'] += 1

        try:
            next_question(update.effective_user.id, quiz_questions)
            update.message.reply_text(config.QUESTION.format(get_redis_var(update.effective_user.id, 'query')),
                                      reply_markup=helpme_markup)
            return CHECK_ANSWER
        except StopIteration as exc:
            end_game(update, context)
            return END_GAME
    else:
        update.message.reply_text(config.WRONG_ANSWER, reply_markup=yes_no_markup)
        return REPEAT_QUESTION


def repeat_question(update, _):
    if update.message.text == config.YES:
        update.message.reply_text(config.QUESTION.format(get_redis_var(update.effective_user.id, 'query')),
                                  reply_markup=helpme_markup)
        return CHECK_ANSWER

    elif update.message.text == config.NO:
        update.message.reply_text(config.LET_NEWGAME, reply_markup=yes_no_markup)
        return REPEAT_GAME


def repeat_game(update, context):
    if update.message.text == config.YES:
        start_game(update, context)
        return CHECK_ANSWER
    elif update.message.text == config.NO:
        update.message.reply_text(config.LET_ANOTHER_TIME)
        return ConversationHandler.END


def end_game(update, context):
    update.message.reply_text(
        config.END_GAME.format(context.bot_data['good_answers'], context.bot_data['questions_count']),
        reply_markup=yes_no_markup)
    return REPEAT_GAME


def done(update, _):
    update.message.reply_text(config.BYE)
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
