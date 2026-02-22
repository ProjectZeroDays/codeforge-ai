"""
Code Quality Metrics Service
Analyzes code quality including complexity, duplication, and security
"""

import os
import re
import ast
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict
import hashlib

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)


class CodeAnalyzer:
    """Static code analyzer for various metrics"""
    
    # Language detection by extension
    LANGUAGE_MAP = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
        ".c": "c",
        ".cpp": "cpp",
        ".cs": "csharp",
        ".swift": "swift",
        ".kt": "kotlin"
    }
    
    # Security patterns to check
    SECURITY_PATTERNS = {
        "python": [
            (r"eval\s*\(", "Potential code injection via eval()"),
            (r"exec\s*\(", "Potential code injection via exec()"),
            (r"subprocess\.call\s*\(.*shell\s*=\s*True", "Shell injection risk"),
            (r"os\.system\s*\(", "Shell command execution risk"),
            (r"pickle\.loads?\s*\(", "Insecure deserialization"),
            (r"yaml\.load\s*\([^,]+\)(?!.*Loader)", "Insecure YAML loading"),
            (r"password\s*=\s*['\"]", "Hardcoded password"),
            (r"api_key\s*=\s*['\"]", "Hardcoded API key"),
            (r"secret\s*=\s*['\"]", "Hardcoded secret"),
        ],
        "javascript": [
            (r"eval\s*\(", "Potential code injection via eval()"),
            (r"innerHTML\s*=", "XSS risk via innerHTML"),
            (r"document\.write\s*\(", "XSS risk via document.write"),
            (r"password\s*[=:]\s*['\"]", "Hardcoded password"),
            (r"api_key\s*[=:]\s*['\"]", "Hardcoded API key"),
            (r"new\s+Function\s*\(", "Dynamic function creation risk"),
        ],
        "typescript": [
            (r"eval\s*\(", "Potential code injection via eval()"),
            (r"innerHTML\s*=", "XSS risk via innerHTML"),
            (r"password\s*[=:]\s*['\"]", "Hardcoded password"),
            (r"api_key\s*[=:]\s*['\"]", "Hardcoded API key"),
        ]
    }
    
    def analyze_file(self, path: str, content: str, language: str) -> Dict:
        """Analyze a single file"""
        lines = content.split('\n')
        
        # Basic metrics
        total_lines = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = self._count_comment_lines(lines, language)
        code_lines = total_lines - blank_lines - comment_lines
        
        # Complexity
        complexity = self._calculate_complexity(content, language)
        
        # Security issues
        security_issues = self._check_security(content, language, path)
        
        return {
            "path": path,
            "language": language,
            "metrics": {
                "total_lines": total_lines,
                "code_lines": code_lines,
                "comment_lines": comment_lines,
                "blank_lines": blank_lines,
                "cyclomatic_complexity": complexity
            },
            "security_issues": security_issues
        }
    
    def _count_comment_lines(self, lines: List[str], language: str) -> int:
        """Count comment lines based on language"""
        count = 0
        in_block_comment = False
        
        for line in lines:
            stripped = line.strip()
            
            if language in ["python"]:
                if stripped.startswith('#'):
                    count += 1
                elif '"""' in stripped or "'''" in stripped:
                    # Simple docstring detection
                    count += 1
            elif language in ["javascript", "typescript", "java", "go", "c", "cpp", "csharp"]:
                if stripped.startswith('//'):
                    count += 1
                elif '/*' in stripped:
                    in_block_comment = True
                    count += 1
                elif '*/' in stripped:
                    in_block_comment = False
                    count += 1
                elif in_block_comment:
                    count += 1
        
        return count
    
    def _calculate_complexity(self, content: str, language: str) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1  # Base complexity
        
        # Decision point patterns by language
        if language == "python":
            patterns = [
                r'\bif\b', r'\belif\b', r'\bfor\b', r'\bwhile\b',
                r'\band\b', r'\bor\b', r'\bexcept\b', r'\bwith\b'
            ]
        elif language in ["javascript", "typescript"]:
            patterns = [
                r'\bif\b', r'\belse\s+if\b', r'\bfor\b', r'\bwhile\b',
                r'\bcase\b', r'\bcatch\b', r'\?\?', r'\?\.',
                r'&&', r'\|\|', r'\?(?!:)'
            ]
        elif language in ["java", "csharp", "go"]:
            patterns = [
                r'\bif\b', r'\belse\s+if\b', r'\bfor\b', r'\bwhile\b',
                r'\bcase\b', r'\bcatch\b', r'&&', r'\|\|'
            ]
        else:
            patterns = [r'\bif\b', r'\bfor\b', r'\bwhile\b']
        
        for pattern in patterns:
            complexity += len(re.findall(pattern, content))
        
        return complexity
    
    def _check_security(self, content: str, language: str, path: str) -> List[Dict]:
        """Check for security vulnerabilities"""
        issues = []
        patterns = self.SECURITY_PATTERNS.get(language, [])
        
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, message in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append({
                        "file": path,
                        "line": i,
                        "severity": "warning",
                        "message": message,
                        "code_snippet": line.strip()[:100]
                    })
        
        return issues
    
    def detect_duplicates(self, files: List[Dict]) -> List[Dict]:
        """Detect code duplication across files"""
        MIN_DUPLICATE_LINES = 5
        duplicates = []
        
        # Create blocks of code for comparison
        code_blocks = defaultdict(list)
        
        for file_info in files:
            content = file_info.get("content", "")
            path = file_info.get("path", "")
            lines = content.split('\n')
            
            # Create overlapping blocks
            for i in range(len(lines) - MIN_DUPLICATE_LINES + 1):
                block = '\n'.join(lines[i:i + MIN_DUPLICATE_LINES])
                # Skip blocks that are mostly whitespace or comments
                if len(block.strip()) > 50:
                    block_hash = hashlib.md5(block.encode()).hexdigest()
                    code_blocks[block_hash].append({
                        "file": path,
                        "start_line": i + 1,
                        "end_line": i + MIN_DUPLICATE_LINES,
                        "content": block
                    })
        
        # Find duplicates
        for block_hash, locations in code_blocks.items():
            if len(locations) > 1:
                duplicates.append({
                    "hash": block_hash,
                    "locations": locations,
                    "lines": MIN_DUPLICATE_LINES
                })
        
        return duplicates


class CodeQualityService:
    """Service for code quality analysis"""
    
    def __init__(self):
        self.analyzer = CodeAnalyzer()
    
    async def analyze_project(
        self,
        db: AsyncSession,
        project_id: str
    ) -> Dict:
        """Perform full code quality analysis on a project"""
        from app.database.models import Project, File
        from app.database.models_extended import CodeQualityMetrics, CodeQualityHistory
        
        # Get project files
        result = await db.execute(
            select(File).where(File.project_id == project_id)
        )
        files = result.scalars().all()
        
        if not files:
            raise ValueError(f"No files found for project {project_id}")
        
        # Analyze each file
        total_metrics = {
            "total_files": 0,
            "total_lines": 0,
            "code_lines": 0,
            "comment_lines": 0,
            "blank_lines": 0
        }
        
        language_breakdown = defaultdict(int)
        complexity_by_file = {}
        all_security_issues = []
        file_data = []
        
        for file in files:
            language = file.language or self._detect_language(file.path)
            if not language or language in ["text", "unknown"]:
                continue
            
            analysis = self.analyzer.analyze_file(
                file.path,
                file.content or "",
                language
            )
            
            metrics = analysis["metrics"]
            total_metrics["total_files"] += 1
            total_metrics["total_lines"] += metrics["total_lines"]
            total_metrics["code_lines"] += metrics["code_lines"]
            total_metrics["comment_lines"] += metrics["comment_lines"]
            total_metrics["blank_lines"] += metrics["blank_lines"]
            
            language_breakdown[language] += metrics["code_lines"]
            complexity_by_file[file.path] = metrics["cyclomatic_complexity"]
            all_security_issues.extend(analysis["security_issues"])
            
            file_data.append({
                "path": file.path,
                "content": file.content or "",
                "language": language
            })
        
        # Calculate averages and aggregates
        avg_complexity = (
            sum(complexity_by_file.values()) / len(complexity_by_file)
            if complexity_by_file else 0
        )
        max_complexity = max(complexity_by_file.values()) if complexity_by_file else 0
        
        # Detect duplicates
        duplicates = self.analyzer.detect_duplicates(file_data)
        duplication_percentage = self._calculate_duplication_percentage(duplicates, total_metrics["code_lines"])
        
        # Calculate scores
        maintainability_index = self._calculate_maintainability_index(
            total_metrics, avg_complexity
        )
        security_score = self._calculate_security_score(all_security_issues, total_metrics["total_files"])
        overall_score = self._calculate_overall_score(
            maintainability_index, security_score, duplication_percentage
        )
        grade = self._score_to_grade(overall_score)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            avg_complexity, max_complexity, duplication_percentage,
            all_security_issues, complexity_by_file
        )
        
        # Technical debt estimation (rough estimate)
        technical_debt_minutes = self._estimate_technical_debt(
            all_security_issues, duplicates, avg_complexity
        )
        
        # Save metrics
        metrics_record = CodeQualityMetrics(
            project_id=project_id,
            total_files=total_metrics["total_files"],
            total_lines=total_metrics["total_lines"],
            code_lines=total_metrics["code_lines"],
            comment_lines=total_metrics["comment_lines"],
            blank_lines=total_metrics["blank_lines"],
            language_breakdown=dict(language_breakdown),
            avg_cyclomatic_complexity=round(avg_complexity, 2),
            max_cyclomatic_complexity=max_complexity,
            complexity_by_file=complexity_by_file,
            maintainability_index=round(maintainability_index, 2),
            technical_debt_minutes=technical_debt_minutes,
            duplication_percentage=round(duplication_percentage, 2),
            duplicated_blocks=[{
                "hash": d["hash"],
                "count": len(d["locations"]),
                "lines": d["lines"]
            } for d in duplicates[:10]],  # Top 10
            security_issues=all_security_issues[:50],  # Top 50
            security_score=security_score,
            overall_score=overall_score,
            grade=grade,
            recommendations=recommendations
        )
        
        db.add(metrics_record)
        
        # Save history
        history_record = CodeQualityHistory(
            project_id=project_id,
            overall_score=overall_score,
            maintainability_index=round(maintainability_index, 2),
            security_score=security_score,
            total_lines=total_metrics["total_lines"]
        )
        db.add(history_record)
        
        await db.commit()
        
        return {
            "project_id": project_id,
            "analyzed_at": datetime.utcnow().isoformat(),
            "summary": {
                "total_files": total_metrics["total_files"],
                "total_lines": total_metrics["total_lines"],
                "code_lines": total_metrics["code_lines"],
                "languages": dict(language_breakdown),
                "overall_score": overall_score,
                "grade": grade
            },
            "complexity": {
                "average": round(avg_complexity, 2),
                "max": max_complexity,
                "high_complexity_files": [
                    path for path, c in complexity_by_file.items()
                    if c > 10
                ]
            },
            "duplication": {
                "percentage": round(duplication_percentage, 2),
                "blocks_found": len(duplicates)
            },
            "security": {
                "score": security_score,
                "issues_found": len(all_security_issues),
                "critical_issues": [i for i in all_security_issues if "password" in i.get("message", "").lower() or "key" in i.get("message", "").lower()]
            },
            "maintainability": {
                "index": round(maintainability_index, 2),
                "technical_debt_minutes": technical_debt_minutes
            },
            "recommendations": recommendations
        }
    
    async def get_metrics(
        self,
        db: AsyncSession,
        project_id: str
    ) -> Optional[Dict]:
        """Get the latest metrics for a project"""
        from app.database.models_extended import CodeQualityMetrics
        
        result = await db.execute(
            select(CodeQualityMetrics)
            .where(CodeQualityMetrics.project_id == project_id)
            .order_by(CodeQualityMetrics.analyzed_at.desc())
            .limit(1)
        )
        metrics = result.scalar_one_or_none()
        
        if not metrics:
            return None
        
        return {
            "project_id": project_id,
            "analyzed_at": metrics.analyzed_at.isoformat() if metrics.analyzed_at else None,
            "total_files": metrics.total_files,
            "total_lines": metrics.total_lines,
            "code_lines": metrics.code_lines,
            "language_breakdown": metrics.language_breakdown,
            "avg_complexity": metrics.avg_cyclomatic_complexity,
            "max_complexity": metrics.max_cyclomatic_complexity,
            "maintainability_index": metrics.maintainability_index,
            "duplication_percentage": metrics.duplication_percentage,
            "security_score": metrics.security_score,
            "overall_score": metrics.overall_score,
            "grade": metrics.grade,
            "recommendations": metrics.recommendations
        }
    
    async def get_metrics_history(
        self,
        db: AsyncSession,
        project_id: str,
        limit: int = 30
    ) -> List[Dict]:
        """Get historical metrics for a project"""
        from app.database.models_extended import CodeQualityHistory
        
        result = await db.execute(
            select(CodeQualityHistory)
            .where(CodeQualityHistory.project_id == project_id)
            .order_by(CodeQualityHistory.recorded_at.desc())
            .limit(limit)
        )
        history = result.scalars().all()
        
        return [
            {
                "recorded_at": h.recorded_at.isoformat() if h.recorded_at else None,
                "overall_score": h.overall_score,
                "maintainability_index": h.maintainability_index,
                "security_score": h.security_score,
                "total_lines": h.total_lines
            }
            for h in reversed(history)
        ]
    
    async def generate_report(
        self,
        db: AsyncSession,
        project_id: str,
        format: str = "markdown"
    ) -> str:
        """Generate a quality report"""
        metrics = await self.get_metrics(db, project_id)
        
        if not metrics:
            return "No metrics available. Run analysis first."
        
        if format == "markdown":
            return self._generate_markdown_report(metrics)
        elif format == "json":
            import json
            return json.dumps(metrics, indent=2)
        else:
            return str(metrics)
    
    def _detect_language(self, path: str) -> str:
        """Detect language from file extension"""
        _, ext = os.path.splitext(path.lower())
        return self.analyzer.LANGUAGE_MAP.get(ext, "unknown")
    
    def _calculate_duplication_percentage(
        self,
        duplicates: List[Dict],
        total_lines: int
    ) -> float:
        """Calculate percentage of duplicated code"""
        if total_lines == 0:
            return 0.0
        
        duplicated_lines = sum(
            d["lines"] * (len(d["locations"]) - 1)
            for d in duplicates
        )
        return (duplicated_lines / total_lines) * 100
    
    def _calculate_maintainability_index(
        self,
        metrics: Dict,
        avg_complexity: float
    ) -> float:
        """Calculate maintainability index (0-100)"""
        # Based on Microsoft's formula
        volume = metrics["code_lines"] * 0.1 if metrics["code_lines"] > 0 else 1
        
        mi = max(0, min(100,
            171 - 5.2 * (volume ** 0.5) - 0.23 * avg_complexity - 16.2 * (volume ** 0.25)
        ))
        
        # Normalize to 0-100
        return (mi / 171) * 100
    
    def _calculate_security_score(
        self,
        issues: List[Dict],
        file_count: int
    ) -> int:
        """Calculate security score (0-100)"""
        if file_count == 0:
            return 100
        
        # Weighted by severity
        issue_weight = len(issues) * 5  # 5 points per issue
        critical_weight = sum(10 for i in issues if "password" in i.get("message", "").lower())
        
        score = 100 - min(100, issue_weight + critical_weight)
        return max(0, score)
    
    def _calculate_overall_score(
        self,
        maintainability: float,
        security: int,
        duplication: float
    ) -> int:
        """Calculate overall quality score"""
        duplication_penalty = min(30, duplication * 1.5)
        
        score = (
            maintainability * 0.4 +
            security * 0.4 +
            (100 - duplication_penalty) * 0.2
        )
        
        return int(min(100, max(0, score)))
    
    def _score_to_grade(self, score: int) -> str:
        """Convert score to letter grade"""
        if score >= 95:
            return "A+"
        elif score >= 90:
            return "A"
        elif score >= 85:
            return "B+"
        elif score >= 80:
            return "B"
        elif score >= 75:
            return "C+"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def _generate_recommendations(
        self,
        avg_complexity: float,
        max_complexity: int,
        duplication: float,
        security_issues: List[Dict],
        complexity_by_file: Dict
    ) -> List[Dict]:
        """Generate improvement recommendations"""
        recommendations = []
        
        if avg_complexity > 8:
            recommendations.append({
                "category": "complexity",
                "priority": "high",
                "message": "Consider refactoring complex functions. Average complexity is high.",
                "action": "Break down functions with complexity > 10 into smaller functions"
            })
        
        if max_complexity > 15:
            high_complexity_files = [
                path for path, c in complexity_by_file.items()
                if c > 15
            ]
            recommendations.append({
                "category": "complexity",
                "priority": "high",
                "message": f"Files with very high complexity: {', '.join(high_complexity_files[:3])}",
                "action": "These files should be prioritized for refactoring"
            })
        
        if duplication > 10:
            recommendations.append({
                "category": "duplication",
                "priority": "medium",
                "message": f"Code duplication is at {duplication:.1f}%",
                "action": "Extract common code into reusable functions or modules"
            })
        
        if security_issues:
            critical = [i for i in security_issues if "password" in i.get("message", "").lower() or "key" in i.get("message", "").lower()]
            if critical:
                recommendations.append({
                    "category": "security",
                    "priority": "critical",
                    "message": f"Found {len(critical)} potential hardcoded secrets",
                    "action": "Move secrets to environment variables or a secrets manager"
                })
            
            if len(security_issues) > len(critical):
                recommendations.append({
                    "category": "security",
                    "priority": "high",
                    "message": f"Found {len(security_issues) - len(critical)} other security concerns",
                    "action": "Review and address security issues in the report"
                })
        
        return recommendations
    
    def _estimate_technical_debt(
        self,
        security_issues: List[Dict],
        duplicates: List[Dict],
        avg_complexity: float
    ) -> int:
        """Estimate technical debt in minutes"""
        debt = 0
        
        # Security issues: ~30 min each
        debt += len(security_issues) * 30
        
        # Duplicates: ~15 min each to refactor
        debt += len(duplicates) * 15
        
        # High complexity: ~60 min per high complexity function
        if avg_complexity > 10:
            debt += int((avg_complexity - 10) * 60)
        
        return debt
    
    def _generate_markdown_report(self, metrics: Dict) -> str:
        """Generate a markdown quality report"""
        return f"""# Code Quality Report

## Summary

| Metric | Value |
|--------|-------|
| Overall Score | **{metrics['overall_score']}** ({metrics['grade']}) |
| Total Files | {metrics['total_files']} |
| Total Lines | {metrics['total_lines']} |
| Code Lines | {metrics['code_lines']} |

## Languages

| Language | Lines |
|----------|-------|
{chr(10).join(f"| {lang} | {lines} |" for lang, lines in (metrics.get('language_breakdown') or {}).items())}

## Complexity

- Average Complexity: {metrics['avg_complexity']}
- Max Complexity: {metrics['max_complexity']}

## Security

- Security Score: {metrics['security_score']}/100

## Maintainability

- Maintainability Index: {metrics['maintainability_index']}
- Code Duplication: {metrics['duplication_percentage']}%

## Recommendations

{chr(10).join(f"- **[{r['priority'].upper()}]** {r['message']}" for r in (metrics.get('recommendations') or []))}

---
*Report generated by CodeForge AI*
"""
