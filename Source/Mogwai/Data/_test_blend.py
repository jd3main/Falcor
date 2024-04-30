import cv2 as cv
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt


SIGMA = 1.0
ALPHA = 0.2
BETA = 1.0 - ALPHA

def B(i, t, beta=BETA):
    return beta**(t-i-1)

def W(n, beta=BETA):
    return (1-beta**n)/(1-beta)

def estimateVar(estimator, ns, sigma=SIGMA):
    avgs = []
    for _ in range(1000):
        x = []
        for n in ns:
            x.append(np.mean(np.random.normal(0, sigma, n)))
        avg = estimator(x)
        avgs.append(avg)
    var = np.var(avgs)
    return var

def lerp(a, b, t):
    return a + (b-a)*t

def estimateBlend(x, n, r):
    t = len(x)
    weights_w = np.array([n[i]*B(i,t) for i in range(t)])
    weights_u = np.array([B(i,t) for i in range(t)])
    total_w = sum(weights_w)
    total_u = sum(weights_u)
    weights_w /= total_w
    weights_u /= total_u
    weights = lerp(weights_w, weights_u, r)
    return np.average(x, weights=weights)

def varLw(n):
    t = len(n)
    w = sum([B(i,t) * n[i] for i in range(t)])
    return sum([B(i,t)**2 * n[i] for i in range(t)]) / w**2

def varLu(n):
    t = len(n)
    w = sum([B(i,t) for i in range(t)])
    return sum([B(i,t)**2 / n[i] for i in range(t)]) / w**2

def analyticVars(n, r):
    t = len(n)
    b_u = [B(i,t) for i in range(t)]
    b_w = [n[i]*B(i,t) for i in range(t)]
    W_u = sum(b_u)
    W_w = sum(b_w)
    return sum([lerp(b_w[i]/W_w, b_u[i]/W_u, r)**2/n[i] for i in range(t)])

assert B(2, 3) == 1
assert B(0, 3) == 0.8**2
assert abs(sum([B(i,5) for i in range(5)]) - W(5)) < 0.01


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
    # wu2 = weight_u * weight_u
    # ww2 = weight_w * weight_w
    # wuww = weight_u * weight_w
    # num = wu2 * n_moments[1] - wuww * n_moments[0]
    # den = wu2 * n_moments[1] - 2 * wuww * n_moments[0] + ww2 * n_moments[-1]
    print(f'X = {weight_u} * ({weight_u} * {n_moments[1]} - {weight_w} * {n_moments[0]})')
    print(f'Y = {weight_w} * ({weight_u} * {n_moments[0]} + {weight_w} * {n_moments[-1]})')
    X = weight_u * (weight_u * n_moments[1] - weight_w * n_moments[0])
    Y = weight_w * (weight_u * n_moments[0] - weight_w * n_moments[-1])
    print(f'X = {X}, Y = {Y}')
    num = X
    den = num - Y
    print(f'num = {num}, den = {den}')
    # if num == 0:
    #     return 0
    # if den == 0:
    #     return 1
    best_r = num/den
    # best_r = min(max(best_r, 0), 1)
    return best_r

T = 2
n = np.full(T, 1)
n[-1] = 8
# for i in range(10,20):
#     n[i] = 8

print(f'n: {n}')
print(f'best: {analyticVars(n, getBestGamma(n))}')
print(f'opt:  {analyticVars(n, 0.1)}')

estimators = []
rs = list(np.arange(0, 1.01, 0.05))

for r in rs:
    estimator = lambda x, r=r: estimateBlend(x, n, r)
    estimators.append(estimator)

vars = [estimateVar(estimator, n) for estimator in estimators]
plt.plot(rs, vars)


# Draw analytic vars
var_x = SIGMA*SIGMA
Bs = [B(i, T) for i in range(T)]
nBs = [n[i]*B(i, T) for i in range(T)]
w = sum(Bs)
nw = sum(nBs)

analytic_vars = [analyticVars(n,r) for r in rs]
print(analytic_vars)
plt.plot(rs, analytic_vars, color='tab:orange')

best_r = getBestGamma(n)
blend_weights = [lerp(nBs[i]/nw, Bs[i]/w, best_r) for i in range(T)]
print(f'blend_weights = {blend_weights}')

print(f'best_r = {best_r}')
plt.stem(best_r, analyticVars(n,best_r), markerfmt='ro', linefmt='r-')

plt.stem(0, analyticVars(n,0), markerfmt='go', linefmt='g-')
plt.stem(1, analyticVars(n,1), markerfmt='bo', linefmt='b-')
# plt.ylim(0, max(vars)*1.1)

# for r in rs:
#     weights = [lerp(n[i]*B(i,T), B(i,T), r) for i in range(T)]
#     plt.plot(weights, label=f'r={r}')
# plt.legend()

plt.show()
