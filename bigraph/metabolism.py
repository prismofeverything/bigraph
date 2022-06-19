import itertools
import fire

from bigraph.bigraph import Base, Bigraph, Merge, BigraphicalReactiveSystem, react, apply_reactions
from bigraph.parse import bigraph


def partition(items, predicate=bool):
    a, b = itertools.tee((predicate(item), item) for item in items)
    return (tuple(item for pred, item in a if not pred),
            tuple(item for pred, item in b if pred))


class Metabolism(Base):
    def __init__(self, path='.'):
        self.controls = {
            # 'A': bigraph('ctrl A = 0'),
            'B': bigraph('ctrl B = 0'),
            'F': bigraph('ctrl F = 0'),
            'Phi': bigraph('ctrl Phi = 0')}

        self.reactions = {}
        for control in self.controls.keys():
            control_reactions = {
                f'fB_{control}': bigraph(f"""
                    react fB_{control} =
                        B | {control}.(F | id)
                        -->
                        {control}.(F | B | id)@[1, 0, 2]"""),
                f'fF_{control}': bigraph(f"""
                    react fF_{control} =
                        F | {control}.(F | id)
                        -->
                        {control}.(F | F | id)@[1, 0, 2]"""),
                f'fPhi_{control}': bigraph(f"""
                    react fPhi_{control} =
                        Phi | {control}.(F | id)
                        -->
                        {control}.(F | Phi | id)@[1, 0, 2]"""),
                f'b': bigraph(f"""
                    react b =
                        B | F
                        -->
                        B | Phi"""),
                f'phi': bigraph(f"""
                    react phi =
                        Phi | B
                        -->
                        Phi | F"""),
                f'degrade_F': bigraph(f"""
                    react degrade_F =
                        F
                        -->
                        B"""),
                f'degrade_B_{control}': bigraph(f"""
                    react degrade_B_{control} =
                        {control}.(B | id)
                        -->
                        B | {control}.id"""),
                # f'degrade_F_{control}': bigraph(f"""
                #     react degrade_F_{control} =
                #         {control}.(F | id)
                #         -->
                #         F | {control}.id"""),
                # f'degrade_Phi_{control}': bigraph(f"""
                #     react degrade_Phi_{control} =
                #         {control}.(Phi | id)
                #         -->
                #         Phi | {control}.id"""),
                f'degrade_Phi': bigraph(f"""
                    react degrade_Phi =
                        Phi
                        -->
                        F"""),
                f'divide_{control}': bigraph(f"""
                    react divide_{control} =
                        {control}.(F | F | Phi | Phi | B | B | B | id)
                        -->
                        {control}.(F | Phi | B | id) | B.(F | Phi | B | id)
                        @[0, 2, 4, 7, 1, 3, 6, 5]
                    """)}

            self.reactions.update(control_reactions)

        def initial_state(n):
            m = bigraph('F | Phi | B')
            internal = len(m.parts)
            a = Merge([bigraph('B') for _ in range(n - internal)])
            a.parts[-1].nest(m)
            return a

        self.bigraphs = {
            'initial': bigraph(f"""
                big initial = {initial_state(21)}""")}

        reaction_keys, divide_keys = partition(
            self.reactions.keys(),
            lambda x: x.startswith('divide'))

        self.system = bigraph("""
            begin brs
                init initial;
                rules = [
                ];
            end""")

        self.system.rules.add(divide_keys)
        self.system.rules.add(reaction_keys)

        self.brs = BigraphicalReactiveSystem(
            controls=self.controls,
            bigraphs=self.bigraphs,
            reactions=self.reactions,
            system=self.system,
            path=path)


def test_metabolism():
    metabolism = Metabolism()
    results = metabolism.brs.simulate(
        key='metabolism',
        path='out/test/metabolism',
        # console=True,
        steps=987)

    # print('\nsimulation:')
    print('\n')
    for result in results:
        print(result)
    

def run_metabolism(
        above=43,
        steps=8888):
    metabolism = Metabolism()

    # script = [
    #     F, B, Phi, F, B, Phi, F, Phi, F, F, F,
    #     divide,
    #     Sf, Sphi, Sb, Sf, Sb, Sphi, Sf, Sb, Sb, Sb]

    # results = apply_reactions(script, initial)

    # print(f'script: {[reaction.symbol for reaction in script]}')
    # for result in results:
    #     print(result)

    running = True
    while running:
        results = metabolism.brs.simulate(
            key='metabolism',
            path='out/test/metabolism',
            # console=True,
            steps=steps)

        if len(results) > above:
            print('\n')
            for result in results:
                print(result)

        # print(f'steps: {len(results)}')
        # running = False
        

if __name__ == '__main__':
    fire.Fire(run_metabolism)


# first division (!)
# A | A | A | A | A | A | A.F
# A | A | A | A | A | A.(F | B)
# A | A | A | A | A | A.(B | Phi)
# A | A | A | A | A | A.(F | B)
# A | A | A | A | A | A.(B | Phi)
# A | A | A | A | A | A.(Phi | F)
# A | A | A | A | A | A.(B | Phi)
# A | A | A | A | A | A.(F | B)
# A | A | A | A | A | A | A.F
# A | A | A | A | A | A.(F | B)
# A | A | A | A | A | A.(B | Phi)
# A | A | A | A | A | A | A.Phi
# A | A | A | A | A | A | A.F
# A | A | A | A | A | A.(F | B)
# A | A | A | A | A.(F | B | B)
# A | A | A | A | A.(B | Phi | B)
# A | A | A | A | A.(F | B | B)
# A | A | A | A | A.(B | Phi | B)
# A | A | A | A | A | A.(B | Phi)
# A | A | A | A | A | A.(Phi | F)
# A | A | A | A | A.(F | B | Phi)
# A | A | A | A | A.(Phi | F | F)
# A | A | A | A.(F | B | Phi | F)
# A | A | A | A.(B | Phi | F | Phi)
# A | A | A | A.(B | Phi | Phi | Phi)
# A | A | A | A.(F | B | Phi | Phi)
# A | A | A | A | A.(F | Phi | Phi)
# A | A | A | A | A.(B | Phi | Phi)
# A | A | A | A | A.(F | B | Phi)
# A | A | A | A.(F | B | B | Phi)
# A | A | A | A.(B | Phi | B | Phi)
# A | A | A | A.(F | B | Phi | B)
# A | A | A | A.(F | F | B | B)
# A | A | A | A.(B | Phi | F | B)
# A | A | A | A.(B | B | Phi | B)
# A | A | A | A | A.(B | B | Phi)
# A | A | A | A | A.(Phi | F | B)
# A | A | A | A | A.(Phi | F | F)
# A | A | A | A | A.(B | Phi | F)
# A | A | A | A | A.(Phi | F | F)
# A | A | A | A.(F | B | Phi | F)
# A | A | A.(F | B | F | B | Phi)
# A | A | A.(Phi | F | F | B | F)
# A | A.(F | B | Phi | F | F | B)
# A.(F | B | F | B | Phi | F | B)
# A.(Phi | F | F | B | F | B | F)
# A.(F | F | F | B | F | B | F)
# A.(B | Phi | F | F | F | B | F)
# A.(B | Phi | B | Phi | F | F | F)
# A.(B | B | Phi | B | Phi | F | F)
# A.(F | Phi | B) | A.(F | Phi | B)
# A.(F | Phi | B) | A.(F | F | B)
# A.(F | F | B) | A.(B | Phi | B)
# A.(F.(B | Phi | B) | B | F | B)
# A.(B | Phi | F.(B | Phi | B) | B)
# A.(F | B | F.(B | Phi | B) | B)
# A | A.(F | B | F.(B | Phi | B))
# A.(F | B.(B | Phi | B) | F | B)
# A.(B | F | B.(B | Phi | B) | B)
# A.(B | Phi | B | B.(B | Phi | B))
# A.(B | Phi | B) | A.(B | Phi | B)
# A.(B | Phi | B) | A.(F | B | B)
# A.(B | Phi | B) | A | A.(F | B)
# A | A.(F | B) | A.(Phi | F | B)
# A | A.(Phi | F | B) | A.(B | Phi)
# A | A.(Phi | F | B) | A.(F | B)
# A | A.(F | B) | A | A.(Phi | F)
# A | A | A.(Phi | F) | A | A.F
# A | A | A | A.(F.F | B | Phi)
# A | A | A | A.(B.F | B | Phi)
# A | A | A | A.F | A.(B | Phi)
# A | A | A | A.F | A | A.Phi
# A | A | A | A.F | A | A.F
# A | A | A | A | A.(F.F | B)
# A | A | A | A | A | A.F.F
# A | A | A | A | A | A.B.F
# A | A | A | A | A | A.F | A
# A | A | A | A | A | A.(F | B)
# A | A | A | A | A | A.(B | B)
# A | A | A | A | A | A | A.B
# A | A | A | A | A | A | A | A

