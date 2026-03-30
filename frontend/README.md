# 前端文件夹上传功能

## 📁 文件结构

```
frontend/
├── upload.html              # 完整上传页面
├── upload_component.html    # 简化版组件（可嵌入 iframe）
├── js/
│   └── folderUploader.js    # JavaScript 模块
└── README.md                # 本文档
```

## 🚀 快速开始

### 方法 1: 直接访问上传页面

启动服务器后访问：
```
http://localhost:8000/upload
```

### 方法 2: 嵌入 iframe

```html
<iframe 
    src="http://localhost:8000/upload_component.html?api=http://localhost:8000/api/upload" 
    width="100%" 
    height="400"
    frameborder="0">
</iframe>
```

### 方法 3: 使用 JavaScript 模块

```html
<script src="js/folderUploader.js"></script>
<script>
    // 创建上传器
    const uploader = new FolderUploader({
        apiUrl: 'http://localhost:8000/api/upload',
        targetFolder: './uploads',
        batchSize: 10
    });
    
    // 绑定到文件输入
    uploader.bindToInput(document.getElementById('fileInput'));
    
    // 绑定到拖拽区域
    uploader.bindToDropZone(document.getElementById('dropZone'));
    
    // 监听事件
    uploader.addEventListener('progress', (e) => {
        console.log('进度:', e.detail.percent + '%');
    });
    
    uploader.addEventListener('complete', (e) => {
        console.log('完成:', e.detail);
    });
    
    // 开始上传
    document.getElementById('uploadBtn').onclick = () => {
        uploader.upload();
    };
</script>
```

## 📋 功能特性

| 特性 | 说明 |
|------|------|
| 📁 文件夹选择 | 使用 `webkitdirectory` 属性选择整个文件夹 |
| 📄 多文件选择 | 支持同时选择多个文件 |
| 🎯 拖拽上传 | 支持拖拽文件夹/文件到指定区域 |
| 📊 进度显示 | 实时显示上传进度 |
| 🗂️ 目录结构 | 可选保留原始目录结构 |
| 🔍 文件过滤 | 按扩展名过滤文件 |
| 📦 分批上传 | 自动分批上传，避免请求过大 |

## 🔧 配置选项

### FolderUploader 配置

| 选项 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `apiUrl` | string | `'http://localhost:8000/api/upload'` | API 地址 |
| `targetFolder` | string | `'./uploads'` | 服务器目标文件夹 |
| `batchSize` | number | `10` | 每批上传文件数 |
| `preserveStructure` | boolean | `true` | 保留目录结构 |

### 事件

| 事件名 | 触发时机 | 参数 |
|--------|---------|------|
| `filesAdded` | 添加文件后 | `{ files, total }` |
| `uploadStart` | 开始上传 | `{ totalFiles }` |
| `progress` | 进度更新 | `{ percent, uploaded, failed, total }` |
| `complete` | 上传完成 | `{ success, uploaded, failed, total }` |
| `cleared` | 清空列表 | - |

## 🌐 API 端点

后端需要提供以下 API：

### POST /upload/files
上传多个文件

**请求**: `multipart/form-data`
- `files`: 文件列表
- `target_folder`: 目标文件夹
- `preserve_structure`: 是否保留目录结构

**响应**:
```json
{
    "status": "success",
    "uploaded_files": 10,
    "total_size_mb": 50.5
}
```

### GET /folder/scan
扫描文件夹

**参数**:
- `folder`: 文件夹路径
- `pattern`: 文件匹配模式

**响应**:
```json
{
    "folder": "./data",
    "total_files": 100,
    "files": [{ "filename": "test.ogg", "size_mb": 5.2 }]
}
```

## 💡 使用示例

### 示例 1: 基础上传

```html
<!DOCTYPE html>
<html>
<head>
    <title>上传示例</title>
</head>
<body>
    <input type="file" id="fileInput" multiple webkitdirectory directory>
    <button id="uploadBtn">上传</button>
    <div id="progress"></div>

    <script src="js/folderUploader.js"></script>
    <script>
        const uploader = new FolderUploader();
        uploader.bindToInput(document.getElementById('fileInput'));
        
        uploader.addEventListener('progress', (e) => {
            document.getElementById('progress').textContent = 
                `${e.detail.percent.toFixed(1)}%`;
        });
        
        document.getElementById('uploadBtn').onclick = () => uploader.upload();
    </script>
</body>
</html>
```

### 示例 2: 拖拽上传

```html
<div id="dropZone" style="border: 2px dashed #ccc; padding: 50px; text-align: center;">
    拖拽文件夹到此处
</div>

<script>
    const uploader = new FolderUploader();
    uploader.bindToDropZone(document.getElementById('dropZone'), {
        autoUpload: true  // 自动开始上传
    });
</script>
```

### 示例 3: 带过滤的上传

```javascript
const uploader = new FolderUploader();

// 只上传 OGG 文件
uploader.bindToInput(document.getElementById('fileInput'), {
    filter: '.ogg',
    autoUpload: false
});
```

## 📝 浏览器兼容性

| 浏览器 | 文件夹选择 | 拖拽上传 |
|--------|-----------|---------|
| Chrome 86+ | ✅ | ✅ |
| Edge 86+ | ✅ | ✅ |
| Firefox 85+ | ✅ | ✅ |
| Safari 14+ | ❌ | ✅ |

> 注：Safari 不支持文件夹选择，但支持多文件选择和拖拽

## 🔒 安全提示

1. **CORS**: 确保后端已配置 CORS
2. **文件大小**: 建议限制单文件大小
3. **文件类型**: 始终验证文件类型，不要仅依赖前端
4. **路径遍历**: 后端需验证文件路径，防止目录遍历攻击

## 🐛 调试

打开浏览器开发者工具查看日志：

```javascript
// 启用调试日志
const uploader = new FolderUploader({
    apiUrl: 'http://localhost:8000/api/upload'
});

// 监听所有事件
['filesAdded', 'uploadStart', 'progress', 'complete'].forEach(event => {
    uploader.addEventListener(event, (e) => {
        console.log(`[${event}]`, e.detail);
    });
});
```
