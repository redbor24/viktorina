import logging

from environs import Env
from redis import Redis
from telegram import ReplyKeyboardMarkup
from telegram.ext import (CommandHandler, ConversationHandler, Filters,
                          MessageHandler, Updater)

import constants
from constants import (CHECK_ANSWER, CHOOSING, END_GAME, NEXT_QUESTION,
                       REPEAT_GAME, REPEAT_QUESTION, UNKNOWN)
from quiz import QuizQuestions
from viktorina_redis import (get_next_question, get_redis_var,
                             save_answered_question_ids, set_redis_var)

USER_PREFIX = 'tg'

yes_no_markup = ReplyKeyboardMarkup([[constants.YES, constants.NO]], resize_keyboard=True, one_time_keyboard=True)
helpme_markup = ReplyKeyboardMarkup([[constants.HELPME]], resize_keyboard=True, one_time_keyboard=True)


def start(update, _):
    update.message.reply_text(
        constants.START_GAME.format(update.effective_user.first_name),
        reply_markup=yes_no_markup)
    return CHOOSING


def start_game(update, _):
    if update.message.text == constants.YES:
        update.message.reply_text(constants.GOGOGO)
        update.message.reply_text(constants.CHOOSING_RANDOM_QUIZ)

        question = get_next_question(USER_PREFIX, update.effective_user.id, rds, quiz)
        update.message.reply_text(constants.QUESTION.format(question['query']), reply_markup=helpme_markup)
        return CHECK_ANSWER

    elif update.message.text == constants.NO:
        update.message.reply_text(constants.LET_ANOTHER_TIME)
        return ConversationHandler.END

    else:
        return UNKNOWN


def check_answer(update, _):
    if update.message.text == constants.HELPME:
        question_id = get_redis_var(rds, USER_PREFIX, update.effective_user.id, 'question_id', 'int')
        question = quiz.get_question(question_id)
        update.message.reply_text(constants.RIGHT_ANSWER.format(question['answer']))
        set_redis_var(rds, USER_PREFIX, update.effective_user.id, 'question_id', '')
        save_answered_question_ids(USER_PREFIX, update.effective_user.id, rds, question_id)

        update.message.reply_text(constants.ASK_NEXT_QUESTION, reply_markup=yes_no_markup)

        return NEXT_QUESTION

    question_id = get_redis_var(rds, USER_PREFIX, update.effective_user.id, 'question_id', 'int')
    question = quiz.get_question(question_id)

    if update.message.text.lower() in question['answer'].lower():
        update.message.reply_text(constants.PRAISE)
        update.message.reply_text(constants.ANSWER.format(question['answer'].strip()))
        set_redis_var(rds, USER_PREFIX, update.effective_user.id, 'question_id', '')
        save_answered_question_ids(USER_PREFIX, update.effective_user.id, rds, question_id)

        update.message.reply_text(constants.ASK_NEXT_QUESTION, reply_markup=yes_no_markup)

        return NEXT_QUESTION

    else:
        update.message.reply_text(constants.WRONG_ANSWER, reply_markup=yes_no_markup)
        return REPEAT_QUESTION


def next_question(update, _):
    if update.message.text == constants.YES:
        question = get_next_question(USER_PREFIX, update.effective_user.id, rds, quiz)
        update.message.reply_text(constants.QUESTION.format(question['query']), reply_markup=helpme_markup)
        return CHECK_ANSWER

    elif update.message.text == constants.NO:
        update.message.reply_text(constants.LET_NEW_GAME, reply_markup=yes_no_markup)
        return REPEAT_GAME


def repeat_question(update, _):
    if update.message.text == constants.YES:
        question = get_next_question(USER_PREFIX, update.effective_user.id, rds, quiz)
        update.message.reply_text(constants.QUESTION.format(question['query']), reply_markup=helpme_markup)
        return CHECK_ANSWER

    elif update.message.text == constants.NO:
        update.message.reply_text(constants.LET_NEW_GAME, reply_markup=yes_no_markup)
        return REPEAT_GAME


def repeat_game(update, context):
    if update.message.text == constants.YES:
        start_game(update, context)
        return CHECK_ANSWER
    elif update.message.text == constants.NO:
        update.message.reply_text(constants.LET_ANOTHER_TIME)
        return ConversationHandler.END


def end_game(update, _):
    update.message.reply_text(constants.STOP_GAME.format(0, 0), reply_markup=yes_no_markup)
    return REPEAT_GAME


def done(update, _):
    update.message.reply_text(constants.BYE)
    return ConversationHandler.END


def error(update, update_error):
    logger.warning('Update "%s" caused error "%s"', update, update_error)


if __name__ == '__main__':
    logging.basicConfig(format=constants.log_format, level=logging.INFO)
    logger = logging.getLogger('tgbot')

    env = Env()
    env.read_env()

    redis_host = env('REDIS_HOST')
    redis_port = env('REDIS_PORT')
    redis_password = env('REDIS_PASSWORD')
    rds = Redis(host=redis_host, port=redis_port, password=redis_password)

    quiz = QuizQuestions('quiz-questions', '*.txt')
    quiz.load_quiz()

    tg_token = env('TG_TOKEN')
    updater = Updater(tg_token)
    dp = updater.dispatcher

    main_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            CHOOSING: [MessageHandler(Filters.text & ~Filters.command, start_game)],
            CHECK_ANSWER: [MessageHandler(Filters.text & ~Filters.command, check_answer)],
            REPEAT_QUESTION: [MessageHandler(Filters.text & ~Filters.command, repeat_question)],
            NEXT_QUESTION: [MessageHandler(Filters.text & ~Filters.command, next_question)],
            END_GAME: [MessageHandler(Filters.text & ~Filters.command, end_game)],
            REPEAT_GAME: [MessageHandler(Filters.text & ~Filters.command, repeat_game)],
        },

        fallbacks=[MessageHandler(Filters.text & ~Filters.command, done)]
    )
    dp.add_handler(main_conv_handler)
    dp.add_handler(CommandHandler('start', start))
    dp.add_error_handler(error)
    updater.start_polling()
    updater.idle()
