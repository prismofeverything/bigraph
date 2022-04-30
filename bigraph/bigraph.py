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


class Base():
    def __init__(self, definition=None):
        self.definition = definition
        self.supernode = None

    def __repr__(self):
        return self.render()

    def merge(self, other):
        return Merge([self, other])

    def join(self, supernode):
        self.supernode = supernode

    def get_merge(self):
        return [self]

    def is_site(self):
        return false

    def to_spec(self):
        # TODO
        return {}

    def find_edges(self):
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

        links = {}
        for link in link_state:
            outer_names = [
                outer['name']
                for outer in link['outer']]
            all_outer_names.extend(outer_names)

            inner_names = [
                inner['name']
                for inner in link['inner']]
            all_inner_names.extend(inner_names)

            link_names = outer_names[:]
            link_names.extend(inner_names)
            link_name = link_names[0]

            # TODO is this necessary? It seems like it might be desirable
            #   to ensure that each link has only one outer/inner name
            if len(outer_names) > 0:
                canonical_name = outer_names[0]
            elif len(inner_names) > 0:
                canonical_name = inner_names[0]
            else:
                raise Exception(f'no defined inner or outer names for link {link}')

            if link_name not in links:
                links[link_name] = Edge(symbol=link_name)
            edge = links[link_name]
            links[link_name] = Edge
            for port in link['ports']:
                node = nodes[port['node_id']]
                edge.link(node)
                node.link(edge)
                # nodes[port['node_id']].link(canonical_name)

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


class Bigraph():
    def __init__(self, nodes, places, links):
        self.nodes = nodes
        self.places = places
        self.links = links

    def fold(self):
        sites = []
        roots = []
        edges = []
        inner_names = []
        outer_names = []
        for over, under in self.places:
            self.nodes[over].nest(self.nodes[under])
        for node in self.nodes.values():
            if node.is_site():
                sites.append(node)
            if not node.supernode:
                roots.append(node)
        for symbol, link in self.links.items():
            edge = Edge(symbol=symbol, nodes=[
                self.nodes[node]
                for node in link])
            for node in edge.nodes:
                node.link(edge)
            edges.append(edge)
        


class Control(Base):
    def __init__(
            self,
            symbol=None,
            arity=0,
            atomic=False,
            fun=()):
        self.symbol = symbol
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
        render = f'ctrl {self.symbol}{params} = {self.arity}'
        if self.fun:
            render = f'fun {render}'
        if self.atomic:
            render = f'atomic {render}'

        return render


class Edge(Base):
    def __init__(self, symbol=None, nodes=None):
        self.symbol = symbol
        self.nodes = nodes or []
        for node in self.nodes:
            self.link(node)

    def is_empty(self):
        return self.symbol is None or self.symbol == ''

    def link(self, node):
        self.nodes.append(node)

    def find_edges(self):
        return {
            self.symbol: self}

    def render(self):
        return self.symbol


class EdgeGroup(Base):
    # TODO: link all edges together?

    def __init__(self, edges=None):
        edges = edges or []
        if len(edges) > 0 and isinstance(edges[0], str):
            edges = [
                Edge(symbol=edge) for edge in edges]
        self.edges = edges

    def link(self, edge):
        self.edges.append(edge)

    def find_edges(self):
        return {
            edge.symbol: edge
            for edge in self.edges}

    def find_empty_index(self):
        for index, edge in enumerate(self.edges):
            if edge.is_empty():
                return index
        return -1

    def render(self, parent=False):
        if len(self.edges) > 0:
            if isinstance(self.edges[0], str):
                import ipdb; ipdb.set_trace()
            render = ','.join([edge.symbol for edge in self.edges])
            return '{' + render + '}'
        else:
            return ''


class Id(Base):
    def render(self, parent=None):
        return 'id'

    def is_site(self):
        return True


class One(Base):
    def render(self, parent=None):
        return '1'


class Node(Base):
    def __init__(
            self,
            control=None,
            ports=None,
            params=None,
            subnodes=None):

        ''' create a bigraphical node 

        Args:
            control: instance of Control describing this node's ports
            ports: a list of edges into this node. initialized to a list
                containing `None` for range(arity) if arg is `None`
            subnodes: TODO
        '''

        self.control = control or Control()
        self.params = params
        ports = ports or []
        if isinstance(ports, list):
            ports = EdgeGroup(edges=ports)
        self.ports = ports
        self.subnodes = subnodes

    def find_edges(self):
        found = {}
        for subnode in self.subnodes:
            subedges = subnode.find_edges()
            for symbol, edge in subedges.items():
                if symbol in found:
                    found[symbol].combine()
            found.merge()
        found.merge(self.ports.find_edges())
        return found

    def find_sites(self):
        return len([
            subnode
            for subnode in self.subnodes
            if subnode.is_site])

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

    def symbol(self):
        return self.control.symbol or 'id'

    def arity(self):
        return self.control.arity

    def link(self, edge):
        self.ports.link(edge)
        # index = self.ports.find_empty_index()
        # # index = none_index(self.ports.edges)

        # if index == -1:
        #     raise Exception(
        #         'cannot link name {name}, all ports have already been named for this node: {self.render()}')

        # self.ports.edges[index] = Edge(name)

    def nest(self, subnode):
        if self.subnodes:
            self.subnodes.merge(subnode)
        else:
            self.subnodes = subnode
        subnode.join(self)
        return self

    def render(self, parent=False):
        render = self.symbol()
        arity = self.arity()

        if self.params:
            params = ','.join([str(param) for param in self.params])
            params = f'({params})'
            render = f'{render}{params}'

        if arity > 0:
            names = self.ports.render()
            render = f'{render}{names}'

        if self.subnodes:
            subnode = self.subnodes.render(parent=True)
            render = f'{render}.{subnode}'

        return render


id_node = Id()


class Parallel(Base):
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


class Merge(Base):
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


class InGroup(Base):
    def __init__(
            self,
            control='',
            target='param',
            negate=False):
        self.control = control
        self.target = target
        self.negate = negate

    def render(self):
        render = f'{self.control.render()} in {self.target}'
        if self.negate:
            render = f'!{render}'
        return render


class Condition(Base):
    def __init__(
            self,
            groups):
        self.groups = groups

    def render(self):
        groups = ', '.join([group.render() for group in self.groups])
        return f'if {groups}'


class Reaction(Base):
    def __init__(
            self,
            symbol=None,
            params=(),
            redex=None,
            arrow=(),
            reactum=None,
            instantiation=None,
            condition=None):

        self.symbol = symbol
        self.params = params
        self.redex = redex
        self.arrow = arrow
        self.reactum = reactum
        self.instantiation = instantiation
        self.condition = condition

    def render(self, indent=0, parent=False):
        block = ''.join([' ' for _ in range(indent)])
        params = ','.join(self.params)
        params = f'({params})' if params else ''
        arrow_params = ','.join([str(arrow) for arrow in self.arrow])
        rate = f'[{arrow_params}]' if arrow_params else ''
        arrow = f'-{rate}->'
        render = f'react {self.symbol}{params} = \n{block}{self.redex.render()}\n{block}{arrow}\n{block}{self.reactum.render()}'
        if self.params:
            render = f'fun {render}'
        if self.instantiation:
            instantiation = ','.join([str(instant) for instant in self.instantiation])
            instantiation = f'[{instantiation}]'
            render = f'{render}\n{block}@{instantiation}'
        if self.condition:
            render = f'{render}\n{block}{self.condition.render()}'
        return render


class Big(Base):
    def __init__(self, symbol, root):
        self.symbol = symbol
        self.root = root

    def render(self):
        return f'big {self.symbol} = {self.root.render()}'


class Range(Base):
    def __init__(
            self,
            start='nil',
            step='il',
            stop='nil'):
        self.start = start
        self.step = step
        self.stop = stop
        
    def render(self):
        return f'[{self.start}:{self.step}:{self.stop}]'


class Assign(Base):
    def __init__(
            self,
            assign_type='nil',
            symbol='il',
            value='nil'):
        self.assign_type = assign_type
        self.symbol = symbol
        self.value = value
        
    def render(self):
        render = str(self.value)
        if isinstance(self.value, Range):
            render = self.value.render()
        elif isinstance(self.value, list):
            render = ','.join(self.value)
            render = '{' + render + '}'
        return f'{self.assign_type} {self.symbol} = {render}'


class Init(Base):
    def __init__(
            self,
            symbol=None):
        self.symbol = symbol

    def render(self):
        return f'init {self.symbol}'


class Param(Base):
    def __init__(
            self,
            symbol=None,
            params=()):
        self.symbol = symbol
        self.params = params

    def render(self):
        params = ','.join([
            param.render() if isinstance(param, Base) else str(param)
            for param in self.params])
        return f'{self.symbol}({params})'


class RuleGroup(Base):
    def __init__(
            self,
            deterministic=True,
            rules=()):
        self.deterministic = deterministic
        self.rules = rules
    
    def render(self):
        render = ','.join([
            rule.render() if isinstance(rule, Base) else rule
            for rule in self.rules])
        if self.deterministic:
            render = f'({render})'
        else:
            render = '{' + render + '}'
        return render


class Rules(Base):
    def __init__(
            self,
            rule_groups=()):
        self.rule_groups = rule_groups

    def render(self):
        rules = ',\n        '.join([
            group.render()
            for group in self.rule_groups])
        render = f'rules = [\n        {rules}\n    ]'
        return render


class Preds(Base):
    def __init__(
            self,
            rules=()):
        self.rules = rules

    def render(self):
        return f'preds = {self.rules.render()}'


class System(Base):
    def __init__(
            self,
            system_type='brs',
            init=None,
            bindings=(),
            rules=None,
            preds=()):

        self.system_type = system_type
        self.init = init
        self.bindings = bindings
        self.rules = rules or Rules(rule_groups=[])
        self.preds = preds
        
    def render(self):
        render = f'begin {self.system_type}\n'
        init = self.init.render() if self.init else ''
        bindings = ';\n'.join([
            '    ' + binding.render()
            for binding in self.bindings]) + ';\n' if self.bindings else ''
        rules = self.rules.render()
        preds = self.preds.render() + ';\n' if self.preds else ''
        render = f'begin {self.system_type}\n{bindings}    {init};\n    {rules};\n    {preds}end\n'
        return render


class BigraphicalReactiveSystem(Base):
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
        self.controls['1'] = Control(symbol='1')
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
        state = Base.from_spec(spec['state'])
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
                    root = Base.from_spec(state)
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
        controls = '\n'.join([
            f'{control.render()};'
            for symbol, control in self.controls.items()
            if symbol != '1'])

        reactions = '\n'.join([
            f'{reaction.render(indent=4)};\n'
            for symbol, reaction in self.reactions.items()])

        bigraphs = '\n'.join([
            f'{bigraph.render()};'
            for symbol, bigraph in self.bigraphs.items()])

        declarations = '\n\n'.join([controls, reactions, bigraphs])

        system = self.system.render() if self.system else ''

        big = '\n\n'.join([declarations, system])
        return big


def test_bigraphs(
        executable='../bigraph-tools/_build/default/bigrapher/src/bigrapher.exe'):

    ctrl = {
        'A': Control(symbol='A', arity=1),
        'A\'': Control(symbol='A\'', arity=1),
        'Mail': Control(symbol='Mail'),
        'M': Control(symbol='M', atomic=True, arity=2),
        'Snd': Control(symbol='Snd'),
        'Ready': Control(symbol='Ready'),
        'New': Control(symbol='New'),
        'Fun': Control(symbol='Fun'),
        '1': Control(symbol='1')}

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
        'a0': Big(symbol='a0', root=a0),
        'a1': Big(symbol='a1', root=a1),

        's0': Big(symbol='s0', root=Merge([
            a0,
            a1,
            Node(ctrl['Mail']).nest(
                Node(ctrl['1']))])),

        'phi': Big(symbol='phi', root=Node(ctrl['Mail']).nest(
            Merge([
                Node(ctrl['M'], ['a', 'v']),
                id_node])))}

    reactions = {
        'snd': Reaction(
            symbol='snd',
            redex=Merge([
                Node(ctrl['A'], ['a0']).nest(
                    Node(ctrl['Snd']).nest(
                        Merge([
                            Node(ctrl['M'], ['a1', 'v']),
                            id_node]))),
                Node(ctrl['Mail'])]),
            reactum=Merge([
                Node(ctrl['A'], ['a0']),
                Node(ctrl['Mail']).nest(
                    Merge([
                        Node(ctrl['M'], ['a1', 'v']),
                        id_node]))])),

        'ready': Reaction(
            symbol='ready',
            redex=Merge([
                Node(ctrl['A'], ['a']).nest(
                    Node(ctrl['Ready'])),
                Node(ctrl['Mail']).nest(
                    Merge([
                        Node(ctrl['M'], ['a', 'v']),
                        id_node]))]),
            reactum=Merge([
                Node(ctrl['A'], ['a']),
                Node(ctrl['Mail']),
                EdgeGroup([Edge('v')])])),

        'lambda': Reaction(
            symbol='lambda',
            redex=Node(ctrl['A'], ['a']).nest(
                Node(ctrl['Fun'])),
            reactum=Node(ctrl['A'], ['a'])),

        'new': Reaction(
            symbol='new',
            redex=Node(ctrl['A'], ['a0']).nest(
                Merge([
                    Node(ctrl['New']).nest(
                        Merge([
                            Node(ctrl['A\''], ['a1']),
                            id_node])),
                    id_node])),
            reactum=Merge([
                Node(ctrl['A'], ['a0']).nest(
                    Merge([id_node, id_node])),
                Node(ctrl['A'], ['a1']).nest(
                    Merge([id_node, id_node]))]),
            instantiation=[1, 2, 0, 2])}
            
    init = Init(symbol='s0')
    rules = Rules(rule_groups=[
        RuleGroup(
            deterministic=False,
            rules=['snd', 'ready', 'lambda', 'new'])])
    preds = Preds(rules=RuleGroup(
        deterministic=False,
        rules=['phi']))
    bindings = []

    system = System(
        system_type='brs',
        bindings=bindings,
        init=init,
        rules=rules,
        preds=preds)

    reactive_system = BigraphicalReactiveSystem(
        controls=ctrl,
        bigraphs=bigraphs,
        reactions=reactions,
        system=system,
        executable=executable,
        path='out/test/execute')

    result = reactive_system.simulate(
       format='json',
       console=True)

       # format='svg',
       # console=True)

    print(reactive_system.render())
    print('\n\n\n')
    print('TRANSITIONS:')
    for transition in result:
        print(transition.render())


if __name__ == '__main__':
    fire.Fire(test_bigraphs)
