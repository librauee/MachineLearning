# -*- coding: utf-8 -*-
"""
Created on Sun Feb 24 18:06:52 2019

@author: Administrator
"""
import numpy as np
import sklearn.cluster as skc
from sklearn import metrics
import matplotlib.pyplot as plt
#数据包括用户ID，设备的MAC地址，IP地址，开始上网时间，停止上网时间，上网时长，校园网套餐等
 
mac2id=dict()
onlinetimes=[]

#读取每条数据中的mac地址，开始上网时间，上网时长
f=open('TestData.txt',encoding='utf-8')
for line in f:
    mac=line.split(',')[2]
    onlinetime=int(line.split(',')[6])
    starttime=int(line.split(',')[4].split(' ')[1].split(':')[0])
    if mac not in mac2id:
        mac2id[mac]=len(onlinetimes)
        onlinetimes.append((starttime,onlinetime))
    else:
        onlinetimes[mac2id[mac]]=[(starttime,onlinetime)]
#mac2id是一个字典：key是mac地址,value是对应mac地址的上网时长以及开始上网时间
real_X=np.array(onlinetimes).reshape((-1,2))
 
X=real_X[:,0:1]

print(real_X)
print(X)
db=skc.DBSCAN(eps=0.01,min_samples=20).fit(X)
labels = db.labels_
 
print('Labels:')
print(labels)
raito=len(labels[labels[:] == -1]) / len(labels)
print('Noise raito:',format(raito, '.2%'))
 
n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)
 
print('Estimated number of clusters: %d' % n_clusters_)
print("Silhouette Coefficient: %0.3f"% metrics.silhouette_score(X, labels))
 
for i in range(n_clusters_):
    print('Cluster ',i,':')
    print(list(X[labels == i].flatten()))
     
plt.hist(X,24)
plt.show()
