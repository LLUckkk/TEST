import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import torch
import tempfile
import os


def get_accelerator():
    class DummyAccelerator:
        def pin_memory(self, tensor):
            return tensor  # 简化模拟

    return DummyAccelerator()


def _get_test_write_file(tmpdir, index):
    file_path = os.path.join(tmpdir, f'test_file_{index}.bin')
    data = bytes([index % 2] * 64)  # 确定性内容：全0或全1
    with open(file_path, 'wb') as f:
        f.write(data)
    return file_path


class DummyAIOHandle:
    def new_cpu_locked_tensor(self, size, data):
        class DummyTensor:
            def __init__(self, data):
                self.data = data.clone()

            def __repr__(self):
                return f"<DummyTensor shape={self.data.shape}>"

        return DummyTensor(data)


class AsyncIOBuilder:
    def load(self):
        return self

    def aio_handle(self, block_size, queue_depth, flag1, flag2, parallel):
        return DummyAIOHandle()


BLOCK_SIZE = 512
QUEUE_DEPTH = 8
IO_PARALLEL = 2


#############change###########
def _get_test_write_file_and_pinned_tensor(tmpdir, ref_buffer, aio_handle=None, index=0):
    test_file = _get_test_write_file(tmpdir, index)
    if aio_handle is None:
        test_buffer = get_accelerator().pin_memory(torch.ByteTensor(list(ref_buffer)))
    else:
        tmp_buffer = torch.ByteTensor(list(ref_buffer))
        test_buffer = aio_handle.new_cpu_locked_tensor(len(ref_buffer), tmp_buffer)
        test_buffer.data.copy_(tmp_buffer)

    return test_file, test_buffer


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


def deterministic_bytes(size):
    return bytearray([i % 256 for i in range(size)])


def testcase_1():
    tmpdir = tempfile.mkdtemp()
    ref_buffer = deterministic_bytes(1024)
    aio_handle = None
    index = 0
    return _get_test_write_file_and_pinned_tensor(tmpdir, ref_buffer, aio_handle, index)


def testcase_2():
    tmpdir = tempfile.mkdtemp()
    ref_buffer = deterministic_bytes(2048)
    aio_handle = None
    index = 1
    return _get_test_write_file_and_pinned_tensor(tmpdir, ref_buffer, aio_handle, index)


def testcase_3():
    tmpdir = tempfile.mkdtemp()
    ref_buffer = deterministic_bytes(512)
    aio_handle = AsyncIOBuilder().load().aio_handle(BLOCK_SIZE, QUEUE_DEPTH, True, True, IO_PARALLEL)
    index = 2
    return _get_test_write_file_and_pinned_tensor(tmpdir, ref_buffer, aio_handle, index)


def testcase_4():
    tmpdir = tempfile.mkdtemp()
    ref_buffer = deterministic_bytes(4096)
    aio_handle = AsyncIOBuilder().load().aio_handle(BLOCK_SIZE, QUEUE_DEPTH, False, False, IO_PARALLEL)
    index = 3
    return _get_test_write_file_and_pinned_tensor(tmpdir, ref_buffer, aio_handle, index)


def testcase_5():
    tmpdir = tempfile.mkdtemp()
    ref_buffer = deterministic_bytes(8192)
    aio_handle = AsyncIOBuilder().load().aio_handle(BLOCK_SIZE, QUEUE_DEPTH, True, False, IO_PARALLEL)
    index = 4
    return _get_test_write_file_and_pinned_tensor(tmpdir, ref_buffer, aio_handle, index)


def main():
    # 执行所有测试用例
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    output = {}
    for key in ["ans1", "ans2", "ans3", "ans4", "ans5"]:
        if test_results[key]["success"]:
            test_file, test_buffer = test_results[key]["result"]
            # 将 Tensor 转换为可序列化的格式（如列表）
            serializable_buffer = test_buffer.tolist() if hasattr(test_buffer, "tolist") else str(test_buffer)
            output[key] = {
                "test_buffer": serializable_buffer
            }
        else:
            output[key] = None
    with open('output.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)


if __name__ == '__main__':
    main()
