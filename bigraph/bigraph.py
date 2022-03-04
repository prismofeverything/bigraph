import os
import copy
import json
import fire
from pathlib import Path

class Bigraph():
    def __init__(self, definition=None):
        self.definition = definition

class Node(Bigraph):
    def __init__(self, control, ports=None, sites=None):
        self.control = control
        self.ports = ports or [
            None for _ in range(self.arity())]
        self.sites = sites

    def label(self):
        if isinstance(self.control, dict):
            return list(self.control.keys())[0]
        else:
            return self.control

    def arity(self):
        if isinstance(self.control, dict):
            return list(self.control.values())[0]
        else:
            return 0

    def nest(self, inner):
        self.sites = inner
        return self

    def render(self):
        render = self.label()
        arity = self.arity()

        if arity > 0:
            names = ', '.join([
                port or '{}'
                for port in self.ports])
            names = '{' + names + '}'
            render = f'{render}{names}'

        if self.sites:
            inner = self.sites.render()
            render = f'{render}.{inner}'

        return render

id_node = Node('id')

class Edge(Bigraph):
    def __init__(self, name):
        self.name = name

    def render(self):
        return '{' + self.name + '}'

class Parallel(Bigraph):
    def __init__(self, parallel):
        self.parallel = parallel or []

    def render(self):
        parallel = ' || '.join([
            parallel.render()
            for parallel in self.parallel])
        return f'({parallel})'

class Merge(Bigraph):
    def __init__(self, merge):
        self.merge = merge or []

    def render(self):
        merge = ' | '.join([
            merge.render()
            for merge in self.merge])
        return f'({merge})'

class Reaction():
    def __init__(self, match, result, instantiation=None, rate=None):
        self.match = match
        self.result = result
        self.instantiation = instantiation
        self.rate = rate

    def render(self, indent=0):
        block = ''.join([' ' for _ in range(indent)])
        rate = '[ ' + str(self.rate) + ' ]' if self.rate else ''
        arrow = f'-{rate}->'
        render = block + self.match.render() + '\n' + block + arrow + '\n' + block + self.result.render()
        if self.instantiation:
            render = render + '\n' + block + '@ ' + str(self.instantiation)
        return render

class BigraphicalReactiveSystem():
    def __init__(
            self,
            controls=None,
            bigraphs=None,
            reactions=None,
            system=None,
            executable='bigrapher',
            path='.'):
        self.controls = controls or {}
        self.bigraphs = bigraphs or {}
        self.reactions = reactions or {}
        self.system = system

        self.executable = executable
        self.path = Path(path)

    def simulate(self):
        render = self.render()
        big_path = self.path / 'system.big'
        if not os.path.exists(self.path):
            os.makedirs(self.path)
        with open(big_path, 'w') as big_file:
            big_file.write(render)

    def render(self):
        controls = '\n'.join([
            f'atomic ctrl {label} = {control["ports"]};' if isinstance(control, dict) and control['atomic'] else f'ctrl {label} = {control};'
            for label, control in self.controls.items()])

        reactions = '\n'.join([
            f'react {label} =\n{reaction.render(2)};\n'
            for label, reaction in self.reactions.items()])

        bigraphs = '\n'.join([
            f'big {label} =\n  {bigraph.render()};\n'
            for label, bigraph in self.bigraphs.items()])

        declarations = '\n\n'.join([controls, reactions, bigraphs])

        rules = ', '.join(self.reactions.keys())
        predicates = ', '.join(self.system.get('preds', []))

        system = '\n'.join([
            'begin brs',
            f'  init {self.system["init"]};',
            f'  rules = [ {{{rules}}} ];',
            f'  preds = {{ {predicates} }};',
            'end'])

        big = '\n\n'.join([declarations, system])
        return big


def test_bigraphs(
        executable='bigrapher'):

    controls = {
        'A': 1,
        'A\'': 1,
        'Mail': 0,
        'M': {'atomic': True, 'ports': 2},
        'Snd': 0,
        'Ready': 0,
        'New': 0,
        'Fun': 0}

    a0 = Node({'A': 1}, ['a']).nest(
        Node('Snd').nest(
            Merge([
                Node({'M': 2}, ['a', 'v_a']),
                Node('Ready').nest(
                    Node('Fun').nest(
                        Node('1')))])))

    a1 = Node({'A': 1}, ['b']).nest(
        Node('Snd').nest(
            Node({'M': 2}, ['a', 'v_b'])))

    bigraphs = {
        'a0': a0,
        'a1': a1,

        's0': Merge([
            a0,
            a1,
            Node('Mail').nest(
                Node('1'))]),

        'phi': Node('Mail').nest(
            Merge([
                Node({'M': 2}, ['a', 'v']),
                id_node]))}

    reactions = {
        'snd': Reaction(
            Merge([
                Node({'A': 1}, ['a0']).nest(
                    Node('Snd').nest(
                        Merge([
                            Node({'M': 2}, ['a1', 'v']),
                            id_node]))),
                Node('Mail')]),
            Merge([
                Node({'A': 1}, ['a0']),
                Node('Mail').nest(
                    Merge([
                        Node({'M': 2}, ['a1', 'v']),
                        id_node]))])),

        'ready': Reaction(
            Merge([
                Node({'A': 1}, ['a']).nest(
                    Node('Ready')),
                Node('Mail').nest(
                    Merge([
                        Node({'M': 2}, ['a', 'v']),
                        id_node]))]),
            Merge([
                Node({'A': 1}, ['a']),
                Node('Mail'),
                Edge('v')])),

        'lambda': Reaction(
            Node({'A': 1}, ['a']).nest(
                Node('Fun')),
            Node({'A': 1}, ['a'])),

        'new': Reaction(
            Node({'A': 1}, ['a0']).nest(
                Merge([
                    Node('New').nest(
                        Merge([
                            Node({'A\'': 1}, ['a1']),
                            id_node])),
                    id_node])),
            Merge([
                Node({'A': 1}, ['a0']).nest(
                    Merge([id_node, id_node])),
                Node({'A': 1}, ['a1']).nest(
                    Merge([id_node, id_node]))]),
            instantiation=[1, 2, 0, 2])}
            
    system = BigraphicalReactiveSystem(
        controls=controls,
        bigraphs=bigraphs,
        reactions=reactions,
        system={'init': 's0', 'preds': ['phi']},
        executable='/home/youdonotexist/code/bigraph-tools/_build/default/bigrapher/src/bigrapher.exe',
        path='out/test/example')

    system.simulate()

    print(system.render())


if __name__ == '__main__':
    fire.Fire(test_bigraphs)
