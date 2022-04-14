import fire
from parsimonious.grammar import Grammar
from parsimonious.nodes import NodeVisitor

from bigraph import Bigraph, Control, Edge, Parallel, Merge, Reaction

examples = {
    'control': 'Aaa',
    'edge': 'Aa{bbb}',
    'edges': 'Aa{bbb, ccc, ddd}',
    'nest': 'Aa.Bb.Ccc',
    'merge': 'A | B | C',
    'parallel': 'A || B || C',
    'merge-nest': 'A.B | C.D',
    'nest-edge': 'A.B{b, c}',
    'nest-merge': 'A.(B | C) | D',
    'nest-merge-edge': 'A{a}.(B | C{c, d})',
    'edge-merge': '(M{a, v_a} | Ready.Fun.1)',
    'partial': 'A{a}.Snd.(M{a, v_a} | Ready.Fun.1)',
    'full': 'A{a}.Snd.(M{a, v_a} | Ready.Fun.1) | A{b}.Snd.M{a, v_b} | Mail.1'}


    # nest = control (period expression)+
big = Grammar(
    """
    expression = group / merge / parallel / bigraph
    merge = bigraph (merge_pipe bigraph)+
    parallel = bigraph (parallel_pipe bigraph)+
    bigraph = group / nest / control
    group = paren_left expression paren_right
    nest = control (period bigraph)+
    control = control_name edge_group?
    control_name = control_start name_tail
    control_start = ~r"[A-Z0-9]"
    edge_group = edge_brace_left edge_name additional_edge* edge_brace_right
    additional_edge = comma edge_name
    edge_name = edge_start name_tail
    edge_start = ~r"[a-z]"
    edge_brace_left = "{"
    edge_brace_right = "}"
    merge_pipe = ws "|" ws
    parallel_pipe = ws "||" ws
    paren_left = "("
    paren_right = ")"
    comma = "," ws
    period = "."
    name_tail = ~r"[-_'A-Za-z]"*
    ws = ~"\s*"
    """)


class BigVisitor(NodeVisitor):
    def visit_expression(self, node, visit):
        return visit[0]

    def visit_bigraph(self, node, visit):
        return visit[0]

    def visit_merge(self, node, visit):
        merge = [visit[0]]
        tail_nodes = visit[1]['visit']
        tail = [
            node['visit'][1]
            for node in tail_nodes]
        merge.extend(tail)
        return Merge(merge)

    def visit_parallel(self, node, visit):
        parallel = [visit[0]]
        tail_nodes = visit[1]['visit']
        tail = [
            node['visit'][1]
            for node in tail_nodes]
        parallel.extend(tail)
        return Parallel(parallel)

    def visit_group(self, node, visit):
        return visit[1]

    def visit_nest(self, node, visit):
        root = visit[0]
        child = visit[1]['visit'][0]['visit'][1]
        root.nest(child)
        return root

    def visit_control(self, node, visit):
        control_name = visit[0]
        edge_names = visit[1]['visit']
        if len(edge_names) > 0:
            edge_names = edge_names[0]

        return Control(
            {visit[0]: len(edge_names)},
            edge_names)

    def visit_control_name(self, node, visit):
        return node.text

    def visit_edge_group(self, node, visit):
        edge_names = [visit[1]]
        additional_edges = visit[2]['visit']
        edge_names.extend(additional_edges)

        return edge_names

    def visit_additional_edge(self, node, visit):
        return visit[1]

    def visit_edge_name(self, node, visit):
        return node.text

    def visit_merge_pipe(self, node, visit):
        return ''

    def visit_parallel_pipe(self, node, visit):
        return ''

    def visit_comma(self, node, visit):
        return ''

    def visit_ws(self, node, visit):
        return ''

    def generic_visit(self, node, visit):
        return {
            'node': node,
            'visit': visit}


def parse_big(expression):
    parse = big.parse(expression)
    visitor = BigVisitor()
    bigraph = visitor.visit(parse)

    return bigraph, parse


if __name__ == '__main__':
    for key, example in examples.items():
        bigraph, parse = parse_big(example)

        print(f'{key}: {example}')
        # print(parse)
        print(bigraph.render())

