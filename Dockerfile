FROM python:2.7.13-onbuild

COPY ./requirements.txt requirements.txt

COPY ./analyzer analyzer 

WORKDIR ./analyzer

EXPOSE 7781

CMD python manage.py migrate 

CMD python manage.py runserver 0.0.0.0:7781
