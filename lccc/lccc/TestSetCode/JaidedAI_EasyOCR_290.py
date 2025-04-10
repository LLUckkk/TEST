import json
import traceback
import threading
import queue
import time
from contextlib import contextmanager
import requests

import numpy as np


#############change###########
def group_text_box(polys, slope_ths=0.1, ycenter_ths=0.5, height_ths=0.5, width_ths=1.0, add_margin=0.05,
                   sort_output=True):
    horizontal_list, free_list, combined_list, merged_list = [], [], [], []

    for poly in polys:
        slope_up = (poly[3] - poly[1]) / np.maximum(10, (poly[2] - poly[0]))
        slope_down = (poly[5] - poly[7]) / np.maximum(10, (poly[4] - poly[6]))
        if max(abs(slope_up), abs(slope_down)) < slope_ths:
            x_max = max([poly[0], poly[2], poly[4], poly[6]])
            x_min = min([poly[0], poly[2], poly[4], poly[6]])
            y_max = max([poly[1], poly[3], poly[5], poly[7]])
            y_min = min([poly[1], poly[3], poly[5], poly[7]])
            horizontal_list.append([x_min, x_max, y_min, y_max, 0.5 * (y_min + y_max), y_max - y_min])
        else:
            height = np.linalg.norm([poly[6] - poly[0], poly[7] - poly[1]])
            width = np.linalg.norm([poly[2] - poly[0], poly[3] - poly[1]])

            margin = int(1.44 * add_margin * min(width, height))

            theta13 = abs(np.arctan((poly[1] - poly[5]) / np.maximum(10, (poly[0] - poly[4]))))
            theta24 = abs(np.arctan((poly[3] - poly[7]) / np.maximum(10, (poly[2] - poly[6]))))
            x1 = poly[0] - np.cos(theta13) * margin
            y1 = poly[1] - np.sin(theta13) * margin
            x2 = poly[2] + np.cos(theta24) * margin
            y2 = poly[3] - np.sin(theta24) * margin
            x3 = poly[4] + np.cos(theta13) * margin
            y3 = poly[5] + np.sin(theta13) * margin
            x4 = poly[6] - np.cos(theta24) * margin
            y4 = poly[7] + np.sin(theta24) * margin

            free_list.append([[x1, y1], [x2, y2], [x3, y3], [x4, y4]])
    if sort_output:
        horizontal_list = sorted(horizontal_list, key=lambda item: item[4])

    new_box = []
    for poly in horizontal_list:

        if len(new_box) == 0:
            b_height = [poly[5]]
            b_ycenter = [poly[4]]
            new_box.append(poly)
        else:
            if abs(np.mean(b_ycenter) - poly[4]) < ycenter_ths * np.mean(b_height):
                b_height.append(poly[5])
                b_ycenter.append(poly[4])
                new_box.append(poly)
            else:
                b_height = [poly[5]]
                b_ycenter = [poly[4]]
                combined_list.append(new_box)
                new_box = [poly]
    combined_list.append(new_box)

    for boxes in combined_list:
        if len(boxes) == 1:
            box = boxes[0]
            margin = int(add_margin * min(box[1] - box[0], box[5]))
            merged_list.append([box[0] - margin, box[1] + margin, box[2] - margin, box[3] + margin])
        else:
            boxes = sorted(boxes, key=lambda item: item[0])

            merged_box, new_box = [], []
            for box in boxes:
                if len(new_box) == 0:
                    b_height = [box[5]]
                    x_max = box[1]
                    new_box.append(box)
                else:
                    if (abs(np.mean(b_height) - box[5]) < height_ths * np.mean(b_height)) and (
                            (box[0] - x_max) < width_ths * (box[3] - box[2])):
                        b_height.append(box[5])
                        x_max = box[1]
                        new_box.append(box)
                    else:
                        b_height = [box[5]]
                        x_max = box[1]
                        merged_box.append(new_box)
                        new_box = [box]
            if len(new_box) > 0: merged_box.append(new_box)

            for mbox in merged_box:
                if len(mbox) != 1:
                    x_min = min(mbox, key=lambda x: x[0])[0]
                    x_max = max(mbox, key=lambda x: x[1])[1]
                    y_min = min(mbox, key=lambda x: x[2])[2]
                    y_max = max(mbox, key=lambda x: x[3])[3]

                    box_width = x_max - x_min
                    box_height = y_max - y_min
                    margin = int(add_margin * (min(box_width, box_height)))

                    merged_list.append([x_min - margin, x_max + margin, y_min - margin, y_max + margin])
                else:
                    box = mbox[0]

                    box_width = box[1] - box[0]
                    box_height = box[3] - box[2]
                    margin = int(add_margin * (min(box_width, box_height)))

                    merged_list.append([box[0] - margin, box[1] + margin, box[2] - margin, box[3] + margin])
    return merged_list, free_list


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
    polys = [
        [10, 20, 30, 40, 50, 60, 70, 80],
        [15, 25, 35, 45, 55, 65, 75, 85],
        [20, 30, 40, 50, 60, 70, 80, 90]
    ]
    slope_ths = 0.1
    ycenter_ths = 0.5
    height_ths = 0.5
    width_ths = 1.0
    add_margin = 0.05
    sort_output = True

    return group_text_box(polys, slope_ths, ycenter_ths, height_ths, width_ths, add_margin, sort_output)


# 定义测试用例2
def testcase_2():
    polys = [
        [100, 200, 300, 400, 500, 600, 700, 800],
        [110, 210, 310, 410, 510, 610, 710, 810],
        [120, 220, 320, 420, 520, 620, 720, 820]
    ]
    slope_ths = 0.2
    ycenter_ths = 0.6
    height_ths = 0.4
    width_ths = 1.2
    add_margin = 0.1
    sort_output = False

    return group_text_box(polys, slope_ths, ycenter_ths, height_ths, width_ths, add_margin, sort_output)


# 定义测试用例3
def testcase_3():
    polys = [
        [50, 60, 70, 80, 90, 100, 110, 120],
        [55, 65, 75, 85, 95, 105, 115, 125],
        [60, 70, 80, 90, 100, 110, 120, 130]
    ]
    slope_ths = 0.05
    ycenter_ths = 0.4
    height_ths = 0.6
    width_ths = 0.8
    add_margin = 0.02
    sort_output = True

    return group_text_box(polys, slope_ths, ycenter_ths, height_ths, width_ths, add_margin, sort_output)


# 定义测试用例4
def testcase_4():
    polys = [
        [200, 300, 400, 500, 600, 700, 800, 900],
        [210, 310, 410, 510, 610, 710, 810, 910],
        [220, 320, 420, 520, 620, 720, 820, 920]
    ]
    slope_ths = 0.15
    ycenter_ths = 0.55
    height_ths = 0.45
    width_ths = 1.1
    add_margin = 0.07
    sort_output = False

    return group_text_box(polys, slope_ths, ycenter_ths, height_ths, width_ths, add_margin, sort_output)


# 定义测试用例5
def testcase_5():
    polys = [
        [30, 40, 50, 60, 70, 80, 90, 100],
        [35, 45, 55, 65, 75, 85, 95, 105],
        [40, 50, 60, 70, 80, 90, 100, 110]
    ]
    slope_ths = 0.08
    ycenter_ths = 0.5
    height_ths = 0.5
    width_ths = 1.0
    add_margin = 0.05
    sort_output = True

    return group_text_box(polys, slope_ths, ycenter_ths, height_ths, width_ths, add_margin, sort_output)


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
