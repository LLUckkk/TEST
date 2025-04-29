import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import yaml
from typing import Any


class TaskProxiedState:
    def __init__(self, task_id: str, proxied: bool):
        self.task_id = task_id
        self.proxied = proxied

    def __repr__(self):
        return f"TaskProxiedState(task_id={self.task_id!r}, proxied={self.proxied!r})"

    def to_dict(self) -> dict:
        return {"id": self.task_id, "proxied": self.proxied}


#############change###########
def from_dict(task_dict: dict[str, Any]) -> "TaskProxiedState":
    if set(task_dict.keys()) != {"id", "proxied"}:
        raise Exception(
            f"Expected 'proxied' and 'id' keys in the task dictionary. Found keys: {task_dict.keys()}"
        )
    if task_dict["proxied"] not in [True, False]:
        raise Exception("Expected 'proxied' key to be a boolean")
    return TaskProxiedState(task_id=task_dict["id"], proxied=task_dict["proxied"])


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
    task_dict_1 = {
        "id": "task_1",
        "proxied": True
    }

    return from_dict(task_dict_1)


# 定义测试用例2
def testcase_2():
    task_dict_2 = {
        "id": "task_2",
        "proxied": False
    }

    return from_dict(task_dict_2)


# 定义测试用例3
def testcase_3():
    task_dict_3 = {
        "id": "task_3",
        "proxied": True
    }

    return from_dict(task_dict_3)


# 定义测试用例4
def testcase_4():
    task_dict_4 = {
        "id": "task_4",
        "proxied": False
    }

    return from_dict(task_dict_4)


# 定义测试用例5
def testcase_5():
    task_dict_5 = {
        "id": "task_5",
        "proxied": True
    }

    return from_dict(task_dict_5)


def main():
    # 执行所有测试用例
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    output = {}
    for key, result in test_results.items():
        if result["success"] and hasattr(result["result"], "to_dict"):
            output[key] = result["result"].to_dict()
        else:
            output[key] = None

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
