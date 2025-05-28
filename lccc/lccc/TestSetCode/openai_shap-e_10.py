import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import torch
import numpy as np
import torch as th


def _extract_into_tensor(arr, timesteps, broadcast_shape):
    # 假设 arr 是 numpy array
    res = th.tensor(arr, dtype=th.float32)[timesteps]
    while len(res.shape) < len(broadcast_shape):
        res = res.unsqueeze(-1)
    return res.expand(broadcast_shape)


#############change###########
def p_mean_variance(
        self, model, x, t, clip_denoised=False, denoised_fn=None, model_kwargs=None
):
    if model_kwargs is None:
        model_kwargs = {}

    B, C = x.shape[:2]
    assert t.shape == (B,)
    model_output = model(x, t, **model_kwargs)
    if isinstance(model_output, tuple):
        model_output, extra = model_output
    else:
        extra = None

    if self.model_var_type in ["learned", "learned_range"]:
        assert model_output.shape == (B, C * 2, *x.shape[2:])
        model_output, model_var_values = th.split(model_output, C, dim=1)
        if self.model_var_type == "learned":
            model_log_variance = model_var_values
            model_variance = th.exp(model_log_variance)
        else:
            min_log = _extract_into_tensor(self.posterior_log_variance_clipped, t, x.shape)
            max_log = _extract_into_tensor(np.log(self.betas), t, x.shape)
            frac = (model_var_values + 1) / 2
            model_log_variance = frac * max_log + (1 - frac) * min_log
            model_variance = th.exp(model_log_variance)
    else:
        model_variance, model_log_variance = {
            "fixed_large": (
                np.append(self.posterior_variance[1], self.betas[1:]),
                np.log(np.append(self.posterior_variance[1], self.betas[1:])),
            ),
            "fixed_small": (
                self.posterior_variance,
                self.posterior_log_variance_clipped,
            ),
        }[self.model_var_type]
        model_variance = _extract_into_tensor(model_variance, t, x.shape)
        model_log_variance = _extract_into_tensor(model_log_variance, t, x.shape)

    def process_xstart(x):
        if denoised_fn is not None:
            x = denoised_fn(x)
        if clip_denoised:
            return x.clamp(-1, 1)
        return x

    if self.model_mean_type == "x_prev":
        pred_xstart = process_xstart(
            self._predict_xstart_from_xprev(x_t=x, t=t, xprev=model_output)
        )
        model_mean = model_output
    elif self.model_mean_type in ["x_start", "epsilon"]:
        if self.model_mean_type == "x_start":
            pred_xstart = process_xstart(model_output)
        else:
            pred_xstart = process_xstart(
                self._predict_xstart_from_eps(x_t=x, t=t, eps=model_output)
            )
        model_mean, _, _ = self.q_posterior_mean_variance(x_start=pred_xstart, x_t=x, t=t)
    else:
        raise NotImplementedError(self.model_mean_type)

    assert model_mean.shape == model_log_variance.shape == pred_xstart.shape == x.shape
    return {
        "mean": model_mean,
        "variance": model_variance,
        "log_variance": model_log_variance,
        "pred_xstart": pred_xstart,
        "extra": extra,
    }


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


class Dummy:
    def __init__(self):
        self.model_var_type = "fixed_large"  # 你可以改成 "learned" 来测试其他分支
        self.model_mean_type = "x_start"  # 支持 "x_start", "epsilon", "x_prev"
        self.betas = np.linspace(1e-4, 0.02, 1000).astype(np.float32)
        self.posterior_variance = np.square(self.betas)
        self.posterior_log_variance_clipped = np.log(np.maximum(self.posterior_variance, 1e-20))

    def _predict_xstart_from_xprev(self, x_t, t, xprev):
        # 伪造实现
        return xprev * 0.5 + x_t * 0.5

    def _predict_xstart_from_eps(self, x_t, t, eps):
        # 伪造实现
        return x_t - eps

    def q_posterior_mean_variance(self, x_start, x_t, t):
        # 伪造实现
        mean = (x_start + x_t) / 2
        variance = th.full_like(x_start, 0.1)
        log_variance = th.full_like(x_start, -2.0)
        return mean, variance, log_variance


# 定义测试用例1
def testcase_1():
    self = Dummy()
    model = lambda x, t, **kwargs: (torch.randn_like(x), None)
    x = torch.randn(4, 3, 32, 32)
    t = torch.tensor([10, 20, 30, 40])
    clip_denoised = True
    denoised_fn = lambda x: x.clamp(-0.5, 0.5)
    model_kwargs = {'param1': 'value1'}

    return p_mean_variance(self, model, x, t, clip_denoised, denoised_fn, model_kwargs)


# 定义测试用例2
def testcase_2():
    self = Dummy()
    model = lambda x, t, **kwargs: (torch.randn_like(x), None)
    x = torch.randn(2, 1, 64, 64)
    t = torch.tensor([5, 15])
    clip_denoised = False
    denoised_fn = None
    model_kwargs = None

    return p_mean_variance(self, model, x, t, clip_denoised, denoised_fn, model_kwargs)


# 定义测试用例3
def testcase_3():
    self = Dummy()
    model = lambda x, t, **kwargs: (torch.randn_like(x), None)
    x = torch.randn(3, 2, 28, 28)
    t = torch.tensor([0, 1, 2])
    clip_denoised = True
    denoised_fn = lambda x: x * 0.5
    model_kwargs = {'condition': 'test'}

    return p_mean_variance(self, model, x, t, clip_denoised, denoised_fn, model_kwargs)


# 定义测试用例4
def testcase_4():
    self = Dummy()
    model = lambda x, t, **kwargs: (torch.randn_like(x), None)
    x = torch.randn(5, 3, 128, 128)
    t = torch.tensor([50, 60, 70, 80, 90])
    clip_denoised = False
    denoised_fn = lambda x: x.abs()
    model_kwargs = {'extra_param': 42}

    return p_mean_variance(self, model, x, t, clip_denoised, denoised_fn, model_kwargs)


# 定义测试用例5
def testcase_5():
    self = Dummy()
    model = lambda x, t, **kwargs: (torch.randn_like(x), None)
    x = torch.randn(6, 1, 16, 16)
    t = torch.tensor([100, 200, 300, 400, 500, 600])
    clip_denoised = True
    denoised_fn = lambda x: x.clamp(-1, 1)
    model_kwargs = {'scale': 0.1}

    return p_mean_variance(self, model, x, t, clip_denoised, denoised_fn, model_kwargs)


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
        if isinstance(obj, th.Tensor):
            return obj.detach().cpu().tolist()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)

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
