FROM ruimashita/scikit-learn

RUN apt-get update
RUN apt-get -y install software-properties-common
RUN add-apt-repository -y ppa:fkrull/deadsnakes-python2.7
RUN apt-get -y install python2.7

COPY ./requirement.txt requirement.txt

RUN pip install -r requirement.txt

COPY ./analyzer analyzer 

EXPOSE 7781

WORKDIR ./analyzer

CMD python manage.py migrate 

CMD python manage.py runserver 0.0.0.0:7781
