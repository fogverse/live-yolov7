ARG DREG # docker registry
FROM ${DREG}ariqbasyar/fogverse:inference-gpu

WORKDIR /app
COPY fog/jetson_nano/inference.py .
COPY fogverse/ fogverse/
CMD ["python3", "inference.py"]
