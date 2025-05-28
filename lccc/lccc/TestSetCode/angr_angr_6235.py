import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests


#############change###########
def get_unambiguous_name(self, display_name: str | None = None) -> str:
    must_disambiguate_by_addr = self.binary is not self.project.loader.main_object and self.binary_name is None

    if not must_disambiguate_by_addr:
        for func in self._function_manager.get_by_name(self.name):
            if func is not self and func.binary is self.binary:
                must_disambiguate_by_addr = True
                break

    separator = "::"
    n = separator
    if must_disambiguate_by_addr:
        n += hex(self.addr) + separator
    elif self.binary is not self.project.loader.main_object:
        n += self.binary_name + separator
    return n + (display_name or self.name)


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


# 通用 Dummy 构造函数
def make_dummy(name="func", binary_is_main=True, binary_name=None, addr=0x400123):
    class Dummy:
        def __init__(self):
            self.name = name
            self.addr = addr
            self.binary_name = binary_name
            self.binary = object()  # just a unique object
            self.project = type("Project", (), {
                "loader": type("Loader", (), {
                    "main_object": object() if binary_is_main else object()
                })()
            })()
            self._function_manager = type("FunctionManager", (), {
                "get_by_name": lambda s, n: [] if n != name else [self]
            })()

    return Dummy()


# 修改后的测试用例
def testcase_1():
    self = make_dummy(name="main_function")
    return get_unambiguous_name(self, display_name="main_function")


def testcase_2():
    self = make_dummy(name="unnamed_func")
    return get_unambiguous_name(self, display_name=None)


def testcase_3():
    self = make_dummy(name="helper", binary_name="libhelper.so", binary_is_main=False)
    return get_unambiguous_name(self, display_name="helper_function")


def testcase_4():
    self = make_dummy(name="init_func", addr=0x401000)
    return get_unambiguous_name(self, display_name="init_function")


def testcase_5():
    self = make_dummy(name="processor", binary_is_main=False, binary_name="libprocessor.so")
    return get_unambiguous_name(self, display_name="process_data")


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
