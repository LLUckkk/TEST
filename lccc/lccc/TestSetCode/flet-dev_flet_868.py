import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import typing
from typing import List


class Control:
    def __init__(self, uid, children=None):
        self.__uid = uid
        self.children = children or []

    def _get_children(self) -> List["Control"]:
        return self.children

    def to_dict(self):
        return {
            "uid": self.__uid,
            "children": [child.to_dict() for child in self.children]
        }


#############change###########
def _get_children(self) -> "List[Control]":
    return []


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
# 定义测试用例1：两层结构
def testcase_1():
    grandchild1 = Control("grandchild1")
    grandchild2 = Control("grandchild2")
    child1 = Control("child1", children=[grandchild1])
    child2 = Control("child2", children=[grandchild2])
    parent = Control("parent1", children=[child1, child2])
    return [c.to_dict() for c in parent._get_children()]


# 定义测试用例2：一层结构（两个 child，没有 children）
def testcase_2():
    child1 = Control("child1")
    child2 = Control("child2")
    parent = Control("parent2", children=[child1, child2])
    return [c.to_dict() for c in parent._get_children()]


# 定义测试用例3：单个 child，有一个 grandchild
def testcase_3():
    grandchild = Control("grandchild")
    child = Control("child", children=[grandchild])
    parent = Control("parent3", children=[child])
    return [c.to_dict() for c in parent._get_children()]


# 定义测试用例4：三层嵌套结构
def testcase_4():
    ggc = Control("greatgrandchild")
    gc = Control("grandchild", children=[ggc])
    c = Control("child", children=[gc])
    parent = Control("parent4", children=[c])
    return [c.to_dict() for c in parent._get_children()]


# 定义测试用例5：多个 child，没有嵌套
def testcase_5():
    children = [Control(f"child{i}") for i in range(1, 5)]
    parent = Control("parent5", children=children)
    return [c.to_dict() for c in parent._get_children()]


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

    print(json.dumps(output, indent=2, default=lambda o: o.to_dict() if hasattr(o, "to_dict") else str(o)))


if __name__ == '__main__':
    main()
