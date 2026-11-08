"""Scrollable, paged investigation leads for the local release viewer."""
from datetime import date
from hashlib import sha256
from pathlib import Path

import streamlit as st

from dashboard.case_catalog import PAGE_SIZE


ASSETS = Path(__file__).parent
WIDGET_KEY = 'q2_lead_cards'
STATE_KEY = 'q2_lead_queue_state'
PATTERNS = {'fan_in': 'Fan-in', 'fan_out': 'Fan-out'}

lead_cards = st.components.v2.component(
    'local_case_queue',
    html="""<section class="queue" aria-labelledby="queue-title">
        <div class="queue-heading"><h2 id="queue-title">Investigation leads</h2>
            <span class="queue-count"></span></div>
        <nav class="queue-pager" aria-label="Investigation lead pages">
            <button type="button" data-step="-1" aria-label="Previous case page">‹</button>
            <span class="queue-page" aria-live="polite"></span>
            <button type="button" data-step="1" aria-label="Next case page">›</button>
        </nav>
        <div class="queue-scroll" role="region" aria-label="Investigation lead cards" tabindex="0"></div>
    </section>""",
    css=(ASSETS / 'case_queue.css').read_text(),
    js=(ASSETS / 'case_queue.js').read_text(),
)


def card_data(row):
    pattern = PATTERNS.get(row['pattern_type'], 'Cycle')
    day = date.fromisoformat(row['snapshot'][:10])
    accounts = int(row['participant_count'])
    payments = int(row['evidence_transaction_count'])
    title = {
        'Fan-in': f'{accounts - 1:,} senders into one account',
        'Fan-out': f'One account sends to {accounts - 1:,} recipients',
        'Cycle': f'Closed loop across {accounts:,} accounts',
    }[pattern]
    return {
        'id': row['case_id'],
        'snapshot': row['snapshot'],
        'pattern': pattern,
        'title': title,
        'summary': (f"{accounts:,} {'account' if accounts == 1 else 'accounts'} · "
                    f"{payments:,} {'payment' if payments == 1 else 'payments'}"),
        'date': day.isoformat(),
        'dateLabel': day.strftime('%d %b'),
    }


def render_case_queue(scope, total, load_page):
    pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    state = st.session_state.get(STATE_KEY, {})
    if state.get('scope') != scope or not 1 <= state['page'] <= pages:
        state = {'scope': scope, 'page': 1, 'selected': None}
        st.session_state[STATE_KEY] = state

    page = state['page']
    rows = load_page(*scope, page)
    by_id = {(row['case_id'], row['snapshot']): row for row in rows}
    selected = by_id.get(state['selected'], rows[0])
    view = sha256(repr((scope, page)).encode()).hexdigest()

    def on_action():
        action = st.session_state.get(WIDGET_KEY, {}).get('action')
        if not isinstance(action, dict) or action.get('view') != view:
            return
        key = action.get('caseId'), action.get('snapshot')
        step = action.get('step')
        if all(isinstance(value, str) for value in key) and key in by_id:
            st.session_state[STATE_KEY] = {**state, 'selected': key}
        elif step in (-1, 1) and 1 <= page + step <= pages:
            st.session_state[STATE_KEY] = {**state, 'page': page + step, 'selected': None}

    lead_cards(key=WIDGET_KEY, on_action_change=on_action, data={
        'view': view, 'count': total, 'page': page, 'pages': pages,
        'selected': [selected['case_id'], selected['snapshot']],
        'cards': [card_data(row) for row in rows],
    })
    st.caption('Ordered by case ID. This order does not indicate urgency.')
    return selected
