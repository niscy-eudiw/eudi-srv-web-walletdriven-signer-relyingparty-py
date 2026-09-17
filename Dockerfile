FROM python:3.9.22-slim-bullseye

WORKDIR /app
COPY app .
COPY requirements.txt .
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
CMD ["flask", "--app", ".", "run", "--host=0.0.0.0"]