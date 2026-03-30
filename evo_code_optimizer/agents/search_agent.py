"""
搜索Agent - 基于 EvoAgentX
负责：并行检索论文和资源，生成Markdown报告
支持迭代搜索、知识库存储、向Supervisor汇报
"""

from evoagentx.agents import Agent
from evoagentx.tools import ArxivToolkit, BrowserToolkit
from utils.agent_logger import get_agent_logger, log_agent_method
import concurrent.futures
import time


class SearchAgent(Agent):
    """搜索Agent"""
    
    def __init__(self, llm, project_manager=None):
        super().__init__(
            name="Search",
            description="搜索Agent，负责并行检索学术资源和开源项目",
            llm=llm,
            system_prompt="""你是搜索Agent，负责：
1. 并行检索学术资源（arXiv、论文）
2. 搜索开源项目和文档
3. 整理关键技术点
4. 生成Markdown格式研究报告

搜索策略：
- 优先搜索近5年的论文
- 关注高引用论文
- 提取核心方法和创新点
- 对比不同方法的优缺点"""
        )
        self.arxiv_tool = ArxivToolkit()
        self.browser_tool = BrowserToolkit()
        self.logger = get_agent_logger()
        self.project_manager = project_manager
    
    @log_agent_method("name")
    def parallel_search(self, tasks, total_time_limit=5, project_name=""):
        """并行搜索多个方向，支持迭代搜索和知识库复用"""
        print(f"\n🔍 Search: 开始并行搜索 {len(tasks)} 个方向")
        print(f"   总时间限制: {total_time_limit}分钟")
        
        # 计算每个任务的时间
        time_per_task = (total_time_limit * 60) // len(tasks) if tasks else 300
        
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_task = {
                executor.submit(self._search_direction_iterative, task, time_per_task, project_name): task 
                for task in tasks
            }
            
            for future in concurrent.futures.as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                    print(f"  ✅ 完成: {task.get('direction_name', '未知方向')}")
                except Exception as e:
                    print(f"  ❌ 失败: {task.get('direction_name', '未知方向')} - {e}")
        
        # 生成Markdown报告
        markdown_report = self._generate_markdown_report(results)
        
        # 保存到知识库
        if project_name and self.project_manager:
            for result in results:
                self.project_manager.save_search_report(
                    project_name=project_name,
                    direction_name=result.get("direction_name", "未知方向"),
                    keywords=result.get("keywords", []),
                    report=result.get("summary", ""),
                    search_results=result.get("papers", [])
                )
            print(f"  💾 搜索报告已存入项目知识库: {project_name}")
        
        print(f"  ✅ 搜索完成，生成 {len(results)} 份报告")
        
        return {
            "search_results": results,
            "markdown_report": markdown_report
        }
    
    @log_agent_method("name")
    def _search_direction_iterative(self, task, time_limit, project_name=""):
        """迭代搜索单个方向，支持知识库复用"""
        direction_name = task.get('direction_name', '未知方向')
        keywords = task.get('keywords', [])
        
        print(f"  🔍 搜索: {direction_name}")
        self.logger.log_step("Search", "_search_direction_iterative", f"开始迭代搜索: {direction_name}", 
                            {"keywords": keywords, "time_limit": time_limit})
        
        # 1. 尝试从知识库复用
        if project_name and self.project_manager:
            cached = self.project_manager.get_search_report(project_name, direction_name, keywords)
            if cached:
                print(f"    ♻️ 从知识库复用报告: {direction_name} (已使用{cached.get('use_count', 1)}次)")
                self.logger.log_step("Search", "cache_hit", f"复用知识库报告: {direction_name}")
                return {
                    "direction_name": direction_name,
                    "keywords": keywords,
                    "papers": cached.get("search_results", []),
                    "repositories": [],
                    "summary": cached.get("report", ""),
                    "rationale": task.get('rationale', ''),
                    "from_cache": True
                }
        
        # 2. 第一轮搜索
        query = " ".join(keywords) if isinstance(keywords, list) else str(keywords)
        start_time = time.time()
        papers_round1 = self._search_papers(query, max_results=3)
        search_duration = (time.time() - start_time) * 1000
        self.logger.log_search_result("Search", query, len(papers_round1), search_duration)
        
        # 3. 动态调整关键词（迭代搜索）
        adjusted_keywords = keywords
        papers_round2 = []
        if papers_round1 and time_limit > 120:  # 如果时间充裕，进行第二轮迭代搜索
            adjusted_keywords = self._refine_keywords(direction_name, keywords, papers_round1)
            if adjusted_keywords != keywords:
                query2 = " ".join(adjusted_keywords) if isinstance(adjusted_keywords, list) else str(adjusted_keywords)
                print(f"    🔄 调整关键词: {keywords} → {adjusted_keywords}")
                self.logger.log_step("Search", "keyword_refine", f"关键词调整: {keywords} → {adjusted_keywords}")
                papers_round2 = self._search_papers(query2, max_results=3)
                self.logger.log_search_result("Search", query2, len(papers_round2), 0)
        
        # 合并去重
        all_papers = papers_round1
        seen_titles = {p['title'] for p in all_papers}
        for p in papers_round2:
            if p['title'] not in seen_titles:
                all_papers.append(p)
                seen_titles.add(p['title'])
        
        # 4. 搜索GitHub/开源项目
        repos = self._search_repositories(query)
        
        # 5. 使用LLM整理搜索结果
        summary = self._summarize_results(direction_name, all_papers, repos)
        
        return {
            "direction_name": direction_name,
            "keywords": adjusted_keywords,
            "papers": all_papers,
            "repositories": repos,
            "summary": summary,
            "rationale": task.get('rationale', ''),
            "from_cache": False
        }
    
    def _refine_keywords(self, direction_name, original_keywords, papers):
        """基于初步搜索结果动态调整关键词"""
        if not papers:
            return original_keywords
        
        prompt = f"""你正在搜索关于"{direction_name}"的学术资源。

原始关键词: {', '.join(original_keywords)}

初步搜索到的论文:
"""
        for i, paper in enumerate(papers[:3], 1):
            prompt += f"{i}. {paper['title']}\n"
            prompt += f"   摘要: {paper['abstract'][:300]}...\n\n"
        
        prompt += """
请分析初步搜索结果，判断是否需要调整关键词以获得更精准的结果。

要求:
1. 如果初步结果已经很好，直接返回原始关键词
2. 如果结果偏离主题或不够精准，请优化关键词（添加更具体的技术术语，或替换过于宽泛的词）
3. 返回3-5个关键词，用逗号分隔

只输出关键词列表，不要任何解释:"""
        
        try:
            result = self.llm.generate(prompt=prompt)
            # 解析关键词
            keywords = [k.strip() for k in result.replace('\n', ',').split(',') if k.strip()]
            if len(keywords) >= 2:
                return keywords[:5]
        except Exception as e:
            self.logger.log_agent_error("Search", "_refine_keywords", e)
        
        return original_keywords
    
    def _search_papers(self, query, max_results=5):
        """搜索学术论文"""
        self.logger.log_step("Search", "_search_papers", f"搜索论文: {query[:50]}...")
        try:
            # 使用Arxiv工具 - 通过 arxiv_base 调用 search_arxiv
            result = self.arxiv_tool.arxiv_base.search_arxiv(
                search_query=query, 
                max_results=max_results
            )
            
            # 检查结果是否成功
            if not result.get('success', False):
                error_msg = result.get('error', '未知错误')
                print(f"    ⚠️ arXiv 搜索失败: {error_msg}")
                return []
            
            # 提取论文列表
            papers = []
            for paper in result.get('papers', []):
                papers.append({
                    "title": paper.get('title', '未知标题'),
                    "authors": paper.get('authors', []),
                    "abstract": paper.get('summary', '')[:500],  # arXiv API 使用 'summary' 作为摘要字段
                    "url": paper.get('url', ''),
                    "year": paper.get('published_date', '').split('-')[0] if paper.get('published_date') else '未知',
                    "citations": paper.get('citation_count', 0)
                })
            return papers
        except Exception as e:
            self.logger.log_agent_error("Search", "_search_papers", e)
            print(f"    ⚠️ 论文搜索失败: {e}")
            return []
    
    def _search_repositories(self, query):
        """搜索开源项目"""
        # 这里可以使用browser工具搜索GitHub
        # 简化版本返回空列表
        return []
    
    @log_agent_method("name")
    def _summarize_results(self, direction, papers, repos):
        """使用LLM总结搜索结果"""
        self.logger.log_step("Search", "_summarize_results", f"总结方向: {direction}")
        
        prompt = f"""请总结以下关于"{direction}"的搜索结果：

论文列表：
"""
        for i, paper in enumerate(papers[:5], 1):
            prompt += f"{i}. {paper['title']} ({paper['year']})\n"
            prompt += f"   摘要: {paper['abstract'][:200]}...\n\n"
        
        prompt += """

请提供：
1. 核心方法概述
2. 关键技术点
3. 与本项目的关联性
4. 可借鉴的实现思路
5. 该方法的优势和局限性

输出格式：Markdown"""
        
        start_time = time.time()
        summary = self.llm.generate(prompt=prompt)
        duration_ms = (time.time() - start_time) * 1000
        
        self.logger.log_llm_call("Search", len(prompt), len(summary), duration_ms)
        return summary
    
    def _generate_markdown_report(self, results):
        """生成Markdown格式研究报告"""
        markdown = "# 文献研究报告\n\n"
        markdown += f"生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        for result in results:
            direction = result.get('direction_name', '未知方向')
            markdown += f"## {direction}\n\n"
            
            if result.get("from_cache"):
                markdown += "*(来自项目知识库复用)*\n\n"
            
            # 添加选择理由
            if result.get('rationale'):
                markdown += f"**选择理由**: {result['rationale']}\n\n"
            
            # 添加关键词
            keywords = result.get('keywords', [])
            if keywords:
                markdown += f"**关键词**: {', '.join(keywords)}\n\n"
            
            # 添加研究总结
            if result.get('summary'):
                markdown += "### 研究总结\n\n"
                markdown += result['summary'] + "\n\n"
            
            # 添加论文列表
            papers = result.get('papers', [])
            if papers:
                markdown += "### 相关论文\n\n"
                for paper in papers:
                    markdown += f"**{paper['title']}** ({paper['year']})\n"
                    markdown += f"- 作者: {', '.join(paper['authors'][:3])}\n"
                    markdown += f"- 摘要: {paper['abstract'][:300]}...\n"
                    markdown += f"- 链接: {paper['url']}\n\n"
            
            markdown += "---\n\n"
        
        return markdown
    
    @log_agent_method("name")
    def report_best_methods(self, search_results):
        """分析所有搜索结果，向Supervisor汇报最有价值的方法"""
        self.logger.log_step("Search", "report_best_methods", "分析最有价值的方法")
        
        if not search_results:
            return {
                "best_methods": [],
                "recommendation": "无搜索结果，建议放宽搜索条件或调整方向",
                "confidence": "low"
            }
        
        prompt = f"""你作为搜索Agent，已经完成了文献检索。现在需要向主管Agent汇报最有价值的方法。

搜索结果摘要:
"""
        for i, result in enumerate(search_results, 1):
            prompt += f"\n方向{i}: {result.get('direction_name', '未知方向')}\n"
            prompt += f"关键词: {', '.join(result.get('keywords', []))}\n"
            prompt += f"论文数量: {len(result.get('papers', []))}\n"
            prompt += f"研究总结: {result.get('summary', '')[:500]}...\n"
        
        prompt += """

请从以上方向中，选出最有价值的1-2个方法，并向主管Agent汇报：
1. 最推荐的方法名称和方向
2. 推荐理由（基于论文质量、方法成熟度、与项目关联性）
3. 预期效果（对精度/性能的提升潜力）
4. 实施风险或注意事项
5. 信心等级（high/medium/low）

输出JSON格式：
{
  "best_methods": [
    {
      "direction_name": "方向名称",
      "method_name": "具体方法名称",
      "recommendation_reason": "推荐理由",
      "expected_effect": "预期效果",
      "risks": "风险或注意事项"
    }
  ],
  "recommendation": "总体建议",
  "confidence": "high/medium/low"
}"""
        
        start_time = time.time()
        result = self.llm.generate(prompt=prompt)
        duration_ms = (time.time() - start_time) * 1000
        self.logger.log_llm_call("Search", len(prompt), len(result), duration_ms)
        
        import json
        import re
        try:
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            self.logger.log_agent_error("Search", "report_best_methods", e)
        
        # 默认返回
        return {
            "best_methods": [
                {
                    "direction_name": search_results[0].get("direction_name", "未知方向"),
                    "method_name": "待进一步分析",
                    "recommendation_reason": "基于初步搜索结果",
                    "expected_effect": "可能有效",
                    "risks": "需实验验证"
                }
            ],
            "recommendation": "建议优先尝试第一个方向",
            "confidence": "medium"
        }
    
    def save_search_report(self, report, output_dir="./data/outputs"):
        """保存搜索报告到本地文件"""
        import os
        from datetime import datetime
        
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"search_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"  💾 报告已保存: {filepath}")
        return filepath
