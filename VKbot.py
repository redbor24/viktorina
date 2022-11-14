import logging

import vk_api as vk
from environs import Env
from redis import Redis
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkEventType, VkLongPoll
from vk_api.utils import get_random_id

import constants
from constants import (CHECK_ANSWER, CHOOSING, END_GAME, NEXT_QUESTION,
                       REPEAT_GAME, REPEAT_QUESTION, redis_conversation_state,
                       redis_unanswered_question_id, redis_var_template)
from quiz import QuizQuestions, get_next_question

USER_PREFIX = 'vk'


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

    keyboard.add_button(constants.HELPME, color=VkKeyboardColor.PRIMARY)
    return keyboard.get_keyboard()


def get_new_game_keyboard():
    keyboard = VkKeyboard(one_time=True)

    keyboard.add_button(constants.NEW_GAME, color=VkKeyboardColor.PRIMARY)
    return keyboard.get_keyboard()


def start_game(event, api, redis, quiz):
    if event.text == constants.YES:
        send_message(event, api, constants.GOGOGO)
        send_message(event, api, constants.CHOOSING_RANDOM_QUIZ)

        question = get_next_question(USER_PREFIX, event.user_id, redis, quiz)
        send_message(event, api, constants.QUESTION.format(question['query']), get_help_keyboard())
        redis.set(redis_var_template.format(USER_PREFIX, event.user_id, redis_conversation_state), CHECK_ANSWER)

    elif event.text == constants.NO:
        send_message(event, api, constants.LET_ANOTHER_TIME)
        redis.set(redis_var_template.format(USER_PREFIX, event.user_id, redis_conversation_state), END_GAME)


def next_question(event, api, redis, quiz):
    if event.text == constants.YES:
        question = get_next_question(USER_PREFIX, event.user_id, redis, quiz)
        send_message(event, api, constants.QUESTION.format(question['query']), get_help_keyboard())

        redis.set(redis_var_template.format(USER_PREFIX, event.user_id, redis_conversation_state), CHECK_ANSWER)

    elif vk_event.text == constants.NO:
        send_message(event, api, constants.LET_NEW_GAME, get_yesno_keyboard())

        redis.set(redis_var_template.format(USER_PREFIX, event.user_id, redis_conversation_state), REPEAT_GAME)


def repeat_question(event, api, redis, quiz):
    if event.text == constants.YES:
        question = get_next_question(USER_PREFIX, user_id, redis, quiz)
        send_message(event, api, constants.QUESTION.format(question['query']), get_help_keyboard())

        redis.set(redis_var_template.format(USER_PREFIX, event.user_id, redis_conversation_state), CHECK_ANSWER)

    elif event.text == constants.NO:
        send_message(event, api, constants.LET_NEW_GAME, get_yesno_keyboard())

        redis.set(redis_var_template.format(USER_PREFIX, event.user_id, redis_conversation_state), REPEAT_GAME)


def check_answer(event, api, redis, quiz):
    question = get_next_question(USER_PREFIX, event.user_id, redis, quiz)
    if event.text == constants.HELPME:
        send_message(event, api, constants.RIGHT_ANSWER.format(question['answer']))
        send_message(event, api, constants.ASK_NEXT_QUESTION, get_yesno_keyboard())

        redis.delete(redis_var_template.format(USER_PREFIX, event.user_id, redis_unanswered_question_id))

        redis.set(redis_var_template.format(USER_PREFIX, event.user_id, redis_conversation_state), NEXT_QUESTION)
        return

    if vk_event.text.lower() in question['answer'].lower():
        send_message(event, api, constants.PRAISE)
        send_message(event, api, constants.ANSWER.format(question['answer'].strip()))
        send_message(event, api, constants.ASK_NEXT_QUESTION, get_yesno_keyboard())

        redis.delete(redis_var_template.format(USER_PREFIX, event.user_id, redis_unanswered_question_id))

        redis.set(redis_var_template.format(USER_PREFIX, event.user_id, redis_conversation_state), NEXT_QUESTION)

    else:
        send_message(event, api, constants.WRONG_ANSWER, get_yesno_keyboard())

        redis.set(redis_var_template.format(USER_PREFIX, event.user_id, redis_conversation_state), REPEAT_QUESTION)


if __name__ == "__main__":
    logging.basicConfig(format=constants.log_format, level=logging.INFO)
    logger = logging.getLogger('vkbot')

    env = Env()
    env.read_env()

    redis_host = env('REDIS_HOST')
    redis_port = env('REDIS_PORT')
    redis_password = env('REDIS_PASSWORD')
    rds = Redis(host=redis_host, port=redis_port, password=redis_password)

    vk_token = env('VK_TOKEN')
    vk_session = vk.VkApi(token=vk_token)
    vk_api = vk_session.get_api()

    quiz = QuizQuestions('quiz-questions', '*.txt')
    quiz.load_quiz()

    long_poll = VkLongPoll(vk_session)
    for vk_event in long_poll.listen():
        if vk_event.type == VkEventType.MESSAGE_NEW and vk_event.to_me:
            user_id = vk_event.user_id
            logger.info(f'user_id: {user_id}')
            redis_user_state = rds.get(redis_var_template.format(USER_PREFIX, user_id, redis_conversation_state))
            if not redis_user_state:
                user_state = END_GAME
            else:
                user_state = int(redis_user_state)

            if vk_event.text.lower() == constants.CMD_NEW_GAME_VK:
                send_message(vk_event, vk_api, constants.START_GAME.format('чувак!'), get_yesno_keyboard())
                rds.set(redis_var_template.format(USER_PREFIX, user_id, redis_conversation_state), CHOOSING)
                continue

            elif user_state == CHOOSING:
                start_game(vk_event, vk_api, rds, quiz)
                continue

            elif user_state == CHECK_ANSWER:
                check_answer(vk_event, vk_api, rds, quiz)
                continue

            elif user_state == REPEAT_QUESTION:
                repeat_question(vk_event, vk_api, rds, quiz)
                continue

            elif user_state == REPEAT_GAME:
                start_game(vk_event, vk_api, rds, quiz)
                continue

            elif user_state == NEXT_QUESTION:
                next_question(vk_event, vk_api, rds, quiz)
