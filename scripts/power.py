import numpy as np
from scipy import stats
rng=np.random.default_rng(20261113)
def logit(p): return np.log(p/(1-p))
def sim(N, base, delta, sd_p=0.8, sd_i=1.0, n_items=16, per_view=4, reps=2000):
    b0=logit(base); b1=logit(base+delta)-b0
    hits=0
    for _ in range(reps):
        items=rng.normal(0,sd_i,n_items)
        diffs=[]
        for p in range(N):
            u=rng.normal(0,sd_p)
            idx=rng.permutation(n_items)[:2*per_view]
            con=idx[:per_view]; vis=idx[per_view:]
            pc=1/(1+np.exp(-(b0+u+items[con]))); pv=1/(1+np.exp(-(b0+b1+u+items[vis])))
            yc=rng.random(per_view)<pc; yv=rng.random(per_view)<pv
            diffs.append(yv.mean()-yc.mean())
        t,pval=stats.ttest_1samp(diffs,0)
        hits+= (pval<0.05 and np.mean(diffs)>0)
    return hits/reps
for base in (0.40,):
    for delta in (0.10,0.15,0.20):
        print('base %.2f delta +%.2f :'%(base,delta), ' '.join('N=%d: %.2f'%(N,sim(N,base,delta)) for N in (24,32,40)))
