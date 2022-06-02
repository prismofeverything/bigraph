from bigraph.bigraph import Base, Bigraph, BigraphicalReactiveSystem
from bigraph.parse import bigraph

class Metabolism(Base):
    def __init__(self):
        self.controls = {
            'A': bigraph('ctrl A = 0'),
            'B': bigraph('ctrl B = 0'),
            'F': bigraph('ctrl F = 0'),
            'Phi': bigraph('ctrl Phi = 0')}

        self.reactions = {
            'f': bigraph("""
                react f =
                    A | A.F
                    -->
                    A.(F | B)"""),
            'b': bigraph("""
                react b =
                    A.(B | F)
                    -->
                    A.(B | Phi)"""),
            'phi': bigraph("""
                react phi =
                    A.(Phi | B)
                    -->
                    A.(Phi | F)"""),
            'degrade_F': bigraph("""
                react degrade_F =
                    A.F
                    -->
                    A"""),
            'degrade_B': bigraph("""
                react degrade_B =
                    A.B
                    -->
                    A"""),
            'degrade_Phi': bigraph("""
                react degrade_Phi =
                    A.Phi
                    -->
                    A""")}

        self.bigraphs = {
            'initial': bigraph("""
                big initial = A | A | A | A | A | A.F""")}

        self.system = bigraph("""
            begin sbrs
                init initial;
                rules = [
                    {f,b,phi,degrade_F,degrade_B,degrade_Phi}
                ];
            end""")

        self.brs = BigraphicalReactiveSystem(
            controls=self.controls,
            bigraphs=self.bigraphs,
            reactions=self.reactions,
            system=self.system)


def test_metabolism():
    metabolism = Metabolism()
    print(metabolism.brs.render())


if __name__ == '__main__':
    test_metabolism()
