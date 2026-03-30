/**
 * FolderUploader - 文件夹上传 JavaScript 模块
 * 
 * 使用方法:
 * ```html
 * <script src="folderUploader.js"></script>
 * <script>
 *   const uploader = new FolderUploader({
 *     apiUrl: 'http://localhost:8000/api/upload',
 *     targetFolder: './uploads',
 *     batchSize: 10
 *   });
 *   
 *   // 绑定到文件输入
 *   uploader.bindToInput(document.getElementById('fileInput'));
 *   
 *   // 监听事件
 *   uploader.on('progress', (e) => console.log(e.percent + '%'));
 *   uploader.on('complete', (e) => console.log('完成:', e));
 * </script>
 * ```
 */

class FolderUploader extends EventTarget {
    /**
     * 创建上传器实例
     * @param {Object} options - 配置选项
     * @param {string} options.apiUrl - API 地址
     * @param {string} options.targetFolder - 目标文件夹
     * @param {number} options.batchSize - 每批上传数量
     * @param {boolean} options.preserveStructure - 保留目录结构
     */
    constructor(options = {}) {
        super();
        this.apiUrl = options.apiUrl || 'http://localhost:8000/api/upload';
        this.targetFolder = options.targetFolder || './uploads';
        this.batchSize = options.batchSize || 10;
        this.preserveStructure = options.preserveStructure !== false;
        
        this.files = [];
        this.isUploading = false;
        this.uploadedCount = 0;
        this.failedCount = 0;
    }
    
    /**
     * 支持的音频格式
     */
    static get SUPPORTED_FORMATS() {
        return ['.ogg', '.wav', '.mp3', '.flac', '.m4a', '.webm', '.ipynb'];
    }
    
    /**
     * 格式化文件大小
     */
    static formatSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    /**
     * 检查文件类型是否支持
     */
    static isSupported(filename) {
        const ext = '.' + filename.split('.').pop().toLowerCase();
        return FolderUploader.SUPPORTED_FORMATS.includes(ext);
    }
    
    /**
     * 添加文件
     * @param {FileList|File[]} fileList - 文件列表
     * @param {Object} options - 选项
     * @param {string} options.filter - 过滤扩展名
     * @returns {number} 添加的文件数量
     */
    addFiles(fileList, options = {}) {
        const added = [];
        
        Array.from(fileList).forEach(file => {
            // 类型检查
            if (!FolderUploader.isSupported(file.name)) {
                return;
            }
            
            // 过滤检查
            if (options.filter) {
                const ext = '.' + file.name.split('.').pop().toLowerCase();
                if (ext !== options.filter) return;
            }
            
            // 去重检查
            const exists = this.files.some(f => 
                f.name === file.name && f.size === file.size
            );
            
            if (!exists) {
                // 添加路径信息
                if (file.webkitRelativePath) {
                    file.relativePath = file.webkitRelativePath;
                }
                this.files.push(file);
                added.push(file);
            }
        });
        
        this.dispatchEvent(new CustomEvent('filesAdded', {
            detail: { files: added, total: this.files.length }
        }));
        
        return added.length;
    }
    
    /**
     * 清空文件列表
     */
    clear() {
        this.files = [];
        this.uploadedCount = 0;
        this.failedCount = 0;
        this.dispatchEvent(new CustomEvent('cleared'));
    }
    
    /**
     * 获取文件列表
     */
    getFiles() {
        return [...this.files];
    }
    
    /**
     * 获取总大小
     */
    getTotalSize() {
        return this.files.reduce((sum, f) => sum + f.size, 0);
    }
    
    /**
     * 绑定到文件输入元素
     * @param {HTMLInputElement} input - 文件输入元素
     * @param {Object} options - 选项
     */
    bindToInput(input, options = {}) {
        input.addEventListener('change', (e) => {
            const count = this.addFiles(e.target.files, options);
            if (options.autoUpload && count > 0) {
                this.upload();
            }
        });
    }
    
    /**
     * 绑定到拖拽区域
     * @param {HTMLElement} element - 拖拽区域元素
     * @param {Object} options - 选项
     */
    bindToDropZone(element, options = {}) {
        element.addEventListener('dragover', (e) => {
            e.preventDefault();
            element.classList.add('dragover');
        });
        
        element.addEventListener('dragleave', () => {
            element.classList.remove('dragover');
        });
        
        element.addEventListener('drop', (e) => {
            e.preventDefault();
            element.classList.remove('dragover');
            
            const files = [];
            
            // 处理拖拽的文件/文件夹
            const traverse = (item, path = '') => {
                if (item.isFile) {
                    item.file(file => {
                        file.relativePath = path + file.name;
                        files.push(file);
                    });
                } else if (item.isDirectory) {
                    const reader = item.createReader();
                    reader.readEntries(entries => {
                        entries.forEach(entry => {
                            traverse(entry, path + item.name + '/');
                        });
                    });
                }
            };
            
            const items = e.dataTransfer.items;
            for (let i = 0; i < items.length; i++) {
                const item = items[i].webkitGetAsEntry();
                if (item) traverse(item);
            }
            
            // 延迟处理
            setTimeout(() => {
                const count = this.addFiles(files, options);
                if (options.autoUpload && count > 0) {
                    this.upload();
                }
            }, 100);
        });
    }
    
    /**
     * 开始上传
     * @returns {Promise<Object>} 上传结果
     */
    async upload() {
        if (this.isUploading || this.files.length === 0) {
            return { success: false, message: 'No files to upload' };
        }
        
        this.isUploading = true;
        this.uploadedCount = 0;
        this.failedCount = 0;
        
        this.dispatchEvent(new CustomEvent('uploadStart', {
            detail: { totalFiles: this.files.length }
        }));
        
        // 分批上传
        for (let i = 0; i < this.files.length; i += this.batchSize) {
            const batch = this.files.slice(i, i + this.batchSize);
            
            try {
                await this._uploadBatch(batch);
                this.uploadedCount += batch.length;
            } catch (error) {
                this.failedCount += batch.length;
                console.error('Batch upload failed:', error);
            }
            
            // 进度事件
            const percent = ((i + this.batchSize) / this.files.length * 100);
            this.dispatchEvent(new CustomEvent('progress', {
                detail: {
                    percent: Math.min(percent, 100),
                    uploaded: this.uploadedCount,
                    failed: this.failedCount,
                    total: this.files.length
                }
            }));
        }
        
        this.isUploading = false;
        
        const result = {
            success: this.failedCount === 0,
            uploaded: this.uploadedCount,
            failed: this.failedCount,
            total: this.files.length
        };
        
        this.dispatchEvent(new CustomEvent('complete', { detail: result }));
        
        return result;
    }
    
    /**
     * 上传一批文件
     * @private
     */
    async _uploadBatch(batch) {
        const formData = new FormData();
        formData.append('target_folder', this.targetFolder);
        formData.append('preserve_structure', this.preserveStructure);
        
        batch.forEach(file => {
            const path = this.preserveStructure ? (file.relativePath || file.name) : file.name;
            formData.append('files', file, path);
        });
        
        const response = await fetch(`${this.apiUrl}/upload/files`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.text();
            throw new Error(error);
        }
        
        return await response.json();
    }
    
    /**
     * 扫描服务器上的文件夹
     * @param {string} folder - 文件夹路径
     * @param {string} pattern - 文件匹配模式
     */
    async scanFolder(folder, pattern = '*') {
        const params = new URLSearchParams({ folder, pattern });
        const response = await fetch(`${this.apiUrl}/folder/scan?${params}`);
        return await response.json();
    }
    
    /**
     * 批量加载音频（服务器端）
     * @param {string} folder - 文件夹路径
     * @param {Object} options - 选项
     */
    async batchLoad(folder, options = {}) {
        const response = await fetch(`${this.apiUrl}/batch/load`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                folder,
                file_pattern: options.pattern || '*.ogg',
                max_workers: options.maxWorkers || 4
            })
        });
        return await response.json();
    }
}

// 导出模块
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FolderUploader;
}
