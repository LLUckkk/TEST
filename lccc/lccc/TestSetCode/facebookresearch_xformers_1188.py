import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import torch
from typing import List


def tensor_to_list(obj):
    if isinstance(obj, torch.Tensor):
        return obj.tolist()
    elif isinstance(obj, list):
        return [tensor_to_list(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: tensor_to_list(v) for k, v in obj.items()}
    else:
        return obj


def _unflatten(flat: List[torch.Tensor], outer_len: int, inner_len: int) -> List[List[torch.Tensor]]:
    return [flat[i * inner_len:(i + 1) * inner_len] for i in range(outer_len)]


def _flatten(nested: List[List[torch.Tensor]], outer_len: int, inner_len: int) -> List[torch.Tensor]:
    return [nested[i][j] for i in range(outer_len) for j in range(inner_len)]


def tiled_matmul_out(a: List[List[torch.Tensor]], b: List[List[torch.Tensor]], out: List[List[torch.Tensor]]):
    for i in range(len(a)):
        for j in range(len(b[0])):
            out[i][j].zero_()
            for k in range(len(a[0])):
                out[i][j] += a[i][k] @ b[k][j]


#############change###########
def tiled_matmul_fwd(
        flat_a: List[torch.Tensor],
        flat_b: List[torch.Tensor],
        ms: List[int],
        ns: List[int],
        ks: List[int],
) -> List[torch.Tensor]:
    a = _unflatten(flat_a, len(ms), len(ks))
    b = _unflatten(flat_b, len(ks), len(ns))

    c = [[a[0][0].new_empty((m, n)) for n in ns] for m in ms]
    tiled_matmul_out(a, b, out=c)

    return _flatten(c, len(ms), len(ns))


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
    flat_a = [torch.randn(2, 3), torch.randn(2, 3)]
    flat_b = [torch.randn(3, 4), torch.randn(3, 4)]
    ms = [2]
    ns = [4]
    ks = [3]

    return tiled_matmul_fwd(flat_a, flat_b, ms, ns, ks, )


# 定义测试用例2
def testcase_2():
    flat_a = [torch.randn(5, 6), torch.randn(5, 6), torch.randn(5, 6)]
    flat_b = [torch.randn(6, 7), torch.randn(6, 7), torch.randn(6, 7)]
    ms = [5]
    ns = [7]
    ks = [6]

    return tiled_matmul_fwd(flat_a, flat_b, ms, ns, ks, )


# 定义测试用例3
def testcase_3():
    flat_a = [torch.randn(8, 9), torch.randn(8, 9)]
    flat_b = [torch.randn(9, 10), torch.randn(9, 10)]
    ms = [8]
    ns = [10]
    ks = [9]

    return tiled_matmul_fwd(flat_a, flat_b, ms, ns, ks, )


# 定义测试用例4
def testcase_4():
    flat_a = [torch.randn(3, 4), torch.randn(3, 4), torch.randn(3, 4), torch.randn(3, 4)]
    flat_b = [torch.randn(4, 5), torch.randn(4, 5), torch.randn(4, 5), torch.randn(4, 5)]
    ms = [3]
    ns = [5]
    ks = [4]

    return tiled_matmul_fwd(flat_a, flat_b, ms, ns, ks, )


# 定义测试用例5
def testcase_5():
    flat_a = [torch.randn(6, 7), torch.randn(6, 7)]
    flat_b = [torch.randn(7, 8), torch.randn(7, 8)]
    ms = [6]
    ns = [8]
    ks = [7]

    return tiled_matmul_fwd(flat_a, flat_b, ms, ns, ks, )


def main():
    # 执行所有测试用例
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    output = {
        "ans1": test_results["ans1"]["result"] if test_results["ans1"]["success"] else None,
        "ans2": test_results["ans2"]["result"] if test_results["ans2"]["success"] else None,
        "ans3": test_results["ans3"]["result"] if test_results["ans3"]["success"] else None,
        "ans4": test_results["ans4"]["result"] if test_results["ans4"]["success"] else None,
        "ans5": test_results["ans5"]["result"] if test_results["ans5"]["success"] else None
    }

    output = tensor_to_list(output)

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
