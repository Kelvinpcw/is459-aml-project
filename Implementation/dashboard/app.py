"""Start from repository root: streamlit run Implementation/dashboard/app.py."""
import json,os,sys,hashlib,html,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import streamlit as st
import plotly.express as px
import pandas as pd
from dashboard.data import q1_query,case_query,run_query,get_case,evidence_csv,wilson,dimension_query,full_evidence_archive
from pipeline.release import ACCOUNT,REGION,load_current,verify_ref

st.set_page_config(page_title='AML investigation workspace',page_icon='◈',layout='wide')
st.markdown('''<style>.stApp {background:#f6f8fb} h1,h2,h3 {color:#142e46 !important} .block-container {padding-top:2rem} h1 {font-size:2rem !important} [data-testid="stMetric"] {background:white;padding:18px;border-radius:12px;border:1px solid #e2e8f0}</style>''',unsafe_allow_html=True)
st.title('AML investigation workspace')
st.caption('Synthetic IBM data · Historical exposure and explainable connected-account leads')

@st.cache_resource
def clients(profile,instance):
    import boto3
    if not profile and not instance:raise ValueError('Select your verified project profile, or explicitly enable the EC2 instance role.')
    session=boto3.Session(profile_name=profile or None,region_name=REGION)
    if session.client('sts').get_caller_identity()['Account']!=ACCOUNT:raise ValueError('Wrong AWS project account')
    return session.client('s3'),session.client('athena')

@st.cache_data(ttl=300)
def query_cached(release_id,sql):
    return run_query(athena,sql)

profile=os.environ.get('AML_AWS_PROFILE','')
instance=os.environ.get('AML_USE_INSTANCE_ROLE')=='1'
try:
    s3,athena=clients(profile,instance)
    if st.sidebar.button('Refresh published release') or 'release' not in st.session_state:
        st.session_state.release=load_current(s3)
    release=st.session_state.release
except Exception as e:
    st.info('Connect a verified project AWS profile to load a published release.')
    st.code('AML_AWS_PROFILE=IS-459-BDA streamlit run Implementation/dashboard/app.py')
    st.caption(str(e));st.stop()

st.sidebar.subheader('Published analysis')
st.sidebar.write(release['release_id'])
st.sidebar.caption(f"Dataset: {release['dataset_version']}\nPreparation: {release['run_id']}")
st.info(('Development pilot' if release['release_kind']=='pilot' else 'Full-data release')+' · Q1: '+release['q1']['dates'][0]+' to '+release['q1']['dates'][-1]+' · Q2: '+release['q2']['window_start']+' to '+release['q2']['window_end'])
with st.expander('Scope and interpretation limits'):
    for warning in release['warnings']:st.write(warning)
management,investigation,validation=st.tabs(['Monitoring allocation','Connected cases','Scope & evaluation'])

with management:
    st.subheader('Where should monitoring resources go?')
    dates=release['q1']['dates']
    c1,c2,c3,c4=st.columns(4)
    start=c1.selectbox('From date',dates,index=0);end=c2.selectbox('Through date',dates,index=dates.index('2022-09-16') if '2022-09-16' in dates else len(dates)-1)
    side=c3.selectbox('Currency side',['payment','receiving'],format_func=lambda x:'Paid' if x=='payment' else 'Received')
    currencies=[r['currency'] for r in query_cached(release['release_id'],dimension_query(release,side))]
    currency=c4.selectbox('Currency',currencies,index=currencies.index('US Dollar') if 'US Dollar' in currencies else 0)
    c1,c2,c3=st.columns(3)
    grain=c1.selectbox('Compare',['format','bank_pair','segment'],format_func=lambda x:{'format':'Payment formats','bank_pair':'Bank pairs','segment':'Bank pair + format'}[x])
    fmt=c2.selectbox('Payment format',['All','ACH','Cash','Cheque','Credit Card','Reinvestment','Wire','Bitcoin'])
    support=c3.selectbox('Minimum ranking support',[1000,500,100] if end<='2022-09-08' else [1000],help='Development sensitivity view; low-support groups remain visible and unranked.')
    if start<'2022-09-17'<=end:st.error('Choose the main period or the sparse tail separately; their traffic distributions differ.')
    elif start>end:st.error('Choose an end date on or after the start date.')
    else:
        try:
            rows=query_cached(release['release_id'],q1_query(release,start,end,currency,side,grain,None if fmt=='All' else fmt,support))
            if not rows:st.info('No transactions match these filters.')
            else:
                frame=pd.DataFrame(rows)
                for col in ['n','l','baseline_n','baseline_l']:frame[col]=pd.to_numeric(frame[col])
                for col in ['rate','lift']:frame[col]=pd.to_numeric(frame[col],errors='coerce')
                n=int(frame.iloc[0]['baseline_n']);l=int(frame.iloc[0]['baseline_l'])
                a,b,c=st.columns(3);a.metric('Transactions',f'{n:,}');b.metric('Labelled laundering',f'{l:,}');c.metric('Selected-population rate',f'{l/n:.4%}' if n else 'Not measurable')
                frame['group']=frame.apply(lambda r:' → '.join(str(r[k]) for k in ['sender_bank','receiver_bank','payment_format'] if k in r),axis=1)
                supported=frame[(frame.support=='supported') & (frame.lift>0)].head(20)
                if supported.empty:st.info('No supported groups have positive labelled exposure. Zero-lift groups do not establish monitoring priorities.')
                else:
                    chart=px.scatter(supported,x='n',y='rate',size='l',color='payment_format' if 'payment_format' in supported else None,hover_name='group',labels={'n':'Transaction volume','rate':'Historical laundering rate'}).update_yaxes(tickformat='.2%')
                    st.plotly_chart(chart,width='stretch')
                frame['descriptive_95pct_interval']=frame.apply(lambda r:'–'.join(f'{x:.4%}' for x in wilson(int(r.l),int(r.n))),axis=1)
                frame['rate']=frame['rate'].map(lambda x:f'{x:.4%}')
                st.dataframe(frame.drop(columns='group').rename(columns={'payment_format':'Payment format','sender_bank':'Sending bank','receiver_bank':'Receiving bank','n':'Transactions','l':'Labelled laundering','selected_currency_amount':currency+' total ('+side+')','baseline_n':'Baseline transactions','baseline_l':'Baseline positives','rate':'Laundering rate','lift':'Risk lift','support':'Support','descriptive_95pct_interval':'Descriptive 95% interval'}),hide_index=True,width='stretch')
                st.caption('At most 500 groups shown. Counts are summed across selected dates before rates/lift. Baseline uses the same filters. Amounts remain exact strings in the selected currency side. Intervals are descriptive; related payments may violate independence. Transferred value is not unique criminal proceeds.')
        except Exception as e:st.error(f'Unable to load this view: {e}')

with investigation:
    st.subheader('Which connected activity warrants a closer look?')
    case_release={**release,'q2':dict(release['q2'])}
    if release['q2'].get('snapshots'):
        snapshots=release['q2']['snapshots']
        ends=[x['window_end'] for x in snapshots]
        choice=st.selectbox('Daily snapshot cutoff',ends,index=ends.index('2022-09-17T00:00:00') if '2022-09-17T00:00:00' in ends else len(ends)-1)
        snapshot=next(x for x in snapshots if x['window_end']==choice)
        case_release['q2'].update({k:snapshot[k] for k in ('window_start','window_end','snapshot_cutoff','case_count')})
        if not snapshot.get('history_complete',True):st.warning('A full seven days of earlier history is unavailable for this snapshot.')
        if snapshot.get('cycle_excluded_nodes_above_degree',0):st.caption(f"Cycle coverage excludes {snapshot['cycle_excluded_nodes_above_degree']:,} accounts above the declared degree threshold; fan evidence remains complete.")
    st.caption(f"Window: {case_release['q2']['window_start']} inclusive → {case_release['q2']['window_end']} exclusive · Cutoff: {case_release['q2']['snapshot_cutoff']} · Dataset-local time")
    pattern=st.selectbox('Pattern',['All','fan_in','fan_out','cycle_2','cycle_3','cycle_4'])
    try:
        rows=query_cached(release['release_id'],case_query(case_release,None if pattern=='All' else pattern))
        st.caption(f"Showing up to 200 matching cases; {case_release['q2']['case_count']:,} total in this snapshot.")
        if not rows:st.info('No cases match this pattern.')
        else:
            selected=st.selectbox('Select an investigation case',range(len(rows)),format_func=lambda i:f"{rows[i]['pattern_type']} · {rows[i]['participant_count']} accounts · {rows[i]['evidence_transaction_count']} payments · {rows[i]['case_id'][:12]}")
            case,raw=get_case(s3,release,rows[selected])
            st.info(case['interpretation'])
            st.write(f"Rule {case['rule_version']} · {case['participant_count']} participants · {case['evidence_transaction_count']} evidence transactions")
            from pyvis.network import Network
            graph=Network(height='500px',width='100%',directed=True,cdn_resources='in_line',bgcolor='#ffffff')
            visible=case['nodes'][:100];ids={n['node_id'] for n in visible}
            for node in visible:
                # No raw data is inserted into HTML tooltips.
                graph.add_node(hashlib.sha256(node['node_id'].encode()).hexdigest(),label=html.escape(node['bank']+' / '+node['account']),group=html.escape(node.get('entity_id') or 'Unknown'),shape='dot')
            for edge in [e for e in case['edges'] if e['source'] in ids and e['target'] in ids][:500]:
                graph.add_edge(hashlib.sha256(edge['source'].encode()).hexdigest(),hashlib.sha256(edge['target'].encode()).hexdigest(),value=edge['transaction_count'],label=str(edge['transaction_count']))
            graph.set_options('{"physics":{"stabilization":{"iterations":100}},"interaction":{"hover":true},"edges":{"arrows":{"to":{"enabled":true}}}}')
            graph_html=re.sub(r'<script[^>]*src=[\"\']https?://[^>]*></script>','',graph.generate_html())
            graph_html=re.sub(r'<link[^>]*href=[\"\']https?://[^>]*>','',graph_html)
            graph_html=graph_html.replace('</body>',"<script>const graphBox=document.getElementById('mynetwork'); if(graphBox){new ResizeObserver(()=>{if(window.network){network.fit({animation:false});}}).observe(graphBox);} if(window.network){network.once('stabilizationIterationsDone',()=>network.fit({animation:false}));network.fit({animation:false});}</script></body>")
            st.iframe(graph_html,height=520,alt="Directed account graph with complete evidence available below")
            if case.get('display_capped') or len(case['nodes'])>100 or len(case['edges'])>500:st.warning('Graph display is capped at 100 nodes / 500 edges. Complete evidence is available below.')
            st.dataframe(pd.DataFrame(case['nodes']),hide_index=True,width='stretch')
            st.dataframe(pd.DataFrame(case['transactions'][:200]),hide_index=True,width='stretch')
            st.caption('First 200 evidence rows displayed. Downloads contain all evidence; parallel payments retain separate source IDs.')
            st.download_button('Download case manifest' if case.get('schema_version',1)>=2 else 'Download complete case JSON',raw,file_name=case['case_id']+'.json',mime='application/json')
            if case.get('schema_version',1)>=2:
                if st.button('Prepare complete evidence download'):
                    try:
                        archive=full_evidence_archive(s3,case)
                        st.download_button('Download all evidence chunks',archive,file_name=case['case_id']+'.zip',mime='application/zip')
                    except Exception as error:st.error(str(error))
            else:st.download_button('Download all supporting transactions',evidence_csv(case),file_name=case['case_id']+'.csv',mime='text/csv')
    except Exception as e:st.error(f'Unable to load cases: {e}')

with validation:
    st.subheader('What this release establishes')
    st.write(release['timestamp_policy'])
    st.write('Q1 reporting dates: '+', '.join(release['q1']['dates']))
    st.write('Q2 snapshot: '+release['q2']['window_start']+' to '+release['q2']['window_end'])
    try:
        metrics=verify_ref(s3,release['evaluation']['metrics'])
        if metrics.get('scoring_window'):
            window=metrics['scoring_window']
            st.write('Holdout payments: '+window['start_inclusive']+' inclusive to '+window['end_exclusive']+' exclusive (dataset-local time).')
        tx=metrics['detector_transaction_metrics'];a,b,c,d=st.columns(4)
        a.metric('Eligible payments',f"{tx['population']:,}");b.metric('Labelled positives',f"{tx['positive_labels']:,}");c.metric('Recall',f"{tx['recall']:.2%}" if tx.get('recall') is not None else 'Not measurable')
        d.metric('Precision',f"{tx['precision']:.3%}" if tx.get('precision') is not None else 'Not measurable')
        annotated=metrics['annotation_metrics'];st.write(f"Eligible annotated attempts: {annotated['eligible_attempts']:,}")
        st.write('Attempt recovery: '+(f"{annotated['attempt_recovery']:.2%}" if annotated.get('attempt_recovery') is not None else 'Not measurable'))
        if 'amount_baseline_transaction_metrics' in metrics:
            comparisons=[]
            for label,key in [('Connected cases','detector_transaction_metrics'),('Matched-volume amount baseline','amount_baseline_transaction_metrics'),('Development-frozen amount baseline','frozen_amount_baseline_transaction_metrics')]:
                if key not in metrics:continue
                item=metrics[key]
                comparisons.append({'Method':label,'Alerted payments':item['unique_alerted_transactions'],
                    'Precision':f"{item['precision']:.3%}" if item.get('precision') is not None else 'Not measurable',
                    'Recall':f"{item['recall']:.2%}" if item.get('recall') is not None else 'Not measurable'})
            st.dataframe(pd.DataFrame(comparisons),hide_index=True,width='stretch')
            coverage=annotated.get('amount_baseline_coverage_80pct')
            st.write('Matched-volume amount baseline: '+(f'{coverage:.2%}' if coverage is not None else 'Not measurable')+' of eligible attempts have at least 80% evidence coverage.')
        if 'recovery_improvement_percentage_points' in metrics:
            improvement=metrics['recovery_improvement_percentage_points']
            st.write('Typed recovery improvement over matched-volume amount coverage: '+(f'{improvement:.2f} percentage points' if improvement is not None else 'Not measurable'))
            target=metrics.get('improvement_target_met')
            st.write('Frozen five-percentage-point recovery target: '+('Met' if target is True else 'Unmet' if target is False else 'Not measurable'))
        st.caption('Attempt recovery concerns only eligible supported annotations. It does not imply recovery of every laundering event or better individual-payment precision/recall than the amount baseline.')
        for limitation in metrics.get('limitations',[]):st.write(limitation)
    except Exception as e:st.error(f'Unable to load evaluation: {e}')
    st.caption('Labels and annotations enter offline evaluation only. Structural leads are not proof of laundering or chronological return of identical funds.')
