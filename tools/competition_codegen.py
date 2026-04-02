"""
Competition 代码生成工具
用于生成支持 OOG 的数据加载代码模板
"""

from typing import Dict, List


class CompetitionCodeGenerator:
    """生成支持 OOG 的 Competition 数据加载代码"""
    
    @staticmethod
    def generate_oog_dataset_code(config: Dict) -> str:
        """
        生成支持 OOG 的数据集类代码
        
        Args:
            config: 配置字典，包含 sr, window_sec 等参数
        """
        sr = config.get('sr', 32000)
        window_sec = config.get('window_sec', 5)
        
        code = f'''"""
Competition 数据加载模块 - 支持 OOG (Out-of-Group) 分割
"""

import numpy as np
import pandas as pd
import soundfile as sf
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from sklearn.model_selection import GroupKFold
import re


class OOGAudioDataset:
    """
    支持 OOG 分割的音频数据集
    确保同一 group (site/filename) 不会同时出现在 train/val
    """
    
    FNAME_RE = re.compile(r"BC2026_(?:Train|Test)_(\\d+)_(S\\d+)_(\\d{{8}})_(\\d{{6}})\\.ogg")
    
    def __init__(self, base_path: str, sr: int = {sr}, window_sec: int = {window_sec}):
        self.base_path = Path(base_path)
        self.sr = sr
        self.window_sec = window_sec
        self.window_samples = sr * window_sec
        self.file_samples = 60 * sr
        self.n_windows = 12
        
        self.df: Optional[pd.DataFrame] = None
        self.labels: Optional[np.ndarray] = None
        self.oog_splits: Optional[Dict] = None
        
    def parse_filename(self, name: str) -> Dict:
        """解析文件名提取元数据"""
        m = self.FNAME_RE.match(name)
        if not m:
            return {{"site": None, "hour_utc": -1}}
        _, site, _, hms = m.groups()
        return {{
            "file_id": m.group(1),
            "site": site,
            "hour_utc": int(hms[:2])
        }}
    
    def load_labels(self, label_csv: str = "train_soundscapes_labels.csv"):
        """加载标签数据"""
        labels_df = pd.read_csv(self.base_path / label_csv)
        sample_sub = pd.read_csv(self.base_path / "sample_submission.csv")
        
        self.class_names = sample_sub.columns[1:].tolist()
        
        # 解析标签
        def parse_labels(x):
            if pd.isna(x):
                return []
            return [t.strip() for t in str(x).split(";") if t.strip()]
        
        # 去重并聚合
        df = (
            labels_df
            .groupby(["filename", "start", "end"])["primary_label"]
            .apply(lambda x: sorted(set(parse_labels(";".join(x)))))
            .reset_index(name="label_list")
        )
        
        # 添加时间信息
        df["end_sec"] = pd.to_timedelta(df["end"]).dt.total_seconds().astype(int)
        df["row_id"] = df["filename"].str.replace(".ogg", "") + "_" + df["end_sec"].astype(str)
        
        # 解析元数据
        meta = df["filename"].apply(self.parse_filename).apply(pd.Series)
        self.df = pd.concat([df, meta], axis=1)
        
        # 构建多热标签
        label_to_idx = {{c: i for i, c in enumerate(self.class_names)}}
        self.labels = np.zeros((len(self.df), len(self.class_names)), dtype=np.uint8)
        
        for i, lbls in enumerate(self.df["label_list"]):
            for lbl in lbls:
                if lbl in label_to_idx:
                    self.labels[i, label_to_idx[lbl]] = 1
        
        print(f"Loaded {{len(self.df)}} rows, {{len(self.class_names)}} classes")
        return self
    
    def create_oog_splits(self, n_splits: int = 5, group_col: str = "site"):
        """
        创建 OOG (Out-of-Group) 分割
        
        Args:
            n_splits: Fold 数量
            group_col: 分组列 ('site', 'filename')
        """
        if self.df is None:
            raise ValueError("Call load_labels() first")
        
        groups = self.df[group_col].to_numpy()
        gkf = GroupKFold(n_splits=n_splits)
        
        self.oog_splits = {{}}
        for fold_idx, (train_idx, val_idx) in enumerate(gkf.split(self.df, groups=groups)):
            self.oog_splits[fold_idx] = {{
                "train": train_idx,
                "val": val_idx,
                "train_groups": np.unique(groups[train_idx]),
                "val_groups": np.unique(groups[val_idx])
            }}
        
        print(f"Created {{n_splits}} OOG splits (group_col='{{group_col}}')")
        for fold_idx, split in self.oog_splits.items():
            print(f"  Fold {{fold_idx}}: train={{len(split['train'])}}, val={{len(split['val'])}}")
        
        return self
    
    def get_fold_indices(self, fold_idx: int) -> Tuple[np.ndarray, np.ndarray]:
        """获取指定 fold 的训练和验证索引"""
        if self.oog_splits is None:
            raise ValueError("Call create_oog_splits() first")
        
        split = self.oog_splits[fold_idx]
        return split["train"], split["val"]
    
    def read_audio(self, filename: str) -> np.ndarray:
        """读取音频文件"""
        path = self.base_path / "train_soundscapes" / filename
        y, sr = sf.read(path, dtype='float32')
        
        if y.ndim == 2:
            y = y.mean(axis=1)
        
        # 填充/截断
        if len(y) < self.file_samples:
            y = np.pad(y, (0, self.file_samples - len(y)))
        else:
            y = y[:self.file_samples]
        
        return y
    
    def read_audio_windows(self, filename: str) -> np.ndarray:
        """读取音频并分割为窗口"""
        y = self.read_audio(filename)
        return y.reshape(self.n_windows, self.window_samples)


# 使用示例
if __name__ == "__main__":
    # 初始化数据集
    dataset = OOGAudioDataset(
        base_path="/kaggle/input/competitions/birdclef-2026",
        sr={sr},
        window_sec={window_sec}
    )
    
    # 加载标签
    dataset.load_labels()
    
    # 创建 OOG 分割 (按 site 分组)
    dataset.create_oog_splits(n_splits=5, group_col="site")
    
    # 获取第 0 个 fold 的数据
    train_idx, val_idx = dataset.get_fold_indices(fold_idx=0)
    print(f"\\nFold 0: train={{len(train_idx)}}, val={{len(val_idx)}}")
    
    # 读取音频
    if len(dataset.df) > 0:
        filename = dataset.df.iloc[0]["filename"]
        audio = dataset.read_audio_windows(filename)
        print(f"Audio windows shape: {{audio.shape}}")
'''
        return code
    
    @staticmethod
    def generate_oog_dataloader_code() -> str:
        """生成 PyTorch DataLoader 代码（支持 OOG）"""
        code = '''"""
PyTorch DataLoader with OOG Support
"""

import torch
from torch.utils.data import Dataset, DataLoader
import numpy as np


class OOGAudioTorchDataset(Dataset):
    """PyTorch Dataset with OOG support"""
    
    def __init__(self, dataset, indices, transform=None):
        """
        Args:
            dataset: OOGAudioDataset instance
            indices: Indices from OOG split
            transform: Optional transform
        """
        self.dataset = dataset
        self.indices = indices
        self.transform = transform
        
    def __len__(self):
        return len(self.indices)
    
    def __getitem__(self, idx):
        real_idx = self.indices[idx]
        row = self.dataset.df.iloc[real_idx]
        
        # 读取音频
        filename = row["filename"]
        audio = self.dataset.read_audio_windows(filename)
        
        # 获取对应时间窗口的标签
        end_sec = row["end_sec"]
        window_idx = (end_sec // self.dataset.window_sec) - 1
        window_idx = max(0, min(window_idx, self.dataset.n_windows - 1))
        
        # 提取该窗口的音频
        window_audio = audio[window_idx]
        
        # 获取标签
        label = self.dataset.labels[real_idx].astype(np.float32)
        
        if self.transform:
            window_audio = self.transform(window_audio)
        
        return torch.tensor(window_audio, dtype=torch.float32), torch.tensor(label)


def create_oog_dataloaders(dataset, fold_idx, batch_size=32, num_workers=4):
    """
    创建支持 OOG 的 DataLoader
    
    Args:
        dataset: OOGAudioDataset
        fold_idx: Which fold to use
        batch_size: Batch size
        num_workers: Number of workers
    
    Returns:
        train_loader, val_loader
    """
    train_idx, val_idx = dataset.get_fold_indices(fold_idx)
    
    train_dataset = OOGAudioTorchDataset(dataset, train_idx)
    val_dataset = OOGAudioTorchDataset(dataset, val_idx)
    
    train_loader = DataLoader(
        train_dataset, 
        batch_size=batch_size, 
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True
    )
    
    return train_loader, val_loader
'''
        return code
    
    @staticmethod
    def generate_train_loop_with_oog() -> str:
        """生成支持 OOG 的训练循环代码"""
        code = '''"""
训练循环 - 支持 OOG Cross-Validation
"""

import torch
import torch.nn as nn
from tqdm import tqdm
import numpy as np
from sklearn.metrics import roc_auc_score


def train_with_oog_cv(model_class, dataset, n_folds=5, epochs=10, device='cuda'):
    """
    使用 OOG 分割进行交叉验证训练
    
    Args:
        model_class: 模型类
        dataset: OOGAudioDataset 实例
        n_folds: Fold 数量
        epochs: 每个 fold 的训练轮数
        device: 训练设备
    
    Returns:
        oof_predictions: Out-of-fold 预测
        scores: 每折的分数
    """
    oof_preds = np.zeros((len(dataset.df), dataset.labels.shape[1]))
    fold_scores = []
    
    for fold_idx in range(n_folds):
        print(f"\\n{'='*70}")
        print(f"Fold {fold_idx + 1}/{n_folds}")
        print(f"{'='*70}")
        
        # 创建 DataLoader
        train_loader, val_loader = create_oog_dataloaders(
            dataset, fold_idx, batch_size=32
        )
        
        # 初始化模型
        model = model_class().to(device)
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3)
        criterion = nn.BCEWithLogitsLoss()
        
        # 训练
        best_val_auc = 0
        for epoch in range(epochs):
            # Train
            model.train()
            train_loss = 0
            for x, y in tqdm(train_loader, desc=f"Epoch {epoch+1}/{epochs}"):
                x, y = x.to(device), y.to(device)
                optimizer.zero_grad()
                pred = model(x)
                loss = criterion(pred, y)
                loss.backward()
                optimizer.step()
                train_loss += loss.item()
            
            # Validation
            model.eval()
            val_preds = []
            val_labels = []
            with torch.no_grad():
                for x, y in val_loader:
                    x = x.to(device)
                    pred = torch.sigmoid(model(x))
                    val_preds.append(pred.cpu().numpy())
                    val_labels.append(y.numpy())
            
            val_preds = np.concatenate(val_preds)
            val_labels = np.concatenate(val_labels)
            
            # 计算 AUC
            val_auc = roc_auc_score(val_labels, val_preds, average='macro')
            print(f"Epoch {epoch+1}: train_loss={train_loss/len(train_loader):.4f}, val_auc={val_auc:.4f}")
            
            if val_auc > best_val_auc:
                best_val_auc = val_auc
                # 保存 OOF 预测
                val_indices = dataset.oog_splits[fold_idx]["val"]
                oof_preds[val_indices] = val_preds
        
        fold_scores.append(best_val_auc)
        print(f"Fold {fold_idx + 1} best AUC: {best_val_auc:.4f}")
    
    # 计算整体 OOF AUC
    overall_auc = roc_auc_score(dataset.labels, oof_preds, average='macro')
    print(f"\\n{'='*70}")
    print(f"Overall OOF AUC: {overall_auc:.4f}")
    print(f"Fold AUCs: {[f'{s:.4f}' for s in fold_scores]}")
    
    return oof_preds, fold_scores
'''
        return code


def generate_oog_template(output_path: str = None, config: dict = None) -> str:
    """
    生成完整的 OOG 支持代码模板
    
    Args:
        output_path: 输出文件路径
        config: 配置字典
    """
    config = config or {}
    
    generator = CompetitionCodeGenerator()
    
    # 生成各部分代码
    dataset_code = generator.generate_oog_dataset_code(config)
    dataloader_code = generator.generate_oog_dataloader_code()
    train_loop_code = generator.generate_train_loop_with_oog()
    
    # 合并
    full_code = f"""# Competition Data Loading with OOG Support
# Auto-generated by EvoAgentX

{dataset_code}

{dataloader_code}

{train_loop_code}
"""
    
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_code)
        print(f"Generated OOG code: {output_path}")
    
    return full_code


if __name__ == "__main__":
    # 测试代码生成
    config = {
        "sr": 32000,
        "window_sec": 5
    }
    
    code = generate_oog_template(config=config)
    print("\n" + "="*70)
    print("Generated Code Preview (first 1500 chars):")
    print("="*70)
    print(code[:1500])
    print("...")
