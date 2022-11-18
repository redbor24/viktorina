heroku login -i
heroku container:login
heroku apps:create --region eu rdb-quiz-docker
heroku plugins:install heroku-config
heroku config:push -f .env -o
heroku container:push worker --app rdb-quiz-docker
heroku container:release worker --app rdb-quiz-docker
heroku ps:scale worker=1 --app=rdb-quiz-docker