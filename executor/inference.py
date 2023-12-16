import asyncio
import os
import torch

import numpy as np

from pathlib import Path
from fogverse import Consumer, Producer, CsvLogging

ENCODING = os.getenv('ENCODING', 'jpg')
MODEL = os.getenv('MODEL', 'yolo7crowdhuman.pt')
SCHEME = os.getenv('SCHEME', '1250-1255')

CSV_DIR = Path('logs') / SCHEME

class MyExecutor(CsvLogging, Consumer, Producer):
    def __init__(self):
        # Using https://github.com/WongKinYiu/yolov7
        # from commit 84932d70fb9e2932d0a70e4a1f02a1d6dd1dd6ca
        self.model = torch.hub.load('yolov7', 'custom',
                                    MODEL, source='local')
        self.consumer_topic = [f'input_{SCHEME}']
        self.producer_topic = f'result_{SCHEME}'
        self.encode_encoding = 'jpg'
        self.always_read_last = True

        csv_file = f'{self.__class__.__name__}_{SCHEME}.csv'
        CsvLogging.__init__(self, filename=csv_file, dirname=CSV_DIR)
        Consumer.__init__(self)
        Producer.__init__(self)

    async def _after_start(self):
        # to fix the first inference bottleneck
        dummy = (np.random.rand(1080,1920,3)*255).astype(np.uint8)
        print('warming up')
        self.model(dummy)
        print('ready')

    def _process(self, data):
        results = self.model(data)
        results.render()
        return data

    async def process(self, data):
        return await self._loop.run_in_executor(None,
                                               self._process,
                                               data)

async def main():
    producer = MyExecutor()
    tasks = [producer.run()]
    try:
        await asyncio.gather(*tasks)
    finally:
        for t in tasks:
            t.close()

if __name__ == '__main__':
    asyncio.run(main())
