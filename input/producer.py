import asyncio
import cv2
import os

from pathlib import Path
from fogverse import Producer, CsvLogging, Consumer, OpenCVConsumer
from fogverse.util import (get_cam_id, get_timestamp_str)

SCHEME = os.getenv('SCHEME', '1250-1255')
VS = int(os.getenv('VS', '1'))
OUT_FRAMERATE = 25/(VS//2 + 1)

CSV_DIR = Path('logs') / SCHEME

class MyFrameProducer(CsvLogging, OpenCVConsumer, Producer):
    def __init__(self, loop=None):
        self.cam_id = get_cam_id()
        self.producer_topic = f'input_{SCHEME}'
        self.auto_decode = False
        self.frame_idx = 1
        self.encode_encoding = 'jpg'

        csv_file = f'{self.__class__.__name__}_{SCHEME}.csv'
        CsvLogging.__init__(self, filename=csv_file, dirname=CSV_DIR)
        OpenCVConsumer.__init__(self,loop=loop,executor=None)
        Producer.__init__(self,loop=loop)

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
        self.consumer_topic = [f'result_{SCHEME}']
        self.auto_encode = False

        vid = Path(os.getenv('DEVICE'))
        self.vid_cap = cv2.VideoWriter(
                            f'results/{vid.stem}-result{vid.suffix}',
                            cv2.VideoWriter_fourcc(*'mp4v'),
                            OUT_FRAMERATE, (1920,1080))

        csv_file = f'{self.__class__.__name__}_{SCHEME}.csv'
        CsvLogging.__init__(self, filename=csv_file, dirname=CSV_DIR)
        Consumer.__init__(self,loop=loop)

    async def _send(self, data, *args, **kwargs):
        def __send(data):
            self.vid_cap.write(data)
        return await self._loop.run_in_executor(None, __send,
                                                data)

    async def _close(self):
        print('Video cap released.')
        self.vid_cap.release()
        await super()._close()

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
