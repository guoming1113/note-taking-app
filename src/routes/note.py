import os
from flask import Blueprint, jsonify, request
from src.models.note import Note, db
from src.llm import translate_note, process_user_notes
import json
from datetime import datetime
from datetime import date as date_cls, timedelta
import re
from src.utils.date_utils import normalize_date, normalize_time, extract_date_from_text, extract_time_from_text
from supabase import create_client, Client

note_bp = Blueprint('note', __name__)

# 初始化Supabase客户端（新增代码）
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("请在.env文件中配置SUPABASE_URL和SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)  # 创建Supabase客户端实例

# 获取所有笔记（使用 Supabase 客户端）
@note_bp.route('/notes', methods=['GET'])
def get_notes():
    try:
        # 调用 Supabase 表查询
        response = supabase.table('note').select('*').order('updated_at', desc=True).execute()
        # 处理响应数据
        if response.data:
            return jsonify(response.data)
        return jsonify([])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 替换原 SQLAlchemy 插入逻辑
@note_bp.route('/notes', methods=['POST'])
def create_note():
    try:
        data = request.json
        if not data or 'title' not in data or 'content' not in data:
            return jsonify({'error': 'Title and content are required'}), 400

        # 处理标签（转为JSON字符串，与原逻辑一致）
        tags = data.get('tags', [])
        # 确保 tags 是数组（处理前端可能传入的字符串情况）
        if not isinstance(tags, list):
            tags = [t.strip() for t in str(tags).split(',') if t.strip()]  # 字符串转数组

        # 构造插入数据
        note_data = {
            'title': data['title'],
            'content': data['content'],
            'tags': tags,
            'event_date': data.get('event_date'),
            'start_time': data.get('start_time'),
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }

        response = supabase.table('note').insert(note_data).execute()
        return jsonify(response.data[0]), 201  # 返回创建的笔记
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 替换原 SQLAlchemy 查询
@note_bp.route('/notes/<int:note_id>', methods=['GET'])
def get_note(note_id):
    try:
        response = supabase.table('note').select('*').eq('id', note_id).single().execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({'error': 'Note not found'}), 404

# 替换原 SQLAlchemy 更新逻辑
@note_bp.route('/notes/<int:note_id>', methods=['PUT'])
def update_note(note_id):
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # 处理标签
        tags = data.get('tags')
        if tags is not None and not isinstance(tags, list):
            tags = [t.strip() for t in str(tags).split(',') if t.strip()]  # 确保是数组

        # 构造更新数据
        update_data = {
            'title': data.get('title'),
            'content': data.get('content'),
            'tags': tags,
            'event_date': data.get('event_date'),
            'start_time': data.get('start_time'),
            'updated_at': datetime.utcnow().isoformat()
        }
        # 过滤空值（不更新未提供的字段）
        update_data = {k: v for k, v in update_data.items() if v is not None}

        response = supabase.table('note').update(update_data).eq('id', note_id).execute()
        return jsonify(response.data[0])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
# 替换原 SQLAlchemy 删除逻辑
@note_bp.route('/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    try:
        supabase.table('note').delete().eq('id', note_id).execute()
        return '', 204
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 替换原 SQLAlchemy 搜索逻辑
@note_bp.route('/notes/search', methods=['GET'])
def search_notes():
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    try:
        # 使用 ilike 实现模糊搜索
        response = supabase.table('note').select('*').ilike('title', f'%{query}%').or_(f'content.ilike.%{query}%').order('updated_at', desc=True).execute()
        return jsonify(response.data if response.data else [])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@note_bp.route('/notes/translate', methods = ['POST'])
def translate_note_api():
    data = request.get_json() or {}
    note_content = data.get('content')
    note_title = data.get('title')
    target_lang = data.get('target_language', 'Chinese')

    if not note_content and not note_title:
        return jsonify({"error": "Note title or content is required"}), 400

    translated_content = translate_note(note_content, target_lang) if note_content else ''
    translated_title = translate_note(note_title, target_lang) if note_title else ''

    return jsonify({
        "translated_title": translated_title,
        "translated_content": translated_content
    })


@note_bp.route('/notes/generate', methods=['POST'])
def generate_note_api():
    """Generate a note from a natural language prompt"""
    try:
        data = request.get_json() or {}
        prompt = data.get('prompt')
        target_lang = data.get('target_language', 'English')
        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400

        # process_user_notes returns a dict with Title, Notes, Tags, Date, Time fields
        result = process_user_notes(target_lang, prompt)
        title = result.get('Title') or 'Generated Note'
        content = result.get('Notes') or ''
        tags = result.get('Tags') or []
        date = result.get('Date')
        time = result.get('Time')

        # If prompt contains relative terms, prefer extracting date/time from prompt
        prompt_date = extract_date_from_text(prompt)
        prompt_time = extract_time_from_text(prompt)

        if prompt_date:
            normalized_date = prompt_date
        else:
            normalized_date = normalize_date(date)

        if prompt_time:
            normalized_time = prompt_time
        else:
            normalized_time = normalize_time(time)

        return jsonify({'title': title, 'content': content, 'tags': tags, 'date': normalized_date, 'time': normalized_time})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
