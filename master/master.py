import asyncio
import docker
import json
import logging
import numpy as np
import os
import operator
import re
import secrets
import sys
import traceback

from fogverse.fogverse_logging import FogVerseLogging

from aiokafka import AIOKafkaConsumer
from datetime import datetime, timedelta

logger_name = 'master'
if len(sys.argv) > 1:
    logger_name = sys.argv[1]
header = ['component', 'latency (ms)', 'framerate (fps)']
logger = FogVerseLogging(name=logger_name,csv_header=header,
                            level=logging.FOGV_FILE)

async def listening(profile_data: dict):
    topic = 'fogverse-profiling'
    server = os.getenv('CLOUD_KAFKA')
    logger.std_log('Consuming topic %s on %s', topic, server)

    consumer = AIOKafkaConsumer(topic, bootstrap_servers=server)
    await consumer.start()
    await consumer.seek_to_end()

    try:
        async for msg in consumer:
            msg_value = msg.value.decode()
            data = json.loads(msg_value)
            name = data['name']
            if profile_data.get(name) is None:
                profile_data[name] = data
                profile_data[name]['log data'] = [data['log data']]
            else:
                lst_logs = profile_data[name]['log data']
                lst_logs.append(data['log data'])
                if len(lst_logs) > 20:
                    lst_logs.pop(0)
    finally:
        await consumer.stop()
        logger.std_log('Consumer closed')

def timestamp_to_datetime(timestamp):
    return datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S.%f')

async def make_decision(data):
    docker_client = docker.from_env()

    re_result_name = re.compile('^MyResultStorage.*$')

    offloading_task_data = {
        'last_offloading': None,
        'gap_offloading': timedelta(minutes=2),
        'provisioned': [],
    }
    metric_data = {}

    def put_metric_data(component, key, val, length_data=None):
        metric_data.setdefault(component, dict())

        _data = metric_data[component]
        _data.setdefault(key, dict())
        if length_data is not None:
            _data['length'] = length_data

        current_val = _data[key].get('value', np.nan)
        current_max = _data[key].get('max', current_val)

        _data[key] = dict(value=val, max=np.nanmax([current_max, val]))

    def print_final_data(padding=20):
        for component, comp_data in metric_data.items():
            if not re_result_name.match(component): continue
            print('~'*40)
            print(component)
            print('client:',data[component]['client'])
            for key, val in comp_data.items():
                s = key.ljust(padding)
                if key == 'length':
                    _val = val
                else:
                    _val = val['value']
                print(f'{s}:', _val)

                if key == 'length': continue
                s2 = f'max {key}'.ljust(padding)
                print(f'{s2}:', val['max'])
                print()

    def log_final_data(logger=logger):
        for component, comp_data in metric_data.items():
            log_data = [component]
            for col in header[1:]:
                log_data.append(comp_data[col]['value'])
            logger.csv_log(log_data)

    def is_eligible_to_offload(comp_name, metric, threshold, op=operator.gt):
        logger.std_log(
            'Is eligible to offload %s, %s, %s, %s, %s',
            comp_name, metric, threshold, op, offloading_task_data['last_offloading'])

        if np.isnan(metric): return False
        if not op(metric, threshold): return False
        if offloading_task_data['last_offloading'] is None: return True
        if comp_name in offloading_task_data['provisioned']: return False

        last_offload = offloading_task_data['last_offloading']
        gap_offload = offloading_task_data['gap_offloading']
        return datetime.now() > (last_offload + gap_offload)

    def put_offloading_task_data(comp_name):
        offloading_task_data['last_offloading'] = datetime.now()
        offloading_task_data['provisioned'].append(comp_name)

    def find_container_id(comp_name):
        for comp, comp_data in data.items():
            match = re.match(comp_name, comp)
            if match:
                return match.group(0), comp_data['client']
        return None, None

    while True:
        await asyncio.sleep(3)
        result_component = list(filter(lambda x:re_result_name.match(x),
                                       data.keys()))
        logger.std_log('%d components', len(result_component))
        for component, comp_data in data.items():
            col_idx = comp_data['log headers'].index('frame delay (ms)')
            length_data = len(comp_data['log data'])
            mean_latency = np.mean(list(map(lambda row:row[col_idx],
                                            comp_data['log data'])))
            mean_latency = round(mean_latency, 2)
            put_metric_data(component, 'latency (ms)', mean_latency, length_data)

            start = timestamp_to_datetime(comp_data['log data'][0][0])
            end = timestamp_to_datetime(comp_data['log data'][-1][0])
            duration = (end - start).total_seconds()
            framerate = -1
            if duration != 0:
                framerate = len(comp_data['log data'])/duration
                framerate = round(framerate, 2)
            put_metric_data(component, 'framerate (fps)', framerate, length_data)
        print_final_data()
        log_final_data()

        # check if any component needs to be offloaded
        for comp_name, metric in metric_data.items():
            if not re_result_name.match(comp_name): continue
            if metric['length'] < 20:
                logger.std_log('%s\'s profiling data is less than 20, continue',
                               comp_name)
                logger.std_log('Length: %s', metric['length'])
                continue
            metric_val = metric['framerate (fps)']
            threshold = 3
            operat = operator.lt
            if not is_eligible_to_offload(comp_name,
                                          metric_val['value'],
                                          threshold,
                                          op=operat):
                logger.std_log('Not eligible')
                continue

            # need to send to cloud
            comp_data = data[comp_name]
            extras_comp_data = comp_data['extras']
            if len(extras_comp_data) == 0: continue
            executor_name_pattern = extras_comp_data['executor_name_pattern']
            executor_img_name = extras_comp_data['executor_image_name']

            logger.std_log('Offloading %s', comp_name)
            exec_comp_name, docker_container_id = \
                find_container_id(executor_name_pattern)

            logger.std_log('Stopping container %s', docker_container_id)
            container = docker_client.containers.get(docker_container_id)
            container.stop()

            env = extras_comp_data['env']
            logger.std_log('Initializing image %s on cloud with env=%s',
                            executor_img_name, env)

            scheme = env['SCHEME']
            model = env['MODEL']
            exec_comp_name = f'{exec_comp_name}-{secrets.token_hex(3)}'\
                .replace('_','-')\
                .lower()

            start_init_gcp = datetime.now()
            initiate_cloud = await asyncio.create_subprocess_shell(
                f'SCHEME={scheme} MODEL={model} INSTANCE_NAME={exec_comp_name} '\
                    'bash cloud.sh',
                stdout=asyncio.subprocess.PIPE)

            stdout, stderr = await initiate_cloud.communicate()
            end_init_gcp = datetime.now()
            stdout = stdout.decode()
            logger.std_log('Initialized container %s.\n'\
                            'Stdout: %s', exec_comp_name, stdout)
            logger.std_log('GCP initialization time: %s.',
                        (end_init_gcp-start_init_gcp).total_seconds())

            await asyncio.sleep(100)
            start_install_dep = datetime.now()
            install_dep = await asyncio.create_subprocess_shell(
                f'gcloud compute ssh --zone "REDACTED" "{exec_comp_name}" '\
                '-- bash -s < install-dep.sh',
                stdout=asyncio.subprocess.PIPE)

            stdout, stderr = await install_dep.communicate()
            end_install_dep = datetime.now()
            stdout = stdout.decode()
            logger.std_log('Installed required dependencies for container %s.\n'\
                            'Stdout: %s', exec_comp_name, stdout)
            logger.std_log('Dependencies installation time: %s.',
                        (end_install_dep-start_install_dep).total_seconds())

            start_scp = datetime.now()
            scp = await asyncio.create_subprocess_shell(
                'gcloud compute scp --zone "REDACTED" '\
                    'yolo7tinycrowdhuman.pt '\
                    f'{exec_comp_name}:/REDACTED/',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)

            stdout, stderr = await scp.communicate()
            end_scp = datetime.now()
            stdout = stdout.decode()
            stderr = stderr.decode()
            logger.std_log('Copied the pretrained weight.\n'\
                            'Stdout: %s'\
                            'stderr: %s', stdout, stderr)
            logger.std_log('Copy time: %s.', (end_scp-start_scp).total_seconds())
            assert stderr == ''

            start_executor_exec_time = datetime.now()
            run_executor = await asyncio.create_subprocess_shell(
                f'nohup gcloud compute ssh --zone "REDACTED" "{exec_comp_name}" '\
                f'-- SCHEME={scheme} bash -s < run-executor.sh >/dev/null 2>&1 &',
            )

            await run_executor.wait()
            end_executor_exec_time = datetime.now()
            logger.std_log('The component %s has been executed.', exec_comp_name)
            logger.std_log('Run script time: %s.',
                        (end_executor_exec_time-start_executor_exec_time).total_seconds())

            await asyncio.sleep(20)
            logger.std_log('Total time to run component %s: %s.',
                        exec_comp_name,
                        (end_executor_exec_time-start_init_gcp).total_seconds())

            put_offloading_task_data(comp_name)


async def main():
    data = {}
    tasks = [listening(data), make_decision(data)]
    tasks = [asyncio.ensure_future(task) for task in tasks]
    try:
        await asyncio.gather(*tasks)
    except:
        err = traceback.format_exc()
        logger.std_log(err)
        for t in tasks:
            t.cancel()
        logger.std_log('Closed all')
    finally:
        logger.std_log('Done')

if __name__ == '__main__':
    asyncio.run(main())
