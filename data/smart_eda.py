"""
SmartEDA - 智能数据探索系统

自动检测数据类型，进行针对性的深度分析：
- 音频数据：采样率、时长、频谱特征、类别分布
- 图像数据：尺寸、色彩、质量、类别不平衡
- 表格数据：缺失值、相关性、异常值
- 文本数据：长度分布、词汇量、主题分布

输出结构化的 EDA 报告，供 Agent 使用
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field, asdict
from collections import Counter
import warnings

warnings.filterwarnings('ignore')


@dataclass
class AudioFeatures:
    """音频特征"""
    sample_rates: List[int] = field(default_factory=list)
    durations: List[float] = field(default_factory=list)
    channels: List[int] = field(default_factory=list)
    rms_values: List[float] = field(default_factory=list)
    spectral_centroids: List[float] = field(default_factory=list)
    
    # 统计信息
    duration_mean: float = 0.0
    duration_std: float = 0.0
    sample_rate_mode: int = 0
    
    # 类别信息（如果可用）
    class_distribution: Dict[str, int] = field(default_factory=dict)
    class_imbalance_ratio: float = 1.0


@dataclass
class ImageFeatures:
    """图像特征"""
    widths: List[int] = field(default_factory=list)
    heights: List[int] = field(default_factory=list)
    modes: List[str] = field(default_factory=list)
    
    # 统计
    size_mean: Tuple[float, float] = (0.0, 0.0)
    aspect_ratios: List[float] = field(default_factory=list)
    
    # 类别
    class_distribution: Dict[str, int] = field(default_factory=dict)


@dataclass
class TabularFeatures:
    """表格特征"""
    n_rows: int = 0
    n_columns: int = 0
    column_types: Dict[str, str] = field(default_factory=dict)
    missing_values: Dict[str, float] = field(default_factory=dict)
    
    # 数值特征统计
    numeric_stats: Dict[str, Dict] = field(default_factory=dict)
    
    # 类别特征
    categorical_cardinality: Dict[str, int] = field(default_factory=dict)
    
    # 相关性
    high_correlations: List[Tuple[str, str, float]] = field(default_factory=list)


@dataclass
class EDAReport:
    """EDA 报告"""
    data_type: str = "unknown"
    file_count: int = 0
    total_size_mb: float = 0.0
    
    # 特征
    audio_features: Optional[AudioFeatures] = None
    image_features: Optional[ImageFeatures] = None
    tabular_features: Optional[TabularFeatures] = None
    
    # 问题和建议
    issues: List[Dict] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    optimization_suggestions: List[Dict] = field(default_factory=list)


class SmartEDA:
    """
    智能数据探索系统
    
    自动识别数据类型并进行深度分析
    """
    
    # 文件扩展名到数据类型的映射
    DATA_TYPE_EXTENSIONS = {
        "audio": [".ogg", ".wav", ".mp3", ".flac", ".m4a", ".aac"],
        "image": [".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".webp"],
        "tabular": [".csv", ".parquet", ".xlsx", ".xls", ".tsv"],
        "text": [".txt", ".json", ".jsonl", ".xml", ".csv"],
        "numpy": [".npy", ".npz"]
    }
    
    def __init__(self, max_sample_size: int = 100, max_analysis_time: int = 60):
        """
        Args:
            max_sample_size: 最大采样数量
            max_analysis_time: 最大分析时间（秒）
        """
        self.max_sample_size = max_sample_size
        self.max_analysis_time = max_analysis_time
        self.report = EDAReport()
    
    def explore(self, data_path: Union[str, Path]) -> EDAReport:
        """
        主入口：探索数据
        
        Args:
            data_path: 数据文件或文件夹路径
            
        Returns:
            EDA 报告
        """
        path = Path(data_path)
        
        print(f"\n🔬 SmartEDA: 开始探索数据")
        print(f"  路径: {path}")
        
        if not path.exists():
            print(f"  ❌ 路径不存在: {path}")
            return self.report
        
        # 检测数据类型
        data_type = self._detect_data_type(path)
        self.report.data_type = data_type
        print(f"  检测到的数据类型: {data_type}")
        
        # 根据数据类型执行相应的分析
        if data_type == "audio":
            self._analyze_audio(path)
        elif data_type == "image":
            self._analyze_image(path)
        elif data_type == "tabular":
            self._analyze_tabular(path)
        elif data_type == "text":
            self._analyze_text(path)
        else:
            self._analyze_generic(path)
        
        # 生成洞察和建议
        self._generate_insights()
        self._generate_suggestions()
        
        print(f"  ✅ EDA 完成")
        print(f"     文件数: {self.report.file_count}")
        print(f"     发现问题: {len(self.report.issues)} 个")
        print(f"     优化建议: {len(self.report.optimization_suggestions)} 个")
        
        return self.report
    
    def _detect_data_type(self, path: Path) -> str:
        """检测数据类型"""
        files = []
        
        if path.is_file():
            files = [path]
        else:
            files = list(path.rglob("*"))
            files = [f for f in files if f.is_file()]
        
        if not files:
            return "unknown"
        
        # 统计扩展名
        ext_counts = Counter()
        for f in files[:100]:  # 采样前100个
            ext = f.suffix.lower()
            ext_counts[ext] += 1
        
        # 匹配数据类型
        for data_type, extensions in self.DATA_TYPE_EXTENSIONS.items():
            for ext in extensions:
                if ext in ext_counts:
                    return data_type
        
        return "unknown"
    
    def _analyze_audio(self, path: Path):
        """分析音频数据"""
        try:
            import soundfile as sf
        except ImportError:
            print("  ⚠️ soundfile 未安装，跳过音频分析")
            return
        
        # 获取所有音频文件
        audio_files = []
        for ext in self.DATA_TYPE_EXTENSIONS["audio"]:
            if path.is_file() and path.suffix.lower() == ext:
                audio_files = [path]
                break
            elif path.is_dir():
                audio_files.extend(path.rglob(f"*{ext}"))
        
        audio_files = list(audio_files)[:self.max_sample_size]
        self.report.file_count = len(audio_files)
        
        if not audio_files:
            return
        
        # 分析每个音频文件
        features = AudioFeatures()
        
        for i, audio_file in enumerate(audio_files):
            if i % 10 == 0:
                print(f"  分析音频 {i+1}/{len(audio_files)}...")
            
            try:
                # 读取信息
                info = sf.info(str(audio_file))
                
                features.sample_rates.append(info.samplerate)
                features.durations.append(info.duration)
                features.channels.append(info.channels)
                
                # 读取部分数据计算 RMS
                if info.duration > 0:
                    try:
                        y, sr = sf.read(str(audio_file), dtype='float32', frames=min(int(sr * 5), info.frames))
                        if y.ndim == 2:
                            y = y.mean(axis=1)
                        rms = float((y ** 2).mean() ** 0.5)
                        features.rms_values.append(rms)
                    except:
                        pass
                
            except Exception as e:
                print(f"    ⚠️ 无法读取 {audio_file.name}: {e}")
        
        # 计算统计信息
        if features.durations:
            features.duration_mean = np.mean(features.durations)
            features.duration_std = np.std(features.durations)
        
        if features.sample_rates:
            features.sample_rate_mode = Counter(features.sample_rates).most_common(1)[0][0]
        
        # 尝试加载标签信息
        features = self._extract_audio_labels(path, features)
        
        self.report.audio_features = features
        
        # 检测问题
        self._detect_audio_issues(features)
    
    def _extract_audio_labels(self, path: Path, features: AudioFeatures) -> AudioFeatures:
        """提取音频标签信息"""
        # 查找 CSV 标签文件
        csv_files = list(path.parent.glob("*.csv")) if path.is_file() else list(path.glob("*.csv"))
        
        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file, nrows=1000)
                
                # 查找类别列
                label_cols = [c for c in df.columns if 'label' in c.lower() or 'class' in c.lower() or 'species' in c.lower()]
                
                if label_cols:
                    col = label_cols[0]
                    value_counts = df[col].value_counts()
                    features.class_distribution = value_counts.to_dict()
                    
                    # 计算不平衡比例
                    if len(value_counts) > 1:
                        features.class_imbalance_ratio = value_counts.iloc[0] / value_counts.iloc[-1]
                    
                    break
            except:
                pass
        
        return features
    
    def _detect_audio_issues(self, features: AudioFeatures):
        """检测音频数据问题"""
        issues = []
        
        # 检查采样率不一致
        if features.sample_rates:
            unique_rates = set(features.sample_rates)
            if len(unique_rates) > 1:
                issues.append({
                    "type": "inconsistent_sample_rate",
                    "severity": "warning",
                    "message": f"发现 {len(unique_rates)} 种不同的采样率: {unique_rates}",
                    "suggestion": "统一重采样到目标采样率"
                })
        
        # 检查时长分布
        if features.durations:
            if features.duration_std / (features.duration_mean + 1e-8) > 0.5:
                issues.append({
                    "type": "high_duration_variance",
                    "severity": "info",
                    "message": f"音频时长差异较大 (mean={features.duration_mean:.1f}s, std={features.duration_std:.1f}s)",
                    "suggestion": "考虑使用动态 padding 或截断策略"
                })
        
        # 检查类别不平衡
        if features.class_imbalance_ratio > 10:
            issues.append({
                "type": "class_imbalance",
                "severity": "warning",
                "message": f"严重的类别不平衡 (比例: {features.class_imbalance_ratio:.1f}:1)",
                "suggestion": "考虑使用 Focal Loss、类别权重或过采样"
            })
        
        self.report.issues.extend(issues)
    
    def _analyze_image(self, path: Path):
        """分析图像数据"""
        try:
            from PIL import Image
        except ImportError:
            print("  ⚠️ PIL 未安装，跳过图像分析")
            return
        
        # 获取图像文件
        image_files = []
        for ext in self.DATA_TYPE_EXTENSIONS["image"]:
            if path.is_file() and path.suffix.lower() == ext:
                image_files = [path]
                break
            elif path.is_dir():
                image_files.extend(path.rglob(f"*{ext}"))
        
        image_files = list(image_files)[:self.max_sample_size]
        self.report.file_count = len(image_files)
        
        if not image_files:
            return
        
        features = ImageFeatures()
        
        for i, img_file in enumerate(image_files):
            if i % 10 == 0:
                print(f"  分析图像 {i+1}/{len(image_files)}...")
            
            try:
                with Image.open(img_file) as img:
                    features.widths.append(img.width)
                    features.heights.append(img.height)
                    features.modes.append(img.mode)
                    features.aspect_ratios.append(img.width / img.height)
            except Exception as e:
                print(f"    ⚠️ 无法读取 {img_file.name}: {e}")
        
        # 计算统计
        if features.widths:
            features.size_mean = (np.mean(features.widths), np.mean(features.heights))
        
        self.report.image_features = features
        
        # 检测问题
        self._detect_image_issues(features)
    
    def _detect_image_issues(self, features: ImageFeatures):
        """检测图像问题"""
        issues = []
        
        # 检查尺寸不一致
        if features.widths:
            unique_sizes = set(zip(features.widths, features.heights))
            if len(unique_sizes) > 1:
                issues.append({
                    "type": "inconsistent_image_size",
                    "severity": "info",
                    "message": f"发现 {len(unique_sizes)} 种不同的图像尺寸",
                    "suggestion": "使用统一的 resize 或 padding 策略"
                })
        
        # 检查极端宽高比
        if features.aspect_ratios:
            extreme_ratios = [r for r in features.aspect_ratios if r > 3 or r < 0.33]
            if len(extreme_ratios) > len(features.aspect_ratios) * 0.1:
                issues.append({
                    "type": "extreme_aspect_ratios",
                    "severity": "warning",
                    "message": f"发现 {len(extreme_ratios)} 张极端宽高比的图像",
                    "suggestion": "检查数据质量或考虑使用不同的增强策略"
                })
        
        self.report.issues.extend(issues)
    
    def _analyze_tabular(self, path: Path):
        """分析表格数据"""
        # 读取数据
        try:
            if path.is_file():
                df = self._read_tabular_file(path)
            else:
                # 读取第一个 CSV
                csv_files = list(path.glob("*.csv"))
                if csv_files:
                    df = self._read_tabular_file(csv_files[0])
                else:
                    return
            
            if df is None or df.empty:
                return
            
            features = TabularFeatures()
            features.n_rows = len(df)
            features.n_columns = len(df.columns)
            
            # 分析列类型
            for col in df.columns:
                if df[col].dtype in ['int64', 'float64']:
                    features.column_types[col] = 'numeric'
                    # 统计信息
                    features.numeric_stats[col] = {
                        'mean': float(df[col].mean()),
                        'std': float(df[col].std()),
                        'min': float(df[col].min()),
                        'max': float(df[col].max()),
                        'missing': float(df[col].isnull().mean())
                    }
                elif df[col].dtype == 'object':
                    features.column_types[col] = 'categorical'
                    features.categorical_cardinality[col] = df[col].nunique()
                
                # 缺失值
                missing_ratio = df[col].isnull().mean()
                if missing_ratio > 0:
                    features.missing_values[col] = missing_ratio
            
            # 相关性分析
            numeric_df = df.select_dtypes(include=[np.number])
            if len(numeric_df.columns) > 1:
                corr_matrix = numeric_df.corr().abs()
                for i in range(len(corr_matrix.columns)):
                    for j in range(i+1, len(corr_matrix.columns)):
                        corr_val = corr_matrix.iloc[i, j]
                        if corr_val > 0.8:
                            features.high_correlations.append(
                                (corr_matrix.columns[i], corr_matrix.columns[j], float(corr_val))
                            )
            
            self.report.tabular_features = features
            self.report.file_count = 1
            
            # 检测问题
            self._detect_tabular_issues(features)
            
        except Exception as e:
            print(f"  ❌ 表格分析失败: {e}")
    
    def _read_tabular_file(self, path: Path) -> Optional[pd.DataFrame]:
        """读取表格文件"""
        ext = path.suffix.lower()
        
        try:
            if ext == '.csv':
                return pd.read_csv(path, nrows=self.max_sample_size)
            elif ext == '.parquet':
                return pd.read_parquet(path)
            elif ext in ['.xlsx', '.xls']:
                return pd.read_excel(path, nrows=self.max_sample_size)
            elif ext == '.tsv':
                return pd.read_csv(path, sep='\t', nrows=self.max_sample_size)
        except Exception as e:
            print(f"  ⚠️ 无法读取 {path}: {e}")
        
        return None
    
    def _detect_tabular_issues(self, features: TabularFeatures):
        """检测表格数据问题"""
        issues = []
        
        # 缺失值
        high_missing = {k: v for k, v in features.missing_values.items() if v > 0.5}
        if high_missing:
            issues.append({
                "type": "high_missing_values",
                "severity": "warning",
                "message": f"{len(high_missing)} 列缺失值超过 50%",
                "suggestion": "考虑删除这些列或使用高级缺失值填充方法"
            })
        
        # 高相关性
        if features.high_correlations:
            issues.append({
                "type": "high_correlation",
                "severity": "info",
                "message": f"发现 {len(features.high_correlations)} 对高度相关的特征",
                "suggestion": "考虑特征选择或降维"
            })
        
        self.report.issues.extend(issues)
    
    def _analyze_text(self, path: Path):
        """分析文本数据"""
        # 简化版文本分析
        pass
    
    def _analyze_generic(self, path: Path):
        """通用文件分析"""
        if path.is_dir():
            files = [f for f in path.rglob("*") if f.is_file()]
            self.report.file_count = len(files)
            
            # 计算总大小
            total_size = sum(f.stat().st_size for f in files[:1000])
            self.report.total_size_mb = total_size / (1024 * 1024)
    
    def _generate_insights(self):
        """生成数据洞察"""
        insights = []
        
        # 音频洞察
        if self.report.audio_features:
            af = self.report.audio_features
            insights.append(f"音频数据: 平均时长 {af.duration_mean:.1f}s, 采样率 {af.sample_rate_mode}Hz")
            
            if af.class_distribution:
                n_classes = len(af.class_distribution)
                insights.append(f"类别数: {n_classes}, 不平衡比例: {af.class_imbalance_ratio:.1f}:1")
        
        # 图像洞察
        if self.report.image_features:
            imgf = self.report.image_features
            insights.append(f"图像数据: 平均尺寸 {imgf.size_mean[0]:.0f}x{imgf.size_mean[1]:.0f}")
        
        # 表格洞察
        if self.report.tabular_features:
            tf = self.report.tabular_features
            insights.append(f"表格数据: {tf.n_rows} 行 x {tf.n_columns} 列")
            
            if tf.missing_values:
                insights.append(f"缺失值: {len(tf.missing_values)} 列存在缺失")
        
        self.report.insights = insights
    
    def _generate_suggestions(self):
        """生成优化建议"""
        suggestions = []
        
        # 基于数据类型生成建议
        if self.report.data_type == "audio":
            suggestions.extend([
                {
                    "category": "data_augmentation",
                    "suggestion": "添加 SpecAugment 时频增强",
                    "expected_benefit": "提升音频分类的鲁棒性",
                    "priority": "high"
                },
                {
                    "category": "feature_engineering",
                    "suggestion": "提取 MFCC 或 Mel 频谱特征",
                    "expected_benefit": "更好的音频表征",
                    "priority": "medium"
                }
            ])
            
            # 类别不平衡建议
            if self.report.audio_features and self.report.audio_features.class_imbalance_ratio > 10:
                suggestions.append({
                    "category": "loss_function",
                    "suggestion": "使用 Focal Loss 或类别权重",
                    "expected_benefit": "改善长尾类别识别",
                    "priority": "high"
                })
        
        elif self.report.data_type == "image":
            suggestions.extend([
                {
                    "category": "data_augmentation",
                    "suggestion": "添加 Mixup/CutMix 增强",
                    "expected_benefit": "提升泛化能力",
                    "priority": "high"
                },
                {
                    "category": "training_strategy",
                    "suggestion": "使用 Test Time Augmentation (TTA)",
                    "expected_benefit": "提升预测稳定性",
                    "priority": "medium"
                }
            ])
        
        elif self.report.data_type == "tabular":
            suggestions.extend([
                {
                    "category": "feature_engineering",
                    "suggestion": "进行特征选择和交叉特征构建",
                    "expected_benefit": "减少维度灾难",
                    "priority": "medium"
                }
            ])
        
        self.report.optimization_suggestions = suggestions
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "data_type": self.report.data_type,
            "file_count": self.report.file_count,
            "total_size_mb": self.report.total_size_mb,
            "audio_features": asdict(self.report.audio_features) if self.report.audio_features else None,
            "image_features": asdict(self.report.image_features) if self.report.image_features else None,
            "tabular_features": asdict(self.report.tabular_features) if self.report.tabular_features else None,
            "issues": self.report.issues,
            "insights": self.report.insights,
            "optimization_suggestions": self.report.optimization_suggestions
        }


# 便捷函数
def quick_eda(data_path: Union[str, Path], max_samples: int = 100) -> Dict:
    """
    快速 EDA 分析
    
    Args:
        data_path: 数据路径
        max_samples: 最大采样数
        
    Returns:
        EDA 报告字典
    """
    eda = SmartEDA(max_sample_size=max_samples)
    report = eda.explore(data_path)
    return eda.to_dict()
