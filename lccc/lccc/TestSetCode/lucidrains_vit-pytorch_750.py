import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager

import requests


def pack(tensors, pattern):
    """
    将一组张量或对象根据 pattern 打包为嵌套结构。

    参数:
        tensors: List[Any] - 要打包的数据项
        pattern: Any - 嵌套结构模式，如 ['a', ['b', 'c']]

    返回:
        打包后的嵌套结构数据
    """

    def _pack_recursive(ptr, pat):
        if isinstance(pat, list):
            result = []
            for subpat in pat:
                item, ptr = _pack_recursive(ptr, subpat)
                result.append(item)
            return result, ptr
        else:
            return ptr[0], ptr[1:]

    packed, _ = _pack_recursive(tensors, pattern)
    return packed


#############change###########
def pack_one(t, pattern):
    return pack([t], pattern)


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
import torch


def testcase_1():
    # 2x3x4 张量，填充确定数值
    t = torch.tensor([[[1, 2, 3, 4],
                       [5, 6, 7, 8],
                       [9, 10, 11, 12]],

                      [[13, 14, 15, 16],
                       [17, 18, 19, 20],
                       [21, 22, 23, 24]]])
    pattern = 'b * d'
    return pack_one(t, pattern)


def testcase_2():
    # 5x6x7 张量，填充简单递增数值
    t = torch.arange(5 * 6 * 7).reshape(5, 6, 7).float()
    pattern = 'b * d'
    return pack_one(t, pattern)


def testcase_3():
    # 8x9x10 张量，填充规律数值
    t = torch.zeros(8, 9, 10)
    for i in range(8):
        for j in range(9):
            for k in range(10):
                t[i, j, k] = i + j / 10 + k / 100
    pattern = 'b * d'
    return pack_one(t, pattern)


def testcase_4():
    # 1x2x3 张量，简单小数
    t = torch.tensor([[[0.1, 0.2, 0.3],
                       [0.4, 0.5, 0.6]]])
    pattern = 'b * d'
    return pack_one(t, pattern)


def testcase_5():
    # 4x5x6 张量，交替1和-1
    t = torch.ones(4, 5, 6)
    for i in range(4):
        for j in range(5):
            for k in range(6):
                if (i + j + k) % 2 == 1:
                    t[i, j, k] = -1
    pattern = 'b * d'
    return pack_one(t, pattern)


def main():
    # 执行所有测试用例
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    def json_serializable(tensor):
        return {
            "shape": tensor.shape,
            "dtype": str(tensor.dtype),
            "data": tensor.tolist()
        }

    output = {
        "ans1": json_serializable(test_results["ans1"]["result"]) if test_results["ans1"]["success"] else None,
        "ans2": json_serializable(test_results["ans2"]["result"]) if test_results["ans2"]["success"] else None,
        "ans3": json_serializable(test_results["ans3"]["result"]) if test_results["ans3"]["success"] else None,
        "ans4": json_serializable(test_results["ans4"]["result"]) if test_results["ans4"]["success"] else None,
        "ans5": json_serializable(test_results["ans5"]["result"]) if test_results["ans5"]["success"] else None
    }

    with open('output.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)


if __name__ == '__main__':
    main()
