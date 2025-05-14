import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
from typing import Dict, Any

import requests

import operator


def _eval_op(op, values: list) -> Any:
    # 如果 op 是字符串（保留原有兼容性）
    if isinstance(op, str):
        if op == "add":
            return values[0] + values[1]
        elif op == "sub":
            return values[0] - values[1]
        elif op == "mult":
            return values[0] * values[1]
        elif op == "div":
            return values[0] / values[1]
        elif op == "eq":
            return values[0] == values[1]
        elif op == "gt":
            return values[0] > values[1]
        elif op == "lt":
            return values[0] < values[1]
        elif op == "ne":
            return values[0] != values[1]
        elif op == "le":
            return values[0] <= values[1]
        else:
            raise ValueError(f"Unsupported operator string: {op}")

    # 如果 op 是函数对象（如 operator.lt）
    elif callable(op):
        return op(values[0], values[1])

    raise TypeError(f"Unsupported operator type: {type(op)}")


class Dummy:
    def _eval_expr(self, expr: Any) -> Any:
        if isinstance(expr, (int, float, str, bool)):
            # 字面量直接返回
            return expr

        if isinstance(expr, dict):
            node_type = expr.get("type")

            if node_type == "Name":
                # 变量引用
                var_name = expr["id"]
                return self.context.get(var_name)  # 假设 self.context 是一个变量作用域的 dict

            elif node_type == "Constant":
                return expr["value"]

            elif node_type == "BinOp":
                left = self._eval_expr(expr["left"])
                right = self._eval_expr(expr["right"])
                return _eval_op(expr["op"], [left, right])  # 假设 _eval_op 能根据 op 处理加减乘除等操作

            elif node_type == "Compare":
                return self._eval_compare(expr)

            # 可扩展其他类型
            raise ValueError(f"Unsupported expression type: {node_type}")

        raise TypeError(f"Unexpected expression format: {expr}")


#############change###########
def _eval_compare(self, fields: Dict[str, Any]) -> Any:
    value = self._eval_expr(fields["left"])
    for op, rhs in zip(fields["ops"], fields["comparators"]):
        value = _eval_op(op, values=[value, self._eval_expr(rhs)])
    return value


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
    fields = {
        "left": 5,
        "ops": [operator.lt],
        "comparators": [10]
    }

    return _eval_compare(self, fields)


# 定义测试用例2
def testcase_2():
    self = Dummy()
    fields = {
        "left": 20,
        "ops": [operator.eq],
        "comparators": [20]
    }

    return _eval_compare(self, fields)


# 定义测试用例3
def testcase_3():
    self = Dummy()
    fields = {
        "left": 15,
        "ops": [operator.gt],
        "comparators": [10]
    }

    return _eval_compare(self, fields)


# 定义测试用例4
def testcase_4():
    self = Dummy()
    fields = {
        "left": 7,
        "ops": [operator.ne],
        "comparators": [8]
    }

    return _eval_compare(self, fields)


# 定义测试用例5
def testcase_5():
    self = Dummy()
    fields = {
        "left": 3,
        "ops": [operator.le],
        "comparators": [3]
    }

    return _eval_compare(self, fields)


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
