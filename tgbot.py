import logging

from environs import Env
from redis import Redis
from telegram import ReplyKeyboardMarkup
from telegram.ext import (CommandHandler, ConversationHandler, Filters,
                          MessageHandler, Updater)

import constants
from constants import (CHECK_ANSWER, CHOOSING, END_GAME, NEXT_QUESTION,
                       REPEAT_GAME, REPEAT_QUESTION,
                       redis_unanswered_question_id, redis_var_template)
from quiz import QuizQuestions, get_next_question

USER_PREFIX = 'tg'

yes_no_markup = ReplyKeyboardMarkup([[constants.YES, constants.NO]], resize_keyboard=True, one_time_keyboard=True)
helpme_markup = ReplyKeyboardMarkup([[constants.HELPME]], resize_keyboard=True, one_time_keyboard=True)

logger = logging.getLogger('tgbot')


def start_conversation(update, _):
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


def check_answer(update, _):
    question = get_next_question(USER_PREFIX, update.effective_user.id, rds, quiz)

    if update.message.text == constants.HELPME:
        update.message.reply_text(constants.RIGHT_ANSWER.format(question['answer']))
        update.message.reply_text(constants.ASK_NEXT_QUESTION, reply_markup=yes_no_markup)

        rds.delete(redis_var_template.format(USER_PREFIX, update.effective_user.id, redis_unanswered_question_id))

        return NEXT_QUESTION

    if update.message.text.lower() in question['answer'].lower():
        update.message.reply_text(constants.PRAISE)
        update.message.reply_text(constants.ANSWER.format(question['answer'].strip()))
        update.message.reply_text(constants.ASK_NEXT_QUESTION, reply_markup=yes_no_markup)

        rds.delete(redis_var_template.format(USER_PREFIX, update.effective_user.id, redis_unanswered_question_id))

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


def stop_conversation(update, _):
    update.message.reply_text(constants.BYE)
    return ConversationHandler.END


def handle_error(update, update_error):
    logger.warning('Update "%s" caused error "%s"', update, update_error)


if __name__ == '__main__':
    logging.basicConfig(format=constants.log_format, level=logging.INFO)

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
        entry_points=[CommandHandler('start', start_conversation)],

        states={
            CHOOSING: [MessageHandler(Filters.text & ~Filters.command, start_game)],
            CHECK_ANSWER: [MessageHandler(Filters.text & ~Filters.command, check_answer)],
            REPEAT_QUESTION: [MessageHandler(Filters.text & ~Filters.command, repeat_question)],
            NEXT_QUESTION: [MessageHandler(Filters.text & ~Filters.command, next_question)],
            END_GAME: [MessageHandler(Filters.text & ~Filters.command, end_game)],
            REPEAT_GAME: [MessageHandler(Filters.text & ~Filters.command, repeat_game)],
        },

        fallbacks=[MessageHandler(Filters.text & ~Filters.command, stop_conversation)]
    )
    dp.add_handler(main_conv_handler)
    dp.add_handler(CommandHandler('start', start_conversation))
    dp.add_error_handler(handle_error)
    updater.start_polling()
    updater.idle()
