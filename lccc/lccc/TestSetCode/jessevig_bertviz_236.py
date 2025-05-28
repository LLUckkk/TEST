import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import torch
import torch.nn as nn


#############change###########
def prune_linear_layer(layer, index, dim=0):
    index = index.to(layer.weight.device)
    W = layer.weight.index_select(dim, index).clone().detach()
    if layer.bias is not None:
        if dim == 1:
            b = layer.bias.clone().detach()
        else:
            b = layer.bias[index].clone().detach()
    new_size = list(layer.weight.size())
    new_size[dim] = len(index)
    new_layer = nn.Linear(new_size[1], new_size[0], bias=layer.bias is not None).to(layer.weight.device)
    new_layer.weight.requires_grad = False
    new_layer.weight.copy_(W.contiguous())
    new_layer.weight.requires_grad = True
    if layer.bias is not None:
        new_layer.bias.requires_grad = False
        new_layer.bias.copy_(b.contiguous())
        new_layer.bias.requires_grad = True
    return new_layer


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
    layer = nn.Linear(10, 20)
    index = torch.tensor([0, 2, 4, 6, 8])
    dim = 0

    return prune_linear_layer(layer, index, dim)


# 定义测试用例2
def testcase_2():
    layer = nn.Linear(15, 30)
    index = torch.tensor([1, 3, 5, 7, 9, 11, 13])
    dim = 1

    return prune_linear_layer(layer, index, dim)


# 定义测试用例3
def testcase_3():
    layer = nn.Linear(25, 50)
    index = torch.tensor([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])
    dim = 0

    return prune_linear_layer(layer, index, dim)


# 定义测试用例4
def testcase_4():
    layer = nn.Linear(8, 16)
    index = torch.tensor([2, 4, 6])
    dim = 1

    return prune_linear_layer(layer, index, dim)


# 定义测试用例5
def testcase_5():
    layer = nn.Linear(12, 24)
    index = torch.tensor([0, 3, 6, 9])
    dim = 0

    return prune_linear_layer(layer, index, dim)


def main():
    # 执行所有测试用例
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    def json_serializable(obj):
        if isinstance(obj, (str, int, float, bool)) or obj is None:
            return obj
        elif isinstance(obj, (list, tuple, set)):
            return [json_serializable(item) for item in obj]
        elif isinstance(obj, dict):
            return {json_serializable(k): json_serializable(v) for k, v in obj.items()}
        elif hasattr(obj, "__dict__"):
            result = {}
            for k, v in obj.__dict__.items():
                # 过滤掉函数和可调用对象
                if not callable(v) and not k.startswith('__'):
                    try:
                        result[k] = json_serializable(v)
                    except Exception:
                        # 万一递归出错，用字符串兜底
                        result[k] = str(v)
            return result
        else:
            # 其他类型用字符串兜底
            return str(obj)

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
