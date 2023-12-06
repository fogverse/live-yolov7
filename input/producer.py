import asyncio
import os
import cv2

from pathlib import Path
from fogverse import Producer, CsvLogging, Consumer, OpenCVConsumer
from fogverse.util import (get_cam_id, get_timestamp_str)

class MyFrameProducer(CsvLogging, OpenCVConsumer, Producer):
    def __init__(self, loop=None):
        self.cam_id = get_cam_id()
        self.producer_topic = 'input'
        self.auto_decode = False
        self.frame_idx = 1
        self.encode_encoding = 'jpg'
        CsvLogging.__init__(self)
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
        self.consumer_topic = 'result'
        self.auto_encode = False

        vid = Path(os.getenv('DEVICE'))
        self.vid_cap = cv2.VideoWriter(
                            f'results/{vid.stem}-result{vid.suffix}',
                            cv2.VideoWriter_fourcc(*'mp4v'),
                            25, (1920,1080))
        CsvLogging.__init__(self)
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
