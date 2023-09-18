#   Houdini Deadline Dependency Filecache Submitter

## Overview

A dependency file caching system is an GUI interface, which facilitate an artist to submit the FA file cache nodes into the renderfarm in a chain order. The order is determined based upon the user selection in the GUI.

## How It Works
The GUI collects all the FA file cache sop nodes from the user selected geo nodes from obj network and showcase to the artist. An artist can choose the file cache nodes from the left-hand-selection side list, move to the right hand side submission list. The Order of the user selection in the left-side-selection list preserved while moving into the right-hand-side submission list. Th submission followup a logic of first-in-first out aka a chained order!!.

The submission Chained order describes, the first item submitted into the deadline as first job. The second item submitted as second job, which holds the job id of first job as dependency . The Third item submitted as third job, which holds the job id of second job as dependency.. vice-versa.. The dependency ensure that the job is starts only after the dependency job finishes.

Let consider a hip file have three FA file cache nodes for a flip sim. Fa_filecache_particles, Fa_filecache_source, Fa_filecache_meshing. Using dependency file cache system, an artist selected source, particle and meshing items in the order and moved to submission list. Now the submission chain is occur like below hierarchy

Fa_filecache_source
     |--Fa_filecache_particles
          |--Fa_filecache_meshing

Important Note:Particle Simulation: 
Make sure caching particle simulation always happen in a single farm machine, To do so, assign `Frame Per Task` field in the deadline submission tab of the FA file cache HDA node to a subtracted value of end frame to the start frame. 
These suggestion upheld-ed due to the current frame of the simulation is depends on the previous frame. 

Important Note:Alembic:
Alembics caches were single files. Use the similar structure for `Frame Per Task` while configuring. 
As so, It utilize only one machine. Writing distinct frames from different machines into a single alembic file may lead to unforseen errors  

## Infos 
- Dependency submitter just submits the FA file cache nodes in top-to-bottom order. All the job files and plugin files for the respective fa file cache nodes created while submitting to the farm. The submission is taken care by clicking each HDA 'Submit' button via the python script.
- A copy of the houdini file with the random number saved and these file submitted into the renderfarm. In submission process a copy of houdini file saved , submitted and the old file is opened once it submitted. The copy is created inside Y:/pipeline/studio/temp/{username}/houdini/deadline_job_files
- Two python threads are running behalf of submission. One is thread run the progress bar while the other one busy with submitting the deadline jobs.
- While processing submitting, apart from the job files several others files were submitted behalf of caching. Which is Post-Job scripts. These python scripts were generated while executing dependency submitter and run at the end of per-job. The dependency submitter write two python files inside Y:/pipeline/studio/temp/{username}/houdini/deadline_job_files. One is post_job_py_file and another is post_job_exec_py_file. post_job_py_file responsible to open the houdini hip file and mark the 'load to disk' parameter `ON` for the currently running FA file cache node. post_job_exec_py_file responsible to execute the post_job_py_file.

Example
:point_down: [Youtube Link]
 
[![Houdini Dependency Cache Submitter](https://img.youtube.com/vi/Sv9WsHsojtg/0.jpg)](https://youtu.be/Sv9WsHsojtg)
