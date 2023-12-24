import string
import re
from farmhash import FarmHash32, FarmHash64
from typing import List
from collections import Counter
from prettytable import PrettyTable


# string.punctuation 返回所有的标点符号
# 效果是去除字符串中的标点符号
def del_punctuations(text: str):
    return text.translate(str.maketrans("", "", string.punctuation))


# 效果是去除字符串中的空格
def del_blank(text: str):
    return text.translate(str.maketrans('', '', ' \t\r'))


# 效果是去除定义的 prohibited words
def del_prohibited_words(text: str, prohibited_words: str):
    return re.sub('|'.join(prohibited_words), '', text)


# 效果是去除换行
def del_line_break(text: str):
    return re.sub('\n', '', text)


# 这里的text应当是去除了标点符号，prohibited words，空格
def get_line_index_table(text: str):
    idx = -1
    p = 0
    line_index_table = []  # 第i个元素的值v  代表  第i行的终止元素在处理后的字符串中的位置v
    while p < len(text):
        if text[p] != '\n':
            idx += 1
        else:
            line_index_table.append(idx)
        p += 1
    return line_index_table


def del_comments(text: str):  # TODO
    return text


def hash(text, idx, k_grams_):
    return FarmHash32(text[idx:idx + k_grams_])


def generate_fingerprints(text, k_grams_):
    fingerprints = []
    for idx in range(0, len(text) - k_grams_ + 1):
        fingerprints.append(hash(text, idx, k_grams_))
    return fingerprints


# 得到了去除了标点符号，空格，换行符，prohibited words等的字符串，也得到了line_index_table
# 所谓line_index_table就是把所有处理后的行变成一整行再标记出每一行起始处的坐标
def pre_treat(text: str, prohibited_words_: str):
    tmp_str = del_blank(del_prohibited_words(del_punctuations(del_comments(text)), prohibited_words_))
    line_index_table = get_line_index_table(tmp_str)
    tmp_str = del_line_break(tmp_str)
    return tmp_str, line_index_table


# 使用了winnowing算法
def winnowing(text: str, k_grams_: int, w_: int, prohibited_words_: str):
    tmp_str, line_index_table = pre_treat(text, prohibited_words_)
    fingerprints = generate_fingerprints(tmp_str, k_grams_)
    q = []
    i = 0
    res = []
    while i < w_ and i < len(fingerprints):
        if len(q) == 0 or fingerprints[i] > q[len(q) - 1][0]:
            q.append((fingerprints[i], i))
            i += 1
        else:
            q.pop()
    res.append(q[0])
    while i < len(fingerprints):
        if len(q) > 0 and q[0][1] == i - w_:
            q.pop(0)
        if len(q) == 0 or fingerprints[i] > q[len(q) - 1][0]:
            q.append((fingerprints[i], i))
            i += 1
            if q[0][1] != res[len(res) - 1][1]:
                res.append(q[0])
        else:
            q.pop()
    return line_index_table, res


def read_file(file_path: str):
    with open(file_path, 'r', encoding='utf-8') as f:
        s = f.read()
        return s


def handle_files(file_path_list: List[str], k_grams_, w_, prohibited_words_):
    global_fingerprints = dict()
    position_dict = dict()

    path_dict = dict()
    fingerprints_dict = dict()
    for i in range(len(file_path_list)):
        path_dict[file_path_list[i]] = i
    for path in file_path_list:
        s = read_file(path)
        if s is None:
            raise Exception("文件读取失败！ " + path)
        line_index_table, finger_prints = winnowing(s, k_grams_, w_, prohibited_words_)
        position_dict[path] = line_index_table
        fingerprints_dict[path] = finger_prints
        for pair in finger_prints:
            if global_fingerprints.get(pair[0]) == None:
                global_fingerprints[pair[0]] = [(path_dict[path], pair[1])]
            else:
                global_fingerprints[pair[0]].append((path_dict[path], pair[1]))

    matrix = [
        [0 for i in range(len(file_path_list))]
        for j in range(len(file_path_list))
    ]
    # 优雅，实在是太优雅了
    position_matrix = [
        [set() for i in range(len(file_path_list))]
        for j in range(len(file_path_list))
    ]
    for path in file_path_list:
        tmpList = []
        finger_prints = fingerprints_dict[path]
        for f in finger_prints:
            tmpList.extend(global_fingerprints[f[0]])
        for tmp in tmpList:
            start = find_line_index(position_dict[file_path_list[tmp[0]]], tmp[1])
            end = find_line_index(position_dict[file_path_list[tmp[0]]], tmp[1] + k_grams_ - 1)
            for i in range(start, end + 1):
                position_matrix[tmp[0]][path_dict[path]].add(i)

        c = Counter(map(lambda elem: elem[0], tmpList))
        for i in range(0, len(file_path_list)):
            matrix[i][path_dict[path]] = c[i] / len(fingerprints_dict[file_path_list[i]])

    res_list = []
    for i in range(len(file_path_list)):
        for j in range(len(file_path_list)):
            if i != j:
                positions = list(position_matrix[i][j])
                positions.sort()
                res_list.append((file_path_list[i], file_path_list[j], matrix[i][j], positions))
    res_list.sort(key=lambda elem: elem[2], reverse=True)
    return res_list


def find_line_index(line_index_table, position):
    l = 0
    r = len(line_index_table) - 1
    while l <= r:
        m = (l + r) // 2
        if position <= line_index_table[m]:
            r = m - 1
        else:
            l = m + 1
    return l + 1


def resultPrinter(res_list):
    table = PrettyTable(['抄袭者', '被抄袭者', '相似度', '相似行号（抄袭者）'])
    table.add_rows(res_list)
    table._max_width = {"相似行号（抄袭者）": 50}
    print(table)


if __name__ == '__main__':
    prohibited_words = ['False', 'None', 'True', 'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del',
                        'elif', 'else', 'except', 'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
                        'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try', 'while', 'with', 'yield']
    k_grams = 30
    w = 29
    filePathList = [
        "./winnowing.py",
        "./winnowing_copy1.py",
        "./winnowing_copy2.py",
        "./winnowing_copy3.py"
    ]

    resList = handle_files(filePathList, k_grams, w, prohibited_words)
    resultPrinter(resList)
    pass
