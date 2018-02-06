# -*- coding: utf-8 -*-

"""
搜索并翻译未处理文字，有两种翻译方式一种是百度翻译，一种是tool.lu在线工具翻译
"""

import os
import glob
import re
import sys
import getopt
import requests
import random
import hashlib
import time
import uniout


# 默认项目路径和搜索路径,搜索路径是项目路径的相对路径
DEFAULT_ROJECT_PATH = 'xxxx'
DEFAULT_SEARCH_PATH = 'xxxx'
# 过滤文件目录（相对路径），过滤文件
Filter_DIRS = ['xxxx']
Filter_FILES = ['xxxx.m',
                'xxxx.h']
# 语言文件
LOCALIZE_STRING_FILE_NAME = 'xxxx.strings'
# 百度翻译
APP_ID = ''
SECRET_KEY = ''
# 自动添加 .localized
IS_AUTO_HANDLE = False
# 正则表达式(匹配需要翻译的汉字)
String_PATTERN = u'(' \
          + u'(?<!Log\()' \
          + u'(?<!Print\()' \
          + u'(?<!description:)' \
          + u'(?<!DDLogError\()' \
          + u'(?<!DDLogWarn\()' \
          + u'(?<!DDLogInfo\()' \
          + u'(?<!DDLogDebug\()' \
          + u'(?<!DDLogVerbose\()' \
          + u'@\"[^\"]*[\u4e00-\u9fa5]+[^\"]*\"(?!\\.localized))'
# 过滤以某些开头的行
LINE_PATTERN = u'(?=//' \
               + u'|NSLog' \
               + u'|DDLogError' \
               + u'|DDLogWarn' \
               + u'|DDLogDebug' \
               + u'|DDLogVerbose)'


class FileModel:
    """
    文件模型
    path 路径
    texts 文字集合
    find 匹配对象
    """
    def __init__(self, path):
        self.path = path
        self.texts = list()
        self.finds = list()


class TextModel:
    """
    目标字符串
    simplified 简体
    line 行数
    """
    def __init__(self, text, line, match):
        self.text = text
        self.line = line
        self.match = match


def find_files_by_name(path, filename):
    """
    通过文件名搜索到文件
    """
    paths = []
    for root, dirs, files in os.walk(path):
        if LOCALIZE_STRING_FILE_NAME in files:
            paths.append(os.path.join(root, filename))
    return paths


def find_all_source_files(path):
    """
    遍历出所有源文件
    """
    if os.path.isfile(path):
        yield path
    else:
        for root, dirs, files in os.walk(path):
            if is_filter_the_dir(root):
                continue
            for file_path in glob.glob(root + r'/*.m'):
                if not is_filter_the_file(file_path):
                    yield file_path


def is_filter_the_dir(path):
    """
    过滤目录
    """
    for filter_dir in Filter_DIRS:
        if filter_dir in path:
            return True
    return False


def is_filter_the_file(path):
    """
    过滤文件
    """
    name = os.path.basename(path)
    for filter_file in Filter_FILES:
        if name == filter_file:
            return True
    return False


def if_filter_the_line(string):
    """
    过滤行
    """
    return re.match(LINE_PATTERN, unicode(string.lstrip(), 'utf-8'))


def get_localize_file_by_type(path, language):
    """
    获取不同语言文件 zh-Hans, zh-Hant-HK
    """
    localize_paths = find_files_by_name(path, LOCALIZE_STRING_FILE_NAME)

    directory = language + '.lproj'
    for path in localize_paths:
        if directory in path:
            return path


def sub_at_symbol(string):
    """
    去掉前缀@符号
    """
    if len(string) > 1:
        return string[1:]
    else:
        return string


def sub_quote_symbol(string):
    """
    去掉两端冒号
    """
    if len(string) > 2:
        return string[1:-1]
    else:
        return string


def create_file_model(path):
    """
    创建FileModel
    """
    file_object = open(path, 'rb')
    file_model = FileModel(path)
    try:
        line = 0
        skip_line = 0
        while 1:
            line_text = file_object.readline()
            if not line_text:
                break
            line += 1
            # 过滤/* */注释
            if re.match('^(/\*).*', line_text.lstrip()):
                skip_line += 1
            if skip_line > 0:
                if re.match('.*(\*/)$', line_text.lstrip()):
                    skip_line -= 1
                continue
            # 过滤这行
            if if_filter_the_line(line_text):
                continue
            line_text = unicode(line_text, 'utf-8')
            for m in re.finditer(String_PATTERN, line_text):
                text = sub_at_symbol(m.group().encode("utf-8"))
                file_model.texts.append(text)
                file_model.finds.append(TextModel(text, line, m))
    finally:
        file_object.close()
    if not len(file_model.finds) == 0:
        print('\n%s' % path)
        for text_model in file_model.finds:
            print ("有未处理翻译字符在第 %s行 [%s]" % (str(text_model.line).center(5), text_model.text))
    return file_model


def filter_exist_localized_string(path, strings):
    """
    过滤已经翻译过的
    """
    file_object = open(path, 'rb')
    strings = list(set(strings))
    try:
        while 1:
            line = file_object.readline()
            if not line:
                break
            for string in strings:
                if string not in line:
                    continue
                strings.remove(string)
    finally:
        file_object.close()
    return strings


def baidu_translate_chinese_string(string):
    """
    翻译成繁体-百度翻译
    """
    url = 'http://api.fanyi.baidu.com/api/trans/vip/translate'
    salt = random.randint(32768, 65536)
    sign = APP_ID + string + str(salt) + SECRET_KEY
    m1 = hashlib.md5()
    m1.update(sign)
    sign = m1.hexdigest()
    params = dict()
    params['appid'] = APP_ID
    params['q'] = string
    params['from'] = 'zh'
    params['to'] = 'cht'
    params['salt'] = salt
    params['sign'] = sign

    r = requests.get(url, params)
    return r.json()['trans_result'][0]['dst'].encode("utf-8")


def tool_lu_translate_chinese_string(string, retry=0):
    """
    翻译成繁体-tool.lu在线工具
    """
    if retry == 3:
        print "实在等不了，过会再试试吧！"
        exit()
    url = 'https://tool.lu/zhconvert/ajax.html'
    params = dict()
    params['code'] = string
    params['operate'] = 'zh-hk'
    r = requests.post(url, params)
    if not r.json() is None:
        return r.json()['text'].encode("utf-8")
    else:
        print "太快啦，慢一点？2秒后我再试试"
        time.sleep(2)
        return tool_lu_translate_chinese_string(string, retry+1)


def composing_line_string(string1, string2):
    """
    组装文字
    """
    return "\"" + string1 + "\"" + "=" + "\"" + string2 + "\"" + ";\n"


def write_chinese_string(path, string):
    """
    写入文字
    """
    with open(path, mode="a") as data:
        data.write(string)


def auto_handle_localized(filemodel):
    """
    自动添加 '.localized'
    """
    with open(filemodel.path, 'r') as f:
        lines = f.readlines()
    with open(filemodel.path, 'w') as f_w:
        line = 0
        for line_text in lines:
            line += 1
            offset = 0
            unicode_line = unicode(line_text, 'utf-8')
            for text_model in filemodel.finds:
                if text_model.line == line:
                    end = text_model.match.end() + offset
                    offset += len(u'.localized')
                    tmp = list(unicode_line)[:end] + list(u'.localized') + list(unicode_line)[end:]
                    unicode_line = ''.join(tmp)
            f_w.write(unicode_line.encode('utf-8'))


def get_project_search_path():
    """
    获取项目路径和搜索路径
    默认项目路径不存在情况下使用脚本所在路径搜索
    如果指定了项目路径使用指定的项目路径
    """
    opts, args = getopt.getopt(sys.argv[1:], "vhp:s:")
    path1 = DEFAULT_ROJECT_PATH
    if not os.path.exists(path1):
        path1 = sys.path[0]
    path2 = DEFAULT_SEARCH_PATH
    if not (path1 in path2):
        path2 = path1+path2
    if not os.path.exists(path2):
        path2 = ""
    for op, value in opts:
        if op == "-p":
            path1 = value
        elif op == "-s":
            path2 = value
        elif op == "-v":
            print ("1.0.0")
            sys.exit()
        elif op == "-h":
            print ("\t-p\t项目路径 \n\t-s\t搜索路径（可以是文件，也可以是目录）")
            sys.exit()
    # 如果搜索路径不是绝对路径，补充完整
    if not (path1 in path2):
        path2 = path1 + path2
    return path1, path2


if __name__ == "__main__":

    project_path, search_path = get_project_search_path()

    if not os.path.exists(project_path):
        print ("请检查项目路径：%s是否正确" % project_path)
        exit()
    if not os.path.exists(search_path):
        print ("请检查搜索路径：%s是否正确" % search_path)
        exit()

    zh_localize_path = get_localize_file_by_type(project_path, 'zh-Hans')
    hk_localize_path = get_localize_file_by_type(project_path, 'zh-Hant-HK')

    if zh_localize_path is None or hk_localize_path is None:
        print ("请检查 LOCALIZE_STRING_FILE_NAME 参数")
        exit()

    print("开始搜索未翻译文案")

    untreated_files = list()
    wait_translates = list()

    for filepath in find_all_source_files(search_path):
        untreated_file_model = create_file_model(filepath)
        if len(untreated_file_model.texts) == 0:
            continue
        wait_translates += untreated_file_model.texts
        untreated_files.append(untreated_file_model)

    if len(untreated_files) == 0:
        print ("\n没有需要处理的文字")
        exit()

    wait_translates = filter_exist_localized_string(zh_localize_path, wait_translates)

    if not len(wait_translates) == 0:
        num = 0
        print ("\n待翻译文字 %s\n" % wait_translates)
        for simplified in wait_translates:
            simplified = sub_quote_symbol(simplified)
            traditional = tool_lu_translate_chinese_string(simplified)
            write_chinese_string(zh_localize_path, composing_line_string(simplified, simplified))
            write_chinese_string(hk_localize_path, composing_line_string(simplified, traditional))
            num += 1
            print simplified + "=" + traditional
            print ('已翻译 %d/%d' % (num, len(wait_translates)))
        print ('\n翻译完成')
    else:
        print ('\n没有需要翻译的文字')

    if not IS_AUTO_HANDLE:
        exit()

    print ('\n开始自动处理\n')

    for untreated_file_model in untreated_files:
        print ('正在处理：%s' % os.path.basename(untreated_file_model.path))
        auto_handle_localized(untreated_file_model)

    print ('\n自动处理完成')
