import copy
import json

def none_str(v, none):
    if v is None:
        return none
    else:
        return str(v)

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
        return list(self.control.keys())[0]

    def arity(self):
        return list(self.control.values())[0]

    def nest(self, inner):
        self.sites = inner
        return self

    def render(self):
        render = self.label()
        arity = self.arity()
        if arity > 0:
            names = ', '.join([
                none_str(port, '{}')
                for port in self.ports])
            names = '{' + names + '}'
            render = f'{render}{names}'
        if self.sites:
            inner = self.sites.render()
            render = f'{render}.{inner}'
        return render

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

    def render(self):
        rate = '[ ' + str(self.rate) + ' ]' if self.rate else ''
        arrow = '-{rate}->'
        render = self.match.render() + '\n' + arrow + '\n' + self.result.render()
        if self.instantiation:
            render = render + '\n@ ' + str(self.instantiation)
        return render

class BigraphicalReactiveSystem():
    def __init__(
            self,
            controls=None,
            bigraphs=None,
            reactions=None,
            system=None):
        self.controls = controls or {}
        self.bigraphs = bigraphs or {}
        self.reactions = reactions or {}
        self.system = system


def test_bigraphs():
    controls = {
        'A': 1,
        'A\'': 1,
        'Mail': 0,
        'M': {'atomic': True, 'ports': 2},
        'Snd': 0,
        'Ready': 0,
        'New': 0,
        'Fun': 0}

    bigraphs = {
        'a0': Node({'A': 1}, ['a']).nest(
            Node({'Snd': 0}).nest(
                Merge([
                    Node({'M': 2}, ['a', 'v_a']),
                    Node({'Ready': 0}).nest(
                        Node({'Fun': 0}).nest(
                            Node({'1': 0})))]))),

        'a1': Node({'A': 1}, ['b']).nest(
            Node({'Snd': 0}).nest(
                Node({'M': 2}, ['a', 'v_b']))),

        's0': Merge([
            a0,
            a1,
            Node({'Mail': 0}).nest(
                Node({'1': 0}))]),

        'phi': Node({'Mail': 0}).nest(
            Merge([
                Node({'M': 2}, ['a', 'v']),
                id_node]))}

    reactions = {
        'snd': Reaction(
            Merge([
                Node({'A': 1}, ['a0']).nest(
                    Node({'Snd': 0}).nest(
                        Merge([
                            Node({'M': 2}, ['a1', 'v']),
                            id_node]))),
                id_node]),
            Merge([
                Node({'A': 1}, ['a0']),
                Node({'Mail': 0}).nest(
                    Merge([
                        Node({'M': 2}, ['a1', 'v']),
                        id_node]))]))

        }
            

    print(f'a0: {a0.render()}')
    print(f'a1: {a1.render()}')
    print(f's0: {s0.render()}')
    print(f'phi: {phi.render()}')


if __name__ == '__main__':
    test_bigraphs()
