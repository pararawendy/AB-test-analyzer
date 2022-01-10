import numpy as np
import pandas as pd
import scipy.stats as st
from statsmodels.stats.proportion import proportions_chisquare, proportions_ztest
from statsmodels.stats.multitest import multipletests

class ABTest:
    def __init__(self, experiment_df, nominator_metric, denominator_metric, platform):
        self.experiment_df = experiment_df
        self.nominator_metric = nominator_metric
        self.denominator_metric = denominator_metric
        self.platform = platform
    
    def get_reporting_df(self, metric_level=None):
        if metric_level is None:
            reporting_df = (self.experiment_df
                               .assign(conversion=self.experiment_df[self.nominator_metric]/self.experiment_df[self.denominator_metric])
                              )
        else :
            reporting_df = (self.experiment_df
                               .loc[self.experiment_df.metric_level == metric_level]
                               .assign(conversion=self.experiment_df[self.nominator_metric]/self.experiment_df[self.denominator_metric])
                              )
        reporting_df.index = range(len(reporting_df))
        return reporting_df
        
    def posthoc_test(self, reporting_df, metric_level, alpha):
        # init placeholders
        pvals_raw = []
        pair_names = []
        deltas = []
        lower_bounds = []
        upper_bounds = []

        # do test for each segment pair
        for i in range(0,len(reporting_df)-1):
            for j in range(1,len(reporting_df)):
                if i != j:
                    # create the working dataframe
                    pair_df = reporting_df.loc[[i,j],['experiment_group',self.denominator_metric,self.nominator_metric]]
                    pair_df.index = range(len(pair_df))
                    pair_name = pair_df.loc[0,'experiment_group'] + ' vs ' + pair_df.loc[1,'experiment_group']
                    pair_names.append(pair_name)

                    # calucate confidence intervals
                    # i.e. populate lower_bounds and upper_bounds
                    pair_df.loc[len(pair_df)] = ['pool',
                                                 pair_df[self.denominator_metric].sum(),
                                                 pair_df[self.nominator_metric].sum()
                                                ]
                    pair_df.loc[:,'ctr'] = pair_df[self.nominator_metric] / pair_df[self.denominator_metric]
                    p1, p2, ppool = pair_df.loc[:,'ctr'].values
                    delta = p2-p1
                    N1, N2 = pair_df.loc[[0,1],self.denominator_metric].values
                    sepool = np.sqrt(ppool*(1-ppool)*(1/N1 + 1/N2))
                    m = st.norm.ppf(1-alpha/2) * sepool
                    deltas.append(delta)
                    lower_bounds.append(delta-m)
                    upper_bounds.append(delta+m)

                    # do proportion test
                    # save the raw p values
                    pair_count = reporting_df.loc[[i,j],self.nominator_metric].values
                    pair_nobs = reporting_df.loc[[i,j],self.denominator_metric].values
                    pvals_raw.append(proportions_ztest(pair_count,
                                                       pair_nobs,
                                                       alternative='two-sided'
                                                      )[1])

        # p-value correction
        signif_flags, pvals_adj = multipletests(pvals_raw,
                                                alpha=alpha,
                                                method='fdr_bh'
                                               )[0:2]

        # beautify pvals_adj as string with asterisk
        # as well as overriding deltas & lower/upper bounds for not significant pair test
        pvals_adj_str = []
        indexes = range(len(pvals_adj))
        for index, signif, pval, delta, lower_bound, upper_bound in zip(indexes, signif_flags, pvals_adj, deltas, lower_bounds, upper_bounds):
            if signif :
                pvals_adj_str.append(str(pval)+'*')
            else :
                pvals_adj_str.append(str(pval))
                deltas[index] = None
                lower_bounds[index] = None
                upper_bounds[index] = None

        # bring everything together
        posthoc_df = pd.DataFrame({
            'pair':pair_names,
            'raw_p_value':pvals_raw,
            'adj_p_value':pvals_adj_str,
            'mean_ci': deltas,
            'lower_ci':lower_bounds,
            'upper_ci':upper_bounds
        })
        
        # optional metric_level column
        if metric_level is not None:
            posthoc_df.insert(0, 'metric_level', [metric_level]*len(posthoc_df))

        return posthoc_df 
    
    def analyze(self, metric_level=None, alpha=0.05):
        # get reporting df
        reporting_df = self.get_reporting_df(metric_level)
      
        # aggregate prelim chi square test
        count = reporting_df.loc[:,self.nominator_metric].values
        nobs = reporting_df.loc[:,self.denominator_metric].values

        chi_pval = proportions_chisquare(count, nobs)[1]

        if chi_pval < alpha:
            report_df = self.posthoc_test(reporting_df, metric_level, alpha)
            return report_df
        else :
            print('Chi-Square test not significant')
            
    def calculate_power(self, practical_lift, alpha=0.05, metric_level=None):
        # get reporting data
        reporting_df = self.get_reporting_df(metric_level)
        # calculate power
        pc = reporting_df.loc[0,'conversion']
        sigma = np.sqrt(pc*(1-pc))
        n = reporting_df[self.denominator_metric].min()
        za = st.norm.ppf(1-alpha/2)
        zb= (np.sqrt(n)*practical_lift)/(2*sigma) - za
        power = st.norm.cdf(zb)
        print(f"The experiment's statistical power is {power}")
