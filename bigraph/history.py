import fire
from pathlib import Path

from bigraph.parse import bigraph

def read_histories(path):
    path = Path(path)
    histories = []
    with open(path, 'r') as file:
        history = []
        for line in file:
            if line == '\n':
                if history:
                    histories.append(history)
                    history = []
            else:
                history.append(line)

    return histories


def test_history(path='histories/metabolism'):
    histories = read_histories(path)
    histories.sort(key=len, reverse=True)
    for line in histories[0]:
        print(line.strip())
    print(f'total histories: {len(histories)}')
    print(f'longest history: {len(histories[0])}')


if __name__ == '__main__':
    fire.Fire(test_history)
