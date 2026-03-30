"""
命令行文件夹上传工具
支持批量上传、扫描、批量加载
"""

import argparse
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.folder_uploader import FolderUploader, FolderDataset
from data.competition_dataset import CompetitionAudioDataset, AudioConfig


def cmd_scan(args):
    """扫描文件夹命令"""
    print(f"🔍 Scanning folder: {args.folder}")
    
    uploader = FolderUploader()
    files = uploader.scan_folder(
        args.folder, 
        pattern=args.pattern,
        recursive=not args.no_recursive
    )
    
    print(f"\n📁 Found {len(files)} files")
    print(f"💾 Total size: {sum(f.size_mb for f in files):.2f} MB")
    
    if args.verbose:
        print("\n📋 File list:")
        for f in files:
            print(f"  {f.relative_path} ({f.size_mb:.2f} MB)")
    
    # 按扩展名统计
    if files:
        from collections import Counter
        exts = Counter(f.path.suffix.lower() for f in files)
        print("\n📊 By extension:")
        for ext, count in exts.most_common():
            print(f"  {ext}: {count} files")


def cmd_upload(args):
    """上传/复制文件夹命令"""
    print(f"📤 Uploading from {args.source} to {args.target}")
    
    uploader = FolderUploader(max_workers=args.workers)
    
    result = uploader.upload_folder(
        source_folder=args.source,
        target_folder=args.target,
        copy=not args.move,
        verify=args.verify,
        progress=True
    )
    
    print(f"\n✅ Successful: {len(result['successful'])}")
    print(f"❌ Failed: {len(result['failed'])}")
    
    if result['failed'] and args.verbose:
        print("\nFailed files:")
        for path, error in result['failed']:
            print(f"  {path}: {error}")
    
    if args.verify:
        print(f"🔐 Verified: {len(result['verified'])}")


def cmd_manifest(args):
    """生成清单命令"""
    print(f"📝 Creating manifest for: {args.folder}")
    
    uploader = FolderUploader()
    manifest = uploader.create_manifest(args.folder, args.output)
    
    print(f"\n📊 Summary:")
    print(f"  Total files: {manifest['total_files']}")
    print(f"  Total size: {manifest['total_size_mb']:.2f} MB")
    
    if args.output:
        print(f"\n💾 Manifest saved: {args.output}")


def cmd_load(args):
    """批量加载音频命令"""
    print(f"📥 Loading audio from: {args.folder}")
    
    import soundfile as sf
    
    def read_audio(path: Path):
        y, sr = sf.read(path, dtype='float32')
        if y.ndim == 2:
            y = y.mean(axis=1)
        return y
    
    uploader = FolderUploader(max_workers=args.workers)
    result = uploader.batch_load_audio(
        folder_path=args.folder,
        read_func=read_audio,
        pattern=args.pattern,
        max_workers=args.workers,
        progress=True
    )
    
    print(f"\n✅ Loaded: {len(result.successful)}")
    print(f"❌ Failed: {len(result.failed)}")
    
    if result.metadata_df is not None:
        print("\n📊 Metadata:")
        print(result.metadata_df.describe())
        
        if args.output:
            result.metadata_df.to_csv(args.output, index=False)
            print(f"\n💾 Metadata saved: {args.output}")


def cmd_oog(args):
    """创建 OOG 数据集命令"""
    print(f"🔀 Creating OOG dataset from: {args.base_path}")
    
    cfg = AudioConfig(sr=args.sr, window_sec=args.window_sec)
    dataset = CompetitionAudioDataset(args.base_path, cfg=cfg)
    
    # 加载标签
    dataset.load_labels()
    
    # 设置 OOG 分割
    dataset.setup_oog_splits(n_splits=args.n_splits, group_col=args.group_col)
    
    # 显示分割详情
    print(f"\n📊 OOG Splits ({args.n_splits} folds):")
    for fold_idx, split in dataset.oog_splitter.splits.items():
        print(f"  Fold {fold_idx}:")
        print(f"    Train: {len(split['train'])} samples, {len(split['train_groups'])} groups")
        print(f"    Val: {len(split['val'])} samples, {len(split['val_groups'])} groups")
    
    # 导出分割信息
    if args.output:
        import json
        splits_info = {}
        for fold_idx, split in dataset.oog_splitter.splits.items():
            splits_info[fold_idx] = {
                "train_indices": split["train"].tolist(),
                "val_indices": split["val"].tolist(),
                "train_groups": split["train_groups"].tolist(),
                "val_groups": split["val_groups"].tolist()
            }
        
        with open(args.output, 'w') as f:
            json.dump(splits_info, f, indent=2)
        print(f"\n💾 Splits saved: {args.output}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Competition Data Folder Upload Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 扫描文件夹
  python upload_cli.py scan ./data/audio --pattern "*.ogg"
  
  # 上传文件夹
  python upload_cli.py upload ./source ./target --workers 8
  
  # 生成清单
  python upload_cli.py manifest ./data/audio -o manifest.json
  
  # 批量加载音频
  python upload_cli.py load ./data/audio --pattern "*.ogg" -o metadata.csv
  
  # 创建 OOG 数据集
  python upload_cli.py oog ./data/birdclef --n-splits 5 --group-col site
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # scan 命令
    scan_parser = subparsers.add_parser("scan", help="扫描文件夹")
    scan_parser.add_argument("folder", help="文件夹路径")
    scan_parser.add_argument("--pattern", "-p", help="文件匹配模式 (如 *.ogg)")
    scan_parser.add_argument("--no-recursive", action="store_true", help="不递归扫描")
    scan_parser.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")
    scan_parser.set_defaults(func=cmd_scan)
    
    # upload 命令
    upload_parser = subparsers.add_parser("upload", help="上传/复制文件夹")
    upload_parser.add_argument("source", help="源文件夹")
    upload_parser.add_argument("target", help="目标文件夹")
    upload_parser.add_argument("--move", action="store_true", help="移动而不是复制")
    upload_parser.add_argument("--verify", action="store_true", help="验证 MD5")
    upload_parser.add_argument("--workers", "-w", type=int, default=4, help="并行线程数")
    upload_parser.add_argument("--verbose", "-v", action="store_true", help="显示详细信息")
    upload_parser.set_defaults(func=cmd_upload)
    
    # manifest 命令
    manifest_parser = subparsers.add_parser("manifest", help="生成清单文件")
    manifest_parser.add_argument("folder", help="文件夹路径")
    manifest_parser.add_argument("--output", "-o", help="输出文件路径")
    manifest_parser.set_defaults(func=cmd_manifest)
    
    # load 命令
    load_parser = subparsers.add_parser("load", help="批量加载音频")
    load_parser.add_argument("folder", help="文件夹路径")
    load_parser.add_argument("--pattern", "-p", default="*.ogg", help="文件匹配模式")
    load_parser.add_argument("--workers", "-w", type=int, default=4, help="并行线程数")
    load_parser.add_argument("--output", "-o", help="输出 CSV 文件")
    load_parser.set_defaults(func=cmd_load)
    
    # oog 命令
    oog_parser = subparsers.add_parser("oog", help="创建 OOG 数据集")
    oog_parser.add_argument("base_path", help="基础数据路径")
    oog_parser.add_argument("--n-splits", type=int, default=5, help="Fold 数量")
    oog_parser.add_argument("--group-col", default="site", help="分组列名")
    oog_parser.add_argument("--sr", type=int, default=32000, help="采样率")
    oog_parser.add_argument("--window-sec", type=int, default=5, help="窗口大小(秒)")
    oog_parser.add_argument("--output", "-o", help="输出 JSON 文件")
    oog_parser.set_defaults(func=cmd_oog)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
