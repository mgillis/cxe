import wx.grid

from constants import *
from containers import *

class DynaTable(wx.grid.Grid):
    def __init__(self, parent, item_schema, value_name):
        wx.grid.Grid.__init__(self, parent)

        self.item_schema = item_schema
        self.value_name = value_name
        self.item = None

        self.row_name = None
        self.group_name = None

        self.SetRowLabelSize(10)
        self.SetDefaultColSize(150, True)

        self.SetUp()

        self.Bind(wx.grid.EVT_GRID_COL_SORT, self.OnHeaderClick)
        self.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK, self.OnCellClick)
        self.Bind(wx.grid.EVT_GRID_CELL_CHANGE, self.OnCellChange)
        self.Bind(wx.EVT_KILL_FOCUS, self.OnBlur)

        self.normal_labelbgcolour = self.GetLabelBackgroundColour()
        self.normal_defaultcellbgcolour = self.GetDefaultCellBackgroundColour()

        self.changed = False

    def OnBlur(self, e):
        # wx is weird so we have to manually do this or it fires later
        self.SaveEditControlValue()
        e.Skip()

    def StopEditing(self):
        self.SaveEditControlValue()
        #self.EnableCellEditControl(False)

    def _ClearChanged(self):
        self.changed = False
        self.SetLabelBackgroundColour(self.normal_labelbgcolour)
        self.SetDefaultCellBackgroundColour(self.normal_defaultcellbgcolour)

    def SetChanged(self):
        if not self.changed:
            self.changed = True
            self.SetLabelBackgroundColour(CHANGED_COLOUR)
            self.SetDefaultCellBackgroundColour(CHANGED_COLOUR)
            self.ForceRefresh()
            self.item.changed = True


    def SetUp(self):
        self.indices = {}

        if self.item_schema.type == DType.COMPLEX:
            # something like TerrainTrades -> TerrainTrade -> stuff

            self.CreateGrid(0, len(self.item_schema.children) + 1)

            col = 0
            for (col_name, col_sch) in self.item_schema.children.items():
                self.SetColLabelValue(col, col_name)
                if col_sch.type == DType.INTEGER:
                    self.SetColFormatNumber(col)
                elif col_sch.type == DType.BOOLEAN:
                    self.SetColFormatBool(col)

                self.indices[col_name] = col
                col += 1

            self.SetColLabelValue(col, "+")
            self.SetColSize(col, 20)
            self.add_del_col = col

        else:
            # something like CommerceFlexible -> bFlexible, bFlexible...
            self.CreateGrid(0, 2)

            self.SetColLabelValue(0, self.item_schema.name)
            if self.item_schema.type == DType.INTEGER:
                self.SetColFormatNumber(0)
            elif self.item_schema.type == DType.BOOLEAN:
                self.SetColFormatBool(0)

            self.indices[self.item_schema.name] = 0

            self.SetColLabelValue(1, "+")
            self.SetColSize(1, 20)
            self.add_del_col = 1

    def OnHeaderClick(self, e):
        if e.GetCol() == self.add_del_col:
            self.AppendRows(1)
            new_row = self.GetNumberRows() - 1
            self.SetCellValue(new_row, self.add_del_col, "-")
            self.ClearSelection() #otherwise things are selected by this click
            self.SaveToItem()
            self.SetChanged()
            wx.PostEvent(self, CXEItemChangedEvent(self, ))
            self.Fit()
            self.GetParent().Fit()
            self.GetParent().GetParent().FitInside()
            self.GetParent().GetParent().Refresh()

        # we're not sorting
        e.Veto()

    def OnCellClick(self, e):
        if e.GetCol() == self.add_del_col:
            self.DeleteRows(e.GetRow())
            self.SaveToItem()
            self.SetChanged()
            wx.PostEvent(self, CXEItemChangedEvent(self))
            self.Fit()
            self.GetParent().Fit()
            self.GetParent().GetParent().FitInside()
            self.GetParent().GetParent().Refresh()
            e.Veto()
        else:
            # don't care
            e.Skip()

    def SaveToItem(self):
        # set item
        item = self.item

        #print "Saving to item %s"  % item
        
        values = []

        if self.row_name == self.GetColLabelValue(0):
            # simple things
            for j in range(0, self.GetNumberRows()):
                values.append(self.GetCellValue(j,0))

        else:
            for j in range(0, self.GetNumberRows()):
                row = Item(self.row_name)
                for k in range(0, self.GetNumberCols() - 1): # skip add/del col
                    colname = self.GetColLabelValue(k)
                    row[colname] = self.GetCellValue(j, k)
                values.append(row)

        container = Item(self.group_name)
        container[self.row_name] = values
        item[self.group_name] = container

    def OnCellChange(self, e):
        self.SaveToItem()
        self.SetChanged()
        print "OnCellChange!"
        wx.PostEvent(self, CXEItemChangedEvent(self))
        self.GetParent().FitInside()
        self.GetParent().GetParent().FitInside()
        self.GetParent().GetParent().Refresh()
        e.Skip()

    def SetRows(self, item, group_name, value):
        self.ClearGrid()

        self.item = item

        if self.GetNumberRows() > 0:
            self.DeleteRows(0, self.GetNumberRows())

        self.group_name = group_name
        self.row_name = self.item_schema.name

        #        if group_name == "CommerceFlexible":
        #            print "CommerceFlexible: %s" % value

        if value != None and self.item_schema.name in value:
            value_list = value[self.item_schema.name]
            row = -1

            if len(value_list) == 0:
                pass

            elif isinstance(value_list[0], Item):
                for obj in value_list:
                    self.AppendRows(1)
                    row += 1
                    for (key, col) in self.indices.items():
                        v = obj[key]
                        if type(v) == bool:
                            v = str(int(v))
                        else:
                            v = str(v)
                        self.SetCellValue(row, col, v)
                    self.SetCellValue(row, self.add_del_col, "-")
                    self.SetReadOnly(row, self.add_del_col)

            else:
                # something like OrPreReqs
                for v in value[self.item_schema.name]:
                    self.AppendRows(1)
                    row += 1
                    if type(v) == bool:
                        v = str(int(v))
                    else:
                        v = str(v)
                    self.SetCellValue(row, 0, v)
                    self.SetCellValue(row, self.add_del_col, "-")
                    self.SetReadOnly(row, self.add_del_col)

        self._ClearChanged()
        self.ForceRefresh()
        self.Fit()

