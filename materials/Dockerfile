FROM rust:slim-buster
RUN apt-get -y update

RUN apt-get install -y build-essential zlib1g-dev libncurses5-dev \
        libgdbm-dev libnss3-dev libssl-dev libreadline-dev libffi-dev curl libbz2-dev
RUN curl -o Python-3.7.3.tar.xz https://www.python.org/ftp/python/3.7.3/Python-3.7.3.tar.xz
RUN tar -xf Python-3.7.3.tar.xz \
    && cd Python-3.7.3 \
    && ./configure \
    && make -j 6 \
    && make altinstall
RUN mv /usr/local/bin/python3.7 /usr/local/bin/python \
    && mv /usr/local/bin/pip3.7 /usr/local/bin/pip

RUN rustup default nightly
RUN python -m pip install setuptools-rust wheel

CMD ["/bin/bash"]