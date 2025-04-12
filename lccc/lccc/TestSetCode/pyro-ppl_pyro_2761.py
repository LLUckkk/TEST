import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import torch


def tensor_to_serializable(obj):
    """递归将Tensor转换为可序列化的Python对象"""
    if isinstance(obj, torch.Tensor):
        return obj.tolist()  # 将Tensor转换为列表
    elif isinstance(obj, dict):
        return {k: tensor_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [tensor_to_serializable(x) for x in obj]
    else:
        return obj


def _single_step_verlet(z, r, potential_fn, kinetic_grad, step_size, z_grads=None):
    # 实现单步Verlet积分
    if z_grads is None:
        with torch.enable_grad():
            z_tensor = {k: v.clone().requires_grad_(True) for k, v in z.items()}
            potential_energy = potential_fn(z_tensor)
            z_grads = torch.autograd.grad(potential_energy, list(z_tensor.values()))
            z_grads = {k: g.detach() for k, g in zip(z.keys(), z_grads)}

    # 半步动量更新
    r_half_step = {k: r[k] - 0.5 * step_size * z_grads[k] for k in r}

    # 全步位置更新
    z_next = {k: z[k] + step_size * kinetic_grad(r_half_step)[k] for k in z}

    # 计算新位置的梯度
    with torch.enable_grad():
        z_next_tensor = {k: v.clone().requires_grad_(True) for k, v in z_next.items()}
        potential_energy = potential_fn(z_next_tensor)
        z_grads_next = torch.autograd.grad(potential_energy, list(z_next_tensor.values()))
        z_grads_next = {k: g.detach() for k, g in zip(z_next.keys(), z_grads_next)}

    # 剩余半步动量更新
    r_next = {k: r_half_step[k] - 0.5 * step_size * z_grads_next[k] for k in r_half_step}

    return z_next, r_next, z_grads_next, potential_energy.item()


#############change###########
def velocity_verlet(
        z, r, potential_fn, kinetic_grad, step_size, num_steps=1, z_grads=None
):
    z_next = z.copy()
    r_next = r.copy()
    for _ in range(num_steps):
        z_next, r_next, z_grads, potential_energy = _single_step_verlet(
            z_next, r_next, potential_fn, kinetic_grad, step_size, z_grads
        )
    return z_next, r_next, z_grads, potential_energy


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
    z = {'x': torch.tensor([1.0, 2.0]), 'y': torch.tensor([3.0, 4.0])}
    r = {'x': torch.tensor([0.5, 0.5]), 'y': torch.tensor([0.1, 0.2])}
    potential_fn = lambda z: sum((val ** 2).sum() for val in z.values())
    kinetic_grad = lambda r: {key: 2 * val for key, val in r.items()}
    step_size = 0.01
    num_steps = 10
    z_grads = {'x': torch.tensor([0.1, 0.2]), 'y': torch.tensor([0.3, 0.4])}

    return velocity_verlet(z, r, potential_fn, kinetic_grad, step_size, num_steps, z_grads)


# 定义测试用例2
def testcase_2():
    z = {'a': torch.tensor([0.0, 1.0]), 'b': torch.tensor([2.0, 3.0])}
    r = {'a': torch.tensor([0.2, 0.3]), 'b': torch.tensor([0.4, 0.5])}
    potential_fn = lambda z: sum((val ** 3).sum() for val in z.values())
    kinetic_grad = lambda r: {key: 3 * val for key, val in r.items()}
    step_size = 0.05
    num_steps = 5
    z_grads = None

    return velocity_verlet(z, r, potential_fn, kinetic_grad, step_size, num_steps, z_grads)


# 定义测试用例3
def testcase_3():
    z = {'p': torch.tensor([1.5, 2.5]), 'q': torch.tensor([3.5, 4.5])}
    r = {'p': torch.tensor([0.6, 0.7]), 'q': torch.tensor([0.8, 0.9])}
    potential_fn = lambda z: sum((val ** 4).sum() for val in z.values())
    kinetic_grad = lambda r: {key: 4 * val for key, val in r.items()}
    step_size = 0.02
    num_steps = 20
    z_grads = {'p': torch.tensor([0.5, 0.6]), 'q': torch.tensor([0.7, 0.8])}

    return velocity_verlet(z, r, potential_fn, kinetic_grad, step_size, num_steps, z_grads)


# 定义测试用例4
def testcase_4():
    z = {'m': torch.tensor([2.0, 3.0]), 'n': torch.tensor([4.0, 5.0])}
    r = {'m': torch.tensor([0.3, 0.4]), 'n': torch.tensor([0.5, 0.6])}
    potential_fn = lambda z: sum((val ** 5).sum() for val in z.values())
    kinetic_grad = lambda r: {key: 5 * val for key, val in r.items()}
    step_size = 0.03
    num_steps = 15
    z_grads = {'m': torch.tensor([0.2, 0.3]), 'n': torch.tensor([0.4, 0.5])}

    return velocity_verlet(z, r, potential_fn, kinetic_grad, step_size, num_steps, z_grads)


# 定义测试用例5
def testcase_5():
    z = {'u': torch.tensor([0.5, 1.5]), 'v': torch.tensor([2.5, 3.5])}
    r = {'u': torch.tensor([0.1, 0.2]), 'v': torch.tensor([0.3, 0.4])}
    potential_fn = lambda z: sum((val ** 6).sum() for val in z.values())
    kinetic_grad = lambda r: {key: 6 * val for key, val in r.items()}
    step_size = 0.04
    num_steps = 25
    z_grads = None

    return velocity_verlet(z, r, potential_fn, kinetic_grad, step_size, num_steps, z_grads)


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
        "ans1": tensor_to_serializable(test_results["ans1"]["result"] if test_results["ans1"]["success"] else None),
        "ans2": tensor_to_serializable(test_results["ans2"]["result"] if test_results["ans2"]["success"] else None),
        "ans3": tensor_to_serializable(test_results["ans3"]["result"] if test_results["ans3"]["success"] else None),
        "ans4": tensor_to_serializable(test_results["ans4"]["result"] if test_results["ans4"]["success"] else None),
        "ans5": tensor_to_serializable(test_results["ans5"]["result"] if test_results["ans5"]["success"] else None)
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
