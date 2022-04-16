import os
import copy
import json
import fire
import subprocess
import networkx as nx
from pathlib import Path


AVAILABLE_OUTPUT_FORMATS = ['json', 'svg', 'txt']


def none_index(seq):
    for index, value in enumerate(seq):
        if value is None:
            return index
    return -1


class Bigraph():
    def __init__(self, definition=None):
        self.definition = definition

    def merge(self, other):
        return Merge([self, other])

    def get_merge(self):
        return [self]

    def to_spec(self):
        # TODO
        return {}

    @classmethod
    def from_spec(cls, spec):
        nodes_state = spec['nodes']
        place_state = spec['place_graph']
        link_state = spec['link_graph']
        
        all_outer_names = []
        all_inner_names = []

        nodes = {
            node['node_id']: Node.from_spec(node['control'])
            for node in nodes_state}

        for link in link_state:
            outer_names = [
                outer['name']
                for outer in link['outer']]
            all_outer_names.extend(outer_names)

            inner_names = [
                inner['name']
                for inner in link['inner']]
            all_inner_names.extend(inner_names)

            # TODO is this necessary? It seems like it might be desirable
            #   to ensure that each link has only one outer/inner name
            if len(outer_names) > 0:
                canonical_name = outer_names[0]
            elif len(inner_names) > 0:
                canonical_name = inner_names[0]
            else:
                raise Exception(f'no defined inner or outer names for link {link}')

            for port in link['ports']:
                nodes[port['node_id']].link(canonical_name)

        targets = [
            edge['target']
            for edge in place_state['rn']]
        if len(targets) > 1:
            root = Merge([
                nodes[id]
                for id in targets])
        elif len(targets) == 1:
            root = nodes[targets[0]]
        else:
            # TODO: is this true?
            raise Exception('cannot have a bigraph without at least one root node')

        for nest in place_state['nn']:
            above = nodes[nest['source']]
            below = nodes[nest['target']]
            above.nest(below)

        return root


class Control(Bigraph):
    def __init__(
            self,
            label=None,
            arity=0,
            atomic=False,
            fun=()):
        self.label = label
        self.arity = arity
        self.atomic = atomic
        self.fun = fun
            
    def generate(self, ports, params=None):
        return Node(
            control=self,
            ports=ports,
            params=params)

    def render(self):
        params = ''
        if self.fun:
            params = ','.join(self.fun)
            params = f'({params})'
        render = f'ctrl {self.label}{params} = {self.arity}'
        if self.fun:
            render = f'fun {render}'
        if self.atomic:
            render = f'atomic {render}'

        return render


class Node(Bigraph):
    def __init__(
            self,
            control=None,
            ports=None,
            sites=None,
            params=None):
        ''' create a bigraphical node 

        Args:
            control: instance of Control describing this node's ports
            ports: a list of edges into this node. initialized to a list
                containing `None` for range(arity) if arg is `None`
            sites: TODO
        '''

        self.control = control or Control()
        self.params = params
        self.ports = ports or [
            None for _ in range(self.arity())]
        self.sites = sites

    @classmethod
    def from_spec(cls, spec):
        # this is from the big_json format
        fun = [
            list(param.keys())[0]
            for param in spec['ctrl_params']]

        params = [
            list(param.values())[0]
            for param in spec['ctrl_params']]

        control = Control(
            spec['ctrl_name'],
            arity=spec['ctrl_arity'],
            fun=fun)

        return cls(control, params=params)

    def label(self):
        return self.control.label or 'id'

    def arity(self):
        return self.control.arity

    def link(self, name):
        index = none_index(self.ports)

        if index == -1:
            raise Exception(
                'cannot link name {name}, all ports have already been named for this node: {self.render()}')

        self.ports[index] = name

    def nest(self, inner):
        if self.sites:
            self.sites.merge(inner)
        else:
            self.sites = inner

        return self

    def render(self, parent=False):
        render = self.label()
        arity = self.arity()

        if self.params:
            params = ','.join([str(param) for param in self.params])
            params = f'({params})'
            render = f'{render}{params}'

        if arity > 0:
            names = ', '.join([
                port or '{}'
                for port in self.ports])
            names = '{' + names + '}'
            render = f'{render}{names}'

        if self.sites:
            inner = self.sites.render(parent=True)
            render = f'{render}.{inner}'

        return render


id_node = Node()


class Edge(Bigraph):
    def __init__(self, name):
        self.name = name

    def render(self, parent=False):
        return '{' + self.name + '}'


class Parallel(Bigraph):
    def __init__(self, parallel):
        self.parallel = parallel or []

    def render(self, parent=False):
        parallel = ' || '.join([
            parallel.render()
            for parallel in self.parallel])
        render = f'{parallel}'
        if parent:
            render = f'({render})'
        return render


class Merge(Bigraph):
    def __init__(self, merges):
        self.parts = []
        for merge in merges:
            self.merge(merge)

    def merge(self, other):
        self.parts.extend(other.get_merge())

    def render(self, parent=False):
        merge = ' | '.join([
            merge.render()
            for merge in self.parts])
        render = f'{merge}'
        if parent:
            render = f'({render})'
        return render


class Reaction():
    def __init__(self, match, result, instantiation=None, rate=None):
        self.match = match
        self.result = result
        self.instantiation = instantiation
        self.rate = rate

    def render(self, indent=0, parent=False):
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
            path='.',
            key='system'):
        self.controls = controls or {}
        self.bigraphs = bigraphs or {}
        self.reactions = reactions or {}
        self.system = system

        self.regions = []
        self.sites = []
        self.outer_names = []
        self.inner_names = []

        self.executable = executable
        self.path = Path(path)
        self.key = key

    @classmethod
    def from_spec(cls, spec):
        state = Bigraph.from_spec(spec['state'])
        return cls(bigraphs=[state])

    def write(self, path=None, key=None):
        path = path or self.path
        key = key or self.key

        render = self.render()
        big_path = path / f'{key}.big'
        if not os.path.exists(path):
            os.makedirs(path)
        with open(big_path, 'w') as big_file:
            big_file.write(render)

    def execute(
        self,
        path=None,
        key=None,
        format='json',
        console=False):

        if not format in AVAILABLE_OUTPUT_FORMATS:
            raise Exception(f'output format "{format}" not supported. Available formats are {AVAILABLE_OUTPUT_FORMATS}')

        path = path or self.path
        key = key or self.key

        command = [
            self.executable,
            'sim',
            '-s',
            '-t',
            path / key,
            '-f',
            format,
            path / f'{key}.big']

        bigrapher_process = subprocess.Popen(command, stdout=subprocess.PIPE)
        output, error = bigrapher_process.communicate()

        if console:
            print(' '.join([str(token) for token in command]))
            print('\n\n\n')
            print(output)
            print('\n\n\n')
            print(error)
            print('\n\n\n')

    def read(self, path=None, key=None):
        path = path or self.path
        key = key or self.key

        with open(path / f'{key}.json', 'r') as system_file:
            transitions = json.load(system_file)['brs']

        trajectory = nx.DiGraph()
        for transition in transitions:
            edge = [transition['source'], transition['target']]
            trajectory.add_edge(*edge)
        steps = nx.topological_generations(trajectory)

        history = []
        for step in steps:
            for parallel in step:
                with open(path / f'{parallel}.json', 'r') as step_file:
                    state = json.load(step_file)
                    root = Bigraph.from_spec(state)
                    history.append(root)

        return history

    def simulate(
        self,
        path=None,
        key=None,
        format='json',
        console=False):

        path = path or self.path
        key = key or self.key

        self.write(path=path, key=key)
        self.execute(path=path, key=key, format=format, console=console)
        result = self.read(path=path, key=key)
        return result

    def render(self, parent=False):
        # controls = '\n'.join([
        #     f'atomic ctrl {label} = {control["ports"]};' if isinstance(control, dict) and control['atomic'] else f'ctrl {label} = {control};'
        #     for label, control in self.controls.items()])

        controls = '\n'.join([
            f'{control.render()};'
            for control in self.controls.values()])

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
        executable='../bigraph-tools/_build/default/bigrapher/src/bigrapher.exe'):

    ctrl = {
        'A': Control(label='A', arity=1),
        'A\'': Control(label='A\'', arity=1),
        'Mail': Control(label='Mail'),
        'M': Control(label='M', atomic=True, arity=2),
        'Snd': Control(label='Snd'),
        'Ready': Control(label='Ready'),
        'New': Control(label='New'),
        'Fun': Control(label='Fun'),
        '1': Control(label='1')}

    # controls = {
    #     'A': 1,
    #     'A\'': 1,
    #     'Mail': 0,
    #     'M': {'atomic': True, 'ports': 2},
    #     'Snd': 0,
    #     'Ready': 0,
    #     'New': 0,
    #     'Fun': 0}

    a0 = Node(ctrl['A'], ['a']).nest(
        Node(ctrl['Snd']).nest(
            Merge([
                Node(ctrl['M'], ['a', 'v_a']),
                Node(ctrl['Ready']).nest(
                    Node(ctrl['Fun']).nest(
                        Node(ctrl['1'])))])))

    a1 = Node(ctrl['A'], ['b']).nest(
        Node(ctrl['Snd']).nest(
            Node(ctrl['M'], ['a', 'v_b'])))

    bigraphs = {
        'a0': a0,
        'a1': a1,

        's0': Merge([
            a0,
            a1,
            Node(ctrl['Mail']).nest(
                Node(ctrl['1']))]),

        'phi': Node(ctrl['Mail']).nest(
            Merge([
                Node(ctrl['M'], ['a', 'v']),
                id_node]))}

    reactions = {
        'snd': Reaction(
            Merge([
                Node(ctrl['A'], ['a0']).nest(
                    Node(ctrl['Snd']).nest(
                        Merge([
                            Node(ctrl['M'], ['a1', 'v']),
                            id_node]))),
                Node(ctrl['Mail'])]),
            Merge([
                Node(ctrl['A'], ['a0']),
                Node(ctrl['Mail']).nest(
                    Merge([
                        Node(ctrl['M'], ['a1', 'v']),
                        id_node]))])),

        'ready': Reaction(
            Merge([
                Node(ctrl['A'], ['a']).nest(
                    Node(ctrl['Ready'])),
                Node(ctrl['Mail']).nest(
                    Merge([
                        Node(ctrl['M'], ['a', 'v']),
                        id_node]))]),
            Merge([
                Node(ctrl['A'], ['a']),
                Node(ctrl['Mail']),
                Edge('v')])),

        'lambda': Reaction(
            Node(ctrl['A'], ['a']).nest(
                Node(ctrl['Fun'])),
            Node(ctrl['A'], ['a'])),

        'new': Reaction(
            Node(ctrl['A'], ['a0']).nest(
                Merge([
                    Node(ctrl['New']).nest(
                        Merge([
                            Node(ctrl['A\''], ['a1']),
                            id_node])),
                    id_node])),
            Merge([
                Node(ctrl['A'], ['a0']).nest(
                    Merge([id_node, id_node])),
                Node(ctrl['A'], ['a1']).nest(
                    Merge([id_node, id_node]))]),
            instantiation=[1, 2, 0, 2])}
            
    system = BigraphicalReactiveSystem(
        controls=ctrl,
        bigraphs=bigraphs,
        reactions=reactions,
        system={
            'init': 's0',
            'preds': ['phi']},
        executable=executable,
        path='out/test/execute')

    result = system.simulate(
       format='json',
       console=True)

       # format='svg',
       # console=True)

    print(system.render())
    print('\n\n\n')
    print('TRANSITIONS:')
    for transition in result:
        print(transition.render())


if __name__ == '__main__':
    fire.Fire(test_bigraphs)
