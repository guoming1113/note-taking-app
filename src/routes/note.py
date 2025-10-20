from flask import Blueprint, jsonify, request
from src.models.note import Note, db
from src.llm import translate_note, process_user_notes
import json
from datetime import datetime
from datetime import date as date_cls, timedelta
import re
from src.utils.date_utils import normalize_date, normalize_time, extract_date_from_text, extract_time_from_text

note_bp = Blueprint('note', __name__)

@note_bp.route('/notes', methods=['GET'])
def get_notes():
    """Get all notes, ordered by most recently updated"""
    notes = Note.query.order_by(Note.updated_at.desc()).all()
    return jsonify([note.to_dict() for note in notes])

@note_bp.route('/notes', methods=['POST'])
def create_note():
    """Create a new note"""
    try:
        data = request.json
        if not data or 'title' not in data or 'content' not in data:
            return jsonify({'error': 'Title and content are required'}), 400

        note = Note(title=data['title'], content=data['content'])
        # optional fields
        tags = data.get('tags')
        if tags:
            # accept list or comma-separated string
            if isinstance(tags, list):
                note.tags = json.dumps(tags)
            else:
                note.tags = json.dumps([t.strip() for t in str(tags).split(',') if t.strip()])

        event_date = data.get('event_date')
        if event_date:
            try:
                note.event_date = datetime.fromisoformat(event_date).date()
            except Exception:
                pass

        start_time = data.get('start_time')
        if start_time:
            try:
                note.start_time = datetime.strptime(start_time, '%H:%M').time()
            except Exception:
                pass
        db.session.add(note)
        db.session.commit()
        return jsonify(note.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@note_bp.route('/notes/<int:note_id>', methods=['GET'])
def get_note(note_id):
    """Get a specific note by ID"""
    note = Note.query.get_or_404(note_id)
    return jsonify(note.to_dict())

@note_bp.route('/notes/<int:note_id>', methods=['PUT'])
def update_note(note_id):
    """Update a specific note"""
    try:
        note = Note.query.get_or_404(note_id)
        data = request.json
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        note.title = data.get('title', note.title)
        note.content = data.get('content', note.content)
        # optional fields
        tags = data.get('tags')
        if tags is not None:
            if isinstance(tags, list):
                note.tags = json.dumps(tags)
            else:
                note.tags = json.dumps([t.strip() for t in str(tags).split(',') if t.strip()])

        event_date = data.get('event_date')
        if event_date is not None:
            try:
                note.event_date = datetime.fromisoformat(event_date).date() if event_date else None
            except Exception:
                pass

        start_time = data.get('start_time')
        if start_time is not None:
            try:
                note.start_time = datetime.strptime(start_time, '%H:%M').time() if start_time else None
            except Exception:
                pass
        db.session.commit()
        return jsonify(note.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@note_bp.route('/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    """Delete a specific note"""
    try:
        note = Note.query.get_or_404(note_id)
        db.session.delete(note)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@note_bp.route('/notes/search', methods=['GET'])
def search_notes():
    """Search notes by title or content"""
    query = request.args.get('q', '')
    if not query:
        return jsonify([])
    
    notes = Note.query.filter(
        (Note.title.contains(query)) | (Note.content.contains(query))
    ).order_by(Note.updated_at.desc()).all()
    
    return jsonify([note.to_dict() for note in notes])

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
