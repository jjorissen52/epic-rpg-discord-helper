FROM rust:slim-buster

RUN apt-get -y update  \
 && apt-get install -y build-essential zlib1g-dev libncurses5-dev \
      libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev libbz2-dev \
      libsqlite3-dev curl git \
 && rm -rf /var/lib/apt/lists/*

RUN curl -so Python-3.7.3.tar.xz https://www.python.org/ftp/python/3.7.3/Python-3.7.3.tar.xz \
 && tar -xf Python-3.7.3.tar.xz \
 && cd Python-3.7.3 \
 && ./configure \
 && make -j 6 \
 && make altinstall \
 && cd ../ \
 && rm Python-3.7.3.tar.xz \
 && rm -rf Python-3.7.3 \
 && ln -s /usr/local/bin/python3.7 /usr/local/bin/python \
 && ln -s /usr/local/bin/pip3.7 /usr/local/bin/pip

RUN rustup default nightly
RUN pip install --upgrade pip --no-cache-dir \
  && pip install setuptools-rust wheel --no-cache-dir

CMD ["/bin/bash"]
