"""Descriptive date trends with separate main-period and sparse-tail reporting."""
from datetime import date,timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dashboard.presentation import chart_style

TAIL_START=date(2022,9,17)


def reporting_periods(start,end):
    start,end=date.fromisoformat(start),date.fromisoformat(end)
    if start>end:raise ValueError('Reversed date range')
    periods=[]
    if start<TAIL_START:periods.append(('Main period',start.isoformat(),min(end,TAIL_START-timedelta(days=1)).isoformat()))
    if end>=TAIL_START:periods.append(('Sparse tail',max(start,TAIL_START).isoformat(),end.isoformat()))
    return periods


def daily_population(rows,start,end,published_dates):
    start,end=date.fromisoformat(start),date.fromisoformat(end)
    if start>end:raise ValueError('Reversed date range')
    published=set(published_dates);by_day={}
    for r in rows:
        day=str(r['event_date'])[:10]
        if day in by_day or day not in published or not start<=date.fromisoformat(day)<=end:raise ValueError('Unexpected or duplicate trend date')
        n,l=int(r['n']),int(r['l'])
        if n<0 or not 0<=l<=n:raise ValueError('Invalid daily counts')
        by_day[day]=(n,l)
    result=[];day=start
    while day<=end:
        key=day.isoformat();n,l=by_day.get(key,(0,0) if key in published else (None,None))
        result.append({'date':key,'n':n,'l':l,'rate':l/n if n else None,'period':'Sparse tail' if day>=TAIL_START else 'Main period'})
        day+=timedelta(days=1)
    return result


def population_total(daily):
    if any(r['n'] is None for r in daily):return None,None,None
    n=sum(r['n'] for r in daily);l=sum(r['l'] for r in daily)
    return n,l,l/n if n else None


def endpoint_comparison(daily):
    if len(daily)<2:return None
    first,last=daily[0],daily[-1]
    if first['n'] is None or last['n'] is None:return 'Endpoint comparison unavailable: a selected date is outside published coverage.'
    a=f"{first['rate']:.4%}" if first['rate'] is not None else 'not measurable'
    b=f"{last['rate']:.4%}" if last['rate'] is not None else 'not measurable'
    text=f"First → last selected day: labelled payments {first['l']:,} → {last['l']:,} ({last['l']-first['l']:+,}); rate {a} → {b}; total payments {first['n']:,} → {last['n']:,}."
    if first['period']!=last['period']:text+=' These endpoints belong to different traffic populations; the change is descriptive, not a like-for-like risk increase.'
    return text


def trend_chart(daily):
    fig=make_subplots(rows=3,cols=1,shared_xaxes=True,vertical_spacing=.09,row_heights=[.38,.32,.30],subplot_titles=['Labelled laundering payments','Laundering rate · labels ÷ all payments','All payments · daily population'])
    for label,color in [('Main period','#147d80'),('Sparse tail','#b77a25')]:
        rows=[r for r in daily if r['period']==label]
        if not rows:continue
        x=[r['date'] for r in rows];custom=[[r['n'],r['l'],r['rate']] for r in rows]
        fig.add_trace(go.Bar(x=x,y=[r['l'] for r in rows],name=label,marker_color=color,customdata=custom,hovertemplate='%{x|%d %b %Y}<br>Labels: %{y:,}<br>All payments: %{customdata[0]:,}<extra>'+label+'</extra>'),row=1,col=1)
        fig.add_trace(go.Scatter(x=x,y=[r['rate'] for r in rows],name=label,mode='lines+markers',line=dict(color=color,width=2),marker=dict(size=5),connectgaps=False,customdata=custom,showlegend=False,hovertemplate='%{x|%d %b %Y}<br>Rate: %{y:.4%}<br>Labels: %{customdata[1]:,}<br>All payments: %{customdata[0]:,}<extra>'+label+'</extra>'),row=2,col=1)
        fig.add_trace(go.Bar(x=x,y=[r['n'] for r in rows],name=label,marker_color=color,opacity=.45,showlegend=False,hovertemplate='%{x|%d %b %Y}<br>All payments: %{y:,}<extra>'+label+'</extra>'),row=3,col=1)
    if any(r['period']=='Sparse tail' for r in daily):
        fig.add_vrect(x0=max(daily[0]['date'],TAIL_START.isoformat()),x1=(date.fromisoformat(daily[-1]['date'])+timedelta(days=1)).isoformat(),fillcolor='#e8bf76',opacity=.16,line_width=0,layer='below',row='all',col=1)
    chart_style(fig,530);fig.update_layout(showlegend=True,legend=dict(orientation='h',y=1.17,x=0),margin=dict(l=20,r=18,t=65,b=35),bargap=.2)
    fig.update_annotations(font=dict(size=12,color='#526f80'),xanchor='left',x=0)
    fig.update_yaxes(rangemode='tozero',tickformat=',d',row=1,col=1);fig.update_yaxes(rangemode='tozero',tickformat='.2%',row=2,col=1);fig.update_yaxes(rangemode='tozero',tickformat='~s',row=3,col=1)
    fig.update_xaxes(type='date',tickformat='%d %b',showgrid=False)
    return fig
