# LocalizeString-iOS
iOS项目自动国际化脚本

找出项目中所有中文字符串文案，并自动翻译成繁体写入到国际化文件中。(不支持xib)

python依赖

```
pip install requests
pip install uniout
```


配置

`LOCALIZE_STRING_FILE_NAME`（国际化语言文件名） 这个是必须配置的。


使用方法：


```python 
python LocalizeString.py -p 项目目录 -s 需要批量翻译的目录
```

也可以在 `LocalizeString.py` 配置默认参数

