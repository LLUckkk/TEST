import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import types
import inspect
import logging


class prompty_sdk:
    name = "PromptySDK"


class prompty_core:
    name = "PromptyCore"


class flex_flow:
    name = "FlexFlow"


class dag_flow:
    name = "DagFlow"


# 假设 evaluator 的类型识别逻辑
def _get_evaluator_type(evaluator):
    if isinstance(evaluator, prompty_sdk):
        return "sdk"
    elif isinstance(evaluator, prompty_core):
        return "core"
    elif isinstance(evaluator, flex_flow):
        return "flow"
    elif isinstance(evaluator, dag_flow):
        return "dag"
    elif inspect.isfunction(evaluator):
        return "function"
    elif hasattr(evaluator, "__class__"):
        return "callable"
    else:
        return "unknown"


# mock logger
LOGGER = logging.getLogger("EvaluatorLogger")
logging.basicConfig(level=logging.DEBUG)


#############change###########
def _get_evaluator_properties(evaluator, evaluator_name):
    try:
        if isinstance(evaluator, (prompty_sdk, prompty_core, flex_flow)):
            name = evaluator.name
            pf_type = evaluator.__class__.__name__
        elif isinstance(evaluator, dag_flow):
            name = evaluator.name
            pf_type = "DagFlow"
        elif inspect.isfunction(evaluator):
            name = evaluator.__name__
            pf_type = flex_flow.__name__
        elif hasattr(evaluator, "__class__") and callable(evaluator):
            name = evaluator.__class__.__name__
            pf_type = flex_flow.__name__
        else:
            name = str(evaluator)
            pf_type = "Unknown"
    except Exception as e:
        LOGGER.debug(f"Failed to get evaluator properties: {e}")
        name = str(evaluator)
        pf_type = "Unknown"

    return {
        "name": name,
        "pf_type": pf_type,
        "type": _get_evaluator_type(evaluator),
        "alias": evaluator_name if evaluator_name else "",
    }


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
    evaluator = types.SimpleNamespace(name="Evaluator1", __class__=types.SimpleNamespace(__name__="EvaluatorClass"))
    evaluator_name = "evaluator_alias_1"

    return _get_evaluator_properties(evaluator, evaluator_name)


# 定义测试用例2
def testcase_2():
    evaluator = types.SimpleNamespace(name="Evaluator2", __class__=types.SimpleNamespace(__name__="CustomEvaluator"))
    evaluator_name = "custom_evaluator"

    return _get_evaluator_properties(evaluator, evaluator_name)


# 定义测试用例3
def testcase_3():
    evaluator = lambda x: x * 2
    evaluator_name = "lambda_evaluator"

    return _get_evaluator_properties(evaluator, evaluator_name)


# 定义测试用例4
def testcase_4():
    evaluator = types.SimpleNamespace(name="ContentSafetyEvaluator",
                                      __class__=types.SimpleNamespace(__name__="ContentSafety"))
    evaluator_name = "content_safety"

    return _get_evaluator_properties(evaluator, evaluator_name)


# 定义测试用例5
def testcase_5():
    evaluator = "UnknownEvaluator"
    evaluator_name = ""
    return _get_evaluator_properties(evaluator, evaluator_name)


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
