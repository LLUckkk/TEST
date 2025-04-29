import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import pydub
from pydub.generators import Sine


#############change###########
def split_to_mono(self):
    if self.channels == 1:
        return [self]

    samples = self.get_array_of_samples()

    mono_channels = []
    for i in range(self.channels):
        samples_for_current_channel = samples[i::self.channels]

        try:
            mono_data = samples_for_current_channel.tobytes()
        except AttributeError:
            mono_data = samples_for_current_channel.tostring()

        mono_channels.append(
            self._spawn(mono_data, overrides={"channels": 1, "frame_width": self.sample_width})
        )

    return mono_channels


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
    event = threading.Event()

    def worker():
        try:
            with request_context() as session:
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
            event.set()

    t = threading.Thread(target=worker)
    t.daemon = True

    start_time = time.time()
    t.start()

    while time.time() - start_time < timeout:
        if event.is_set() or not result_queue.empty():
            break
        time.sleep(0.1)

    event.set()

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
    audio_segment = Sine(440).to_audio_segment(duration=1000).set_channels(2)
    return split_to_mono(audio_segment)


# 定义测试用例2
def testcase_2():
    audio_segment = Sine(1000).to_audio_segment(duration=500).set_channels(2)
    return split_to_mono(audio_segment)


# 定义测试用例3
def testcase_3():
    audio_segment = Sine(250).to_audio_segment(duration=2000).set_channels(2)
    return split_to_mono(audio_segment)


# 定义测试用例4
def testcase_4():
    audio_segment = Sine(500).to_audio_segment(duration=1500).set_channels(2)
    return split_to_mono(audio_segment)


# 定义测试用例5
def testcase_5():
    audio_segment = Sine(750).to_audio_segment(duration=3000).set_channels(2)
    return split_to_mono(audio_segment)


def main():
    # 执行所有测试用例
    test_results = {
        "ans1": safe_execute_testcase(testcase_1, timeout=5),
        "ans2": safe_execute_testcase(testcase_2, timeout=5),
        "ans3": safe_execute_testcase(testcase_3, timeout=5),
        "ans4": safe_execute_testcase(testcase_4, timeout=5),
        "ans5": safe_execute_testcase(testcase_5, timeout=5)
    }

    def serialize_audio_segments(result):
        if result is None:
            return None
        return [f"<AudioSegment {i}: duration={seg.duration_seconds:.2f}s, channels={seg.channels}>" for i, seg in
                enumerate(result)]

    output = {
        "ans1": serialize_audio_segments(test_results["ans1"]["result"]) if test_results["ans1"]["success"] else None,
        "ans2": serialize_audio_segments(test_results["ans2"]["result"]) if test_results["ans2"]["success"] else None,
        "ans3": serialize_audio_segments(test_results["ans3"]["result"]) if test_results["ans3"]["success"] else None,
        "ans4": serialize_audio_segments(test_results["ans4"]["result"]) if test_results["ans4"]["success"] else None,
        "ans5": serialize_audio_segments(test_results["ans5"]["result"]) if test_results["ans5"]["success"] else None
    }

    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
