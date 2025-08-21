# -*- coding: utf-8 -*-
"""
修复页面文件的缩进问题
将Component格式的缩进改为Page格式
"""

import re

file_path = r"E:\ppfiles\mp\ganghaofan\client\miniprogram\pages\index\index.ts"

# 读取文件
import codecs
with codecs.open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 修复方法定义的缩进（从4个空格改为2个空格）
lines = content.split('\n')
fixed_lines = []
inside_page = False

for line in lines:
    # 检测Page({开始
    if line.strip().startswith('Page({'):
        inside_page = True
        fixed_lines.append(line)
        continue
    
    # 如果在Page内部
    if inside_page:
        # 如果是方法定义行（以4个空格开头，包含函数名和括号）
        if re.match(r'^    [a-zA-Z_][a-zA-Z0-9_]*\s*\(', line):
            # 改为2个空格
            fixed_line = '  ' + line[4:]
            fixed_lines.append(fixed_line)
            continue
        # 如果是方法内容行（以6个或更多空格开头）
        elif line.startswith('      '):
            # 减少2个空格
            fixed_line = '  ' + line[4:]
            fixed_lines.append(fixed_line)
            continue
        # 如果是结束的大括号
        elif line.strip() == '}' and len([l for l in fixed_lines if l.strip() == 'Page({']) > 0:
            inside_page = False
            fixed_lines.append(line)
            continue
    
    # 其他行保持原样
    fixed_lines.append(line)

# 写回文件
with codecs.open(file_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(fixed_lines))

print("Indentation fixed successfully!")