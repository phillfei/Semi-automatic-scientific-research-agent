#!/usr/bin/env python3
"""检查项目中的所有Python文件编码"""

import os
import sys
from pathlib import Path

def check_file_encoding(filepath):
    """检查单个文件的编码"""
    try:
        with open(filepath, 'rb') as f:
            raw = f.read()
        
        # 尝试UTF-8解码
        try:
            content = raw.decode('utf-8')
            return ('utf-8', None, content)
        except UnicodeDecodeError as e:
            # 尝试GBK解码
            try:
                content = raw.decode('gbk')
                return ('gbk', None, content)
            except:
                # 尝试GB2312
                try:
                    content = raw.decode('gb2312')
                    return ('gb2312', None, content)
                except:
                    return ('unknown', str(e), None)
    except Exception as e:
        return ('error', str(e), None)

def main():
    project_path = Path(__file__).parent
    py_files = list(project_path.rglob("*.py"))
    
    problematic = []
    fixed = []
    
    for py_file in py_files:
        # 跳过当前脚本
        if py_file.name == 'check_encoding.py':
            continue
            
        enc, err, content = check_file_encoding(py_file)
        
        if enc != 'utf-8':
            if content:
                # 可以修复
                problematic.append((str(py_file), enc, 'fixable'))
                # 自动修复
                try:
                    with open(py_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    fixed.append(str(py_file))
                except Exception as e:
                    problematic.append((str(py_file), enc, f'fix failed: {e}'))
            else:
                problematic.append((str(py_file), enc, err))
    
    # 输出结果
    print(f"\n扫描完成: 共 {len(py_files)} 个Python文件")
    print(f"已修复: {len(fixed)} 个文件")
    
    if fixed:
        print("\n已修复的文件:")
        for f in fixed:
            print(f"  ✓ {f}")
    
    if problematic:
        print(f"\n有问题但无法自动修复的文件 ({len(problematic)}):")
        for p in problematic:
            print(f"  ✗ {p[0]}: {p[1]} - {p[2]}")
    else:
        print("\n所有文件编码正常!")
    
    return len(problematic)

if __name__ == '__main__':
    sys.exit(main())