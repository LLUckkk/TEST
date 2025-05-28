import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import pytest
from typing import Optional


#############change###########
def add(self, role: str, content: str, name: Optional[str] = None) -> "Convo":
    if role not in self.ROLES:
        raise ValueError(f"Unknown role: {role}")
    if not content:
        raise ValueError("Empty message content")
    if not isinstance(content, str) and not isinstance(content, dict):
        raise TypeError(f"Invalid message content: {type(content).__name__}")

    message = {
        "role": role,
        "content": self._dedent(content) if isinstance(content, str) else content,
    }
    if name is not None:
        message["name"] = name

    self.messages.append(message)
    return self


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
    self.ROLES = ["user", "assistant", "system", "function"]
    self.messages = []
    self._dedent = lambda x: x.strip()

    role = "user"
    content = "Hello, how can I help you today?"
    name = "Alice"

    return add(self, role, content, name)


def testcase_2():
    class Dummy:
        pass

    self = Dummy()
    self.ROLES = ["user", "assistant", "system", "function"]
    self.messages = []
    self._dedent = lambda x: x.strip()

    role = "assistant"
    content = {"text": "Sure, I can assist you with that."}
    name = None

    return add(self, role, content, name)


def testcase_3():
    class Dummy:
        pass

    self = Dummy()
    self.ROLES = ["user", "assistant", "system", "function"]
    self.messages = []
    self._dedent = lambda x: x.strip()

    role = "system"
    content = "System initialization complete."
    name = "System"

    return add(self, role, content, name)


def testcase_4():
    class Dummy:
        pass

    self = Dummy()
    self.ROLES = ["user", "assistant", "system", "function"]
    self.messages = []
    self._dedent = lambda x: x.strip()

    role = "function"
    content = "Executing function call."
    name = "FunctionHandler"

    return add(self, role, content, name)


def testcase_5():
    class Dummy:
        pass

    self = Dummy()
    self.ROLES = ["user", "assistant", "system", "function"]
    self.messages = []
    self._dedent = lambda x: x.strip()

    role = "user"
    content = "\n    This is a test message.\n    Please respond.\n"
    name = "Bob"

    return add(self, role, content, name)


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
        "ans1": json_serializable(test_results["ans1"]["result"]) if test_results["ans1"]["success"] else None,
        "ans2": json_serializable(test_results["ans2"]["result"]) if test_results["ans2"]["success"] else None,
        "ans3": json_serializable(test_results["ans3"]["result"]) if test_results["ans3"]["success"] else None,
        "ans4": json_serializable(test_results["ans4"]["result"]) if test_results["ans4"]["success"] else None,
        "ans5": json_serializable(test_results["ans5"]["result"]) if test_results["ans5"]["success"] else None
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
