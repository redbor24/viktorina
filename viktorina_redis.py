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


if __name__ == '__main__':
    env = Env()
    env.read_env()

    redis_link = env('REDIS_LINK')
    redis_port = env('REDIS_PORT', 6379)
    redis_db = env('REDIS_DB', 0)
    redis = Redis(host=redis_link, port=redis_port, db=redis_db)

    user_id = 901108747
    # TGuser: 901108747, question_id
    # set_redis_var(redis, user_id, 'question_id', 111)
    # redis.delete(f'{str(user_id)}:{"question_id"}')
    # print(get_redis_var(redis, user_id, 'question_id'))

    redis.flushdb()

    # get_redis_var(redis, user_id, 'answered', 'list')
