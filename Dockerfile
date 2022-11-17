FROM python:3.10
# set work directory
WORKDIR /usr/src/app/
# copy project
COPY . /usr/src/app/
# install dependencies
RUN pip install -r requirements.txt
# run app
CMD ["/bin/sh", "-c", "python tgbot.py & python VKbot.py"]
