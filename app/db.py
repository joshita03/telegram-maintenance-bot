import os
from supabase import create_client, Client
from typing import Optional, List, Dict, Any

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

TASKS_TABLE = 'maintenance_logs'

def add_task(task: Dict[str, Any]) -> Dict:
    if not supabase:
        raise Exception('Supabase not initialized')
    return supabase.table(TASKS_TABLE).insert(task).execute()

def get_tasks(status: Optional[str] = None, property: Optional[str] = None) -> List[Dict]:
    if not supabase:
        raise Exception('Supabase not initialized')
    query = supabase.table(TASKS_TABLE).select('*')
    if status:
        query = query.eq('status', status)
    if property:
        query = query.eq('property', property)
    return query.order('created_at', desc=False).execute().data

def complete_task(description: str, property: str) -> Dict:
    if not supabase:
        raise Exception('Supabase not initialized')
    return supabase.table(TASKS_TABLE).update({'status': 'completed', 'completed_at': 'now()'}).match({'description': description, 'property': property, 'status': 'pending'}).execute()

def get_summary(start_date: str, end_date: str) -> Dict:
    if not supabase:
        raise Exception('Supabase not initialized')
    # Get completed tasks in date range
    data = supabase.table(TASKS_TABLE).select('*').eq('status', 'completed').gte('completed_at', start_date).lte('completed_at', end_date).execute().data
    total_cost = sum([float(task['cost'] or 0) for task in data])
    return {'tasks': data, 'total_cost': total_cost, 'count': len(data)}

def check_duplicate(description: str, property: str) -> bool:
    if not supabase:
        raise Exception('Supabase not initialized')
    data = supabase.table(TASKS_TABLE).select('id').eq('description', description).eq('property', property).eq('status', 'pending').execute().data
    return len(data) > 0 