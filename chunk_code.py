import ast
import networkx as nx
from typing import List

# === 1. Build dependency graph ===
class DependencyGraphBuilder(ast.NodeVisitor):
    def __init__(self):
        self.graph = nx.DiGraph()
        self.current_function = None

    def visit_FunctionDef(self, node):
        self.current_function = node.name
        self.graph.add_node(node.name)
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name) and self.current_function:
            self.graph.add_edge(self.current_function, node.func.id)
        self.generic_visit(node)

# === 2. Split large functions at control flow blocks ===
def split_large_function(node: ast.FunctionDef, source: str, max_lines: int = 50) -> List[str]:
    code = ast.get_source_segment(source, node)
    lines = code.splitlines()
    if len(lines) <= max_lines:
        return [code]

    chunks, buffer = [], []
    for line in lines:
        buffer.append(line)
        if line.strip().startswith(('if ', 'for ', 'while ', 'try', 'except', 'def ')) and len(buffer) >= max_lines:
            chunks.append("\n".join(buffer))
            buffer = []
    if buffer:
        chunks.append("\n".join(buffer))
    return chunks

# === 3. Extract connected function groups ===
def chunk_code(source: str) -> List[str]:
    tree = ast.parse(source)
    builder = DependencyGraphBuilder()
    builder.visit(tree)
    graph = builder.graph

    # Map name → node
    func_nodes = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}

    # Group by strongly connected components (functions that reference each other)
    clusters = list(nx.strongly_connected_components(graph))
    chunks = []

    for cluster in clusters:
        full_code = ""
        for func_name in cluster:
            node = func_nodes.get(func_name)
            if node:
                full_code += ast.get_source_segment(source, node) + "\n\n"

        if len(full_code.splitlines()) > 100:
            # Split cluster into smaller chunks
            for func_name in cluster:
                node = func_nodes.get(func_name)
                if node:
                    chunks.extend(split_large_function(node, source))
        else:
            chunks.append(full_code.strip())

    # Handle global (non-function) code
    global_code = ""
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            global_code += ast.get_source_segment(source, node) + "\n\n"

    if global_code.strip():
        chunks.insert(0, global_code.strip())  # Add to beginning

    # Fallback
    if not chunks:
        chunks = [source.strip()]

    # --- New: Split chunks that exceed token limit ---
    MAX_TOKENS = 4000
    APPROX_CHARS_PER_TOKEN = 4  # Approximate chars per token

    def split_large_chunk_by_token(chunk: str, max_tokens=MAX_TOKENS):
        max_chars = max_tokens * APPROX_CHARS_PER_TOKEN
        lines = chunk.splitlines()
        small_chunks = []
        buffer = []
        buffer_len = 0

        for line in lines:
            line_len = len(line) + 1  # Include newline
            if buffer_len + line_len > max_chars and buffer:
                small_chunks.append("\n".join(buffer))
                buffer = [line]
                buffer_len = line_len
            else:
                buffer.append(line)
                buffer_len += line_len

        if buffer:
            small_chunks.append("\n".join(buffer))
        return small_chunks

    final_chunks = []
    for c in chunks:
        if len(c) > MAX_TOKENS * APPROX_CHARS_PER_TOKEN:
            final_chunks.extend(split_large_chunk_by_token(c))
        else:
            final_chunks.append(c)

    return final_chunks
