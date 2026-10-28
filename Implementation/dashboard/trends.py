"""Date-independent reporting windows and descriptive coverage/volume flags."""
from datetime import date,timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dashboard.presentation import chart_style

MAX_DAYS=500
LOW_DAILY_VOLUME=1000


def range_options(published_dates):
    dates=sorted(date.fromisoformat(d) for d in set(published_dates))
    if not dates:raise ValueError('No published reporting dates')
    return ['Last 7 days','Last 30 days']+(['All available'] if (dates[-1]-dates[0]).days<MAX_DAYS else [])+['Custom dates']


def date_window(published_dates,preset,start=None,end=None):
    dates=sorted(date.fromisoformat(d) for d in set(published_dates))
    if not dates:raise ValueError('No published reporting dates')
    first,latest=dates[0],dates[-1]
    if preset in ('Last 7 days','Last 30 days'):
        days=7 if preset=='Last 7 days' else 30
        a,b=max(first,latest-timedelta(days=days-1)),latest
    elif preset=='All available':a,b=first,latest
    elif preset=='Custom dates':a,b=date.fromisoformat(start),date.fromisoformat(end)
    else:raise ValueError('Unknown reporting window')
    if not first<=a<=b<=latest:raise ValueError('Choose ordered dates within the published coverage')
    if (b-a).days>=MAX_DAYS:raise ValueError('Choose at most 500 calendar days per view')
    return a.isoformat(),b.isoformat()


def daily_population(rows,start,end,published_dates,day_coverage=None):
    """Missing release dates are unknown; absent filtered rows on known dates are zero.

    Optional per-day completeness must come explicitly from the release. Low
    volume never infers incomplete ingestion and never filters records.
    """
    start,end=date.fromisoformat(start),date.fromisoformat(end)
    if start>end:raise ValueError('Reversed date range')
    published=set(published_dates);by_day={};day_coverage=day_coverage or {}
    for r in rows:
        day=str(r['event_date'])[:10]
        if day in by_day or day not in published or not start<=date.fromisoformat(day)<=end:raise ValueError('Unexpected or duplicate trend date')
        n,l=int(r['n']),int(r['l'])
        if n<0 or not 0<=l<=n:raise ValueError('Invalid daily counts')
        by_day[day]=(n,l)
    result=[];day=start
    while day<=end:
        key=day.isoformat();n,l=by_day.get(key,(0,0) if key in published else (None,None))
        coverage=day_coverage.get(key,'unknown') if key in published else 'missing'
        if coverage not in ('complete','partial','unknown','missing'):raise ValueError('Invalid published day-completeness status')
        if coverage=='missing' and key in published:raise ValueError('Published date cannot be marked missing')
        result.append({'date':key,'n':n,'l':l,'rate':l/n if n else None,'coverage':coverage,'low_volume':n is not None and n<LOW_DAILY_VOLUME})
        day+=timedelta(days=1)
    return result


def population_total(daily):
    if any(r['n'] is None for r in daily):return None,None,None
    n=sum(r['n'] for r in daily);l=sum(r['l'] for r in daily)
    return n,l,l/n if n else None


def coverage_counts(daily):
    return {key:sum(r['coverage']==key for r in daily) for key in ('missing','partial','unknown','complete')} | {'low_volume':sum(r['low_volume'] for r in daily)}


def endpoint_comparison(daily):
    if len(daily)<2:return None
    first,last=daily[0],daily[-1]
    if first['n'] is None or last['n'] is None:return 'Endpoint comparison unavailable: a selected date is outside published coverage.'
    a=f"{first['rate']:.4%}" if first['rate'] is not None else 'not measurable';b=f"{last['rate']:.4%}" if last['rate'] is not None else 'not measurable'
    text=f"First → last selected day: labelled payments {first['l']:,} → {last['l']:,} ({last['l']-first['l']:+,}); rate {a} → {b}; total payments {first['n']:,} → {last['n']:,}."
    if first['low_volume'] or last['low_volume']:text+=' Small selected populations can make rates unstable; compare the traffic counts as well.'
    if first['coverage']=='partial' or last['coverage']=='partial':text+=' An endpoint has explicitly reported partial coverage; treat the comparison as provisional.'
    return text


def trend_chart(daily):
    fig=make_subplots(rows=3,cols=1,shared_xaxes=True,vertical_spacing=.09,row_heights=[.38,.32,.30],subplot_titles=['Labelled laundering payments','Laundering rate · labels ÷ all payments','All payments · daily population'])
    colors=['#9266a8' if r['coverage']=='partial' else '#b77a25' if r['low_volume'] else '#147d80' for r in daily]
    x=[r['date'] for r in daily];custom=[[r['n'],r['l'],r['rate'],r['coverage']] for r in daily]
    fig.add_trace(go.Bar(x=x,y=[r['l'] for r in daily],marker_color=colors,customdata=custom,showlegend=False,hovertemplate='%{x|%d %b %Y}<br>Labels: %{y:,}<br>All payments: %{customdata[0]:,}<br>Completeness: %{customdata[3]}<extra></extra>'),row=1,col=1)
    fig.add_trace(go.Scatter(x=x,y=[r['rate'] for r in daily],mode='lines+markers',line=dict(color='#147d80',width=2),marker=dict(size=5,color=colors),connectgaps=False,customdata=custom,showlegend=False,hovertemplate='%{x|%d %b %Y}<br>Rate: %{y:.4%}<br>Labels: %{customdata[1]:,}<br>All payments: %{customdata[0]:,}<br>Completeness: %{customdata[3]}<extra></extra>'),row=2,col=1)
    fig.add_trace(go.Bar(x=x,y=[r['n'] for r in daily],marker_color=colors,opacity=.45,showlegend=False,hovertemplate='%{x|%d %b %Y}<br>All payments: %{y:,}<extra></extra>'),row=3,col=1)
    legend=[('Published count','#147d80')]
    if any(r['low_volume'] for r in daily):legend.append(('Low volume','#b77a25'))
    if any(r['coverage']=='partial' for r in daily):legend.append(('Partial coverage','#9266a8'))
    for label,color in legend:fig.add_trace(go.Scatter(x=[None],y=[None],mode='markers',marker=dict(color=color,size=9),name=label,showlegend=True),row=1,col=1)
    chart_style(fig,530);fig.update_layout(showlegend=True,legend=dict(orientation='h',y=1.17,x=0),margin=dict(l=20,r=18,t=65,b=35),bargap=.2)
    fig.update_annotations(font=dict(size=12,color='#526f80'),xanchor='left',x=0)
    fig.update_yaxes(rangemode='tozero',tickformat=',d',row=1,col=1);fig.update_yaxes(rangemode='tozero',tickformat='.2%',row=2,col=1);fig.update_yaxes(rangemode='tozero',tickformat='~s',row=3,col=1)
    fig.update_xaxes(type='date',tickformat='%d %b',showgrid=False)
    return fig
