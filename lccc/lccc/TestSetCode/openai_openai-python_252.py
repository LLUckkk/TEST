import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import urllib.parse
from typing import Any, Dict, Union, Optional, List, Tuple

ArrayFormat = str  # 比如 'brackets', 'indices', 'repeat'
NestedFormat = str  # 比如 'brackets', 'dot'，这里简单处理


def urlencode(params: List[Tuple[str, Any]]) -> str:
    """简单封装 urllib 的 urlencode"""
    return urllib.parse.urlencode(params, doseq=True)


def stringify_items(
        self,
        params: Dict[str, Any],
        array_format: Optional[ArrayFormat] = None,
        nested_format: Optional[NestedFormat] = None,
        prefix: Optional[str] = None
) -> List[Tuple[str, Any]]:
    """递归展开字典成键值对"""
    items = []
    for key, value in params.items():
        full_key = f"{prefix}.{key}" if (prefix and nested_format == 'dot') else \
            (f"{prefix}[{key}]" if prefix else key)

        if isinstance(value, dict):
            items.extend(
                stringify_items(self, value, array_format=array_format, nested_format=nested_format, prefix=full_key)
            )
        elif isinstance(value, list):
            if array_format == 'brackets':
                for v in value:
                    items.append((f"{full_key}[]", v))
            elif array_format == 'indices':
                for idx, v in enumerate(value):
                    items.append((f"{full_key}[{idx}]", v))
            elif array_format == 'repeat':
                for v in value:
                    items.append((full_key, v))
            else:  # 默认处理
                for v in value:
                    items.append((full_key, v))
        else:
            items.append((full_key, value))
    return items


#############change###########
def stringify(
        self,
        params: Dict[str, Any],
        *,
        array_format: Optional[ArrayFormat] = None,
        nested_format: Optional[NestedFormat] = None,
) -> str:
    return urlencode(
        stringify_items(
            self,
            params,
            array_format=array_format,
            nested_format=nested_format,
        )
    )


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
    class Dummy:
        pass

    self = Dummy()
    params: Dict[str, Any] = {"name": "Alice", "age": 30, "active": True}

    return stringify(self, params, array_format='brackets', nested_format='brackets')


# 定义测试用例2
def testcase_2():
    class Dummy:
        pass

    self = Dummy()
    params: Dict[str, Any] = {"search": {"query": "openai", "page": 2}}

    return stringify(self, params, array_format='repeat', nested_format='dot')


# 定义测试用例3
def testcase_3():
    class Dummy:
        pass

    self = Dummy()
    params: Dict[str, Any] = {"filters": {"category": ["books", "electronics"], "price": {"min": 10, "max": 100}}}

    return stringify(self, params, array_format='indices', nested_format='brackets')


# 定义测试用例4
def testcase_4():
    class Dummy:
        pass

    self = Dummy()
    params: Dict[str, Any] = {"user": {"id": 123, "preferences": {"newsletter": False, "notifications": True}}}

    return stringify(self, params, array_format='repeat', nested_format='dot')


# 定义测试用例5
def testcase_5():
    class Dummy:
        pass

    self = Dummy()
    params: Dict[str, Any] = {"order": {"items": [{"id": 1, "quantity": 2}, {"id": 2, "quantity": 1}], "total": 59.99}}

    return stringify(self, params, array_format='brackets', nested_format='brackets')


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

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
