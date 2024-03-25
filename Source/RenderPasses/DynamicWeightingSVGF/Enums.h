#pragma once


#define FOR_SELECTION_MODES(X)\
    X(SELECTION_MODE_UNWEIGHTED) \
    X(SELECTION_MODE_WEIGHTED) \
    X(SELECTION_MODE_LINEAR) \
    X(SELECTION_MODE_STEP) \
    X(SELECTION_MODE_LOGISTIC) \

enum SelectionMode
{
    #define X(x) x,
    FOR_SELECTION_MODES(X)
    #undef X
    SELECTION_MODE_MAX
};

#ifdef __cplusplus
const char* SelectionModeNames[] = {
    #define X(x) #x,
    FOR_SELECTION_MODES(X)
    #undef X
};
#endif

#define FOR_NORMALIZATION_MODES(X)\
    X(NORMALIZATION_MODE_NONE) \
    X(NORMALIZATION_MODE_LUMINANCE) \
    X(NORMALIZATION_MODE_VARIANCE) \
    X(NORMALIZATION_MODE_STANDARDDEVIATION) \

enum NormalizationMode
{
    #define X(x) x,
    FOR_NORMALIZATION_MODES(X)
    #undef X
    NORMALIZATION_MODE_MAX
};

#ifdef __cplusplus
const char* NormalizationModeNames[] = {
    #define X(x) #x,
    FOR_NORMALIZATION_MODES(X)
    #undef X
};
#endif
