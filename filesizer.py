import sys
import os
from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QScrollArea, 
    QVBoxLayout, QPushButton, QProgressBar, QLabel,
    QHBoxLayout
)
"""

General design:  create a tree data structure holding the sizes of all the files
Add up all the sub trees into sorted buttons for everything we're trying to track
Press a button to open a sub tree
Allow a slick user interface into where the disk space is going
"""

class DataModel(QObject):
    variable_changed = pyqtSignal(str)

    def __init__(self, mytree):
        super().__init__()
        self._mytree = mytree

    @property
    def mytree(self):
        return self._mytree

    @mytree.setter
    def mytree(self, value):
        self._mytree = value
        self.variable_changed.emit(f"Dynamic Button {value}")
        
        
class ClickRow(QWidget):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

        
class ScrollWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("File Size Explorer")
        self.setGeometry(100, 100, 800, 600)
        self.pretree = {}
        self.starttree = 'c:\\'
        self.openpaths = {self.starttree: True}
        self.travtree = DataModel(self.pretree)
        self.travtree.variable_changed.connect(self.add_in_buttons)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content_widget = QWidget()
        self.layout = QVBoxLayout(content_widget)
        self.mylabel = QLabel("Button not pushed yet", self)
        self.layout.addWidget(self.mylabel)
        self.refresh_button = QPushButton("Refresh Data")        
        self.refresh_button.clicked.connect(self.wrapper)
        self.layout.addWidget(self.refresh_button)
        # We don't have a good enough idea when we'll finish for a progress bar
        #self.pb = QProgressBar(content_widget)
        #self.pb.setProperty("value", 0)
        scroll_area.setWidget(content_widget)
        self.setCentralWidget(scroll_area)
        
    def wrapper(self):
        #self.pb.setRange(0, 100)
        #self.pb.setValue(50)
        self.mylabel.setText("Scanning Drive....")
        self.mylabel.repaint()
        tree = self.starttree
        self.refreshdata(tree)
        #for mykey in self.travtree.mytree:
        #    print(mykey)
        self.mylabel.setText("Scan Complete")
        self.add_in_buttons()
        self.mylabel.repaint()
        #self.pb.setRange(0, 100)
        #self.pb.setValue(100)
        
    def mysizer(self, mykey, mysize):
        if mykey not in self.travtree.mytree:
            # strip off the final sep
            mykey = mykey[:-1]
            if mykey not in self.travtree.mytree:
                #print(f'no key {mykey} size {mysize}')
                return mysize
        for mysubkey in self.travtree.mytree[mykey]:
            mysize += mysubkey[1]  
            # we mark dir's with 0 size
            if mysubkey[1] == 0:
                #print(f'following {mysubkey[0]} {mysize}')
                # this will not work if mykey doesn't end with os.sep
                mysize = self.mysizer(mykey + mysubkey[0] + os.sep, mysize)
        #print(f'returning {mysize}')
        return mysize
        
    def clear_dynamic_widgets(self):
        for i in reversed(range(self.layout.count())):
            item = self.layout.itemAt(i)
            widget = item.widget()
    
            # Skip permanent widgets
            if widget in (self.mylabel, self.refresh_button):
                continue
    
            # Delete dynamic widgets
            if widget:
                widget.setParent(None)
                widget.deleteLater()
    
    def add_in_buttons(self):
        # Clear old widgets
        self.clear_dynamic_widgets()
    
        # Build sorted list of (path, size)
        entries = {}
        for mykey in self.travtree.mytree:
            path_parts = mykey.split(os.sep)
            # get the parent folder to slot this under
            upone = os.sep.join(path_parts[:-2]) + os.sep
            if len(upone) < 2: upone = self.starttree
            openkey_path_parts = []
            cango = False
            # root structures are always visible
            if len(path_parts) <= 3:
                cango = True
            else:
                for openkey in self.openpaths:
                    openkey_path_parts = openkey.split(os.sep)
                    thisgo = True
                    if len(path_parts) - 1 == len(openkey_path_parts):
                        for compx, compy in zip(path_parts, openkey_path_parts):
                            # these are empty string terminated
                            if len(compx) < 1 or len(compy) < 1:
                                continue
                            if compx != compy:
                                thisgo = False
                                break
                        cango = thisgo
                        if cango: break
            if cango:
                if mykey not in entries:
                    entries[mykey] = []
                if upone not in entries:
                    entries[upone] = []
                mysize = 0
                # get the files in this folder too
                if mykey in self.openpaths:
                    for mysubkey in self.travtree.mytree[mykey]:
                        #print(cango, mykey, mysubkey, upone)
                        if mysubkey[1] > 0:
                            entries[mykey].append((mykey, mysubkey[0], mysubkey[1]))
                # recursize function to get all the subdir sizes
                mysize = self.mysizer(mykey, mysize)            
                entries[upone].append((mykey, mykey, mysize))
    
        # sort so each open entry is sorted descending by size
        for mykey in entries:
            entries[mykey].sort(key=lambda x: x[2], reverse=True)
                
        # Create buttons
        self.create_clickable_rows(self.starttree, entries)
        
    def create_clickable_rows(self, mydir, entries):
        for path, name, size in entries[mydir]:
            self.make_row(path, name, size)
            if name in entries and name != self.starttree:
                self.create_clickable_rows(name, entries)

    def open_subtree(self, path):
        # toggle
        if path != self.starttree:
            if path in self.openpaths:
                del self.openpaths[path]
            else:
                self.openpaths[path] = True
        self.add_in_buttons()
            
    def refreshdata(self, tree):
        #if 'ProgramData' not in tree and len(tree) > 7: #for testing purposes
        #    return False
        try:
            subdirs = [d.name for d in os.scandir(tree) if os.path.isdir(tree + d.name)]
        except (PermissionError, FileNotFoundError) as myerr:
            print('cannot scan ', tree, myerr)
            return False
        for mysubdir in subdirs:
            if tree not in self.travtree.mytree:
                self.travtree.mytree[tree] = []
            self.travtree.mytree[tree].append([mysubdir, 0])
            self.refreshdata(tree + mysubdir + os.sep)
        try:
            subfiles = [f.name for f in os.scandir(tree) if os.path.isfile(tree + os.sep + f.name)]
        except (PermissionError, FileNotFoundError) as myerr:
            print('cannot scan ', tree, myerr)
            return False
        for mysubfile in subfiles:
            try:
                filesize = os.path.getsize(tree + os.sep + mysubfile)
            except (PermissionError, FileNotFoundError) as myerr:
                print('cannot scan ', tree, myerr)
                continue
            if tree not in self.travtree.mytree:
                self.travtree.mytree[tree] = []
            self.travtree.mytree[tree].append([mysubfile, filesize])
        return True
    
    def make_row(self, path, name, size):
        row = ClickRow()
        h = QHBoxLayout(row)
    
        prefix = ""
        pathlen = path.split(os.sep)
        for counter in range(3, len(pathlen)):
            prefix += "|--"
        # files get one more indent
        if path != name:
            prefix += "|--"
        left = QLabel(f"{prefix}{name}")
        right = QLabel(f"{size:,}")
        right.setStyleSheet("font-weight: bold;")
    
        h.addWidget(left)
        h.addStretch(1)
        h.addWidget(right)
    
        row.clicked.connect(lambda: self.open_subtree(name))
        self.layout.addWidget(row)
    
    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ScrollWindow()
    window.show()
    sys.exit(app.exec())
