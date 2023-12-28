import asyncio
import json
import logging
import numpy as np
import operator
import pprint
import re
import sys

from datetime import datetime
from fogverse import (Manager, Consumer, AbstractConsumer, AbstractProducer,
                      Runnable)
from fogverse.fogverse_logging import FogVerseLogging
from fogverse.constants import (FOGV_STATUS_RUNNING, FOGV_STATUS_SHUTDOWN,
                                FOGV_STATUS_RUN_IN_CLOUD,
                                FOGV_STATUS_RUN_IN_LOCAL)

pp = pprint.PrettyPrinter(depth=2)

class MySharedData:
    def __init__(self, data):
        self.lock = asyncio.Lock()
        self.data = data

class MyMasterProfileListener(Consumer):
    def __init__(self, profiling_data, loop=None):
        self.profiling_data = profiling_data
        self.consumer_topic = 'fogverse-profiling'
        self.auto_encode = False
        Consumer.__init__(self, loop=loop)

    def decode(self, data):
        return json.loads(data)

    async def process(self, data):
        app_id = data['app_id']
        current_data = self.profiling_data.data
        async with self.profiling_data.lock:
            if current_data.get(app_id) is None:
                current_data[app_id] = data
                current_data[app_id]['log data'] = [data['log data']]
            else:
                current_data[app_id]['app_id'] = data['app_id']
                current_data[app_id]['log headers'] = data['log headers']
                current_data[app_id]['extras'] = data['extras']
                lst_logs = current_data[app_id].get('log data', [])
                lst_logs.append(data['log data'])
                if len(lst_logs) > 20:
                    lst_logs.pop(0)
                current_data[app_id]['log data'] = lst_logs

    async def send(self, *args, **kwargs):
        pass

def timestamp_to_datetime(timestamp):
    return datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')

class MyMasterProfiler(AbstractConsumer, AbstractProducer, Runnable):
    def __init__(self,
                 profiling_data: MySharedData,
                 metric_data: MySharedData,
                 chosen_metric,
                 threshold,
                 loop=None):
        self.profiling_data = profiling_data
        self.metric_data = metric_data
        self.chosen_metric = chosen_metric
        self.threshold = threshold
        self.auto_decode = False
        self.auto_encode = False
        self.csv_header = ['component', 'where', self.chosen_metric]
        self.logger = FogVerseLogging(self.__class__.__name__,
                                    csv_header=self.csv_header,
                                    level=logging.FOGV_CSV)
        self.re_result_name = re.compile('^MyResultStorage.*$')
        Consumer.__init__(self, loop=loop)

    async def receive(self):
        await asyncio.sleep(5)
        return self.profiling_data.data

    def process_framerate(self, data):
        framerates = []
        for component, comp_data in data.items():
            if comp_data.get('where') == FOGV_STATUS_RUN_IN_CLOUD: continue
            if comp_data.get('status') == FOGV_STATUS_SHUTDOWN: continue
            if comp_data.get('log data') is None: continue
            if len(comp_data.get('log data', [])) < 20: continue
            start = timestamp_to_datetime(comp_data['log data'][0][0])
            end = timestamp_to_datetime(comp_data['log data'][-1][0])
            duration = (end - start).total_seconds()
            framerate = np.nan
            if duration != 0:
                framerate = len(comp_data['log data'])/duration
                framerate = round(framerate, 2)
            framerates.append(framerate)
        return np.nanmean(framerates)

    def put_metric_data(self, key, data):
        self.metric_data.data[key] = data

    def log_metric_data(self, data):
        log_data = []
        for header in self.csv_header:
            log_data.append(data[header])
        self.logger.csv_log(log_data)

    async def process(self, data):
        print('di dalam proses')
        print('Profiling data:')
        pp.pprint(data)
        if not data: return
        framerate = np.nan
        async with self.profiling_data.lock:
            framerate = self.process_framerate(data)

        async with self.metric_data.lock:
            self.put_metric_data('framerate (fps)', framerate)
            self.log_metric_data(self.metric_data.data)
            print('Metric data:')
            pp.pprint(self.metric_data.data)

    async def send(self, *args, **kwargs):
        pass

class MyMasterCommandListener(Consumer):
    def __init__(self,
                 profiling_data: MySharedData,
                 metric_data: MySharedData,
                 chosen_metric,
                 threshold,
                 compare=operator.gt,
                 loop=None):
        self.profiling_data = profiling_data
        self.metric_data = metric_data
        self.chosen_metric = chosen_metric
        self.threshold = threshold
        self.compare = compare
        self.consumer_topic = 'fogverse-commands'
        self.auto_decode = False
        self.auto_encode = False
        self.logger = FogVerseLogging(self.__class__.__name__,
                                    level=logging.FOGV_FILE)
        self.scheduled = []
        Consumer.__init__(self, loop=loop)

    def decode(self, data):
        return json.loads(data)

    async def handle_local_deployment(self, message):
        self.logger.std_log('Deploying to local')
        image = message['image']
        env = message['env']
        scheme = env['scheme']
        consumer_servers = env['consumer_servers']
        producer_servers = env['producer_servers']

        cmd = f'gcloud compute ssh --zone us-west4-a gpu-t4-1 -- '\
              f'"docker pull {image} && '\
               'cd ~/documents/live-yolov7/executor && '\
               'docker run -d --gpus all '\
               '-w /workplace/fogverse-app '\
               '-v \$(pwd)/logs/:/workplace/fogverse-app/logs/ '\
              f'-e SCHEME={scheme} '\
              f'-e CONSUMER_SERVERS={consumer_servers} '\
              f'-e PRODUCER_SERVERS={producer_servers} '\
              f'{image} inference.py" '\
               '>/dev/null 2>&1'
        self.logger.std_log('Running command %s', cmd)
        shell = await asyncio.create_subprocess_shell(cmd)
        await shell.wait()

    async def handle_cloud_deployment(self, message):
        self.logger.std_log('Deploying to cloud')
        image = message['image']
        env = message['env']
        scheme = env['scheme']
        consumer_servers = env['consumer_servers']
        producer_servers = env['producer_servers']
        ins_name = f'myexecutor-{scheme}'

        cmd = f'INSTANCE_NAME={ins_name} bash cloud.sh >/dev/null 2>&1'
        self.logger.std_log('Running command %s', cmd)
        shell = await asyncio.create_subprocess_shell(cmd)
        await shell.wait()

        await asyncio.sleep(10)
        cmd = f'gcloud compute ssh --zone us-east4-c {ins_name} -- '\
              f'"docker pull {image} && '\
               'cd ~ && '\
               'docker run -d -w /workplace/fogverse-app '\
               '-v \$(pwd)/logs/:/workplace/fogverse-app/logs/ '\
              f'-e SCHEME={scheme} '\
              f'-e CONSUMER_SERVERS={consumer_servers} '\
              f'-e PRODUCER_SERVERS={producer_servers} '\
              f'{image} inference.py" '\
               '>/dev/null 2>&1'
        self.logger.std_log('Running command %s', cmd)
        shell = await asyncio.create_subprocess_shell(cmd)
        await shell.wait()

    async def handle_request_deploy(self, message):
        app_id = message['app_id']
        metric = None
        async with self.profiling_data.lock:
            if self.profiling_data.data.get(app_id, {})\
                                  .get('status') == FOGV_STATUS_RUNNING:
                return

        async with self.metric_data.lock:
            metric = self.metric_data.data.get(self.chosen_metric)
        if metric is None or np.isnan(metric) or \
                self.compare(metric, self.threshold):
            await self.handle_local_deployment(message)
            where = FOGV_STATUS_RUN_IN_LOCAL
        else:
            await self.handle_cloud_deployment(message)
            where = FOGV_STATUS_RUN_IN_CLOUD

        self.logger.std_log('Component %s has been deployed', app_id)
        async with self.profiling_data.lock:
            self.profiling_data.data.setdefault(app_id, {
                'app_id': app_id,
                'log headers': [],
                'log data': [],
                'extras': {},
                'status': None,
                'where': None,
            })
            self.profiling_data.data[app_id]['status'] = FOGV_STATUS_RUNNING
            self.profiling_data.data[app_id]['where'] = where

    async def handle_shutdown(self, message):
        self.logger.std_log('Handling shutdown status')
        await asyncio.sleep(5)
        app_id = message['app_id']
        async with self.profiling_data.lock:
            if self.profiling_data.data.get(app_id) is None: return
            self.profiling_data.data[app_id]['status'] = FOGV_STATUS_SHUTDOWN

    async def process(self, data):
        self.logger.std_log('got command: %s', data)
        command = data['command']
        message = data['message']
        handler = getattr(self, f'handle_{command.lower()}', None)
        if callable(handler):
            ret = handler(message)
            if asyncio.iscoroutine(ret):
                ret = await ret
            return ret
        if hasattr(self, 'handle_message'):
            return await self.handle_message(command, message)


    async def send(self, *args, **kwargs):
        pass

async def main():
    profiling_data = MySharedData(dict())
    metric_data = MySharedData(dict())
    profile_listener = MyMasterProfileListener(profiling_data)

    threshold = int(sys.argv[1])
    chosen_metric = 'framerate (fps)'
    compare = operator.gt
    profiler = MyMasterProfiler(profiling_data, metric_data,
                                chosen_metric, threshold)
    command_listener = MyMasterCommandListener(profiling_data,
                                               metric_data,
                                               chosen_metric,
                                               threshold,
                                               compare=compare)
    manager = Manager()
    await manager.run_components([profile_listener, profiler, command_listener])

if __name__ == '__main__':
    asyncio.run(main())
