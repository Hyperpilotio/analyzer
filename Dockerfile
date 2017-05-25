FROM python:alpine

RUN pip install django

COPY ./analyzer analyzer 

EXPOSE 7781

WORKDIR ./analyzer

CMD python manage.py migrate 

CMD python manage.py runserver 0.0.0.0:7781
