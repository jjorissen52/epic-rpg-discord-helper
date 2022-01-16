FROM jjorissen/rust-python:3.7
RUN apt-get -y update \
 && apt-get install -y tree \
 && rm -rf /var/lib/apt/lists/*

ENV APP_HOME /app
WORKDIR $APP_HOME

# Install dependencies
COPY pyproject.toml poetry.lock ./
RUN pip install --upgrade pip \
 && pip install poetry \
 && poetry config virtualenvs.create false \
 && poetry install \
 && pip cache purge

# Build and install materials dependency
COPY materials materials
RUN cd /app/materials \
 && python setup.py install \
 && rm -rf build dist *.egg-info target \
 && cd /app

COPY . .

ENV PYTHONBUFFERED=1
CMD ["python"]
