#pragma once


#define FOR_SELECTION_MODES(X)\
    X(Unweighted) \
    X(Weighted) \
    X(Linear) \
    X(Step) \
    X(Logistic) \


enum SelectionMode
{
    #define X(x) x,
    FOR_SELECTION_MODES(X)
    #undef X
    MAX
};
