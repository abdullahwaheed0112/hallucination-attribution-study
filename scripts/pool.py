import sys, os, json, collections
root=sys.argv[1]
rows=[]
for fw in ['Magentic_One','Camel']:
    p=os.path.join(root,fw)
    for f in sorted(os.listdir(p)):
        if not f.endswith('.json'): continue
        d=json.load(open(os.path.join(p,f),encoding='utf-8'))
        if d.get('is_hallucination')!='true': continue
        h=d['history']; n=len(h)
        wc=sum(len(str(s.get('content','')).split())+len(str(s.get('tool_responses','')).split())+len(str(s.get('tool_calls','')).split()) for s in h)
        cw=sum(len(str(s.get('content','')).split()) for s in h)
        hs=int(d['hallucination_step'])
        role=[s for s in h if int(s['step'])==hs][0].get('role')
        agents=sorted(set(str(s.get('role')) for s in h))
        rows.append(dict(fw=fw,f=f,n=n,wc=wc,cw=cw,hs=hs,role=str(role),cat=d.get('hallucination_category'),q=d.get('question','')[:200],model=d.get('model_id'),nag=len(agents)))
print('positives',len(rows))
A=[r for r in rows if r['n']<=20]; print('<=20 steps',len(A))
B=[r for r in A if r['wc']<=3000]; print('<=20 steps & <=3000 words (content+tool I/O)',len(B))
C=[r for r in B if r['role'] not in ('None','')]; print('... & responsible role known',len(C))
# unique questions
seen=set(); D=[]
for r in C:
    k=r['q'].strip().lower()
    if k in seen: continue
    seen.add(k); D.append(r)
print('... & unique question',len(D))
cnt=collections.Counter((('short<=10' if r['n']<=10 else 'long11-20'),('early<=3' if r['hs']<=3 else 'later>=4')) for r in D)
print('strata (length x position):',dict(cnt))
print('by framework:',collections.Counter(r['fw'] for r in D))
print('by category:',collections.Counter(r['cat'] for r in D))
print('agents per trace:',collections.Counter(r['nag'] for r in D))
# heuristics on D
import statistics as st
first=sum(1 for r in D if r['hs']==1)/len(D)
mode_step=collections.Counter(r['hs'] for r in D).most_common(1)[0]
chance=st.mean(1/r['n'] for r in D)
print('first-step heuristic acc %.3f; most common step %s; mean chance (1/n) %.3f'%(first,mode_step,chance))
# step-3 heuristic
print('step-3 heuristic acc %.3f'%(sum(1 for r in D if r['hs']==3)/len(D)))
print('words: median',st.median(r['wc'] for r in D),'max',max(r['wc'] for r in D))
med=st.median(r['wc'] for r in D)
cnt2=collections.Counter((('words<=%d'%med if r['wc']<=med else 'words>%d'%med),('early<=3' if r['hs']<=3 else 'later>=4')) for r in D)
print('strata (words median split x position):',dict(cnt2))
print('later items by fw:',collections.Counter(r['fw'] for r in D if r['hs']>=4))
print('later items by cat:',collections.Counter(r['cat'] for r in D if r['hs']>=4))
print('early step values:',collections.Counter(r['hs'] for r in D if r['hs']<=3))
print('later step values:',sorted(collections.Counter(r['hs'] for r in D if r['hs']>=4).items()))
print('responsible agent (role) dist:',collections.Counter(r['role'] for r in D))
print('steps distribution: min',min(r['n'] for r in D),'median',st.median(r['n'] for r in D),'max',max(r['n'] for r in D))
