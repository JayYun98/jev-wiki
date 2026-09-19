#!/usr/bin/env python3
"""Offline full-rescan estimate; assumptions and implementation limits in README."""
import json
from decimal import Decimal as D, getcontext, ROUND_HALF_UP
from pathlib import Path

getcontext().rounding = ROUND_HALF_UP
ROOT = Path(__file__).resolve().parents[1]
PRICES = json.loads((ROOT / 'references/cost-pricing.json').read_text())


def charge(endpoint, inputs, outputs=0):
    p = endpoint['pricing_per_token']
    return D(inputs) * D(p['prompt']) + D(outputs) * D(p['completion'])


def estimate(writer, jev, added, existing=1000, scope='domain'):
    """Round-robin arrivals, five balanced domains, growing retained corpus."""
    scan_tokens = {'llm_only': 0, 'llm_jev': 0}
    scan_calls = {'llm_only': 0, 'llm_jev': 0}
    for total in range(existing, existing + added):
        # The next round-robin domain has floor(total / 5) existing documents.
        documents = total // 5 if scope == 'domain' else total
        for key, batch in [('llm_only', 12), ('llm_jev', 2)]:
            calls = (documents + batch - 1) // batch
            scan_calls[key] += calls
            scan_tokens[key] += documents * 2000 + calls * 2500
    # Equal writing, final plan consolidation, three verification calls per arrival.
    writing = charge(writer, added * 13000, added * 2000)
    llm = writing + charge(writer, added * 13500 + scan_tokens['llm_only'],
                           added * 750 + scan_calls['llm_only'] * 300)
    hybrid = writing + charge(jev, added * 13500 + scan_tokens['llm_jev'])
    return {'llm_only': llm, 'llm_jev': hybrid, 'scan_calls': scan_calls,
            'scan_input_tokens': scan_tokens}


def checks():
    w, j = PRICES['endpoints'][0], PRICES['endpoints'][-1]
    assert estimate(w, j, 0)['llm_only'] == 0
    r = estimate(w, j, 1, existing=10)
    assert r['scan_input_tokens'] == {'llm_only': 6500, 'llm_jev': 6500}
    assert r['scan_calls'] == {'llm_only': 1, 'llm_jev': 1}
    assert r['llm_only'] == D('0.005876')
    assert r['llm_jev'] == D('0.00357')
    assert estimate(w, j, 5, existing=0)['scan_calls']['llm_jev'] == 0
    assert estimate(w, j, 1, existing=10, scope='all')['scan_input_tokens']['llm_jev'] == 32500


def rows(writer, scope='domain'):
    j = PRICES['endpoints'][-1]
    initial = estimate(writer, j, 1000, 0, scope)
    yield 'Initial 1,000', initial
    for added in (100, 500, 1000):
        yield f'Month 1 +{added:,}', estimate(writer, j, added, 1000, scope)
        yield f'Month 12 +{added:,}', estimate(writer, j, added, 1000 + 11 * added, scope)
        recurring = estimate(writer, j, 12 * added, 1000, scope)
        yield f'Year 1 +{added:,}/mo', {k: initial[k] + recurring[k] for k in ('llm_only','llm_jev')}


def chart():
    """Optional documentation build; matplotlib is not a runtime dependency."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.5))
    fig.patch.set_facecolor('#fafaf7')
    for ax, writer, name in zip(axes, PRICES['endpoints'][:-1], ['DeepSeek V4.1 Flash', 'Qwen3.8 Flash']):
        ax.set_facecolor('#fafaf7')
        data = dict(rows(writer))
        keys = ['Initial 1,000','Month 1 +100','Month 1 +500','Month 1 +1,000','Month 12 +1,000']
        for offset, key, label, color in [(-.16,'llm_only','LLM only','#778397'),(.16,'llm_jev','Same LLM + Jev','#178472')]:
            values = [data[k][key] for k in keys]
            bars=ax.barh([i+offset for i in range(len(keys))],[float(v) for v in values],height=.28,color=color,label=label,zorder=3)
            ax.bar_label(bars,labels=[f'${v:,.2f}' for v in values],padding=5,fontsize=10)
        ax.set_yticks(range(len(keys)),keys,fontsize=10)
        ax.invert_yaxis();ax.set_xlim(0,1000)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v,_:f'${v:,.0f}'))
        ax.grid(axis='x',alpha=.15,zorder=0)
        ax.spines[['top','right','left']].set_visible(False)
        ax.set_title(name,loc='left',fontsize=14,fontweight='bold',pad=18)
        ax.set_xlabel('Estimated API cost, USD')
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper left',bbox_to_anchor=(.04,.91),ncol=2,frameon=False)
    fig.suptitle('Read the whole domain again on every arrival',x=.045,y=.98,ha='left',fontsize=22,fontweight='bold')
    fig.text(.045,.035,'1,000 starting documents / 5 domains. Corpus grows each month; 2,000 retained tokens per document.\n'
             'LLM scan batches: 12 documents; Jev: 2. Both include writing and verification. Hypothetical rescan workflow, not shipped runtime.\n'
             'OpenRouter snapshot: 2026-09-20 KST. No cache discounts. Excludes queries, extra retries and infrastructure.',fontsize=10,linespacing=1.5)
    fig.subplots_adjust(left=.15,right=.94,top=.80,bottom=.20,wspace=.6)
    for ext in ('png','svg'):
        fig.savefig(ROOT/'assets'/f'cost-comparison.{ext}',dpi=160,facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__ == '__main__':
    import sys
    checks()
    if '--chart' in sys.argv:
        chart()
    else:
        for w in PRICES['endpoints'][:-1]:
            print(w['model'])
            for scope in ('domain','all'):
                print(scope)
                for label,r in rows(w,scope):
                    print(label, {k:f'${r[k]:,.2f}' for k in ('llm_only','llm_jev')})
            for existing,added in [(10000,10000),(100000,10000),(100000,100000)]:
                r=estimate(w,PRICES['endpoints'][-1],added,existing)
                print('Enterprise',existing,added,{k:f'${r[k]:,.2f}' for k in ('llm_only','llm_jev')},r['scan_calls'])
