#
# A GUI tool gather all the fae_file_cache nodes from the obj context
# allow users to multi select the items from the collection tree view widget(left side) and 
# move the selected items to the sumbission list list view widget(right side). 
# The Submission list preserves the order based upon the selection carried out by the user.
# The Dependency submission achieved one job dependent on another. A chained order !!. 
#
# Submission Methodology:
# -----------------------
# A copy of hip file saved under users temp directory. The Submission script submit custom 
# file cache nodes one-by-one from top-to-bottom from these file to the deadline farm. 
# Each file_cache node submitted as a single deadline job and Each job dispatched with 
# the 'Post Job Script' to the dealine farm, which ideally run at the end of the job once all 
# the frames completes. Second job depends First. Third job depends Second. etc..,,
# The 'Post Job Script' is a python file runs at last from the native deadline python plugin,
# In-charge of executing another python file from the hython standalone to open the hip file
# switch the current custom file_cache 'load from disk' and save the hip file back again. 
# 
# Example
# -------
#
# Consider a hip file contains custom file cache nodes for source, particle and meshing.
# User submit in the order source -> particle -> meshing.  particle job depends on source job
# mesh job dependes on particle job. Once source particles dumped out in the disk, 
# the 'Post Job Script' open the current hip file, toggle on the 'load from disk' of source
# file cache node and save it back. As so, when particles starting caching the simulation
# network read the source particles from the disk. Similarly works for other jobs too


import hou
import os 
import subprocess
import copy
import time
import random
import threading
from PySide2 import QtCore, QtGui, QtWidgets
from PySide2.QtCore import Qt
from PySide2.QtGui import QStandardItemModel, QStandardItem
from PySide2.QtUiTools import QUiLoader


class CollectGeoNodes:
    
    """Returns Gathered custom fae_file_Cache nodes""" 
    
    def get_seleted_nodes(self) -> hou.Node:

        """Dive inside into user selected geo nodes 
        collects all the custom file cache nodes and
        return it
        """
        
        nodes= hou.selectedNodes()
        filecache_tree_items = {}

        for node in nodes:
            filecache_tree_items[node] =[]
            for file_cache_node in node.children():
                if 'farm_dependency' in  file_cache_node.userDataDict():
                    filecache_tree_items[node].append(file_cache_node)
        return filecache_tree_items


class progressBarWindow(QtWidgets.QDialog):
    
    """Standalone progress window

    A progress window runs each time the 
    submission happens. Run from seperate thread
    """
    def __init__(self, parent=None) -> None:
                
            super().__init__(parent)
            self.setGeometry(100, 100, 340, 100)
            self.setWindowTitle('FAE Submitter Progress')

            qtRectangle = self.frameGeometry()
            centerPoint = QtWidgets.QDesktopWidget().availableGeometry().center()
            qtRectangle.moveCenter(centerPoint)
            self.move(qtRectangle.topLeft())

            self.job_id_label = QtWidgets.QLabel(self)
            self.job_id_label.move(2, 7)
            self.job_id_label.resize(600, 30)
            # self.job_id_label.setText("Submitting... ")

            self.progress_bar = QtWidgets.QProgressBar(self)
            self.progress_bar.setMaximum(100)
            self.progress_bar.move(2, 50)
            self.progress_bar.resize(340,50)
            self.progress_bar.setFont(QtGui.QFont("", 11))
  
            self.show()
    

class DependencyFileCacheSubmitter(QtWidgets.QMainWindow):
        """Master Class execute the task of dependency submission

        GUI tool loaded from the Qt ui read utility. Gui contain Two widgets  
        one is collection treeview widget(left) another is user moved submission listview widget(right).
        Collections are list of items ideally custom file cache nodes inside geo nodes of the Obj.
        It is loaded on the left side list widget. 
        GUI Allows user actions like selecting, moving, linting, reloading and 
        clearing both the list widgets. 
        Submit pushbutton do several task. Once it pressed it trigger two thread. 
        one is reposible for counting the waiting time while the deadline commandline tool perform
        it task. It trigger the qt progress dialog which mapped the waiting time to the counter.
        another one, create plugin and jobinfo job files, submit to dealine.
        """
        
        def __init__(self) -> None:

            """Initialize the qt GUI

            Read the UI file and widgets. 
            Trigger necessary user actions to a performable task
            """
            
            super().__init__()

            self.count = 0
            self.deadline_cmd_Status = []
            self.process_counter = 0
            self.show_job_id = []
            self.random_no = random.randint(100, 9999)
            self.dl_root_submission_file_path = "Y:/pipeline/studio/temp/" + \
                                                hou.userName() + \
                                                "/houdini/deadline_job_files"
            if not os.path.exists(self.dl_root_submission_file_path): 
                os.makedirs(self.dl_root_submission_file_path)

            # Deadline Command line exe
            self.dl_path = r"C:/Program Files/Thinkbox/Deadline10/bin"
            self.dl_path = self.dl_path.replace(r"/", "//") + "//deadlinecommand.exe"
            self.dl_path = '"%s"' %self.dl_path

            # Load Ui File via the qt loader to read the children widgets
            dirname = os.path.dirname(__file__)
            filename = os.path.join(dirname, 'dependency_submitter_gui.ui')
            loader = QUiLoader()
            self.window = loader.load(filename, None)

            # Arrow button to move items from left to right
            self.move_widget = self.window.findChild(QtWidgets.QPushButton, 'move')
            self.move_widget.clicked.connect(self.move_selected)

            # Left lit tree view 
            self.file_cache_tree_view = self.window.findChild(QtWidgets.QTreeView, 'treeView')
            self.file_cache_tree_view.setSelectionMode(self.file_cache_tree_view.ExtendedSelection)
            self.tree_view_model = QStandardItemModel()
                
            self.file_cache_tree_view.setModel(self.tree_view_model)
            self.file_cache_tree_view.expandAll()

            # Right List view
            self.file_cache_list_view = self.window.findChild(QtWidgets.QListView, 'listView')
            self.list_view_model = QStandardItemModel()
            self.file_cache_list_view.setModel(self.list_view_model)

            # Trigger submission task to deadline 
            self.submit_deadline_button = self.window.findChild(QtWidgets.QPushButton, 'submit_deadline')
            self.submit_deadline_button.setStyleSheet("font: 10pt 'Nirmala UI'")
            self.submit_deadline_button.clicked.connect(self.generate_deadline_data)

            # Flush out the tree view and load back again with new set of selection
            # made by the user on the obj context
            self.reload_hou_geo_into_treeview = \
                self.window.findChild(QtWidgets.QPushButton, 'reload')
            self.reload_hou_geo_into_treeview.clicked.connect(self.reload_obj_context_geos)
            
            self.clear_items_list_view = \
                self.window.findChild(QtWidgets.QPushButton, 'clear')
            self.clear_items_list_view.clicked.connect(self.clear_all_list_view)
            
            self.collect_geo_nodes_from_obj()
            

        def reload_obj_context_geos(self) -> None:

            """Flush the tree view. Re-append all the items based on 
            the new selection by the user
            """
            
            self.collect_geo_nodes_from_obj()

        def clear_all_list_view(self) -> None:

            """Wipe out the items in the list view
            make the left side collected treeview items to 
            linted white
            """
            
            self.list_view_model.clear()

            for row in range(self.tree_view_model.rowCount()):
                treeview_parent_index = self.tree_view_model.index(row, 0)
                child_count = 0
                while child_count >= 0:
                    if not treeview_parent_index.child(child_count,0).data():
                        break
                    else:
                        self.tree_view_model.setData(
                                    self.tree_view_model.index(
                                                                treeview_parent_index.child(child_count,0).row(), 
                                                                0, 
                                                                treeview_parent_index
                                                            ), 
                                    QtGui.QBrush(Qt.white),
                                    QtCore.Qt.ForegroundRole
                        )
                        child_count = child_count + 1


        def collect_geo_nodes_from_obj(self) -> None:
            """ Manipulate tree view and list view with items

            Create standard item model for tree view. parents were
            geo node names. child names are the sop nodes of the geo nodes.
            
            Consider, If user leave some nodes and do a fresh selection of geo nodes
            then the tree view cleared out and loaded with new items
            Old items in the List view which not exsist in the fresh selection is also 
            cleared. Other remainig items order and color preserved
             """
            
            
            items = self.get_all_submission_items()
            moved_items = []
            self.tree_view_model.clear()
            self.tree_view_model.setHorizontalHeaderLabels(['File Cache Nodes'])
            self.file_cache_tree_view.header().setDefaultSectionSize(180)

            geo_nodes = CollectGeoNodes()
            for geo_nodes, sop_nodes in geo_nodes.get_seleted_nodes().items():
                obj_geo_items = QStandardItem(geo_nodes.name())
                obj_geo_items.setFont(QtGui.QFont("", 11))
                obj_geo_items.setSelectable(False)
                obj_geo_items.setEditable(False)

                for sop_node in sop_nodes:
                    file_cache_node_items = QStandardItem(sop_node.name())
                    file_cache_node_items.setFont(QtGui.QFont("", 9))
                    file_cache_node_items.setEditable(False)
                    obj_geo_items.appendRow(file_cache_node_items)

                self.tree_view_model.appendRow(obj_geo_items)
            self.file_cache_tree_view.expandAll()

            # Red Color gonna assign during reloaded 
            for row in range(self.tree_view_model.rowCount()):
                treeview_parent_index = self.tree_view_model.index(row, 0)
                child_count = 0

                while child_count >= 0:
                    if not treeview_parent_index.child(child_count,0).data():
                        break

                    else:
                        tree_file_cache = treeview_parent_index.data() + "/" + treeview_parent_index.child(child_count,0).data()
                        
                        if tree_file_cache in items:
                            moved_items.append(tree_file_cache)
                            self.tree_view_model.setData(
                                        self.tree_view_model.index(
                                                                    treeview_parent_index.child(child_count,0).row(), 
                                                                    0, 
                                                                    treeview_parent_index
                                                                ), 
                                        QtGui.QBrush(Qt.red),
                                        QtCore.Qt.ForegroundRole
                            )
                        child_count = child_count + 1


            get_overlap_items = copy.deepcopy(
                                            sorted(
                                                set(moved_items).intersection(set(items)), 
                                                key= items.index
                                            )
                                )
            
            # Clear the list view.
            self.list_view_model.clear()
            if get_overlap_items:  
                for get_overlap_item in get_overlap_items:
                    moved_file_cache_node_name = QStandardItem(get_overlap_item)
                    moved_file_cache_node_name.setFont(QtGui.QFont("", 9))
                    self.list_view_model.appendRow(moved_file_cache_node_name)


        def get_all_submission_items(self) -> list:
            
            """Returns the items exist in the 
            list view"""
            
            items = []
            model = self.file_cache_list_view.model()
            for row in range(model.rowCount()):
                index = model.index(row, 0)
                item = model.data(index, Qt.DisplayRole)
                items.append(item)
            return items


        def move_selected(self) -> None:
            
            """Move the selected item between views

            Move the selected tree item to list view. 
            Once migrated the migrated item in the tree view
            linted with red and clear the selection. 
            The item name in the list concatinated with 
            the parent name ie geo node name and child name 
            ie sop file cache node name
            """
            
            items = self.get_all_submission_items()
            
            for selected_items in self.file_cache_tree_view.selectedIndexes():
                parent = selected_items.parent().data()
                file_cache_node = parent + "/" + selected_items.data()
                if file_cache_node not in items:
            
                    selected_row = selected_items.row()

                    self.tree_view_model.setData(
                                        self.tree_view_model.index(selected_row, 0, selected_items.parent()), 
                                        QtGui.QBrush(Qt.red),
                                        QtCore.Qt.ForegroundRole
                    )

                    moved_file_cache_node_name = QStandardItem(file_cache_node)
                    moved_file_cache_node_name.setFont(QtGui.QFont("", 9))
                    self.list_view_model.appendRow(moved_file_cache_node_name)

            self.file_cache_tree_view.selectionModel().clearSelection()

        def generate_deadline_data(self) -> None:
            """Attain deadline job files path and submit the deadline job 
            
            Method atain dealine plugin and job files of the respective file cache node.
            Initiate two threads parellely. one for counter another for deadline job submission.
            If the commandline line job submission thread took a while from one thread then the other 
            thread initiate the progress bar and run counter. A recursive deadline commandline line submission
            carried out based upon the number of job submissions. 

            A first submission dont have dependencies. the job id of the first job passed as 
            argument to the same function as so while the second job have dependent job id of the 
            first job. vice versa. 
            """
            
            farm_submit_items = self.get_all_submission_items()
            
            self.current_hip_path = hou.hipFile.path()
            sim_hip_file_path =  self.dl_root_submission_file_path + \
                                "/%s_%s_submission.hip" %(
                                                            hou.hipFile.basename().split(".")[0], 
                                                            self.random_no
                                                        )
            hou.hipFile.save(sim_hip_file_path)

            # Pull the job files path from the HDA it is currently submitting with
            deadline_job_files = []
            for sop_nodes in farm_submit_items:
                sop_node = hou.node("/obj/" + sop_nodes)
                deadline_job_files.append(
                            sop_node.hdaModule().SubmitToDeadline(sop_node)
                )

            # declare the progress bar 
            self.submit_progress = progressBarWindow(self)

            # Execute deadline submission method from a thread 
            # with deadline job files. Which ideadlly a plugin.job and 
            # jobfile.job files 
            self.thread_job_submit = threading.Thread(target=self.dependency_submit_to_deadline,
                                    args = (deadline_job_files,) ,
                                    kwargs={ 'dep_job_id':''}
                                )
            # A second thread which initiate the progress bar and run the counter 
            # during the deadline command line utilies are busy with executing his own task
            self.thread_counter_number = threading.Thread(target=self.calculate_counter)

            # Both thread Started
            self.thread_job_submit.start()
            self.thread_counter_number.start()


        def calculate_counter(self):

            self.process_counter = 0
            while self.process_counter< 360:
                time.sleep(0.1)
                self.submit_progress.progress_bar.setValue(
                                                            self.process_counter * 3.2
                                                        )
                
                if not self.deadline_cmd_Status:
                    self.process_counter = self.process_counter+1
                else: 
                    self.submit_progress.close()
                    self.thread_job_submit.join()
                    break


        def dependency_submit_to_deadline(
                                            self, 
                                            deadline_job_files, 
                                            dep_job_id = ''
                                        ):
            
            if not deadline_job_files:
                QtWidgets.QMessageBox.question(self, 
                                               'FAE Message',
                                                "Submission Node List is Empty", 
                                                QtWidgets.QMessageBox.Ok)
            else:
                self.deadline_cmd_Status = []
                job_files = deadline_job_files.pop(0)

                # Access the plugin_info file of each file cache submission node 
                plugin_info_job_file = ",".join(job_files).split(",")[-1]
                job_info_file = ",".join(job_files).split(",")[0]

                self.build_post_job_script( 
                                           job_info_file, 
                                           plugin_info_job_file
                                        )

                job_names = job_info_file.split("\\")[-1]
                self.submit_progress.job_id_label.setText(
                                                    "Submitting ... %s" %job_names
                                                )

                if self.count == 0 and not dep_job_id:
                    dl_command = '%s %s' %(self.dl_path, " ".join(job_files))
                    first_job_result = subprocess.run(dl_command, 
                                        stdout=subprocess.PIPE, 
                                        shell=True,
                                        text=True)
                    first_job_id = [
                                id 
                                for id in first_job_result.stdout.split() 
                                if 'JobID' in id
                            ][0]
                    first_job_id = first_job_id.split('=')[-1]

                    self.show_job_id.append(first_job_id)
                    self.deadline_cmd_Status.append(first_job_id)
                    
                    self.process_counter = 0
                    self.count = self.count+1

                    self.dependency_submit_to_deadline(deadline_job_files,first_job_id)

                elif self.count>0 and dep_job_id:

                    self.deadline_cmd_Status = []

                    f1 = open(job_files[0], "a")
                    f1.write("\nJobDependencies=%s" %dep_job_id)
                    f1.close()
                    dl_command = '%s %s' %(self.dl_path, " ".join(job_files))
                    dep_submission_result = subprocess.run(dl_command, 
                                        stdout=subprocess.PIPE, 
                                        shell=True,
                                        text=True)
                    job_id = [
                                id 
                                for id in dep_submission_result.stdout.split() 
                                if 'JobID' in id
                            ][0]
                    job_id = job_id.split('=')[-1]

                    self.show_job_id.append(job_id)
                    self.deadline_cmd_Status.append(job_id)

                    self.process_counter = 0
                    self.count = self.count+1
                    
                    if deadline_job_files:
                        self.dependency_submit_to_deadline(deadline_job_files,job_id)
                    else:
                        
                        txt = ""
                        txt = "Submitter Deadline Job Id's\n\n"
                        txt += "  ↓\n".join(self.show_job_id)
                        QtWidgets.QMessageBox.about(self,
                                              "FAE Message Box",
                                              txt
                                              )
                        self.window.close()
                        hou.hipFile.load(self.current_hip_path)

                        self.thread_counter_number.join()


        def build_post_job_script(self, 
                                  job_info_file, 
                                  plugin_info_job_file
                                ):
            
            
            with open(plugin_info_job_file, 'r') as pjf:
                file_data = pjf.readlines() 

            file_cache_node = [
                                line.strip("\n") 
                                for line in file_data
                                if line.startswith('CurrentNodeName')
                            ][0].split('=')[-1] 
            
            hip_file_path = [
                            line.strip("\n") 
                            for line in file_data 
                            if line.startswith('SceneFile')
                            ][0].split('=')[-1]
            
            file_cache_node_name = file_cache_node.split("/")[-1]    
            post_job_py_file = self.dl_root_submission_file_path + \
                                "/%s_%s.py" %(file_cache_node_name, self.random_no)
            post_job_exec_py_file = self.dl_root_submission_file_path + \
                                "/%s_exec_%s.py" %(file_cache_node_name, self.random_no)
            
            script = 'import hou\n'
            script += 'hou.hipFile.load("%s")\n' %hip_file_path
            script += 'node = hou.node("%s")\n' %file_cache_node
            script += 'node.parm("load_from_disk").set(1)\n'
            script += 'hou.hipFile.save("%s")\n' %hip_file_path
            script += 'print("Load disk setted True. Hip File Saved")\n'
            
            with open(post_job_py_file, 'w') as post_job_file:
                post_job_file.write(script)

            hython_path  = "C:\\Program Files\\Side Effects Software\\Houdini 19.5.534\\bin\\hython.exe" 
                                                                                
            exec_script = 'def __main__(*args):\n'
            exec_script += '    import subprocess\n'
            exec_script += '    subprocess.Popen([r"%s", "%s"], shell=True)\n' \
                                                         %(hython_path, post_job_py_file)
            exec_script += '    print("File_cache_node Load_from_disk option sucessfully setted True")\n'
            with open(post_job_exec_py_file, 'w') as post_job_exec_file:
                post_job_exec_file.write(exec_script)

            with open(job_info_file, 'a') as jfl: 
                jfl.write('\nPostJobScript=%s' %post_job_exec_py_file)

            pass                
                        
                         
win = DependencyFileCacheSubmitter()
win.window.show()
