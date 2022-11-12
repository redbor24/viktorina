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

    redis.flushdb()
    exit()

    user_id = 225300898

    prefix = 'vk'
    var_type = 'int'
    print(get_redis_var(redis, prefix, user_id, 'state'))
    redis.delete(f'vk_{str(user_id)}:state')
    exit()

    prefix = 'tst'
    var_name = 'var_int'
    var_type = 'int'
    set_redis_var(redis, prefix, user_id, var_name, 0)
    print(f'{var_name}({var_type}): {{0}}'.format(get_redis_var(redis, prefix, user_id, var_name, var_type)))
    redis.delete(f'{prefix}_{str(user_id)}:{var_name}')
    set_redis_var(redis, prefix, user_id, var_name, 123)
    print(f'{var_name}({var_type}): {{0}}'.format(get_redis_var(redis, prefix, user_id, var_name, var_type)))
    redis.delete(f'{prefix}_{str(user_id)}:{var_name}')

    var_name = 'var_list'
    var_type = 'list'
    set_redis_var(redis, prefix, user_id, var_name, [])
    print(f'{var_name}({var_type}): {{0}}'.format(get_redis_var(redis, prefix, user_id, var_name, var_type)))
    redis.delete(f'{prefix}_{str(user_id)}:{var_name}')
    set_redis_var(redis, prefix, user_id, var_name, [1, 2, 3])
    print(f'{var_name}({var_type}): {{0}}'.format(get_redis_var(redis, prefix, user_id, var_name, var_type)))
    redis.delete(f'{prefix}_{str(user_id)}:{var_name}')

    var_name = 'var'
    set_redis_var(redis, prefix, user_id, var_name, '')
    print(f'{var_name}({var_type}): {{0}}'.format(get_redis_var(redis, prefix, user_id, var_name)))
    redis.delete(f'{prefix}_{str(user_id)}:{var_name}')
    set_redis_var(redis, prefix, user_id, var_name, 'ss123')
    print(f'{var_name}({var_type}): {{0}}'.format(get_redis_var(redis, prefix, user_id, var_name)))
    redis.delete(f'{prefix}_{str(user_id)}:{var_name}')
