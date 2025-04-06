import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests
import numpy as np
from typing import Union, Tuple, Optional, Any

# 使用适当的类型注释
ArrayLike = Union[np.ndarray, list]  # 定义类型别名


def window_bandwidth(window: str) -> float:
    if window == "hann":
        return 1.0  # 假设hann窗口的带宽为1.0
    elif window == "hamming":
        return 1.0  # 假设hamming窗口的带宽为1.0
    elif window == "blackman":
        return 2.0  # 假设blackman窗口的带宽为2.0
    elif window == "bartlett":
        return 1.5  # 假设bartlett窗口的带宽为1.5
    elif window == "kaiser":
        return 2.5  # 假设kaiser窗口的带宽为2.5
    else:
        raise ValueError(f"Unknown window type: {window}")


def _relative_bandwidth(freqs: np.ndarray) -> np.ndarray:
    """计算给定频率数组的相对带宽"""
    if len(freqs) < 2:
        raise ValueError("频率数组需要至少包含两个频率值")

    # 计算频率范围的宽度
    bandwidth = freqs[-1] - freqs[0]

    # 计算中心频率
    center_frequency = np.mean(freqs)

    # 相对带宽计算公式：带宽 / 中心频率
    relative_bandwidth = bandwidth / center_frequency

    # 如果只有一个频率点，返回一个常数的相对带宽
    if len(freqs) == 1:
        return [relative_bandwidth]

    return [relative_bandwidth] * len(freqs)


#############change###########

def wavelet_lengths(
        *,
        freqs: ArrayLike,
        sr: float = 22050,
        window: str = "hann",
        filter_scale: float = 1,
        gamma: Optional[float] = 0,
        alpha: Optional[Union[float, np.ndarray]] = None,
) -> Tuple[np.ndarray, float]:
    # 确保 freqs 是 np.ndarray 类型
    freqs = np.asarray(freqs)

    # 参数检查
    if filter_scale <= 0:
        raise ValueError(f"filter_scale={filter_scale} must be positive")

    if gamma is not None and gamma < 0:
        raise ValueError(f"gamma={gamma} must be non-negative")

    if np.any(freqs <= 0):
        raise ValueError("frequencies must be strictly positive")

    if len(freqs) > 1 and np.any(freqs[:-1] > freqs[1:]):
        raise ValueError(
            f"Frequency array={freqs} must be in strictly ascending order"
        )

    # 如果 alpha 是 None，使用 _relative_bandwidth 函数计算 alpha
    if alpha is None:
        alpha = _relative_bandwidth(freqs=freqs)
    else:
        # 确保 alpha 是 np.ndarray 类型
        alpha = np.asarray(alpha)

    # 如果 gamma 是 None，使用默认值，否则使用传入的 gamma
    gamma_ = alpha * 24.7 / 0.108 if gamma is None else gamma

    # 计算 Q
    Q = float(filter_scale) / alpha

    # 计算 f_cutoff
    f_cutoff = np.max(freqs * (1 + 0.5 * window_bandwidth(window) / Q) + 0.5 * gamma_)

    # 计算 lengths
    lengths = Q * sr / (freqs + gamma_ / alpha)

    return lengths, f_cutoff


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
    freqs = np.array([100, 200, 300, 400, 500])
    sr = 22050
    window = "hann"
    filter_scale = 1
    gamma = 0
    alpha = None

    return wavelet_lengths(freqs=freqs, sr=sr, window=window, filter_scale=filter_scale, gamma=gamma, alpha=alpha)


# 定义测试用例2
def testcase_2():
    freqs = np.array([50, 100, 150, 200])
    sr = 44100
    window = "blackman"
    filter_scale = 2
    gamma = 5
    alpha = np.array([0.1, 0.2, 0.3, 0.4])

    return wavelet_lengths(freqs=freqs, sr=sr, window=window, filter_scale=filter_scale, gamma=gamma, alpha=alpha)


# 定义测试用例3
def testcase_3():
    freqs = np.array([200, 400, 600, 800, 1000])
    sr = 16000
    window = "hamming"
    filter_scale = 0.5
    gamma = None
    alpha = None

    return wavelet_lengths(freqs=freqs, sr=sr, window=window, filter_scale=filter_scale, gamma=gamma, alpha=alpha)


# 定义测试用例4
def testcase_4():
    freqs = np.array([250, 500, 750, 1000])
    sr = 48000
    window = "bartlett"
    filter_scale = 1.5
    gamma = 10
    alpha = np.array([0.05, 0.1, 0.15, 0.2])

    return wavelet_lengths(freqs=freqs, sr=sr, window=window, filter_scale=filter_scale, gamma=gamma, alpha=alpha)


# 定义测试用例5
def testcase_5():
    freqs = np.array([300, 600, 900])
    sr = 32000
    window = "kaiser"
    filter_scale = 0.8
    gamma = 2
    alpha = np.array([0.07, 0.14, 0.21])

    return wavelet_lengths(freqs=freqs, sr=sr, window=window, filter_scale=filter_scale, gamma=gamma, alpha=alpha)


def main():
    # 执行所有测试用例
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    # 输出结果
    output = {}
    for key, result in test_results.items():
        if result["success"]:
            lengths, f_cutoff = result["result"]

            # 如果 lengths 是 ndarray 类型，则转换为列表
            if isinstance(lengths, np.ndarray):
                lengths = lengths.tolist()

            output[key] = {
                "lengths": lengths,
                "f_cutoff": f_cutoff
            }
        else:
            output[key] = {
                "error": result["error"],
                "traceback": result["traceback"]
            }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
