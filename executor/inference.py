import asyncio
import os
import re
import torch

import numpy as np

from fogverse import Consumer, Producer, ConsumerStorage, CsvLogging

from pathlib import Path

ENCODING = os.getenv('ENCODING', 'jpg')
MODEL = os.getenv('MODEL', 'yolo7crowdhuman.pt')

def get_csv_file_folder(cls: object):
    device = Path(os.getenv('DEVICE'))
    csv_file = f'{cls.__class__.__name__}_{device.stem}.csv'
    csv_folder = re.sub('^(\d{2})-(\d{2})-\d{2}_(\d{2})-(\d{2})-\d{2}',
                        '\g<1>\g<2>-\g<3>\g<4>', device.stem)
    csv_folder = 'logs' / Path(csv_folder)
    return csv_file, csv_folder

class MyStorage(Consumer, ConsumerStorage):
    def __init__(self, keep_messages=False):
        self.consumer_topic = ['input']
        Consumer.__init__(self)
        ConsumerStorage.__init__(self, keep_messages=keep_messages)

class MyExecutor(CsvLogging, Producer):
    def __init__(self, consumer):
        # Using https://github.com/WongKinYiu/yolov7
        # from commit 84932d70fb9e2932d0a70e4a1f02a1d6dd1dd6ca
        self.model = torch.hub.load('yolov7', 'custom',
                                    MODEL, source='local')
        self.producer_topic = 'result'
        self.consumer = consumer
        self.encode_encoding = 'jpg'

        csv_file, csv_folder = get_csv_file_folder(self)
        CsvLogging.__init__(self, filename=csv_file, dirname=csv_folder)
        Producer.__init__(self)

    async def _after_start(self):
        # to fix the first inference bottleneck
        dummy = (np.random.rand(1080,1920,3)*255).astype(np.uint8)
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
    producer = MyExecutor(consumer)
    tasks = [consumer.run(), producer.run()]
    try:
        await asyncio.gather(*tasks)
    finally:
        for t in tasks:
            t.close()

if __name__ == '__main__':
    asyncio.run(main())
