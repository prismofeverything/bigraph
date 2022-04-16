import fire
from parsimonious.grammar import Grammar
from parsimonious.nodes import NodeVisitor

from bigraph import Bigraph, Control, Node, Edge, Parallel, Merge, Reaction


examples = {
    'nothing': '',
    'control': 'Aaa',
    'edge': 'Aa{bbb}',
    'edges': 'Aa{bbb, ccc, ddd}',
    'multiple-comments': "##yellow \n\n\n#what \n\nAa{bbb}\n#okay",
    'simple-control': 'ctrl B = 0',
    'atomic-fun-control': 'atomic fun ctrl B(m,n,o) = 0',
    'atomic-controls-comments': '#atomic\natomic ctrl B = 0;\n#other\n#atomic\natomic ctrl C = 3;#yes\n',
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


big = Grammar(
    """
    big_source = (comment_expression semicolon? newline? comment?)*
    comment_expression = comment* control_expression
    
    control_expression = control_declare / expression
    control_declare = atomic? fun? ctrl control_invoke equals number
    control_invoke = control_label control_params?
    control_params = paren_left edge_commas paren_right

    expression = group / merge / parallel / bigraph
    merge = bigraph (merge_pipe bigraph)+
    parallel = bigraph (parallel_pipe bigraph)+
    bigraph = group / nest / control
    group = paren_left expression paren_right
    nest = control (dot bigraph)+
    control = control_label edge_group?
    control_label = control_start name_tail
    edge_group = edge_brace_left edge_name additional_edge* edge_brace_right
    edge_commas = edge_name additional_edge*
    additional_edge = comma edge_name
    edge_name = edge_start name_tail

    atomic = "atomic" ws
    fun = "fun" ws
    ctrl = "ctrl" ws
    equals = ws "=" ws
    comment = octothorpe not_newline newline?
    octothorpe = "#"
    number = digit+ (dot digit+)?
    digit = ~r"[0-9]"
    control_start = ~r"[A-Z0-9]"
    edge_start = ~r"[a-z]"
    edge_brace_left = "{"
    edge_brace_right = "}"
    merge_pipe = ws "|" ws
    parallel_pipe = ws "||" ws
    paren_left = "("
    paren_right = ")"
    comma = "," ws
    dot = "."
    semicolon = ws ";" ws
    name_tail = ~r"[-_'A-Za-z]"*
    not_newline = ~r"[^\\n\\r]"*
    newline = ~"[\\n\\r]+"
    ws = ~"\s*"
    """)


class BigVisitor(NodeVisitor):
    def visit_big_source(self, node, visit):
        expressions = [
            node['visit'][0]
            for node in visit]
        return expressions

    def visit_comment_expression(self, node, visit):
        return visit[1]

    def visit_control_expression(self, node, visit):
        return visit[0]

    def visit_control_declare(self, node, visit):
        atomic = bool(visit[0]['visit'])
        fun = bool(visit[1]['visit'])
        control = visit[3]['visit']
        label = control[0]
        params = control[1]['visit']
        if params:
            params = params[0]
        arity = visit[5]

        return Control(
            label=label,
            arity=arity,
            atomic=atomic,
            fun=tuple(params))

    def visit_atomic(self, node, visit):
        return node.text

    def visit_fun(self, node, visit):
        return node.text

    def visit_control_params(self, node, visit):
        params = [visit[1]['visit'][0]]
        tail = visit[1]['visit'][1]['visit']
        params.extend(tail)
        return params

    def visit_number(self, node, visit):
        return node.text

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
        control_label = visit[0]
        edge_names = visit[1]['visit']
        if len(edge_names) > 0:
            edge_names = edge_names[0]

        return Node(
            Control(
                label=control_label,
                arity=len(edge_names)),
            edge_names)

    def visit_control_label(self, node, visit):
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

    def generic_visit(self, node, visit):
        return {
            'node': node,
            'visit': visit}


def parse_expression(expression):
    parse = big.parse(expression)
    visitor = BigVisitor()
    bigraphs = visitor.visit(parse)

    return bigraphs, parse


def parse_big(path):
    with open(path, 'r') as big:
        source = big.read()

    bigraphs, parse = parse_expression(source)
    return bigraphs


if __name__ == '__main__':
    for key, example in examples.items():
        bigraphs, parse = parse_expression(example)

        print(f'{key}: {example}')
        if bigraphs:
            for bigraph in bigraphs:
                print(bigraph.render())

    psd_fifo = parse_big('examples/big/PSD_FIFO_ctrl.big')
    for bigraph in psd_fifo:
        print(bigraph.render())

