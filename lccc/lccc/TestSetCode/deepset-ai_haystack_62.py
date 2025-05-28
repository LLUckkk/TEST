import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import jinja2  # 添加模板引擎
from typing import Dict, Any, Optional


#############change###########
def run(self, template: Optional[str] = None, template_variables: Optional[Dict[str, Any]] = None, **kwargs):
    kwargs = kwargs or {}
    template_variables = template_variables or {}
    template_variables_combined = {**kwargs, **template_variables}
    self._validate_variables(set(template_variables_combined.keys()))

    compiled_template = self.template
    if template is not None:
        compiled_template = self._env.from_string(template)

    result = compiled_template.render(template_variables_combined)
    return {"prompt": result}


#############change###########


@contextmanager
def request_context():
    session = requests.Session()
    try:
        yield session
    finally:
        session.close()


def safe_execute_testcase(testcase_func, timeout):
    result_queue = queue.Queue()
    event = threading.Event()

    def worker():
        try:
            with request_context() as session:
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
            event.set()

    t = threading.Thread(target=worker)
    t.daemon = True
    start_time = time.time()
    t.start()

    while time.time() - start_time < timeout:
        if event.is_set() or not result_queue.empty():
            break
        time.sleep(0.1)

    event.set()

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


# 创建基础Dummy类，包含template和_env
class Dummy:
    def __init__(self):
        self._env = jinja2.Environment()
        self.template = self._env.from_string("{{ greeting }} {{ name }}")

    def _validate_variables(self, keys):
        # 这里只是模拟检查，不报错即可
        pass


# 测试用例定义
def testcase_1():
    self = Dummy()
    template = "Hello, {{ name }}!"
    template_variables = {"name": "Alice"}
    kwargs = {}
    return run(self, template, template_variables, **kwargs)


def testcase_2():
    self = Dummy()
    template = "The current temperature is {{ temperature }} degrees."
    template_variables = {"temperature": 25}
    kwargs = {}
    return run(self, template, template_variables, **kwargs)


def testcase_3():
    self = Dummy()
    self.template = self._env.from_string("{{ greeting }} {{ name }}")  # 使用默认模板
    template = None
    template_variables = {"greeting": "Hi", "name": "Bob"}
    kwargs = {"greeting": "Hello"}
    return run(self, template, template_variables, **kwargs)


def testcase_4():
    self = Dummy()
    template = "Today is {{ day }} and the weather is {{ weather }}."
    template_variables = {"day": "Monday", "weather": "sunny"}
    kwargs = {}
    return run(self, template, template_variables, **kwargs)


def testcase_5():
    self = Dummy()
    template = "Your order number {{ order_id }} will be delivered on {{ delivery_date }}."
    template_variables = {"order_id": 12345, "delivery_date": "2023-10-15"}
    kwargs = {}
    return run(self, template, template_variables, **kwargs)


def main():
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
