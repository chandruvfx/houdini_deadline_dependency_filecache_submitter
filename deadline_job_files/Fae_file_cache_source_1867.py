import hou
hou.hipFile.load("Y:/pipeline/studio/temp/chandra.santharam/houdini/deadline_job_files/sim_test_1867_submission.hip")
node = hou.node("/obj/sphere_object1/Fae_file_cache_source")
node.parm("load_from_disk").set(1)
hou.hipFile.save("Y:/pipeline/studio/temp/chandra.santharam/houdini/deadline_job_files/sim_test_1867_submission.hip")
print("Load disk setted True. Hip File Saved")
