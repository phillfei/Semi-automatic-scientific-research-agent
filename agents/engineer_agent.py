"""
工程师Agent - 基于 EvoAgentX
负责：生成代码和测试
"""

from evoagentx.agents import Agent
from evoagentx.tools import PythonInterpreterToolkit, FileToolkit
from evoagentx.actions.code_extraction import CodeExtraction
from utils.agent_logger import get_agent_logger, log_agent_method
import os
from datetime import datetime
import time


class EngineerAgent(Agent):
    """工程师Agent"""
    
    def __init__(self, llm):
        super().__init__(
            name="Engineer",
            description="工程师Agent，负责生成高质量代码和测试用例",
            llm=llm,
            system_prompt="""你是工程师Agent，负责生成高质量的Python代码。

代码要求：
1. 代码必须完整、可运行
2. 添加详细的中文注释
3. 遵循PEP8规范
4. 包含错误处理
5. 提供使用示例

测试代码要求：
1. 覆盖主要功能
2. 包含边界条件测试
3. 提供性能测试
4. 使用pytest框架"""
        )
        self.code_toolkit = PythonInterpreterToolkit()
        self.file_toolkit = FileToolkit()
        self.logger = get_agent_logger()
        
        # 初始化 CodeExtraction 用于代码保存
        self.code_extractor = CodeExtraction()
    
    @log_agent_method("name")
    def generate_code_and_tests(self, search_results, original_code, project_name, data_info=""):
        """生成代码和测试"""
        print(f"\n👨‍💻 Engineer: 开始生成代码")
        
        generated_items = []
        
        # 检查是否是 Competition 项目
        is_competition = 'competition' in project_name.lower() or 'birdclef' in project_name.lower()
        
        # 为每个方向生成代码
        for i, result in enumerate(search_results, 1):
            direction_name = result.get('direction_name', f'方向{i}')
            summary = result.get('summary', '')
            
            print(f"  📝 生成: {direction_name}")
            
            # 如果是 Competition 项目且方向涉及数据加载，生成 OOG 支持代码
            if is_competition and any(kw in direction_name.lower() for kw in ['data', 'oog', 'cv', 'cross']):
                main_code = self._generate_oog_data_code()
                test_code = self._generate_oog_test_code()
            else:
                # 生成主代码
                main_code = self._generate_main_code(
                    original_code=original_code,
                    direction=direction_name,
                    summary=summary,
                    papers=result.get('papers', []),
                    data_info=data_info,
                    project_name=project_name
                )
                
                # 生成测试代码
                test_code = self._generate_test_code(
                    main_code=main_code,
                    direction=direction_name
                )
            
            # 验证代码
            validation = self._validate_code(main_code, test_code)
            
            generated_items.append({
                "direction": direction_name,
                "main_code": main_code,
                "test_code": test_code,
                "validation": validation,
                "timestamp": datetime.now().isoformat()
            })
            
            print(f"    ✅ 代码生成完成")
        
        print(f"  ✅ 共生成 {len(generated_items)} 组代码")
        
        return {
            "generated_items": generated_items,
            "total_count": len(generated_items)
        }
    
    @log_agent_method("name")
    def _generate_oog_data_code(self) -> str:
        """生成支持 OOG 的数据加载代码"""
        self.logger.log_step("Engineer", "_generate_oog_data_code", "开始生成 OOG 数据加载代码")
        try:
            from tools.competition_codegen import generate_oog_template
            
            config = {
                "sr": 32000,
                "window_sec": 5
            }
            
            code = generate_oog_template(config=config)
            self.logger.log_step("Engineer", "_generate_oog_data_code", "OOG 代码生成成功")
            return code
        except Exception as e:
            self.logger.log_agent_error("Engineer", "_generate_oog_data_code", e)
            print(f"    ⚠️ OOG code generation failed: {e}")
            return "# OOG code generation failed\n"
    
    def _generate_oog_test_code(self) -> str:
        """生成 OOG 数据加载的测试代码"""
        code = '''"""
测试 OOG 数据加载
"""

import pytest
import numpy as np
from pathlib import Path


def test_oog_dataset_init():
    """测试 OOG 数据集初始化"""
    # 这里添加测试代码
    pass


def test_oog_splits():
    """测试 OOG 分割"""
    # 验证同一 group 不会同时出现在 train/val
    pass


def test_audio_reading():
    """测试音频读取"""
    # 测试音频读取和窗口分割
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
'''
        return code
    
    @log_agent_method("name")
    def _generate_main_code(self, original_code, direction, summary, papers, data_info="", project_name=""):
        """生成主实现代码"""
        self.logger.log_step("Engineer", "_generate_main_code", f"生成方向: {direction}")
        
        prompt = f"""请基于以下信息生成优化后的Python代码：

## 项目背景
{project_name}

## 优化方向
{direction}

## 研究总结
{summary}

## 参考论文
"""
        for paper in papers[:2]:
            prompt += f"- {paper.get('title', '')}\n"
            prompt += f"  方法: {paper.get('abstract', '')[:200]}...\n\n"
        
        prompt += f"""
## 数据信息（必须适配）
{data_info if data_info else '无特定数据路径信息'}

## 原始代码
```python
{original_code[:3000] if original_code else '# 无原始代码'}
```

## 要求
1. 基于原始代码进行优化，不要完全重写，保留原有逻辑框架
2. 应用"{direction}"方向的最新研究成果
3. 如果提供了数据路径/格式信息，代码中的数据读取路径必须与实际一致
4. 代码必须完整可运行
5. 添加详细中文注释
6. 包含__main__示例

请直接输出完整的Python代码：
"""
        
        start_time = time.time()
        code = self.llm.generate(prompt=prompt)
        duration_ms = (time.time() - start_time) * 1000
        
        self.logger.log_llm_call("Engineer", len(prompt), len(code), duration_ms)
        
        # 清理代码（去除可能的markdown标记）
        code = self._clean_code(code)
        
        return code
    
    @log_agent_method("name")
    def _generate_test_code(self, main_code, direction):
        """生成测试代码"""
        self.logger.log_step("Engineer", "_generate_test_code", f"为方向生成测试: {direction}")
        
        prompt = f"""请为以下代码生成测试用例：

## 优化方向
{direction}

## 代码
```python
{main_code[:2000]}
```

## 要求
1. 使用pytest框架
2. 测试主要功能
3. 包含边界条件测试
4. 添加性能测试（可选）
5. 包含中文注释说明

请直接输出测试代码：
"""
        
        test_code = self.llm.generate(prompt=prompt)
        test_code = self._clean_code(test_code)
        
        return test_code
    
    def _validate_code(self, main_code, test_code):
        """验证代码"""
        # 简化验证，实际可以使用code_toolkit执行验证
        checks = {
            "syntax_ok": self._check_syntax(main_code),
            "has_main": "__main__" in main_code,
            "has_tests": "def test_" in test_code or "import pytest" in test_code,
            "has_comments": "# " in main_code
        }
        
        checks["overall"] = all(checks.values())
        
        return checks
    
    def _check_syntax(self, code):
        """检查语法"""
        try:
            compile(code, '<string>', 'exec')
            return True
        except SyntaxError:
            return False
    
    def _clean_code(self, code):
        """清理代码"""
        # 去除markdown代码块标记
        if code.startswith("```python"):
            code = code[9:]
        elif code.startswith("```"):
            code = code[3:]
        
        if code.endswith("```"):
            code = code[:-3]
        
        return code.strip()
    
    @log_agent_method("name")
    def save_generated_code(self, generated_items, output_dir="./output"):
        """保存生成的代码（使用 CodeExtraction）"""
        self.logger.log_step("Engineer", "save_generated_code", f"保存 {len(generated_items)} 组代码到 {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
        
        saved_files = []
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for i, item in enumerate(generated_items, 1):
            direction = item.get('direction', f'direction_{i}')
            direction_slug = direction.replace(' ', '_').replace('/', '_')[:30]
            
            # 准备代码块（符合 CodeExtraction 格式）
            code_blocks = [
                {
                    "filename": f"{timestamp}_{i}_{direction_slug}_main.py",
                    "content": item['main_code']
                },
                {
                    "filename": f"{timestamp}_{i}_{direction_slug}_test.py",
                    "content": item['test_code']
                }
            ]
            
            # 使用 CodeExtraction 保存代码块
            project_dir = os.path.join(output_dir, f"{timestamp}_{i}_{direction_slug}")
            saved = self.code_extractor.save_code_blocks(code_blocks, project_dir)
            
            saved_files.extend(list(saved.values()))
            
            # 识别主文件
            main_file = self.code_extractor.identify_main_file(saved)
            if main_file:
                print(f"    🔑 主文件: {os.path.basename(main_file)}")
            
            for filename, filepath in saved.items():
                print(f"    💾 {filename}")
        
        return saved_files
    
    @log_agent_method("name")
    def extract_and_save_code_from_llm_output(self, llm_output: str, output_dir: str = "./output", project_name: str = None):
        """
        从 LLM 输出中提取代码块并保存
        
        使用 CodeExtraction Action 智能提取代码块，自动识别文件名和语言类型
        
        Args:
            llm_output: LLM 生成的包含代码块的文本
            output_dir: 输出目录
            project_name: 可选的项目名称（作为子目录）
            
        Returns:
            dict: {
                "extracted_files": {filename: filepath},
                "main_file": 主文件路径,
                "error": 错误信息（如果有）
            }
        """
        self.logger.log_step("Engineer", "extract_and_save_code", f"从 LLM 输出提取代码到 {output_dir}")
        
        inputs = {
            "code_string": llm_output,
            "target_directory": output_dir,
            "project_name": project_name
        }
        
        try:
            result = self.code_extractor.execute(
                llm=self.llm,
                inputs=inputs,
                return_prompt=False
            )
            
            if result.error:
                print(f"    ⚠️ 代码提取失败: {result.error}")
                self.logger.log_agent_error("Engineer", "extract_and_save_code", Exception(result.error))
            else:
                print(f"    ✅ 成功提取 {len(result.extracted_files)} 个文件")
                if result.main_file:
                    print(f"    🔑 主文件: {os.path.basename(result.main_file)}")
                for filename in result.extracted_files.keys():
                    print(f"    💾 {filename}")
                    
            return {
                "extracted_files": result.extracted_files,
                "main_file": result.main_file,
                "error": result.error
            }
            
        except Exception as e:
            error_msg = f"代码提取异常: {str(e)}"
            print(f"    ⚠️ {error_msg}")
            self.logger.log_agent_error("Engineer", "extract_and_save_code", e)
            return {
                "extracted_files": {},
                "main_file": None,
                "error": error_msg
            }