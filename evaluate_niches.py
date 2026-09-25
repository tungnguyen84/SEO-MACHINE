import sys
sys.stdout.reconfigure(encoding='utf-8')
from saas_affiliate.diamond_hunter import DiamondNicheHunter

hunter = DiamondNicheHunter()

niches_to_test = [
    'Car Battery Jump Starter',
    'Portable Espresso Machine',
    'Under Desk Walking Pad',
    'Outdoor Pizza Oven'
]

for n in niches_to_test:
    print('=============================================')
    print('NICHE:', n)
    res = hunter.generate_blueprint(n, plan_days=7)
    print('Category Name:', res.get('category_name'))
    print('Total Keywords Found:', res.get('total_keywords_found'))
    print('Roundup Diamonds Count:', len(res.get('roundup_diamonds', [])))
    print('Review Diamonds Count:', len(res.get('review_diamonds', [])))
    print('Info Diamonds Count:', len(res.get('info_diamonds', [])))
    
    print('\nSample Scheduled Articles:')
    for s in res.get('schedule', [])[:4]:
        day = s['day_number']
        t = s['article_type']
        kw = s['keyword']
        vol = s['volume']
        kd = s['kd']
        title = s['title']
        aff = 'Affiliate' if s['has_affiliate_links'] else '100% Infor (HCU Safe)'
        print(f"  Day {day} [{t}] ({aff}) | Vol: {vol:,} | KD: {kd}% | {kw}")
        print(f"       -> Title: {title}")
