# TEST

记录实验中遇到的问题和解决方法：

+ 已经下载了库但仍然报错

  + subprocess执行的时候使用的是默认的python解释器，替换为当前的python解释器即可

    ```python
    result = subprocess.run(
        [sys.executable, filename],  # ✅ 用当前解释器执行
    ```

+ gruns_icecream_36，测试函数调用的是外部的函数，根据函数名写了一个函数模拟这个行为