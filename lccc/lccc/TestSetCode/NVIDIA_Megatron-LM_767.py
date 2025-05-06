import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import torch
from typing import Callable


# ModelParallelConfig 类的定义
class ModelParallelConfig:
    def __init__(
            self,
            perform_initialization,
            use_cpu_initialization,
            params_dtype,
            sequence_parallel,
            gradient_accumulation_fusion,
            tp_comm_overlap,
            tp_comm_split_ag,
            tp_comm_atomic_ag,
            tp_comm_split_rs,
            tp_comm_atomic_rs,
            expert_model_parallel_size,
            disable_parameter_transpose_cache,
            normalization,
            layernorm_epsilon,
            layernorm_zero_centered_gamma,
            tensor_model_parallel_size
    ):
        self.perform_initialization = perform_initialization
        self.use_cpu_initialization = use_cpu_initialization
        self.params_dtype = params_dtype
        self.sequence_parallel = sequence_parallel
        self.gradient_accumulation_fusion = gradient_accumulation_fusion
        self.tp_comm_overlap = tp_comm_overlap
        self.tp_comm_split_ag = tp_comm_split_ag
        self.tp_comm_atomic_ag = tp_comm_atomic_ag
        self.tp_comm_split_rs = tp_comm_split_rs
        self.tp_comm_atomic_rs = tp_comm_atomic_rs
        self.expert_model_parallel_size = expert_model_parallel_size
        self.disable_parameter_transpose_cache = disable_parameter_transpose_cache
        self.normalization = normalization
        self.layernorm_epsilon = layernorm_epsilon
        self.layernorm_zero_centered_gamma = layernorm_zero_centered_gamma
        self.tensor_model_parallel_size = tensor_model_parallel_size


#############change###########
def condition_init_method(config, init_method):
    return init_method if config.perform_initialization else (lambda w: None)


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
    config = ModelParallelConfig(
        perform_initialization=True,
        use_cpu_initialization=False,
        params_dtype=torch.float32,
        sequence_parallel=True,
        gradient_accumulation_fusion=True,
        tp_comm_overlap=True,
        tp_comm_split_ag=True,
        tp_comm_atomic_ag=True,
        tp_comm_split_rs=True,
        tp_comm_atomic_rs=True,
        expert_model_parallel_size=2,
        disable_parameter_transpose_cache=False,
        normalization="LayerNorm",
        layernorm_epsilon=1e-5,
        layernorm_zero_centered_gamma=False,
        tensor_model_parallel_size=2
    )
    init_method = lambda w: torch.nn.init.xavier_uniform_(w)

    if condition_init_method(config, init_method) is None:
        return False
    else:
        return init_method.__name__


# 定义测试用例2
def testcase_2():
    config = ModelParallelConfig(
        perform_initialization=False,
        use_cpu_initialization=True,
        params_dtype=torch.float16,
        sequence_parallel=False,
        gradient_accumulation_fusion=False,
        tp_comm_overlap=False,
        tp_comm_split_ag=False,
        tp_comm_atomic_ag=False,
        tp_comm_split_rs=False,
        tp_comm_atomic_rs=False,
        expert_model_parallel_size=1,
        disable_parameter_transpose_cache=True,
        normalization="BatchNorm",
        layernorm_epsilon=1e-6,
        layernorm_zero_centered_gamma=True,
        tensor_model_parallel_size=4
    )
    init_method = lambda w: torch.nn.init.kaiming_normal_(w)
    if condition_init_method(config, init_method) is None:
        return False
    else:
        return init_method.__name__


# 定义测试用例3
def testcase_3():
    config = ModelParallelConfig(
        perform_initialization=True,
        use_cpu_initialization=False,
        params_dtype=torch.float64,
        sequence_parallel=True,
        gradient_accumulation_fusion=True,
        tp_comm_overlap=True,
        tp_comm_split_ag=True,
        tp_comm_atomic_ag=True,
        tp_comm_split_rs=True,
        tp_comm_atomic_rs=True,
        expert_model_parallel_size=3,
        disable_parameter_transpose_cache=False,
        normalization="LayerNorm",
        layernorm_epsilon=1e-7,
        layernorm_zero_centered_gamma=False,
        tensor_model_parallel_size=8
    )
    init_method = lambda w: torch.nn.init.constant_(w, 0.1)

    if condition_init_method(config, init_method) is None:
        return False
    else:
        return init_method.__name__


# 定义测试用例4
def testcase_4():
    config = ModelParallelConfig(
        perform_initialization=False,
        use_cpu_initialization=True,
        params_dtype=torch.float32,
        sequence_parallel=False,
        gradient_accumulation_fusion=False,
        tp_comm_overlap=False,
        tp_comm_split_ag=False,
        tp_comm_atomic_ag=False,
        tp_comm_split_rs=False,
        tp_comm_atomic_rs=False,
        expert_model_parallel_size=1,
        disable_parameter_transpose_cache=True,
        normalization="LayerNorm",
        layernorm_epsilon=1e-8,
        layernorm_zero_centered_gamma=True,
        tensor_model_parallel_size=1
    )
    init_method = lambda w: torch.nn.init.uniform_(w, -0.1, 0.1)

    if condition_init_method(config, init_method) is None:
        return False
    else:
        return init_method.__name__


# 定义测试用例5
def testcase_5():
    config = ModelParallelConfig(
        perform_initialization=True,
        use_cpu_initialization=False,
        params_dtype=torch.float16,
        sequence_parallel=True,
        gradient_accumulation_fusion=True,
        tp_comm_overlap=True,
        tp_comm_split_ag=True,
        tp_comm_atomic_ag=True,
        tp_comm_split_rs=True,
        tp_comm_atomic_rs=True,
        expert_model_parallel_size=4,
        disable_parameter_transpose_cache=False,
        normalization="LayerNorm",
        layernorm_epsilon=1e-9,
        layernorm_zero_centered_gamma=False,
        tensor_model_parallel_size=16
    )
    init_method = lambda w: torch.nn.init.normal_(w, mean=0.0, std=0.02)

    if condition_init_method(config, init_method) is None:
        return False
    else:
        return init_method.__name__


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

    with open('output.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)


if __name__ == '__main__':
    main()
