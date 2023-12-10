FROM python:3.8
WORKDIR /app

COPY . /app

RUN apt-get update && apt-get install -y gcc

RUN pip install -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--env-file", "./env/.env"]
