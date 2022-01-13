# AB-test-analyzer
Python class to perform AB test analysis

## Table of Contents
* [Overview](#overview)
* [The `ABTest` Class](#the-abtest-class)
* [Class Init](#class-init)
* [Methods](#methods)
  - [`get_reporting_df`](#get_reporting_df)

## Overview
This repo contains a Python class to perform an A/B/C… test analysis with **proportion-based metrics** (including posthoc test). In practice, the class can be used along with any appropriate RDBMS retrieval tool (e.g. [`google.cloud.bigquery`](https://github.com/googleapis/python-bigquery) module for BigQuery) so that, together, they result in an end-to-end analysis process, i.e. from querying the experiment data stored originally in SQL to arriving at the complete analysis results.

## The `ABTest` Class
The class is named `ABTest`. It is written on top of several well-known libraries (`numpy`, `pandas`, `scipy`, and `statsmodels`). The class' main functionality is to consume an experiment results data frame (`experiment_df`), metric information (`nominator_metric`, `denominator_metric`), and meta-information about the platform being experimented (`platform`) to perform two layers of statistical tests.
<br>
<br>
First, it will perform a Chi-square test on the aggregate data level. If this test is significant, the function will continue to perform a posthoc test that consists of testing each pair of experimental groups to report their adjusted p-values, as well as their absolute lift (difference) confidence intervals. Moreover, the class also has a method to calculate the statistical power of the experiment.

### Class Init
To create an instance of ABTest class, we need to pass the following parameters--that also become the class instance attributes:
1. `experiment_df`: pandas dataframe that contains the experiment data to be analyzed. The data contained  must form a proportion based metric (`nominator_metric/denominator_metric <= 1`). More on this parameter can be found in a later section.
2. `nominator_metric`: string representing the name of the nominator metric, one constituent of the proportion-based metric in `experiment_df`, e.g. `"transaction"`
3. `denominator_metric`: string representing the name of the denominator metric, another constituent of the proportion-based metric in `experiment_df`, e.g. `"visit"`
4. `platform`: string representing the platform represented by the experiment data, e.g. `"android"`, `"ios"`

## Methods
### `get_reporting_df`
This function has one parameter called `metric_level` (string, default value is `None`) that specifies the metric level of the experiment data whose reporting dataframe is to be derived. Two common values for this parameter are `"user"` and `"event"`.
<br>
<br>
Below is the output example from calling `self.get_reporting_df(metric_level='user')`
```
|    | experiment_group   | metric_level   |   targeted |   redeemed |   conversion |
|---:|:-------------------|:---------------|-----------:|-----------:|-------------:|
|  0 | control            | user           |       8333 |       1062 |     0.127445 |
|  1 | variant1           | user           |       8002 |        825 |     0.103099 |
|  2 | variant2           | user           |       8251 |       1289 |     0.156223 |
|  3 | variant3           | user           |       8275 |       1228 |     0.148399 |
```

### `posthoc_test`
This function is the engine under the hood of the `analyze` method. It has three parameters:
1. `reporting_df`: pandas dataframe, output of `get_reporting_df` method
2. `metric_level`: string, the metric level of the experiment data whose reporting dataframe is to be derived
3. `alpha`: float, the used alpha in the analysis

### `analyze`
The main function to analyze the AB test. It has two parameters:
1. `metric_level`: string, the metric level of the experiment data whose reporting dataframe is to be derived (default value is `None`). Two common values for this parameter are `"user"` and `"event"`
2. `alpha`: float, the used alpha in the analysis (default value is `0.05`)

The output of this method is a pandas dataframe with the following columns:
1. `metric_level`: optional, only if metric_level parameter is not `None`
2. `pair`: the segment pair being individually tested using z-proportion test
3. `raw_p_value`:  the raw p-value from the individual z-proportion test
4. `adj_p_value`: the adjusted p-value (using Benjamini-Hochberg method) from z-proportion tests. Note that significant result is marked with *
5. `mean_ci`: the mean (center value) of the metrics delta confidence interval at `1-alpha`
6. `lower_ci`: the lower bound of the metrics delta confidence interval at `1-alpha`
7. `upper_ci`: the upper bound of the metrics delta confidence interval at `1-alpha`

Sample output:
```
|    | metric_level   | pair                 |   raw_p_value | adj_p_value             |     mean_ci |    lower_ci |    upper_ci |
|---:|:---------------|:---------------------|--------------:|:------------------------|------------:|------------:|------------:|
|  0 | user           | control vs variant1  |   1.13731e-06 | 1.592240591875927e-06*  |  -0.0243459 |  -0.0341516 |  -0.0145402 |
|  1 | user           | control vs variant2  |   1.08192e-07 | 1.8933619380632198e-07* |   0.0287784 |   0.0181608 |   0.0393959 |
|  2 | user           | control vs variant3  |   9.00223e-05 | 0.00010502606726165857* |   0.0209537 |   0.0104664 |   0.031441  |
|  3 | user           | variant1 vs variant2 |   7.82096e-24 | 2.737334684573585e-23*  |   0.0531243 |   0.0427802 |   0.0634683 |
|  4 | user           | variant1 vs variant3 |   3.23786e-18 | 7.554997289146693e-18*  |   0.0452996 |   0.0350976 |   0.0555015 |
|  5 | user           | variant2 vs variant1 |   7.82096e-24 | 2.737334684573585e-23*  |  -0.0531243 |  -0.0634683 |  -0.0427802 |
|  6 | user           | variant2 vs variant3 |   0.161595    | 0.16159493454321772     | nan         | nan         | nan         |
```

### `calculate_power`
This function calculates the experiment’s statistical power for the supplied `experiment_df`. It has three parameters:
1. `practical_lift`: float, the metrics lift that perceived meaningful
2. `alpha`: float, the used alpha in the analysis (default value is `0.05`)
3. `metric_level`: string, the metric level of the experiment data whose reporting dataframe is to be derived (default value is `None`). Two common values for this parameter are `"user"` and `"event"`

Sample output:
```
The experiment's statistical power is 0.2680540196528648
```

## Data Format
This section is dedicated to explaining the details of the format of `experiment_df` , i.e. the main data supply for the `ABTest` class.
<br>
`experiment_df` must at least have three columns with the following names:
1. `experiment_group`: self-explanatory
2. `denominator_metric`: the name of the denominator metric, one constituent of the proportion-based metric in `experiment_df`, e.g. `"visit"` 
3. `nominator_metric`: the name of the nominator metric, one constituent of the proportion-based metric in `experiment_df`, e.g. `"transaction"`
4. (optional) `metric_level`: the metric level of the data (usually either `"user"` or `"event"`)

In practice, this dataframe is derived by querying SQL tables using an appropriate retrieval tool.  
<br>
Sample `experiment_df`
```
|    | experiment_group   | metric_level   |   targeted |   redeemed |
|---:|:-------------------|:---------------|-----------:|-----------:|
|  0 | control            | user           |       8333 |       1062 |
|  1 | variant1           | user           |       8002 |        825 |
|  2 | variant2           | user           |       8251 |       1289 |
|  3 | variant3           | user           |       8275 |       1228 |
```

## Usage Guideline
The general steps:
1. Prepare `experiment_df` (via anything you’d prefer)
2. Create an `ABTest` class instance
3. To get reporting dataframe, call `get_reporting_df` method
4. To analyze end-to-end, call `analyze` method
5. To calculate experiment’s statistical power, call `calculate_power` method

See the [sample usage notebook](https://github.com/pararawendy/AB-test-analyzer/blob/main/sample_usage.ipynb) for more details.

