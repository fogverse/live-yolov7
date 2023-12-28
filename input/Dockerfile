# `bash ci.sh` to build
# it's recommended to build from root project
ARG DREG # docker registry
FROM ${DREG}ariqbasyar/fogbus2-fogverse:base-user

RUN pip install confluent-kafka pyyaml

# FogBus2
WORKDIR /workplace/fogbus2-app
COPY FogBus2/containers/user/sources/requirementsDockerImage.txt .
RUN pip install -r requirementsDockerImage.txt

# Hostname
RUN echo "User" > /etc/hostname

COPY FogBus2/containers/user/sources/ .

# FogVerse
WORKDIR /workplace/fogverse-app
COPY live-yolov7/fogverse fogverse
COPY live-yolov7/input/producer.py .

ENTRYPOINT ["python", "-u"]
