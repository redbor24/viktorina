from environs import Env
from redis import Redis


def set_redis_var(redis, user_prefix, user_id, var_name, var_value):
    if isinstance(var_value, list):
        redis.set(f'{user_prefix}_{str(user_id)}:{var_name}', ','.join(str(x) for x in var_value))
    else:
        redis.set(f'{user_prefix}_{str(user_id)}:{var_name}', var_value)


def get_redis_var(redis, user_prefix, user_id, var_name, var_type=None):
    try:
        redis_value = redis.get(f'{user_prefix}_{str(user_id)}:{var_name}').decode('utf-8')

        if var_type == 'list':
            if redis_value:
                return [int(element) for element in redis_value.split(',')]
            else:
                return []
        elif var_type == 'int':
            if redis_value:
                return int(redis_value)
            else:
                return 0
        else:
            return redis_value
    except AttributeError:
        if var_type == 'list':
            return []
        elif var_type == 'int':
            return None
        else:
            return ''


def get_next_question(user_prefix, user_id, redis, quiz):
    unanswered_question_id = get_redis_var(redis, user_prefix, user_id, 'question_id')

    if unanswered_question_id:
        question = quiz.get_question(unanswered_question_id)
    else:
        answered_questions = get_redis_var(redis, user_prefix, user_id, 'answered', 'list')
        # logger.info(f'answered_questions: {answered_questions}')
        if len(answered_questions) == len(quiz.questions):
            answered_questions = []
            set_redis_var(redis, user_prefix, user_id, 'answered', answered_questions)
        question_id, question = quiz.get_random_question(answered_questions)
        set_redis_var(redis, user_prefix, user_id, 'question_id', question_id)

    return question


def save_answered_question_ids(user_prefix, user_id, redis, question_id, logger=None):
    answered_questions = get_redis_var(redis, user_prefix, user_id, 'answered', 'list')
    answered_questions.append(question_id)
    set_redis_var(redis, user_prefix, user_id, 'answered', answered_questions)
    logger.info(answered_questions)
