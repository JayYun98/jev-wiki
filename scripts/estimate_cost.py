#!/usr/bin/env python3
"""Offline full-rescan estimate; full-rescan planning scenario; not measured runtime usage."""
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
    matplotlib.rcParams['text.parse_math'] = False
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter, MaxNLocator
    writer = next(p for p in PRICES['endpoints'] if p['model'] == 'qwen/qwen3.8-flash')
    jev = PRICES['endpoints'][-1]
    initial = estimate(writer, jev, 1000, 0)
    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    fig.patch.set_facecolor('#fafaf7')
    months = list(range(1, 13))
    for col, added in enumerate((100, 500, 1000)):
        results = [estimate(writer, jev, added, 1000 + (m-1)*added) for m in months]
        for key, label, color, style in [('llm_only','Qwen only','#69788f','--'),
                                         ('llm_jev','Qwen + Jev','#11836f','-')]:
            monthly = [float(r[key]) for r in results]
            running = initial[key]
            cumulative = []
            for result in results:
                running += result[key]
                cumulative.append(float(running))
            for row, values in enumerate((monthly,cumulative)):
                ax=axes[row,col]
                ax.plot(months,values,color=color,linestyle=style,marker='o',markersize=3,
                        linewidth=2.5,label=label)
                ax.annotate(f'${values[-1]:,.0f}',(12,values[-1]),xytext=(6,0),
                            textcoords='offset points',va='center',color=color,fontweight='bold',fontsize=10)
        for row in (0,1):
            ax=axes[row,col];ax.set_facecolor('#fafaf7')
            ax.set_xlim(.6,15);ax.set_ylim(bottom=0)
            ax.set_xticks([1,3,6,9,12]);ax.set_xlabel('Month')
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v,_:f'${v:,.0f}'))
            ax.yaxis.set_major_locator(MaxNLocator(nbins=5))
            ax.grid(alpha=.15);ax.spines[['top','right']].set_visible(False)
            ax.set_title(f'+{added:,} documents / month',loc='left',fontweight='bold',pad=12)
        axes[0,col].set_ylabel('This month · USD')
        axes[1,col].set_ylabel('Cumulative incl. setup · USD')
    handles,labels=axes[0,0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper left',bbox_to_anchor=(.055,.935),ncol=2,frameon=False,fontsize=12)
    fig.suptitle('Qwen alone or Qwen + Jev: the full first year',x=.06,y=.985,
                 ha='left',fontsize=23,fontweight='bold',color='#20322e')
    fig.text(.06,.865,'MONTHLY BILL  /  12 points per line; vertical scales differ by scenario',fontsize=11,fontweight='bold',color='#47554f')
    fig.text(.06,.465,'RUNNING TOTAL  /  includes the initial build: Qwen $39.64 · Qwen + Jev $17.07',fontsize=11,fontweight='bold',color='#47554f')
    fig.text(.06,.025,'Full-domain rescan per arrival · 1,000 starting documents · 5 domains · 2,000 retained tokens/document\n'
             'Estimated API costs, not measured bills. OpenRouter snapshot: Sep 20, 2026 KST. No cache discounts.\n'
             'Includes writing + checks; excludes queries and infrastructure. Hypothetical rescan workflow, not runtime capacity.',
             fontsize=10,color='#47554f',linespacing=1.5)
    fig.subplots_adjust(left=.07,right=.96,top=.81,bottom=.14,wspace=.32,hspace=.60)
    for ext in ('png','svg'):
        fig.savefig(ROOT/'assets'/f'cost-comparison.{ext}',dpi=160,facecolor=fig.get_facecolor())
    svg = ROOT/'assets'/'cost-comparison.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
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
