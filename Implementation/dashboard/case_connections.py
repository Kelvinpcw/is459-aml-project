"""Interactive Q2 graph linked to the published evidence preview."""
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from itertools import islice
import json
from pathlib import Path

import streamlit as st

from dashboard.data import read_evidence_part
from dashboard.presentation import graph_payload


ASSETS = Path(__file__).parent
connection_graph = st.components.v2.component(
    'q2_case_connections',
    html='''<section class="graph-frame">
        <div class="graph-tools">
            <button type="button" class="zoom-out" aria-label="Zoom out">−</button>
            <button type="button" class="zoom-in" aria-label="Zoom in">+</button>
            <button type="button" class="zoom-fit" aria-label="Fit graph">Fit</button>
        </div>
        <div class="graph-canvas"></div>
        <p class="graph-note">Select an arrow to see its payments. Numbers show payment counts.</p>
    </section>''',
    css=(ASSETS / 'connections.css').read_text(),
    js=(ASSETS / 'connections.js').read_text(),
)


def graph_data(case, show_labels):
    payload = graph_payload(case, show_labels)
    accounts = {sha256(node['node_id'].encode()).hexdigest(): node for node in case['nodes']}
    edges = {(sha256(edge['source'].encode()).hexdigest(), sha256(edge['target'].encode()).hexdigest()): edge
             for edge in case['edges']}
    nodes = [
        dict(id=node['id'], x=node['x'], y=node['y'], size=node['size'], fill=node['color']['background'],
             account=accounts[node['id']]['account'], bank=accounts[node['id']]['bank'],
             entity=accounts[node['id']].get('entity_name') or 'Entity unknown')
        for node in payload['nodes']
    ]
    links = {}
    arrows = []
    for index, arrow in enumerate(payload['edges']):
        edge = edges[arrow['from'], arrow['to']]
        link_id = str(index)
        links[link_id] = edge
        arrows.append({'id': link_id, 'from': arrow['from'], 'to': arrow['to'],
                       'curved': bool(arrow['smooth']), 'count': edge['transaction_count']})
    return dict(nodes=nodes, edges=arrows, showLabels=show_labels), accounts, links


def transfer_links(case):
    links = {}
    for edge in case['edges']:
        pair = edge['source'], edge['target']
        (from_bank, sender), (to_bank, receiver) = (json.loads(value) for value in pair)
        count = int(edge['transaction_count'])
        links[pair] = (f'Bank {from_bank} / {sender} → Bank {to_bank} / {receiver} ({count:,})', count)
    return links


@st.cache_data(ttl=300, max_entries=32, show_spinner=False)
def link_payments(_s3, release_id, case, source, target, count):
    sender, receiver = tuple(json.loads(source)), tuple(json.loads(target))

    def matches(payment):
        return ((payment['sender_bank'], payment['sender_account']) == sender
                and (payment['receiver_bank'], payment['receiver_account']) == receiver)

    limit = min(int(count), 200)
    rows = list(islice(filter(matches, case['transactions']), limit))
    if len(rows) == limit:
        return rows

    def stored():
        cache, size = {}, 0
        for part in case.get('evidence_parts', []):
            size += part['bytes']
            if size > 50_000_000:
                break
            for line in read_evidence_part(_s3, part, cache).splitlines():
                yield json.loads(line)

    stored_rows = list(islice(filter(matches, stored()), limit))
    return stored_rows if len(stored_rows) >= len(rows) else rows


def render_graph(case, show_labels, s3, release_id, selected_link_key):
    diagram, accounts, links = graph_data(case, show_labels)
    key = 'q2_graph_' + case['case_id']
    account_key = 'q2_account_' + case['case_id']
    directions = {index: (edge['source'], edge['target']) for index, edge in links.items()}

    def arrow_clicked():
        arrow = st.session_state[key].get('arrow')
        if arrow in directions:
            st.session_state[selected_link_key] = directions[arrow]
            st.session_state[account_key] = None

    def account_clicked():
        node = st.session_state[key].get('account')
        if node in accounts:
            st.session_state[account_key] = node
            st.session_state[selected_link_key] = None

    focus = st.session_state.get(selected_link_key)
    account = st.session_state.get(account_key)
    selected = next((index for index, pair in directions.items() if pair == focus), None)
    rows = None
    graph, inspector = st.columns([2, 1.12], gap='small')
    with graph:
        connection_graph(
            key=key, on_arrow_change=arrow_clicked, on_account_change=account_clicked,
            data={**diagram, 'selected': selected, 'selectedAccount': account},
        )
        if case.get('display_capped') or len(diagram['nodes']) < case['participant_count'] or len(diagram['edges']) < case.get('unique_edge_count', len(case['edges'])):
            st.caption(f"Graph preview: {len(diagram['nodes']):,} accounts / {len(diagram['edges']):,} links. Complete stored evidence is retained.")
    with inspector, st.container(border=True):
        st.markdown('**Connection payments**')
        if selected is not None:
            edge = links[selected]
            count = int(edge['transaction_count'])
            rows = link_payments(s3, release_id, case, *focus, count)
            sender, receiver = (json.loads(value)[1] for value in focus)
            st.text(f"{sender} → {receiver}")
            st.caption(f"{count:,} {'payment' if count == 1 else 'payments'}")
            for row in rows[:4]:
                whole, _, fraction = f"{Decimal(row['amount_paid']):,f}".partition('.')
                st.text(f"{whole}.{fraction.rstrip('0').ljust(2, '0')} {row['payment_currency']}")
                st.caption(datetime.fromisoformat(row['event_time']).strftime('%d %b · %H:%M')
                           + ' · ' + row['payment_format'])
            if len(rows) < min(count, 200):
                st.caption('Some payments are outside this preview. Use the case evidence download.')
            elif len(rows) > 4:
                st.caption('See Evidence preview for more payments.')
        elif account in accounts:
            node = accounts[account]
            st.text(f"Account {node['account']} · Bank {node['bank']}")
            st.caption(node.get('entity_name') or 'Entity unknown')
        else:
            st.caption('Select an arrow to see the payments behind it.')
    return rows
