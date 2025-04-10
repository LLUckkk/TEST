# TEST

记录实验中遇到的问题和解决方法：

+ 已经下载了库但仍然报错

  + subprocess执行的时候使用的是默认的python解释器，替换为当前的python解释器即可

    ```python
    result = subprocess.run(
        [sys.executable, filename],  # ✅ 用当前解释器执行
    ```

+ test文件里面除了ans1-5不要有额外的打印