import asyncio
import os
import cv2

import numpy as np

from pathlib import Path
from fogverse import Producer, Consumer, ConsumerStorage
from fogverse.logging import CsvLogging
from fogverse.util import (get_cam_id, get_timestamp_str)

SIZE = (640,480)
DIR = Path('val2017')

VID_PATH = os.getenv('VID_PATH')
VID_PATH = Path(VID_PATH)

class MyFrameProducer(CsvLogging, Producer):
    def __init__(self, loop=None):
        self.cam_id = get_cam_id()
        self.producer_topic = 'input'
        self.auto_decode = False
        self.frame_idx = 1
        CsvLogging.__init__(self)
        Producer.__init__(self,loop=loop)

    def _after_start(self):
        self.vid_cap = cv2.VideoCapture(str(VID_PATH))

    async def receive(self):
        data = self.vid_cap.read()
        return data

    async def send(self, data):
        key = str(self.frame_idx).encode()
        headers = [
            ('cam', self.cam_id.encode()),
            ('frame', str(self.frame_idx).encode()),
            ('timestamp', get_timestamp_str().encode())]
        await super().send(data, key=key, headers=headers)
        self.frame_idx += 1

class MyResultStorage(CsvLogging, Consumer):
    def __init__(self, loop=None):
        self.consumer_topic = 'result'
        self.auto_encode = False
        self.vid_cap = cv2.VideoWriter(f'result/{VID_PATH.stem}-result\
                                       {VID_PATH.suffix}')

    def send(self, data):
        self.vid_cap.write(data)

async def main():
    producer = MyFrameProducer()
    result_storage = MyResultStorage()
    tasks = [producer.run(), result_storage.run()]
    try:
        await asyncio.gather(*tasks)
    except:
        for t in tasks:
            t.close()

if __name__ == '__main__':
    asyncio.run(main())
