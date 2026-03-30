"""
Competition 数据加载模块 - 支持 OOG (Out-of-Group) 分割
用于 BirdCLEF 等竞赛的音频数据加载
"""

import numpy as np
import pandas as pd
import soundfile as sf
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass
from sklearn.model_selection import GroupKFold
import re


@dataclass
class AudioConfig:
    """音频配置"""
    sr: int = 32000  # 采样率
    window_sec: int = 5  # 窗口大小(秒)
    file_duration: int = 60  # 文件长度(秒)
    
    @property
    def window_samples(self) -> int:
        return self.sr * self.window_sec
    
    @property
    def file_samples(self) -> int:
        return self.sr * self.file_duration
    
    @property
    def n_windows(self) -> int:
        return self.file_duration // self.window_sec


class OOGSplitter:
    """
    Out-of-Group 分割器
    确保同一组的数据(如同一site或filename)不会同时出现在训练集和验证集
    """
    
    def __init__(self, n_splits: int = 5, group_col: str = "site", seed: int = 42):
        self.n_splits = n_splits
        self.group_col = group_col
        self.seed = seed
        self.splits = {}
        
    def create_splits(self, df: pd.DataFrame) -> Dict[int, Dict]:
        """
        创建 OOG 分割
        
        Args:
            df: 包含元数据的DataFrame
            
        Returns:
            splits: {fold_idx: {"train": indices, "val": indices, "train_groups": groups, "val_groups": groups}}
        """
        groups = df[self.group_col].to_numpy()
        
        # 使用 GroupKFold 进行分割
        gkf = GroupKFold(n_splits=self.n_splits)
        
        self.splits = {}
        for fold_idx, (train_idx, val_idx) in enumerate(gkf.split(df, groups=groups)):
            train_groups = np.unique(groups[train_idx])
            val_groups = np.unique(groups[val_idx])
            
            self.splits[fold_idx] = {
                "train": train_idx,
                "val": val_idx,
                "train_groups": train_groups,
                "val_groups": val_groups
            }
            
        return self.splits
    
    def get_fold(self, fold_idx: int) -> Tuple[np.ndarray, np.ndarray]:
        """获取指定 fold 的训练和验证索引"""
        if fold_idx not in self.splits:
            raise ValueError(f"Fold {fold_idx} not found. Call create_splits first.")
        
        split = self.splits[fold_idx]
        return split["train"], split["val"]
    
    def print_summary(self):
        """打印分割摘要"""
        print(f"=== OOG Splits Summary (group_col='{self.group_col}') ===")
        for fold_idx, split in self.splits.items():
            print(f"Fold {fold_idx}: "
                  f"train_groups={len(split['train_groups'])}, "
                  f"val_groups={len(split['val_groups'])}, "
                  f"train_rows={len(split['train'])}, "
                  f"val_rows={len(split['val'])}")


class CompetitionAudioDataset:
    """
    Competition 音频数据集
    支持 OOG 读取和分割
    """
    
    # 文件名解析正则
    FNAME_RE = re.compile(r"BC2026_(?:Train|Test)_(\d+)_(S\d+)_(\d{8})_(\d{6})\.ogg")
    
    def __init__(self, base_path: Union[str, Path], cfg: Optional[AudioConfig] = None):
        self.base_path = Path(base_path)
        self.cfg = cfg or AudioConfig()
        
        # 数据存储
        self.sc_clean: Optional[pd.DataFrame] = None
        self.full_truth: Optional[pd.DataFrame] = None
        self.Y_SC: Optional[np.ndarray] = None
        self.Y_FULL_TRUTH: Optional[np.ndarray] = None
        self.primary_labels: List[str] = []
        self.n_classes: int = 0
        
        # OOG Splitter
        self.oog_splitter: Optional[OOGSplitter] = None
        
    def parse_soundscape_filename(self, name: str) -> Dict:
        """解析 soundscape 文件名提取元数据"""
        m = self.FNAME_RE.match(name)
        if not m:
            return {
                "file_id": None,
                "site": None,
                "date": pd.NaT,
                "time_utc": None,
                "hour_utc": -1,
                "month": -1,
            }
        file_id, site, ymd, hms = m.groups()
        dt = pd.to_datetime(ymd, format="%Y%m%d", errors="coerce")
        return {
            "file_id": file_id,
            "site": site,
            "date": dt,
            "time_utc": hms,
            "hour_utc": int(hms[:2]),
            "month": int(dt.month) if pd.notna(dt) else -1,
        }
    
    @staticmethod
    def parse_labels(x) -> List[str]:
        """解析标签字符串"""
        if pd.isna(x):
            return []
        return [t.strip() for t in str(x).split(";") if t.strip()]
    
    @staticmethod
    def union_labels(series: pd.Series) -> List[str]:
        """合并标签列表"""
        return sorted(set(lbl for x in series for lbl in CompetitionAudioDataset.parse_labels(x)))
    
    def load_labels(self) -> "CompetitionAudioDataset":
        """加载标签数据"""
        taxonomy = pd.read_csv(self.base_path / "taxonomy.csv")
        sample_sub = pd.read_csv(self.base_path / "sample_submission.csv")
        soundscape_labels = pd.read_csv(self.base_path / "train_soundscapes_labels.csv")
        
        self.primary_labels = sample_sub.columns[1:].tolist()
        self.n_classes = len(self.primary_labels)
        
        taxonomy["primary_label"] = taxonomy["primary_label"].astype(str)
        soundscape_labels["primary_label"] = soundscape_labels["primary_label"].astype(str)
        
        # 去重并聚合标签
        self.sc_clean = (
            soundscape_labels
            .groupby(["filename", "start", "end"])["primary_label"]
            .apply(self.union_labels)
            .reset_index(name="label_list")
        )
        
        # 添加时间信息
        self.sc_clean["start_sec"] = pd.to_timedelta(self.sc_clean["start"]).dt.total_seconds().astype(int)
        self.sc_clean["end_sec"] = pd.to_timedelta(self.sc_clean["end"]).dt.total_seconds().astype(int)
        self.sc_clean["row_id"] = (
            self.sc_clean["filename"].str.replace(".ogg", "", regex=False) + 
            "_" + self.sc_clean["end_sec"].astype(str)
        )
        
        # 解析文件名元数据
        meta = self.sc_clean["filename"].apply(self.parse_soundscape_filename).apply(pd.Series)
        self.sc_clean = pd.concat([self.sc_clean, meta], axis=1)
        
        # 标记完全标记的文件
        windows_per_file = self.sc_clean.groupby("filename").size()
        full_files = sorted(windows_per_file[windows_per_file == self.cfg.n_windows].index.tolist())
        self.sc_clean["file_fully_labeled"] = self.sc_clean["filename"].isin(full_files)
        
        # 构建多热标签矩阵
        label_to_idx = {c: i for i, c in enumerate(self.primary_labels)}
        self.Y_SC = np.zeros((len(self.sc_clean), self.n_classes), dtype=np.uint8)
        
        for i, labels in enumerate(self.sc_clean["label_list"]):
            idxs = [label_to_idx[lbl] for lbl in labels if lbl in label_to_idx]
            if idxs:
                self.Y_SC[i, idxs] = 1
        
        # 提取完全标记的数据
        self.full_truth = (
            self.sc_clean[self.sc_clean["file_fully_labeled"]]
            .sort_values(["filename", "end_sec"])
            .reset_index(drop=False)
        )
        
        if len(self.full_truth) > 0:
            self.Y_FULL_TRUTH = self.Y_SC[self.full_truth["index"].to_numpy()]
        else:
            self.Y_FULL_TRUTH = np.array([])
        
        print(f"Loaded {len(self.sc_clean)} soundscape rows")
        print(f"Full files: {len(full_files)}")
        print(f"Trusted windows: {len(self.full_truth)}")
        print(f"Classes: {self.n_classes}")
        
        return self
    
    def setup_oog_splits(self, n_splits: int = 5, group_col: str = "site") -> "CompetitionAudioDataset":
        """
        设置 OOG 分割
        
        Args:
            n_splits: CV fold 数量
            group_col: 分组列名 ('site', 'filename', 'file_id')
        """
        if self.sc_clean is None:
            raise ValueError("Call load_labels() first")
        
        self.oog_splitter = OOGSplitter(n_splits=n_splits, group_col=group_col)
        
        # 对所有数据创建分割
        self.oog_splitter.create_splits(self.sc_clean)
        self.oog_splitter.print_summary()
        
        return self
    
    def get_fold_data(self, fold_idx: int, use_full_truth: bool = True) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        获取指定 fold 的数据
        
        Args:
            fold_idx: Fold 索引
            use_full_truth: 是否只使用完全标记的数据
            
        Returns:
            (meta_df, y_true)
        """
        if self.oog_splitter is None:
            raise ValueError("Call setup_oog_splits() first")
        
        train_idx, val_idx = self.oog_splitter.get_fold(fold_idx)
        
        if use_full_truth:
            # 返回完全标记的数据
            return self.full_truth.iloc[val_idx], self.Y_FULL_TRUTH[val_idx]
        else:
            # 返回所有数据
            return self.sc_clean.iloc[val_idx], self.Y_SC[val_idx]
    
    def read_audio_full(self, path: Path) -> np.ndarray:
        """
        读取完整音频文件
        
        Args:
            path: 音频文件路径
            
        Returns:
            audio: 音频数组 (file_samples,)
        """
        y, sr = sf.read(path, dtype='float32', always_2d=False)
        
        # 转换为单声道
        if y.ndim == 2:
            y = y.mean(axis=1)
        
        # 重采样到目标采样率
        if sr != self.cfg.sr:
            from scipy import signal
            y = signal.resample(y, int(len(y) * self.cfg.sr / sr))
        
        # 填充或截断到标准长度
        expected_len = self.cfg.file_samples
        if len(y) < expected_len:
            y = np.pad(y, (0, expected_len - len(y)))
        elif len(y) > expected_len:
            y = y[:expected_len]
        
        return y
    
    def read_audio_windows(self, path: Path) -> np.ndarray:
        """
        读取音频并分割为窗口
        
        Args:
            path: 音频文件路径
            
        Returns:
            windows: (n_windows, window_samples)
        """
        y = self.read_audio_full(path)
        return y.reshape(self.cfg.n_windows, self.cfg.window_samples)
    
    def get_train_val_paths(self, fold_idx: int) -> Tuple[List[Path], List[Path]]:
        """
        获取训练和验证文件路径
        
        Args:
            fold_idx: Fold 索引
            
        Returns:
            (train_paths, val_paths)
        """
        if self.oog_splitter is None:
            raise ValueError("Call setup_oog_splits() first")
        
        train_idx, val_idx = self.oog_splitter.get_fold(fold_idx)
        
        train_files = self.sc_clean.iloc[train_idx]["filename"].unique()
        val_files = self.sc_clean.iloc[val_idx]["filename"].unique()
        
        train_paths = [self.base_path / "train_soundscapes" / f for f in train_files]
        val_paths = [self.base_path / "train_soundscapes" / f for f in val_files]
        
        return train_paths, val_paths


# ============================================
# 使用示例
# ============================================

def example_usage():
    """使用示例"""
    # 初始化数据集
    cfg = AudioConfig(sr=32000, window_sec=5)
    dataset = CompetitionAudioDataset(
        base_path="/kaggle/input/competitions/birdclef-2026",
        cfg=cfg
    )
    
    # 加载标签
    dataset.load_labels()
    
    # 设置 OOG 分割 (按 site 分组)
    dataset.setup_oog_splits(n_splits=5, group_col="site")
    
    # 获取第 0 个 fold 的验证数据
    val_meta, val_y = dataset.get_fold_data(fold_idx=0, use_full_truth=True)
    print(f"\nFold 0 val samples: {len(val_meta)}")
    
    # 获取训练和验证文件路径
    train_paths, val_paths = dataset.get_train_val_paths(fold_idx=0)
    print(f"Train files: {len(train_paths)}, Val files: {len(val_paths)}")
    
    # 读取音频
    if val_paths:
        audio = dataset.read_audio_full(val_paths[0])
        print(f"Audio shape: {audio.shape}")
        
        windows = dataset.read_audio_windows(val_paths[0])
        print(f"Windows shape: {windows.shape}")


if __name__ == "__main__":
    example_usage()
