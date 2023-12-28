ARG DREG # docker registry
FROM ${DREG}ariqbasyar/fogbus2-fogverse:base-CCTVInference

RUN pip install confluent-kafka

# FogBus2
WORKDIR /workplace/fogbus2-app
COPY FogBus2/containers/taskExecutor/sources/requirements.txt .
RUN pip install -r requirements.txt
RUN git clone https://github.com/WongKinYiu/yolov7.git
RUN cd yolov7 && git checkout 84932d70fb9e2932d0a70e4a1f02a1d6dd1dd6ca

# Hostname
RUN echo "CCTVInference" > /etc/hostname

COPY FogBus2/containers/taskExecutor/sources/ .

# FogVerse
WORKDIR /workplace/fogverse-app
RUN cp -r ../fogbus2-app/yolov7/ yolov7/

COPY live-yolov7/fogverse/ fogverse/
COPY live-yolov7/executor/inference.py .
COPY live-yolov7/executor/yolo7crowdhuman.pt .
COPY live-yolov7/executor/yolo7tinycrowdhuman.pt .

ENTRYPOINT ["python", "-u"]
