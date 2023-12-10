import json
import os
import re
import sys
import shutil

import pandas as pd

from io import StringIO
from pathlib import Path

scheme_to_vid = {
    '0940-0945':'09-40-00_09-45-00',
    '1150-1155':'11-50-00_11-55-00',
    '1250-1255':'12-50-00_12-55-00',
    '1610-1615':'16-10-00_16-15-00',
    '1750-1755':'17-50-00_17-55-00',
}

vid_to_scheme = dict((v,k) for k, v in scheme_to_vid.items())

def append_with_title(filepath: Path, title, data):
    with filepath.open('a') as f:
        f.write('\n')
        f.write(title + '\n')
        f.write(data)

def read_framerate(filepath: Path, output: Path):
    title = 'Framerate'
    df = pd.read_csv(StringIO(filepath.read_text()))
    df['start'] = pd.to_datetime(df['start'], unit='s')
    df['end'] = pd.to_datetime(df['end'], unit='s')
    df['duration (s)'] = df['end'] - df['start']
    df['duration (s)'] = df['duration (s)'].apply(lambda x: x.total_seconds())
    df['framerate (fps)'] = df['num frames'] / df['duration (s)']
    df.drop(['duration', 'framerate'], axis=1, inplace=True)
    data = df.to_csv(index=False)
    output.write_text(f'{title}\n{data}')
    return output

def read_delay(cursor, filepath, scheme_filters: list):
    title = 'Delay'
    sql = 'SELECT source,destination,delay FROM delay'
    cursor.execute(sql)
    res = cursor.fetchall()
    df = pd.DataFrame(res)
    a = df[df['source'].str.contains('SmartCCTV|CCTVInference')]
    b = df[df['destination'].str.contains('SmartCCTV|CCTVInference')]
    df = pd.concat([a,b])
    df.reset_index(drop=True,inplace=True)
    df.rename(columns={'delay':'delay (ms)'}, inplace=True)
    for i,row in df.iterrows():
        source = row['source']
        dest = row['destination']
        filtered = re.match('^.+-(\d+)_127\.0\.0\.1$', source)
        if filtered and filtered.group(1) not in scheme_filters:
            df.drop(i, inplace=True)
        filtered = re.match('^.+-(\d+)_127\.0\.0\.1$', dest)
        if filtered and filtered.group(1) not in scheme_filters:
            df.drop(i, inplace=True)
    df['source'] = df['source'].apply(
                   lambda x: re.sub('(-\d{3}){0,1}(_127.0.0.1)$','\g<1>',x))
    df['destination'] = df['destination'].apply(
                   lambda x: re.sub('(-\d{3}){0,1}(_127.0.0.1)$','\g<1>',x))
    data = df.to_csv(index=False)
    append_with_title(filepath, title, data)

def read_processing_time(cursor, filepath, scheme_filters: list):
    title = 'Processing Time'
    sql = 'SELECT nameConsistent,processingTime FROM processingTime \
           WHERE nameConsistent LIKE "%CCTVInference%"'
    cursor.execute(sql)
    rows = cursor.fetchall()
    lst = []
    for row in rows:
        name = row['nameConsistent']
        if not name.endswith('127.0.0.1'): continue
        proc_time = json.loads(row['processingTime'].decode())
        filtered = re.match('^.+-(\d+)_127\.0\.0\.1$', name)
        if filtered and filtered.group(1) not in scheme_filters: continue
        lst.append({'name': name,
                    'processing time (ms)': proc_time['processingTime']})
    df = pd.DataFrame(lst)
    df['name'] = df['name'].apply(
                   lambda x: re.sub('(-\d{3}){0,1}(_127.0.0.1)$','\g<1>',x))
    data = df.to_csv(index=False)
    append_with_title(filepath, title, data)

def read_packet_size(cursor, filepath, scheme_filters):
    title = 'Packet Size'
    sql = 'SELECT source,destination,packetSize FROM packetSize'
    cursor.execute(sql)
    res = cursor.fetchall()
    df = pd.DataFrame(res)
    a = df[df['source'].str.contains('SmartCCTV|CCTVInference')]
    b = df[df['destination'].str.contains('SmartCCTV|CCTVInference')]
    df = pd.concat([a,b])
    df.reset_index(drop=True,inplace=True)
    for i,row in df.iterrows():
        source = row['source']
        dest = row['destination']
        filtered = re.match('^.+-(\d+)_127\.0\.0\.1$', source)
        if filtered and filtered.group(1) not in scheme_filters:
            df.drop(i, inplace=True)
        filtered = re.match('^.+-(\d+)_127\.0\.0\.1$', dest)
        if filtered and filtered.group(1) not in scheme_filters:
            df.drop(i, inplace=True)
    df['source'] = df['source'].apply(
                   lambda x: re.sub('(-\d{3}){0,1}(_127.0.0.1)$','\g<1>',x))
    df['destination'] = df['destination'].apply(
                        lambda x: re.sub('(-\d{3}){0,1}(_127.0.0.1)$','\g<1>',x))
    df.rename(columns={'packetSize': 'packet size (bytes)'}, inplace=True)
    data = df.to_csv(index=False)
    append_with_title(filepath, title, data)

def read_docker_stat(filepath: Path):
    data = ''
    with filepath.open() as f:
        data = f.read()
    records = data.split('\n\n')
    df = pd.DataFrame(columns=['timestamp','NAME','CPU %','MEM USAGE / LIMIT',
                               'NET I/O','BLOCK I/O','PIDS'])
    for record in records:
        if record == '': continue
        _, timestamp, csv_text = re.split('^(\d{10})\.\d{9}\n', record)
        _df = pd.read_csv(StringIO(csv_text))
        _df.insert(loc=0, column='timestamp', value=float(timestamp))
        _df['timestamp'] = pd.to_datetime(_df['timestamp'], unit='s', utc=True)\
                            .map(lambda x: x.tz_convert('Asia/Jakarta'))
        drops = ['--', 'fogbus2-mariadb']
        for _drop in drops:
            null_index = _df[_df['NAME'].str.contains(_drop)].index
            _df.drop(null_index, inplace=True)
        _df['NAME'] = _df['NAME'].apply(lambda x:
            re.sub('^(CCTVInference-\d+).*Actor-(\d+).*$', 'TaskExecutor-\g<1>-\g<2>', x))
        if filepath.parent.name == 'fogbus2':
            _df['NAME'] = _df['NAME'].apply(lambda x: x.split('_')[0].rstrip('-'))
        elif filepath.parent.name == 'fogverse':
            _df['NAME'] = _df['NAME'].str.replace(r'-executor-pod-\d+','',
                                                  regex=True)
            _df['NAME'] = _df['NAME'].str.replace(r'(executor_\d{4}-\d{4})',
                                                  r'fogverse-\g<1>',regex=True)

            _df['NAME'] = _df['NAME'].str.replace(r'-input-pod-\d+','',
                                                  regex=True)
            _df['NAME'] = _df['NAME'].str.replace(r'input_(\d{4}-\d{4})',
                                                  r'fogverse-producer_\g<1>',
                                                  regex=True)

            _df['NAME'] = _df['NAME'].str.replace(r'-kafka-broker-\d+','',
                                                  regex=True)
        df = pd.concat([df,_df], axis=0)
    pd.options.display.max_colwidth = 100
    df.columns = df.columns.str.lower()
    return df

def read_memory(df):
    def convert_mem(mem_usg_str):
        usg = float(mem_usg_str[:-3])
        if mem_usg_str[-3:] == 'GiB':
            usg *= 1000
        usg *= 2**20/1e6
        return round(usg, 2)

    df[['mem usage (MB)', 'mem limit (MB)']] = \
        df['mem usage / limit'].str.split(' / ', n=1, expand=True)
    df['mem usage (MB)'] = df['mem usage (MB)'].apply(convert_mem)
    df['mem limit (MB)'] = df['mem limit (MB)'].str.rstrip('GiB')\
                                                     .astype('float') \
                                                     * 2**20/1e6 * 1000
    df['mem limit (MB)'] = df['mem limit (MB)'].round(1)
    df.drop('mem usage / limit', axis=1, inplace=True)

def read_cpu(df):
    df['cpu %'] = df['cpu %'].str.rstrip('%').astype(float)
    df.rename(columns={'cpu %': 'cpu (%)'}, inplace=True)

def read_io(df):
    df.drop(['net i/o', 'block i/o'], axis=1, inplace=True)

def read_docker(filepath: Path, filepath_csv: Path):
    stats = read_docker_stat(filepath)
    read_memory(stats)
    read_cpu(stats)
    read_io(stats)
    stats.drop('pids', axis=1, inplace=True)
    data = stats.to_csv(index=False)
    append_with_title(filepath_csv, 'Docker Stats', data)

def read_fogbus(filepath: Path, filepath_csv: Path, scheme_filters: list):
    from mysql.connector import connect

    db_password = os.getenv('DBPASSWORD')

    mydb = connect(
        host="localhost",
        user="root",
        password=db_password,
        database="FogBus2_SystemPerformance"
    )

    cursor = mydb.cursor(dictionary=True)
    read_framerate(filepath.with_name('framerate.csv'), filepath_csv)

    read_delay(cursor, filepath_csv, scheme_filters)
    read_processing_time(cursor, filepath_csv, scheme_filters)
    read_packet_size(cursor, filepath_csv, scheme_filters)

    read_docker(filepath, filepath_csv)

def move_log_files(move_to: Path):
    ask_move = input('Do you also want to copy csv log files? [y/N] ')
    if ask_move.lower() not in ['y', 'yes', '1']: return

    _input_component = Path('input')
    _executor_component = Path('executor')
    vs = int(move_to.parent.name.split('vs')[0])

    for scheme in list(scheme_to_vid.keys())[:vs]:
        scheme_folder = (move_to / scheme)
        scheme_folder.mkdir(exist_ok=True)
        for log_file in (_input_component / 'logs' / scheme).iterdir():
            _match = re.match('^My\w+_(\d{4}-\d{4}).csv$', log_file.name)
            if not _match or _match.group(1) != scheme: continue
            shutil.move(str(log_file.resolve()), str(scheme_folder.resolve()))

        for log_file in (_executor_component / 'logs' / scheme).iterdir():
            _match = re.match('^My\w+_(\d{4}-\d{4}).csv$', log_file.name)
            if not _match or _match.group(1) != scheme: continue
            shutil.move(str(log_file.resolve()), str(scheme_folder.resolve()))

        for vid_result in (_input_component / 'results').iterdir():
            _match = re.match('^(.+)-result.mp4$',
                              vid_result.name)
            if not _match or _match.group(1) != scheme_to_vid[scheme]: continue
            shutil.move(str(vid_result.resolve()), str(scheme_folder.resolve()))

def read_fogverse(filepath: Path, filepath_csv: Path):
    filepath_csv.write_text('')
    read_docker(filepath, filepath_csv)
    move_log_files(filepath.parent)

if __name__ == '__main__':
    filepath = Path(sys.argv[1])
    scheme_filters = []
    if len(sys.argv) > 2:
        scheme_filters = sys.argv[2].split(',')
    if filepath.stem == '.csv':
        raise Exception('Path is expected to be .txt extension file.')
    filepath_csv = filepath.with_suffix('.csv')
    if filepath_csv.exists():
        ans = input(f'We found that the {filepath_csv} file is '
                    'already exists.\n'
                    'Are you sure to continue? [Y/n] ')
        if ans.lower() not in ['', 'y', 'yes', '1']:
            print('bye')
            sys.exit()
    else:
        ans = input(f'Will write to {filepath_csv}.\n'
                    'Do you want to proceed? [Y/n] ')
        if ans.lower() not in ['', 'y', 'yes', '1']:
            print('bye')
            sys.exit()
    # read_fogbus(filepath, filepath_csv, scheme_filters)
    read_fogverse(filepath, filepath_csv)
