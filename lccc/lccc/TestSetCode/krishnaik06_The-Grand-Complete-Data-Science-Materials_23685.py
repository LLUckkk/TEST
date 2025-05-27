import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import numpy as np
import pickle
import io

from joblib.numpy_pickle_utils import _ensure_native_byte_order, _read_bytes, BUFFER_SIZE


#############change###########
def read_array(self, unpickler):
    if len(self.shape) == 0:
        count = 1
    else:
        shape_int64 = [unpickler.np.int64(x) for x in self.shape]
        count = unpickler.np.multiply.reduce(shape_int64)
    if self.dtype.hasobject:
        array = pickle.load(unpickler.file_handle)
    else:
        numpy_array_alignment_bytes = \
            self.safe_get_numpy_array_alignment_bytes()
        if numpy_array_alignment_bytes is not None:
            padding_byte = unpickler.file_handle.read(1)
            padding_length = int.from_bytes(
                padding_byte, byteorder='little')
            if padding_length != 0:
                unpickler.file_handle.read(padding_length)

        max_read_count = BUFFER_SIZE // min(BUFFER_SIZE,
                                            self.dtype.itemsize)

        array = unpickler.np.empty(count, dtype=self.dtype)
        for i in range(0, count, max_read_count):
            read_count = min(max_read_count, count - i)
            read_size = int(read_count * self.dtype.itemsize)
            data = _read_bytes(unpickler.file_handle,
                               read_size, "array data")
            array[i:i + read_count] = \
                unpickler.np.frombuffer(data, dtype=self.dtype,
                                        count=read_count)
            del data

        if self.order == 'F':
            array.shape = self.shape[::-1]
            array = array.transpose()
        else:
            array.shape = self.shape

    return _ensure_native_byte_order(array)


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
    class Dummy:
        pass

    self = Dummy()
    self = type('test', (object,), {
        'shape': (2, 3),
        'dtype': np.dtype('float64'),
        'order': 'C',
        'safe_get_numpy_array_alignment_bytes': lambda self: None
    })()
    unpickler = type('unpickler', (object,), {
        'np': np,
        'file_handle': io.BytesIO(np.array([[1.1, 2.2, 3.3], [4.4, 5.5, 6.6]], dtype='float64').tobytes())
    })()

    return read_array(self, unpickler)


# 定义测试用例2
def testcase_2():
    class Dummy:
        pass

    self = Dummy()
    self = type('test', (object,), {
        'shape': (3, 3),
        'dtype': np.dtype('int32'),
        'order': 'F',
        'safe_get_numpy_array_alignment_bytes': lambda self: 8
    })()
    unpickler = type('unpickler', (object,), {
        'np': np,
        'file_handle': io.BytesIO(np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype='int32').tobytes())
    })()

    return read_array(self, unpickler)


# 定义测试用例3
def testcase_3():
    class Dummy:
        pass

    self = Dummy()
    self = type('test', (object,), {
        'shape': (4,),
        'dtype': np.dtype('complex64'),
        'order': 'C',
        'safe_get_numpy_array_alignment_bytes': lambda self: None
    })()
    unpickler = type('unpickler', (object,), {
        'np': np,
        'file_handle': io.BytesIO(np.array([1 + 2j, 3 + 4j, 5 + 6j, 7 + 8j], dtype='complex64').tobytes())
    })()

    return read_array(self, unpickler)


# 定义测试用例4
def testcase_4():
    class Dummy:
        pass

    self = Dummy()
    self = type('test', (object,), {
        'shape': (2, 2, 2),
        'dtype': np.dtype('int16'),
        'order': 'F',
        'safe_get_numpy_array_alignment_bytes': lambda self: None
    })()
    unpickler = type('unpickler', (object,), {
        'np': np,
        'file_handle': io.BytesIO(np.array([[[1, 2], [3, 4]], [[5, 6], [7, 8]]], dtype='int16').tobytes())
    })()

    return read_array(self, unpickler)


# 定义测试用例5
def testcase_5():
    class Dummy:
        pass

    self = Dummy()
    self = type('test', (object,), {
        'shape': (5,),
        'dtype': np.dtype('float32'),
        'order': 'C',
        'safe_get_numpy_array_alignment_bytes': lambda self: None
    })()
    unpickler = type('unpickler', (object,), {
        'np': np,
        'file_handle': io.BytesIO(np.array([1.1, 2.2, 3.3, 4.4, 5.5], dtype='float32').tobytes())
    })()

    return read_array(self, unpickler)


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
            return json_serializable(obj.tolist())  # 再递归转换内容
        elif isinstance(obj, (np.generic,)):
            return json_serializable(obj.item())  # 转成 Python 原生类型后继续处理
        elif isinstance(obj, complex):
            return {"real": obj.real, "imag": obj.imag}
        elif isinstance(obj, list):
            return [json_serializable(i) for i in obj]
        elif isinstance(obj, tuple):
            return tuple(json_serializable(i) for i in obj)
        elif isinstance(obj, dict):
            return {str(k): json_serializable(v) for k, v in obj.items()}
        else:
            return obj  # 假设是基本类型（int、float、str、bool、None）

    output = {
        "ans1": json_serializable(test_results["ans1"]["result"]) if test_results["ans1"]["success"] else None,
        "ans2": json_serializable(test_results["ans2"]["result"]) if test_results["ans2"]["success"] else None,
        "ans3": json_serializable(test_results["ans3"]["result"]) if test_results["ans3"]["success"] else None,
        "ans4": json_serializable(test_results["ans4"]["result"]) if test_results["ans4"]["success"] else None,
        "ans5": json_serializable(test_results["ans5"]["result"]) if test_results["ans5"]["success"] else None
    }

    with open('output.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)


if __name__ == '__main__':
    main()
