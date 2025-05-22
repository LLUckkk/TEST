import os
import json
import re
import sys
import subprocess
import time
from typing import List, Dict


def load_dataset_json(file_path: str):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_call_func(func_header):
    # 提取函数名和参数部分
    func_name = func_header.split("def ")[1].split("(")[0]  # 得到 "modulate"
    params_part = func_header.split("(")[1].split(")")[0]  # 得到 "x, shift=None, scale=None"

    # 移除参数中的默认值（去掉 =None 部分）
    params = [p.split("=")[0].strip().split(":")[0].strip() for p in params_part.split(",")]
    clean_params = ", ".join(params)  # 得到 "x, shift, scale"

    # 组合成调用字符串
    call_str = f"{func_name}({clean_params})"  # 得到 "modulate(x, shift, scale)"
    print(call_str)
    return call_str


def fix_indentation_simple(code: str) -> str:
    """如果 def 前面有缩进，则整体往前移动相同空格数"""
    seperate_str = "#############change###########\n"

    lines = code.split('\n')
    if not lines:
        return seperate_str + code + "\n" + seperate_str

    # 检查第一个 def 的缩进
    first_def_line = next((line for line in lines if line.lstrip().startswith('def ')), None)
    if not first_def_line:
        return seperate_str + code + "\n" + seperate_str  # 没有函数定义，直接返回

    # 计算缩进量（def 前面的空格数）
    indent = len(first_def_line) - len(first_def_line.lstrip())
    if indent == 0:
        return seperate_str + code + "\n" + seperate_str  # 已经顶格，无需处理

    # 整体往前移动缩进
    fixed_lines = []
    for line in lines:
        if line.startswith(' ' * indent):
            fixed_lines.append(line[indent:])  # 去掉缩进
        elif line.strip() == '':
            fixed_lines.append('')  # 空行保留
        else:
            fixed_lines.append(line)  # 其他情况（如注释）不做处理

    new_code = '\n'.join(fixed_lines)
    new_code = seperate_str + new_code + "\n" + seperate_str
    return new_code


def _extract_libraries(import_text: str) -> List[str]:
    """从文本中提取需要import的库名"""
    # 匹配以下模式：
    # 1. import xxx
    # 2. import xxx as yy
    # 3. from xxx import yy
    patterns = [
        r'^\s*import\s+(\w+)',
        r'^\s*from\s+(\w+)\s+import'
    ]
    libraries = set()
    for pattern in patterns:
        matches = re.findall(pattern, import_text, re.MULTILINE)
        for match in matches:
            lib = match if isinstance(match, str) else match[0]
            if lib:  # 忽略空匹配
                libraries.add(lib)

    return sorted(libraries)  # 返回按字母排序的列表


def check_and_install_libraries(needimport: str, max_retries: int = 3) -> None:
    """从 import 语句提取库名并检查安装（支持重试和镜像源切换）
    
    Args:
        needimport: 包含import语句的字符串
        max_retries: 最大重试次数（默认3次）
    """
    # 国内镜像源列表（优先级从高到低）
    MIRROR_SOURCES = [
        "https://pypi.tuna.tsinghua.edu.cn/simple",
        "https://mirrors.aliyun.com/pypi/simple",
        "https://pypi.mirrors.ustc.edu.cn/simple",
        ""  # 最后尝试官方源
    ]

    # 提取需要安装的库列表
    libraries = _extract_libraries(needimport)

    for lib in libraries:
        print(f"🔍 检查库: {lib}")
        try:
            # 先尝试直接导入
            __import__(lib)
            print(f"✅ 库 '{lib}' 已安装")
            continue
        except ImportError:
            print(f"⚠️ 库 '{lib}' 未安装，开始自动安装...")

            # 尝试用不同镜像源安装
            installed = False
            last_error = None

            for attempt in range(max_retries):
                for mirror in MIRROR_SOURCES:
                    try:
                        # 构建安装命令
                        cmd = [sys.executable, "-m", "pip", "install", lib]
                        if mirror:
                            cmd.extend(["-i", mirror, "--trusted-host", mirror.split("//")[1]])

                        print(f"🔄 尝试安装 ({attempt + 1}/{max_retries}) [源: {mirror or '官方'}]")

                        # 执行安装（增加超时时间）
                        subprocess.run(
                            cmd,
                            check=True,
                            timeout=300,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            encoding='utf-8',
                            text=True
                        )

                        print(f"✅ 成功安装 '{lib}'")
                        installed = True
                        break

                    except subprocess.TimeoutExpired:
                        last_error = f"安装超时（尝试 {attempt + 1}/{max_retries}）"
                        print(f"⏳ {last_error}")
                    except subprocess.CalledProcessError as e:
                        last_error = f"安装失败: {e.stderr.strip() or e.stdout.strip()}"
                        print(f"⚠️ {last_error}")

                    # 等待2秒后重试
                    if attempt < max_retries - 1:
                        time.sleep(2)

                if installed:
                    break

            # 所有重试失败后的处理
            if not installed:
                raise RuntimeError(
                    f"❌ 无法安装库 '{lib}'，请手动执行:\n"
                    f"pip install {lib} -i {MIRROR_SOURCES[0]}\n"
                    f"最后错误: {last_error}"
                )

    print(f"✅ 全部检查完毕")


def save_test_code(filename, output_code):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(output_code)
    print(f"已保存文件: {filename}")


def save_item_to_json(item: dict, filename: str) -> None:
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(item, f, indent=2, ensure_ascii=False)  # 美化格式，支持中文

    print(f"✅ Item 已保存到 {filename}")


def fill_template(template_path, replacements):
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()

    # 确保有7个占位符和6个替换
    assert template.count('{}') == 7
    assert len(replacements) == 7

    # 分割模板
    parts = template.split('{}')

    # 插入替换值
    filled = []
    for i in range(7):
        filled.append(parts[i])
        filled.append(str(replacements[i]))  # 确保转换为字符串

    # 添加最后部分
    if len(parts) > 7:
        filled.append(parts[7])

    return ''.join(filled)


def solve(dataset: Dict[str, Dict]) -> Dict[str, List[Dict]]:
    cnt = 1
    index = 425  # 该426了先吃饭

    for item_key in dataset:
        if cnt < index:
            cnt += 1
            continue

        if cnt > index:
            break

        # 生成代码
        item = dataset[item_key]  # 获取这个 key 对应的 value（是一个 dict）

        call_func = get_call_func(item["input_header"])
        generated_inputs = item["generated_inputs"][0]
        if not generated_inputs == "None":
            needimport = generated_inputs.split("<needimport>\n")[1].split("<testcase_1>")[0]
        else:
            print("no generated_inputs")
            break

        replacements = []
        replacements.append(needimport)
        replacements.append(fix_indentation_simple(item["output_code"]))
        selfstr = "    class Dummy:\n        pass\n    self = Dummy()\n"
        for i in range(1, 6):
            testcase_str_now = f"<testcase_{i}>\n"
            testcase_str_next = f"\n<testcase_{i + 1}>"
            if testcase_str_now in generated_inputs:
                str1 = generated_inputs.split(testcase_str_now)[1]
            else:
                replacements.append("    return")
                continue

            if testcase_str_next in str1:
                str1 = str1.split(testcase_str_next)[0]
            else:
                str1 += "\n"
            indentline = []
            for line in str1.split('\n'):
                if i == 1:
                    print("    " + line.lstrip())
                indentline.append("    " + line)

            testcase_code = '\n'.join(indentline) + "\n" + f"    return {call_func}"
            if "self" in call_func:
                testcase_code = selfstr + testcase_code
            replacements.append(testcase_code)

        output_code = fill_template("TestSetCode/example_style.py", replacements)

        # 2. 将 output_code 写入文件
        filename = os.path.join("TestSetCode", f"{item_key}.py")
        save_test_code(filename, output_code)

        # 3. 检查依赖        
        check_and_install_libraries(needimport)

        exec_result = execute_test_code(filename)
        if exec_result["success"]:
            item["needimport"] = needimport
            item["test_results"] = exec_result["results"]  # 保存 ans1-ans5
            output_filename = f"TestSetOutput/{item_key}.json"  # 按 item_key 命名文件
            save_item_to_json(item, output_filename)
        else:
            print(exec_result)

        cnt += 1


def execute_test_code(filename):
    try:
        result = subprocess.run(
            [sys.executable, filename],
            capture_output=True,
            text=True,
            encoding='utf-8',
            check=True
        )
        # 解析标准输出的最后一行（JSON字符串）
        print("完整输出：\n" + result.stdout)
        output_line = result.stdout.strip().split('\n')[-1]
        ans_data = json.loads(result.stdout)  # 转为字典
        # with open('output.json', 'r', encoding='utf-8') as f:
        #     ans_data = json.load(f)
        print(f"执行成功:\n{result.stdout}")

        return {
            "success": True,
            "results": ans_data
        }

    except subprocess.CalledProcessError as e:
        print(f"执行失败:\n{e.stderr}")
        return {
            "success": False,
            "error": str(e),
            "stdout": result.stdout if 'result' in locals() else "",
            "stderr": result.stderr if 'result' in locals() else ""
        }


if __name__ == "__main__":
    input_file = "function_testcase.jsonl"
    data = load_dataset_json(input_file)
    solve(data)
