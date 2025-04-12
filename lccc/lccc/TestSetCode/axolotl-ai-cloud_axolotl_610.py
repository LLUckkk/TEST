import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests
import warnings
import torch
import torch.distributed as dist
import os

# 忽略特定警告
warnings.filterwarnings("ignore", category=UserWarning, module="torch.distributed.distributed_c10d")

def is_distributed():
    """检查是否在分布式环境中"""
    return dist.is_available() and dist.is_initialized()


#############change###########
def barrier():
    if is_distributed():
        dist.barrier()


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
                    result_queue.put(('success', "barrier_executed"))
        except Exception as e:
            if not event.is_set():
                result_queue.put(('error', e))
        finally:
            event.set()  # 标记线程已完成
            # 清理分布式环境
            if is_distributed():
                dist.destroy_process_group()

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
# 所有测试用例使用gloo后端
def testcase_1():
    os.environ['WORLD_SIZE'] = '4'
    os.environ['MASTER_ADDR'] = 'localhost'
    os.environ['MASTER_PORT'] = '12355'
    dist.init_process_group(backend='gloo', rank=0, world_size=4)
    barrier()
    return True


# 定义测试用例2
def testcase_2():
    os.environ['WORLD_SIZE'] = '1'
    os.environ['MASTER_ADDR'] = 'localhost'
    os.environ['MASTER_PORT'] = '12356'
    dist.init_process_group(backend='gloo', rank=0, world_size=1)
    barrier()
    return True


# 定义测试用例3
def testcase_3():
    os.environ['WORLD_SIZE'] = '2'
    os.environ['MASTER_ADDR'] = 'localhost'
    os.environ['MASTER_PORT'] = '12357'
    dist.init_process_group(backend='gloo', rank=1, world_size=2)
    barrier()
    return True


# 定义测试用例4
def testcase_4():
    os.environ['WORLD_SIZE'] = '8'
    os.environ['MASTER_ADDR'] = 'localhost'
    os.environ['MASTER_PORT'] = '12358'
    dist.init_process_group(backend='gloo', rank=3, world_size=8)
    barrier()
    return True


# 定义测试用例5
def testcase_5():
    os.environ['WORLD_SIZE'] = '16'
    os.environ['MASTER_ADDR'] = 'localhost'
    os.environ['MASTER_PORT'] = '12359'
    dist.init_process_group(backend='gloo', rank=15, world_size=16)
    barrier()
    return True


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
        "ans1": "barrier_success" if test_results["ans1"]["success"] else "barrier_failed",
        "ans2": "barrier_success" if test_results["ans2"]["success"] else "barrier_failed",
        "ans3": "barrier_success" if test_results["ans3"]["success"] else "barrier_failed",
        "ans4": "barrier_success" if test_results["ans4"]["success"] else "barrier_failed",
        "ans5": "barrier_success" if test_results["ans5"]["success"] else "barrier_failed"
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
