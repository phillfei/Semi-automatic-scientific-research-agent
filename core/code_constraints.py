"""
代码约束验证器

严格检查生成的代码是否符合：
1. 不修改 baseline 原有代码
2. 使用增量修改模式
3. API 兼容性
4. 不引入破坏性变更
"""

import re
import ast
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from enum import Enum


class ViolationLevel(str, Enum):
    """违规级别"""
    ERROR = "error"       # 必须修复
    WARNING = "warning"   # 建议修复
    INFO = "info"         # 仅供参考


@dataclass
class CodeViolation:
    """代码违规"""
    level: ViolationLevel
    rule: str
    message: str
    line_number: int = 0
    suggestion: str = ""


class CodeConstraintValidator:
    """
    代码约束验证器
    
    验证生成的优化代码是否严格遵守 baseline 约束
    """
    
    # 禁止的修改模式
    FORBIDDEN_PATTERNS = {
        "direct_modification": {
            "name": "直接修改 baseline 代码",
            "description": "生成的代码不能包含对 baseline 函数/类的直接修改",
            "level": ViolationLevel.ERROR,
            "patterns": [
                # 检测直接替换函数体
                r'^\s*def\s+\w+\s*\([^)]*\)\s*:\s*\n(\s+.+\n)+',
                # 检测修改类属性
                r'\w+\.__dict__\[',
                # 检测猴子补丁（monkey patching）
                r'\w+\s*=\s*\w+\s*#.*(?:override|replace)',
            ]
        },
        "signature_change": {
            "name": "修改函数签名",
            "description": "不能改变 baseline 函数的参数列表",
            "level": ViolationLevel.ERROR,
            "patterns": [
                r'def\s+\w+\s*\([^)]*\*\*kwargs[^)]*\)\s*->',  # 添加类型注解可能改变签名
            ]
        },
        "api_break": {
            "name": "破坏 API 兼容性",
            "description": "不能删除或重命名 baseline 的公共 API",
            "level": ViolationLevel.ERROR,
            "patterns": [
                r'del\s+\w+',  # 删除变量
                r'^\s*\w+\s*=\s*None\s*$',  # 清空变量
            ]
        },
        "global_state": {
            "name": "修改全局状态",
            "description": "谨慎修改全局变量，应通过配置传入",
            "level": ViolationLevel.WARNING,
            "patterns": [
                r'^\w+\s*=\s*[^=]',  # 全局变量赋值
                r'global\s+\w+',
            ]
        },
        "import_pollution": {
            "name": "导入污染",
            "description": "导入的库可能与 baseline 冲突",
            "level": ViolationLevel.WARNING,
            "forbidden_imports": [
                "numpy", "torch", "tensorflow"  # 版本可能冲突
            ]
        }
    }
    
    # 推荐的增量修改模式
    RECOMMENDED_PATTERNS = {
        "decorator": {
            "indicators": ["@", "decorator", "wraps"],
            "score": 10
        },
        "inheritance": {
            "indicators": ["class.*\(", "super()", "__init__"],
            "score": 10
        },
        "wrapper": {
            "indicators": ["wrapper", "wrapped", "lambda.*:"],
            "score": 10
        },
        "callback": {
            "indicators": ["callback", "hook", "on_epoch", "on_batch"],
            "score": 10
        },
        "config": {
            "indicators": ["config", "cfg", "settings"],
            "score": 8
        }
    }
    
    def __init__(self, baseline_code: str = ""):
        self.baseline_code = baseline_code
        self.baseline_functions = self._extract_functions(baseline_code)
        self.baseline_classes = self._extract_classes(baseline_code)
    
    def validate(
        self,
        generated_code: str,
        strict_mode: bool = False
    ) -> Dict:
        """
        验证生成的代码
        
        Args:
            generated_code: 生成的优化代码
            strict_mode: 严格模式（任何警告都视为错误）
            
        Returns:
            {
                "valid": bool,
                "violations": [CodeViolation, ...],
                "score": float,  # 0-100，代码质量评分
                "recommendations": [str, ...]
            }
        """
        violations = []
        
        # 1. 检查禁止的修改模式
        violations.extend(self._check_forbidden_patterns(generated_code))
        
        # 2. 检查是否修改了 baseline 的函数/类
        violations.extend(self._check_baseline_modifications(generated_code))
        
        # 3. 检查增量修改模式的使用
        pattern_score = self._check_incremental_patterns(generated_code)
        
        # 4. 检查导入冲突
        violations.extend(self._check_import_conflicts(generated_code))
        
        # 5. 检查代码结构
        violations.extend(self._check_code_structure(generated_code))
        
        # 计算总体评分
        score = self._calculate_score(violations, pattern_score)
        
        # 生成建议
        recommendations = self._generate_recommendations(violations, pattern_score)
        
        # 判断是否通过
        has_errors = any(v.level == ViolationLevel.ERROR for v in violations)
        has_warnings = any(v.level == ViolationLevel.WARNING for v in violations)
        
        is_valid = not has_errors and (not strict_mode or not has_warnings)
        
        return {
            "valid": is_valid,
            "violations": [
                {
                    "level": v.level.value,
                    "rule": v.rule,
                    "message": v.message,
                    "line": v.line_number,
                    "suggestion": v.suggestion
                }
                for v in violations
            ],
            "score": score,
            "recommendations": recommendations,
            "pattern_score": pattern_score
        }
    
    def _extract_functions(self, code: str) -> Set[str]:
        """提取代码中的函数名"""
        functions = set()
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.add(node.name)
        except:
            pass
        return functions
    
    def _extract_classes(self, code: str) -> Set[str]:
        """提取代码中的类名"""
        classes = set()
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.add(node.name)
        except:
            pass
        return classes
    
    def _check_forbidden_patterns(self, code: str) -> List[CodeViolation]:
        """检查禁止的模式"""
        violations = []
        lines = code.split('\n')
        
        for rule_name, rule_config in self.FORBIDDEN_PATTERNS.items():
            for pattern in rule_config.get("patterns", []):
                for i, line in enumerate(lines, 1):
                    if re.search(pattern, line):
                        violations.append(CodeViolation(
                            level=rule_config["level"],
                            rule=rule_name,
                            message=f"检测到: {rule_config['name']}",
                            line_number=i,
                            suggestion=f"避免 {rule_config['description']}"
                        ))
        
        return violations
    
    def _check_baseline_modifications(self, code: str) -> List[CodeViolation]:
        """检查是否修改了 baseline"""
        violations = []
        
        if not self.baseline_code:
            return violations
        
        # 提取生成的代码中的函数和类
        generated_functions = self._extract_functions(code)
        generated_classes = self._extract_classes(code)
        
        # 检查是否有重名（可能是覆盖）
        for func in generated_functions:
            if func in self.baseline_functions:
                # 检查是否是继承（允许）
                if f"super().{func}" not in code and f"self.{func}" not in code:
                    violations.append(CodeViolation(
                        level=ViolationLevel.WARNING,
                        rule="function_override",
                        message=f"函数 '{func}' 与 baseline 重名，可能是覆盖",
                        suggestion="使用装饰器模式或继承，避免直接覆盖"
                    ))
        
        for cls in generated_classes:
            if cls in self.baseline_classes:
                violations.append(CodeViolation(
                    level=ViolationLevel.ERROR,
                    rule="class_override",
                    message=f"类 '{cls}' 与 baseline 重名",
                    suggestion="重命名新类或使用继承扩展"
                ))
        
        return violations
    
    def _check_incremental_patterns(self, code: str) -> float:
        """检查增量修改模式的使用"""
        score = 0
        
        for pattern_name, pattern_info in self.RECOMMENDED_PATTERNS.items():
            for indicator in pattern_info["indicators"]:
                if re.search(indicator, code, re.IGNORECASE):
                    score += pattern_info["score"]
                    break
        
        # 归一化到 0-100
        max_score = sum(p["score"] for p in self.RECOMMENDED_PATTERNS.values())
        return min(100, (score / max_score) * 100) if max_score > 0 else 0
    
    def _check_import_conflicts(self, code: str) -> List[CodeViolation]:
        """检查导入冲突"""
        violations = []
        
        # 提取导入语句
        import_lines = re.findall(r'^(?:import|from)\s+(\w+)', code, re.MULTILINE)
        
        for forbidden in self.FORBIDDEN_PATTERNS["import_pollution"]["forbidden_imports"]:
            if forbidden in import_lines:
                violations.append(CodeViolation(
                    level=ViolationLevel.WARNING,
                    rule="import_conflict",
                    message=f"导入 '{forbidden}' 可能与 baseline 版本冲突",
                    suggestion=f"检查 baseline 的 {forbidden} 版本，确保兼容"
                ))
        
        return violations
    
    def _check_code_structure(self, code: str) -> List[CodeViolation]:
        """检查代码结构"""
        violations = []
        
        # 检查是否有主逻辑（不应该有，应该是库形式）
        if re.search(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]', code):
            violations.append(CodeViolation(
                level=ViolationLevel.INFO,
                rule="main_block",
                message="代码包含 __main__ 块",
                suggestion="作为库使用，移除主逻辑或改为示例"
            ))
        
        # 检查是否有硬编码路径
        if re.search(r'[\'"]/\w+[/\w]*[\'"]', code):
            violations.append(CodeViolation(
                level=ViolationLevel.WARNING,
                rule="hardcoded_path",
                message="检测到硬编码路径",
                suggestion="使用配置或参数传入路径"
            ))
        
        return violations
    
    def _calculate_score(self, violations: List[CodeViolation], pattern_score: float) -> float:
        """计算总体评分"""
        base_score = 100
        
        for v in violations:
            if v.level == ViolationLevel.ERROR:
                base_score -= 20
            elif v.level == ViolationLevel.WARNING:
                base_score -= 10
            elif v.level == ViolationLevel.INFO:
                base_score -= 2
        
        # 结合模式分数
        final_score = (base_score * 0.6) + (pattern_score * 0.4)
        
        return max(0, min(100, final_score))
    
    def _generate_recommendations(
        self,
        violations: List[CodeViolation],
        pattern_score: float
    ) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 基于违规生成建议
        error_rules = set()
        warning_rules = set()
        
        for v in violations:
            if v.level == ViolationLevel.ERROR:
                error_rules.add(v.rule)
            elif v.level == ViolationLevel.WARNING:
                warning_rules.add(v.rule)
        
        if "direct_modification" in error_rules:
            recommendations.append("使用装饰器模式或继承，不要直接修改 baseline 函数")
        
        if "class_override" in error_rules:
            recommendations.append("重命名新类，或确保继承自 baseline 类并使用 super()")
        
        if pattern_score < 50:
            recommendations.append("代码缺少明确的增量修改模式，建议添加装饰器、继承或包装器")
        
        if not recommendations:
            recommendations.append("代码结构良好，符合增量修改原则")
        
        return recommendations


# 便捷函数
def validate_code(
    generated_code: str,
    baseline_code: str = "",
    strict_mode: bool = False
) -> Dict:
    """
    便捷函数：验证代码
    
    Args:
        generated_code: 生成的代码
        baseline_code: baseline 代码
        strict_mode: 严格模式
        
    Returns:
        验证结果
    """
    validator = CodeConstraintValidator(baseline_code)
    return validator.validate(generated_code, strict_mode)
