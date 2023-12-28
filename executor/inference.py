import asyncio
import os
import torch

import numpy as np

from pathlib import Path
from fogverse import Consumer, Producer, Profiling, Manager

ENCODING = os.getenv('ENCODING', 'jpg')
MODEL = os.getenv('MODEL', 'yolo7tinycrowdhuman.pt')
SCHEME = os.getenv('SCHEME', '0940-0945')

CSV_DIR = Path('logs') / SCHEME

class MyExecutor(Profiling, Consumer, Producer):
    def __init__(self):
        # Using https://github.com/WongKinYiu/yolov7
        # from commit 84932d70fb9e2932d0a70e4a1f02a1d6dd1dd6ca
        self.consumer_topic = [f'input_{SCHEME}']
        self.group_id = f'group-{SCHEME}'
        self.producer_topic = f'result_{SCHEME}'
        self.encode_encoding = 'jpg'
        self.always_read_last = True

        profiling_name = f'{self.__class__.__name__}_{SCHEME}'
        Profiling.__init__(self, name=profiling_name, dirname=CSV_DIR)
        Consumer.__init__(self)
        Producer.__init__(self)

    async def _after_start(self):
        # to fix the first inference bottleneck
        self.model = torch.hub.load('yolov7', 'custom',
                                    MODEL, source='local')
        dummy = (np.random.rand(1080,1920,3)*255).astype(np.uint8)
        self._log.std_log('Warming up')
        self.model(dummy)
        self._log.std_log('Ready')

    def _process(self, data):
        results = self.model(data)
        results.render()
        return data

    async def process(self, data):
        return await self._loop.run_in_executor(None,
                                               self._process,
                                               data)

async def main():
    executor = MyExecutor()
    manager = Manager([executor],
                      component_id=f'executor',
                      app_id=SCHEME,
                      topic_str_format=dict(scheme=SCHEME),
                      log_dir=CSV_DIR)
    await manager.run()

if __name__ == '__main__':
    asyncio.run(main())
