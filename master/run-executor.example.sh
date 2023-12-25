source /opt/conda/bin/activate base
cd live-yolov7/executor \
&& SCHEME=$SCHEME \
    MODEL=yolo7tinycrowdhuman.pt \
    PRODUCER_SERVERS=kafka-0 \
    CONSUMER_SERVERS=kafka-0 nohup python inference.py >/dev/null 2>&1 &
