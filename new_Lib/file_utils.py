# file_utils.py
from pathlib import Path


def markdown_to_string_path(markdown_path):
    """
    从指定路径读取 Markdown 文件内容并返回字符串。
    
    参数:
        markdown_path: Markdown 文件路径
        
    返回:
        str: 文件内容
        
    异常:
        FileNotFoundError: 文件不存在时抛出
    """
    path = Path(markdown_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {path}")
    if path.suffix.lower() != '.md':
        print(f"警告: 文件 '{path}' 可能不是Markdown文件")
    return path.read_text(encoding='utf-8')


def string_to_markdown_path(content, markdown_path, overwrite=True):
    """
    将字符串内容保存到指定的 Markdown 文件路径。
    
    参数:
        content: 要保存的内容
        markdown_path: 目标文件路径
        overwrite: 是否覆盖已存在的文件（默认 True）
        
    返回:
        bool: 成功返回 True
        
    异常:
        FileExistsError: 文件已存在且 overwrite=False 时抛出
    """
    path = Path(markdown_path)
    if path.suffix.lower() != '.md':
        path = path.with_suffix('.md')
    if path.exists() and not overwrite:
        raise FileExistsError(f"文件已存在: {path}，设置 overwrite=True 来覆盖")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    print(f"成功将内容保存到: {path}")
    return True

