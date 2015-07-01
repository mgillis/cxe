import wx
import copy
from containers import Item
from constants import *


#                                   foregd,     backgd,         font
changed_attr  = wx.ListItemAttr(wx.NullColour, CHANGED_COLOUR,  wx.NullFont)
selected_attr = wx.ListItemAttr(wx.NullColour, SELECTED_COLOUR, wx.NullFont)
changedselected_attr = wx.ListItemAttr(wx.NullColour, CHANGED_SELECTED_COLOUR, wx.NullFont)

class ItemList(wx.ListCtrl):
    def __init__(self, parent):
        wx.ListCtrl.__init__(self, parent, style=wx.LC_SINGLE_SEL|wx.LC_REPORT|wx.LC_VIRTUAL)

        self.fields = ['Type', 'iCost']
        self.data = []

    def OnChangeColumnsDialog(self, e):
        fieldlist = self.data[0].schema.children.keys()
        dlg = wx.MultiChoiceDialog(self, 
                "Choose one or more columns to show in the list",
                "List Columns Selection",
                fieldlist
            )

        used_fields = filter(lambda x: x in fieldlist, self.fields)

        dlg.SetSelections([fieldlist.index(x) for x in used_fields])

        if dlg.ShowModal() == wx.ID_OK:
            choices = dlg.GetSelections()
            if len(choices) > 0:
                self.SetLabelFields([fieldlist[x] for x in choices])

    def SetLabelFields(self, fields_list):
        self.fields = fields_list
        self.Refresh()

    def AutoSize(self):
        if self.GetColumnCount() == 1:
            # hacks
            self.SetColumnWidth(0, self.GetSize()[0] - 30)
        else:
            for i in range(0, self.GetColumnCount()):
                self.SetColumnWidth(i, -2)

    def GetData(self, index):
        if index >= 0 and index < len(self.data):
            return self.data[index]
        else:
            return None

    def GetIndex(self, item=None):
        if item == None:
            return self.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED);
        elif item in self.data:
            return self.data.index(item)
        else:
            return -1

    def OnFieldChange(self, field_name):
        idx = self.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED);
        if idx != -1:
            self.RefreshItem(idx)

    def RefreshValues(self):
        self.SetItemCount(len(self.data))
        self.RefreshItems(0, len(self.data)-1)

    def GetItemDescription(self, item):
        idx = self.data.index(item)
        values = [self.GetItemText(idx, c) for c in range(0,self.GetColumnCount())]
        strings = [("    %s: %s" % (self.fields[i], values[i])) for i in range(0,len(values))]
        return "\n".join(strings)

    def Refresh(self):
        self.ClearAll()

        col = 0
        for label in self.fields:
            self.InsertColumn(col, label, width=-1)
            col += 1

        self.SetItemCount(len(self.data))
        self.AutoSize()

    def GetItems(self):
        return self.data

    def NewItemAfter(self, item):
        idx = self.data.index(item)
        new_item = Item(item.name)
        self.data.insert(idx+1, new_item)
        self.RefreshValues()
        return idx+1

    def InsertCopyAfter(self, item):
        idx = self.data.index(item)
        new_item = copy.deepcopy(item)
        self.data.insert(idx+1, new_item)
        self.RefreshValues()
        return idx+1

    def DeleteItem(self, item):
        idx = self.data.index(item)
        self.data.remove(item)
        self.RefreshValues()
        if idx >= len(self.data):
            return idx - 1
        else:
            return idx

    def SetItems(self, items):
        self.DeleteAllItems()
        self.data = []
        idx = 0

        for i in items:
#           li = wx.ListItem()
#           li.SetId(idx)

#           self.InsertItem(li)
            self.data.append(i)

            idx += 1

        self.Refresh()

    def GetSelectedItem(self):
        idx = self.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED);
        if idx == -1:
            return None
        else:
            return self.data[idx]

    def OnGetItemAttr(self, id):
        item = self.data[id]

        selected = self.GetItemState(id, wx.LIST_STATE_SELECTED) & wx.LIST_STATE_SELECTED

        if selected:
            if item.changed:
                return changedselected_attr
            else:
                return selected_attr
        elif item.changed:
            return changed_attr
        else:
            return None

    def OnGetItemText(self, id, col):
        item = self.data[id]

        if self.fields[col] in item:
            s = item[self.fields[col]]
            if isinstance(s, Item) or isinstance(s, list):
                s = "(%d)" % len(s)
        else:
            s = ""

        if col == 0 and item.changed:
            return str(s) + "*"
        else:
            return str(s)
