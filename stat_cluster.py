''' This version makes a unified inverse operator for each subject. Since the cortical info is 
    the same for all the evoked data from one subject, we only calculate one inverse 
    operator on 'LLst' evoked data. 
    To reduce the time consuming, funcction 'mv_ave' is used for reduce the size of timepoints.
'''
from mne import (spatial_tris_connectivity,
                 grade_to_tris)
from mne.stats import (spatio_temporal_cluster_1samp_test,
                       summarize_clusters_stc, spatio_temporal_cluster_test)
from scipy import stats as stats
import os, glob, mne
import numpy as np
from dirs_manage import set_directory
from jumeg.jumeg_preprocessing import get_files_from_list
subjects_dir = os.environ['SUBJECTS_DIR'] 

def apply_inverse_ave(fnevo, min_subject='fsaverage'):
    
    from mne import make_forward_solution
    from mne.minimum_norm import write_inverse_operator
    fnlist = get_files_from_list(fnevo)
    # loop across all filenames
    for fname in fnlist:
        fn_path = os.path.split(fname)[0]
        name = os.path.basename(fname)
        #fn_inv = fname[:fname.rfind('-ave.fif')] + ',ave-inv.fif' 
        subject = name.split('_')[0]
        fn_inv = fn_path + '/%s_fibp1-45,ave-inv.fif' %subject
        subject_path = subjects_dir + '/%s' %subject
        #min_dir = subjects_dir + '/%s' %min_subject
        fn_trans = fn_path + '/%s-trans.fif' % subject
        #fn_cov = fn_path + '/%s_empty,nr,fibp1-45-cov.fif' % subject
        fn_cov = fn_path + '/%s_empty,fibp1-45-cov.fif' %subject
        fn_src = subject_path + '/bem/%s-oct-6-src.fif' % subject
        fn_bem = subject_path + '/bem/%s-5120-5120-5120-bem-sol.fif' % subject
        [evoked] = mne.read_evokeds(fname)
        evoked.pick_types(meg=True, ref_meg=False)
        noise_cov = mne.read_cov(fn_cov)
        #noise_cov = mne.cov.regularize(noise_cov, evoked.info,
         #                               mag=0.05, grad=0.05, proj=True)
        fwd = make_forward_solution(evoked.info, fn_trans, fn_src, fn_bem)
        fwd['surf_ori'] = True
        inv = mne.minimum_norm.make_inverse_operator(evoked.info, fwd, noise_cov, loose=0.2,
                                                     depth=0.8, limit_depth_chs=False)
        write_inverse_operator(fn_inv, inv)
        
def apply_STC_ave(fnevo, method='dSPM', snr=3.0, min_subject='fsaverage'):
    ''' Inverse evoked data into the source space. 
        Parameter
        ---------
        fnevo: string or list
            The evoked file with ECG, EOG and environmental noise free.
        method:string
            Inverse method, 'MNE' or 'dSPM'
        snr: float
            Signal to noise ratio for inverse solution.
        event: string
            The event name related with evoked data.
        baseline: bool
            If true, prestimulus segment from 'btmin' to 'btmax' will be saved, 
            If false, no baseline segment is saved.
        btmin: float
            The start time point (second) of baseline.
        btmax: float
            The end time point(second) of baseline.
        min_subject: string
            The subject name as the common brain.
    '''
    #Get the default subjects_dir
    from mne.minimum_norm import apply_inverse, read_inverse_operator
    fnlist = get_files_from_list(fnevo)
    # loop across all filenames
    for fname in fnlist:
        name = os.path.basename(fname)
        fn_path = os.path.split(fname)[0]
        fn_stc = fname[:fname.rfind('-ave.fif')] 
        #fn_inv = fname[:fname.rfind('-ave.fif')] + ',ave-inv.fif' 
        subject = name.split('_')[0]
        fn_inv = fn_path + '/%s_fibp1-45,ave-inv.fif' %subject
        snr = snr
        lambda2 = 1.0 / snr ** 2 
        #noise_cov = mne.read_cov(fn_cov)
        [evoked] = mne.read_evokeds(fname)
        evoked.pick_types(meg=True, ref_meg=False)
        inv = read_inverse_operator(fn_inv)
        stc = apply_inverse(evoked, inv, lambda2, method,
                            pick_ori='normal')
        stc.save(fn_stc)
        

def morph_STC(fn_stc, grade, template='fsaverage', event='LLst', 
              baseline=True, btmin=-0.3, btmax=0.):
    from mne import read_source_estimate, morph_data
    fnlist = get_files_from_list(fn_stc) 
    for fname in fnlist:  
        name = os.path.basename(fname)
        subject = name.split('_')[0]
        stc_name = name[:name.rfind('-ave.fif')] 
        min_dir = subjects_dir + '/%s' %template
        # this path used for ROI definition
        stc_path = min_dir + '/dSPM_ROIs/%s' %(subject)
        #fn_cov = meg_path + '/%s_empty,fibp1-45,nr-cov.fif' % subject
        set_directory(stc_path) 
        # Morph STC
        stc = read_source_estimate(fname)
        stc_morph = morph_data(subject, template, stc, grade=grade)
        stc_morph.save(stc_path + '/%s' % (stc_name), ftype='stc')
        if baseline == True:
            stc_base = stc_morph.crop(btmin, btmax)
            stc_base.save(stc_path + '/%s_%s_baseline' % (subject, event[:2]), ftype='stc') 
                    
def Ara_contr(evt_list, tmin, tmax, conf_type, stcs_path, n_subjects=14, template='fsaverage'):
    con_stcs = []
    for evt in evt_list[:2]:
        fn_stc_list1 = glob.glob(subjects_dir+'/fsaverage/dSPM_ROIs/*[0-9]/*fibp1-45,evtW_%s_bc-lh.stc' %evt)
        for fn_stc1 in fn_stc_list1[:n_subjects]:
            stc1 = mne.read_source_estimate(fn_stc1, subject=template)
            stc1.crop(tmin, tmax)
            con_stcs.append(stc1.data)
    cons = np.array(con_stcs).transpose(1,2,0) 
    
    #tmin = stc1.tmin 
    tstep = stc1.tstep 
    fsave_vertices = stc1.vertices
    del stc1
   
    incon_stcs = []
    for evt in evt_list[2:]:
        fn_stc_list2 = glob.glob(subjects_dir+'/fsaverage/dSPM_ROIs/*[0-9]/*fibp1-45,evtW_%s_bc-lh.stc' %evt)
        for fn_stc2 in fn_stc_list2[:n_subjects]:
            stc2 = mne.read_source_estimate(fn_stc2, subject=template)
            stc2.crop(tmin, tmax)
            incon_stcs.append(stc2.data)
    incons = np.array(incon_stcs).transpose(1,2,0)  
    del stc2
    X = [cons[:, :, :], incons[:, :, :]]
    #import pdb
    #pdb.set_trace()
    # save data matrix
    X = np.array(X).transpose(1,2,3,0)
    X = np.abs(X)  # only magnitude
    np.savez(stcs_path + '%s.npz' %conf_type, X=X, tstep=tstep, fsave_vertices=fsave_vertices)
    return tstep, fsave_vertices, X
    
def Ara_contr_base(evt_list, tmin, tmax, conf_type, stcs_path, n_subjects=14, template='fsaverage'):
    stcs = []
    bs_stcs = []
    for evt in evt_list:
        fn_stc_list1 = glob.glob(subjects_dir+'/fsaverage/dSPM_ROIs/*[0-9]/*fibp1-45,evtW_%s_bc-lh.stc' %evt)
        for fn_stc1 in fn_stc_list1[:n_subjects]:
            #fn_stc2 = fn_stc1.split(evt)[0] + evt[:2] +  fn_stc1.split(evt)[1]
            name = os.path.basename(fn_stc1)
            fn_path = os.path.split(fn_stc1)[0]
            subject = name.split('_')[0]
            fn_stc2 = fn_path + '/%s_%s_baseline-lh.stc' % (subject, evt[:2])
            stc1 = mne.read_source_estimate(fn_stc1, subject=template)
            stc1.crop(tmin, tmax)
            stcs.append(stc1.data)
            stc2 = mne.read_source_estimate(fn_stc2, subject=template)
            bs_stcs.append(stc2.data)
    stcs_ = np.array(stcs).transpose(1,2,0) 
    bsstcs = np.array(bs_stcs).transpose(1,2,0)
    #tmin = stc1.tmin 
    tstep = stc1.tstep 
    fsave_vertices = stc1.vertices
    del stc1, stc2
    X = [stcs_[:, :, :], bsstcs[:, :, :]]
    #import pdb
    #pdb.set_trace()
    # save data matrix
    X = np.array(X).transpose(1,2,3,0)
    X = np.abs(X)  # only magnitude
    np.savez(stcs_path + '%s.npz' %conf_type, X=X, tstep=tstep, fsave_vertices=fsave_vertices)
    return tstep, fsave_vertices, X  
      
def mv_ave(X, window, overlap, freqs=678.17):
    ''' The shape of X should be (Vertices, timepoints, subjects*2, cases)
    '''
    mv_wind = window * 0.001
    step_wind = (window - overlap) * 0.001
    st_point = 0
    win_id = int(mv_wind * freqs)
    ste_id = int(step_wind * freqs)
    N_X = []
    while win_id < X.shape[1]:
        N_X.append(X[:, st_point:win_id, :, :].mean(axis=1))
        win_id = win_id + ste_id
        st_point = st_point + ste_id
    N_X = np.array(N_X).transpose(1,0,2,3) 
    return N_X    
    
def stat_clus(X, tstep, time_thre=0, n_per=8192, p_threshold=0.01, p=0.05, fn_clu_out=None):
    print('Computing connectivity.')
    connectivity = spatial_tris_connectivity(grade_to_tris(5))
    #    Note that X needs to be a multi-dimensional array of shape
    #    samples (subjects) x time x space, so we permute dimensions
    X = np.transpose(X, [2, 1, 0])
    n_subjects = X.shape[0]
    fsave_vertices = [np.arange(X.shape[-1]/2), np.arange(X.shape[-1]/2)]
    #    Now let's actually do the clustering. This can take a long time...
    #    Here we set the threshold quite high to reduce computation.
    t_threshold = -stats.distributions.t.ppf(p_threshold / 2., n_subjects - 1)
    print('Clustering.')
    max_step = int(time_thre * 0.001 / tstep) + 1
    T_obs, clusters, cluster_p_values, H0 = clu = \
        spatio_temporal_cluster_1samp_test(X, connectivity=connectivity, n_jobs=1, max_step=max_step,
                                        threshold=t_threshold, n_permutations=n_per)
    #    Now select the clusters that are sig. at p < 0.05 (note that this value
    #    is multiple-comparisons corrected).
    good_cluster_inds = np.where(cluster_p_values < p)[0]
    print 'the amount of significant clusters are: %d' %good_cluster_inds.shape
    ###############################################################################
    # Save the clusters as stc file
    # ----------------------
    assert good_cluster_inds.shape != 0, ('Current p_threshold is %f %p_thr,\
                                 maybe you need to reset a lower p_threshold')
    np.savez(fn_clu_out, clu=clu, tstep=tstep, fsave_vertices=fsave_vertices)


def per2test(X1, X2, p_thr, p, tstep, n_per=8192, fn_clu_out=None):

    #    Note that X needs to be a multi-dimensional array of shape
    #    samples (subjects) x time x space, so we permute dimensions
    n_subjects1 = X1.shape[2]
    n_subjects2 = X2.shape[2]
    fsave_vertices = [np.arange(X1.shape[0]/2), np.arange(X1.shape[0]/2)]
    X1 = np.transpose(X1, [2, 1, 0])
    X2 = np.transpose(X2, [2, 1, 0])
    X = [X1, X2]
    #    Now let's actually do the clustering. This can take a long time...
    #    Here we set the threshold quite high to reduce computation.
    f_threshold = stats.distributions.f.ppf(1. - p_thr / 2., n_subjects1 - 1, n_subjects2 - 1)
    print('Clustering.')
    connectivity = spatial_tris_connectivity(grade_to_tris(5))
    T_obs, clusters, cluster_p_values, H0 = clu = \
        spatio_temporal_cluster_test(X, n_permutations=n_per, 
                                    connectivity=connectivity, n_jobs=1,
                                    threshold=f_threshold)
    #    Now select the clusters that are sig. at p < 0.05 (note that this value
    #    is multiple-comparisons corrected).
    good_cluster_inds = np.where(cluster_p_values < p)[0]
    print 'the amount of significant clusters are: %d' %good_cluster_inds.shape
    ###############################################################################
    # Save the clusters as stc file
    # ----------------------
    assert good_cluster_inds.shape != 0, ('Current p_threshold is %f %p_thr,\
                                 maybe you need to reset a lower p_threshold')
    np.savez(fn_clu_out, clu=clu, tstep=tstep, fsave_vertices=fsave_vertices)
   
def clu2STC(fn_cluster, p_thre=0.05, tmin=0.):
    #    Now let's build a convenient representation of each cluster, where each
    #    cluster becomes a "time point" in the SourceEstimate
    fn_stc_out = fn_cluster[:fn_cluster.rfind('.npz')] + ',temp_%.3f,tmin_%.3f' %(p_thre, tmin)
    npz = np.load(fn_cluster)
    tstep = npz['tstep'].flatten()[0]
    clu = npz['clu']
    fsave_vertices = list(npz['fsave_vertices'])
    stc_all_cluster_vis = summarize_clusters_stc(clu, p_thre, tstep=tstep, 
                                                 tmin=tmin, vertices=fsave_vertices,
                                                subject='fsaverage')
    
    if fn_stc_out == None:
        return stc_all_cluster_vis    
    stc_all_cluster_vis.save(fn_stc_out)
    
