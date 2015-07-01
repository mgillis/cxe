import wx

class ScrollingPane(wx.ScrolledWindow):
    def __init__(self, parent):
        wx.ScrolledWindow.__init__(self, parent)

        # default sizer
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.SetSizer(self.sizer)

        self.FitInside()
        self.SetScrollRate(5,5)

        self.Bind(wx.EVT_CHILD_FOCUS, self.OnChildFocus)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnActivity)

        self.last_focus = None

    def OnChildFocus(self, e):
        self.last_focus = self.FindFocus()
        e.Skip()

    def OnActivity(self, e):
        if self.last_focus != None:
            self.last_focus.SetFocus()
        e.Skip()

    def SwapSizer(self, new_sizer):
        self.sizer = new_sizer

        self.SetSizer(new_sizer, True) # delete old

        new_sizer.Layout()
        self.FitInside()

    def GetActiveItem(self):
        return self.GetParent().GetActiveItem()
