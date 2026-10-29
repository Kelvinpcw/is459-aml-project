"""Display-only charts and bounded graphs; no detector or metric policy."""
import hashlib,html,json,math,re
from datetime import datetime
import plotly.graph_objects as go

NAVY='#203d33';TEAL='#256653';MUTED='#738078'
PATTERNS={'fan_in':'Fan-in','fan_out':'Fan-out','cycle_2':'2-account cycle','cycle_3':'3-account cycle','cycle_4':'4-account cycle'}
CSS='''<style>
:root{--ink:#263c33;--muted:#748078;--line:#e1e5dc;--teal:#256653}
.stApp{background:#f5f6f2;color:var(--ink);font-family:'Avenir Next',system-ui,sans-serif}
[data-testid="stMainBlockContainer"]{max-width:1400px;padding:2rem 2.5rem 3rem}
[data-testid="stHeader"]{background:transparent}[data-testid="stToolbar"]{visibility:hidden}
[data-testid="stSidebar"]{background:#fafbf7;border-right:1px solid var(--line)}
[data-testid="stSidebar"] [data-testid="stRadio"] label{padding:12px 9px;border-radius:9px;margin:5px 0}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked){background:#e9efde;color:#123d32}
[data-testid="stSidebar"] [data-testid="stRadio"] label p{font-size:14px;font-weight:600}
h1,h2,h3{color:var(--ink)!important;letter-spacing:-.035em}
h1{font-size:2.1rem!important;font-weight:650!important;padding:.2rem 0 .4rem!important}
h3{font-size:1.12rem!important;letter-spacing:-.02em}p,[data-testid="stCaptionContainer"]{line-height:1.55}
[data-testid="stCaptionContainer"]{color:var(--muted)}
.brand{display:flex;align-items:center;gap:12px;margin:0 0 35px;color:#123d32}.brand strong{font-size:34px;letter-spacing:-.06em}.brand span{font-size:9px;letter-spacing:.16em;font-weight:600;line-height:1.8}
.eyebrow{font-size:10px;letter-spacing:.15em;font-weight:700;color:#52735f;margin:8px 0 10px}
.workspace-bar{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line);padding:0 0 15px;margin-bottom:24px;font-size:11px;color:#778279;gap:12px}
.workspace-bar b{color:#256653;font-weight:500}.release-pill{padding:6px 10px;background:white;border:1px solid var(--line);border-radius:6px;overflow-wrap:anywhere}
.kpis{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px;margin:10px 0 24px}.kpis.four{grid-template-columns:repeat(4,minmax(0,1fr))}
.kpi{background:#fff;border:1px solid var(--line);border-radius:10px;padding:20px;min-width:0}.kpis.four .kpi:last-child{background:#eaf0df}
.kpi-label{font-size:11px;color:#788479;margin-bottom:12px}.kpi-value{font-size:30px;line-height:1.15;letter-spacing:-.045em;font-weight:650;color:#273d33;overflow-wrap:anywhere}.kpi-detail{font-size:10px;color:#7c897e;margin-top:10px}
.context{font-size:13px;color:#748078;margin:0 0 14px}.insight{font-size:14px;background:#eaf0df;border-left:3px solid #256653;padding:13px 17px;border-radius:0 7px 7px 0;margin:0 0 16px;color:#244b3d}
.priority-card{background:#173f33;border-radius:12px;padding:25px;color:#eff6e8;min-height:340px;margin:0 0 12px}.priority-card .eyebrow{color:#c9d9b7;font-size:9px}.priority-card h3{color:#eff6e8!important;font-size:1.55rem!important;line-height:1.35}.priority-value{font-size:55px;letter-spacing:-.06em;line-height:1.15;color:#ddedb5;margin:22px 0 5px}.priority-card p{font-size:13px;color:#deead7}.priority-card small{display:block;font-size:10px;line-height:1.6;color:#bdd0b8;margin-top:18px}.priority-card hr{border-color:#ffffff25;margin:20px 0}
.rule-card{background:#eaf0df;border:1px solid #dce5ce;padding:18px 22px;border-radius:10px;margin:14px 0}.rule-card p{margin:7px 0;font-size:13px;line-height:1.6}.rule-card .eyebrow{margin:0}
[data-testid="stPlotlyChart"],[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:10px;overflow:hidden;background:white}
[data-testid="stExpander"]{background:#ffffff99;border-radius:10px;border-color:var(--line)}
[data-testid="stButton"] button,[data-testid="stDownloadButton"] button,[data-testid="stPopover"] button{border-radius:7px}
[data-testid="stButton"] button:hover{border-color:#256653;color:#256653}
[data-testid="stRadio"] label{cursor:pointer}
@media(max-width:740px){[data-testid="stMainBlockContainer"]{padding:1.25rem 1rem 2rem}.kpis,.kpis.four{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.kpi{padding:14px 12px}.kpi-value{font-size:23px}.kpi-label{font-size:10px}.kpi-detail{font-size:10px}h1{font-size:1.8rem!important}.workspace-bar{font-size:10px;flex-wrap:wrap}.priority-card{min-height:0}.priority-value{font-size:42px;margin:12px 0}}
</style>'''


def esc(value):return html.escape(str(value),quote=True)


def kpis(items):
    return '<div class="kpis'+(' four' if len(items)==4 else '')+'">'+''.join('<div class="kpi"><div class="kpi-label">'+esc(label)+'</div><div class="kpi-value">'+esc(value)+'</div><div class="kpi-detail">'+esc(detail)+'</div></div>' for label,value,detail in items)+'</div>'


def period(start,end):
    a=datetime.fromisoformat(start);b=datetime.fromisoformat(end)
    return a.strftime('%d %b %Y')+' – '+b.strftime('%d %b %Y')


def chart_style(fig,height=350):
    fig.update_layout(height=height,margin=dict(l=10,r=38,t=25,b=35),paper_bgcolor='#ffffff',plot_bgcolor='#ffffff',font=dict(family='Arial, sans-serif',size=12,color=NAVY),hoverlabel=dict(bgcolor='white',font_size=13),showlegend=False)
    fig.update_xaxes(showgrid=True,gridcolor='#edf0e8',zeroline=False,linecolor='#e1e5dc',title_font_size=12)
    fig.update_yaxes(showgrid=False,zeroline=False,title_font_size=12)
    return fig


def exposure_chart(rows,mode='Risk lift'):
    # SQL supplies rates/lift for the same selected population. Never recompute
    # them from daily rates or combine monetary units for display.
    ranked=sorted((r for r in rows if r.get('support')=='supported' and int(r.get('n') or 0)>0 and (float(r.get('lift') or 0)>0 if mode=='Risk lift' else r.get('rate') is not None)),key=lambda r:(-float(r['lift']),-int(r['n']),str(r.get('group',''))))[:10]
    if not ranked:return None
    labels=[r['group'] for r in ranked]
    custom=[[int(r['n']),int(r['l']),float(r['rate']),float(r['lift'])] for r in ranked]
    if mode=='Risk lift':
        fig=go.Figure(go.Bar(x=[float(r['lift']) for r in ranked],y=labels,orientation='h',marker_color=[TEAL if i==0 else '#b6c8ad' for i in range(len(ranked))],text=[f"{float(r['lift']):.2f}×" for r in ranked],textposition='outside',cliponaxis=False,customdata=custom,hovertemplate='%{y}<br>Lift: %{customdata[3]:.2f}×<br>Payments: %{customdata[0]:,}<br>Labels: %{customdata[1]:,}<br>Rate: %{customdata[2]:.4%}<extra></extra>'))
        fig.add_vline(x=1,line_width=1,line_dash='dot',line_color=MUTED)
        fig.update_yaxes(autorange='reversed',automargin=True);fig.update_xaxes(title='Lift against the same filtered population',rangemode='tozero');fig.update_layout(bargap=.45)
    else:
        fig=go.Figure(go.Scatter(x=[int(r['n']) for r in ranked],y=[float(r['rate']) for r in ranked],mode='markers',text=labels,marker=dict(size=[min(38,12+math.sqrt(int(r['l']))) for r in ranked],color=TEAL,opacity=.8,line=dict(width=2,color='white')),customdata=custom,hovertemplate='%{text}<br>Payments: %{customdata[0]:,}<br>Labels: %{customdata[1]:,}<br>Rate: %{customdata[2]:.4%}<br>Lift: %{customdata[3]:.2f}×<extra></extra>'))
        fig.update_xaxes(title='Transaction volume (log scale)',type='log');fig.update_yaxes(title='Historical labelled rate',tickformat='.2%')
        baseline=next((int(r['baseline_l'])/int(r['baseline_n']) for r in ranked if int(r.get('baseline_n') or 0)>0),None)
        if baseline is not None:fig.add_hline(y=baseline,line_dash='dot',line_color=MUTED,annotation_text='Selected baseline',annotation_position='top right')
    return chart_style(fig,max(300,85+len(ranked)*38) if mode=='Risk lift' else 360)


def monitoring_lead(rows):
    """Describe one supported row against its supplied, full filtered baseline.

    Preview rows may be capped. Never derive the baseline or shares by summing
    the preview, and never interpret a low-support row as a ranked priority.
    """
    eligible=[]
    for row in rows:
        try:
            n,l,bn,bl=(int(row[k]) for k in ('n','l','baseline_n','baseline_l'))
            lift=float(row['lift'])
        except (TypeError,ValueError,KeyError):continue
        if row.get('support')=='supported' and n>=1000 and 0<l<=n<=bn and 0<l<=bl<=bn and math.isfinite(lift) and lift>1:
            eligible.append((row,n,l,bn,bl,lift))
    if not eligible:return None
    row,n,l,bn,bl,lift=min(eligible,key=lambda x:(-x[5],-x[1],str(x[0].get('group',''))))
    return {'group':str(row['group']),'n':n,'l':l,'lift':lift,'traffic_share':n/bn,'label_share':l/bl}


def priority_card(lead):
    if not lead:
        return '<aside class="priority-card"><div class="eyebrow">READING THE SIGNAL</div><h3>No supported above-baseline lead.</h3><p>Review the counts or widen the reporting window. A small population or zero baseline cannot support a ranked interpretation.</p><small>Historical association, not a laundering verdict.</small></aside>'
    return ('<aside class="priority-card"><div class="eyebrow">A MONITORING LEAD, EXPLAINED</div><h3>'+esc(lead['group'])+' deserves a closer look.</h3><div class="priority-value">'+f"{lead['lift']:.1f}×"+'</div><p>the selected population’s labelled rate</p><hr><p><b>'+f"{lead['traffic_share']:.1%}"+'</b> of payments account for <b>'+f"{lead['label_share']:.1%}"+'</b> of historical labelled activity.</p><small>Selected from the displayed ranking preview. Review the controls alongside volume and support. Historical association is not proof of criminal intent.</small></aside>')


def rule_card(case):
    return '<div class="rule-card"><div class="eyebrow">WHY THIS CASE WAS GENERATED</div><p>'+esc(case['interpretation'])+'</p><p><b>Rule:</b> '+esc(case['rule_version'])+'</p><p>Structural lead for investigation. A cycle does not establish chronological return of identical funds.</p></div>'


def graph_payload(case,show_labels=True):
    candidates={n['node_id']:n for n in case['nodes']};degree={k:0 for k in candidates}
    for e in case['edges']:
        for k in ('source','target'):
            if e[k] in degree:degree[e[k]]+=1
    # A bounded preview favors connected core accounts; stored/downloaded data
    # is untouched and the displayed population is explicitly reported.
    ordered=sorted(candidates,key=lambda k:(-degree[k],k))[:100]
    if case.get('pattern_type','').startswith('cycle') and len(ordered)<=4:
        walk=[ordered[0]] if ordered else []
        while len(walk)<len(ordered):
            next_ids=sorted(e['target'] for e in case['edges'] if e['source']==walk[-1] and e['target'] in ordered and e['target'] not in walk)
            walk.append(next_ids[0] if next_ids else next(x for x in ordered if x not in walk))
        ordered=walk
    ids=set(ordered);edges=[e for e in case['edges'] if e['source'] in ids and e['target'] in ids][:500]
    entities=sorted({candidates[k].get('entity_id') for k in ordered if candidates[k].get('entity_id')})
    palette=['#dcecf1','#e4e6f7','#f4e8d8','#dff0e7','#f3e0e7','#e8e8e1']
    colors={entity:palette[i%len(palette)] for i,entity in enumerate(entities)}
    fan=case.get('pattern_type') in ('fan_in','fan_out') and len(ordered)>2
    nodes=[]
    for i,key in enumerate(ordered):
        n=candidates[key];index=i-1 if fan else i;count=len(ordered)-1 if fan else len(ordered)
        angle=2*math.pi*index/max(count,1)-math.pi/2;radius=200 if len(ordered)<12 else 320
        x,y=(0,0) if fan and i==0 else (radius*math.cos(angle),radius*math.sin(angle))
        label='…'+str(n['account'])[-6:]+'\nBank '+str(n['bank']) if show_labels else ''
        nodes.append({'id':hashlib.sha256(key.encode()).hexdigest(),'label':esc(label),'x':round(x,4),'y':round(y,4),'size':25 if fan and i==0 else 19,'color':{'background':colors.get(n.get('entity_id'),'#e8edf0'),'border':'#6d8a70','highlight':{'background':'#c7e4e3','border':TEAL}},'title':esc('Account '+str(n['account'])+' | Bank '+str(n['bank'])+' | '+str(n.get('entity_name') or 'Entity unknown')),'details':esc('Account '+str(n['account'])+' · Bank '+str(n['bank'])+' · '+str(n.get('entity_name') or 'Entity unknown'))})
    pairs={(e['source'],e['target']) for e in edges}
    links=[{'from':hashlib.sha256(e['source'].encode()).hexdigest(),'to':hashlib.sha256(e['target'].encode()).hexdigest(),'label':str(e['transaction_count']) if len(edges)<=12 else '', 'title':esc(f"{int(e['transaction_count']):,} supporting payments"),'width':min(4,1.3+math.log1p(int(e['transaction_count']))/3),'smooth':{'enabled':True,'type':'curvedCW','roundness':.18} if (e['target'],e['source']) in pairs else False} for e in edges]
    return {'nodes':nodes,'edges':links,'visible_accounts':len(nodes),'visible_edges':len(links)}


def graph_html(case,show_labels=True):
    from pyvis.network import Network
    data=graph_payload(case,show_labels);g=Network(height='460px',width='100%',directed=True,cdn_resources='in_line',bgcolor='#fafbf7')
    for n in data['nodes']:g.add_node(n['id'],**{k:v for k,v in n.items() if k!='id'},shape='dot',borderWidth=2,font={'face':'Arial','size':15,'color':NAVY,'strokeWidth':3,'strokeColor':'#fafbf7'})
    for e in data['edges']:g.add_edge(e['from'],e['to'],**{k:v for k,v in e.items() if k not in ('from','to')})
    g.set_options(json.dumps({'physics':{'enabled':False},'interaction':{'hover':True,'tooltipDelay':100,'hideEdgesOnDrag':False},'edges':{'arrows':{'to':{'enabled':True,'scaleFactor':.65}},'color':{'color':'#92a887','highlight':TEAL},'font':{'size':12,'align':'middle','background':'#fafbf7','strokeWidth':0}},'layout':{'improvedLayout':False}}))
    result=g.generate_html()
    result=re.sub(r'<script[^>]*src=[\"\']https?://[^>]*></script>','',result);result=re.sub(r'<link[^>]*href=[\"\']https?://[^>]*>','',result)
    controls='''<style>html,body{margin:0;background:#fafbf7;font-family:Arial,sans-serif}#mynetwork{border:0!important;outline:0}.card{border:0!important}#graph-tools{position:absolute;right:12px;top:12px;display:flex;gap:5px}#graph-tools button{border:1px solid #dce3d4;background:white;color:#203d33;padding:7px 11px;border-radius:6px;cursor:pointer}#account-detail{position:absolute;left:14px;right:14px;bottom:8px;font-size:12px;line-height:1.5;color:#617463;background:#fafbf7e8;padding:6px;border-radius:5px}</style>
<div id="graph-tools"><button id="graph-zoom-in" aria-label="Zoom in">+</button><button id="graph-zoom-out" aria-label="Zoom out">−</button><button id="graph-fit">Fit graph</button></div><output id="account-detail">Click an account to see its full identifier and entity.</output>
<script>function fitGraph(){network.fit({animation:false,padding:65});}document.getElementById('graph-fit').onclick=fitGraph;document.getElementById('graph-zoom-in').onclick=()=>network.moveTo({scale:network.getScale()*1.25});document.getElementById('graph-zoom-out').onclick=()=>network.moveTo({scale:network.getScale()/1.25});network.on('selectNode',p=>{document.getElementById('account-detail').textContent=nodes.get(p.nodes[0]).details;});new ResizeObserver(fitGraph).observe(document.getElementById('mynetwork'));fitGraph();</script>'''
    return result.replace('</body>',controls+'</body>'),data
