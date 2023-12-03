FROM ariqbasyar/opencv:v4.8.1.78-py3.9.18

RUN --mount=type=cache,target=/var/cache/apt_update apt update \
    && apt install -y --no-install-recommends \
    libssl-dev \
    zlib1g-dev \
    gcc \
    g++ \
    make \
    git \
    vim \
    curl

RUN pip install pandas aiokafka
