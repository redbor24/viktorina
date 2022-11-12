import logging

import vk_api as vk
from environs import Env
from redis import Redis
from viktorina_redis import (get_next_question, get_redis_var,
                             save_answered_question_ids, set_redis_var)
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkEventType, VkLongPoll
from vk_api.utils import get_random_id

import config
from config import (CHOOSING, NEXT_QUESTION, REPEAT_QUESTION, CHECK_ANSWER, END_GAME, REPEAT_GAME, UNKNOWN)
from quiz import QuizQuestions

USER_PREFIX = 'vk'

logging.basicConfig(format=config.log_format, level=logging.INFO)
logger = logging.getLogger(__name__)


def send_message(event, api, message='', keyboard=None):
    api.messages.send(
        user_id=event.user_id,
        keyboard=keyboard,
        message=(message if message else event.text),
        random_id=get_random_id()
    )
    logger.info(f'{event.user_id} - {message}')


def get_yesno_keyboard():
    keyboard = VkKeyboard(one_time=True)

    keyboard.add_button('Да', color=VkKeyboardColor.POSITIVE)
    keyboard.add_button('Нет', color=VkKeyboardColor.NEGATIVE)
    return keyboard.get_keyboard()


def get_help_keyboard():
    keyboard = VkKeyboard(one_time=True)

    keyboard.add_button(config.HELPME, color=VkKeyboardColor.PRIMARY)
    return keyboard.get_keyboard()


def get_new_game_keyboard():
    keyboard = VkKeyboard(one_time=True)

    keyboard.add_button(config.NEW_GAME, color=VkKeyboardColor.PRIMARY)
    return keyboard.get_keyboard()


def start_game(event, api, redis, quiz):
    if event.text == config.YES:
        send_message(event, api, config.GOGOGO)
        send_message(event, api, config.CHOOSING_RANDOM_QUIZ)

        question = get_next_question(USER_PREFIX, event.user_id, redis, quiz)
        send_message(event, api, config.QUESTION.format(question['query']), get_help_keyboard())
        set_redis_var(redis, USER_PREFIX, user_id, 'state', CHECK_ANSWER)

    elif event.text == config.NO:
        send_message(event, api, config.LET_ANOTHER_TIME)
        set_redis_var(redis, USER_PREFIX, user_id, 'state', END_GAME)


if __name__ == "__main__":
    env = Env()
    env.read_env()

    redis_link = env('REDIS_LINK')
    redis_port = env('REDIS_PORT', 6379)
    redis_db = env('REDIS_DB', 0)
    rds = Redis(host=redis_link, port=redis_port, db=redis_db)

    vk_token = env('VK_TOKEN')
    vk_session = vk.VkApi(token=vk_token)
    vk_api = vk_session.get_api()

    # quiz = QuizQuestions('quiz-questions', '*.txt', _slice=3)
    quiz = QuizQuestions('quiz-questions', '*.txt')
    quiz.load_quiz()

    states = {}

    long_poll = VkLongPoll(vk_session)
    for vk_event in long_poll.listen():
        if vk_event.type == VkEventType.MESSAGE_NEW and vk_event.to_me:
            user_id = vk_event.user_id
            logger.info(f'user_id: {user_id}')
            user_state = get_redis_var(rds, USER_PREFIX, user_id, 'state')
            if not user_state:
                user_state = END_GAME
            else:
                user_state = int(user_state)

            if user_state == END_GAME:
                if vk_event.text.lower() == config.CMD_NEW_GAME_VK:
                    send_message(vk_event, vk_api, config.START_GAME.format('чувак!'), get_yesno_keyboard())
                    set_redis_var(rds, USER_PREFIX, user_id, 'state', CHOOSING)
                    continue

            elif user_state == CHOOSING:
                if vk_event.text == config.YES:
                    send_message(vk_event, vk_api, config.GOGOGO)
                    send_message(vk_event, vk_api, config.CHOOSING_RANDOM_QUIZ)

                    question = get_next_question(USER_PREFIX, user_id, rds, quiz)
                    send_message(vk_event, vk_api, config.QUESTION.format(question['query']), get_help_keyboard())
                    set_redis_var(rds, USER_PREFIX, user_id, 'state', CHECK_ANSWER)
                    continue

                elif vk_event.text == config.NO:
                    send_message(vk_event, vk_api, config.LET_ANOTHER_TIME)
                    set_redis_var(rds, USER_PREFIX, user_id, 'state', END_GAME)
                    continue

            elif user_state == CHECK_ANSWER:
                if vk_event.text == config.HELPME:
                    question_id = get_redis_var(rds, USER_PREFIX, user_id, 'question_id')
                    question = quiz.get_question(question_id)
                    send_message(vk_event, vk_api, config.RIGHT_ANSWER.format(question['answer']))

                    set_redis_var(rds, USER_PREFIX, user_id, 'question_id', '')
                    save_answered_question_ids(USER_PREFIX, user_id, rds, question_id, logger)

                    send_message(vk_event, vk_api, config.ASK_NEXT_QUESTION, get_yesno_keyboard())
                    set_redis_var(rds, USER_PREFIX, user_id, 'state', NEXT_QUESTION)
                    continue

                question_id = get_redis_var(rds, USER_PREFIX, user_id, 'question_id')
                question = quiz.get_question(question_id)

                if vk_event.text.lower() in question['answer'].lower():
                    send_message(vk_event, vk_api, config.PRAISE)
                    send_message(vk_event, vk_api, config.ANSWER.format(question['answer'].strip()))

                    set_redis_var(rds, USER_PREFIX, user_id, 'question_id', '')
                    save_answered_question_ids(USER_PREFIX, user_id, rds, question_id, logger)

                    send_message(vk_event, vk_api, config.ASK_NEXT_QUESTION, get_yesno_keyboard())
                    set_redis_var(rds, USER_PREFIX, user_id, 'state', NEXT_QUESTION)
                    continue

                else:
                    send_message(vk_event, vk_api, config.WRONG_ANSWER, get_yesno_keyboard())
                    set_redis_var(rds, USER_PREFIX, user_id, 'state', REPEAT_QUESTION)
                    continue

            elif user_state == REPEAT_QUESTION:
                if vk_event.text == config.YES:
                    question = get_next_question(USER_PREFIX, user_id, rds, quiz)
                    send_message(vk_event, vk_api, config.QUESTION.format(question['query']), get_help_keyboard())
                    set_redis_var(rds, USER_PREFIX, user_id, 'state', CHECK_ANSWER)
                    continue

                elif vk_event.text == config.NO:
                    send_message(vk_event, vk_api, config.LET_NEW_GAME, get_yesno_keyboard())
                    set_redis_var(rds, USER_PREFIX, user_id, 'state', REPEAT_GAME)
                    continue

            elif user_state == REPEAT_GAME:
                if vk_event.text == config.YES:
                    start_game(vk_event, vk_api, rds, quiz)
                    set_redis_var(rds, USER_PREFIX, user_id, 'state', CHECK_ANSWER)
                    continue

                elif vk_event.text == config.NO:
                    send_message(vk_event, vk_api, config.LET_ANOTHER_TIME)
                    set_redis_var(rds, USER_PREFIX, user_id, 'state', END_GAME)
                    continue

            elif user_state == NEXT_QUESTION:
                if vk_event.text == config.YES:
                    question = get_next_question(USER_PREFIX, user_id, rds, quiz)
                    send_message(vk_event, vk_api, config.QUESTION.format(question['query']), get_help_keyboard())
                    set_redis_var(rds, USER_PREFIX, user_id, 'state', CHECK_ANSWER)
                    continue

                elif vk_event.text == config.NO:
                    send_message(vk_event, vk_api, config.LET_NEW_GAME, get_yesno_keyboard())
                    set_redis_var(rds, USER_PREFIX, user_id, 'state', REPEAT_GAME)
                    continue