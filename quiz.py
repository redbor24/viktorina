from pathlib import Path
from random import choice

from constants import redis_unanswered_question_id, redis_var_template

SEARCH, QUERY, ANSWER, COMMENT = range(4)


def load_questions(file):
    with open(file, mode='r', encoding='koi8_r') as raw_quiz:
        quiz_lines = raw_quiz.readlines()

    file_questions = []
    answer = query = comment = ''
    mode = SEARCH
    question = {}
    for quiz_line in quiz_lines:
        if mode == SEARCH:
            if 'Вопрос ' in quiz_line:
                mode = QUERY
                answer = query = comment = ''
                if question:
                    file_questions.append(question)
                question = {}
            if 'Ответ:' in quiz_line:
                mode = ANSWER
            if 'Комментарий:' in quiz_line:
                mode = COMMENT
        else:
            if mode == QUERY:
                if quiz_line.strip():
                    query += quiz_line
                else:
                    question['query'] = query.strip()
                    mode = SEARCH

            if mode == ANSWER:
                if quiz_line.strip():
                    answer += quiz_line
                else:
                    question['answer'] = answer.strip()
                    mode = SEARCH

            if mode == COMMENT:
                if quiz_line.strip():
                    comment += quiz_line
                else:
                    question['comment'] = comment.strip()
                    mode = SEARCH
    return file_questions


def get_next_question(user_prefix, user_id, redis, quiz):
    unanswered_question_id = redis.get(redis_var_template.format(user_prefix, user_id, redis_unanswered_question_id))
    question_id, question = quiz.get_question(unanswered_question_id)
    if not unanswered_question_id:
        redis.set(redis_var_template.format(user_prefix, user_id, redis_unanswered_question_id), question_id)

    return question


class QuizQuestions:
    def __init__(self, catalog, mask, _slice=None):
        self.questions = []
        self.catalog = catalog
        self.mask = mask
        self._file_path = str(Path(catalog) / mask)
        self._slice = _slice

    def get_question(self, question_id):
        if question_id:
            return question_id, self.questions[int(question_id)]
        else:
            random_question = choice(self.questions)
            return self.questions.index(random_question), random_question

    def load_quiz(self):
        self.questions = []
        quiz_files = Path().glob(self._file_path)

        for quiz_file in quiz_files:
            quiz_subset = load_questions(quiz_file)
            self.questions += quiz_subset

        if self._slice:
            self.questions = self.questions[:self._slice]
