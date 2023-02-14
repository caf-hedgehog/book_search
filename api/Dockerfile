FROM python:3
ENV PYTHONUNBUFFERED 1

RUN pip install --upgrade pip && pip install fastapi uvicorn
RUN pip install pandas && pip install beautifulsoup4 && pip install requests && pip install elasticsearch && pip install aiohttp

RUN mkdir /app
COPY ./ /app
WORKDIR /app

ENTRYPOINT ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002"]

EXPOSE 8002
