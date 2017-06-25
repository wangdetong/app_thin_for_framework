# app_thin_for_framework
[app瘦身之移除无用macho文件](https://wangdetong.github.io/2017/06/25/app%E7%98%A6%E8%BA%AB%E4%B9%8B%E7%A7%BB%E9%99%A4%E6%97%A0%E7%94%A8macho%E6%96%87%E4%BB%B6/)

作用：
> app thin : remove needless  mach-o file for static framework with python script

>1，通过执行该脚本，可以自动移除项目中的所有第三方framework可以移除的mach-o，达到瘦身的目的。

>2，如果整个framework在项目中都没有使用的话，需要手动删除，它的信息在log.txt（在项目目录下生成的log信息文件）中

使用python脚本的规范如下：

``` python
# python thin_framework.py project_path target_folder_path

# 0 : python_script_path 【必填】
# 1 : project_path 		 【必填】
# 2 : target_folder_path 【选填】需要检查 Framework的文件夹，默认为 project_path
```
举个例子，在命令行输入：

```
> python thin_framework.py '/Users/wangdt/XcodeSpace/TestView'

```

注意：当前demo没有使用workspace，如果使用workspace需要修改python 中编译项目的命令： xcodebuild的方式。