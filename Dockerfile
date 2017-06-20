FROM python:3.6

# RUN apk add --update gcc gfortran
ADD https://raw.github.com/kennethreitz/pipenv/master/get-pipenv.py /get-pipenv.py
RUN python /get-pipenv.py
COPY . /app
WORKDIR /app

RUN pipenv install --system

ENV FLASK_APP api_service/app.py

EXPOSE 5000

CMD flask run -h 0.0.0.0 -p 5000
