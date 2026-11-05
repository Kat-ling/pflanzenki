FROM python:3.14-slim

ENV APP_ENV=production PYTHONUNBUFFERED=1
WORKDIR /srv/app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY data ./data
COPY static ./static

RUN useradd --create-home app
USER app
EXPOSE 8000
CMD ["python", "-m", "app"]
