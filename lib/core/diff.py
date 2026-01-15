"""
Graph diff utilities.

Computes semantic differences between two NetworkX graphs.
"""
import networkx as nx


def diff_graphs(old_graph: nx.MultiDiGraph, new_graph: nx.MultiDiGraph) -> list[str]:
    """
    Compute semantic diff between two graphs.

    Returns list of diff lines:
    - add node <id> <attr>=<val> ...
    - remove node <id>
    - set node <id> <attr>=<val> ...
    - add edge <src> -> <dst> <label> <attr>=<val> ...
    - remove edge <src> -> <dst> <label>
    - set edge <src> -> <dst> <label> <attr>=<val> ...

    Args:
        old_graph: Previous state graph
        new_graph: Current state graph

    Returns:
        List of diff lines (no header, just operations)
    """
    lines = []

    old_nodes = set(old_graph.nodes())
    new_nodes = set(new_graph.nodes())

    # Nodes added
    for node in sorted(new_nodes - old_nodes):
        attrs = _format_attrs(new_graph.nodes[node])
        lines.append(f"add node {node} {attrs}")

    # Nodes removed
    for node in sorted(old_nodes - new_nodes):
        lines.append(f"remove node {node}")

    # Nodes changed (exist in both, check attrs)
    for node in sorted(old_nodes & new_nodes):
        changed = _diff_attrs(old_graph.nodes[node], new_graph.nodes[node])
        if changed:
            lines.append(f"set node {node} {changed}")

    # Edges: identify by (src, dst, label)
    old_edges = _edge_map(old_graph)
    new_edges = _edge_map(new_graph)

    old_keys = set(old_edges.keys())
    new_keys = set(new_edges.keys())

    # Edges added
    for key in sorted(new_keys - old_keys):
        src, dst, label = key
        attrs = _format_attrs(new_edges[key], exclude={"label"})
        suffix = f" {attrs}" if attrs else ""
        lines.append(f"add edge {src} -> {dst} {label}{suffix}")

    # Edges removed
    for key in sorted(old_keys - new_keys):
        src, dst, label = key
        lines.append(f"remove edge {src} -> {dst} {label}")

    # Edges changed
    for key in sorted(old_keys & new_keys):
        src, dst, label = key
        changed = _diff_attrs(old_edges[key], new_edges[key], exclude={"label"})
        if changed:
            lines.append(f"set edge {src} -> {dst} {label} {changed}")

    return lines


def _edge_map(G: nx.MultiDiGraph) -> dict[tuple[str, str, str], dict]:
    """Map (src, dst, label) -> edge data dict."""
    edges = {}
    for u, v, key, data in G.edges(keys=True, data=True):
        # Prefer action_type for action edges, then label, then key
        label = _clean(data.get("action_type") or data.get("label") or key)
        edges[(u, v, label)] = data
    return edges


def _format_attrs(attrs: dict, exclude: set = None) -> str:
    """Format attributes as key=value pairs."""
    exclude = exclude or set()
    parts = [f"{k}={_clean(v)}" for k, v in sorted(attrs.items()) if k not in exclude]
    return " ".join(parts)


def _diff_attrs(old: dict, new: dict, exclude: set = None) -> str:
    """Return changed attributes as key=value pairs, empty string if unchanged."""
    exclude = exclude or set()
    all_keys = (set(old.keys()) | set(new.keys())) - exclude
    changed = []
    for k in sorted(all_keys):
        old_val = _clean(old.get(k))
        new_val = _clean(new.get(k))
        if old_val != new_val:
            changed.append(f"{k}={new_val}")
    return " ".join(changed)


def _clean(val) -> str:
    """Strip quotes from string values."""
    if val is None:
        return "None"
    if isinstance(val, str):
        return val.strip('"')
    return str(val)
