FROM python:3.10
ENV POETRY_VIRTUALENVS_CREATE=false
COPY pyproject.toml .env /
RUN pip install poetry
RUN poetry install

RUN apt-get update
RUN apt -f install -y
RUN apt-get install -y wget
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN apt-get install ./google-chrome-stable_current_amd64.deb -y

# ENTRYPOINT ["python", "scraper.py"]