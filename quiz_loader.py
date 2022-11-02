SEARCH, QUERY, ANSWER, COMMENT = range(4)


# def process_line(line):
#     processed_line = ''
#     if line.strip():
#         processed_line += line.replace('\n', ' ')
#     else:
#         quiz['query'] = processed_line.strip()
#         mode = SEARCH


def load_quiz(file):
    with open(file, mode='r', encoding='koi8_r') as raw_quizzes:
        lines = raw_quizzes.readlines()

    quizzes = []
    answer = query = comment = ''
    mode = SEARCH
    for line in lines:
        if mode == SEARCH:
            if 'Вопрос ' in line:
                mode = QUERY
                quiz = {}
                answer = query = comment = ''
            if 'Ответ:' in line:
                mode = ANSWER
            if 'Комментарий:' in line:
                mode = COMMENT
        else:
            if mode == QUERY:
                if line.strip():
                    query += line
                else:
                    quiz['query'] = query.strip()
                    mode = SEARCH

            if mode == ANSWER:
                if line.strip():
                    answer += line
                else:
                    quiz['answer'] = answer.strip()
                    mode = SEARCH
                    quizzes.append(quiz)

            # if mode == COMMENT:
            #     if line.strip():
            #         comment += line  # .replace('\n', ' ')
            #     else:
            #         quiz['comment'] = comment.replace('\n', '')
            #         mode = SEARCH
    return quizzes[:3]
