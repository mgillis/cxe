import wxversion

import wx
import os
import re
import datetime
import sys

from xml.dom import minidom
from table import *
from containers import *
from scrolling import *
from listctrl import *

import cxexml

BASE_MODS_DIR = "C:\\Program Files (x86)\\Firaxis Games\\Sid Meier's Civilization 4\\Beyond the Sword\\Mods"

wx_map = {}

schema_filename = ""
main_element_name = ""
schema = None

def file_comments():
    return [
        "Created with the CXE tool",
        str(datetime.datetime.now())
    ]

def write_file(items, f):
    global schema_filename
    global schema
    root_name = "Civ4%ss" % (main_element_name)

    doc = minidom.getDOMImplementation().createDocument(None, root_name, None)
    root = doc.documentElement

    root.setAttribute("xmlns", "x-schema:%s" % schema_filename)

    for c in file_comments():
        root.appendChild(doc.createComment(c))

    container = doc.createElement(main_element_name + "s")
    root.appendChild(container)

    for i in items:
        el = doc.createElement(main_element_name)
        schema.write_into_element(doc, el, i)
        container.appendChild(el)

    doc.writexml(f, "", "\t", "\n")
    return True

def load_file(win, f):
    global wx_map
    global schema_filename
    global main_element_name
    global schema

    wx_map = {}

    win.SetStatusText("Parsing XML...")
    try:
        root = cxexml.parse(f)
    except Exception, e:
        error("Unexpected error parsing XML: %s" + e)
        return False
    
    schema_filename = root.documentElement.getAttribute("xmlns").split(':',1)[-1]

    if schema_filename == "":
        error("No schema!")
        return False
    elif schema_filename[0:1] == "//":
        error("XML has invalid schema filename '%s'." % schema_filename)
        return False

    win.SetStatusText("Loading and parsing schema (%s)..." % schema_filename)

    schema_root = cxexml.parse(os.path.join(win.dirname, schema_filename))

    # determine main element
    main_element_name = re.search('Civ4(.+)s$', root.documentElement.tagName).group(1)

    win.SetStatusText("Loading %ss...\n" % main_element_name)

    schema = SchemaElement.from_xml(schema_root, main_element_name, defns={})

    items = read_objects(schema, root.getElementsByTagName(main_element_name), main_element_name)

    # FIXME ??
    win.listctrl.SetItems(items)

    # make a wx structure based on schema

    new_scroller = ScrollingPane(win)
    grid = wx.GridBagSizer(vgap=0, hgap=0)
    
    win.SetStatusText("Creating layout...\n")
    win.Freeze()
    add_to_grid(new_scroller, grid, schema)

    grid.AddGrowableCol(0,1)
    grid.AddGrowableCol(1,2)
    grid.AddGrowableCol(2,1)
    grid.AddGrowableCol(3,2)
    grid.AddGrowableCol(4,1)
    grid.AddGrowableCol(5,2)

    new_scroller.SwapSizer(grid)
    win.SwapScroller(new_scroller)
    win.Thaw()

    win.SetStatusText("") # sometimes the layout status text doesn't disappear
    win.SelectItem()

class TypedTextCtrl(wx.TextCtrl):
    def __init__(self, parent, dtype):
        wx.TextCtrl.__init__(self, parent)

        self.datatype = dtype
        if dtype == DType.INTEGER:
            self.SetMaxLength(9) # we can't hold much more capn (that's all the bits we've got)
        self.Bind(wx.EVT_TEXT, self.OnChange)

    def OnChange(self, e):
        if self.datatype == DType.INTEGER:
            uvalue = unicode(self.GetValue())
            if not uvalue.isnumeric():
                self.SetForegroundColour(wx.RED)
            else:
                self.SetForegroundColour(wx.NullColour)

        e.Skip()


def add_to_grid(parent, grid, schema):
    row = 0
    col = 0
    COLMAX = 5
    messy = False

    # now do something cool with the schema
    for (name, sch) in schema.children.items():
        if col > COLMAX:
            col = 0
            row += 1
            messy = False

        if sch.type != DType.COMPLEX:
            text = sch.name
            if not sch.optional:
                text += "*"
        
            if sch.type == DType.STRING:
                label = wx.StaticText(parent, wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE)
                label.SetLabel(text)

                box = TypedTextCtrl(parent, sch.type)
                wx_map[sch.name] = box
                box.value_name = sch.name

                if messy:
                    col = 0
                    row += 1
                    messy = False

                if col > 0 and col < 3:
                    col = 3
                elif col > 3:
                    col = 0
                    row += 1

                grid.Add(label, (row, col), flag=wx.ALL|wx.EXPAND, border=8)
                grid.Add(box, (row, col+1), (1, 2), flag=wx.ALL|wx.EXPAND, border=8)
                col += 3

            elif sch.type == DType.INTEGER:
                label = wx.StaticText(parent, wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE)
                label.SetLabel(text)

                box = TypedTextCtrl(parent, sch.type)
                wx_map[sch.name] = box
                box.value_name = sch.name

                if messy:
                    col = 0
                    row += 1
                    messy = False
                if col == 3:
                    col = 4

                grid.Add(label, (row, col), flag=wx.ALL|wx.EXPAND, border=8)
                grid.Add(box, (row, col+1), flag=wx.ALL|wx.EXPAND, border=8)
                col += 2

            elif sch.type == DType.BOOLEAN:
                box = wx.CheckBox(parent, label=text,) # style=wx.ALIGN_RIGHT)
                wx_map[sch.name] = box
                box.value_name = sch.name

                grid.Add(box, (row, col), flag=wx.EXPAND|wx.ALL, border=4)
                col += 1
            else:
                error("Internal error: unknown simple type (%s) in layout process." % sch.type)

        else:
            if col > 0 and not messy:
                # we need it messy ^_^
                col = 0
                row += 1
            elif col > 0 and col < 3:
                col = 3
            elif col > 3:
                col = 0
                row += 1

            subwin = wx.Window(parent)
            sizer = wx.BoxSizer(wx.VERTICAL)
            subwin.SetSizer(sizer)

            label = wx.StaticText(subwin)
            label.SetLabel(sch.name)

            sizer.Add(label, 0, flag=wx.ALL, border=0)

            item_schema = sch.children.values()[0]

            # was parent, blah, blah
            table = DynaTable(subwin, item_schema, sch.name)
            wx_map[sch.name] = table

            sizer.Add(table, 0, flag=wx.ALL, border=0)

            grid.Add(subwin, (row, col), (1,3), flag=wx.ALL|wx.EXPAND, border=8)
            messy = True

            col += 3

def read_objects(item_schema, elements, main_element_name):
    items = []

    for e in elements:
        item = Item(main_element_name)

        success = item_schema.read_into_item(e, item)

        if success:
            items.append(item[main_element_name])
        else:
            return []

    return items

class MainWindow(wx.Frame):

    def SwapScroller(self, new_scroller):
        if self.scroller != None:
            self.sizer.Detach(self.scroller)
            self.scroller.Destroy()

        self.scroller = new_scroller
        self.sizer.Add(self.scroller, 2, wx.ALL|wx.EXPAND, border=15)
        self.Fit()
        self.Refresh()

    def __init__(self, parent, title):

        if os.path.exists(BASE_MODS_DIR):
            self.dirname = BASE_MODS_DIR
        else:
            self.dirname = '/'
        self.filename=None
        self.active_item = None
        self.changed = False

        wx.Frame.__init__(self, parent, title=title, size=(800,800))
        self.CreateStatusBar() # A Statusbar in the bottom of the window

        # Setting up the menu.
        # Creating the menubar.
        menuBar = wx.MenuBar()

        filemenu= wx.Menu()
        menuOpen = filemenu.Append(wx.ID_OPEN, "&Open...\tCtrl+O"," Open a file to edit")
        menuSave = filemenu.Append(wx.ID_SAVE, "&Save\tCtrl+S"," Write your work to the file")
        menuSaveAs = filemenu.Append(wx.ID_SAVEAS, "S&ave As...\tCtrl+Alt+S"," Write your work to a specific file")
        menuRevert = filemenu.Append(wx.ID_REVERT_TO_SAVED, "&Revert\tCtrl+R"," Reload the file")
        #menuAbout= filemenu.Append(wx.ID_ABOUT, "&About"," Information about this program")
        menuExit = filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")

        menuBar.Append(filemenu,"&File") # Adding the "filemenu" to the MenuBar

        viewmenu = wx.Menu()
        menuListColumns = viewmenu.Append(wx.ID_ANY, "Change &list columns...\tCtrl+L", "Change the columns displayed on the left-hand side list.")
        menuBar.Append(viewmenu, "&View")

        navmenu = wx.Menu()
        menuUp   = navmenu.Append(wx.ID_UP, "&Previous item\tCtrl+Up", "Display the previous item.")
        menuDown = navmenu.Append(wx.ID_DOWN, "&Next item\tCtrl+Down", "Display the next item.")
        menuBar.Append(navmenu, "&Navigate")

        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.


        self.sizer = wx.BoxSizer(wx.HORIZONTAL)

        buttonsizer = wx.BoxSizer(wx.HORIZONTAL)
        leftsidesizer = wx.BoxSizer(wx.VERTICAL)

        addbutton = wx.Button(self, wx.ID_ADD, "Insert &New")
        copybutton = wx.Button(self, wx.ID_COPY, "Insert &Copy")
        delbutton = wx.Button(self, wx.ID_DELETE, "&Delete")
        buttonsizer.Add(addbutton, 1, wx.ALL|wx.EXPAND, border=8)
        buttonsizer.Add(copybutton, 1, wx.ALL|wx.EXPAND, border=8)
        buttonsizer.Add(delbutton, 1, wx.ALL|wx.EXPAND, border=8)

        self.listctrl = ItemList(self)
        leftsidesizer.Add(self.listctrl, 1, wx.EXPAND)
        leftsidesizer.Add(buttonsizer, 0, wx.EXPAND)

        self.sizer.Add(leftsidesizer, 1, wx.ALL|wx.EXPAND, border=15)
        self.sizer.SetItemMinSize(leftsidesizer, (150,300))

        self.scroller = ScrollingPane(self)
        self.sizer.Add(self.scroller, 4, wx.ALL|wx.EXPAND, border=15)
        self.SetSizer(self.sizer)


        # Events.
        self.Bind(wx.EVT_MENU, self.OnOpen, menuOpen)
        self.Bind(wx.EVT_MENU, self.OnSave, menuSave)
        self.Bind(wx.EVT_MENU, self.OnSaveAs, menuSaveAs)
        self.Bind(wx.EVT_MENU, self.OnRevert, menuRevert)
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit)

        self.Bind(wx.EVT_MENU, self.listctrl.OnChangeColumnsDialog, menuListColumns)

        self.Bind(wx.EVT_MENU, self.OnUp, menuUp)
        self.Bind(wx.EVT_MENU, self.OnDown, menuDown)
        
        #self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
        self.Bind(wx.EVT_TEXT, self.OnTextChange)
        self.Bind(wx.EVT_CHECKBOX, self.OnCheckBox)

        self.Bind(wx.EVT_BUTTON, self.OnAdd, addbutton)
        self.Bind(wx.EVT_BUTTON, self.OnCopy, copybutton)
        self.Bind(wx.EVT_BUTTON, self.OnDelete, delbutton)

        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnListSelect, self.listctrl)
        self.Bind(EVT_CXE_ITEM_CHANGED, self.OnItemModified, None)

        self.Show()

        # DEBUG
        #self.dirname += "\\FFH2 BGE\\Assets\\XML"

    def OnCheckBox(self,e):
        control = e.GetEventObject()
        self._changed_control(control)

    def _changed_control(self,control):
        if not ('value_name' in control.__dict__):
            return

        if self.active_item != None:
            control.SetBackgroundColour(CHANGED_COLOUR)
            control.Refresh()
            self.active_item[control.value_name] = control.GetValue()
            self.active_item.changed = True
            wx.PostEvent(control, CXEItemChangedEvent(control))


    def OnTextChange(self,e):
        control = e.GetEventObject()
        self._changed_control(control)

    def OnItemModified(self, e):
        control = e.GetEventObject()
        self.active_item.change_set.add(control)
        self.listctrl.OnFieldChange(control.value_name)

        if not self.changed:
            self.changed = True
            self.SetTitle("CXE - " + self.filename + "*")

    def OnAdd(self, e):
        index = self.listctrl.NewItemAfter(self.active_item)
        self.SelectItem(index)

    def OnCopy(self, e):
        index = self.listctrl.InsertCopyAfter(self.active_item)
        self.SelectItem(index)

    def OnDelete(self,e):
        dlg = wx.MessageDialog(self, "Really delete the current item? \n" + self.listctrl.GetItemDescription(self.active_item), "Delete Item?", wx.YES_NO)

        if dlg.ShowModal() == wx.ID_YES:
            index = self.listctrl.DeleteItem(self.active_item)
            self.SelectItem(index)

    def OnListSelect(self,e):
        #single select, change if that changes
        self.SelectItem(e.GetIndex())

    def OnUp(self, e):
        i = self.listctrl.GetIndex()
        if i != 0:
            self.SelectItem(i-1)

    def OnDown(self, e):
        i = self.listctrl.GetIndex()

        # GetData in SelectItem will just return None if we're past the end
        self.SelectItem(i+1)

    def SelectItem(self, index = 0):
        item = self.listctrl.GetData(index)

        if item == None:
            return

        self.listctrl.SetItemState(index, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
        self.listctrl.EnsureVisible(index)
        self.ShowItem(item)
        self.active_item = item

    def ShowItem(self, item):
        if item == None:
            raise ArgumentError("nope")

        for (name, control) in wx_map.items():
            if name in item:
                value = item[name]

                if type(value) == int:
                    value = str(value)
            else:
                value = None

            if isinstance(control, wx.CheckBox):
                control.SetValue(bool(value))
            elif isinstance(control, DynaTable):
                control.StopEditing()
                control.SetRows(item, name, value)
            else:
                control.ChangeValue(value or "")
                if control.HasFocus() and isinstance(control, wx.TextCtrl):
                    control.SetInsertionPointEnd()

            if isinstance(control, DynaTable):
                if control in item.change_set:
                    control.SetChanged()
            else:
                control.SetBackgroundColour(wx.NullColour)
                if control in item.change_set:
                    control.SetBackgroundColour(CHANGED_COLOUR)

        self.scroller.Refresh()
        self.scroller.FitInside()

    def GetActiveItem(self):
        return self.active_item

    def OnAbout(self,e):
        # Create a message dialog box
        dlg = wx.MessageDialog(self, " A sample editor \n in wxPython", "About Sample Editor", wx.OK)
        dlg.ShowModal() # Shows it
        dlg.Destroy() # finally destroy it when finished.

    def OnExit(self,e):
        self.Close(True)  # Close the frame.

    def OnSave(self,e):
        if self.filename != None and self.dirname != None:
            self.SaveAsSetFile()
        else:
            self.OnSaveAs(e)

    def OnSaveAs(self,e):
        if self.active_item == None:
            # we don't even have any data, go away kid
            return
        dlg = wx.FileDialog(self, "Choose or enter a filename to save XML", self.dirname, "", "*.xml", wx.SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            self.filename = dlg.GetFilename()
            self.dirname = dlg.GetDirectory()
            self.SaveAsSetFile()

    def SaveAsSetFile(self):
        if self.filename == None or self.dirname == None:
            crash("SaveAsSetFile without set filename/dirname???")

        path = os.path.join(self.dirname, self.filename)
        try:
            f = open(path, 'w')
        except IOError, e:
            error("Couldn't open %s for writing: %s" % (path, e))
        
        self.SetStatusText("Saving to %s..." % path)

        items = self.listctrl.GetItems()
        write_file(items, f)
        f.close()
        for item in items:
            item.set_saved()

        # redraw for colour fixes
        self.listctrl.RefreshValues()
        self.ShowItem(self.active_item)

        self.SetStatusText("Saved to %s." % path)
        self.SetTitle("CXE - " + self.filename)
        self.changed = False

    def OnRevert(self,e):
        if self.filename != None and self.dirname != None:
            success = self.ReadFile()
            if success:
                self.SetStatusText("%s reloaded." % self.filename)

    def ReadFile(self):
        try:
            f = open(os.path.join(self.dirname, self.filename), 'r')
        except IOError, e:
            error("Couldn't open %s for reading: %s" % (self.filename, e))
            return False
        load_file(self, f)
        f.close()
        self.SetTitle("CXE - " + self.filename)
        return True

    def OnOpen(self,e):
        """ Open a file"""
        dlg = wx.FileDialog(self, "Choose an XML file", self.dirname, "", "*.xml", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.filename = dlg.GetFilename()
            self.dirname = dlg.GetDirectory()
            success = self.ReadFile()

            if success:
                self.listctrl.SetFocus()
                self.SetStatusText("%s opened." % self.filename)

        dlg.Destroy()

app = wx.App(False)
frame = MainWindow(None, "CXE")
app.MainLoop()
