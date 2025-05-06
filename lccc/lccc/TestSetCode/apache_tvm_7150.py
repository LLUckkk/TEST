import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import torch
import re
import itertools


def _get_uses(node):
    """获取某个节点的所有 uses"""
    uses = []
    for output in node.outputs():
        uses.extend(output.uses())
    return uses


def get_node_by_op(graph, op_name):
    """从 graph 中获取第一个 op_name 类型的 node"""
    for node in graph.nodes():
        if node.kind() == op_name:
            return node
    raise ValueError(f"No node with op type '{op_name}' found.")


#############change###########
def _get_users(node):
    return [use.user for use in _get_uses(node)]


#############change###########


@contextmanager
def request_context():
    """确保requests会话被正确关闭的上下文管理器"""
    session = requests.Session()
    try:
        yield session
    finally:
        session.close()


def safe_execute_testcase(testcase_func, timeout):
    """完全解决线程残留问题的执行器"""
    result_queue = queue.Queue()
    event = threading.Event()  # 线程协调事件

    def worker():
        try:
            with request_context() as session:
                # 将session传递给测试函数（如果需要）
                if 'session' in testcase_func.__code__.co_varnames:
                    result = testcase_func(session=session)
                else:
                    result = testcase_func()

                if not event.is_set():
                    result_queue.put(('success', result))
        except Exception as e:
            print(e)
            if not event.is_set():
                result_queue.put(('error', e))
        finally:
            event.set()  # 标记线程已完成

    t = threading.Thread(target=worker)
    t.daemon = True  # 必须设置为守护线程

    start_time = time.time()
    t.start()

    # 等待线程完成或超时
    while time.time() - start_time < timeout:
        if event.is_set() or not result_queue.empty():
            break
        time.sleep(0.1)

    event.set()  # 通知线程终止

    if not result_queue.empty():
        status, data = result_queue.get_nowait()
        return {
            'success': status == 'success',
            'result': data if status == 'success' else None,
            'error': None if status == 'success' else str(data),
            'traceback': traceback.format_exc() if status == 'error' else None
        }

    return {
        'success': False,
        'error': f'Timeout after {timeout} seconds',
        'traceback': 'Test execution timed out'
    }


# 定义测试用例1
def testcase_1():
    class MyModule(torch.nn.Module):
        def forward(self, x, y):
            return x + y

    scripted = torch.jit.script(MyModule())
    graph = scripted.forward.graph
    node = get_node_by_op(graph, "aten::add")
    return _get_users(node)


# 定义测试用例2
def testcase_2():
    class MyModule(torch.nn.Module):
        def forward(self, x, y):
            return x * y

    scripted = torch.jit.script(MyModule())
    graph = scripted.forward.graph
    node = get_node_by_op(graph, "aten::mul")
    return _get_users(node)


# 定义测试用例3
def testcase_3():
    class MyModule(torch.nn.Module):
        def forward(self, x, y):
            return x - y

    scripted = torch.jit.script(MyModule())
    graph = scripted.forward.graph
    node = get_node_by_op(graph, "aten::sub")
    return _get_users(node)


# 定义测试用例4
def testcase_4():
    class MyModule(torch.nn.Module):
        def forward(self, x):
            return x + 3  # 常量 3 会变成 prim::Constant

    scripted = torch.jit.script(MyModule())
    graph = scripted.forward.graph
    node = get_node_by_op(graph, "prim::Constant")
    return _get_users(node)


# 定义测试用例5
def testcase_5():
    class MyModule(torch.nn.Module):
        def forward(self, x):
            return torch.relu(x)

    scripted = torch.jit.script(MyModule())
    graph = scripted.forward.graph
    node = get_node_by_op(graph, "aten::relu")
    return _get_users(node)


def main():
    # 执行所有测试用例
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    def serialize(obj):
        """将 PyTorch JIT Node 等复杂对象转换为可 JSON 序列化的形式"""
        if isinstance(obj, torch._C.Node):
            return {
                "kind": obj.kind(),
                "inputs": [inp.debugName() for inp in obj.inputs()],
                "outputs": [out.debugName() for out in obj.outputs()],
                "scope": obj.scopeName()
            }
        elif isinstance(obj, list):
            return [serialize(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: serialize(value) for key, value in obj.items()}
        elif isinstance(obj, (str, int, float, type(None))):
            return obj
        else:
            return str(obj)  # fallback：转换为字符串

    output = {
        "ans1": test_results["ans1"]["result"] if test_results["ans1"]["success"] else None,
        "ans2": test_results["ans2"]["result"] if test_results["ans2"]["success"] else None,
        "ans3": test_results["ans3"]["result"] if test_results["ans3"]["success"] else None,
        "ans4": test_results["ans4"]["result"] if test_results["ans4"]["success"] else None,
        "ans5": test_results["ans5"]["result"] if test_results["ans5"]["success"] else None
    }

    with open('output.json', 'w', encoding='utf-8') as f:
        json.dump(serialize(output), f, indent=2)


if __name__ == '__main__':
    main()
