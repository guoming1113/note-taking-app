import re
from datetime import datetime, date as date_cls, timedelta


def _strip_edge_punct(s: str) -> str:
    if s is None:
        return ''
    # strip whitespace and common punctuation from start/end
    return s.strip().strip(" \t\n\r,.;:!，。！？'")


def normalize_date(date_str: str):
    """Normalize a date string into ISO YYYY-MM-DD if possible.
    Keeps original string if no parseable date is found.
    Handles relative terms like 'tomorrow', 'yesterday', Chinese '明天/昨天', 'in 2 days', weekdays and some common numeric formats.
    """
    if not date_str:
        return None
    ds = str(date_str)
    if not ds.strip():
        return None
    s = _strip_edge_punct(ds).lower()
    today = date_cls.today()

    # direct ISO-like formats (allow spaces around hyphens)
    iso_candidate = re.sub(r"\s+", "", ds)
    try:
        parsed = datetime.fromisoformat(iso_candidate)
        return parsed.date().isoformat()
    except Exception:
        pass

    # common keywords (english and chinese)
    if s in ('tomorrow', 'tmr', 'tomorow', '明天'):
        return (today + timedelta(days=1)).isoformat()
    if s in ('yesterday', 'yday', '昨天'):
        return (today - timedelta(days=1)).isoformat()
    if s in ('today', 'tonight', '今天'):
        return today.isoformat()

    # phrases like 'in 2 days'
    m = re.search(r'in\s+(\d+)\s+day', s)
    if m:
        days = int(m.group(1))
        return (today + timedelta(days=days)).isoformat()

    # 'next monday' or just weekday name
    weekdays = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6,
                '周一': 0, '周二': 1, '周三': 2, '周四': 3, '周五': 4, '周六': 5, '周日': 6, '星期一': 0, '星期二': 1,
                '星期三': 2, '星期四': 3, '星期五': 4, '星期六': 5, '星期日': 6}
    m = re.search(r'next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)', s)
    if m:
        wd = weekdays[m.group(1)]
        days_ahead = (wd - today.weekday() + 7) % 7
        days_ahead = days_ahead if days_ahead != 0 else 7
        return (today + timedelta(days=days_ahead)).isoformat()

    # plain weekday like 'monday' - pick nearest upcoming (including today)
    m = re.match(r'^(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$', s)
    if m:
        wd = weekdays[m.group(1)]
        days_ahead = (wd - today.weekday() + 7) % 7
        if days_ahead == 0:
            return today.isoformat()
        return (today + timedelta(days=days_ahead)).isoformat()

    # chinese weekday names
    for name in ('星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日', '星期天', '周一', '周二', '周三', '周四', '周五', '周六', '周日'):
        if name in s:
            wd = weekdays.get(name.replace('星期', '星期').replace('周', '周')) if name in weekdays else None
            # fallback: match by mapping
            for k, v in weekdays.items():
                if k in ('星期一','星期二','星期三','星期四','星期五','星期六','星期日','周一','周二','周三','周四','周五','周六','周日') and k in s:
                    wd = v
                    break
            if wd is not None:
                days_ahead = (wd - today.weekday() + 7) % 7
                return (today + timedelta(days=days_ahead)).isoformat()

    # 'on 20 Oct' or numeric date patterns
    m = re.search(r'on\s+(\d{1,2})(?:st|nd|rd|th)?\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)', s)
    if m:
        day = int(m.group(1))
        mon_str = m.group(2)
        mon_map = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'sept': 9,
                   'oct': 10, 'nov': 11, 'dec': 12}
        mon = mon_map.get(mon_str, None)
        if mon:
            year = today.year
            try:
                d = date_cls(year, mon, day)
                if d < today:
                    d = date_cls(year + 1, mon, day)
                return d.isoformat()
            except Exception:
                pass

    # try common numeric date formats
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d'):
        try:
            parsed = datetime.strptime(s, fmt)
            return parsed.date().isoformat()
        except Exception:
            pass

    # fallback: return original (trimmed) string so frontend can handle free-form
    return _strip_edge_punct(ds)


def normalize_time(time_str: str):
    if not time_str:
        return None
    ts = str(time_str)
    if not ts.strip():
        return None
    s = _strip_edge_punct(ts).lower().replace('.', '')
    # if already HH:MM
    m = re.match(r'^(\d{1,2}):(\d{2})$', s)
    if m:
        hh = int(m.group(1))
        mm = int(m.group(2))
        return f"{hh:02d}:{mm:02d}"
    # am/pm like '5pm' or '5:30pm'
    m = re.match(r'^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$', s)
    if m:
        hh = int(m.group(1))
        mm = int(m.group(2) or 0)
        ampm = m.group(3)
        if ampm == 'pm' and hh != 12:
            hh += 12
        if ampm == 'am' and hh == 12:
            hh = 0
        return f"{hh:02d}:{mm:02d}"
    # 24h without colon like '1730'
    m = re.match(r'^(\d{2})(\d{2})$', s)
    if m:
        return f"{int(m.group(1)):02d}:{int(m.group(2)):02d}"
    return _strip_edge_punct(ts)


def extract_date_from_text(text: str):
    if not text:
        return None
    s = text.lower()
    today = date_cls.today()
    # english keywords
    if re.search(r'\btomorrow\b', s) or 'tmr' in s or '明天' in s:
        return (today + timedelta(days=1)).isoformat()
    if re.search(r'\byesterday\b', s) or 'yday' in s or '昨天' in s:
        return (today - timedelta(days=1)).isoformat()
    if re.search(r'\btoday\b', s) or 'tonight' in s or '今天' in s:
        return today.isoformat()
    m = re.search(r'in\s+(\d+)\s+day', s)
    if m:
        days = int(m.group(1))
        return (today + timedelta(days=days)).isoformat()
    # next weekday
    weekdays = {'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6}
    m = re.search(r'next\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)', s)
    if m:
        wd = weekdays[m.group(1)]
        days_ahead = (wd - today.weekday() + 7) % 7
        days_ahead = days_ahead if days_ahead != 0 else 7
        return (today + timedelta(days=days_ahead)).isoformat()
    m = re.search(r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', s)
    if m:
        wd = weekdays[m.group(1)]
        days_ahead = (wd - today.weekday() + 7) % 7
        return (today + timedelta(days=days_ahead)).isoformat()
    # chinese weekdays
    for idx, names in enumerate([('monday', '星期一', '周一'), ('tuesday', '星期二', '周二'), ('wednesday', '星期三', '周三'),
                                 ('thursday', '星期四', '周四'), ('friday', '星期五', '周五'), ('saturday', '星期六', '周六'),
                                 ('sunday', '星期日', '周日', '星期天')]):
        for name in names:
            if name in s:
                wd = idx
                days_ahead = (wd - today.weekday() + 7) % 7
                return (today + timedelta(days=days_ahead)).isoformat()
    # english 'on 20 Oct'
    m = re.search(r'on\s+(\d{1,2})(?:st|nd|rd|th)?\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)', s)
    if m:
        day = int(m.group(1))
        mon_str = m.group(2)
        mon_map = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6, 'jul': 7, 'aug': 8, 'sep': 9, 'sept': 9,
                   'oct': 10, 'nov': 11, 'dec': 12}
        mon = mon_map.get(mon_str, None)
        if mon:
            year = today.year
            try:
                d = date_cls(year, mon, day)
                if d < today:
                    d = date_cls(year + 1, mon, day)
                return d.isoformat()
            except Exception:
                pass
    return None


def extract_time_from_text(text: str):
    if not text:
        return None
    s = text.lower()
    # look for patterns like 5pm, 7:30pm, 19:00
    m = re.search(r'(\d{1,2}:\d{2}\s*(am|pm)?)', s)
    if m:
        return normalize_time(m.group(1))
    m = re.search(r'(\d{1,2}\s*(am|pm))', s)
    if m:
        return normalize_time(m.group(1))
    m = re.search(r'(\b\d{2}:\d{2}\b)', s)
    if m:
        return normalize_time(m.group(1))
    return None
