from environs import Env
from redis import Redis


def set_redis_var(redis, user_prefix, user_id, var_name, var_value):
    if isinstance(var_value, list):
        redis.set(f'{user_prefix}_{str(user_id)}:{var_name}', ','.join(str(x) for x in var_value))
    else:
        redis.set(f'{user_prefix}_{str(user_id)}:{var_name}', var_value)


def get_redis_var(redis, user_prefix, user_id, var_name, var_type=None):
    if var_type == 'list':
        try:
            redis_value = redis.get(f'{user_prefix}_{str(user_id)}:{var_name}').decode('utf-8')
            if redis_value:
                return [int(element) for element in redis_value.split(',')]
            else:
                return []
        except AttributeError:
            return []
    else:
        try:
            return redis.get(f'{user_prefix}_{str(user_id)}:{var_name}').decode('utf-8')
        except AttributeError:
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


if __name__ == '__main__':
    env = Env()
    env.read_env()

    redis_link = env('REDIS_LINK')
    redis_port = env('REDIS_PORT', 6379)
    redis_db = env('REDIS_DB', 0)
    redis = Redis(host=redis_link, port=redis_port, db=redis_db)

    user_id = 901108747
    # set_redis_var(redis, user_id, 'question_id', 111)
    # redis.delete(f'{str(user_id)}:{"question_id"}')
    # print(get_redis_var(redis, user_id, 'question_id'))

    # redis.flushdb()

    S1, S2 = range(2)

    # set_redis_var(redis, 'tg', user_id, 'state', S2)
    redis.delete(f'tg_{str(user_id)}:state')
    print(get_redis_var(redis, 'tg', user_id, 'state'))
