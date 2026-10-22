FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY garmin_app.py .

ENV HOME=/home/app
RUN useradd -m -d /home/app app && mkdir /data && chown app /data
USER app

ENTRYPOINT ["python", "garmin_app.py", "--out", "/data"]
