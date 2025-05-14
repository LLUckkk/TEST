import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import numpy as np
import tensorflow as tf


def compare_tflite_with_tvm(input_data, input_name, input_tensors, output_tensors):
    """
    模拟 compare_tflite_with_tvm 行为：打印输入输出张量形状和数值。
    实际使用中请替换为真正的 tflite vs TVM 比较函数。
    """
    with tf.Session() as sess:
        feed_dict = {input_tensors[0]: input_data}
        output = sess.run(output_tensors, feed_dict=feed_dict)
        # print(f"[INFO] Tile input shape: {input_data.shape}")
        # print(f"[INFO] Tile input data:\n{input_data}")
        # print(f"[INFO] Tile output shape: {output[0].shape}")
        # print(f"[INFO] Tile output data:\n{output[0]}")
        return output[0]  # 返回值便于测试框架接收


#############change###########
def _test_forward_tile(in_shape, reps, dtype):
    # 禁用 Eager Execution，启用 Graph 模式
    tf.compat.v1.disable_eager_execution()

    data = np.random.uniform(-5, 5, size=in_shape).astype(dtype)

    with tf.Graph().as_default():
        # 使用 TF 2.x 推荐方式构建 placeholder 和 tile 操作
        in_data = tf.compat.v1.placeholder(shape=data.shape, dtype=data.dtype)
        out = tf.tile(in_data, reps)

        # 构建并执行会话
        with tf.compat.v1.Session() as sess:
            result = sess.run(out, feed_dict={in_data: data})

        # 返回结果以便测试框架使用（这里只是演示，真实使用你可能需要 compare_tflite_with_tvm）
        return result.tolist()


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
    in_shape = (4,)
    reps = (2,)
    dtype = "float64"

    return _test_forward_tile(in_shape, reps, dtype)


# 定义测试用例2
def testcase_2():
    in_shape = (3, 3)
    reps = (1, 2)
    dtype = "int32"

    return _test_forward_tile(in_shape, reps, dtype)


# 定义测试用例3
def testcase_3():
    in_shape = (5, 2)
    reps = (3, 1)
    dtype = "float32"

    return _test_forward_tile(in_shape, reps, dtype)


# 定义测试用例4
def testcase_4():
    in_shape = (2, 2, 2)
    reps = (2, 2, 2)
    dtype = "int64"

    return _test_forward_tile(in_shape, reps, dtype)


# 定义测试用例5
def testcase_5():
    in_shape = (6,)
    reps = (4,)
    dtype = "int32"

    return _test_forward_tile(in_shape, reps, dtype)


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
