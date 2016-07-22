# Peter Duggins
# ICCM 2016 Project
# June-August 2016
# Modeling the effects of drugs on working memory

import nengo
from nengo.dists import Choice,Exponential,Uniform
import nengo_gui
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import os
# import ipdb

'''Parameters ###############################################'''
#simulation parameters
filename='wm_1'
n_trials=500
dt=0.001 #timestep
dt_sample=0.05 #probe sample_every
t_stim=1.0 #duration of cue presentation
t_delay=8.0 #duration of delay period between cue and decision
decision_type='addition' #which decision procedure to use
drug_type='additive_noise'
drugs=['control','PHE','GFC']
drugs_effect={'control':0.00,'PHE':-0.6,'GFC':0.2} #for additive_noise, [gfc_mean, phe_mean];
ramp_scale=0.42 #how fast does the 'time' dimension accumulate in WM neurons
stim_scale=1.0 #how strong is the stimulus from the visual system
cues=2*np.random.randint(2,size=n_trials)-1 #whether the cues is on the left or right
misperceive=0.1 #chance of failing to perceive the cue, causing no info to go into WM
perceived=np.ones(n_trials)
for n in range(len(perceived)):
	if np.random.rand()<misperceive: perceived[n]=0

#ensemble parameters
neurons_sensory=100 #neurons for the sensory ensemble
neurons_wm=1000
neurons_decide=100
tau_stim=None #synaptic time constant of stimuli to populations
tau=0.01 #synaptic time constant between ensembles
tau_wm=0.1 #synapse on recurrent connection in wm
noise_wm=0.005 #standard deviation of full-spectrum white noise injected into wm.neurons
noise_decision=0.3 #for addition, std of added gaussian noise; 
wm_decay=1.0 #recurrent transform in wm ensemble: set <1.0 for decay

params={
	'filename':filename,
	'n_trials':n_trials,
	'dt':dt,
	'dt_sample':dt_sample,
	't_stim':t_stim,
	't_delay':t_delay,
	'decision_type':decision_type,
	'drug_type':drug_type,
	'drugs':drugs,
	'drugs_effect':drugs_effect,
	'ramp_scale':ramp_scale,
	'stim_scale':stim_scale,
	# 'cues':cues,
	'misperceive':misperceive,
	'perceived':perceived,

	'neurons_sensory':neurons_sensory,
	'neurons_wm':neurons_wm,
	'neurons_decide':neurons_decide,
	'tau_stim':tau_stim,
	'tau':tau,
	'tau_wm':tau_wm,
	'noise_wm':noise_wm,
	'noise_decision':noise_decision,
	'wm_decay':wm_decay,
}


'''helper functions ###############################################'''
drug='control'
n=0
def stim_function(t):
	if t < t_stim and perceived[n]!=0: return stim_scale*cues[n]
	else: return 0

def ramp_function(t):
	if t > t_stim: return ramp_scale
	else: return 0

def noise_bias_function(t):
	if drug_type=='additive_noise':
		return np.random.normal(drugs_effect[drug],noise_wm)

def noise_decision_function(t):
	return np.random.normal(0.0,noise_decision)

def decision_function(x):
	output=0.0
	if decision_type=='addition':
		value=x[0]+x[1]
		if value > 0.0: output = 1.0
		elif value < 0.0: output = -1.0
		# output=2.0*np.ceil(value)-1
	elif decision_type=='cdf': #to-do
		value=0 
		output=value
	#misperceive?
	return output 


'''model definition ###############################################'''
model=nengo.Network(label='Working Memory DRT with Drugs')
with model:

	#Input
	stim = nengo.Node(output=stim_function)
	ramp = nengo.Node(output=ramp_function)
	noise_wm_ens = nengo.Node(output=noise_bias_function)
	noise_decision_ens = nengo.Node(output=noise_decision_function)	
	sensory = nengo.Ensemble(neurons_sensory,2)

	#Working Memory
	wm = nengo.Ensemble(neurons_wm,2)

	#Output
	decision = nengo.Ensemble(neurons_decide,2)
	output = nengo.Ensemble(neurons_decide,1)

	#Connections
	nengo.Connection(stim,sensory[0],synapse=tau_stim)
	nengo.Connection(ramp,sensory[1],synapse=tau_stim)

	nengo.Connection(sensory,wm,synapse=tau_wm,transform=tau_wm)
	nengo.Connection(noise_wm_ens,wm.neurons,synapse=tau_wm,transform=np.ones((neurons_wm,1))*tau_wm)
	nengo.Connection(wm,wm,synapse=tau_wm,transform=wm_decay)

	nengo.Connection(wm[0],decision[0],synapse=tau) #no ramp information passed
	nengo.Connection(noise_decision_ens,decision[1],synapse=None)
	nengo.Connection(decision,output,function=decision_function)

	#Probes
	probe_wm=nengo.Probe(wm[0],synapse=0.1,sample_every=dt_sample) #no ramp information collected
	probe_spikes=nengo.Probe(wm.neurons, sample_every=dt_sample) #spike data
	probe_output=nengo.Probe(output,synapse=None,sample_every=dt_sample) #decision data



'''simulation and data collection ###############################################'''
#create Pandas dataframe for model data
columns=('time','drug','wm','output','correct','spikes','trial')
trials=np.arange(n_trials)
timesteps=np.arange(0,int((t_stim+t_delay)/dt_sample))
dataframe = pd.DataFrame(index=np.arange(0, len(drugs)*len(trials)*len(timesteps)),columns=columns)
i=0
for drug in drugs:
    for n in trials:
		print 'Running drug \"%s\", trial %s...' %(drug,n+1)
		sim=nengo.Simulator(model,dt=dt)
		sim.run(t_stim+t_delay)
		for t in timesteps:
			wm=np.abs(sim.data[probe_wm][t][0])
			output=sim.data[probe_output][t][0]
			spikes=sim.data[probe_spikes][t][0]
			if (cues[n] > 0.0 and output > 0.0) or (cues[n] < 0.0 and output < 0.0):
				correct=1
			else:
				correct=0
			rt=t*dt_sample
			dataframe.loc[i]=[rt,drug,wm,output,correct,spikes,n]
			i+=1

#create Pandas dataframe for model data
emp_columns=('time','drug','accuracy','trial')
emp_timesteps = [2.0,4.0,6.0,8.0]
pre_PHE=[0.972, 0.947, 0.913, 0.798]
pre_GFC=[0.970, 0.942, 0.882, 0.766]
post_GFC=[0.966, 0.928, 0.906, 0.838]
post_PHE=[0.972, 0.938, 0.847, 0.666]
emp_dataframe = pd.DataFrame(index=np.arange(0, 12),columns=emp_columns)
i=0
for t in range(len(emp_timesteps)):
	emp_dataframe.loc[i]=[emp_timesteps[t],'control',np.average([pre_GFC[t],pre_PHE[t]]),0]
	emp_dataframe.loc[i+1]=[emp_timesteps[t],'PHE',post_PHE[t],0]
	emp_dataframe.loc[i+2]=[emp_timesteps[t],'GFC',post_GFC[t],0]
	i+=3


'''data analysis, plotting, exporting ###############################################'''
root=os.getcwd()
os.chdir(root+'/data/')
addon=str(np.random.randint(0,100000))
fname=filename+addon

print 'Exporting Data...'
dataframe.to_pickle(fname+'_data.pkl')
param_df=pd.DataFrame([params])
param_df.reset_index().to_json(fname+'_params.json',orient='records')

print 'Plotting...'
sns.set(context='poster')
figure, (ax1, ax2) = plt.subplots(2, 1)
sns.tsplot(time="time",value="wm",data=dataframe,unit="trial",condition='drug',ax=ax1,ci=95)
sns.tsplot(time="time",value="correct",data=dataframe,unit="trial",condition='drug',ci=95,ax=ax2)
sns.tsplot(time="time",value="accuracy",data=emp_dataframe,unit='trial',condition='drug',
			interpolate=False,ax=ax2)
ax1.set(xlabel='',ylabel='abs(WM value)')
ax2.set(xlabel='time (s)',xlim=(2.0,8.0),ylabel='accuracy')
figure.savefig(fname+'_plots.png')
plt.show()

os.chdir(root)