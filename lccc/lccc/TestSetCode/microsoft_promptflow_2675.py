import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

from typing import Dict
from enum import Enum


class InputValueType(Enum):
    FLOW_INPUT = "flow_input"
    NODE_REFERENCE = "node_reference"


class FlowInputDefinition:
    def __init__(self, name: str, value_type: InputValueType):
        self.name = name
        self.value_type = value_type

    def to_dict(self):
        return {
            "name": self.name,
            "value_type": self.value_type.value
        }


class NodeInput:
    def __init__(self, value_type: InputValueType, value: str):
        self.value_type = value_type
        self.value = value

    def to_dict(self):
        return {
            "value_type": self.value_type.value,
            "value": self.value
        }


class Node:
    def __init__(self, inputs: Dict[str, NodeInput]):
        self.inputs = inputs

    def to_dict(self):
        return {
            "inputs": {k: v.to_dict() for k, v in self.inputs.items()}
        }


#############change###########


def _get_node_referenced_flow_inputs(
        node, flow_inputs: Dict[str, FlowInputDefinition]
) -> Dict[str, FlowInputDefinition]:
    node_referenced_flow_inputs = {}
    for _, value in node.inputs.items():
        if value.value_type == InputValueType.FLOW_INPUT and value.value in flow_inputs:
            node_referenced_flow_inputs[value.value] = flow_inputs[value.value]
    return node_referenced_flow_inputs


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
    flow_inputs = {
        "input1": FlowInputDefinition(name="input1", value_type=InputValueType.FLOW_INPUT),
        "input2": FlowInputDefinition(name="input2", value_type=InputValueType.FLOW_INPUT),
    }
    node_inputs = {
        "input1": NodeInput(value_type=InputValueType.FLOW_INPUT, value="input1"),
        "input2": NodeInput(value_type=InputValueType.FLOW_INPUT, value="input2"),
    }
    node = Node(inputs=node_inputs)

    return _get_node_referenced_flow_inputs(node, flow_inputs)


# 定义测试用例2
def testcase_2():
    flow_inputs = {
        "inputA": FlowInputDefinition(name="inputA", value_type=InputValueType.FLOW_INPUT),
        "inputB": FlowInputDefinition(name="inputB", value_type=InputValueType.FLOW_INPUT),
    }
    node_inputs = {
        "inputA": NodeInput(value_type=InputValueType.FLOW_INPUT, value="inputA"),
        "inputB": NodeInput(value_type=InputValueType.FLOW_INPUT, value="inputB"),
    }
    node = Node(inputs=node_inputs)

    return _get_node_referenced_flow_inputs(node, flow_inputs)


# 定义测试用例3
def testcase_3():
    flow_inputs = {
        "data1": FlowInputDefinition(name="data1", value_type=InputValueType.FLOW_INPUT),
        "data2": FlowInputDefinition(name="data2", value_type=InputValueType.FLOW_INPUT),
    }
    node_inputs = {
        "data1": NodeInput(value_type=InputValueType.FLOW_INPUT, value="data1"),
        "data2": NodeInput(value_type=InputValueType.FLOW_INPUT, value="data2"),
    }
    node = Node(inputs=node_inputs)

    return _get_node_referenced_flow_inputs(node, flow_inputs)


# 定义测试用例4
def testcase_4():
    flow_inputs = {
        "param1": FlowInputDefinition(name="param1", value_type=InputValueType.FLOW_INPUT),
        "param2": FlowInputDefinition(name="param2", value_type=InputValueType.FLOW_INPUT),
    }
    node_inputs = {
        "param1": NodeInput(value_type=InputValueType.FLOW_INPUT, value="param1"),
        "param2": NodeInput(value_type=InputValueType.FLOW_INPUT, value="param2"),
    }
    node = Node(inputs=node_inputs)

    return _get_node_referenced_flow_inputs(node, flow_inputs)


# 定义测试用例5
def testcase_5():
    flow_inputs = {
        "inputX": FlowInputDefinition(name="inputX", value_type=InputValueType.FLOW_INPUT),
        "inputY": FlowInputDefinition(name="inputY", value_type=InputValueType.FLOW_INPUT),
    }
    node_inputs = {
        "inputX": NodeInput(value_type=InputValueType.FLOW_INPUT, value="inputX"),
        "inputY": NodeInput(value_type=InputValueType.FLOW_INPUT, value="inputY"),
    }
    node = Node(inputs=node_inputs)

    return _get_node_referenced_flow_inputs(node, flow_inputs)


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

    def convert_result(result_dict):
        return {
            k: v.to_dict() for k, v in result_dict.items()
        }

    output = {
        k: convert_result(v["result"]) if v["success"] else None
        for k, v in test_results.items()
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
