"""Read-only visualization of one immutable published release."""
import json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
import streamlit as st
from dashboard.data import q1_query,q1_trend_query,case_query,run_query,get_case,evidence_csv,wilson,dimension_query,full_evidence_archive
from dashboard.presentation import CSS,PATTERNS,esc,kpis,period,exposure_chart,graph_html
from dashboard.trends import range_options,date_window,daily_population,population_total,coverage_counts,LOW_DAILY_VOLUME,endpoint_comparison,trend_chart
from pipeline.release import ACCOUNT,REGION,load_current,verify_ref

st.set_page_config(page_title='AML | Investigation workspace',page_icon='◈',layout='wide',initial_sidebar_state='collapsed')
st.markdown(CSS,unsafe_allow_html=True)
st.markdown('<div class="brand"><strong>◈ AML</strong><span>INVESTIGATION WORKSPACE · SYNTHETIC IBM DATA</span></div>',unsafe_allow_html=True)

@st.cache_resource
def clients(profile,instance):
    import boto3
    if not profile and not instance:raise ValueError('Select a verified project profile or explicitly enable the EC2 instance role.')
    session=boto3.Session(profile_name=profile or None,region_name=REGION)
    if session.client('sts').get_caller_identity()['Account']!=ACCOUNT:raise ValueError('Wrong AWS project account')
    return session.client('s3'),session.client('athena')

@st.cache_data(ttl=300,max_entries=64)
def query_cached(release_id,sql):return run_query(athena,sql)

@st.cache_data(ttl=300,max_entries=4)
def case_cached(release_data,row):return get_case(s3,release_data,row)

profile=os.environ.get('AML_AWS_PROFILE','');instance=os.environ.get('AML_USE_INSTANCE_ROLE')=='1'
try:
    s3,athena=clients(profile,instance)
    if 'release' not in st.session_state:st.session_state.release=load_current(s3)
    release=st.session_state.release
except Exception as error:
    st.title('Connect your published analysis')
    st.info('Start this workspace with your verified project profile.')
    st.code('bash Implementation/scripts/start_local_dashboard.sh YOUR_PROJECT_PROFILE')
    st.caption(str(error));st.stop()

page=st.segmented_control('Workspace',['Monitoring','Case explorer','Evaluation'],default='Monitoring',required=True,label_visibility='collapsed',width='stretch',key='workspace_page')


def caption(text):st.markdown('<div class="context">'+esc(text)+'</div>',unsafe_allow_html=True)


def cards(items):st.markdown(kpis(items),unsafe_allow_html=True)


def select_filter(*args,**kwargs):
    return st.selectbox(*args,persist_state='session',**kwargs)


def refresh_data():
    try:updated=load_current(s3)
    except Exception as error:
        st.error('Refresh failed; the previous release is still selected. '+str(error));return
    st.session_state.release=updated;st.session_state.pop('prepared_archive',None);st.rerun()


def monitoring():
    st.title('Monitoring allocation')
    caption('Compare historical exposure with transaction volume. Find supported segments for control review.')
    dates=sorted(set(release['q1']['dates']))
    with st.popover('Reporting filters',icon=':material/tune:'):
        st.caption('All counts and baselines use these same filters.')
        if st.button('Refresh data',icon=':material/refresh:',key='refresh_monitoring'):refresh_data()
        preset=select_filter('Date range',range_options(dates),index=1,key='q1_range')
        custom_start=custom_end=None
        if preset=='Custom dates':
            for key in ('q1_start','q1_end'):
                if key in st.session_state and st.session_state[key] not in dates:del st.session_state[key]
            a,b=st.columns(2)
            custom_start=a.selectbox('From date',dates,persist_state='session',index=0,key='q1_start')
            custom_end=b.selectbox('Through date',dates,persist_state='session',index=len(dates)-1,key='q1_end')
        side=select_filter('Currency side',['payment','receiving'],format_func=lambda x:'Paid' if x=='payment' else 'Received',key='q1_side')
        currencies=[r['currency'] for r in query_cached(release['release_id'],dimension_query(release,side))]
        currency=select_filter('Currency',currencies,index=currencies.index('US Dollar') if 'US Dollar' in currencies else 0,key='q1_currency_'+side)
        grain=select_filter('Compare',['format','bank_pair','segment'],format_func=lambda x:{'format':'Payment formats','bank_pair':'Bank pairs','segment':'Bank pair + format'}[x],key='q1_grain')
        fmt=select_filter('Payment format',['All','ACH','Cash','Cheque','Credit Card','Reinvestment','Wire','Bitcoin'],key='q1_format')
        support=1000
        st.caption('Ranked segments require at least 1,000 payments. Low-support rows remain available in the details.')
    try:start,end=date_window(dates,preset,custom_start,custom_end)
    except ValueError as error:st.warning(str(error));return
    caption(period(start,end)+' · '+('Paid' if side=='payment' else 'Received')+' in '+currency+' · '+('All formats' if fmt=='All' else fmt)+' · Minimum '+f'{support:,}'+' payments')
    caption('Latest published date: '+period(dates[-1],dates[-1]).split(' – ')[0]+' · Rolling windows end on that date, not today.')
    with st.spinner('Loading daily published counts…'):
        trend_rows=query_cached(release['release_id'],q1_trend_query(release,start,end,currency,side,None if fmt=='All' else fmt))
    daily=daily_population(trend_rows,start,end,dates,release['q1'].get('day_coverage'));n,l,rate=population_total(daily)
    count=lambda value:f'{value:,}' if value is not None else 'Not available'
    cards([('Transactions',count(n),'Selected currency population'),('Labelled laundering',count(l),'Historical labels, not predictions'),('Population rate',f'{rate:.4%}' if rate is not None else 'Not measurable','Labels ÷ payments in this selection')])
    st.subheader('How exposure changed')
    coverage=coverage_counts(daily)
    if coverage['missing']:st.warning(f"{coverage['missing']} dates are absent from the published coverage. They remain gaps, not zero-count days.")
    if coverage['partial']:st.warning(f"{coverage['partial']} dates have explicitly reported partial coverage. Counts are retained; comparisons are provisional.")
    if coverage['low_volume']:st.info(f"{coverage['low_volume']} low-volume days: fewer than {LOW_DAILY_VOLUME:,} payments in this filtered population. Rates can be unstable. Low volume alone does not establish incomplete or bad data.")
    st.plotly_chart(trend_chart(daily),width='stretch',config={'displayModeBar':False})
    st.caption('Daily counts, rate and total traffic use the same currency side and format filter. Hover for exact values. Rates are calculated from counts; a day with no payments has no measurable rate.')
    comparison=endpoint_comparison(daily)
    if comparison:st.caption(comparison)
    with st.expander('Daily counts behind the trend'):
        st.dataframe(pd.DataFrame(daily).rename(columns={'date':'Date','n':'Transactions','l':'Labelled laundering','rate':'Laundering rate','coverage':'Day completeness','low_volume':'Low volume'}),hide_index=True,width='stretch',column_config={'Laundering rate':st.column_config.NumberColumn(format='percent')})
    if coverage['unknown']:st.caption('Whole-day completeness metadata was not supplied for some published dates. Publication alone does not certify a full day of source coverage.')
    with st.spinner('Loading published segment comparisons…'):
        rows=query_cached(release['release_id'],q1_query(release,start,end,currency,side,grain,None if fmt=='All' else fmt,support))
    if not rows:st.info('No transactions match the selected reporting window.');return
    frame=pd.DataFrame(rows)
    for col in ['n','l','baseline_n','baseline_l']:frame[col]=pd.to_numeric(frame[col])
    for col in ['rate','lift']:frame[col]=pd.to_numeric(frame[col],errors='coerce')
    baseline_n=int(frame.iloc[0].baseline_n);baseline_l=int(frame.iloc[0].baseline_l)
    baseline_rate=f'{baseline_l/baseline_n:.4%}' if baseline_n else 'Not measurable'
    caption('Selected-window ranking · '+period(start,end)+f' · Published baseline: {baseline_n:,} payments / {baseline_l:,} labels / '+baseline_rate)
    frame['group']=frame.apply(lambda r:' → '.join(str(r[k]) for k in ['sender_bank','receiver_bank','payment_format'] if k in r),axis=1)
    st.subheader('Where exposure is concentrated')
    mode=st.segmented_control('Chart view',['Risk lift','Volume vs rate'],default='Risk lift',required=True,label_visibility='collapsed',key='q1_chart',persist_state='session')
    chart=exposure_chart(frame.to_dict('records'),mode)
    if chart is None:st.info('No supported groups have positive labelled exposure in this selection.')
    else:
        st.plotly_chart(chart,width='stretch',config={'displayModeBar':False})
        st.caption('Supported groups only · Up to 10 shown · 1× is the same historical rate as the selected population.' if mode=='Risk lift' else 'Supported groups only · Logarithmic volume axis · Hover for exact counts, rates and lift.')
    with st.expander('Explore exact counts, amounts and uncertainty',expanded=False):
        display=frame.copy();display['Rate']=display.rate.map(lambda x:f'{x:.4%}');display['Lift']=display.lift.map(lambda x:f'{x:.2f}×' if pd.notna(x) else 'Not measurable');display['Descriptive 95% interval']=display.apply(lambda r:' – '.join(f'{x:.4%}' for x in wilson(int(r.l),int(r.n))),axis=1)
        display=display.rename(columns={'group':'Segment','n':'Transactions','l':'Labels','support':'Support','selected_currency_amount':currency+' amount ('+('paid' if side=='payment' else 'received')+')'})
        amount=currency+' amount ('+('paid' if side=='payment' else 'received')+')'
        st.dataframe(display[['Segment','Transactions','Labels','Rate','Lift','Support',amount,'Descriptive 95% interval']],hide_index=True,width='stretch')
        st.caption('Up to 500 groups. Low-support groups are unranked. Amount strings retain exact precision in the selected currency. Intervals are descriptive; related payments may violate independence. Transferred value is not unique criminal proceeds.')


def explorer():
    st.title('Connected cases')
    caption('Follow the accounts behind a structural lead, then inspect the supporting payments.')
    case_release={**release,'q2':dict(release['q2'])};snapshots=release['q2'].get('snapshots')
    with st.popover('Case filters',icon=':material/tune:'):
        if snapshots:
            ends=sorted(x['window_end'] for x in snapshots)
            snapshot_mode=select_filter('Snapshot view',['Latest published','Custom snapshot'],key='q2_snapshot_mode')
            if snapshot_mode=='Latest published':choice=ends[-1]
            else:
                if 'q2_snapshot' in st.session_state and st.session_state.q2_snapshot not in ends:del st.session_state['q2_snapshot']
                choice=select_filter('Daily snapshot cutoff',ends,index=len(ends)-1,format_func=lambda x:period(x,x).split(' – ')[0],key='q2_snapshot')
            snapshot=next(x for x in snapshots if x['window_end']==choice)
            case_release['q2'].update({k:snapshot[k] for k in ('window_start','window_end','snapshot_cutoff','case_count')})
        else:snapshot={}
        pattern=select_filter('Pattern',['All',*PATTERNS],format_func=lambda x:PATTERNS.get(x,'All patterns'),key='q2_pattern')
    caption(period(case_release['q2']['window_start'],case_release['q2']['window_end'])+' · End exclusive · Dataset-local time · '+PATTERNS.get(pattern,'All patterns'))
    if not snapshot.get('history_complete',True):st.warning('Earlier history is incomplete for this snapshot.')
    with st.spinner('Finding published cases…'):rows=query_cached(release['release_id'],case_query(case_release,None if pattern=='All' else pattern))
    if not rows:st.info('No cases match this pattern.');return
    st.caption(f"{len(rows):,} cases available in this preview · {case_release['q2']['case_count']:,} across all patterns in this snapshot")
    selected=select_filter('Investigation case',range(len(rows)),format_func=lambda i:f"{PATTERNS.get(rows[i]['pattern_type'],rows[i]['pattern_type'])} · {int(rows[i]['participant_count']):,} accounts · {int(rows[i]['evidence_transaction_count']):,} payments · {rows[i]['case_id'][:10]}",key='selected_case_'+case_release['q2']['window_end']+'_'+pattern)
    with st.spinner('Opening case evidence…'):case,raw=case_cached(release,rows[selected])
    cards([('Pattern',PATTERNS.get(case['pattern_type'],case['pattern_type']),'Structural lead, not proof'),('Accounts',f"{case['participant_count']:,}",'Distinct participating bank/accounts'),('Evidence payments',f"{case['evidence_transaction_count']:,}",'Complete evidence is downloadable')])
    labels=st.toggle('Show account labels',value=len(case['nodes'])<=20,key='labels_'+case['case_id'],persist_state='session',help='Hover or click an account for the full identifier. Large graphs start without labels to avoid overlap.')
    markup,data=graph_html(case,labels)
    st.iframe(markup,height=485,alt='Interactive directed account graph. Click an account for full identifiers; use Fit graph or zoom controls.')
    st.caption('Arrows show payment direction · Edge numbers show payment counts · Colors group entities; the palette repeats · Drag to explore, scroll to zoom')
    if case.get('display_capped') or len(case['nodes'])>100 or len(case['edges'])>500:st.warning(f"Graph preview: {data['visible_accounts']} accounts / {data['visible_edges']} links. Complete stored evidence is retained beyond this preview.")
    if snapshot.get('cycle_excluded_nodes_above_degree',0):st.caption(f"Cycle coverage excludes {snapshot['cycle_excluded_nodes_above_degree']:,} high-degree accounts; fan evidence remains complete.")
    accounts,evidence=st.tabs(['Accounts & entities','Evidence preview'])
    with accounts:
        fields=['bank','account','entity_name','entity_id','entity_unknown'];available=[k for k in fields if any(k in n for n in case['nodes'])]
        st.dataframe(pd.DataFrame(case['nodes'])[available].rename(columns={'bank':'Bank','account':'Account','entity_name':'Entity','entity_id':'Entity ID','entity_unknown':'Unknown mapping'}),hide_index=True,width='stretch')
        st.caption('Account preview from the case bundle. Full participants and evidence references remain in the case manifest.')
    with evidence:
        st.dataframe(pd.DataFrame(case['transactions'][:200]).rename(columns={'event_time':'Time','source_id':'Source ID','sender_bank':'Sending bank','sender_account':'Sending account','receiver_bank':'Receiving bank','receiver_account':'Receiving account','amount_paid':'Amount paid','payment_currency':'Paid currency','amount_received':'Amount received','receiving_currency':'Received currency','payment_format':'Format'}),hide_index=True,width='stretch')
        st.caption('Up to 200 preview rows. Amounts retain exact strings and separate paid/received currencies. Downloads contain all evidence, including distinct parallel payments.')
    st.subheader('Keep the evidence')
    st.download_button('Download case manifest' if case.get('schema_version',1)>=2 else 'Download complete case JSON',raw,file_name=case['case_id']+'.json',mime='application/json')
    if case.get('schema_version',1)>=2:
        if st.button('Prepare complete evidence download',icon=':material/download:'):
            with st.spinner('Verifying all evidence chunks…'):st.session_state['prepared_archive']=(release['release_id'],case['case_id'],full_evidence_archive(s3,case))
        archive=st.session_state.get('prepared_archive')
        if archive and archive[:2]==(release['release_id'],case['case_id']):st.download_button('Download all evidence chunks',archive[2],file_name=case['case_id']+'.zip',mime='application/zip')
    else:st.download_button('Download all supporting transactions',evidence_csv(case),file_name=case['case_id']+'.csv',mime='text/csv')
    with st.expander('Rule, scope and full case identity'):
        st.write(case['interpretation']);st.write('Rule: '+case['rule_version']);st.write('Case: '+case['case_id']);st.write('Snapshot cutoff: '+case_release['q2']['snapshot_cutoff']);st.caption('A structural cycle does not establish a chronological return of identical funds.')


def evaluation():
    st.title('Evaluation & limitations')
    caption('Separate connected-pattern recovery from individual-payment classification.')
    metrics=verify_ref(s3,release['evaluation']['metrics']);window=metrics.get('scoring_window')
    if window:caption('Holdout: '+period(window['start_inclusive'],window['end_exclusive'])+' · Start inclusive, end exclusive · Dataset-local time')
    tx=metrics['detector_transaction_metrics'];annotated=metrics['annotation_metrics']
    cards([('Eligible payments',f"{tx['population']:,}",'Full eligible holdout population' if window else 'Declared evaluation population'),('Labelled positives',f"{tx['positive_labels']:,}",'Historical evaluation labels'),('Precision',f"{tx['precision']:.3%}" if tx.get('precision') is not None else 'Not measurable','Labels among alerted payments'),('Recall',f"{tx['recall']:.2%}" if tx.get('recall') is not None else 'Not measurable','Positive labels covered')])
    st.subheader('Individual-payment comparison')
    comparisons=[]
    for label,key in [('Connected cases','detector_transaction_metrics'),('Matched-volume amount','amount_baseline_transaction_metrics'),('Development-frozen amount','frozen_amount_baseline_transaction_metrics')]:
        if key not in metrics:continue
        item=metrics[key];comparisons.append({'Method':label,'Alerted payments':item['unique_alerted_transactions'],'Precision':f"{item['precision']:.3%}" if item.get('precision') is not None else 'Not measurable','Recall':f"{item['recall']:.2%}" if item.get('recall') is not None else 'Not measurable'})
    st.dataframe(pd.DataFrame(comparisons),hide_index=True,width='stretch')
    baseline=metrics.get('amount_baseline_transaction_metrics',{})
    if all(tx.get(k) is not None and baseline.get(k) is not None and baseline[k]>tx[k] for k in ('precision','recall')):st.info('The amount baseline performs better on individual-payment precision and recall. Connected cases add explainable relationship evidence, but do not outperform it on these measures.')
    st.subheader('Eligible pattern recovery')
    recovery=annotated.get('attempt_recovery');coverage=annotated.get('amount_baseline_coverage_80pct');gain=metrics.get('recovery_improvement_percentage_points');target=metrics.get('improvement_target_met')
    cards([('Eligible annotations',f"{annotated['eligible_attempts']:,}",'Supported attempts in this population'),('Attempt recovery',f'{recovery:.2%}' if recovery is not None else 'Not measurable','Correct type and ≥80% core evidence'),('Recovery gain',f'{gain:.2f} pp' if gain is not None else 'Not measurable','Against matched-volume amount coverage')])
    if 'improvement_target_met' in metrics:st.write('Frozen five-percentage-point target: **'+('Met' if target is True else 'Unmet' if target is False else 'Not measurable')+'**')
    if coverage is not None:st.caption(f'Matched-volume amount baseline covers at least 80% of evidence for {coverage:.2%} of eligible attempts.')
    with st.expander('How to interpret these findings',expanded=True):
        st.write('Recovery applies only to eligible supported annotations. It does not mean every laundering event was recovered. Unannotated cases are not automatically false positives.')
        st.write('Development, holdout and sparse-tail periods stay separate. Calibration is frozen before holdout; rules are not retuned against these results.')
        for limitation in metrics.get('limitations',[]):st.write(limitation)
        st.caption('Labels and annotations enter offline evaluation only. Structural leads are not proof of laundering.')


try:
    if page=='Monitoring':monitoring()
    elif page=='Case explorer':explorer()
    else:evaluation()
except Exception as error:st.error('This view could not load. '+str(error))

st.divider()
with st.expander('Published release & scope'):
    st.write('Release: '+release['release_id']);st.caption('Dataset: '+release['dataset_version']+' · Preparation: '+release['run_id'])
    st.caption('Q1: '+period(release['q1']['dates'][0],release['q1']['dates'][-1])+' · Q2 snapshots: '+period(release['q2']['window_start'],release['q2']['window_end']))
    st.caption(release['timestamp_policy'])
    for warning in release['warnings']:st.write(warning)
    if st.button('Refresh published release'):refresh_data()
