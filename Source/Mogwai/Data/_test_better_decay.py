from pathlib import Path
from pprint import pprint
import json
import re
import argparse

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt


SIGMA = 1.0
ALPHA = 0.2
BETA = 1.0 - ALPHA

def lerp(a, b, t):
    return a + (b-a)*t

def B(i, t, beta=BETA):
    return beta**(t-i-1)

def estimateVar(estimator, n, sigma=SIGMA):
    avgs = []
    for _ in range(1000):
        x = []
        for n_i in n:
            x.append(np.mean(np.random.normal(0, sigma, n_i)))
        weights = estimator(n)
        avgs.append(np.average(x, weights=weights))
    var = np.var(avgs)
    return var

def unweightedEsitmator(n):
    t = len(n)
    b = [B(i,t) for i in range(t)]
    return b

def weightedEsitmator(n):
    t = len(n)
    b = [B(i,t) * n[i] for i in range(t)]
    return b

def optimalEstimator(n):
    ### reference: p.33
    b = []
    for t in range(1, len(n)+1):
        if t == 1:
            b_t = 1
        else:
            num = sum([b[i] * B(i,t) **2 * n[i] for i in range(t-1)])
            den = sum([b[i] * B(i,t) * n[i] for i in range(t-1)])
            b_t = num / den
            b_t = max(b_t, 1/n[t-1])
        b.append(b_t)

    t = len(n)
    weights = [b[i] * B(i,t) * n[i] for i in range(t)]
    return weights

def blendEstimator(n, r):
    t = len(n)
    weights_u = unweightedEsitmator(n)
    weights_w = weightedEsitmator(n)
    r = min(max(r, 0), 1)
    weights = [lerp(weights_w[i], weights_u[i], r) for i in range(t)]
    return weights


def getBestGamma(n):
    ### reference: p.30, 34
    t = len(n)
    b = [B(i,t) for i in range(t)]
    n_moments = [
        sum([b[i]*b[i] for i in range(t)]),
        sum([b[i]*b[i] * n[i] for i in range(t)]),
        sum([b[i]*b[i] / n[i] for i in range(t)]),
    ]
    print(f'n_moments: {n_moments}')
    weight_u = sum([b[i] for i in range(t)])
    weight_w = sum([n[i]*b[i] for i in range(t)])
    print(f'X = {weight_u} * ({weight_u} * {n_moments[1]} - {weight_w} * {n_moments[0]})')
    print(f'Y = {weight_w} * ({weight_u} * {n_moments[0]} + {weight_w} * {n_moments[-1]})')
    X = weight_u * (weight_u * n_moments[1] - weight_w * n_moments[0])
    Y = weight_w * (weight_u * n_moments[0] - weight_w * n_moments[-1])
    print(f'X = {X}, Y = {Y}')
    num = X
    den = num - Y
    print(f'num = {num}, den = {den}')
    if num == 0 and den == 0:
        return 0
    best_r = num/den
    # best_r = min(max(best_r, 0), 1)
    return best_r

def bestGammaEstimator(n):
    t = len(n)
    weights_w = weightedEsitmator(n)
    weights_u = unweightedEsitmator(n)
    r = getBestGamma(n)
    total_w = sum(weights_w)
    total_u = sum(weights_u)
    weights = [lerp(weights_w[i]/total_w, weights_u[i]/total_u, r) for i in range(t)]
    # normalize
    weights /= weights[0]
    return weights

T = 2
n = np.full(T, 1)
# for i in range(20,21):
#     n[i] = 8
n[-1] = 8

vars = []


# optimalVars = [estimateVar(optimalEstimator, n[:i]) for i in range(1, len(n)+1)]
# unweightedVars = [estimateVar(unweightedEsitmator, n[:i]) for i in range(1, len(n)+1)]
# weightedVars = [estimateVar(weightedEsitmator, n[:i]) for i in range(1, len(n)+1)]
# bestGammaVars = [estimateVar(bestGammaEstimator, n[:i]) for i in range(1, len(n)+1)]
# print(f'optimalVar:     {optimalVars}')
# print(f'unweightedVar:  {unweightedVars}')
# print(f'weightedVar:    {weightedVars}')
# print(f'bestGammaVar:   {bestGammaVars}')

bestGammas = [getBestGamma(n[:i]) for i in range(1, len(n)+1)]
print(f'best_r: {bestGammas}')

optimalWeights = optimalEstimator(n)
unweightedWeights = unweightedEsitmator(n)
weightedWeights = weightedEsitmator(n)
bestGammaWeights = bestGammaEstimator(n)
print(f'optimal weights:    {optimalWeights}')
print(f'unweighted weights: {unweightedWeights}')
print(f'weighted weights:   {weightedWeights}')
print(f'bestGamma weights:  {bestGammaWeights}')

ax1 = plt.subplot(2,1,1)
ax1.plot(optimalEstimator(n), label='optimal')
ax1.plot(unweightedEsitmator(n), label='unweighted')
ax1.plot(weightedEsitmator(n), label='weighted')
ax1.plot(bestGammaEstimator(n), label='bestGamma')
ax1.legend()

# ax2 = plt.subplot(2,1,2, sharex=ax1)
# ax2.plot(optimalVars, label='optimalVar')
# ax2.plot(unweightedVars, label='unweightedVar')
# ax2.plot(weightedVars, label='weightedVar')
# ax2.plot(bestGammaVars, label='bestGammaVar')
# ax2.plot(bestGammas, label='best_r')
# ax2.legend()

plt.show()
