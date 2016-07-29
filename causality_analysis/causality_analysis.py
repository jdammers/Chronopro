# -*- coding: UTF-8 -*-

"""

=================================================================
Causality analysis
=================================================================



"""
# Authors: Dong Qunxi <dongqunxi@gmail.com>
#         Jürgen Dammers <j.dammers@fz-juelich.de>
# License: BSD (3-clause)

import os, glob
#from dirs_manage import set_directory
from apply_causality import apply_inverse_oper, apply_STC_epo
from apply_causality import cal_labelts,normalize_data, sig_thresh, group_causality
from apply_causality import model_order, model_estimation, causal_analysis
print(__doc__)

###############################################################################
# Set parameters
# ------------------------------------------------
subjects_dir = os.environ['SUBJECTS_DIR'] 
# Set the path for storing STCs of conflicts processing
stcs_path = subjects_dir + '/fsaverage/conf_stc/'
#set_directory(stcs_path) 
template = 'fsaverage'
st_list = ['LLst', 'RRst', 'RLst',  'LRst']


# Cluster operation
do_apply_invers_oper = False # Making inverse operator
do_apply_STC_epo = False # Making STCs
do_extract_rSTCs = False   
do_norm = False
do_morder = False
do_moesti = True
do_cau = True
do_sig_est = True
do_group = True

###############################################################################
# Make inverse operator for each subject
# ------------------------------------------------
if do_apply_invers_oper:
    print '>>> Calculate Inverse Operator ....'
    fn_epo_list = glob.glob(subjects_dir+'/*[0-9]/MEG/*ocarta,evtW_LLst_bc-epo.fif')
    apply_inverse_oper(fn_epo_list)
    print '>>> FINISHED with STC generation.'
    print ''
        
###############################################################################
# Makeing STCs
# ------------------------------------------------
if do_apply_STC_epo:
    print '>>> Calculate morphed STCs ....'
    for evt in st_list:
        fn_epo = glob.glob(subjects_dir+'/*[0-9]/MEG/*ocarta,evtW_%s_bc-epo.fif' %evt)
        apply_STC_epo(fn_epo, event=evt)
    print '>>> FINISHED with morphed STC generation.'
    print ''
###############################################################################
# Extract representative STCs from ROIs
# ------------------------------------------------
if do_extract_rSTCs:
    print '>>> Calculate representative STCs ....'
    func_list_file = subjects_dir+'/fsaverage/conf_stc/STC_ROI/func_list.txt'
    for evt_st in st_list:
        #Calculate the representative STCs(rSTCs) for each ROI.
        stcs_path = glob.glob(subjects_dir+'/fsaverage/stcs/*[0-9]/%s/' %evt_st)
        cal_labelts(stcs_path, func_list_file, condition=evt_st, min_subject='fsaverage')
    print '>>> FINISHED with rSTC generation.'
    print ''    
###############################################################################
# Normalization STCs
# ------------------------------------------------
if do_norm:
    print '>>> Calculate normalized rSTCs ....'
    ts_path = glob.glob(subjects_dir+'/fsaverage/stcs/*[0-9]/*_labels_ts.npy')
    normalize_data(ts_path)
    print '>>> FINISHED with normalized rSTC generation.'
    print ''
###############################################################################
# Make mat version of normalized data 
# ------------------------------------------------ 
do_mat = False
if do_mat:
    print '>>> Calculate the mat version of normalized rSTCs ....'  
    from apply_causality import trans_mat 
    fn_norm = glob.glob(subjects_dir+'/fsaverage/stcs/*[0-9]/*_labels_ts,norm.npy')
    out_path = subjects_dir+'/fsaverage/stcs/normmat/'
    trans_mat(fn_norm, out_path)
    print '>>> FINISHED with normalized mats generation.'
    print ''
###############################################################################
# 1) Model construction and estimation
# 2) Causality analysis
# ------------------------------------------------
if do_morder:
    print '>>> Calculate the optimized Model order....'
    fn_norm = glob.glob(subjects_dir+'/fsaverage/stcs/*[0-9]/*_labels_ts,norm.npy')
    # Get optimized model order using BIC
    model_order(fn_norm)
    print '>>> FINISHED with optimized model order generation.'
    print ''
if do_moesti:
    print '>>> Envaluate the cosistency, whiteness, and stable features of the Model....'
    fn_monorm = glob.glob(subjects_dir+'/fsaverage/stcs/*[0-9]/*_labels_ts,norm,morder_*.npz')
    model_estimation(fn_monorm)
    print '>>> FINISHED with the results of statistical tests generation.'
    print ''
if do_cau:
    print '>>> Make the causality analysis....'
    fn_monorm = glob.glob(subjects_dir+'/fsaverage/stcs/*[0-9]/*_labels_ts,norm,morder_*.npz')
    causal_analysis(fn_monorm, repeats=500)
    print '>>> FINISHED with causal matrices and surr-causal matrices generation.'
    print ''
###############################################################################
# Significant estimation
# ------------------------------------------------
if do_sig_est:
    print '>>> Estimate the significance of the causality matrices....'
    sfreq = 678.17
    freqs = [(4, 8), (8, 12), (12, 18), (18, 30), (30, 40)]
    fn_cau = glob.glob(subjects_dir+'/fsaverage/stcs/*[0-9]/*,cau.npy')
    sig_thresh(cau_list=fn_cau, sfreq=sfreq, freqs=freqs, alpha=0.01)
    print '>>> FINISHED with significant causal matrices generation.'
    print ''
###############################################################################
# Group causality analysis
# ------------------------------------------------
if do_group:
    print '>>> Generate the group causal matrices....'
    for evt_st in st_list:
        fnsig_list = glob.glob(subjects_dir+'/fsaverage/stcs/*[0-9]/sig_cau/*%s_sig_con_band.npy' %evt_st)
        group_causality(fnsig_list, evt_st, submount=14)
    print '>>> FINISHED with group causal matrices generation.'
    print ''    
    
###############################################################################
# Make differences
# ------------------------------------------------

#
#    #Inverse epochs into the source space
#    #fn_epo = glob.glob(subjects_dir+'/*/MEG/*evtW_%s_bc-epo.fif' %evt_st)
#    #apply_inverse_epo(fn_epo,method=method, event=evt_st)
#    #Calculate the representative STCs(rSTCs) for each ROI.
#    #stcs_path = glob.glob(subjects_dir+'/fsaverage/stcs/*[0-9]/%s/' %evt_st)
#    #cal_labelts(stcs_path, func_list_file, condition=evt_st, min_subject='fsaverage')
#    ##Normalize rSTCs
#    #fn_ts = glob.glob(subjects_dir+'/fsaverage/stcs/*[0-9]/%s_labels_ts.npy' %evt_st)
#    #normalize_data(fn_ts) 
#    #MVAR model construction and evaluation, individual causality analysis for
#    #each condition 
#    fn_norm = glob.glob(subjects_dir+'/fsaverage/stcs/*[0-9]/%s_labels_ts,1-norm.npy' %evt_st)
#    model_estimation(fn_norm)
#    causal_analysis(fn_norm, method='PDC')
#    #Estimate the significance of each causal matrix.
#    fn_cau = glob.glob(subjects_dir+'/fsaverage/stcs/*[0-9]/%s_labels_ts,1-norm,cau.npy' %evt_st)
#    sig_thresh(cau_list=fn_cau, condition=evt_st, sfreq=sfreq)
#    ##Group causality analysis 
#    fn_sig = glob.glob(subjects_dir+'/fsaverage/stcs/*[0-9]/sig_con/%s_sig_con_band.npy' %evt_st)
#    group_causality(fn_sig, evt_st, submount=13)
#    
##Difference between incongruent and congruent tasks
#for ifreq in freqs:
#    fmin = ifreq[0]
#    fmax = ifreq[1] 
#    diff_mat(fmin=fmin, fmax=fmax)