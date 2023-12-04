ARG DREG # docker registry
FROM ${DREG}ariqbasyar/fogbus2-fogverse:base-CCTVInference

WORKDIR /workplace/fogverse-app
RUN git clone https://github.com/WongKinYiu/yolov7.git
RUN cd yolov7 && git checkout 84932d70fb9e2932d0a70e4a1f02a1d6dd1dd6ca

COPY fogverse/ fogverse/
COPY executor/inference.py .

ENTRYPOINT ["python", "-u"]
