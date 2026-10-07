"""Generate the Task 1 walkthrough of saved CLI results; never run a model."""
import argparse
from pathlib import Path
from textwrap import dedent

import nbformat as nbf


ROOT = Path(__file__).resolve().parents[1]


def build_notebook():
    def md(source):
        return nbf.v4.new_markdown_cell(dedent(source).strip())

    def code(source):
        source = dedent(source).strip()
        compile(source, "Task 1 results cell", "exec")
        return nbf.v4.new_code_cell(source)

    nb = nbf.v4.new_notebook()
    nb.cells = [
        md("""
        # Task 1 — Organizational memory from the completed CLI runs

        This is the main Task 1 results walkthrough. I generated the memory with the
        command-line pipeline: **Luna judged the base episodes, facts and outcomes;
        Astra synthesized only the patterns.** This notebook reads that completed
        result from `artifacts/memory/memory.json` and demonstrates the five Task 1
        capabilities: episodes, facts/outcomes, patterns, recall and retention.

        **Run all cells without provider access.** The executable cells make no model
        calls, rebuild no memory, and write no artifacts. They need the committed memory
        and Python modules, not `KEP_2026.json`, credentials, provider caches or old runs.
        Saved cell outputs make the result inspectable without executing the notebook.

        [Methodology](METHODOLOGY.md#task-1-organizational-memory-methodology) explains
        the design and trade-offs. [Data understanding](DATA_UNDERSTANDING.md) connects
        source-data problems to safeguards and surviving errors. Examples here are
        selected development inspections, not an independently labeled quality benchmark.
        """),
        md(r"""
        ## 1. CLI workflow used to generate `memory.json`

        The generation stages were `run_task1.py` followed by `run_abstraction.py`.
        The saved metadata records the models, batch size, reasoning effort, packet cap,
        cache locations and completed coverage. It does **not** retain the original shell
        command lines. The following commands reconstruct the recorded configuration and
        historical output paths; they are not a verbatim shell-history transcript.

        **Stage A — Luna base memory.** Review the full graph with one candidate per
        batch, then construct episodes, facts, outcome assessments and retention decisions.
        The final saved invocation had a 300-call allowance. The run resumed across
        invocations and records 838 cumulative requests; 300 was not the total build cost.

        ```bash
        MEMORY_CACHE_DIR=artifacts/cache-production-batch1 \
        MEMORY_CODEX_REASONING_EFFORT=medium \
        python run_task1.py \
          --input KEP_2026.json \
          --mode hosted --provider codex --model gpt-5.6-luna \
          --batch-size 1 --max-calls 300 --max-packet-chars 100000 \
          --output artifacts/hosted/codex/gpt-5.6-luna/judge-v1/production-batch1
        ```

        Rerunning with unchanged settings and cache resumes validated judgments. Proceed
        to Stage B only after the base has completed and written `memory.json`, rather
        than `memory.incomplete.json`. A fresh build can require multiple invocations;
        do not interpret one successful pilot as full-graph completion.

        **Stage B — Astra pattern synthesis.** Read the completed Luna base and use the
        four configured question areas to compare evidence across records. This preserves
        the base and adds the pattern layer. The selected run records 23 synthesis calls.

        ```bash
        MEMORY_CACHE_DIR=artifacts/cache \
        python run_abstraction.py \
          --memory artifacts/hosted/codex/gpt-5.6-luna/judge-v1/production-batch1/memory.json \
          --questions config/abstraction_questions.json \
          --provider codex --model gpt-6-astra --max-calls 40 \
          --output artifacts/abstraction-gpt-6-astra
        ```

        The abstraction CLI sets medium reasoning. Its historical call allowance is not
        retained in the selected artifact; `40` above is the script's default allowance,
        not a claim that 40 calls were used. `--dry-run` inspects the plan without calls.

        **Submission location.** The completed Stage B directory was subsequently renamed
        from `artifacts/abstraction-gpt-6-astra/` to **`artifacts/memory/`**. The JSON files
        were unchanged. The final memory therefore contains both the Luna-built base
        and Astra-generated patterns; it is not an Astra-only extraction.

        These are documentation-only shell blocks. Rebuilding requires the supplied raw
        graph and provider authentication. For a new reproduction, use fresh output and
        cache directories under `artifacts/rebuild/`, pass the new base path to Stage B,
        and preserve the submitted snapshot. New model generations need not be identical.
        """),
        md("""
        ## 2. Load the selected artifact

        Install `requirements.txt` and select that environment as the notebook kernel.
        Run from the repository root (or a subdirectory). The tables below are computed
        from the saved JSON. Quotations are displayed verbatim and escaped as text.
        """),
        code(r"""
        from collections import Counter
        import hashlib
        import html
        import json
        from pathlib import Path
        import sys
        from IPython.display import display, HTML, Markdown

        ROOT = next((p for p in (Path.cwd(), *Path.cwd().parents)
                     if (p / 'artifacts/memory/memory.json').is_file()
                     and (p / 'org_memory').is_dir()), None)
        if ROOT is None:
            raise FileNotFoundError('Run from the repository containing artifacts/memory/memory.json.')
        sys.path.insert(0, str(ROOT))
        from org_memory import get_item, RecallIndex, validate_memory

        MEMORY_PATH = ROOT / 'artifacts/memory/memory.json'
        original_sha256 = hashlib.sha256(MEMORY_PATH.read_bytes()).hexdigest()
        memory = json.loads(MEMORY_PATH.read_text())
        base = memory['build_metadata']
        abstraction = memory['abstraction_metadata']

        def show_table(rows):
            rows = list(rows)
            if not rows:
                display(Markdown('_No rows._'))
                return
            columns = list(dict.fromkeys(k for row in rows for k in row))
            def text(value):
                if value is None:
                    return 'unknown / unscored'
                if isinstance(value, (dict, list)):
                    return json.dumps(value, ensure_ascii=False)
                return str(value)
            head = '<tr>' + ''.join('<th>' + html.escape(c) + '</th>' for c in columns) + '</tr>'
            body = ''.join('<tr>' + ''.join('<td>' + html.escape(text(row.get(c))) + '</td>'
                                          for c in columns) + '</tr>' for row in rows)
            display(HTML('<div class="task1-results"><table>' + head + body + '</table></div>'))

        def show_evidence(evidence_ids):
            rows = []
            for eid in dict.fromkeys(evidence_ids):
                e = memory['evidence'][eid]
                rows.append({'evidence_id': eid, 'record': e['record_id'],
                             'provenance': e['provenance']['kind'], 'relation': e['relation'],
                             'original text': e['source_span'] or e['provenance'].get('rationale', '')})
            show_table(rows)

        display(HTML('<style>.task1-results{overflow-x:auto;margin:12px 0}'
                     '.task1-results table{border-collapse:collapse;font-size:13px}'
                     '.task1-results th,.task1-results td{border:1px solid #ccc;padding:8px;'
                     'text-align:left;vertical-align:top;white-space:pre-wrap;'
                     'min-width:100px;max-width:520px;overflow-wrap:anywhere}'
                     '.task1-results th{background:#edf2f7;color:#18232f}</style>'))
        show_table([{'artifact': str(MEMORY_PATH.relative_to(ROOT)),
                     'schema': memory['schema_version'], 'SHA-256': original_sha256}])
        """),
        md("""
        ## 3. Validate completion and inspect provenance

        Validation replays stored judgments and checks raw evidence integrity, citations,
        base preservation and pattern construction. It does not call a provider or establish
        semantic correctness. This checks the archive stored in the memory; an independent
        comparison with the supplied raw graph is an additional, optional check below.

        The base metadata still reports zero patterns because it describes Stage A.
        The actual `patterns` collection and `abstraction_metadata` describe Stage B.
        """),
        code("""
        assert memory['schema_version'] == '3.1'
        assert base['status'] == 'complete' and base['scope'] == 'full_graph'
        assert abstraction['status'] == 'complete' and abstraction['execution_scope'] == 'production'
        validation = validate_memory(memory, raise_on_error=True)
        show_table([validation])
        show_table([
            {'stage': 'Base episodes, facts and outcomes', 'CLI': 'run_task1.py',
             'model': base['hosted_model'], 'provider': base['hosted_provider'],
             'reasoning': base['hosted_reasoning_effort'],
             'batch size': base['config']['llm_batch_size'], 'status': base['status'],
             'processed': base['coverage']['reviewed_candidates'],
             'planned': base['coverage']['selected_candidates']},
            {'stage': 'Pattern synthesis', 'CLI': 'run_abstraction.py',
             'model': abstraction['settings']['model'], 'provider': abstraction['settings']['provider'],
             'reasoning': abstraction['settings']['reasoning_effort'],
             'batch size': 'evidence bundles per synthesis packet', 'status': abstraction['status'],
             'processed': abstraction['coverage']['processed_packets'],
             'planned': abstraction['coverage']['planned_packets']},
        ])
        show_table([{'collection': k, 'count': len(memory[k])}
                    for k in ('nodes', 'evidence', 'episodes', 'facts', 'outcome_assessments', 'patterns')])
        show_table([{'evidence kind': k, 'count': v}
                    for k, v in sorted(Counter(e['provenance']['kind'] for e in memory['evidence'].values()).items())])
        """),
        md("""
        ## 4. Episodes: preserve an incident and its evidence

        The government-tenant example separates the reported absence of narrative updates,
        timeout behavior, and intervention from unverified causal claims. Episode grouping
        and retention were judged by Luna. Titles come from unverified graph labels;
        approval of a group does not verify every attached passage or relation.
        The archive below includes inferred context, explicitly labeled as such.
        """),
        code("""
        episode = next(e for e in memory['episodes'] if 'KEP-6969' in e['record_ids'])
        show_table([{k: episode[k] for k in ('id', 'record_ids', 'title', 'title_origin',
                                            'retention', 'retention_reason', 'uncertainties')}])
        show_table([{'claim': c['text'], 'status': c['status'], 'evidence_ids': c['evidence_ids']}
                    for c in episode['claims']])
        show_evidence(episode['evidence_ids'])
        """),
        md("""
        ## 5. Facts and outcomes: distinguish reports from prescriptions

        A retained historical statement reports what a source says happened. Requirements
        and documented routines describe prescribed behavior; they do not prove execution.
        These three selected facts show those distinctions with their source references.
        Labels below are stored model judgments, not independently adjudicated truth.
        """),
        code("""
        show_table([{'fact kind': k, 'count': v}
                    for k, v in sorted(Counter(f['kind'] for f in memory['facts']).items())])
        fact_ids = ['fact_1d79bf4d32849728', 'fact_001b9d9caf7ebb77', 'fact_b539b2b4cbe85407']
        selected_facts = [get_item(memory, fid) for fid in fact_ids]
        show_table([{k: f[k] for k in ('id', 'kind', 'statement', 'record_ids', 'entity_ids', 'uncertainties')}
                    for f in selected_facts])
        show_evidence([eid for f in selected_facts for eid in f['evidence_ids']])

        show_table([{'observed': observed, 'valence': valence, 'count': count}
                    for (observed, valence), count in sorted(Counter(
                        (o['observed'], o['valence']) for o in memory['outcome_assessments']).items())])
        selected_outcomes = [
            next(o for o in memory['outcome_assessments'] if o['method'] == 'exact_administrative_guard'),
            next(o for o in memory['outcome_assessments'] if 'KEP-6969' in o['record_ids']),
        ]
        show_table([{k: o[k] for k in ('id', 'record_ids', 'observed', 'valence', 'impact',
                                      'signed_impact', 'reason', 'causal_attribution')}
                    for o in selected_outcomes])
        show_evidence([eid for o in selected_outcomes for eid in o['evidence_ids']])
        """),
        md("""
        `status: Done` is administrative closure, not proof of successful recovery. An
        observed harmful outcome above means the source reports harm. The signed impact
        is an ordinal sign × scope weight (local=1, service=2, customer=3), not measured
        business value. Mixed and unknown results remain unscored. A `PRODUCES` edge does
        not establish causality between an intervention and an outcome.

        ## 6. Patterns: Astra compares the completed Luna base

        The final 46 patterns consist of reported recurrences, hypothesized mechanisms
        and prescribed routines. Inspect all three categories below. Each pattern has
        exact support, links to episodes/facts, comparison insight, counterevidence and
        uncertainty. A structural support-group count is a conservative proxy for
        independent occurrences, not proof of independence or causal validity.
        """),
        code("""
        show_table([{'pattern kind': k, 'count': v}
                    for k, v in sorted(Counter(p['kind'] for p in memory['patterns']).items())])
        pattern_ids = ['pattern_780a6edcbfcaacb4', 'pattern_a1665b6ced1f35a6', 'pattern_f4d689e47e00fa12']
        for pid in pattern_ids:
            pattern = get_item(memory, pid)
            display(Markdown('### ' + pattern['kind'].replace('_', ' ')))
            show_table([{k: pattern[k] for k in ('id', 'statement', 'comparison_insight',
                        'differences_counterevidence', 'uncertainty', 'usefulness',
                        'independent_support_count', 'supporting_episode_ids', 'supporting_fact_ids')}])
            display(Markdown('**Supporting source passages**'))
            show_evidence(pattern['evidence_ids'])
            display(Markdown('**Counterevidence / qualifying source passages**'))
            show_evidence(pattern['counterevidence_evidence_ids'])
        """),
        md("""
        ### What the pattern stage covered and rejected

        Synthesis is question-focused: four investigation areas route selected evidence
        bundles into packets. Completion means all planned packets were processed; it
        does not mean exhaustive discovery across the organization. Primary and context
        sets can overlap, so their sizes should not be summed as disjoint coverage.
        The rejected proposal below illustrates that a plausible comparison can fail the
        admission contract; rejection is not proof that its underlying events are false.
        """),
        code("""
        coverage = abstraction['coverage']
        show_table([{'question': q['question'], 'routing cues': q['cues']}
                    for q in abstraction['questions']])
        show_table([{
            'prepared bundles': coverage['total_bundles'],
            'primary bundles': len(coverage['selected_bundle_ids']),
            'context bundles': len(coverage['context_bundle_ids']),
            'omitted bundles': len(coverage['omitted_bundle_ids']),
            'processed packets': coverage['processed_packets'],
            'retained patterns': len(memory['patterns']),
            'rejected proposals': len(abstraction['rejected_proposals']),
        }])
        rejection = abstraction['rejected_proposals'][0]
        show_table([{'packet': rejection['packet_id'],
                     'proposed statement': rejection['proposal']['statement'],
                     'proposed kind': rejection['proposal']['kind'], 'reason': rejection['reason']}])
        display(Markdown('The full [inspection examples](artifacts/memory/inspection_examples.json), '
                         '[rejections](artifacts/memory/rejected_proposals.json) and '
                         '[coverage report](artifacts/memory/coverage.json) retain the other cases.'))
        """),
        md("""
        ## 7. Retention: reduce prominence without deleting evidence

        Of the 653 accepted episodes, 547 are retained for default recall and 106 are
        compressed. Here, compression means exclusion from default recall, while all
        source excerpts remain in the archive. It does not shorten the stored excerpts
        or implement age-based decay. Useful facts can survive a rejected episode.
        This distinction keeps low-value administrative history inspectable without
        treating it as a useful default answer.
        """),
        code("""
        retriever = RecallIndex(memory)
        inclusive_retriever = RecallIndex(memory, include_compressed=True)
        show_table([{'episode retention': k, 'count': v}
                    for k, v in sorted(Counter(e['retention'] for e in memory['episodes']).items())])
        compressed = next(e for e in memory['episodes'] if e['retention'] == 'compressed')
        assert compressed['id'] not in retriever.by_id
        assert compressed['id'] in inclusive_retriever.by_id
        assert all(eid in memory['evidence'] for eid in compressed['evidence_ids'])
        show_table([{'episode': compressed['id'], 'records': compressed['record_ids'],
                     'retention reason': compressed['retention_reason'],
                     'default recall eligible': compressed['id'] in retriever.by_id,
                     'include_compressed eligible': compressed['id'] in inclusive_retriever.by_id,
                     'preserved source passages': len(compressed['evidence_ids'])}])
        show_table([{'archived candidate groups': len(memory['archived_candidates']),
                     'archived fact proposals': len(memory['archived_facts']),
                     'all preserved evidence records': len(memory['evidence'])}])
        show_evidence(compressed['evidence_ids'])
        """),
        md("""
        ## 8. Recall from partial cues

        This portable demonstration uses **BM25 lexical recall plus bounded memory
        associations**, without the raw graph's node embeddings and without hosted
        embeddings. Scores are ranking heuristics, not calibrated confidence or evidence
        that a claim is true. Associations link patterns with supporting episodes/facts
        and scoped entities. The development cues illustrate behavior, not retrieval
        accuracy on held-out labels. Their results can differ from runs with node vectors.
        """),
        code("""
        cues = [
            'Jobs keep retrying but users see no output',
            'Pruning rules deleted but narratives remain hidden',
            'Routine API health checks',
            'Data differs between stores',
            'DocDB Elasticsearch incomplete storage and drift',
        ]
        recalls = {cue: retriever.recall(cue, limit=4) for cue in cues}
        for cue, result in recalls.items():
            display(Markdown('### ' + cue))
            show_table([{'rank': rank, 'id': r['item_id'], 'type': r['type'], 'title': r['title'],
                         'records': r['record_ids'], 'score': r['score'], 'retrieval reason': r['why']}
                        for rank, r in enumerate(result['results'], 1)])
        first = recalls[cues[0]]
        show_table([{'query': cues[0], 'base retrieval mode': first['trace']['mode'],
                     'association hop limit': first['trace']['max_hops'],
                     'score interpretation': first['trace']['score_note']}])
        best = get_item(memory, first['results'][0]['item_id'])
        display(Markdown('**Open the top item and follow its exact evidence**'))
        show_table([{'id': best['id'], 'type': best['type'], 'statement': best.get('statement', best['summary']),
                     'records': best['record_ids'], 'uncertainties': best.get('uncertainties', [])}])
        show_evidence(best['evidence_ids'])
        """),
        md("""
        ## 9. Construction cost and a known surviving error

        Report construction cost separately from notebook inspection or per-question
        answering cost. The base summary below is cumulative across resumes; the last
        invocation's smaller usage summary would undercount the completed build. Logged
        provider seconds are accumulated request latency, not an end-to-end wall-clock
        measurement. Reported usage can omit failed calls, and subscription dollar cost
        is unknown. Cached input tokens are a subset of input tokens, not an extra total.
        """),
        code("""
        cost_rows = []
        for stage, usage in [('Luna base: cumulative', base['cumulative_usage_summary']),
                             ('Astra patterns', abstraction['usage_summary'])]:
            tokens = usage['reported_new_call_tokens']
            cost_rows.append({'stage': stage, 'measured requests': usage['measured_requests'],
                              'input tokens': tokens.get('input_tokens'),
                              'cached input tokens': tokens.get('cached_input_tokens'),
                              'output tokens': tokens.get('output_tokens'),
                              'summed provider seconds': usage['elapsed_provider_seconds'],
                              'failed requests': usage['failed_requests'],
                              'estimated dollars': usage['estimated_this_run_cost_usd']})
        show_table(cost_rows)

        known_error = get_item(memory, 'fact_59af81ef6bfea7e3')
        show_table([{'fact': known_error['id'], 'statement': known_error['statement'],
                     'assigned entities': [{'id': eid, 'graph label': memory['nodes'][eid]['label']}
                                           for eid in known_error['entity_ids']],
                     'records': known_error['record_ids']}])
        show_evidence(known_error['evidence_ids'])
        """),
        md("""
        The last example is a known subject-scoping failure: the passage refers to
        `RedditPostMetadata`, but the stored fact is assigned to a Twitter resource.
        The quotation can be exact while the entity assignment is unsupported. The
        notebook preserves and exposes this error instead of silently repairing the
        frozen artifact. A passing structural check is therefore not an accuracy score.

        Other limits remain: fixed groups can conflate events; rejecting a whole excerpt
        can lose useful subclaims; prescribed routines do not prove execution; retained
        patterns have low heuristic confidence and may overstate independence or causality.
        This inspection does not establish a downstream advantage over text RAG or graph
        retrieval. That comparison belongs in Task 2. Generate its `task2_evaluation.ipynb`
        source with `python scripts/create_evaluation_notebook.py`.

        ## 10. Optional source comparison and reproduction

        To compare the memory archive with the original graph, place the supplied
        `KEP_2026.json` at the repository root and run this **validation-only** CLI:

        ```bash
        python run_task2.py --graph KEP_2026.json \\
          --memory artifacts/memory/memory.json --validate-only
        ```

        That command makes no model calls. For recall with the supplied node vectors,
        pass `graph['id2embeddings']` as the second argument to `RecallIndex`; label that
        mode explicitly. The original embedding encoder is unknown, so those vectors
        do not enable direct embedding of new question text into a known space.

        Generate or refresh this results notebook without regenerating memory:

        ```bash
        python scripts/create_task1_results_notebook.py
        python scripts/execute_notebook.py --notebook task1_results.ipynb --in-process
        ```

        The generator clears notebook outputs. The executor fills them from the saved
        artifact. `task1_hosted.ipynb` remains an optional live construction pilot; its
        execution is not required to inspect these completed results.
        """),
        code("""
        assert hashlib.sha256(MEMORY_PATH.read_bytes()).hexdigest() == original_sha256
        show_table([{'memory unchanged during inspection': True,
                     'structural validation passed': validation['passed'],
                     'base completion': base['status'], 'pattern completion': abstraction['status'],
                     'model calls in this notebook': 0}])
        """),
    ]
    for i, cell in enumerate(nb.cells):
        cell.id = f"task1-results-{i:03d}"
    nb.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12"},
        "task1_results": {"artifact_only": True, "memory": "artifacts/memory/memory.json",
                          "raw_graph_required": False, "cli_commands": "reconstructed from retained run settings"},
    }
    return nb


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'task1_results.ipynb')
    args = parser.parse_args(argv)
    nbf.write(build_notebook(), args.output)
    print(args.output)


if __name__ == '__main__':
    main()
