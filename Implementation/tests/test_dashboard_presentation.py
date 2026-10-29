import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dashboard.presentation import graph_payload,graph_html,exposure_chart,kpis


def case_fixture():
    nodes=[{'node_id':json.dumps([str(i),f'acct-{i}']),'bank':str(i),'account':f'acct-{i}','entity_id':'same-owner' if i<2 else None,'entity_name':'Owner A' if i<2 else None} for i in range(3)]
    edges=[{'source':nodes[i]['node_id'],'target':nodes[(i+1)%3]['node_id'],'transaction_count':i+1} for i in range(3)]
    return {'pattern_type':'cycle_3','nodes':nodes,'edges':edges}


class DashboardPresentationTests(unittest.TestCase):
    def test_preview_preserves_directed_links_counts_and_same_entity_colors(self):
        case=case_fixture();prior=copy.deepcopy(case);p=graph_payload(case)
        self.assertEqual(case,prior);self.assertEqual((p['visible_accounts'],p['visible_edges']),(3,3))
        nodes={n['id']:n for n in p['nodes']};self.assertEqual(sorted(e['label'] for e in p['edges']),['1','2','3'])
        self.assertTrue(all(e['from'] in nodes and e['to'] in nodes for e in p['edges']))
        same=[n for n in p['nodes'] if 'Owner A' in n['details']];self.assertEqual(same[0]['color'],same[1]['color'])
        self.assertEqual(graph_payload(case),p)

    def test_caps_do_not_mutate_or_truncate_stored_evidence(self):
        c={'pattern_type':'fan_out','nodes':[{'node_id':str(i),'account':str(i),'bank':'1'} for i in range(110)],'edges':[{'source':str(i%100),'target':str((i+1)%100),'transaction_count':1} for i in range(700)],'evidence_transaction_count':700,'transactions':[{'source_id':str(i)} for i in range(700)]}
        prior=copy.deepcopy(c);p=graph_payload(c,False)
        self.assertLessEqual(p['visible_accounts'],100);self.assertLessEqual(p['visible_edges'],500);self.assertTrue(all(n['label']=='' for n in p['nodes']));self.assertEqual(c,prior)

    def test_raw_identifiers_cannot_escape_inline_graph_script_or_kpis(self):
        c=case_fixture();attack='</script><script>alert("x")</script>';c['nodes'][0].update(account=attack,entity_name=attack)
        markup,_=graph_html(c);self.assertNotIn(attack,markup);self.assertTrue('\\u0026lt;/script\\u0026gt;' in markup or '&lt;/script&gt;' in markup,'Graph text must remain escaped')
        self.assertNotIn('<script>alert',kpis([(attack,attack,attack)]))
        import re
        self.assertNotRegex(markup,r'<script[^>]+src=["\x27]https?://');self.assertNotRegex(markup,r'<link[^>]+href=["\x27]https?://')

    def test_reciprocal_edges_are_separated_and_full_identifiers_retrievable(self):
        c=case_fixture();c['edges'].append({'source':c['nodes'][1]['node_id'],'target':c['nodes'][0]['node_id'],'transaction_count':8})
        p=graph_payload(c);self.assertEqual(sum(isinstance(e['smooth'],dict) for e in p['edges']),2)
        self.assertTrue(all('Account acct-' in n['details'] for n in p['nodes']))

    def test_ranking_uses_supplied_rates_excludes_low_support_and_no_amount_math(self):
        rows=[{'group':'supported','n':'2000','l':'3','rate':.0015,'lift':2.3,'support':'supported','selected_currency_amount':'0.47209301'},{'group':'small','n':'2','l':'2','rate':1,'lift':1000,'support':'low_support'},{'group':'zero','n':'2000','l':'0','rate':0,'lift':0,'support':'supported'}]
        prior=copy.deepcopy(rows);f=exposure_chart(rows);self.assertEqual(list(f.data[0].y),['supported']);self.assertEqual(list(f.data[0].x),[2.3]);self.assertEqual(f.data[0].customdata[0][2],.0015);self.assertEqual(rows,prior)
        scatter=exposure_chart(rows,'Volume vs rate');self.assertEqual(scatter.layout.xaxis.type,'log');self.assertEqual(list(scatter.data[0].y),[.0015])
        self.assertIsNone(exposure_chart(rows[1:]))


if __name__=='__main__':unittest.main()
