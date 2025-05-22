import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import numpy as np
import operator
from numpy.ma import MaskedArray, mask_or, getmask, getdata, masked, nomask


def _check_fill_value(value, dtype):
    """
    尝试将 fill_value 转换为指定的 numpy 类型 dtype。
    如果不合法，将抛出 TypeError 或 ValueError。
    """
    if value is None:
        return dtype()  # 返回 dtype 的默认值（例如 np.bool_() 是 False）

    try:
        return dtype(value)
    except (TypeError, ValueError) as e:
        raise type(e)(f"Invalid fill value {value!r} for dtype {dtype}: {e}")


#############change###########
def _comparison(self, other, compare):
    omask = getmask(other)
    smask = self.mask
    mask = mask_or(smask, omask, copy=True)

    odata = getdata(other)
    if mask.dtype.names is not None:
        if compare not in (operator.eq, operator.ne):
            return NotImplemented
        broadcast_shape = np.broadcast(self, odata).shape
        sbroadcast = np.broadcast_to(self, broadcast_shape, subok=True)
        sbroadcast._mask = mask
        sdata = sbroadcast.filled(odata)
        mask = (mask == np.ones((), mask.dtype))

    else:
        sdata = self.data

    check = compare(sdata, odata)

    if isinstance(check, (np.bool_, bool)):
        return masked if mask else check

    if mask is not nomask and compare in (operator.eq, operator.ne):
        check = np.where(mask, compare(smask, omask), check)
        if mask.shape != check.shape:
            mask = np.broadcast_to(mask, check.shape).copy()

    check = check.view(type(self))
    check._update_from(self)
    check._mask = mask

    if check._fill_value is not None:
        try:
            fill = _check_fill_value(check._fill_value, np.bool_)
        except (TypeError, ValueError):
            fill = _check_fill_value(None, np.bool_)
        check._fill_value = fill

    return check


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
    self = MaskedArray(data=[1, 2, 3], mask=[False, True, False])
    other = MaskedArray(data=[1, 2, 4], mask=[False, True, False])
    compare = operator.eq

    return _comparison(self, other, compare)


# 定义测试用例2
def testcase_2():
    class Dummy:
        pass

    self = Dummy()
    self = MaskedArray(data=[1.0, 2.0, 3.0], mask=[False, False, True])
    other = MaskedArray(data=[1.0, 2.0, 3.0], mask=[False, False, True])
    compare = operator.ne

    return _comparison(self, other, compare)


# 定义测试用例3
def testcase_3():
    class Dummy:
        pass

    self = Dummy()
    self = MaskedArray(data=[1, 2, 3], mask=[False, False, False])
    other = MaskedArray(data=[4, 5, 6], mask=[False, False, False])
    compare = operator.le

    return _comparison(self, other, compare)


# 定义测试用例4
def testcase_4():
    class Dummy:
        pass

    self = Dummy()
    self = MaskedArray(data=[1, 2, 3], mask=[True, True, True])
    other = MaskedArray(data=[1, 2, 3], mask=[True, True, True])
    compare = operator.lt

    return _comparison(self, other, compare)


# 定义测试用例5
def testcase_5():
    class Dummy:
        pass

    self = Dummy()
    self = MaskedArray(data=[1, 2, 3], mask=[False, False, False])
    other = MaskedArray(data=[1, 2, 3], mask=[False, False, False])
    compare = operator.ge

    return _comparison(self, other, compare)


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
        if isinstance(obj, dict):
            return {k: json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [json_serializable(v) for v in obj]
        elif isinstance(obj, tuple):
            return tuple(json_serializable(v) for v in obj)
        elif isinstance(obj, np.generic):
            return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, MaskedArray):
            return obj.filled(-1).tolist()
        else:
            return obj

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
