import os
import asyncio
import torch

import numpy as np

from fogverse import Consumer, Producer, ConsumerStorage
from fogverse.logging.logging import CsvLogging

ENCODING = os.getenv('ENCODING', 'jpg')
MODEL = os.getenv('MODEL', 'yolo7crowdhuman.pt')

class MyStorage(Consumer, ConsumerStorage):
    def __init__(self, keep_messages=False):
        self.consumer_topic = ['input']
        Consumer.__init__(self)
        ConsumerStorage.__init__(self, keep_messages=keep_messages)

class MyJetson(CsvLogging, Producer):
    def __init__(self, consumer):
        # Using https://github.com/WongKinYiu/yolov7
        # from commit 84932d70fb9e2932d0a70e4a1f02a1d6dd1dd6ca
        self.model = torch.hub.load('.', 'custom',
                           MODEL, source='local')
        self.consumer = consumer
        self.auto_encode = False
        CsvLogging.__init__(self)
        Producer.__init__(self)

    async def _after_start(self):
        # to fix the first inference bottleneck
        dummy = (np.random.rand(480,640,3)*255).astype(np.uint8)
        print('warming up')
        self.model(dummy)
        print('ready')

    async def receive(self):
        return await self.consumer.get()

    def _process(self, data):
        results = self.model(data)
        results.render()
        return data

    async def process(self, data):
        return await self._loop.run_in_executor(None,
                                               self._process,
                                               data)

async def main():
    consumer = MyStorage()
    producer = MyJetson(consumer)
    tasks = [consumer.run(), producer.run()]
    try:
        await asyncio.gather(*tasks)
    finally:
        for t in tasks:
            t.close()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
