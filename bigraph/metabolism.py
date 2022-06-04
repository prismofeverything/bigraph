from bigraph.bigraph import Base, Bigraph, Merge, BigraphicalReactiveSystem, react, apply_reactions
from bigraph.parse import bigraph

class Metabolism(Base):
    def __init__(self, path='.'):
        self.controls = {
            'A': bigraph('ctrl A = 0'),
            'B': bigraph('ctrl B = 0'),
            'F': bigraph('ctrl F = 0'),
            'Phi': bigraph('ctrl Phi = 0')}

        self.reactions = {
            'f': bigraph("""
                react f =
                    A | A.(F | id)
                    -->
                    A.(B | F | id)"""),
            'b': bigraph("""
                react b =
                    A.(B | F | id)
                    -->
                    A.(B | Phi | id)"""),
            'phi': bigraph("""
                react phi =
                    A.(Phi | B | id)
                    -->
                    A.(Phi | F | id)"""),
            'degrade_F': bigraph("""
                react degrade_F =
                    A.(F | id)
                    -->
                    A.(B | id)"""),
            'degrade_B': bigraph("""
                react degrade_B =
                    A.(B | id)
                    -->
                    A | A.id"""),
            'degrade_Phi': bigraph("""
                react degrade_Phi =
                    A.(Phi | id)
                    -->
                    A.(F | id)"""),
            'divide': bigraph("""
                react divide =
                    A.(F | F | Phi | Phi | B | B | B | id)
                    -->
                    A.(F | Phi | B | id) | A.(F | Phi | B)
                    @[0,2,4,7,1,3,5];
                """),
            'b_f': bigraph("""
                react b_f =
                    B | B.(F | id)
                    -->
                    B.(B | F | id)"""),
            'b_b': bigraph("""
                react b_b =
                    B.(B | F | id)
                    -->
                    B.(B | Phi | id)"""),
            'b_phi': bigraph("""
                react b_phi =
                    B.(Phi | B | id)
                    -->
                    B.(Phi | F | id)"""),
            'b_degrade_F': bigraph("""
                react b_degrade_F =
                    B.(F | id)
                    -->
                    B.(B | id)"""),
            'b_degrade_B': bigraph("""
                react b_degrade_B =
                    B.(B | id)
                    -->
                    B | B.id"""),
            'b_degrade_Phi': bigraph("""
                react b_degrade_Phi =
                    B.(Phi | id)
                    -->
                    B.(F | id)"""),
            'b_divide': bigraph("""
                react b_divide =
                    B.(F | F | Phi | Phi | B | B | B | id)
                    -->
                    B.(F | Phi | B | id) | B.(F | Phi | B)
                    @[0,2,4,7,1,3,5];
                """)}

        # optimal transitions
        #   "A | A | A.F"
        #   "A | A.(B | F)"
        #   "A | A.(Phi | B)"
        #   "A | A.(F | Phi)"
        #   "A.(F | Phi | B)"

        def initial_state(n):
            m = bigraph('F | Phi | B')
            a = Merge([bigraph('A') for _ in range(n - 1)])
            a.parts[-1].nest(m)
            return a

        self.bigraphs = {
            'initial': bigraph(f"""
                big initial = {initial_state(34)}""")}

        self.system = bigraph("""
            begin brs
                init initial;
                rules = [
                    {divide,b_divide},
                    {f,b,phi,degrade_F,degrade_B,degrade_Phi,
                     b_f,b_b,b_phi,b_degrade_F,b_degrade_B,b_degrade_Phi}
                ];
            end""")

        self.brs = BigraphicalReactiveSystem(
            controls=self.controls,
            bigraphs=self.bigraphs,
            reactions=self.reactions,
            system=self.system,
            path=path)


def test_metabolism():
    metabolism = Metabolism()
    # print(metabolism.brs.render())
    
    initial = metabolism.bigraphs['initial'].root
    F = metabolism.reactions['f']
    B = metabolism.reactions['b']
    Phi = metabolism.reactions['phi']
    divide = metabolism.reactions['divide']
    Sf = metabolism.reactions['degrade_F']
    Sb = metabolism.reactions['degrade_B']
    Sphi = metabolism.reactions['degrade_Phi']

    # script = [
    #     F, B, Phi, F, B, Phi, F, Phi, F, F, F,
    #     divide,
    #     Sf, Sphi, Sb, Sf, Sb, Sphi, Sf, Sb, Sb, Sb]

    # results = apply_reactions(script, initial)

    # print(f'script: {[reaction.symbol for reaction in script]}')
    # for result in results:
    #     print(result)

    while True:
        results = metabolism.brs.simulate(
            key='metabolism',
            path='out/test/metabolism',
            # console=True,
            steps=987)

        # print('\nsimulation:')
        print('\n')
        for result in results:
            print(result)
        

if __name__ == '__main__':
    test_metabolism()


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
