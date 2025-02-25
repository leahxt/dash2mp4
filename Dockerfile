FROM python:3.13

LABEL org.opencontainers.image.source=https://github.com/leahxt/dash2mp4
LABEL org.opencontainers.image.licenses=MIT

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt
RUN apt-get update && apt-get install -y ffmpeg

COPY ./hypercorn.toml /app/hypercorn.toml
COPY ./dash2mp4.py /app/dash2mp4.py

CMD ["hypercorn", "-c", "hypercorn.toml", "dash2mp4:app"]