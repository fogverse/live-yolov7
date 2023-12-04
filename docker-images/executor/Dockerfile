FROM ariqbasyar/pytorch:v2.1.1-py3.9.18-yolov7

RUN --mount=type=cache,target=/var/cache/apt_update apt update \
    && apt install -y --no-install-recommends \
    libssl-dev \
    zlib1g-dev \
    curl \
    gcc \
    vim \
    g++

RUN pip install setuptools wheel pandas aiokafka
