"""Dizo 网表分析工具库"""
import datalens


def load_netlist(netlist_path):
    """加载 Verilog 网表，返回 (project, top_module)"""
    datalens.exchange.load_netlist([netlist_path])
    p = datalens.design.present_project()
    p.make_unique()
    return p, p.present_module()


def get_single_file(netlist_dir, keyword):
    """从目录中获取包含 keyword 的第一个 .v 文件"""
    import os
    for f in sorted(os.listdir(netlist_dir)):
        if keyword in f.lower() and f.endswith('.v'):
            return os.path.join(netlist_dir, f)
    return None


def _iter_all_leaf(top):
    """遍历所有模块的所有非层级实例"""
    for module in datalens.design.module_iter():
        for inst in module.inst_iter(False):
            yield inst


def count_by_ref(top):
    """按 ref_name 统计所有实例，返回 {ref_name: count}"""
    counts = {}
    for inst in _iter_all_leaf(top):
        ref = inst.ref_name
        counts[ref] = counts.get(ref, 0) + 1
    return counts


def get_inst_degrees(top):
    """返回每个实例的 pin 数列表"""
    return [sum(1 for _ in inst.pin_iter()) for inst in _iter_all_leaf(top)]


def get_net_fanouts(top):
    """返回每条 net 的 pin 数列表"""
    return [sum(1 for _ in net.pin_iter()) for net in top.net_iter()]


def get_top_fanout_nets(top, top_n=10):
    """返回高扇出 net 列表 [(name, fanout), ...]"""
    fanouts = {}
    for net in top.net_iter():
        fanouts[net.name] = sum(1 for _ in net.pin_iter())
    return sorted(fanouts.items(), key=lambda x: -x[1])[:top_n]


SEQ_PREFIXES = ('DFF', 'SDFF', 'DLAT', 'SEDFF', 'RSDFF')


def classify_seq_comb(top):
    """区分时序/组合，返回 (seq_insts, comb_insts)"""
    seq, comb = [], []
    for inst in _iter_all_leaf(top):
        ref = inst.ref_name
        (seq if any(ref.startswith(p) for p in SEQ_PREFIXES) else comb).append(inst)
    return seq, comb


def get_cell_categories(top, top_n=None):
    """按功能类别分组统计，返回 {category: count}"""
    from collections import defaultdict
    cats = defaultdict(int)
    for inst in _iter_all_leaf(top):
        base = inst.ref_name.split('_')[0].rstrip('0123456789X')
        cats[base] += 1
    sorted_cats = sorted(cats.items(), key=lambda x: -x[1])
    if top_n:
        sorted_cats = sorted_cats[:top_n]
    return dict(sorted_cats)


def get_inst_degrees_with_ref(top):
    """一次遍历获取 degree 列表 + 按 ref 分组的 degree 列表"""
    degrees = []
    ref_deg = {}
    for inst in _iter_all_leaf(top):
        d = sum(1 for _ in inst.pin_iter())
        degrees.append(d)
        ref = inst.ref_name
        ref_deg.setdefault(ref, []).append(d)
    return degrees, ref_deg
