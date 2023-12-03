#pragma once


#define FOR_SELECTION_MODES(X)\
    X(Unweighted) \
    X(Weighted) \
    X(Linear) \
    X(Step) \
    X(Logistic) \


enum class SelectionMode
{
    #define X(x) x,
    FOR_SELECTION_MODES(X)
    #undef X
    MAX
};


#define FOR_NORMALIZATION_MODES(X)\
    X(None) \
    X(Luminance) \
    X(Variance) \
    X(StandardDeviation) \

enum class NormalizationMode
{
    #define X(x) x,
    FOR_NORMALIZATION_MODES(X)
    #undef X
    MAX
};
