FROM python:2.7.13-onbuild

COPY ./requirements.txt requirements.txt
COPY ./web-service web-service 

WORKDIR ./web-service

EXPOSE 7781
