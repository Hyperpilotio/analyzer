FROM python:2.7.13-onbuild

COPY ./requirements.txt requirements.txt
COPY ./analyzer analyzer 

WORKDIR ./analyzer

EXPOSE 7781
