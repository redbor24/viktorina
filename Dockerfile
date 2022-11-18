FROM python:3.10
WORKDIR /usr/src/app/
COPY . /usr/src/app/
RUN pip install -r requirements.txt
CMD ["/bin/sh", "-c", "python tgbot.py & python VKbot.py"]
