FROM jjorissen/rust-python:3.7
RUN apt-get -y update \
 && apt-get install -y tree \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip \
 && pip install poetry

ENV APP_HOME /app
WORKDIR $APP_HOME

# Install dependencies from poetry
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
 && poetry install

# Build and install materials dependency
COPY . .
RUN cd /app/materials \
 && python setup.py install \
 && rm -rf build dist *.egg-info target \
 && cd /app

ENV PYTHONBUFFERED=1
CMD ["python"]
