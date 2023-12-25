source /opt/conda/bin/activate base
git clone --recurse-submodules https://github.com/fogverse/live-yolov7.git
cd live-yolov7 && pip install -e .
cd executor \
    && git clone https://github.com/WongKinYiu/yolov7.git \
    && cd yolov7 \
    && git checkout 84932d70fb9e2932d0a70e4a1f02a1d6dd1dd6ca
pip install aiokafka opencv-python
