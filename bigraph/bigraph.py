import os
import copy
import json
import fire
import subprocess
import networkx as nx
from pathlib import Path
from IPython.display import SVG, HTML, display


AVAILABLE_OUTPUT_FORMATS = ['json', 'svg', 'txt']
PARAMETER_SYMBOLS = 'abcdefghijklmnopqrstuvwxyz'


def show_svg(path):
    display(SVG(filename=path))


def show_svgs(paths):
    display([
        SVG(filename=path)
        for path in paths])


def none_index(seq):
    for index, value in enumerate(seq):
        if value is None:
            return index
    return -1


def merge_links(a, b):
    links = {}
    for key, nodes in a.items():
        if key in b:
            nodes = list(nodes)
            nodes.extend(b[key])
        links[key] = nodes
    for key, nodes in b.items():
        if key not in a:
            links[key] = nodes
    return links


def merge_spec(a, b):
    controls = a.get('controls', {}).copy()
    controls.update(b.get('controls', {}))

    nodes = a.get('nodes', {}).copy()
    nodes.update(b.get('nodes', {}))

    places = a.get('places', {}).copy()
    places.update(b.get('places', {}))

    links = merge_links(a.get('links', {}), b.get('links', {}))

    return {
        'controls': controls,
        'nodes': nodes,
        'places': places,
        'links': links}


def tupleize_spec(original_spec):
    spec = original_spec.copy()
    spec['places'] = {
        key: tuple(value)
        for key, value in spec['places'].items()}

    spec['links'] = {
        key: tuple(value)
        for key, value in spec['links'].items()}

    return spec




class Base():
    def __init__(self):
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
        return False

    def to_spec(self):
        # TODO
        return {}

    def find_edges(self):
        return {}

    def unfold(self, id_generator=None):
        return {
            'controls': {},
            'nodes': {},
            'places': {},
            'links': {}}, []

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
            raise Exception('cannot have a bigraph without at least one root node')

        for nest in place_state['nn']:
            above = nodes[nest['source']]
            below = nodes[nest['target']]
            above.nest(below)

        return root


class SequentialGenerator():
    def __init__(self, initial_count=0):
        self.count = initial_count

    def generate(self):
        new_id = self.count
        self.count += 1
        return new_id


def unfold_spec(roots):
    spec = {}
    id_generator = SequentialGenerator()
    root_ids = []

    if isinstance(roots, Base):
        roots = [roots]

    for root in roots:
        root_spec, root_ids = root.unfold(id_generator)
        spec = merge_spec(spec, root_spec)
        spec = tupleize_spec(spec)
        root_ids.extend(root_ids)

    return spec




class Bigraph():
    def __init__(
            self,
            controls=None,
            nodes=None,
            places=None,
            links=None):
        self.controls_spec = controls or {}
        self.nodes_spec = nodes or {}
        self.places_spec = places or {}
        self.links_spec = links or {}

        self.fold()

    def get_spec(self):
        return {
            'controls': self.controls_spec.copy(),
            'nodes': self.nodes_spec.copy(),
            'places': self.places_spec.copy(),
            'links': self.links_spec.copy()}

    def fold(self):
        controls = {}
        nodes = {}
        links = {}

        sites = []
        roots = []
        inner_names = []
        outer_names = []

        for control, params in self.controls_spec.items():
            controls[control] = Control(**params)

        for node, original_params in self.nodes_spec.items():
            params = original_params.copy()
            control = params.pop('control')
            if not control in controls:
                controls[control] = Control(symbol=control)
            nodes[node] = Node(
                control=controls[control],
                **params)

        for key, subnodes in self.places_spec.items():
            for subnode in subnodes:
                nodes[key].nest(nodes[subnode])

        for symbol, link in self.links_spec.items():
            edge = Edge(
                symbol=symbol,
                nodes=[
                    nodes[node]
                    for node in link])
            for node in edge.nodes:
                node.link(edge)
            links[symbol] = edge
        
        for node in nodes.values():
            if node.is_site():
                sites.append(node)
            if not node.supernode:
                roots.append(node)

        self.roots = roots
        self.sites = sites
        self.controls = controls
        self.nodes = nodes
        self.links = links

        if len(self.roots) > 1:
            self.roots = Merge(self.roots)
        else:
            self.roots = self.roots[0]

        return self.roots

    @classmethod
    def unfold(cls, roots):
        spec = unfold_spec(roots)
        return cls(**spec)


class Control(Base):
    def __init__(
            self,
            symbol=None,
            arity=0,
            atomic=False,
            fun=()):

        super().__init__()
        self.symbol = symbol
        self.arity = arity
        self.atomic = atomic
        self.fun = fun
            
    def get_spec(self):
        return {
            'symbol': self.symbol,
            'arity': self.arity,
            'atomic': self.atomic,
            'fun': self.fun}

    def generate(self, ports, params=None):
        return Node(
            control=self,
            params=params,
            ports=ports)

    def param_index(self, symbol):
        return self.fun.index(symbol)

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
        super().__init__()
        self.symbol = symbol
        self.nodes = nodes or []

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
    def __init__(self, edges=None):
        super().__init__()
        edges = edges or []
        if len(edges) > 0 and isinstance(edges[0], str):
            edges = [
                Edge(symbol=edge) for edge in edges]
        self.edges = edges

    def arity(self):
        return len(self.edges)

    def link(self, edge):
        if isinstance(edge, str):
            edge = Edge(symbol=edge)
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
            render = ','.join([edge.symbol for edge in self.edges])
            return '{' + render + '}'
        else:
            return ''


class One(Base):
    def render(self, parent=None):
        return '1'

    def ground(self):
        return self


class Id(Base):
    def merge(self, node):
        return node

    def render(self, parent=None):
        return 'id'

    def is_site(self):
        return True

    def ground(self):
        return One()


id_node = Id()


class Node(Base):
    def __init__(
            self,
            control=None,
            params=None,
            ports=None,
            subnodes=None):

        ''' create a bigraphical node 

        Args:
            control: instance of Control describing this node's ports
            ports: a list of edges into this node. initialized to a list
                containing `None` for range(arity) if arg is `None`
            subnodes: TODO
        '''

        super().__init__()
        self.control = control or Control()
        self.params = params or []
        missing = len(self.control.fun) - len(self.params)
        if missing > 0:
            self.params.extend([
                None for _ in range(missing)])
        elif missing < 0:
            self.control.fun.extend([
                PARAMETER_SYMBOLS[index]
                for index in range(-missing)])
        ports = ports or []
        if isinstance(ports, (list, tuple)):
            ports = EdgeGroup(edges=ports)
        if self.control.arity < len(ports.edges):
            self.control.arity = len(ports.edges)
        self.ports = ports
        self.subnodes = subnodes

    def get_spec(self):
        return {
            'control': self.control.symbol,
            'params': self.params}

    def unfold(self, id_generator=None):
        id_generator = id_generator or SequentialGenerator()
        id = id_generator.generate()
        if self.subnodes:
            spec, subnode_ids = self.subnodes.unfold(id_generator)
            spec['places'][id] = subnode_ids
        else:
            spec = {
                'controls': {},
                'nodes': {},
                'places': {},
                'links': {}}

        spec['controls'][self.control.symbol] = self.control.get_spec()
        spec['nodes'][id] = self.get_spec()
        for edge in self.ports.edges:
            if edge.symbol not in spec['links']:
                spec['links'][edge.symbol] = []
            spec['links'][edge.symbol].append(id)
        return spec, [id]

    def find_edges(self):
        found = {}
        for subnode in self.subnodes:
            subedges = subnode.find_edges()
            for symbol, edge in subedges.items():
                if symbol in found:
                    found[symbol].combine()
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
        arity = self.ports.arity()
        if self.control.arity > arity:
            arity = self.control.arity
        return arity

    def link(self, edge):
        self.ports.link(edge)
        if self.control.arity < self.ports.arity():
            self.control.arity = self.ports.arity()
        return self

    def assign(self, param, value):
        index = self.control.param_index(param)

        if index >= 0:
            params = list(self.params)
            params[index] = value
            self.params = tuple(params)

        return self

    def nest(self, subnode):
        if self.subnodes:
            self.subnodes = self.subnodes.merge(subnode)
        else:
            self.subnodes = subnode
        subnode.join(self)
        return self

    def ground(self):
        if self.subnodes:
            self.subnodes = self.subnodes.ground()
        else:
            self.subnodes = One()
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


class Parallel(Base):
    def __init__(self, parallel):
        super().__init__()
        self.parallel = parallel or []

    def unfold(self, id_generator=None):
        id_generator = id_generator or SequentialGenerator()
        spec = {}
        subnode_ids = []
        for parallel in self.parallel:
            subspec, ids = parallel.unfold(id_generator)
            spec = merge_spec(spec, subspec)
            subnode_ids.extend(ids)
        return spec, subnode_ids

    def ground(self):
        self.parallel = [
            parallel.ground()
            for parallel in self.parallel]
        return self

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
        super().__init__()
        self.parts = []
        for merge in merges:
            self.merge(merge)

    def unfold(self, id_generator=None):
        id_generator = id_generator or SequentialGenerator()
        spec = {}
        subnode_ids = []
        for parts in self.parts:
            subspec, ids = parts.unfold(id_generator)
            spec = merge_spec(spec, subspec)
            subnode_ids.extend(ids)
        return spec, subnode_ids

    def merge(self, other):
        self.parts.extend(other.get_merge())
        return self

    def ground(self):
        self.parts = [
            parts.ground()
            for parts in self.parts]
        return self

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
        super().__init__()
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
        super().__init__()
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

        super().__init__()
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
        super().__init__()
        self.symbol = symbol
        self.root = root

    def ground(self):
        self.root.ground()

    def render(self):
        return f'big {self.symbol} = {self.root.render()}'


class Range(Base):
    def __init__(
            self,
            start='nil',
            step='il',
            stop='nil'):
        super().__init__()
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
        super().__init__()
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
        super().__init__()
        self.symbol = symbol

    def render(self):
        return f'init {self.symbol}'


class Param(Base):
    def __init__(
            self,
            symbol=None,
            params=()):
        super().__init__()
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
            deterministic=False,
            rules=()):
        super().__init__()
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
        super().__init__()
        self.rule_groups = rule_groups

    def add(self, rule_group):
        if not isinstance(rule_group, Base):
            rule_group = RuleGroup(rules=rule_group)
        self.rule_groups.append(rule_group)

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
        super().__init__()
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

        super().__init__()
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
        render = f'begin {self.system_type}\n{bindings}    {init};\n    {rules};'
        if self.preds:
            render = f'{render}\n    {self.preds.render()};'
        render = f'{render}\nend\n'
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

        super().__init__()

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

        self.ground_initial()

    @classmethod
    def from_spec(cls, spec):
        state = Base.from_spec(spec['state'])
        return cls(bigraphs=[state])

    def ground_initial(self):
        if self.system and self.bigraphs:
            symbol = self.system.init.symbol
            self.bigraphs[symbol].ground()

    def write(self, path=None, key=None):
        path = path or self.path
        key = key or self.key

        render = self.render()
        big_path = path / f'{key}.big'
        if not os.path.exists(path):
            os.makedirs(path)
        with open(big_path, 'w') as big_file:
            big_file.write(render)

    def subcommand_options(self, subcommand, path, key, steps=None):
        command = [subcommand]
        if subcommand == 'sim':
            command.extend(['-s', '-t', path / key])
            if steps is not None:
                command.extend(['-S', str(steps)])
        elif subcommand == 'validate':
            command.extend(['-s', '-t', path / key])
        return command

    def execute(
            self,
            path=None,
            key=None,
            subcommand='sim',
            format='json',
            steps=None,
            console=False):

        if isinstance(format, str):
            format = (format,)
        for f in format:
            if not f in AVAILABLE_OUTPUT_FORMATS:
                raise Exception(f'output format "{format}" not supported. Available formats are {AVAILABLE_OUTPUT_FORMATS}')

        path = path or self.path
        key = key or self.key

        options = self.subcommand_options(
            subcommand,
            path,
            key,
            steps=steps)

        command = [self.executable]
        command.extend(options)
        command.extend([
            '-f',
            ','.join(format),
            path / f'{key}.big'])

        bigrapher_process = subprocess.Popen(command, stdout=subprocess.PIPE)
        output, error = bigrapher_process.communicate()

        if console:
            print(' '.join([str(token) for token in command]))
            print('\n\n\n')
            print(output)
            print('\n\n\n')
            print(error)
            print('\n\n\n')

    def read(self, path=None, key=None, format='json'):
        path = Path(path or self.path)
        key = key or self.key

        with open(path / f'{key}.json', 'r') as system_file:
            transitions = json.load(system_file)['brs']

        if len(transitions) > 0:
            trajectory = nx.DiGraph()
            for transition in transitions:
                edge = [transition['source'], transition['target']]
                trajectory.add_edge(*edge)
            steps = nx.topological_generations(trajectory)
        else:
            steps = [['0']]

        history = []
        for step in steps:
            for parallel in step:
                if format == 'svg':
                    svg_path = path / f'{parallel}.svg'
                    history.append(svg_path)
                elif format == 'json':
                    with open(path / f'{parallel}.{format}', 'r') as step_file:
                        state = json.load(step_file)
                        root = Base.from_spec(state)
                        history.append(root)
                else:
                    raise Exception(f'format {format} not supported')

        return history

    def html_transitions(self, path=None, key=None):
        transition_paths = self.read(path=path, key=key, format='svg')
        width = 100 // len(transition_paths)
        header = '<div class="row">\n'
        footer = '</div>'
        styles = 'float:left;'
        # styles = 'float:left;margin-right:30px;'
        rows = [
            f'<img src="{path}" style="width:{width}%;{styles}"></img>'
            for path in transition_paths
        ]
        result = header + '\n'.join(rows) + footer
        return result

    def display_transitions(self, path=None, key=None):
        result = self.html_transitions(path=path, key=key)
        return display(HTML(result))

    def simulate(
            self,
            path=None,
            key=None,
            subcommand='sim',
            format=('json', 'svg'),
            steps=None,
            console=False):

        path = Path(path or self.path)
        key = key or self.key

        self.write(path=path, key=key)
        self.execute(
            path=path,
            key=key,
            subcommand=subcommand,
            format=format,
            steps=steps,
            console=console)
        result = self.read(path=path, key=key)

        return result

    def render(self, parent=False):
        controls = '\n'.join([
            f'{control.render()};'
            for symbol, control in self.controls.items()
            if symbol != '1' and symbol != 'id'])

        reactions = '\n'.join([
            f'{reaction.render(indent=4)};\n'
            for symbol, reaction in self.reactions.items()])

        bigraphs = '\n'.join([
            f'{bigraph.render()};'
            for symbol, bigraph in self.bigraphs.items()])

        big = '\n\n'.join([controls, reactions, bigraphs])

        if self.system:
            system = self.system.render()
            big = '\n\n'.join([big, system])

        return big


def visualize_transition(
        index,
        path='out/test/visualize'):

    show_svg(Path(path) / f'{index}.svg')


def visualize(
        big,
        names=PARAMETER_SYMBOLS,
        path='out/test/visualize',
        executable='bigrapher'):

    bigraph = Bigraph.unfold(big)
    bigraphs = {
        names[0]: Big(symbol=names[0], root=bigraph.roots.ground())}

    system = System(
        system_type='brs',
        bindings=[],
        init=Init(symbol=names[0]))

    brs = BigraphicalReactiveSystem(
        controls=bigraph.controls,
        bigraphs=bigraphs,
        system=system,
        executable=executable,
        path=path)

    result = brs.simulate(
        subcommand='sim',
        format=('json','svg'))
    
    visualize_transition(0)

    return result[0]


def react(
        reaction,
        big,
        names=PARAMETER_SYMBOLS,
        path='out/test/react',
        executable='bigrapher'):

    bigraph = Bigraph.unfold(big)
    bigraph_symbol = 'initial'
    bigraphs = {
        bigraph_symbol: Big(symbol=bigraph_symbol, root=bigraph.roots.ground())}

    reactions = {
        reaction.symbol: reaction}

    rules = Rules(
        rule_groups=[
            RuleGroup(
                deterministic=False,
                rules=[reaction.symbol])])

    redex = Bigraph.unfold(reaction.redex)
    reactum = Bigraph.unfold(reaction.reactum)
    controls = bigraph.controls.copy()
    controls.update(redex.controls)
    controls.update(reactum.controls)

    system = System(
        system_type='brs',
        bindings=[],
        init=Init(symbol=bigraph_symbol),
        rules=rules)

    brs = BigraphicalReactiveSystem(
        controls=controls,
        bigraphs=bigraphs,
        reactions=reactions,
        system=system,
        executable=executable,
        path=path)

    result = brs.simulate(
        subcommand='sim',
        format=('json','svg'),
        # console=True,
        steps=0)
    
    return result[1]


def apply_reactions(reactions, initial):
    history = [initial]
    state = initial
    for reaction in reactions:
        state = react(reaction, state)
        history.append(state)
    return history


def test_bigraphical_system(
        executable='bigrapher'):

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

    a0 = Node(ctrl['A'], ports=['a']).nest(
        Node(ctrl['Snd']).nest(
            Merge([
                Node(ctrl['M'], ports=['a', 'v_a']),
                Node(ctrl['Ready']).nest(
                    Node(ctrl['Fun']).nest(
                        Node(ctrl['1'])))])))

    a1 = Node(ctrl['A'], ports=['b']).nest(
        Node(ctrl['Snd']).nest(
            Node(ctrl['M'], ports=['a', 'v_b'])))

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
                Node(ctrl['M'], ports=['a', 'v']),
                id_node])))}

    reactions = {
        'snd': Reaction(
            symbol='snd',
            redex=Merge([
                Node(ctrl['A'], ports=['a0']).nest(
                    Node(ctrl['Snd']).nest(
                        Merge([
                            Node(ctrl['M'], ports=['a1', 'v']),
                            id_node]))),
                Node(ctrl['Mail'])]),
            reactum=Merge([
                Node(ctrl['A'], ports=['a0']),
                Node(ctrl['Mail']).nest(
                    Merge([
                        Node(ctrl['M'], ports=['a1', 'v']),
                        id_node]))])),

        'ready': Reaction(
            symbol='ready',
            redex=Merge([
                Node(ctrl['A'], ports=['a']).nest(
                    Node(ctrl['Ready'])),
                Node(ctrl['Mail']).nest(
                    Merge([
                        Node(ctrl['M'], ports=['a', 'v']),
                        id_node]))]),
            reactum=Merge([
                Node(ctrl['A'], ports=['a']),
                Node(ctrl['Mail']),
                EdgeGroup([Edge('v')])])),

        'lambda': Reaction(
            symbol='lambda',
            redex=Node(ctrl['A'], ports=['a']).nest(
                Node(ctrl['Fun'])),
            reactum=Node(ctrl['A'], ports=['a'])),

        'new': Reaction(
            symbol='new',
            redex=Node(ctrl['A'], ports=['a0']).nest(
                Merge([
                    Node(ctrl['New']).nest(
                        Merge([
                            Node(ctrl['A\''], ports=['a1']),
                            id_node])),
                    id_node])),
            reactum=Merge([
                Node(ctrl['A'], ports=['a0']).nest(
                    Merge([id_node, id_node])),
                Node(ctrl['A'], ports=['a1']).nest(
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

    print(reactive_system.render())
    print('\n\n\n')
    print('TRANSITIONS:')
    for transition in result:
        print(transition.render())


def test_bigraph(
        executable='bigrapher'):

    controls = {
        'A': {
            'symbol': 'A',
            'arity': 1},
        'B': {
            'symbol': 'B',
            'arity': 2,
            'fun': ('x', 'y')}}

    nodes = {
        '1': {
            'control': 'A'},
        '2': {
            'control': 'A'},
        '3': {
            'control': 'B',
            'params': (3, 5)},
        '4': {
            'control': 'B',
            'params': (11, 13)}}

    places = {
        '1': ('2', '4'),
        '2': ('3',)}

    links = {
        'm': ('1', '3'),
        'n': ('2', '3', '4'),
        'o': ('4',)}

    bigraph = Bigraph(
        controls=controls,
        nodes=nodes,
        places=places,
        links=links)

    bigraph.nodes['3'].assign('y', 14)

    transition = visualize(bigraph.roots)

    print('\n\n\n')
    print('TRANSITION:')
    print(transition.render())


def test_all():
    test_bigraphical_system()
    print('\n\n\n')
    test_bigraph()


if __name__ == '__main__':
    fire.Fire(test_all)
