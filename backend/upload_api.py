"""
文件夹上传 API - FastAPI
支持文件夹上传、批量处理、进度跟踪
"""

import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict
from dataclasses import asdict
from datetime import datetime
import tempfile
import zipfile

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, BackgroundTasks, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import sys
sys.path.append(str(Path(__file__).parent.parent))

from data.folder_uploader import FolderUploader, FolderDataset, FileInfo
from data.competition_dataset import CompetitionAudioDataset, AudioConfig


# ============================================
# Pydantic 模型
# ============================================

class UploadRequest(BaseModel):
    """上传请求"""
    target_folder: str
    extract_zip: bool = True
    verify_checksum: bool = False


class UploadResponse(BaseModel):
    """上传响应"""
    status: str
    message: str
    uploaded_files: int = 0
    total_size_mb: float = 0.0
    failed_files: List[Dict] = []


class FolderScanResponse(BaseModel):
    """文件夹扫描响应"""
    folder: str
    total_files: int
    total_size_mb: float
    files: List[Dict]


class BatchLoadRequest(BaseModel):
    """批量加载请求"""
    folder: str
    file_pattern: Optional[str] = "*.ogg"
    max_workers: int = 4


class BatchLoadResponse(BaseModel):
    """批量加载响应"""
    status: str
    loaded_files: int
    failed_files: List[Dict]
    metadata: Optional[List[Dict]] = None


# ============================================
# FastAPI 应用
# ============================================

app = FastAPI(title="Competition Data Upload API", version="1.0.0")

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局上传器实例
uploader = FolderUploader(max_workers=4)

# 上传任务存储（实际应用应使用 Redis）
upload_tasks: Dict[str, Dict] = {}


@app.get("/")
def root(request: Request):
    """根路径"""
    logger.info(f"Root request from {request.client.host}:{request.client.port}")
    return {
        "message": "Competition Data Upload API",
        "version": "1.0.0",
        "endpoints": [
            "/upload/files - 上传多个文件",
            "/upload/zip - 上传 ZIP 压缩包",
            "/folder/scan - 扫描文件夹",
            "/folder/manifest - 生成清单",
            "/batch/load - 批量加载文件",
            "/dataset/oog - 创建 OOG 数据集"
        ]
    }


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有请求详细信息"""
    client_host = request.client.host if request.client else 'unknown'
    logger.info(f"➡️  {request.method} {request.url.path} from {client_host}")
    logger.info(f"   Headers: {dict(request.headers)}")
    
    try:
        response = await call_next(request)
        logger.info(f"⬅️  {response.status_code} {request.url.path}")
        return response
    except Exception as e:
        logger.error(f"❌  Error processing {request.url.path}: {e}")
        raise


@app.post("/upload/files", response_model=UploadResponse)
async def upload_files(
    files: List[UploadFile] = File(...),
    target_folder: str = Form(...),
    preserve_structure: bool = Form(True)
):
    """
    上传多个文件
    
    Args:
        files: 文件列表
        target_folder: 目标文件夹路径
        preserve_structure: 是否保留原始目录结构
    """
    target = Path(target_folder)
    target.mkdir(parents=True, exist_ok=True)
    
    uploaded = []
    failed = []
    total_size = 0
    
    for file in files:
        try:
            # 确定目标路径
            if preserve_structure and file.filename:
                # 保留相对路径
                file_path = target / file.filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                file_path = target / file.filename
            
            # 保存文件
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
            
            uploaded.append(str(file.filename))
            total_size += len(content)
            
        except Exception as e:
            failed.append({"file": file.filename, "error": str(e)})
    
    return UploadResponse(
        status="success" if not failed else "partial",
        message=f"Uploaded {len(uploaded)} files, failed {len(failed)}",
        uploaded_files=len(uploaded),
        total_size_mb=total_size / (1024 * 1024),
        failed_files=failed
    )


@app.post("/upload/zip")
async def upload_zip(
    file: UploadFile = File(...),
    target_folder: str = Form(...),
    extract: bool = Form(True)
):
    """
    上传 ZIP 压缩包并解压
    
    Args:
        file: ZIP 文件
        target_folder: 解压目标文件夹
        extract: 是否自动解压
    """
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only ZIP files are supported")
    
    target = Path(target_folder)
    target.mkdir(parents=True, exist_ok=True)
    
    # 保存 ZIP 文件
    zip_path = target / file.filename
    with open(zip_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    extracted_files = []
    
    if extract:
        # 解压
        extract_dir = target / zip_path.stem
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
            extracted_files = zip_ref.namelist()
        
        # 删除 ZIP 文件（可选）
        zip_path.unlink()
    
    return {
        "status": "success",
        "message": f"ZIP uploaded and extracted to {extract_dir if extract else zip_path}",
        "zip_file": file.filename,
        "extracted_files": len(extracted_files),
        "files": extracted_files[:20]  # 只显示前20个
    }


@app.get("/folder/scan", response_model=FolderScanResponse)
def scan_folder(
    folder: str,
    pattern: Optional[str] = None,
    recursive: bool = True
):
    """
    扫描文件夹中的文件（支持音频和.ipynb）
    
    Args:
        folder: 文件夹路径
        pattern: 文件匹配模式 (如 "*.ogg")
        recursive: 是否递归扫描
    """
    try:
        files = uploader.scan_folder(folder, pattern=pattern, recursive=recursive)
        
        file_list = []
        for f in files:
            file_list.append({
                "filename": f.filename,
                "relative_path": str(f.relative_path),
                "size_mb": round(f.size_mb, 2)
            })
        
        return FolderScanResponse(
            folder=folder,
            total_files=len(files),
            total_size_mb=sum(f.size_mb for f in files),
            files=file_list
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/folder/manifest")
def create_manifest(
    folder: str = Form(...),
    output_file: Optional[str] = Form(None)
):
    """
    创建文件夹清单文件
    
    Args:
        folder: 文件夹路径
        output_file: 清单文件输出路径
    """
    try:
        output_path = Path(output_file) if output_file else None
        manifest = uploader.create_manifest(folder, output_path)
        
        return {
            "status": "success",
            "folder": manifest["folder"],
            "total_files": manifest["total_files"],
            "total_size_mb": manifest["total_size_mb"],
            "manifest_file": str(output_path) if output_path else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch/load")
async def batch_load_audio(request: BatchLoadRequest):
    """
    批量加载文件
    
    Args:
        request: 批量加载请求
    """
    try:
        import soundfile as sf
        
        def read_audio(path: Path) -> np.ndarray:
            y, sr = sf.read(path, dtype='float32')
            if y.ndim == 2:
                y = y.mean(axis=1)
            return y
        
        result = uploader.batch_load_audio(
            request.folder,
            read_func=read_audio,
            pattern=request.file_pattern,
            max_workers=request.max_workers
        )
        
        failed = [{"file": str(p), "error": e} for p, e in result.failed]
        
        metadata = None
        if result.metadata_df is not None:
            metadata = result.metadata_df.to_dict('records')
        
        return BatchLoadResponse(
            status="success" if not failed else "partial",
            loaded_files=len(result.successful),
            failed_files=failed,
            metadata=metadata
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/dataset/oog")
def create_oog_dataset(
    base_path: str = Form(...),
    n_splits: int = Form(5),
    group_col: str = Form("site")
):
    """
    创建支持 OOG 的 Competition 数据集
    
    Args:
        base_path: 基础数据路径
        n_splits: Fold 数量
        group_col: 分组列名
    """
    try:
        cfg = AudioConfig()
        dataset = CompetitionAudioDataset(base_path, cfg=cfg)
        
        # 加载标签
        dataset.load_labels()
        
        # 设置 OOG 分割
        dataset.setup_oog_splits(n_splits=n_splits, group_col=group_col)
        
        # 返回分割信息
        splits_info = {}
        for fold_idx, split in dataset.oog_splitter.splits.items():
            splits_info[fold_idx] = {
                "train_size": len(split["train"]),
                "val_size": len(split["val"]),
                "train_groups": len(split["train_groups"]),
                "val_groups": len(split["val_groups"])
            }
        
        return {
            "status": "success",
            "message": "OOG dataset created",
            "total_samples": len(dataset.sc_clean),
            "total_classes": dataset.n_classes,
            "n_folds": n_splits,
            "group_col": group_col,
            "splits": splits_info
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/download/manifest/{folder:path}")
def download_manifest(folder: str):
    """下载文件夹清单文件"""
    try:
        import json
        import io
        
        manifest = uploader.create_manifest(folder)
        
        # 转换为 JSON 流
        json_str = json.dumps(manifest, indent=2, ensure_ascii=False)
        json_bytes = json_str.encode('utf-8')
        
        return StreamingResponse(
            io.BytesIO(json_bytes),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=manifest_{Path(folder).name}.json"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/folder/clear")
def clear_folder(folder: str):
    """清空文件夹"""
    try:
        path = Path(folder)
        if path.exists():
            shutil.rmtree(path)
            return {"status": "success", "message": f"Folder {folder} cleared"}
        else:
            return {"status": "warning", "message": f"Folder {folder} does not exist"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# 启动服务器
# ============================================

def start_server(host="0.0.0.0", port=8001):
    """启动上传服务器"""
    import uvicorn
    print(f"Starting Upload API server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_server()
