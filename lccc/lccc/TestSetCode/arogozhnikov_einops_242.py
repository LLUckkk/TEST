import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import numpy as np
from einops import pack
from typing import List, Tuple

from typing import Union

Tensor = np.ndarray
Shape = Tuple[int, ...]


class EinopsError(Exception):
    pass


def prod(x):
    result = 1
    for i in x:
        result *= i
    return result


def get_backend(tensor):
    class Backend:
        def shape(self, t):
            return t.shape

        def reshape(self, t, shape):
            return np.reshape(t, shape)

    return Backend()


def analyze_pattern(pattern: str, opname="unpack"):
    parts = pattern.split('*')
    if len(parts) != 2:
        raise ValueError(f"{opname} pattern must contain exactly one '*', got: {pattern}")
    n_axes_before = len(parts[0].strip().split())
    n_axes_after = len(parts[1].strip().split())
    min_axes = n_axes_before + n_axes_after + 1
    return n_axes_before, n_axes_after, min_axes


#############change###########
def unpack(tensor: Tensor, packed_shapes: List[Shape], pattern: str) -> List[Tensor]:
    n_axes_before, n_axes_after, min_axes = analyze_pattern(pattern, opname="unpack")

    backend = get_backend(tensor)
    input_shape = backend.shape(tensor)
    if len(input_shape) != n_axes_before + 1 + n_axes_after:
        raise EinopsError(f"unpack(..., {pattern}) received input of wrong dim with shape {input_shape}")

    unpacked_axis: int = n_axes_before

    lengths_of_composed_axes: List[int] = [-1 if -1 in p_shape else prod(p_shape) for p_shape in packed_shapes]

    n_unknown_composed_axes = sum(int(x == -1) for x in lengths_of_composed_axes)
    if n_unknown_composed_axes > 1:
        raise EinopsError(
            f"unpack(..., {pattern}) received more than one -1 in {packed_shapes} and can't infer dimensions"
        )

    split_positions = [0] * len(packed_shapes) + [input_shape[unpacked_axis]]
    if n_unknown_composed_axes == 0:
        for i, x in enumerate(lengths_of_composed_axes[:-1]):
            split_positions[i + 1] = split_positions[i] + x
    else:
        unknown_composed_axis: int = lengths_of_composed_axes.index(-1)
        for i in range(unknown_composed_axis):
            split_positions[i + 1] = split_positions[i] + lengths_of_composed_axes[i]
        for j in range(unknown_composed_axis + 1, len(lengths_of_composed_axes))[::-1]:
            split_positions[j] = split_positions[j + 1] - lengths_of_composed_axes[j]

    shape_start = input_shape[:unpacked_axis]
    shape_end = input_shape[unpacked_axis + 1:]
    slice_filler = (slice(None, None),) * unpacked_axis
    try:
        return [
            backend.reshape(
                tensor[(*slice_filler, slice(split_positions[i], split_positions[i + 1]))],
                (*shape_start, *element_shape, *shape_end),
            )
            for i, element_shape in enumerate(packed_shapes)
        ]
    except Exception:
        raise RuntimeError(
            f'Error during unpack(..., "{pattern}"): could not split axis of size {split_positions[-1]}'
            f" into requested {packed_shapes}"
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
    tensor = np.random.random((2, 3, 71, 5))
    packed_shapes = [(), (7,), (7, 9)]
    pattern = 'i j * k'

    return unpack(tensor, packed_shapes, pattern)


# 定义测试用例2
def testcase_2():
    tensor = np.random.random((4, 5, 36, 7))
    packed_shapes = [(6,), (6, 6)]
    pattern = 'a b * c'

    return unpack(tensor, packed_shapes, pattern)


# 定义测试用例3
def testcase_3():
    tensor = np.random.random((3, 2, 20, 4))
    packed_shapes = [(5,), (5, 3)]
    pattern = 'x y * z'

    return unpack(tensor, packed_shapes, pattern)


# 定义测试用例4
def testcase_4():
    tensor = np.random.random((5, 3, 45, 6))
    packed_shapes = [(9,), (9, 5)]
    pattern = 'p q * r'

    return unpack(tensor, packed_shapes, pattern)


# 定义测试用例5
def testcase_5():
    tensor = np.random.random((6, 4, 24, 8))
    packed_shapes = [(4,), (4, 2)]
    pattern = 'm n * o'

    return unpack(tensor, packed_shapes, pattern)


def main():
    # 执行所有测试用例
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    def json_serializable(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, tuple):
            return [json_serializable(i) for i in obj]
        else:
            return str(obj)

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
