"""Display-only charts and bounded graphs; no detector or metric policy."""
import hashlib,html,json,math,re
from datetime import datetime
import plotly.graph_objects as go

NAVY='#183549';TEAL='#147d80';MUTED='#68808f'
PATTERNS={'fan_in':'Fan-in','fan_out':'Fan-out','cycle_2':'2-account cycle','cycle_3':'3-account cycle','cycle_4':'4-account cycle'}
CSS='''<style>
:root{--ink:#183549;--muted:#68808f;--line:#e0e8ed;--teal:#147d80}
.stApp{background:#f5f7fa;color:var(--ink)}
[data-testid="stMainBlockContainer"]{max-width:1260px;padding:2rem 2.5rem 3rem}
[data-testid="stHeader"]{background:transparent}
[data-testid="stToolbar"]{visibility:hidden}
h1,h2,h3{color:var(--ink)!important;letter-spacing:-.035em}
h1{font-size:2.05rem!important;font-weight:650!important;padding:.25rem 0 .35rem!important}
h3{font-size:1.15rem!important;letter-spacing:-.02em}
p,[data-testid="stCaptionContainer"]{line-height:1.5}
[data-testid="stCaptionContainer"]{color:var(--muted)}
.brand{display:flex;align-items:center;justify-content:space-between;margin-bottom:1.25rem;font-size:11px;letter-spacing:.12em;font-weight:700;color:#607989}
.brand strong{font-size:16px;letter-spacing:.13em;color:#183549}.brand span{letter-spacing:.02em;font-weight:500}
.kpis{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin:6px 0 22px}
.kpis.four{grid-template-columns:repeat(4,minmax(0,1fr))}
.kpi{background:#fff;border:1px solid var(--line);border-radius:12px;padding:18px 20px;min-width:0}
.kpi-label{font-size:12px;color:#607989;margin-bottom:7px}.kpi-value{font-size:29px;line-height:1.15;letter-spacing:-.045em;font-weight:650;color:#183549;overflow-wrap:anywhere}.kpi-detail{font-size:11px;color:#78909d;margin-top:7px}
.context{font-size:13px;color:#68808f;margin:0 0 14px}.insight{font-size:14px;background:#eaf3f2;border-left:3px solid #147d80;padding:13px 17px;border-radius:0 7px 7px 0;margin:0 0 16px;color:#244b52}
[data-testid="stSegmentedControl"]{margin-bottom:8px}
[data-testid="stPlotlyChart"], [data-testid="stDataFrame"]{border-radius:10px;overflow:hidden}
[data-testid="stExpander"]{background:rgba(255,255,255,.7);border-radius:10px;border-color:#e0e8ed}
[data-testid="stButton"] button,[data-testid="stDownloadButton"] button,[data-testid="stPopover"] button{border-radius:8px}
@media(max-width:740px){[data-testid="stMainBlockContainer"]{padding:1.3rem 1rem 2rem}.kpis,.kpis.four{gap:7px}.kpi{padding:13px 10px}.kpi-value{font-size:22px}.kpi-label{font-size:11px}.kpi-detail{font-size:10px}.kpis.four{grid-template-columns:repeat(2,minmax(0,1fr))}h1{font-size:1.8rem!important}.brand span{display:none}}
</style>'''


def esc(value):return html.escape(str(value),quote=True)


def kpis(items):
    return '<div class="kpis'+(' four' if len(items)==4 else '')+'">'+''.join('<div class="kpi"><div class="kpi-label">'+esc(label)+'</div><div class="kpi-value">'+esc(value)+'</div><div class="kpi-detail">'+esc(detail)+'</div></div>' for label,value,detail in items)+'</div>'


def period(start,end):
    a=datetime.fromisoformat(start);b=datetime.fromisoformat(end)
    return a.strftime('%d %b %Y')+' – '+b.strftime('%d %b %Y')


def chart_style(fig,height=350):
    fig.update_layout(height=height,margin=dict(l=10,r=38,t=25,b=35),paper_bgcolor='#ffffff',plot_bgcolor='#ffffff',font=dict(family='Arial, sans-serif',size=12,color=NAVY),hoverlabel=dict(bgcolor='white',font_size=13),showlegend=False)
    fig.update_xaxes(showgrid=True,gridcolor='#edf1f4',zeroline=False,linecolor='#e5ebef',title_font_size=12)
    fig.update_yaxes(showgrid=False,zeroline=False,title_font_size=12)
    return fig


def exposure_chart(rows,mode='Risk lift'):
    # SQL supplies rates/lift for the same selected population. Never recompute
    # them from daily rates or combine monetary units for display.
    ranked=sorted((r for r in rows if r.get('support')=='supported' and float(r.get('lift') or 0)>0),key=lambda r:(-float(r['lift']),-int(r['n']),str(r.get('group',''))))[:10]
    if not ranked:return None
    labels=[r['group'] for r in ranked]
    custom=[[int(r['n']),int(r['l']),float(r['rate']),float(r['lift'])] for r in ranked]
    if mode=='Risk lift':
        fig=go.Figure(go.Bar(x=[float(r['lift']) for r in ranked],y=labels,orientation='h',marker_color=[TEAL if i==0 else '#adc8cb' for i in range(len(ranked))],text=[f"{float(r['lift']):.2f}×" for r in ranked],textposition='outside',cliponaxis=False,customdata=custom,hovertemplate='%{y}<br>Lift: %{customdata[3]:.2f}×<br>Payments: %{customdata[0]:,}<br>Labels: %{customdata[1]:,}<br>Rate: %{customdata[2]:.4%}<extra></extra>'))
        fig.add_vline(x=1,line_width=1,line_dash='dot',line_color=MUTED)
        fig.update_yaxes(autorange='reversed',automargin=True);fig.update_xaxes(title='Lift against the same filtered population',rangemode='tozero');fig.update_layout(bargap=.45)
    else:
        fig=go.Figure(go.Scatter(x=[int(r['n']) for r in ranked],y=[float(r['rate']) for r in ranked],mode='markers',text=labels,marker=dict(size=[min(38,12+math.sqrt(int(r['l']))) for r in ranked],color=TEAL,opacity=.8,line=dict(width=2,color='white')),customdata=custom,hovertemplate='%{text}<br>Payments: %{customdata[0]:,}<br>Labels: %{customdata[1]:,}<br>Rate: %{customdata[2]:.4%}<br>Lift: %{customdata[3]:.2f}×<extra></extra>'))
        fig.update_xaxes(title='Transaction volume',type='log');fig.update_yaxes(title='Historical laundering rate',tickformat='.2%')
    return chart_style(fig,max(300,85+len(ranked)*38) if mode=='Risk lift' else 360)


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
        nodes.append({'id':hashlib.sha256(key.encode()).hexdigest(),'label':esc(label),'x':round(x,4),'y':round(y,4),'size':25 if fan and i==0 else 19,'color':{'background':colors.get(n.get('entity_id'),'#e8edf0'),'border':'#52798d','highlight':{'background':'#c7e4e3','border':TEAL}},'title':esc('Account '+str(n['account'])+' | Bank '+str(n['bank'])+' | '+str(n.get('entity_name') or 'Entity unknown')),'details':esc('Account '+str(n['account'])+' · Bank '+str(n['bank'])+' · '+str(n.get('entity_name') or 'Entity unknown'))})
    pairs={(e['source'],e['target']) for e in edges}
    links=[{'from':hashlib.sha256(e['source'].encode()).hexdigest(),'to':hashlib.sha256(e['target'].encode()).hexdigest(),'label':str(e['transaction_count']) if len(edges)<=12 else '', 'title':esc(f"{int(e['transaction_count']):,} supporting payments"),'width':min(4,1.3+math.log1p(int(e['transaction_count']))/3),'smooth':{'enabled':True,'type':'curvedCW','roundness':.18} if (e['target'],e['source']) in pairs else False} for e in edges]
    return {'nodes':nodes,'edges':links,'visible_accounts':len(nodes),'visible_edges':len(links)}


def graph_html(case,show_labels=True):
    from pyvis.network import Network
    data=graph_payload(case,show_labels);g=Network(height='460px',width='100%',directed=True,cdn_resources='in_line',bgcolor='#f8fafc')
    for n in data['nodes']:g.add_node(n['id'],**{k:v for k,v in n.items() if k!='id'},shape='dot',borderWidth=2,font={'face':'Arial','size':15,'color':NAVY,'strokeWidth':3,'strokeColor':'#f8fafc'})
    for e in data['edges']:g.add_edge(e['from'],e['to'],**{k:v for k,v in e.items() if k not in ('from','to')})
    g.set_options(json.dumps({'physics':{'enabled':False},'interaction':{'hover':True,'tooltipDelay':100,'hideEdgesOnDrag':False},'edges':{'arrows':{'to':{'enabled':True,'scaleFactor':.65}},'color':{'color':'#809aaa','highlight':TEAL},'font':{'size':12,'align':'middle','background':'#f8fafc','strokeWidth':0}},'layout':{'improvedLayout':False}}))
    result=g.generate_html()
    result=re.sub(r'<script[^>]*src=[\"\']https?://[^>]*></script>','',result);result=re.sub(r'<link[^>]*href=[\"\']https?://[^>]*>','',result)
    controls='''<style>html,body{margin:0;background:#f8fafc;font-family:Arial,sans-serif}#mynetwork{border:0!important;outline:0}.card{border:0!important}#graph-tools{position:absolute;right:12px;top:12px;display:flex;gap:5px}#graph-tools button{border:1px solid #d8e3e9;background:white;color:#183549;padding:7px 11px;border-radius:6px;cursor:pointer}#account-detail{position:absolute;left:14px;right:14px;bottom:8px;font-size:12px;line-height:1.5;color:#526f80;background:#f8fafce8;padding:6px;border-radius:5px}</style>
<div id="graph-tools"><button id="graph-zoom-in" aria-label="Zoom in">+</button><button id="graph-zoom-out" aria-label="Zoom out">−</button><button id="graph-fit">Fit graph</button></div><output id="account-detail">Click an account to see its full identifier and entity.</output>
<script>function fitGraph(){network.fit({animation:false,padding:65});}document.getElementById('graph-fit').onclick=fitGraph;document.getElementById('graph-zoom-in').onclick=()=>network.moveTo({scale:network.getScale()*1.25});document.getElementById('graph-zoom-out').onclick=()=>network.moveTo({scale:network.getScale()/1.25});network.on('selectNode',p=>{document.getElementById('account-detail').textContent=nodes.get(p.nodes[0]).details;});new ResizeObserver(fitGraph).observe(document.getElementById('mynetwork'));fitGraph();</script>'''
    return result.replace('</body>',controls+'</body>'),data
