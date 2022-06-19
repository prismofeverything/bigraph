import fire
from pathlib import Path

from bigraph.parse import bigraph

def read_histories(path):
    path = Path(path)
    if not path.exists():
        return []

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
    if len(histories) == 0:
        print('no histories')
    else:
        histories.sort(key=len, reverse=True)
        for line in histories[0]:
            print(line.strip())
        print(f'history lengths: {[len(history) for history in histories]}')
        print(f'total histories: {len(histories)}')
        print(f'longest history: {len(histories[0])}')


if __name__ == '__main__':
    fire.Fire(test_history)
