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

if __name__ == '__main__':
    scheme = int(sys.argv[1])
    for comp in components:
        print('='*40)
        for i in range(scheme):
            vid = Path(vid_names[i])
            executor_cmd = f'cd {comp}; '\
                           f'GROUP_ID=group-{vid.stem}-{i} ' \
                           f'DEVICE=videos/{vid} ' \
                           f'docker-compose -p {comp}-{vid.stem} up -d'
            print(executor_cmd)
            os.system(executor_cmd)
        print('='*40)
        time.sleep(5)
