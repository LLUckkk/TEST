import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

from mlflow import MlflowException
from mlflow.protos.databricks_pb2 import INVALID_PARAMETER_VALUE
from mlflow.recipes.cards import CardTab


class Dummy:
    def __init__(self):
        self._variables = {
            "HTML_1": "valid_variable",
            "SUMMARY": "valid_variable",
            "PROFILE": "valid_variable",
            "MODEL_URI": "valid_variable",
            "DATA_PREVIEW": "valid_variable"
        }
        self._context = {}
        self.template = "default_template"

    def __repr__(self):
        """返回类实例的字符串表示，便于调试"""
        return f"Dummy(template={self.template}, _variables={self._variables}, _context={self._context})"


#############change###########
def add_html(self, name: str, html_content: str) -> CardTab:
    if name not in self._variables:
        raise MlflowException(
            f"{name} is not a valid template variable defined in template: '{self.template}'",
            error_code=INVALID_PARAMETER_VALUE,
        )
    self._context[name] = html_content
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
    self = Dummy()
    name = "HTML_1"
    html_content = "<div><p>This is a test paragraph.</p></div>"

    return add_html(self, name, html_content)


# 定义测试用例2
def testcase_2():
    self = Dummy()
    name = "SUMMARY"
    html_content = "<h1>Summary Report</h1><p>Details of the report go here.</p>"

    return add_html(self, name, html_content)


# 定义测试用例3
def testcase_3():
    self = Dummy()
    name = "PROFILE"
    html_content = "<iframe srcdoc='profile-content' width='100%' height='500' frameborder='0'></iframe>"

    return add_html(self, name, html_content)


# 定义测试用例4
def testcase_4():
    self = Dummy()
    name = "MODEL_URI"
    html_content = "<a href='http://example.com/model'>Model Link</a>"

    return add_html(self, name, html_content)


# 定义测试用例5
def testcase_5():
    self = Dummy()
    name = "DATA_PREVIEW"
    html_content = "<table><tr><td>Data 1</td></tr><tr><td>Data 2</td></tr></table>"

    return add_html(self, name, html_content)


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

    print(json.dumps(output, default=lambda obj: obj.__repr__(), indent=2))


if __name__ == '__main__':
    main()
