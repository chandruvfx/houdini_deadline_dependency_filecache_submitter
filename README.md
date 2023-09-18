#   Houdini Deadline Dependency Filecache Submitter

## Overview

A dependency file caching system is an GUI interface, which facilitate an artist to submit the FA file cache nodes into the renderfarm in a chain order. The order is determined based upon the user selection in the GUI.

## How It Works
The GUI collects all the FA file cache sop nodes from the user selected geo nodes from obj network and showcase to the artist. An artist can choose the file cache nodes from the left-hand-selection side list, move to the right hand side submission list. The Order of the user selection in the left-side-selection list preserved while moving into the right-hand-side submission list. Th submission followup a logic of first-in-first out aka a chained order!!.

The submission Chained order describes, the first item submitted into the deadline as first job. The second item submitted as second job, which holds the job id of first job as dependency . The Third item submitted as third job, which holds the job id of second job as dependency.. vice-versa.. The dependency ensure that the job is starts only after the dependency job finishes.

Let consider a hip file have three FA file cache nodes for a flip sim. Fa_filecache_particles, Fa_filecache_source, Fa_filecache_meshing. Using dependency file cache system, an artist selected source, particle and meshing items in the order and moved to submission list. Now the submission chain is occur like below hierarchy

Fa_filecache_source
     ^
     |  (depends)
     |--Fa_filecache_particles
          ^
          |  (depends)
          |--Fa_filecache_meshing

Example
:point_down: [Youtube Link]
 
[![Houdini Dependency Cache Submitter](https://img.youtube.com/vi/Sv9WsHsojtg/0.jpg)](https://youtu.be/Sv9WsHsojtg)
