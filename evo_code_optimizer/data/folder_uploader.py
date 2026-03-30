"""
文件夹上传和批量处理模块
支持递归扫描、批量读取音频文件
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Union, Callable, Iterator, Tuple
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
from tqdm import tqdm
import json


@dataclass
class FileInfo:
    """文件信息数据类"""
    path: Path
    relative_path: Path  # 相对于根目录的路径
    filename: str
    size_bytes: int
    md5_hash: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    
    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)


@dataclass
class BatchLoadResult:
    """批量加载结果"""
    files: List[FileInfo]
    successful: List[Path]
    failed: List[Tuple[Path, str]]  # (path, error_message)
    audio_data: Dict[Path, np.ndarray]  # path -> audio array
    metadata_df: Optional[pd.DataFrame] = None


class FolderUploader:
    """
    文件夹上传管理器
    支持递归扫描、批量处理、进度跟踪
    """
    
    # 支持的音频格式
    SUPPORTED_AUDIO_EXTS = {'.ogg', '.wav', '.mp3', '.flac', '.m4a', '.webm', '.ipynb'}
    
    def __init__(self, 
                 supported_extensions: Optional[set] = None,
                 max_workers: int = 4,
                 chunk_size: int = 8192):
        """
        Args:
            supported_extensions: 支持的文件扩展名集合
            max_workers: 并行处理的最大线程数
            chunk_size: 读取文件的块大小
        """
        self.supported_extensions = supported_extensions or self.SUPPORTED_AUDIO_EXTS
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        
    def scan_folder(self, 
                    folder_path: Union[str, Path],
                    pattern: Optional[str] = None,
                    recursive: bool = True) -> List[FileInfo]:
        """
        扫描文件夹中的所有音频文件
        
        Args:
            folder_path: 文件夹路径
            pattern: 可选的文件名匹配模式 (如 "*.ogg")
            recursive: 是否递归扫描子文件夹
            
        Returns:
            List[FileInfo]: 文件信息列表
        """
        folder_path = Path(folder_path)
        if not folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")
        
        files = []
        
        if pattern:
            # 使用通配符模式
            if recursive:
                matched_paths = folder_path.rglob(pattern)
            else:
                matched_paths = folder_path.glob(pattern)
        else:
            # 扫描所有支持的音频格式
            matched_paths = []
            for ext in self.supported_extensions:
                if recursive:
                    matched_paths.extend(folder_path.rglob(f"*{ext}"))
                else:
                    matched_paths.extend(folder_path.glob(f"*{ext}"))
        
        for path in matched_paths:
            if path.is_file():
                relative = path.relative_to(folder_path)
                file_info = FileInfo(
                    path=path,
                    relative_path=relative,
                    filename=path.name,
                    size_bytes=path.stat().st_size
                )
                files.append(file_info)
        
        # 按路径排序
        files.sort(key=lambda x: str(x.path))
        
        return files
    
    def compute_md5(self, file_path: Path) -> str:
        """计算文件的 MD5 哈希"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(self.chunk_size), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def upload_folder(self,
                      source_folder: Union[str, Path],
                      target_folder: Union[str, Path],
                      copy: bool = True,
                      verify: bool = True,
                      progress: bool = True) -> Dict:
        """
        上传/复制整个文件夹
        
        Args:
            source_folder: 源文件夹路径
            target_folder: 目标文件夹路径
            copy: True=复制文件, False=移动文件
            verify: 是否验证 MD5
            progress: 是否显示进度条
            
        Returns:
            Dict: 上传结果统计
        """
        source_folder = Path(source_folder)
        target_folder = Path(target_folder)
        
        # 扫描文件
        files = self.scan_folder(source_folder)
        
        if not files:
            return {"status": "empty", "message": "No supported files found"}
        
        # 创建目标文件夹
        target_folder.mkdir(parents=True, exist_ok=True)
        
        # 复制/移动文件
        results = {
            "total_files": len(files),
            "total_size_mb": sum(f.size_mb for f in files),
            "successful": [],
            "failed": [],
            "verified": []
        }
        
        iterator = tqdm(files, desc="Uploading") if progress else files
        
        for file_info in iterator:
            try:
                # 计算目标路径（保持目录结构）
                target_path = target_folder / file_info.relative_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 复制或移动
                if copy:
                    shutil.copy2(file_info.path, target_path)
                else:
                    shutil.move(str(file_info.path), str(target_path))
                
                # 验证
                if verify:
                    source_md5 = self.compute_md5(file_info.path)
                    target_md5 = self.compute_md5(target_path)
                    if source_md5 == target_md5:
                        results["verified"].append(str(file_info.relative_path))
                    else:
                        results["failed"].append((str(file_info.relative_path), "MD5 mismatch"))
                        continue
                
                results["successful"].append(str(file_info.relative_path))
                
            except Exception as e:
                results["failed"].append((str(file_info.relative_path), str(e)))
        
        return results
    
    def batch_load_audio(self,
                        folder_path: Union[str, Path],
                        read_func: Callable[[Path], np.ndarray],
                        pattern: Optional[str] = None,
                        max_workers: Optional[int] = None,
                        progress: bool = True) -> BatchLoadResult:
        """
        批量加载音频文件
        
        Args:
            folder_path: 文件夹路径
            read_func: 音频读取函数 (path -> numpy array)
            pattern: 文件匹配模式
            max_workers: 并行线程数
            progress: 是否显示进度
            
        Returns:
            BatchLoadResult: 批量加载结果
        """
        folder_path = Path(folder_path)
        files = self.scan_folder(folder_path, pattern=pattern)
        
        if not files:
            return BatchLoadResult(
                files=[], 
                successful=[], 
                failed=[], 
                audio_data={}
            )
        
        max_workers = max_workers or self.max_workers
        audio_data = {}
        successful = []
        failed = []
        
        # 并行加载
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(read_func, f.path): f 
                for f in files
            }
            
            # 处理结果
            iterator = tqdm(as_completed(future_to_file), 
                          total=len(files), 
                          desc="Loading audio") if progress else as_completed(future_to_file)
            
            for future in iterator:
                file_info = future_to_file[future]
                try:
                    audio = future.result()
                    audio_data[file_info.path] = audio
                    successful.append(file_info.path)
                    file_info.metadata["shape"] = audio.shape
                    file_info.metadata["dtype"] = str(audio.dtype)
                except Exception as e:
                    failed.append((file_info.path, str(e)))
        
        # 构建 metadata DataFrame
        if files:
            metadata_records = []
            for f in files:
                record = {
                    "path": str(f.path),
                    "relative_path": str(f.relative_path),
                    "filename": f.filename,
                    "size_mb": f.size_mb,
                }
                record.update(f.metadata)
                metadata_records.append(record)
            
            metadata_df = pd.DataFrame(metadata_records)
        else:
            metadata_df = None
        
        return BatchLoadResult(
            files=files,
            successful=successful,
            failed=failed,
            audio_data=audio_data,
            metadata_df=metadata_df
        )
    
    def create_manifest(self, 
                       folder_path: Union[str, Path],
                       output_path: Optional[Path] = None) -> Dict:
        """
        创建文件夹清单文件
        
        Args:
            folder_path: 文件夹路径
            output_path: 清单文件输出路径
            
        Returns:
            Dict: 清单内容
        """
        folder_path = Path(folder_path)
        files = self.scan_folder(folder_path)
        
        manifest = {
            "folder": str(folder_path),
            "total_files": len(files),
            "total_size_mb": sum(f.size_mb for f in files),
            "files": []
        }
        
        for f in files:
            file_entry = {
                "path": str(f.relative_path),
                "size_mb": round(f.size_mb, 2),
                "md5": self.compute_md5(f.path) if f.size_mb < 100 else None  # 大文件跳过 MD5
            }
            manifest["files"].append(file_entry)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2, ensure_ascii=False)
            print(f"Manifest saved: {output_path}")
        
        return manifest


class FolderDataset:
    """
    文件夹数据集 - 支持批量处理和惰性加载
    """
    
    def __init__(self, 
                 folder_path: Union[str, Path],
                 uploader: Optional[FolderUploader] = None):
        """
        Args:
            folder_path: 文件夹路径
            uploader: FolderUploader 实例
        """
        self.folder_path = Path(folder_path)
        self.uploader = uploader or FolderUploader()
        
        # 扫描文件
        self.files: List[FileInfo] = []
        self._index: Dict[str, FileInfo] = {}
        
    def scan(self, pattern: Optional[str] = None, recursive: bool = True):
        """扫描文件夹"""
        self.files = self.uploader.scan_folder(self.folder_path, pattern, recursive)
        self._index = {str(f.relative_path): f for f in self.files}
        print(f"Scanned {len(self.files)} files")
        return self
    
    def __len__(self) -> int:
        return len(self.files)
    
    def __getitem__(self, idx: Union[int, str]) -> FileInfo:
        """通过索引或相对路径获取文件"""
        if isinstance(idx, int):
            return self.files[idx]
        else:
            return self._index[idx]
    
    def __iter__(self) -> Iterator[FileInfo]:
        """迭代文件"""
        return iter(self.files)
    
    def get_by_extension(self, ext: str) -> List[FileInfo]:
        """按扩展名筛选文件"""
        ext = ext if ext.startswith('.') else f'.{ext}'
        return [f for f in self.files if f.path.suffix.lower() == ext.lower()]
    
    def get_relative_paths(self) -> List[str]:
        """获取所有相对路径"""
        return [str(f.relative_path) for f in self.files]
    
    def load_batch(self, 
                   read_func: Callable[[Path], np.ndarray],
                   max_workers: int = 4) -> BatchLoadResult:
        """批量加载所有文件"""
        return self.uploader.batch_load_audio(
            self.folder_path, 
            read_func,
            max_workers=max_workers
        )
    
    def to_dataframe(self) -> pd.DataFrame:
        """转换为 DataFrame"""
        records = []
        for f in self.files:
            records.append({
                "filename": f.filename,
                "relative_path": str(f.relative_path),
                "full_path": str(f.path),
                "size_mb": round(f.size_mb, 2)
            })
        return pd.DataFrame(records)


# ============================================
# 使用示例
# ============================================

def example_usage():
    """使用示例"""
    import soundfile as sf
    
    # 初始化上传器
    uploader = FolderUploader(max_workers=4)
    
    # 扫描文件夹
    folder = "/path/to/audio/folder"
    files = uploader.scan_folder(folder, pattern="*.ogg")
    print(f"Found {len(files)} audio files")
    
    # 显示文件信息
    for f in files[:5]:
        print(f"  {f.relative_path} ({f.size_mb:.2f} MB)")
    
    # 定义音频读取函数
    def read_audio(path: Path) -> np.ndarray:
        y, sr = sf.read(path, dtype='float32')
        if y.ndim == 2:
            y = y.mean(axis=1)
        return y
    
    # 批量加载
    result = uploader.batch_load_audio(folder, read_audio, max_workers=4)
    print(f"\nLoaded {len(result.successful)} files successfully")
    print(f"Failed: {len(result.failed)}")
    
    if result.metadata_df is not None:
        print("\nMetadata preview:")
        print(result.metadata_df.head())
    
    # 使用 FolderDataset
    dataset = FolderDataset(folder)
    dataset.scan()
    
    # 获取所有 .ogg 文件
    ogg_files = dataset.get_by_extension(".ogg")
    print(f"\nOGG files: {len(ogg_files)}")
    
    # 转换为 DataFrame
    df = dataset.to_dataframe()
    print(f"\nDataset DataFrame shape: {df.shape}")
    print(df.head())


if __name__ == "__main__":
    example_usage()
