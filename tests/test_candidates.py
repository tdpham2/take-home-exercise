import copy
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from org_memory.candidates import build_candidates
from org_memory.evidence import index_graph, normalize_index


def edge(source='d1', target='r1', *, source_type='decision', target_type='resource',
         relation='AFFECTS', record='R1', text='The service failed.', kind='extracted'):
    provenance = {'kind': kind, 'record_id': record, 'source_span': text} if kind == 'extracted' else {'kind': kind, 'rationale': text}
    return {'source': {'id': source, 'type': source_type, 'label': source},
            'target': {'id': target, 'type': target_type, 'label': target},
            'relation': {'type': relation, 'record_id': record, 'provenance': json.dumps(provenance)}}


def graph(edges):
    return {'graph': edges, 'id2embeddings': {e[side]['id']: [0.] * 512 for e in edges for side in ('source', 'target')}}


def test_hosted_never_calls_semantic_annotations_and_preserves_archives():
    data = graph([edge(), edge(text='2026-04-19', kind='inferred'), edge(text='')])
    original = copy.deepcopy(data)
    with patch('org_memory.evidence.classify_evidence', side_effect=AssertionError), patch('org_memory.evidence.quality_flags', side_effect=AssertionError):
        hosted = index_graph(data, annotate_offline=False)
    offline = index_graph(data)
    assert data == original
    assert hosted['nodes'] == offline['nodes']
    for eid, e in hosted['evidence'].items():
        assert 'status' not in e and 'quality_flags' not in e
        assert e['raw_edge'] == offline['evidence'][eid]['raw_edge']
    assert next(e for e in hosted['evidence'].values() if e['provenance']['kind'] == 'inferred')['dates'][0]['status'] == 'tentative_inference'


def test_supplied_indexes_are_copied_normalized_and_validated():
    data = graph([edge()])
    offline = index_graph(data)
    original = copy.deepcopy(offline)
    with patch('org_memory.evidence.classify_evidence', side_effect=AssertionError):
        hosted = normalize_index(data, offline, annotate_offline=False)
    assert offline == original
    assert all('status' not in e for e in hosted['evidence'].values())
    assert normalize_index(data, hosted, annotate_offline=True) == offline
    changed = copy.deepcopy(offline)
    changed['outgoing'] = {}
    with pytest.raises(ValueError, match='differs'):
        normalize_index(data, changed, annotate_offline=False)


def test_resources_do_not_merge_but_extracted_dependencies_do():
    data = graph([edge(), edge('d2', record='R2'), edge('d1', 'd2', target_type='decision', relation='DEPENDS_ON', kind='inferred')])
    c, u, _ = build_candidates(index_graph(data, False))
    assert len(c) == len(u) == 2
    data['graph'][-1] = edge('d1', 'd2', target_type='decision', relation='DEPENDS_ON')
    c, u, _ = build_candidates(index_graph(data, False))
    assert len(c) == len(u) == 1


def test_shared_events_cross_record_join_only_review_units():
    data = graph([edge('d1', 'e', target_type='event'), edge('d2', 'e', target_type='event', record='R2')])
    c, u, _ = build_candidates(index_graph(data, False))
    assert len(c) == 2 and len(u) == 1
    same = graph([edge('d1', 'e', target_type='event'), edge('d2', 'e', target_type='event')])
    assert len(build_candidates(index_graph(same, False))[0]) == 1


def test_eight_decision_cap_and_nonempty_extracted_support():
    data = graph([edge(f'd{i}', f'd{i+1}', target_type='decision', relation='CAUSES') for i in range(9)])
    c, u, _ = build_candidates(index_graph(data, False))
    assert max(len(x['decision_ids']) for x in c) <= 8
    assert len(u) == 1
    data = graph([edge('d1', 'd2', target_type='decision', relation='DEPENDS_ON', text=''), edge('d3', text='status: Done')])
    c, u, _ = build_candidates(index_graph(data, False))
    assert len(c) == 3 and all(x['eligible'] for x in c)
    assert {eid for x in c for eid in x['evidence_ids']} == set(index_graph(data, False)['evidence'])


def test_frozen_structural_reproducibility_counts():
    data = json.loads((Path(__file__).resolve().parents[1] / 'KEP_2026.json').read_text())
    index = index_graph(data, False)
    c, u, trace = build_candidates(index)
    assert sum(x['eligible'] for x in c) == 816
    assert len(u) == 802
    assert (c, u, trace) == build_candidates(index)
    assert {d for x in c for d in x['decision_ids']} == {n for n, v in index['nodes'].items() if v['type'] == 'decision'}
    proposed, no_units, same_trace = build_candidates(index, include_review_units=False)
    assert proposed == c and not no_units and same_trace == trace


def test_broad_event_hub_does_not_arbitrarily_join_first_eight():
    data = graph([edge(f"d{i}", "event", target_type="event") for i in range(9)])
    candidates, _, traces = build_candidates(index_graph(data, False), include_review_units=False)
    assert len(candidates) == 9
    assert all(not t["joined"] for t in traces)
