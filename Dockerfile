FROM jjorissen/rust-python:3.7

ENV APP_HOME /app
WORKDIR $APP_HOME

# Install dependencies.
COPY pyproject.toml requirements.txt ./
RUN pip install -r requirements.txt
COPY . .
RUN cd /app/materials \
    && python setup.py test \
    && cd /app

ENV PYTHONBUFFERED=1
CMD ["python"]
