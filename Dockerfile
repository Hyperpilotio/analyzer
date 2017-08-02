FROM python:3.6

# Install pipenv
ADD https://raw.github.com/kennethreitz/pipenv/master/get-pipenv.py /get-pipenv.py
RUN python /get-pipenv.py && rm /get-pipenv.py

# Add source code
COPY . /app
WORKDIR /app
VOLUME /app/config.ini

# Install dependencies
RUN make init

# Run app
EXPOSE 5000
CMD make run-server
