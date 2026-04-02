"""
文件编码工具

确保所有生成的文件使用 UTF-8 编码
"""

import os
import chardet
from pathlib import Path
from typing import List, Tuple


def ensure_utf8(filepath: str, content: str = None) -> bool:
    """
    确保文件以 UTF-8 编码保存
    
    Args:
        filepath: 文件路径
        content: 要写入的内容（如果为 None 则只检查）
        
    Returns:
        是否成功
    """
    try:
        if content is not None:
            # 确保内容有 UTF-8 声明
            if not content.startswith('# -*- coding:'):
                content = '# -*- coding: utf-8 -*-\n' + content
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # 验证编码
        with open(filepath, 'rb') as f:
            raw = f.read()
            result = chardet.detect(raw)
            encoding = result.get('encoding', '').lower()
            
            # 检查是否是 UTF-8 或 ASCII（ASCII 是 UTF-8 的子集）
            if encoding in ['utf-8', 'ascii', 'utf-8-sig']:
                return True
            else:
                print(f"⚠️ 文件 {filepath} 编码为 {encoding}，建议转换为 UTF-8")
                return False
                
    except Exception as e:
        print(f"❌ 处理文件 {filepath} 时出错: {e}")
        return False


def check_directory_encoding(directory: str) -> List[Tuple[str, str]]:
    """
    检查目录下所有 Python 文件的编码
    
    Args:
        directory: 目录路径
        
    Returns:
        文件和编码的列表
    """
    results = []
    path = Path(directory)
    
    for py_file in path.rglob('*.py'):
        try:
            with open(py_file, 'rb') as f:
                raw = f.read()
                result = chardet.detect(raw)
                encoding = result.get('encoding', 'unknown')
                confidence = result.get('confidence', 0)
                
                results.append((str(py_file), encoding, confidence))
                
        except Exception as e:
            results.append((str(py_file), f"error: {e}", 0))
    
    return results


def convert_to_utf8(filepath: str) -> bool:
    """
    将文件转换为 UTF-8 编码
    
    Args:
        filepath: 文件路径
        
    Returns:
        是否成功
    """
    try:
        # 检测当前编码
        with open(filepath, 'rb') as f:
            raw = f.read()
            result = chardet.detect(raw)
            source_encoding = result.get('encoding', 'utf-8')
        
        # 读取并转换
        with open(filepath, 'r', encoding=source_encoding) as f:
            content = f.read()
        
        # 添加 UTF-8 声明（如果是 Python 文件且没有声明）
        if filepath.endswith('.py') and not content.startswith('# -*- coding:'):
            content = '# -*- coding: utf-8 -*-\n' + content
        
        # 以 UTF-8 写入
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 已转换: {filepath} ({source_encoding} -> UTF-8)")
        return True
        
    except Exception as e:
        print(f"❌ 转换失败: {filepath} - {e}")
        return False


# 便捷函数
def write_python_file(filepath: str, content: str, ensure_utf8_header: bool = True) -> bool:
    """
    写入 Python 文件，确保 UTF-8 编码
    
    Args:
        filepath: 文件路径
        content: 文件内容
        ensure_utf8_header: 是否确保有 UTF-8 声明
        
    Returns:
        是否成功
    """
    try:
        # 确保有 UTF-8 声明
        if ensure_utf8_header and not content.startswith('# -*- coding:'):
            content = '# -*- coding: utf-8 -*-\n\n' + content
        
        # 创建目录
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # 写入文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True
        
    except Exception as e:
        print(f"❌ 写入文件失败: {filepath} - {e}")
        return False


def read_python_file(filepath: str) -> str:
    """
    读取 Python 文件，自动检测编码
    
    Args:
        filepath: 文件路径
        
    Returns:
        文件内容
    """
    try:
        # 尝试 UTF-8
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            pass
        
        # 检测编码
        with open(filepath, 'rb') as f:
            raw = f.read()
            result = chardet.detect(raw)
            encoding = result.get('encoding', 'utf-8')
        
        # 使用检测到的编码读取
        with open(filepath, 'r', encoding=encoding) as f:
            return f.read()
            
    except Exception as e:
        print(f"❌ 读取文件失败: {filepath} - {e}")
        return ""
