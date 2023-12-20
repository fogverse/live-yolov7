import os
import sys
import time

from pathlib import Path

components = ['executor', 'input']

vid_names = [
    '09-40-00_09-45-00.mp4',
    '11-50-00_11-55-00.mp4',
    '12-50-00_12-55-00.mp4',
    '16-10-00_16-15-00.mp4',
    '17-50-00_17-55-00.mp4',
]

scheme_to_vid = {
    '0940-0945':'09-40-00_09-45-00',
    '1150-1155':'11-50-00_11-55-00',
    '1250-1255':'12-50-00_12-55-00',
    '1610-1615':'16-10-00_16-15-00',
    '1750-1755':'17-50-00_17-55-00',
}

vid_to_scheme = dict((v,k) for k, v in scheme_to_vid.items())

if __name__ == '__main__':
    scheme_num = int(sys.argv[1])
    last = False
    for i in range(scheme_num):
        print('='*40)
        for j, comp in enumerate(components):
            vid = Path(vid_names[i])
            scheme = vid_to_scheme[vid.stem]
            executor_cmd = f'cd {comp}; '\
                           f'SCHEME={scheme} ' \
                           f'VS={scheme_num} ' \
                           f'GROUP_ID=group-{scheme} ' \
                           f'DEVICE=videos/{vid} ' \
                           f'docker-compose -p {comp}_{scheme} up -d'
            print(executor_cmd)
            os.system(executor_cmd)
            if j != len(components) - 1:
                time.sleep(15)
        print('='*40)
        if i != scheme_num - 1:
            time.sleep(30)
