import asyncio
import cv2
import os

from pathlib import Path
from fogverse import Producer, Profiling, Consumer, OpenCVConsumer, Manager
from fogverse.util import (get_cam_id, get_timestamp_str)
from fogverse.constants import FOGV_STATUS_SHUTDOWN

SCHEME = os.getenv('SCHEME', '0940-0945')
VS = int(os.getenv('VS', '1'))
OUT_FRAMERATE = 25/(VS//2 + 1)

CSV_DIR = Path('logs') / SCHEME
VID = Path(os.getenv('DEVICE') or 'videos/09-40-00_09-45-00.mp4')

class MyFrameProducer(Profiling, OpenCVConsumer, Producer):
    def __init__(self, loop=None, shutdown_callback=None):
        self.loop = loop or asyncio.get_event_loop()
        self.cam_id = get_cam_id()
        self.producer_topic = f'input_{SCHEME}'
        self.auto_decode = False
        self.frame_idx = 1
        self.encode_encoding = 'jpg'
        self.device = str(VID)
        self.shutdown_callback = shutdown_callback

        self.profiling_name = f'{self.__class__.__name__}_{SCHEME}'
        Profiling.__init__(self, name=self.profiling_name, dirname=CSV_DIR)
        OpenCVConsumer.__init__(self,loop=loop,executor=None)
        Producer.__init__(self,loop=loop)

    async def receive_error(self, *args, **kwargs):
        self._log.std_log('At the last frame')
        if callable(self.shutdown_callback):
            await self.shutdown_callback()
        return await super().receive_error(*args, **kwargs)

    async def send(self, data):
        key = str(self.frame_idx).encode()
        headers = [
            ('cam', self.cam_id.encode()),
            ('frame', str(self.frame_idx).encode()),
            ('timestamp', get_timestamp_str().encode())]
        await super().send(data, key=key, headers=headers)
        self.frame_idx += 1

class MyResultStorage(Profiling, Consumer):
    def __init__(self, loop=None):
        self.consumer_topic = [f'result_{SCHEME}']
        self.auto_encode = False
        self.group_id = f'group-{SCHEME}'

        self.vid_cap = cv2.VideoWriter(
                            f'results/{VID.stem}-result{VID.suffix}',
                            cv2.VideoWriter_fourcc(*'mp4v'),
                            OUT_FRAMERATE, (1920,1080))

        self.extra_remote_data = {'app_id': SCHEME}
        self.profiling_name = f'{self.__class__.__name__}_{SCHEME}'
        Profiling.__init__(self, name=self.profiling_name, dirname=CSV_DIR,
                           remote_logging=True, app_id=SCHEME)
        Consumer.__init__(self,loop=loop)

    async def _send(self, data, *args, **kwargs):
        def __send(data):
            self.vid_cap.write(data)
        return await self._loop.run_in_executor(None, __send,
                                                data)

    async def _close(self):
        self._log.std_log('Video cap released.')
        self.vid_cap.release()
        await super()._close()

async def main():
    producer = MyFrameProducer()
    result_storage = MyResultStorage()
    dreg = os.getenv('DREG') or ''
    to_deploy = {
        'executor': {
            'wait_to_start': True,
            'image': f'{dreg}ariqbasyar/fogbus2-fogverse:CCTVInference',
            'component': result_storage.profiling_name,
            'app_id': SCHEME,
            'env': {
                'scheme': SCHEME,
                'consumer_servers': os.getenv('PRODUCER_SERVERS'),
                'producer_servers': os.getenv('CONSUMER_SERVERS'),
            }
        }
    }

    manager = Manager([producer, result_storage],
                      to_deploy=to_deploy,
                      component_id=f'producer',
                      app_id=SCHEME,
                      topic_str_format=dict(scheme=SCHEME),
                      log_dir=CSV_DIR)
    producer.shutdown_callback = manager.send_shutdown
    await manager.run()

if __name__ == '__main__':
    asyncio.run(main())
