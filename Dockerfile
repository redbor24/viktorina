FROM python:3.10-slim

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

WORKDIR /usr/src/app
COPY requirements.txt /usr/src/app/
RUN pip install --requirement /usr/src/app/requirements.txt
COPY . /usr/src/app/

CMD ["/bin/sh", "-c", "python tgbot.py"]
CMD ["/bin/sh", "-c", "python VKbot.py"]
