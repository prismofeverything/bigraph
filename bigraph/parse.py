import fire
from parsimonious.grammar import Grammar


examples = {
    'control': 'Aaa',
    'nest': 'A.B.C',
    'merge': 'A | B | C',
    'parallel': 'A || B || C',
    'edge': 'A{a}',
    'multi-edge': 'A{a, b}',
    'merge-nest': 'A.B | C.D',
    'nest-edge': 'A.B{b, c}',
    'nest-merge': 'A.(B | C) | D',
    'nest-merge-edge': 'A{a}.(B | C{c, d})',
    'edge-merge': '(M{a, v_a} | Ready.Fun.1)',
    'partial': 'A{a}.Snd.(M{a, v_a} | Ready.Fun.1)',
    'full': 'A{a}.Snd.(M{a, v_a} | Ready.Fun.1) | A{b}.Snd.M{a, v_b} | Mail.1'}


big = Grammar(
    """
    expression = merge / parallel / bigraph
    merge = bigraph (ws "|" ws bigraph)+
    parallel = bigraph (ws "||" ws bigraph)+
    bigraph = group / nest / control
    group = paren_left expression paren_right
    nest = control ("." expression)+
    control = control_start name_tail edge_group?
    control_start = ~r"[A-Z0-9]"
    edge_group = edge_brace_left edge_name (comma edge_name)* edge_brace_right
    edge_name = edge_start name_tail
    edge_start = ~r"[a-z]"
    edge_brace_left = "{"
    edge_brace_right = "}"
    paren_left = "("
    paren_right = ")"
    comma = "," ws
    name_tail = ~r"[-_'A-Za-z]"*
    ws = ~"\s*"
    """)


if __name__ == '__main__':
    for key, example in examples.items():
        print(f'{key}: {example}')
        print(big.parse(example))

