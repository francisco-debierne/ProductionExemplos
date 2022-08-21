FROM python:latest
WORKDIR /app
ADD . /app

RUN pip install -r requirements.txt

EXPOSE 8090

CMD [ "python","main.py","&" ]
