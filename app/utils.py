from typing import List, Dict

def format_task_list(tasks: List[Dict]) -> str:
    if not tasks:
        return 'No tasks.'
    return '\n'.join([f"- {t['description']} ({t['property']})" + (f" [cost: {t['cost']}]" if t.get('cost') else '') for t in tasks])

def format_summary(summary: Dict) -> str:
    lines = [f"Completed this week: {summary['count']} tasks, total cost: {summary['total_cost']}"]
    for t in summary.get('tasks', []):
        lines.append(f"- {t['description']} ({t['property']}) [cost: {t['cost']}] on {t['completed_at']}")
    return '\n'.join(lines) 