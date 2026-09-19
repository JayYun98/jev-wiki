#!/usr/bin/env python3
"""Offline planning estimate; not measured workload usage. See README assumptions."""
import json
from decimal import Decimal as D, getcontext, ROUND_HALF_UP
from pathlib import Path

getcontext().rounding = ROUND_HALF_UP

PRICES = json.loads((Path(__file__).resolve().parents[1] / 'references/cost-pricing.json').read_text())


def charge(endpoint, inputs, outputs=0):
    pricing = endpoint['pricing_per_token']
    return D(inputs) * D(pricing['prompt']) + D(outputs) * D(pricing['completion'])


def estimate(writer, jev, documents, lint_pairs, scale=1):
    # Shared extraction + three page drafts: 2,500 + 3*3,500 in; 500 + 3*500 out.
    writing = charge(writer, 13000 * scale, 2000 * scale) * documents
    # Planning + three grounding checks: 4,500 + 3*3,000 in; 300 + 3*150 out.
    baseline = writing + charge(writer, 13500 * scale, 750 * scale) * documents
    hybrid = writing + charge(jev, 13500 * scale) * documents
    baseline += charge(writer, 2000 * scale, 100 * scale) * lint_pairs
    hybrid += charge(jev, 2000 * scale) * lint_pairs
    # Optimistic fused baseline: decisions piggyback on writing, no separate checks/lint.
    return {'llm_led': baseline, 'jev_hybrid': hybrid, 'fused_writer_only': writing}


def main():
    writers, jev = PRICES['endpoints'][:-1], PRICES['endpoints'][-1]
    assert charge(jev, 1000000) == D('0.042')
    assert estimate(writers[0], jev, 0, 0) == dict.fromkeys(
        ('llm_led', 'jev_hybrid', 'fused_writer_only'), D(0))
    for writer in writers:
        print('\n' + writer['model'])
        initial = estimate(writer, jev, 1000, 20)
        for label, docs, pairs in [('Initial 1000', 1000, 20), ('Monthly +100', 100, 80),
                                   ('Monthly +500', 500, 80), ('Monthly +1000', 1000, 80)]:
            values = estimate(writer, jev, docs, pairs)
            # One thousand docs must cost ten times one hundred when lint is zero.
            assert estimate(writer, jev, 1000, 0)['jev_hybrid'] == 10 * estimate(writer, jev, 100, 0)['jev_hybrid']
            savings = (1 - values['jev_hybrid'] / values['llm_led']) * 100
            print(label, {k: f'${v:.2f}' for k, v in values.items()}, f'saving={savings:.1f}%')
            if label.startswith('Monthly'):
                print('Year 1', {k: f'${initial[k] + 12*v:.2f}' for k, v in values.items()})
        print('Monthly +500, 0.5x/2x/5x tokens', [
            {k: f'${v:.2f}' for k, v in estimate(writer, jev, 500, 80, scale).items()}
            for scale in (D('0.5'), D(2), D(5))])


if __name__ == '__main__':
    main()
