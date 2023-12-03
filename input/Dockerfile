# `bash ci.sh` to build
# it's recommended to build from root project
ARG DREG # docker registry
FROM ${DREG}ariqbasyar/fogbus2-fogverse:base-user

WORKDIR /workplace/fogverse-app
COPY fogverse fogverse
COPY input/producer.py .

ENTRYPOINT ["python", "-u"]
