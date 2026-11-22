import time, os, sys
import pandas as pd
from model import run_exp, default_params

t0=time.time()
valid=set(pd.read_csv('./Completeness_783.csv').iloc[:,0])
neu=[720575940624963786,720575940630233916,720575940637568838,720575940638202345,
     720575940617000768,720575940630797113,720575940632889389,720575940621754367,
     720575940621502051,720575940640649691,720575940639332736,720575940616885538,
     720575940639198653,720575940620900446,720575940617937543,720575940632425919,
     720575940633143833,720575940612670570,720575940628853239,720575940629176663,
     720575940611875570]
neu=[n for n in neu if n in valid]
print("有效糖神经元:",len(neu),"读表耗时 %.1fs"%(time.time()-t0), flush=True)

os.makedirs('./results/bench', exist_ok=True)
config=dict(path_res='./results/bench', path_comp='./Completeness_783.csv',
            path_con='./Connectivity_783.parquet', n_proc=-1)
params=dict(default_params); params['n_run']=1; params['t_run']=200*ms if False else params['t_run']

t1=time.time()
run_exp(exp_name='bench1', neu_exc=neu, **config)
print("1 次试验(1s 脑时间) 耗时 %.1f 秒"%(time.time()-t1), flush=True)
print("输出:", os.listdir('./results/bench'))
